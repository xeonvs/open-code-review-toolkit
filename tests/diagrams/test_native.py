"""Qualified native OCR crosses real MCP, cleanup, admission and private reporting."""

from __future__ import annotations

import http.server
import json
import os
import threading
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from ocr_toolkit import cli, provider_config, review_runner
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.preflight import validate_ocr_binary
from ocr_toolkit.review_range import ReviewRange, admit_native_range
from tests.diagrams.support import flow_submission, sequence_submission
from tests.diagrams.test_stdio import bind
from tests.test_evidence_repository import git


@pytest.mark.parametrize(
    "case",
    (
        "flow",
        "sequence",
        "absent",
        "not-applicable",
        "invalid",
        "parse-failure",
        "conflict",
        "call-failure",
        "startup-failure",
        "probe-failure",
        "off",
    ),
)
def test_qualified_native_diagram_handoff_preserves_review_and_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    binary = os.environ.get("OCR_GITLINK_QUALIFY_BINARY")
    if binary is None:
        pytest.skip("set OCR_GITLINK_QUALIFY_BINARY to checksum-verified OCR 1.13.3")
    assert validate_ocr_binary(executable=binary, announce=False) == "1.13.3"
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from ocr_compat import _StubHandler

    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    source = root / "example.py"
    source.write_text("def value():\n    return 1\n")
    git(root, "add", "example.py")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    source.write_text("def value():\n    return 2\n")
    git(root, "add", "example.py")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    review_range = ReviewRange(base, head)
    # Immutable readers and native range execution must preserve local work.
    source.write_text("local unstaged work\n")
    staged = root / "staged.txt"
    staged.write_text("local staged work\n")
    git(root, "add", "staged.txt")
    untracked = root / "untracked.txt"
    untracked.write_text("local untracked work\n")
    preserved = (root / ".git" / "HEAD", root / ".git" / "index", source, staged, untracked)
    before = tuple(path.read_bytes() for path in preserved)
    artifacts = repository_artifacts(root)
    prepare_artifact_directory(artifacts)
    if case == "startup-failure":
        artifacts.diagram.mkdir(mode=0o700)
    candidate = bind(
        sequence_submission() if case == "sequence" else flow_submission(), review_range
    )

    def repath(value):
        if isinstance(value, dict):
            if set(value) == {"path", "start_line", "end_line"}:
                value["path"] = "example.py"
            else:
                for child in value.values():
                    repath(child)
        elif isinstance(value, list):
            for child in value:
                repath(child)

    repath(candidate)
    submissions = (
        [] if case in ("absent", "off", "startup-failure", "probe-failure") else [candidate]
    )
    if case == "invalid":
        candidate["base_sha"] = "0" * 40
    if case == "not-applicable":
        submissions = [{"state": "not-applicable", "base_sha": base, "head_sha": head}]
    if case == "conflict":
        submissions.append({"state": "not-applicable", "base_sha": base, "head_sha": head})

    class DiagramPeer(_StubHandler):
        stage = 0
        output_visible = False
        output_responses: list[dict] = []

        def do_POST(self) -> None:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            request = json.loads(raw)
            names = {tool.get("function", {}).get("name") for tool in request.get("tools", [])}
            if "ocr_toolkit_evidence" not in names or "approve_all_comments" in names:
                self.rfile = BytesIO(raw)
                super().do_POST()
                return
            cls = type(self)
            cls.output_visible = DIAGRAM_TOOL_NAME in names
            cls.output_responses.extend(
                message
                for message in request["messages"]
                if message.get("role") == "tool"
                and message.get("tool_call_id", "").startswith("diagram-")
            )
            index = cls.stage
            cls.stage += 1
            if index == 0:
                name, arguments = "ocr_toolkit_evidence", {"action": "summary"}
            elif index <= len(submissions):
                if case == "call-failure":
                    artifacts.diagram.unlink()
                    artifacts.diagram.mkdir(mode=0o700)
                name, arguments = DIAGRAM_TOOL_NAME, submissions[index - 1]
            else:
                name, arguments = "task_done", {}
            payload = json.dumps(
                {
                    "id": "synthetic-diagram-proof",
                    "object": "chat.completion",
                    "model": "synthetic-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": f"diagram-{index}",
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": "{"
                                            if case == "parse-failure" and name == DIAGRAM_TOOL_NAME
                                            else json.dumps(arguments),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            self.close_connection = True

    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ocr").symlink_to(binary)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-token")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("OCR_LLM_PROTOCOL", "openai")
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "api-key")
    monkeypatch.setenv("OCR_TELEMETRY_ENABLED", "false")
    monkeypatch.setenv("OCR_REVIEW_CONTEXT_MODE", "off")
    monkeypatch.setenv("OCR_REVIEW_PROGRESS", "false")
    monkeypatch.setenv("OCR_REVIEW_DIAGRAM_MODE", "off" if case == "off" else "local")
    resolutions = 0
    resolve_binary = review_runner._resolve_ocr_binary

    def transient_resolution():
        nonlocal resolutions
        resolutions += 1
        if resolutions == 1:
            raise review_runner.ReviewRunnerError("synthetic optional executable lookup failure")
        return resolve_binary()

    if case == "probe-failure":
        monkeypatch.setattr(review_runner, "_resolve_ocr_binary", transient_resolution)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DiagramPeer)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/v1"
    parse_url = provider_config._parse_https_url
    monkeypatch.setattr(
        provider_config,
        "_parse_https_url",
        lambda value, name: urlsplit(value) if value == url else parse_url(value, name),
    )
    monkeypatch.setenv("OCR_LLM_URL", url)
    monkeypatch.chdir(root)
    result, stderr, report = (
        tmp_path / name for name in ("review.json", "review.stderr", "review.md")
    )
    try:
        code = cli.main(
            [
                "review",
                "--local",
                "--result",
                str(result),
                "--stderr",
                str(stderr),
                "--report",
                str(report),
                "--",
                "--from",
                base,
                "--to",
                head,
                "--concurrency",
                "1",
            ]
        )
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    assert code == 0, stderr.read_text()[-3000:]
    raw = json.loads(result.read_text())
    assert admit_native_range(raw, review_range) == review_range
    assert raw["comments"] == []
    assert raw["manifest"]["terminal_state"] == "complete"
    assert raw["tool_calls"]["failure"] == (1 if case == "parse-failure" else 0)
    markdown = report.read_text()
    assert base in markdown and head in markdown
    expected = (
        "generated"
        if case in ("flow", "sequence")
        else "disabled"
        if case == "off"
        else "not-generated"
        if case == "absent"
        else "not-applicable"
        if case == "not-applicable"
        else "unsupported"
        if case == "probe-failure"
        else "omitted-invalid"
    )
    assert f"Change diagram: `{expected}`" in markdown
    assert ("```mermaid" in markdown) == (expected == "generated")
    assert DiagramPeer.output_visible == (case not in ("off", "startup-failure", "probe-failure"))
    if case == "probe-failure":
        assert resolutions >= 2
    if submissions:
        assert DiagramPeer.output_responses
    assert tuple(path.read_bytes() for path in preserved) == before
    assert not artifacts.store.exists() and not artifacts.bootstrap.exists()
    assert not artifacts.diagram_lock.exists()
    assert (
        artifacts.diagram.is_dir()
        if case in ("startup-failure", "call-failure")
        else not artifacts.diagram.exists()
    )
