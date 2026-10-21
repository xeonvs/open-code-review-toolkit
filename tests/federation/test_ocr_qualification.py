"""Opt-in qualification of the real verified OCR binary against the production gateway."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.config_writer import write_ocr_config
from ocr_toolkit.evidence.actions import read_action_receipt
from ocr_toolkit.evidence.artifacts import (
    prepare_artifact_directory,
    repository_artifacts,
    write_private_text,
)
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.review_context import (
    merge_request_context_record,
    normalize_merge_request_context,
)
from ocr_toolkit.evidence.store import EvidenceStore
from ocr_toolkit.federation import parse_registry, start_gateway
from ocr_toolkit.mcp_config import MCPCapability
from tests.test_ocr_compat import load_script


def test_checksum_verified_ocr_reads_mr_intent_before_federated_tracker(tmp_path: Path) -> None:
    """Prove real OCR routing with a deterministic peer, not natural model selection."""
    binary_name = os.environ.get("OCR_FEDERATION_QUALIFY_BINARY")
    digest = os.environ.get("OCR_FEDERATION_QUALIFY_SHA256")
    if not binary_name or not digest:
        pytest.skip("external OCR binary qualification requires its verified path and SHA-256")
    binary = Path(binary_name)
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=10)
    assert version.returncode == 0 and "1.13.2" in version.stdout
    compat = load_script()
    env = compat._isolated_probe_environment(tmp_path / "isolated-home")
    repo, base, head = compat._synthetic_repo(tmp_path, env)
    tracker_key = "SYNTH-" + uuid.uuid4().hex[:12]
    tracker_calls = tmp_path / "tracker-calls.json"
    tracker_peer = tmp_path / "tracker_peer.py"
    tracker_peer.write_text(
        """import json
import sys
from pathlib import Path
from mcp.server import MCPServer
server = MCPServer("controlled-tracker")
@server.tool()
def read_issue(key: str) -> str:
    \"\"\"Read one operator-authorized synthetic issue by its exact key.\"\"\"
    if key != sys.argv[1]:
        raise ValueError("unauthorized issue")
    Path(sys.argv[2]).write_text(json.dumps({"key": key}), encoding="utf-8")
    return json.dumps({"key": key, "summary": "Controlled rollout requirement"})
server.run()
""",
        encoding="utf-8",
    )
    registry = {
        "version": 2,
        "servers": {
            "tracker": {
                "transport": {
                    "type": "stdio",
                    "command": sys.executable,
                    "args": ["-I", str(tracker_peer), tracker_key, str(tracker_calls)],
                },
                "tools": {"read_issue": {"assurance": "review_read"}},
            }
        },
    }
    store = EvidenceStore()
    record = merge_request_context_record(
        normalize_merge_request_context(
            provider="gitlab",
            project_id="7",
            merge_request_iid="9",
            source_sha=head,
            title="Controlled rollout",
            description=json.dumps({"tracker_key": tracker_key}),
            labels=[],
            source_branch=None,
        )
    )
    assert store.add(record)
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    store.write(artifacts.store)
    write_private_text(
        artifacts.bootstrap,
        render_bootstrap(
            store,
            capabilities=(MCPCapability("tracker", ("tracker__read_issue",)),),
        ),
    )
    # The real evidence child must keep isolated import semantics in OCR's cwd.
    (repo / "ocr_toolkit.py").write_text("raise RuntimeError('repository shadow')\n")
    gateway = start_gateway(parse_registry(json.dumps(registry)), environment={}, run_id="a" * 32)
    model_calls: list[tuple[str, dict[str, str]]] = []
    peer_errors: list[str] = []

    def decoded_objects(value: object, depth: int = 0) -> list[dict[str, Any]]:
        """Unwrap bounded JSON MCP text envelopes from actual tool responses."""
        if depth > 5:
            return []
        if isinstance(value, str):
            try:
                return decoded_objects(json.loads(value), depth + 1)
            except json.JSONDecodeError:
                return []
        if isinstance(value, list):
            return [item for part in value for item in decoded_objects(part, depth + 1)]
        if isinstance(value, dict):
            return [value] + [
                item
                for name in ("content", "text")
                if name in value
                for item in decoded_objects(value[name], depth + 1)
            ]
        return []

    class ModelPeer(compat._StubHandler):
        """Read real internal MCP output before deriving an authorized tracker call."""

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(body)
            tools = {tool["function"]["name"] for tool in request.get("tools", [])}
            if "tracker__read_issue" not in tools or "approve_all_comments" in tools:
                self.rfile = io.BytesIO(body)
                super().do_POST()
                return
            calls = {
                call["id"]: call["function"]
                for message in request["messages"]
                for call in message.get("tool_calls", [])
            }
            returned = [
                (calls[message["tool_call_id"]], decoded_objects(message.get("content")))
                for message in request["messages"]
                if message.get("role") == "tool" and message.get("tool_call_id") in calls
            ]
            try:
                name = "ocr_toolkit_evidence"
                arguments = {"action": "summary"}
                if any(call["name"] == "tracker__read_issue" for call, _ in returned):
                    name, arguments = "task_done", {}
                elif any(
                    call["name"] == name and json.loads(call["arguments"]).get("action") == "get"
                    for call, _ in returned
                ):
                    fetched = [
                        item["record"]
                        for call, items in returned
                        if call["name"] == name
                        and json.loads(call["arguments"]).get("action") == "get"
                        for item in items
                        if "record" in item
                    ]
                    assert fetched and fetched[0]["kind"] == "review.merge_request_context"
                    description = fetched[0]["value"]["fields"]["description"]
                    assert description["status"] == "admitted"
                    # Only the returned private MR field supplies this argument.
                    key = json.loads(description["value"])["tracker_key"]
                    name, arguments = "tracker__read_issue", {"key": key}
                elif any(call["name"] == name for call, _ in returned):
                    contents = "\n".join(type(self)._message_contents(request["messages"]))
                    pointer = re.search(r'action=get, id="(ev1_[a-f0-9]{64})"', contents)
                    assert pointer is not None
                    arguments = {"action": "get", "id": pointer.group(1)}
                model_calls.append((name, arguments))
            except (AssertionError, KeyError, TypeError, ValueError) as exc:
                peer_errors.append(type(exc).__name__)
                self.send_error(400, "controlled model sequence failed")
                return
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
                                        "id": f"synthetic-call-{len(model_calls)}",
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
        {
            "mcp_servers": {
                "federation": gateway.ocr_server,
                "ocr_toolkit_evidence": {
                    "command": sys.executable,
                    "args": ["-I", "-m", "ocr_toolkit.evidence"],
                    "tools": ["ocr_toolkit_evidence"],
                },
            }
        },
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
                "--background-file",
                str(artifacts.bootstrap),
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert completed.returncode == 0, (completed.stderr, peer_errors)
        output = json.loads(completed.stdout)
        assert isinstance(output, dict)
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()
        receipt = gateway.close()
    assert not peer_errors
    assert model_calls[:3] == [
        ("ocr_toolkit_evidence", {"action": "summary"}),
        ("ocr_toolkit_evidence", {"action": "get", "id": record.id}),
        ("tracker__read_issue", {"key": tracker_key}),
    ]
    assert json.loads(tracker_calls.read_text()) == {"key": tracker_key}
    assert receipt["tools"]["tracker__read_issue"]["completed"] >= 1
    actions = read_action_receipt(artifacts.action_receipt)
    assert actions is not None and actions["completed"]["summary"] >= 1
    assert actions["completed"]["get"] >= 1 and actions["attempted"]["list"] == 0
    assert tracker_key in " ".join(gateway.forbidden_publication)
