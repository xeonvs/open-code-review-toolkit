"""Qualify no-finding OCR output through the real launcher and atomic finalizer."""

import json

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.config_writer import write_ocr_config
from ocr_toolkit.evidence.actions import read_action_receipt
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.store import EvidenceStore
from ocr_toolkit.result_contract import parse_result_outcome
from ocr_toolkit.review_range import ReviewRange
from tests.test_ocr_compat import load_script
from tests.test_review_rejection import composition


@pytest.mark.parametrize("audience", [None, "agent"])
@pytest.mark.parametrize("mode", ["zero", "native", "evidence"])
def test_native_no_findings_telemetry_reaches_finalizer(
    tmp_path, monkeypatch, capsys, qualified_native_ocr, audience, mode
):
    binary, _version = qualified_native_ocr("OCR_FEDERATION_QUALIFY_BINARY")
    compat = load_script()
    environment = compat.execution._isolated_probe_environment(tmp_path / "home")
    baseline = "".join(f"value_{index} = 1\n" for index in range(20))
    changed = baseline.replace("= 1", "= 2")
    other_paths = ("second.py", "third.py", "fourth.py", "fifth.py")
    repo, base, _head = compat.execution._synthetic_repo(
        tmp_path,
        environment,
        baseline=baseline,
        changed=changed,
        context_files=dict.fromkeys(other_paths, baseline),
    )
    for path in other_paths:
        (repo / path).write_text(changed)
    compat.execution._run(["git", "add", *other_paths], cwd=repo, env=environment)
    compat.execution._run(
        ["git", "commit", "-m", "second synthetic change"], cwd=repo, env=environment
    )
    head = compat.execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=environment).strip()
    monkeypatch.chdir(repo)
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    if mode == "evidence":
        import sys

        EvidenceStore().write(artifacts.store)
        write_ocr_config(
            {
                "mcp_servers": {
                    "ocr_toolkit_evidence": {
                        "command": sys.executable,
                        "args": ["-I", "-m", "ocr_toolkit.evidence"],
                        "tools": ["ocr_toolkit_evidence"],
                    }
                }
            },
            tmp_path / "home" / ".opencodereview" / "config.json",
        )

    def conversation(request):
        messages = request["messages"]
        calls = [call for message in messages for call in message.get("tool_calls", [])]
        if mode != "zero" and not calls:
            name = "ocr_toolkit_evidence" if mode == "evidence" else "file_read"
            arguments = (
                {"action": "summary"}
                if mode == "evidence"
                else {
                    "file_path": compat.peer._StubHandler._review_path(messages),
                }
            )
        else:
            name, arguments = "task_done", {}
        return {"name": name, "arguments": json.dumps(arguments)}, f"synthetic-{len(calls)}"

    result = tmp_path / "result.json"
    stderr = tmp_path / "stderr.log"
    with compat.peer._stub_gateway(tool_script=conversation) as url:
        environment.update(
            OCR_LLM_URL=url,
            OCR_LLM_TOKEN="synthetic-token",
            OCR_LLM_MODEL="synthetic-model",
            OCR_LLM_PROTOCOL="openai",
            OCR_TELEMETRY_ENABLED="false",
        )
        arguments = ["--from", base, "--to", head, "--format", "json", "--concurrency", "2"]
        if audience is not None:
            arguments.extend(["--audience", audience])
        code = review_runner.run_review(
            result, stderr, arguments, ocr_binary=binary, child_environment=environment
        )
    assert code == 0, stderr.read_text()
    raw = json.loads(result.read_text())
    assert raw["comments"] == [] and parse_result_outcome(raw).kind == "clean"
    assert len(raw["manifest"]["coverage"]["selected"]) == 5
    assert len(raw["manifest"]["coverage"]["completed"]) == 5
    assert len(raw["groups"]) == 5
    telemetry = raw["tool_calls"]
    assert telemetry["failure"] == 0
    if mode == "zero":
        assert telemetry["total"] == 0 and telemetry["by_tool"] == {}
    else:
        tool = "ocr_toolkit_evidence" if mode == "evidence" else "file_read"
        assert set(telemetry["by_tool"]) == {tool}
        assert telemetry["by_tool"][tool] == telemetry["total"] > 0
    identity = review_runner.ReviewIdentity(head, base, None, "off", None, head, "local")
    actions = read_action_receipt(artifacts.action_receipt)
    arguments = (result, composition(), identity, None, actions)
    options = {"forbidden": (), "expected_range": ReviewRange(base, head), "ocr_exit_code": code}
    if mode == "evidence":
        usage, filtered, publication = review_runner._finalize_ocr_result(*arguments, **options)
        assert usage["ocr_toolkit_evidence"] == telemetry["total"]
        assert not filtered and publication["state"] == "passed"
        assert result.exists()
    else:
        with pytest.raises(review_runner.ReviewRejected) as caught:
            review_runner._finalize_ocr_result(*arguments, **options)
        assert caught.value.calls == 0 and not result.exists()
        output = capsys.readouterr().err
        assert "tool_calls=present ocr_exit_code=0" in output
        assert f"reported_total={telemetry['total']} reported_evidence_calls=0" in output
