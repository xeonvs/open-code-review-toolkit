"""Exercise the qualified native Analysis handoff and its private CLI boundary."""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from ocr_toolkit import cli, native_capabilities, preflight, review_analysis, review_runner
from ocr_toolkit.result_contract import parse_result_outcome
from tests.test_ocr_compat import load_script

RAW_MARKER = "Synthetic raw Analysis trace only."
REPORT_TEXT = "The example returns a different value."
FORBIDDEN_REPORT = "provider credential synthetic-model-access-token"


def _combined(markdown: str = REPORT_TEXT) -> dict:
    return {
        "schema_version": review_analysis.COMBINED_SCHEMA,
        "status": "complete",
        "review_status": "complete",
        "analysis": markdown,
        "analysis_raw": RAW_MARKER,
        "session_id": RAW_MARKER,
        "analysis_meta": {
            "schema_version": review_analysis.METADATA_SCHEMA,
            "execution_status": "completed",
            "submission_accepted": True,
            "declared_completion": "partial",
            "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
            "artifact_dir": RAW_MARKER,
            "scope": [{"path": RAW_MARKER}],
        },
    }


@pytest.mark.parametrize(
    ("flag", "expected"),
    [("--analysis", True), ("--analysis=false", False)],
)
def test_analysis_option_forms_keep_model_only_flags_out_of_review_args(flag, expected):
    review_args, options = review_analysis.extract_options(
        ["--from", "base", flag, "--analysis-max-tokens-budget=42", "--to", "head"],
        {"OCR_ANALYSIS": "false", "OCR_ANALYSIS_MAX_TOKENS_BUDGET": "10"},
    )
    assert options.enabled is expected
    assert options.budget == 42
    assert review_args == ["--from", "base", "--to", "head"]


@pytest.mark.parametrize("value", ["", "-1", "1.5", "9223372036854775808"])
def test_analysis_rejects_invalid_budget(value):
    with pytest.raises(ValueError, match="non-negative 64-bit integer"):
        review_analysis.extract_options(["--analysis-max-tokens-budget", value], {})


@pytest.mark.parametrize("field", ["execution_status", "submission_accepted", "schema_version"])
def test_invalid_analysis_metadata_degrades_without_reclassifying_review(field):
    payload = _combined()
    payload["analysis_meta"][field] = {"raw": RAW_MARKER}
    assert review_analysis.admit_analysis(payload, requested=True, forbidden=()) == {
        "status": "unavailable"
    }
    assert payload == {"status": "complete"}


def test_analysis_review_status_mismatch_rejects_result():
    payload = _combined()
    payload["review_status"] = "skipped"
    with pytest.raises(ValueError, match="primary review outcome"):
        review_analysis.admit_analysis(payload, requested=True, forbidden=())


@pytest.mark.parametrize("counts", [{"total_tokens": True}, {"input_tokens": 2**63}])
def test_invalid_analysis_usage_is_omitted(counts):
    payload = _combined()
    payload["analysis_meta"]["usage"] = counts
    assert review_analysis.admit_analysis(payload, requested=True, forbidden=()) == {
        "status": "completed",
        "declared_completion": "partial",
        "markdown": REPORT_TEXT,
    }


@pytest.mark.parametrize(
    ("exit_code", "classification", "reserved", "retained"),
    [
        (1, "provider", "", True),
        (1, "budget", "", False),
        (2, "provider", "", False),
        (1, "provider", "_ocr_toolkit", False),
        (1, "provider", "toolkit_analysis", False),
        (1, "provider", "analysis_raw", False),
    ],
)
def test_nonzero_handoff_requires_native_operational_partial_coverage(
    tmp_path, exit_code, classification, reserved, retained
):
    payload = {
        "status": "partial",
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "partial",
            "coverage": {
                "selected": [{"item_id": "done"}, {"item_id": "failed"}],
                "completed": [{"item_id": "done"}],
                "failed": [{"item_id": "failed", "classification": classification}],
                "reused": [],
                "waived": [],
            },
        },
    }
    assert parse_result_outcome(payload).operational_partial is (classification != "budget")
    if reserved:
        payload[reserved] = RAW_MARKER
    result = tmp_path / "native-result.json"
    result.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        review_runner._failed_review_result_is_partial(
            result, exit_code=exit_code, analysis_requested=False
        )
        is retained
    )
    assert result.exists() is retained


@pytest.mark.parametrize(
    ("markdown", "exit_code", "partial", "expected_exit"),
    [
        (REPORT_TEXT, 0, False, 0),
        (FORBIDDEN_REPORT, 0, False, 0),
        ("x" * 64001, 0, False, 0),
        (REPORT_TEXT, 1, True, 1),
        (REPORT_TEXT, 0, True, 2),
        (REPORT_TEXT, 1, False, 1),
    ],
)
def test_analysis_cli_runs_plain_preview_and_delivers_only_admitted_private_markdown(
    tmp_path, monkeypatch, capsys, markdown, exit_code, partial, expected_exit
):
    compat = load_script()
    git_environment = compat.execution._isolated_probe_environment(tmp_path / "git-home")
    repo, base, head = compat.execution._synthetic_repo(tmp_path, git_environment)
    monkeypatch.chdir(repo)

    combined = _combined(markdown)
    combined.update(
        status="skipped",
        review_status="skipped",
        comments=[],
        tool_calls={"total": 0, "by_tool": {}},
        manifest={
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "skipped",
            "input": {
                "mode": "range",
                "requested_from": base,
                "requested_head": head,
                "resolved_base": base,
                "resolved_head": head,
                "exact_range": f"{base}..{head}",
            },
            "coverage": {
                key: [] for key in ("selected", "completed", "failed", "reused", "waived")
            },
        },
    )
    if partial:
        combined.update(status="partial", review_status="partial")
        combined["manifest"]["terminal_state"] = "partial"
        combined["manifest"]["coverage"].update(
            selected=[{"item_id": "done"}, {"item_id": "unreviewed"}],
            completed=[{"item_id": "done"}],
            failed=[{"item_id": "unreviewed", "classification": "provider"}],
        )
        combined["tool_calls"] = {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}
    payload = tmp_path / "native.json"
    payload.write_text(json.dumps(combined), encoding="utf-8")
    calls_path = tmp_path / "process.jsonl"
    binary = tmp_path / "ocr"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "if args == ['--version']:\n"
        "    print('Open Code Review 1.14.2')\n"
        "    raise SystemExit(0)\n"
        "home = Path(os.environ['HOME'])\n"
        f"with open({str(calls_path)!r}, 'a', encoding='utf-8') as calls:\n"
        "    print(json.dumps({'args': args, 'home': str(home), 'leaked_env': "
        "any(key in os.environ for key in ('OCR_ANALYSIS', 'OCR_ANALYSIS_MAX_TOKENS_BUDGET', "
        "'OCR_RAW_LOGGING'))}), file=calls)\n"
        "if '--preview' in args:\n"
        "    print('{\"files\": []}')\n"
        "else:\n"
        "    session = home / '.opencodereview' / 'sessions' / 'synthetic' / 'analysis'\n"
        "    session.mkdir(parents=True)\n"
        f"    session.joinpath('trace.log').write_text({RAW_MARKER!r})\n"
        f"    if {partial!r}:\n"
        "        from ocr_toolkit.evidence.actions import record_action\n"
        "        from ocr_toolkit.evidence.artifacts import repository_artifacts\n"
        "        receipt = repository_artifacts().action_receipt\n"
        "        record_action(receipt, 'summary')\n"
        "        record_action(receipt, 'summary', completed=True)\n"
        f"    print(Path({str(payload)!r}).read_text())\n"
        f"    print({RAW_MARKER!r}, file=sys.stderr)\n"
        f"    raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    binary.chmod(0o700)
    monkeypatch.setattr(preflight, "SUPPORTED_OCR_VERSIONS", ("1.14.2",))
    monkeypatch.setitem(native_capabilities._QUALIFIED_HANDOFFS, "1.14.2", frozenset({"analysis"}))
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("OCR_LLM_URL", "https://model.example.invalid/v1")
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-model-access-token")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("OCR_LLM_PROTOCOL", "openai")
    monkeypatch.setenv("OCR_ANALYSIS", "true")
    monkeypatch.setenv("OCR_ANALYSIS_MAX_TOKENS_BUDGET", "30")
    monkeypatch.setenv("OCR_RAW_LOGGING", "true")
    monkeypatch.setenv("OCR_DLP_ENABLED", "false")
    monkeypatch.setenv("OCR_REVIEW_DIAGRAM_MODE", "off")

    result, stderr, debug = (tmp_path / name for name in ("result.json", "stderr.log", "debug"))
    assert (
        cli.main(
            [
                "review",
                "--local",
                "--analysis",
                "--analysis-max-tokens-budget",
                "40",
                "--result",
                str(result),
                "--stderr",
                str(stderr),
                "--debug-dir",
                str(debug),
                "--",
                "--from",
                base,
                "--to",
                head,
            ]
        )
        == expected_exit
    )
    preview, review = (json.loads(line) for line in calls_path.read_text().splitlines())
    assert preview["args"][-1] == "--preview"
    assert review["args"] == [
        *preview["args"][:-1],
        "--analysis",
        "--analysis-max-tokens-budget",
        "40",
    ]
    assert not (preview["leaked_env"] or review["leaked_env"])
    assert preview["home"] == review["home"] and not Path(review["home"]).exists()
    serialized = result.read_text(encoding="utf-8")
    if exit_code == int(partial):
        admitted = json.loads(serialized)
        analysis = {
            "status": "completed",
            "declared_completion": "partial",
            "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
        }
        assert admitted["toolkit_analysis"] == {
            **analysis,
            **(
                {"markdown": REPORT_TEXT}
                if markdown == REPORT_TEXT
                else {"report_state": "filtered"}
            ),
        }
        assert admitted["status"] == ("partial" if partial else "skipped")
        assert not {"analysis", "analysis_raw", "analysis_meta", "session_id"} & admitted.keys()
    else:
        assert not serialized
    assert stat.S_IMODE(result.stat().st_mode) == 0o600
    assert stderr.read_bytes() == b""
    assert RAW_MARKER not in serialized and FORBIDDEN_REPORT not in serialized
    journal = json.loads((debug / "journal.json").read_text())
    assert journal["artifacts"]["raw-result.json"]["status"] == "not-run"
    assert journal["artifacts"]["raw-stderr.log"]["status"] == "not-run"
    assert not (debug / "safe-result.json").exists()
    output = capsys.readouterr()
    for text in (output.out, output.err, (debug / "summary.md").read_text()):
        assert RAW_MARKER not in text and REPORT_TEXT not in text and FORBIDDEN_REPORT not in text
