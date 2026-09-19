"""Opt-in qualification of the real verified OCR binary against the production gateway."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.config_writer import write_ocr_config
from ocr_toolkit.federation import parse_registry, start_gateway
from tests.federation.test_gateway import registry_value
from tests.test_ocr_compat import load_script


def test_checksum_verified_ocr_calls_the_real_federation_relay(tmp_path: Path) -> None:
    binary_name = os.environ.get("OCR_FEDERATION_QUALIFY_BINARY")
    digest = os.environ.get("OCR_FEDERATION_QUALIFY_SHA256")
    if not binary_name or not digest:
        pytest.skip("external OCR binary qualification requires its verified path and SHA-256")
    binary = Path(binary_name)
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    compat = load_script()
    env = compat._isolated_probe_environment(tmp_path / "isolated-home")
    repo, base, head = compat._synthetic_repo(tmp_path, env)
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )
    model_calls: list[str] = []

    class ModelPeer(compat._StubHandler):
        """Reuse OCR's canonical grouping/planning stub and select one federation tool."""

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(body)
            tools = {tool["function"]["name"] for tool in request.get("tools", [])}
            if "synthetic__echo" not in tools or "approve_all_comments" in tools:
                self.rfile = io.BytesIO(body)
                super().do_POST()
                return
            prior = any(
                call.get("function", {}).get("name") == "synthetic__echo"
                for message in request["messages"]
                for call in message.get("tool_calls", [])
            )
            name = "task_done" if prior else "synthetic__echo"
            model_calls.append(name)
            arguments = {} if prior else {"text": "controlled OCR external response"}
            payload = json.dumps(
                {
                    "id": "synthetic-completion",
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
                                        "id": "synthetic-call-" + name,
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": json.dumps(arguments),
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
            self.close_connection = True

        def log_message(self, *_args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelPeer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env.update(
        OCR_LLM_URL=f"http://127.0.0.1:{server.server_port}/v1",
        OCR_LLM_TOKEN="synthetic-token",
        OCR_LLM_MODEL="synthetic-model",
        OCR_LLM_PROTOCOL="openai",
        OCR_TELEMETRY_ENABLED="false",
    )
    write_ocr_config(
        {"mcp_servers": {"federation": gateway.ocr_server}},
        Path(env["HOME"]) / ".opencodereview" / "config.json",
    )
    try:
        completed = subprocess.run(
            [
                str(binary),
                "review",
                "--from",
                base,
                "--to",
                head,
                "--format",
                "json",
                "--audience",
                "agent",
                "--concurrency",
                "1",
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert completed.returncode == 0, completed.stderr
        output = json.loads(completed.stdout)
        assert isinstance(output, dict)
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()
        receipt = gateway.close()
    assert "synthetic__echo" in model_calls
    assert receipt["tools"]["synthetic__echo"]["completed"] == model_calls.count("synthetic__echo")
    assert "controlled OCR external response" in gateway.forbidden_publication
