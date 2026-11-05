"""Opt-in native diff recovery, ambiguous Git paths and new-side line anchors."""

from __future__ import annotations

import http.server
import json
import threading
from io import BytesIO

import pytest

from ocr_toolkit.review_range import ReviewRange, admit_native_range
from tests.test_evidence_repository import git
from tests.test_ocr_compat import load_script


@pytest.mark.parametrize("case", ["missing-mixed", "modify", "rename", "copy"])
def test_native_path_recovery_and_blank_line_anchor(tmp_path, qualified_native_ocr, case):
    binary, version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    compat = load_script()
    if case != "missing-mixed" and compat.core._version(version) < (1, 13, 5):
        pytest.skip("complex-header and blank-line changes are qualified from the new epoch")
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    old_path = (
        "example.go"
        if case == "missing-mixed"
        else "x.go"
        if case in {"rename", "copy"}
        else "x b/y.go"
    )
    new_path = "y.go b/x.go b/y.go" if case in {"rename", "copy"} else old_path
    padding = "".join(f"// Unchanged synthetic context {index}\n" for index in range(8))
    before = padding + "func a() {\n\tx := 1\n\n\treturn x\n}\n"
    old = root / old_path
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text(before, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    new = root / new_path
    new.parent.mkdir(parents=True, exist_ok=True)
    if case == "rename":
        old.rename(new)
    new.write_text(before + "\nfunc b() {\n\tx := 1\n\n\treturn x\n}\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    before_state = git(root, "status", "--porcelain=v1")
    if case in {"rename", "copy"}:
        patch = git(root, "diff", "-M", "-C", "--find-copies-harder", base, head)
        assert f"{case} from {old_path}" in patch
        assert f"{case} to {new_path}" in patch
    snippet = "\tx := 1\n\n\treturn x\n}"
    if case == "copy":
        # A copied file is entirely new work to OCR; identify the second block
        # explicitly rather than expecting duplicate snippets to select it.
        snippet = "func b() {\n" + snippet
    calls = [
        ("file_read_diff", {"path_array": ["absent.go"]}),
        ("file_read_diff", {"path_array": [new_path, "absent.go"]}),
        ("file_read_diff", {"path_array": [new_path]}),
        (
            "code_comment",
            {
                "comments": [
                    {
                        "path": new_path,
                        "content": "Synthetic changed-block finding.",
                        "existing_code": snippet,
                        "category": "maintainability",
                        "severity": "low",
                    }
                ]
            },
        ),
        ("task_done", {}),
    ]

    class PathPeer(compat.peer._StubHandler):
        step = 0
        observed: dict[str, str] = {}

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            request = json.loads(raw)
            names = {item.get("function", {}).get("name") for item in request.get("tools", [])}
            if "file_read_diff" not in names:
                self.rfile = BytesIO(raw)
                super().do_POST()
                return
            cls = type(self)
            for message in request["messages"]:
                if message.get("role") == "tool":
                    cls.observed[message.get("tool_call_id", "")] = str(message.get("content"))
            if cls.step >= len(calls):
                self.send_error(400, "unexpected extra native round")
                return
            name, args = calls[cls.step]
            cls.step += 1
            payload = json.dumps(
                {
                    "id": "synthetic-native-path",
                    "object": "chat.completion",
                    "model": "synthetic-model",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": f"path-{cls.step}",
                                        "type": "function",
                                        "function": {"name": name, "arguments": json.dumps(args)},
                                    }
                                ],
                            },
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

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PathPeer)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    env = compat.execution._isolated_probe_environment(tmp_path / "home")
    env.update(
        {
            "OCR_LLM_URL": f"http://127.0.0.1:{server.server_port}/v1",
            "OCR_LLM_TOKEN": "synthetic-token",
            "OCR_LLM_MODEL": "synthetic-model",
            "OCR_LLM_PROTOCOL": "openai",
            "OCR_TELEMETRY_ENABLED": "false",
        }
    )
    try:
        payload = json.loads(
            compat.execution._run(
                [
                    binary,
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
                    "--effort",
                    "low",
                    "--no-filter",
                ],
                cwd=root,
                env=env,
            )
        )
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    assert admit_native_range(payload, ReviewRange(base, head)) == ReviewRange(base, head)
    assert payload["status"] == "complete"
    assert PathPeer.step == len(calls)
    missing = PathPeer.observed["path-1"]
    assert "diff not found for: absent.go" in missing and new_path in missing
    assert "file_read" in missing
    mixed = PathPeer.observed["path-2"]
    assert f"==== FILE: {new_path} ====" in mixed
    assert "diff not found for: absent.go" in mixed
    assert f"diff not found for: {new_path}" not in mixed
    assert "func b()" in mixed
    assert "diff not found" not in PathPeer.observed["path-3"]
    assert len(payload["comments"]) == 1
    comment = payload["comments"][0]
    assert comment["path"] == new_path
    if case != "missing-mixed":
        assert (comment["start_line"], comment["end_line"]) == (
            15 if case == "copy" else 16,
            19,
        )
    assert git(root, "status", "--porcelain=v1") == before_state
