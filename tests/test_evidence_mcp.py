"""Contract and abuse tests for the built-in read-only evidence MCP server."""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest

from ocr_toolkit import __version__
from ocr_toolkit.evidence import EvidenceRecord, EvidenceStore, RefRole, TrustClass
from ocr_toolkit.evidence.mcp import (
    MAX_REQUEST_BYTES,
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
