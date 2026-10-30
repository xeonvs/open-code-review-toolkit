"""Observe qualified OCR group, round and immutable cross-group context boundaries."""

from __future__ import annotations

import http.server
import json
import os
import re
import threading
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from ocr_toolkit import cli, provider_config, review_debug, review_runner
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.preflight import validate_ocr_binary
from tests.diagrams.support import references
from tests.test_evidence_repository import git


@pytest.mark.parametrize("grouping", ("combined", "singletons", "fallback", "configuration"))
@pytest.mark.parametrize("missing_context", (False, True))
@pytest.mark.parametrize("diagram_kind", (None, "flowchart", "sequence"))
def test_native_group_context_and_rounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    grouping: str,
    missing_context: bool,
    diagram_kind: str | None,
) -> None:
    """Cross the actual launcher/tools to distinguish global access from group visibility."""

    binary = os.environ.get("OCR_GITLINK_QUALIFY_BINARY")
    if binary is None:
        pytest.skip("set OCR_GITLINK_QUALIFY_BINARY to checksum-verified OCR 1.13.3")
    assert validate_ocr_binary(executable=binary, announce=False) == "1.13.3"
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from ocr_compat import _StubHandler

    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    paths = ("a_first.py", "b_second.py", "c_before.py", "d_fourth.py", "filtered.py")
    stable = "# Unchanged synthetic context\n" * 6
    for index, path in enumerate(paths):
        (root / path).write_text(f"# BASE_{index}\n{stable}def value():\n    return 1\n")
    (root / "removed.py").write_text("# REMOVED_CONTEXT\ndef old():\n    return 1\n")
    (root / "pyproject.toml").write_text(
        '[project]\nname="synthetic"\nversion="1.0.0"\n'
        'requires-python=">=3.12"\ndependencies=["Jinja2>=3.1"]\n'
    )
    (root / "pylock.toml").write_text(
        'lock-version="1.0"\n[[packages]]\nname="jinja2"\nversion="3.1.6"\n'
    )
    configuration = root / ".github/workflows/quality.yml"
    if grouping == "configuration":
        configuration.parent.mkdir(parents=True)
        configuration.write_text("name: synthetic\njobs: {}\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    for index, path in enumerate(paths):
        # Preserve enough identical lines to make the rename unambiguous.
        (root / path).write_text(f"# HEAD_{index}\n{stable}def value():\n    return 2\n")
    git(root, "mv", "c_before.py", "c_after.py")
    (root / "removed.py").unlink()
    if grouping == "configuration":
        configuration.write_text("name: synthetic updated\njobs: {}\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    assert re.search(
        r"R[0-9]+\tc_before.py\tc_after.py", git(root, "diff", "--name-status", "-M", base, head)
    )
    selected = {"a_first.py", "b_second.py", "c_after.py", "d_fourth.py"}
    if grouping == "configuration":
        selected.add(".github/workflows/quality.yml")
    elements = [
        {"id": identity, "label": label, "references": references(path, 9, 9)}
        for identity, label, path in (
            ("first", "First helper", "a_first.py"),
            ("second", "Second helper", "b_second.py"),
        )
    ]
    candidate = {
        "state": "generated",
        "base_sha": base,
        "head_sha": head,
        "diagram": {
            "kind": diagram_kind,
            **(
                {
                    "nodes": [{**item, "kind": "step"} for item in elements],
                    "edges": [
                        {
                            "source": "first",
                            "target": "second",
                            "condition": "version >= 2026.10.19",
                            "references": references("a_first.py", 9, 9),
                        }
                    ],
                }
                if diagram_kind == "flowchart"
                else {
                    "participants": elements,
                    "steps": [
                        {
                            "kind": "message",
                            "source": "first",
                            "target": "second",
                            "message_type": "call",
                            "label": "version >= 2026.10.19",
                            "references": references("b_second.py", 9, 9),
                        }
                    ],
                }
            ),
        },
    }
    (root / "b_second.py").write_text("# UNSTAGED_POISON\n")
    (root / "staged.txt").write_text("staged local work\n")
    git(root, "add", "staged.txt")
    (root / "untracked.txt").write_text("untracked local work\n")
    preserved = tuple(
        root / value
        for value in (".git/HEAD", ".git/index", "b_second.py", "staged.txt", "untracked.txt")
    )
    before = tuple(path.read_bytes() for path in preserved)

    class ContextPeer(_StubHandler):
        grouping_mode = "combined" if grouping == "combined" else "singletons"
        observations: list[dict[str, object]] = []

        def response(self, message: dict[str, object], *, tools: bool = True) -> None:
            payload = json.dumps(
                {
                    "id": "synthetic-context-probe",
                    "object": "chat.completion",
                    "model": "synthetic-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": message,
                            "finish_reason": "tool_calls" if tools else "stop",
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

        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 512_000:
                self.send_error(400)
                return
            raw = self.rfile.read(size)
            request = json.loads(raw)
            names = {tool.get("function", {}).get("name") for tool in request.get("tools", [])}
            messages = request.get("messages", [])
            if grouping == "fallback" and not names and self._is_grouping_request(messages):
                self.response({"role": "assistant", "content": "invalid grouping"}, tools=False)
                return
            if "ocr_toolkit_evidence" not in names or "approve_all_comments" in names:
                self.rfile = BytesIO(raw)
                super().do_POST()
                return
            assert DIAGRAM_TOOL_NAME in names
            prompt = next(
                message["content"] for message in messages if message.get("role") == "user"
            )
            assert "even with no findings" in prompt and "entire reviewed change" in prompt
            assert "include dotfiles" in prompt
            own_block = prompt.split("<review_files>", 1)[1].split("</review_files>", 1)[0]
            own = set(re.findall(r'<file path="([^"\r\n]+)">', own_block))
            other = prompt.split("<other_changed_files>", 1)[1].split("</other_changed_files>", 1)[
                0
            ]
            first = min(own)
            results = [message for message in messages if message.get("role") == "tool"]
            if not results:
                type(self).observations.append(
                    {
                        "own": own,
                        "other": other,
                        "confirmed": "Synthetic cross-group finding." in prompt,
                    }
                )
                name, arguments = "ocr_toolkit_evidence", {"action": "summary"}
            elif len(results) == 1:
                requested = (
                    ["missing.py"]
                    if missing_context
                    else [*sorted(selected - own), "removed.py", "filtered.py"]
                )
                name, arguments = "file_read_diff", {"path_array": requested}
            else:
                summary = json.loads(results[0]["content"])
                called = {
                    tool["function"]["name"]
                    for message in messages
                    for tool in message.get("tool_calls", [])
                }
                domain_kinds = ("framework.detected", "dependency.locked", "runtime.declared")
                queries = {
                    call["id"]: json.loads(call["function"]["arguments"])
                    for message in messages
                    for call in message.get("tool_calls", [])
                    if call["function"]["name"] == "ocr_toolkit_evidence"
                }
                queried = {query.get("kind") for query in queries.values()}
                for response in results:
                    kind = queries.get(response.get("tool_call_id"), {}).get("kind")
                    if kind in domain_kinds:
                        type(self).observations.append(
                            {"kind": kind, "evidence": json.loads(response["content"])}
                        )
                remaining = [kind for kind in domain_kinds if kind not in queried]
                if len(results) == 2:
                    type(self).observations.append(
                        {"own": own, "diff_result": results[-1].get("content", "")}
                    )
                    if "Synthetic cross-group finding." in prompt:
                        type(self).observations.append(
                            {"repeat_diagram_state": summary["diagram_output"]["state"], "own": own}
                        )
                if remaining:
                    name, arguments = (
                        "ocr_toolkit_evidence",
                        {"action": "list", "kind": remaining[0], "ref": "head"},
                    )
                elif (
                    diagram_kind is not None
                    and not missing_context
                    and min(selected) in own
                    and summary["diagram_output"]["state"] == "pending"
                    and DIAGRAM_TOOL_NAME not in called
                ):
                    name, arguments = DIAGRAM_TOOL_NAME, candidate
                elif "Synthetic cross-group finding." in prompt or "code_comment" in called:
                    name, arguments = "task_done", {}
                elif grouping == "configuration" and min(selected) in own:
                    # A configuration-only owner still emits the global diagram,
                    # independently of whether that group has any finding.
                    name, arguments = "task_done", {}
                else:
                    name, arguments = (
                        "code_comment",
                        {
                            "comments": [
                                {
                                    "path": first,
                                    "existing_code": "    return 2",
                                    "content": "Synthetic cross-group finding.",
                                    "severity": "low",
                                    "category": "maintainability",
                                }
                            ]
                        },
                    )
            self.response(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"context-{first}-{len(results)}",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                    ],
                }
            )

    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ocr").symlink_to(binary)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    for name, value in {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "OCR_LLM_TOKEN": "synthetic-token",
        "OCR_LLM_MODEL": "synthetic-model",
        "OCR_LLM_PROTOCOL": "openai",
        "OCR_LLM_AUTH_MODE": "api-key",
        "OCR_TELEMETRY_ENABLED": "false",
        "OCR_REVIEW_CONTEXT_MODE": "off",
        "OCR_REVIEW_PROGRESS": "false",
        "OCR_REVIEW_DIAGRAM_MODE": "local",
    }.items():
        monkeypatch.setenv(name, value)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), ContextPeer)
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
    debug = tmp_path / "debug"
    session_homes = []
    mkdtemp = review_runner.tempfile.mkdtemp

    def observed_temp(*args, **kwargs):
        value = mkdtemp(*args, **kwargs)
        if kwargs.get("prefix") == "ocr-toolkit-session-":
            session_homes.append(Path(value))
        return value

    monkeypatch.setattr(review_runner.tempfile, "mkdtemp", observed_temp)
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
                "--debug-dir",
                str(debug),
                "--",
                "--from",
                base,
                "--to",
                head,
                "--exclude",
                "filtered.py",
                "--concurrency",
                "2",
                "--max-tokens-budget",
                "0",
            ]
        )
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    assert code == 0, stderr.read_text()[-3000:]
    raw_result = json.loads(result.read_text())
    assert raw_result["manifest"]["terminal_state"] == "complete"
    assert {item["path"] for item in raw_result["manifest"]["coverage"]["selected"]} == selected
    assert tuple(path.read_bytes() for path in preserved) == before
    journal = json.loads((debug / "journal.json").read_text())
    assert journal["schema_version"] == review_debug.DEBUG_SCHEMA
    assert journal["artifacts"]["native-trace.jsonl"]["status"] == "passed", journal["artifacts"]
    trace = [json.loads(line) for line in (debug / "native-trace.jsonl").read_text().splitlines()]
    assert trace[0]["diffFrom"] == base and trace[0]["diffTo"] == head
    assert trace[-1]["type"] == "session_end"
    # Private native diagnostics preserve identifiers that final DLP may redact.
    native_result = json.loads((debug / "raw-result.json").read_bytes())
    assert {row["sessionId"] for row in trace} == {native_result["session_id"]}
    assert any(row["type"] == "llm_request" and row["taskType"] == "main_task" for row in trace)
    assert any(row["type"] == "tool_call" and row["tool_name"] == "file_read_diff" for row in trace)
    assert "cross-group diffs" in (debug / "bootstrap.md").read_text()
    bootstrap = (debug / "bootstrap.md").read_text()
    assert bootstrap.count(base) == bootstrap.count(head) == 1
    assert "same commit as base" in bootstrap
    assert bootstrap.index("## Requested change diagram") > bootstrap.index("## Evidence coverage")
    assert "frameworks/runtimes" in bootstrap and "declared/locked dependency versions" in bootstrap
    by_kind = {
        item["kind"]: item["evidence"] for item in ContextPeer.observations if "evidence" in item
    }
    for kind in ("framework.detected", "dependency.locked", "runtime.declared"):
        assert by_kind[kind]["records"]
    assert "jinja2" in str(by_kind["framework.detected"]).lower()
    assert "3.1.6" in str(by_kind["dependency.locked"])
    assert ">=3.12" in str(by_kind["runtime.declared"])
    assert "Text equivalent:" not in report.read_text()
    generated = diagram_kind is not None and not missing_context
    assert json.loads((debug / "diagram.json").read_text())["submissions"] == int(generated)
    assert ("```mermaid" in report.read_text()) == generated
    assert (
        f"Change diagram: `{'generated' if generated else 'not-generated'}`" in report.read_text()
    )
    if generated:
        private_candidate = (debug / "diagram.json").read_text()
        assert "a_first.py" in private_candidate and "b_second.py" in private_candidate
        assert "First helper" in report.read_text() and "Second helper" in report.read_text()
        diagram_section = (
            report.read_text().split("### Change flow", 1)[1].split("### Technical details", 1)[0]
        )
        assert "a_first.py:L9" not in diagram_section
        assert any(
            row["type"] == "tool_call" and row["tool_name"] == DIAGRAM_TOOL_NAME for row in trace
        )
        owner_repeat = [
            item["repeat_diagram_state"]
            for item in ContextPeer.observations
            if "repeat_diagram_state" in item and min(selected) in item["own"]
        ]
        assert owner_repeat == ([] if grouping == "configuration" else ["received"])
    assert session_homes and all(not path.exists() for path in session_homes)
    assert (debug / "native-trace.jsonl").stat().st_mode & 0o777 == 0o600
    initial = [
        item for item in ContextPeer.observations if "other" in item and not item["confirmed"]
    ]
    repeated = [item for item in ContextPeer.observations if "other" in item and item["confirmed"]]
    assert {
        tuple(sorted(item["own"]))
        for item in initial
        if not (grouping == "configuration" and min(selected) in item["own"])
    } == {tuple(sorted(item["own"])) for item in repeated}
    assert len(initial) == (1 if grouping == "combined" else len(selected))
    for item in initial:
        for path in selected - item["own"]:
            assert path in item["other"]
        assert "filtered.py" not in item["other"]
        assert "removed.py" in item["other"]
    contexts = [
        str(item["diff_result"]) for item in ContextPeer.observations if "diff_result" in item
    ]
    assert contexts
    if missing_context:
        assert all("Error: diff not found" in value for value in contexts)
        assert raw_result["tool_calls"]["failure"] == 0
    else:
        assert all(
            "UNSTAGED_POISON" not in value and "REMOVED_CONTEXT" in value and "HEAD_4" in value
            for value in contexts
        )
        if grouping != "combined":
            for item in ContextPeer.observations:
                if "diff_result" not in item:
                    continue
                for path in selected - item["own"]:
                    assert f"==== FILE: {path} ====\n" in item["diff_result"]
