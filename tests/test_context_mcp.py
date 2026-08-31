"""Handle-only context tools in the single toolkit-owned MCP process."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from ocr_toolkit import mcp_config
from ocr_toolkit.context.mcp import ContextMCPError, call_context_tool, tool_definitions
from ocr_toolkit.evidence.mcp import TOOL_NAME, handle_request
from tests.test_context_store import POLICY_DIGEST, RUN_ID, commit, pending, remediation_pending
from tests.test_evidence_mcp import _store


def payload(result: dict[str, object]) -> dict[str, object]:
    content = result["content"]
    assert isinstance(content, list) and isinstance(content[0], dict)
    return json.loads(str(content[0]["text"]))


def test_context_tools_list_and_get_only_minted_handles(tmp_path: Path) -> None:
    store = commit(tmp_path / "context.json")
    listed = payload(call_context_tool(store, "context_list", {"page_size": 1}, now=150))
    handle = listed["records"][0]["handle"]

    fetched = payload(call_context_tool(store, "context_get", {"handle": handle}, now=150))
    assert fetched["record"]["text"] == "Synthetic admitted issue context."
    assert "private-object-1" not in json.dumps((listed, fetched))
    for arguments in (
        {"handle": "DEMO-7"},
        {"handle": "https://example.invalid/issue/7"},
        {"handle": handle, "url": "https://example.invalid"},
    ):
        with pytest.raises(ContextMCPError):
            call_context_tool(store, "context_get", arguments, now=150)
    for arguments in (
        {"resource_class": []},
        {"cursor": []},
        {"cursor": "%%%%"},
        {"cursor": "A==="},
    ):
        with pytest.raises(ContextMCPError):
            call_context_tool(store, "context_list", arguments, now=150)

    malformed = handle_request(
        _store(),
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "context_list", "arguments": {"cursor": "%%%%"}},
        },
        store,
    )
    assert malformed is not None
    assert malformed["result"]["isError"] is True  # type: ignore[index]


def test_context_tools_expose_fixed_remediation_resource_without_provider_identity(
    tmp_path: Path,
) -> None:
    store = commit(
        tmp_path / "context.json",
        completeness={"forge_remediation": "complete"},
        records=[remediation_pending()],
    )
    listed = payload(
        call_context_tool(
            store,
            "context_list",
            {"resource_class": "remediation_thread"},
            now=150,
        )
    )
    handle = listed["records"][0]["handle"]
    fetched = payload(call_context_tool(store, "context_get", {"handle": handle}, now=150))
    serialized = json.dumps((listed, fetched), sort_keys=True)

    assert fetched["resource_class"] == "remediation_thread"
    assert fetched["record"]["remediation_thread"]["counts"] == {
        "outdated": 0,
        "replies": 1,
        "resolved": 0,
    }
    assert "current_project" not in serialized
    assert "thread-" not in serialized
    assert "provider_id" not in serialized
    resource_schema = tool_definitions()[0]["inputSchema"]["properties"]["resource_class"]  # type: ignore[index]
    assert resource_schema["enum"] == ["document", "issue", "remediation_thread"]


def test_context_tools_enforce_live_expiry_and_colon_source_cursor(tmp_path: Path) -> None:
    tokens = iter((b"x" * 32, b"y" * 32))
    store = commit(
        tmp_path / "context.json",
        records=[
            pending(canonical_object=f"private-object-{index}", expiry=200 if index else 151)
            for index in range(2)
        ],
        token_bytes=lambda _size: next(tokens),
    )
    listed = payload(
        call_context_tool(
            store,
            "context_list",
            {"page_size": 1, "source": "reference:tracker"},
            now=150,
        )
    )
    cursor = listed["next_cursor"]
    assert cursor
    payload(
        call_context_tool(
            store,
            "context_list",
            {
                "page_size": 1,
                "source": "reference:tracker",
                "cursor": cursor,
            },
            now=150,
        )
    )
    expired = store.records[0]
    with pytest.raises(ContextMCPError, match="unavailable"):
        call_context_tool(store, "context_get", {"handle": expired.handle}, now=151)
    after_expiry = payload(call_context_tool(store, "context_list", {}, now=151))
    assert expired.handle not in json.dumps(after_expiry)
    assert after_expiry["completeness"][expired.source] == "partial"
    with pytest.raises(ContextMCPError, match="cursor is invalid"):
        call_context_tool(
            store,
            "context_list",
            {
                "page_size": 1,
                "source": "reference:tracker",
                "cursor": cursor,
            },
            now=151,
        )
    with pytest.raises(ContextMCPError, match="store is unavailable"):
        call_context_tool(store, "context_list", {}, now=200)


def test_enriched_tools_are_declared_only_with_bound_context(tmp_path: Path) -> None:
    store_path = tmp_path / "context.json"
    context_store = commit(store_path)
    evidence = _store()
    ordinary = handle_request(evidence, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    enriched = handle_request(
        evidence,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        context_store,
    )
    malformed_name = handle_request(
        evidence,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": [], "arguments": {}},
        },
        context_store,
    )

    assert ordinary is not None and enriched is not None
    assert malformed_name is not None and malformed_name["error"]["code"] == -32602  # type: ignore[index]
    assert [tool["name"] for tool in ordinary["result"]["tools"]] == [  # type: ignore[index]
        TOOL_NAME,
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
    ]
    assert [tool["name"] for tool in enriched["result"]["tools"]] == [  # type: ignore[index]
        TOOL_NAME,
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        "context_list",
        "context_get",
    ]

    composition = mcp_config.compose_mcp_servers(
        [],
        replace=True,
        context=mcp_config.MCPContextConfig(
            store_path=str(store_path.resolve()),
            run_id=RUN_ID,
            policy_digest=POLICY_DIGEST,
        ),
    )
    builtin = composition.payload[mcp_config.BUILTIN_EVIDENCE_SERVER]
    assert builtin["tools"] == [
        TOOL_NAME,
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        "context_list",
        "context_get",
    ]
    assert composition.capabilities[0].tools == (
        TOOL_NAME,
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        "context_list",
        "context_get",
    )


def test_real_stdio_mcp_serves_evidence_and_committed_context_in_one_process(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / ".review-context"
    artifact_dir.mkdir()
    _store().write(artifact_dir / "evidence.json")
    context_path = artifact_dir / "context.json"
    now = int(time.time())
    context_store = commit(
        context_path,
        created_at=now,
        expiry=now + 100,
        records=[pending(expiry=now + 100)],
    )
    handle = context_store.records[0].handle
    composition = mcp_config.compose_mcp_servers(
        [],
        replace=True,
        context=mcp_config.MCPContextConfig(
            store_path=str(context_path.resolve()),
            run_id=RUN_ID,
            policy_digest=POLICY_DIGEST,
        ),
    )
    builtin = composition.payload[mcp_config.BUILTIN_EVIDENCE_SERVER]
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "context_list", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "context_get", "arguments": {"handle": handle}},
        },
    ]
    completed = subprocess.run(
        [str(builtin["command"]), *map(str, builtin["args"])],
        cwd=tmp_path,
        env={"PATH": ""},
        input="".join(json.dumps(request) + "\n" for request in requests),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert completed.returncode == 0, completed.stderr
    assert [tool["name"] for tool in responses[0]["result"]["tools"]] == [
        TOOL_NAME,
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
        "context_list",
        "context_get",
    ]
    assert handle in responses[1]["result"]["content"][0]["text"]
    assert "Synthetic admitted issue context." in responses[2]["result"]["content"][0]["text"]
