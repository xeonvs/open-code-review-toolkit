"""Observe the production MCP definition after each actual native API adapter."""

from __future__ import annotations

import http.server
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from ocr_toolkit import cli, provider_config
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME, diagram_tool_definition
from ocr_toolkit.evidence.artifacts import repository_artifacts
from tests.test_evidence_repository import synthetic_repository


@pytest.mark.parametrize("protocol", ("openai", "openai-responses", "anthropic"))
def test_native_provider_wire_preserves_advertised_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qualified_native_ocr, protocol: str
) -> None:
    binary, _version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    root, base, head = synthetic_repository(tmp_path)
    # Native OCR selects the source file; the test repository's default .txt is not selected.
    (root / "changed.txt").rename(root / "changed.py")
    from tests.test_evidence_repository import git

    git(root, "add", "-A")
    git(root, "commit", "-qm", "select source")
    head = git(root, "rev-parse", "HEAD")
    captured: list[dict] = []

    class Peer(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2 * 1024 * 1024:
                self.send_error(413)
                return
            request = json.loads(self.rfile.read(length))
            for tool in request.get("tools", []):
                definition = tool.get("function", tool)
                if definition.get("name") == DIAGRAM_TOOL_NAME:
                    assert len(captured) < 16
                    captured.append(definition)
            if captured:
                # Serialization proof only. Successful MCP/admission has a separate peer.
                self.send_error(400, "Synthetic schema capture complete")
                return
            content = "Summary: Review the changed code.\n\nIssues\n(none)"
            if protocol == "anthropic":
                response = {
                    "id": "synthetic",
                    "type": "message",
                    "role": "assistant",
                    "model": "synthetic-model",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": content}],
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            elif protocol == "openai-responses":
                response = {
                    "id": "synthetic",
                    "object": "response",
                    "status": "completed",
                    "output": [
                        {
                            "id": "synthetic-message",
                            "type": "message",
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": content}],
                        }
                    ],
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                }
            else:
                response = {
                    "id": "synthetic",
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            payload = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ocr").symlink_to(binary)
    for key, value in {
        "HOME": str(home),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "OCR_LLM_TOKEN": "synthetic-token",
        "OCR_LLM_MODEL": "synthetic-model",
        "OCR_LLM_PROTOCOL": protocol,
        "OCR_LLM_AUTH_MODE": "api-key",
        "OCR_TELEMETRY_ENABLED": "false",
        "OCR_REVIEW_CONTEXT_MODE": "off",
        "OCR_REVIEW_PROGRESS": "false",
        "OCR_REVIEW_DIAGRAM_MODE": "local",
    }.items():
        monkeypatch.setenv(key, value)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Peer)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}" + ("" if protocol == "anthropic" else "/v1")
    parse_url = provider_config._parse_https_url
    monkeypatch.setattr(
        provider_config,
        "_parse_https_url",
        lambda value, name: urlsplit(value) if value == url else parse_url(value, name),
    )
    monkeypatch.setenv("OCR_LLM_URL", url)
    monkeypatch.chdir(root)
    try:
        cli.main(
            [
                "review",
                "--local",
                "--result",
                str(tmp_path / "result.json"),
                "--stderr",
                str(tmp_path / "stderr"),
                "--report",
                str(tmp_path / "report.md"),
                "--",
                "--from",
                base,
                "--to",
                head,
                "--concurrency",
                "1",
                "--effort",
                "low",
            ]
        )
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    expected = diagram_tool_definition()["inputSchema"]
    assert captured, (tmp_path / "stderr").read_text()[-2000:]
    assert all(
        item.get("input_schema" if protocol == "anthropic" else "parameters") == expected
        for item in captured
    )
    artifacts = repository_artifacts(root)
    assert not artifacts.diagram.exists() and not artifacts.diagram_lock.exists()
    assert not artifacts.store.exists() and not artifacts.bootstrap.exists()
