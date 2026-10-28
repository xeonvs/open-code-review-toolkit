"""Diagram faults cannot break mandatory evidence or finding/report delivery."""

from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path
from subprocess import TimeoutExpired

import pytest

from ocr_toolkit import mcp_config, review_runner
from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.diagrams import lifecycle, mcp
from ocr_toolkit.diagrams.lifecycle import DiagramExecution
from ocr_toolkit.evidence.actions import read_action_receipt
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.mcp import handle_request, serve
from ocr_toolkit.evidence.repository import GitRepositoryReader
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.posting import formatting
from ocr_toolkit.providers.local import local_summary
from ocr_toolkit.reporting import diagram as rendering
from ocr_toolkit.reporting.model import report_from_result
from ocr_toolkit.review_range import ReviewRange
from tests.diagrams.support import REVIEW_RANGE, flow_submission
from tests.diagrams.test_admission_reporting import admitted
from tests.reporting.test_local import execution_facts
from tests.test_evidence_mcp import _store
from tests.test_evidence_repository import git
from tests.test_review_range import native_result
from tests.test_review_runner import BUILTIN_EVIDENCE_TOOLS, LOCAL_IDENTITY, SUMMARY_ACTION_COUNTS


def fail(*_args, **_kwargs):
    raise RuntimeError("synthetic optional failure; never publish this diagnostic")


@pytest.mark.parametrize("failure", ("io", "missing", "unicode", "timeout"))
def test_transient_diagram_source_failure_cannot_poison_finding_code_proof(
    tmp_path, monkeypatch, failure
):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    source = root / "app.py"
    source.write_text("List<Entry> value;\none\ntwo\n")
    git(root, "add", "app.py")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    source.write_text("List<Entry> value;\nchanged\ntwo\n")
    git(root, "add", "app.py")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    review_range = ReviewRange(base, head)
    artifacts = repository_artifacts(root)
    prepare_artifact_directory(artifacts)
    execution = DiagramExecution.prepare(
        "local",
        local=True,
        native_version="1.13.3",
        review_range=review_range,
        path=artifacts.diagram,
    )
    candidate = flow_submission()
    candidate.update(base_sha=base, head_sha=head)
    execution.collector.submit(candidate)
    execution.capture()
    comment = {
        "path": "app.py",
        "line": 1,
        "content": "Update the declaration.",
        "existing_code": "List<Entry> value;",
        "suggestion_code": "List<Node> value;",
    }
    payload = native_result(review_range)
    payload.update(
        comments=[comment],
        tool_calls={"total": 2, "by_tool": {"ocr_toolkit_evidence": 1, mcp.DIAGRAM_TOOL_NAME: 1}},
    )
    result = tmp_path / "review.json"
    result.write_text(json.dumps(payload))
    composition = MCPComposition(
        {},
        (
            MCPCapability(
                "ocr_toolkit_evidence", (*BUILTIN_EVIDENCE_TOOLS, mcp.DIAGRAM_TOOL_NAME), True
            ),
        ),
        (),
        (),
    )
    read_blob = GitRepositoryReader.read_blob
    calls = []

    def transient(reader, sha, path):
        calls.append((sha, path))
        if len(calls) == 1:
            if failure == "missing":
                return None
            if failure == "unicode":
                return b"\xff"
            if failure == "timeout":
                raise TimeoutExpired("git", 1)
            raise OSError("synthetic optional source read failure")
        return read_blob(reader, sha, path)

    monkeypatch.chdir(root)
    monkeypatch.setattr(GitRepositoryReader, "read_blob", transient)
    reports = []
    _, filtered, publication = review_runner._finalize_ocr_result(
        result,
        composition,
        replace(LOCAL_IDENTITY, source_sha=head),
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        expected_range=review_range,
        diagram_execution=execution,
        report_consumer=reports.append,
    )
    assert not filtered and publication["state"] == "passed"
    assert reports[0].comments == (comment,) and reports[0].diagram.state == "omitted-invalid"
    assert reports[0].outcome.status == "complete"
    assert calls == [(head, "app.py"), (head, "app.py")]


@pytest.fixture
def execution(tmp_path: Path) -> DiagramExecution:
    tmp_path.chmod(0o700)
    return DiagramExecution.prepare(
        "local",
        local=True,
        native_version="1.13.3",
        review_range=REVIEW_RANGE,
        path=tmp_path / "diagram.json",
    )


def finish(execution: DiagramExecution):
    return execution.finish(
        review_range=REVIEW_RANGE,
        calls=1,
        failed_calls=0,
        read_source=lambda _path: "one\ntwo\nthree\n",
        forbidden_matcher=ForbiddenMatcher.compile(()),
        dlp_enabled=True,
    )


def test_collector_runtime_exception_is_a_normal_optional_mcp_response(
    execution: DiagramExecution, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    assert execution.collector is not None
    monkeypatch.setattr(type(execution.collector), "submit", fail)
    response = handle_request(
        _store(),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": mcp.DIAGRAM_TOOL_NAME, "arguments": flow_submission()},
        },
        diagram_collector=execution.collector,
    )
    assert response is not None and "error" not in response
    result = response["result"]
    assert result.get("isError") is not True
    assert json.loads(result["content"][0]["text"])["state"] == "omitted-invalid"
    receipt = tmp_path / "actions.json"
    summary = handle_request(
        _store(),
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "ocr_toolkit_evidence", "arguments": {"action": "summary"}},
        },
        diagram_collector=execution.collector,
        action_receipt_path=receipt,
    )
    assert summary is not None and summary["result"].get("isError") is not True
    assert read_action_receipt(receipt)["completed"]["summary"] == 1
    assert "synthetic optional failure" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "bad_definition",
    (None, {"name": "wrong"}, {"name": mcp.DIAGRAM_TOOL_NAME, "inputSchema": {"x": object()}}),
)
def test_bad_optional_schema_never_corrupts_evidence_tool_registry(
    execution: DiagramExecution, monkeypatch: pytest.MonkeyPatch, bad_definition: object
) -> None:
    monkeypatch.setattr(mcp, "diagram_tool_definition", lambda: bad_definition)
    response = handle_request(
        _store(),
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        diagram_collector=execution.collector,
    )
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {
        "ocr_toolkit_evidence",
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        mcp.DIAGRAM_TOOL_NAME,
    } <= names


def test_schema_exception_uses_a_serializable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp, "diagram_tool_definition", fail)
    fallback = mcp.optional_diagram_tool_definition()
    assert fallback["name"] == mcp.DIAGRAM_TOOL_NAME
    json.dumps(fallback)


@pytest.mark.parametrize("stage", ("initialize", "read", "admit", "serialize"))
def test_lifecycle_faults_leave_an_explicit_omission(
    execution: DiagramExecution, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stage: str
) -> None:
    assert execution.collector is not None
    if stage == "initialize":
        monkeypatch.setattr(type(execution.collector), "initialize", fail)
        prepared = DiagramExecution.prepare(
            "local",
            local=True,
            native_version="1.13.3",
            review_range=REVIEW_RANGE,
            path=tmp_path / "new.json",
        )
        assert prepared.result.state == "omitted-invalid"
        return
    execution.collector.submit(flow_submission())
    if stage == "read":
        monkeypatch.setattr(type(execution.collector), "read", fail)
    execution.capture()
    if stage == "admit":
        monkeypatch.setattr(lifecycle, "admit_diagram", fail)
    if stage == "serialize":
        monkeypatch.setattr(lifecycle, "diagram_payload", fail)
    result = finish(execution)
    assert result.state == "omitted-invalid" and result.submission is None


def test_output_registration_fault_keeps_the_original_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {})
    base = mcp_config.compose_mcp_servers([])
    monkeypatch.setattr(mcp_config, "with_diagram_output", fail)
    actual = mcp_config.compose_mcp_servers([], diagram_run_id="c" * 32)
    assert actual == base and mcp.DIAGRAM_TOOL_NAME not in actual.capabilities[0].tools


def test_bad_diagram_binding_keeps_the_real_evidence_server_running(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    path = tmp_path / "evidence.json"
    _store().write(path)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": mcp.DIAGRAM_TOOL_NAME, "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "ocr_toolkit_evidence", "arguments": {"action": "summary"}},
        },
    ]
    output = io.StringIO()
    code = serve(
        path,
        io.StringIO("".join(json.dumps(request) + "\n" for request in requests)),
        output,
        diagram_path=tmp_path / "diagram.json",
        diagram_run_id="invalid",
    )
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert code == 0 and len(replies) == 2
    assert all(
        "error" not in reply and reply["result"].get("isError") is not True for reply in replies
    )
    assert "records" in json.loads(replies[1]["result"]["content"][0]["text"])


def test_renderer_exception_preserves_every_finding_and_review_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = admitted(flow_submission())
    report = report_from_result(
        {
            "status": "success",
            "comments": [{"path": "app.py", "line": 1, "content": "Keep this finding."}],
            "warnings": [],
        },
        execution=replace(execution_facts(), review_range=REVIEW_RANGE, diagram=result),
        reviewed_sha=REVIEW_RANGE.head,
    )
    monkeypatch.setattr(rendering, "diagram_mermaid", fail)
    rendered = local_summary(report)
    assert "1 finding" in rendered and "omitted-invalid" in rendered
    assert "```mermaid" not in rendered and report.outcome.kind == "clean"
    assert report.comments[0]["content"] == "Keep this finding."


@pytest.mark.parametrize("failure", ("renderer", "budget"))
def test_gitlab_optional_rendering_preserves_the_main_summary(monkeypatch, failure) -> None:
    if failure == "renderer":
        monkeypatch.setattr(rendering, "diagram_mermaid", fail)
    else:
        monkeypatch.setattr(formatting, "FALLBACK_NOTE_CHUNK_BUDGET", 1)
    summary = formatting.summarize_result(
        total=1,
        inline_count=1,
        fallback_count=0,
        warning_count=0,
        diagram=admitted(flow_submission()),
        emoji=False,
    )
    assert "1 finding" in summary and "omitted-invalid" in summary
    assert "```mermaid" not in summary


@pytest.mark.parametrize(
    "local,mode", ((True, ""), (False, ""), (True, "unknown"), (False, "local"))
)
def test_invalid_configuration_stops_before_any_private_or_repository_acquisition(
    tmp_path, monkeypatch, local, mode
) -> None:
    monkeypatch.setenv("OCR_REVIEW_DIAGRAM_MODE", mode)
    monkeypatch.setattr(
        review_runner, "repository_artifacts", lambda: pytest.fail("private acquisition")
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="OCR_REVIEW_DIAGRAM_MODE"):
        review_runner.run_evidence_review(
            tmp_path / "result.json", tmp_path / "stderr", ["--commit", "HEAD"], local=local
        )
    assert not tuple(tmp_path.iterdir())


def test_optional_cleanup_fault_does_not_hide_mandatory_cleanup(
    tmp_path, monkeypatch, capsys
) -> None:
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    artifacts.store.write_text("owned mandatory input")
    artifacts.diagram.mkdir(mode=0o700)
    review_runner._remove_ephemeral_review_artifacts(artifacts)
    assert not artifacts.store.exists() and artifacts.diagram.is_dir()
    assert "review continues without it" in capsys.readouterr().err


def test_warning_sink_failure_cannot_replace_an_optional_failure(monkeypatch) -> None:
    monkeypatch.setattr(lifecycle, "print", fail, raising=False)
    lifecycle.diagram_warning()
