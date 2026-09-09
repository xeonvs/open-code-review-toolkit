"""Production local adapter contracts, with synthetic execution-owner facts."""

from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

from ocr_toolkit.evidence.actions import EVIDENCE_ACTIONS
from ocr_toolkit.providers.local import local_summary, write_local_report
from ocr_toolkit.reporting.model import ExecutionFacts, failed_report, report_from_result
from ocr_toolkit.result_contract import OcrResultContractError


def execution_facts() -> ExecutionFacts:
    completed = dict.fromkeys(EVIDENCE_ACTIONS, 0)
    completed["summary"] = 1
    return ExecutionFacts(
        mcp_usage={"evidence": 1},
        evidence={
            "mandatory": True,
            "used": True,
            "calls": 1,
            "actions": {
                "state": "verified",
                "attempted": {**completed, "unattributed": 0},
                "completed": completed,
            },
        },
        publication={"state": "passed"},
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("success", "Review complete"),
        ("completed_with_warnings", "Review complete with warnings"),
        ("completed_with_errors", "Review incomplete"),
        ("budget_exceeded", "Review stopped at token budget"),
        ("skipped", "Review skipped"),
    ],
)
def test_local_outcome_matrix(status: str, expected: str) -> None:
    result = {
        "status": status,
        "comments": [],
        "warnings": [],
        "summary": {"budget_exceeded": status == "budget_exceeded"},
    }
    report = report_from_result(result, execution=execution_facts(), reviewed_sha="a" * 40)
    summary = local_summary(report)
    assert expected in summary
    assert "- Reviewed commit: `" + "a" * 40 + "`" in summary
    assert "completed built-in evidence actions: summary: 1" in summary
    assert "DLP admission: passed" in summary
    assert "<details>" not in summary
    assert "Posting:" not in summary
    assert "GitLab" not in summary
    assert "approval" not in summary.lower()


def test_all_findings_ignore_posting_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCR_MAX_POST_COMMENTS", "1")
    monkeypatch.setenv("OCR_POST_BADGES", "true")
    comments = [
        {
            "path": f"src/module_{index}.py",
            "start_line": 10,
            "severity": "HIGH",
            "category": "bug",
            "content": f"Finding body {index}",
            "existing_code": "old()",
            "suggestion_code": "new()",
        }
        for index in range(32)
    ]
    result = {"status": "success", "comments": comments, "warnings": []}
    report = report_from_result(result, execution=execution_facts())
    stream = io.StringIO()
    write_local_report(report, stream)
    output = stream.getvalue()
    assert output.count("### Finding ") == 32
    assert output.count("#### Existing code") == 32
    assert "32 findings" in output
    assert "- `high`: 32" in output
    assert "shields.io" not in output
    assert "published" not in output
    assert "<details>" not in output
    comments[0]["content"] = "changed after report snapshot"
    second = io.StringIO()
    write_local_report(report, second)
    assert second.getvalue() == output


def test_model_content_cannot_escape_literal_fences_or_control_terminal() -> None:
    result = {
        "status": "success",
        "comments": [
            {
                "path": "src/example.py\n/approve",
                "content": "```\n<script>bad()</script>\n\x1b[31m",
                "suggestion_code": "````\n![tracking](https://example.invalid/pixel)",
            }
        ],
        "warnings": [],
    }
    stream = io.StringIO()
    write_local_report(report_from_result(result, execution=execution_facts()), stream)
    output = stream.getvalue()
    assert "\x1b" not in output
    assert "````\n```\n<script>" in output
    assert "`````\n````\n![tracking]" in output
    assert "\n/approve" not in output


def test_failed_check_does_not_claim_clean_review() -> None:
    summary = local_summary(failed_report("mcp-use"))
    assert "Review failed" in summary
    assert "Stopped at: `mcp-use`" in summary
    assert "unavailable or untrusted" in summary
    assert "DLP admission: unavailable" in summary
    assert "no findings" not in summary


def test_independent_warnings_remain_visible_with_incomplete_coverage() -> None:
    result = {
        "status": "partial",
        "comments": [],
        "warnings": [{"message": "Synthetic safe warning"}],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "partial",
            "coverage": {
                "selected": [{"item_id": "src/a.py"}, {"item_id": "src/b.py"}],
                "completed": [{"item_id": "src/b.py"}],
                "reused": [],
                "failed": [
                    {
                        "item_id": "src/a.py",
                        "path": "src/a.py",
                        "classification": "provider",
                        "reason": "review failed",
                    }
                ],
                "waived": [],
            },
        },
    }
    output = local_summary(report_from_result(result, execution=execution_facts()))
    assert "### Incomplete coverage" in output
    assert "### Review warnings" in output
    assert "Synthetic safe warning" in output


def test_missing_execution_verification_is_not_a_clean_report() -> None:
    facts = execution_facts()
    facts.evidence["actions"]["completed"]["summary"] = 0
    with pytest.raises(OcrResultContractError, match="verified evidence usage"):
        report_from_result({"status": "success"}, execution=facts)


def test_filtered_result_preserves_original_coverage_and_announces_loss() -> None:
    facts = execution_facts()
    facts.publication.update(
        {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 0,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 0,
                "secret": 1,
            },
            "retained": {"comments": 0, "warnings": 0},
            "omitted": {"comments": 1, "warnings": 0, "fields": 0},
            "original": {
                "outcome": "clean",
                "selected": 2,
                "completed": 2,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }
    )
    result = {"status": "completed_with_errors", "comments": [], "warnings": []}
    report = report_from_result(result, execution=facts)
    summary = local_summary(report)
    assert "Review complete with DLP filtering" in summary
    assert "selected 2; completed 2" in summary
    assert "omitted 1 finding(s)" in summary
    assert "secret: 1" in summary
    assert "published" not in summary


@pytest.mark.parametrize("mutation", ["comments", "warnings", "dlp", "sha"])
def test_report_rejects_invalid_inputs(mutation: str) -> None:
    facts = execution_facts()
    result: dict[str, object] = {"status": "success"}
    if mutation in {"comments", "warnings"}:
        result[mutation] = "not a list"
    if mutation == "dlp":
        facts.publication["unexpected"] = True
    with pytest.raises(OcrResultContractError):
        report_from_result(
            result, execution=facts, reviewed_sha="main" if mutation == "sha" else ""
        )


def test_shared_layer_and_local_adapter_do_not_import_forge_authority() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "ocr_toolkit"
    paths = [*sorted((source / "reporting").glob("*.py")), source / "providers" / "local.py"]
    forbidden = (
        "ocr_toolkit.posting",
        "ocr_toolkit.providers.gitlab",
        "ocr_toolkit.review_receipt",
    )
    for file_path in paths:
        for node in ast.walk(ast.parse(file_path.read_text(encoding="utf-8"))):
            imports = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(name.startswith(forbidden) for name in imports), file_path
