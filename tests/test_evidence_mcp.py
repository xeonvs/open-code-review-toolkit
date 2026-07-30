"""Contract and abuse tests for the built-in read-only evidence MCP server."""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from ocr_toolkit import __version__, mcp_config
from ocr_toolkit.evidence import EvidenceRecord, EvidenceStore, RefRole, TrustClass
from ocr_toolkit.evidence.mcp import (
    MAX_REQUEST_BYTES,
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    TOOL_NAME,
    call_tool,
    handle_request,
    serve,
)

SHA = "a" * 40


def _store(count: int = 3) -> EvidenceStore:
    """Build deterministic synthetic records for MCP tests."""

    store = EvidenceStore()
    for index in range(count):
        assert store.add(
            EvidenceRecord(
                kind="dependency.declared",
                value={"name": f"package-{index}", "version": f"{index}.0"},
                source_path="requirements.txt",
                ref=RefRole.HEAD,
                commit_sha=SHA,
                component="python",
                provenance="synthetic parser",
                trust=TrustClass.SOURCE_REPOSITORY,
            )
        )
    return store


def _payload(result: dict[str, object]) -> dict[str, object]:
    """Decode the JSON text carried by one successful tool result."""

    content = result["content"]
    assert isinstance(content, list)
    block = content[0]
    assert isinstance(block, dict)
    return json.loads(str(block["text"]))


def test_summary_list_get_and_cursor_binding() -> None:
    store = _store()

    summary = _payload(call_tool(store, {"action": "summary"}))
    first = _payload(call_tool(store, {"action": "list", "page_size": 2}))
    second = _payload(
        call_tool(
            store,
            {"action": "list", "page_size": 2, "cursor": first["next_cursor"]},
        )
    )
    records = first["records"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    fetched = _payload(call_tool(store, {"action": "get", "id": record["id"]}))

    assert summary["records"] == 3
    assert first["returned"] == 2
    assert second["returned"] == 1
    assert fetched["record"] == record
    with pytest.raises(ValueError, match="cursor"):
        call_tool(
            store,
            {
                "action": "list",
                "kind": "repository.file",
                "cursor": first["next_cursor"],
            },
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"action": "write"},
        {"action": "summary", "extra": True},
        {"action": "list", "page_size": 0},
        {"action": "list", "ref": "working_tree"},
        {"action": "get", "id": "not-an-id"},
    ],
)
def test_tool_rejects_unknown_or_mutating_requests(arguments: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        call_tool(_store(), arguments)


def test_json_rpc_initialize_lists_read_only_tool_and_returns_safe_errors() -> None:
    store = _store()
    initialized = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        },
    )
    listed = handle_request(store, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    failed = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": {"action": "write"}},
        },
    )

    assert initialized and initialized["result"]
    assert initialized and initialized["result"]["serverInfo"]["version"] == __version__  # type: ignore[index]
    assert listed and TOOL_NAME in json.dumps(listed)
    assert listed and '"readOnlyHint": true' in json.dumps(listed)
    assert failed and failed["result"]["isError"] is True  # type: ignore[index]


def test_initialize_supports_exact_ocr_1_8_sdk_protocol_revisions() -> None:
    """Negotiate every revision supported by OCR 1.8.0's Go MCP SDK."""

    assert PROTOCOL_VERSION == "2025-11-25"
    assert {
        "2024-11-05",
        "2025-03-26",
        "2025-06-18",
        "2025-11-25",
    } == SUPPORTED_PROTOCOL_VERSIONS
    for request_id, version in enumerate(sorted(SUPPORTED_PROTOCOL_VERSIONS), start=1):
        initialized = handle_request(
            _store(),
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {"name": "ocr", "version": "1.8.0"},
                },
            },
        )

        assert initialized is not None
        assert initialized["result"]["protocolVersion"] == version
        assert initialized["result"]["capabilities"] == {"tools": {"listChanged": False}}


def test_initialized_notification_and_post_handshake_operations() -> None:
    """Accept the 2025-11-25 lifecycle before listing and calling tools."""

    store = _store()
    assert (
        handle_request(
            store,
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        is None
    )
    pinged = handle_request(store, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert pinged is not None
    assert pinged["result"] == {}
    listed = handle_request(store, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed is not None
    assert [tool["name"] for tool in listed["result"]["tools"]] == [TOOL_NAME]
    called = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": {"action": "summary"}},
        },
    )
    assert called is not None
    assert called["result"].get("isError", False) is False
    assert called["result"]["content"][0]["type"] == "text"


def test_notifications_never_receive_json_rpc_responses() -> None:
    """Honor the no-response contract for every request without an id."""

    store = _store()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "evidence.json"
        store.write(path)
        notifications = [
            {"jsonrpc": "2.0", "method": "ping"},
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": TOOL_NAME, "arguments": {"action": "summary"}},
            },
            {"jsonrpc": "2.0", "method": "synthetic/unknown"},
        ]
        stdin = io.StringIO("".join(json.dumps(item) + "\n" for item in notifications))
        stdout = io.StringIO()

        assert serve(path, stdin, stdout) == 0

    assert stdout.getvalue() == ""


def test_initialize_negotiates_current_revision_for_unknown_client_version() -> None:
    """Return one supported revision and leave acceptance to the client."""

    negotiated = handle_request(
        _store(),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2026-06-30"},
        },
    )

    assert negotiated is not None
    assert negotiated["result"]["protocolVersion"] == PROTOCOL_VERSION


def test_stdio_uses_stdout_only_for_protocol_and_bounds_requests() -> None:
    store = _store()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "evidence.json"
        store.write(path)
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        oversized = "x" * MAX_REQUEST_BYTES
        stdout = io.StringIO()

        assert serve(path, io.StringIO(request + "\n" + oversized + "\n"), stdout) == 0

    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert responses[0]["result"] == {}
    assert responses[1]["error"]["code"] == -32700


def test_stdio_stops_reading_an_oversized_request_at_the_boundary() -> None:
    """Do not materialize an unbounded protocol line before rejecting it."""

    class RecordingInput(io.StringIO):
        """Record every explicit readline limit requested by the server."""

        def __init__(self, value: str) -> None:
            super().__init__(value)
            self.limits: list[int] = []

        def readline(self, size: int = -1, /) -> str:
            self.limits.append(size)
            return super().readline(size)

    store = _store()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "evidence.json"
        store.write(path)
        stdin = RecordingInput("x" * (MAX_REQUEST_BYTES * 4) + "\n")
        stdout = io.StringIO()

        assert serve(path, stdin, stdout) == 0

    assert stdin.limits
    assert all(0 < limit <= MAX_REQUEST_BYTES + 2 for limit in stdin.limits)
    assert json.loads(stdout.getvalue())["error"]["code"] == -32700


def test_composed_server_launches_without_path_lookup() -> None:
    """Prove OCR can start the installed server with a restricted PATH."""

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store_path = root / ".review-context" / "evidence.json"
        _store().write(store_path)
        shadow_package = root / "ocr_toolkit"
        shadow_package.mkdir()
        (shadow_package / "__init__.py").write_text(
            "raise RuntimeError('untrusted shadow package imported')\n",
            encoding="utf-8",
        )
        composition = mcp_config.compose_mcp_servers([], replace=True)
        builtin = composition.payload[mcp_config.BUILTIN_EVIDENCE_SERVER]
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        completed = subprocess.run(
            [str(builtin["command"]), *map(str, builtin["args"])],
            cwd=root,
            env={"PATH": ""},
            input=request + "\n",
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["result"] == {}
