"""Real SDK stdio/Unix-relay gateway lifecycle, accounting, and isolation checks."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from ocr_toolkit.federation import FederationError, parse_registry, start_gateway

PEER = Path(__file__).with_name("sdk_peer.py")


def registry_value() -> dict[str, Any]:
    """Return one selected synthetic tool over an explicit absolute argv."""
    return {
        "version": 2,
        "servers": {
            "synthetic": {
                "transport": {
                    "type": "stdio",
                    "command": sys.executable,
                    "args": ["-I", str(PEER)],
                },
                "tools": {"echo": {}},
            }
        },
    }


def relay_client(gateway: Any) -> Client:
    """Use the official SDK as the external OCR-side protocol collaborator."""
    return Client(
        StdioServerParameters(
            command=gateway.ocr_server["command"], args=gateway.ocr_server["args"]
        ),
        cache=None,
    )


def test_actual_sdk_relay_cache_dlp_and_closed_receipt() -> None:
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())),
        environment={},
        forbidden=("controlled protected phrase",),
        run_id="a" * 32,
    )
    endpoint = Path(gateway.ocr_server["args"][-1])
    assert gateway._gateway is not None
    assert gateway._gateway.budget.requests == 2  # Upstream discovery and tools/list.
    assert endpoint.stat().st_mode & 0o777 == 0o600
    assert endpoint.parent.stat().st_mode & 0o777 == 0o700

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            assert client.protocol_version == "2026-07-28"
            listing = await client.list_tools()
            assert [tool.name for tool in listing.tools] == ["synthetic__echo"]
            for _ in range(2):
                response = await client.call_tool("synthetic__echo", {"text": "controlled result"})
                assert response.content[0].text == "controlled result"
            denied = await client.call_tool(
                "synthetic__echo", {"text": "controlled protected phrase"}
            )
            assert denied.is_error
            assert denied.content[0].text == "federation_unavailable"

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["attempted"] == 3
    assert counts["completed"] == 2
    assert counts["denied"] == counts["dlp_rejected"] == counts["cache_hits"] == 1
    assert "controlled result" in gateway.forbidden_publication
    assert "controlled protected phrase" not in json.dumps(receipt)
    assert not endpoint.parent.exists()
    assert gateway.close() == receipt


def test_actual_sdk_single_flight_counts_each_waiter() -> None:
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            results = await asyncio.gather(
                *(
                    client.call_tool(
                        "synthetic__echo", {"text": "shared controlled result", "delay": 0.1}
                    )
                    for _ in range(3)
                )
            )
            assert all(result.content[0].text == "shared controlled result" for result in results)

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["attempted"] == counts["completed"] == 3
    assert counts["single_flight"] == 2


def test_missing_tool_fails_before_gateway_is_returned() -> None:
    value = registry_value()
    value["servers"]["synthetic"]["tools"] = {"missing": {}}
    with pytest.raises(FederationError, match="inventory_invalid"):
        start_gateway(parse_registry(json.dumps(value)), environment={}, run_id="a" * 32)


def test_stdio_child_receives_only_explicit_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNTHETIC_UNSELECTED", "synthetic-parent-value")
    value = registry_value()
    value["servers"]["synthetic"]["transport"]["env_from"] = {"SELECTED_VALUE": "SYNTHETIC_SOURCE"}
    value["servers"]["synthetic"]["tools"] = {"environment_probe": {}}
    gateway = start_gateway(
        parse_registry(json.dumps(value)),
        environment={
            "SYNTHETIC_SOURCE": "synthetic-selected-value",
            "SYNTHETIC_UNSELECTED": "synthetic-parent-value",
        },
        run_id="a" * 32,
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            result = await client.call_tool("synthetic__environment_probe", {})
            assert result.content[0].text == "isolated"

    try:
        asyncio.run(exercise())
    finally:
        assert gateway.close()["tools"]["synthetic__environment_probe"]["completed"] == 1


def test_upstream_response_admission_is_atomic_and_rejections_are_not_cached() -> None:
    value = registry_value()
    value["servers"]["synthetic"]["tools"] = {"response_probe": {}}
    gateway = start_gateway(
        parse_registry(json.dumps(value)),
        environment={},
        forbidden=("controlled protected response",),
        run_id="a" * 32,
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            for kind in ("items", "image", "oversized", "protected", "protected"):
                result = await client.call_tool("synthetic__response_probe", {"kind": kind})
                assert result.is_error
                assert result.content[0].text == "federation_unavailable"

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__response_probe"]
    assert counts["attempted"] == 5
    assert counts["completed"] == counts["cache_hits"] == 0
    assert counts["dlp_rejected"] == 2
    assert counts["oversized"] == 1
    assert not gateway.forbidden_publication


def test_cached_return_still_consumes_delivery_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    import ocr_toolkit.federation.gateway as module

    monkeypatch.setattr(module, "DELIVERY_BYTES", 1024)
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            first = await client.call_tool("synthetic__echo", {"text": "x" * 300})
            assert not first.is_error
            second = await client.call_tool("synthetic__echo", {"text": "x" * 300})
            assert second.is_error

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["attempted"] == 2
    assert counts["completed"] == counts["denied"] == counts["cache_hits"] == 1


def test_empty_registry_and_secret_resolution_are_closed() -> None:
    gateway = start_gateway(
        parse_registry('{"version":2,"servers":{}}'), environment={}, run_id="a" * 32
    )
    assert gateway.aliases == ()
    assert gateway.close()["tools"] == {}
    value = registry_value()
    value["servers"]["synthetic"]["transport"]["env_from"] = {"SYNTHETIC_VALUE": "SYNTHETIC_SECRET"}
    with pytest.raises(FederationError, match="secret_missing"):
        start_gateway(parse_registry(json.dumps(value)), environment={}, run_id="a" * 32)


@pytest.mark.parametrize("run_id", ["", "synthetic_run", "A" * 32, "g" * 32, "a" * 31, "a" * 33])
def test_gateway_rejects_unbound_run_identity(run_id: str) -> None:
    with pytest.raises(FederationError, match="registry_invalid"):
        start_gateway(parse_registry('{"version":2,"servers":{}}'), environment={}, run_id=run_id)


def test_call_overflow_bounds_counters_and_blocks_finalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ocr_toolkit.federation.gateway as module

    monkeypatch.setattr(module, "MAX_CALLS", 2)
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            for _ in range(2):
                assert not (
                    await client.call_tool("synthetic__echo", {"text": "controlled"})
                ).is_error
            assert (await client.call_tool("synthetic__echo", {"text": "controlled"})).is_error

    try:
        asyncio.run(exercise())
    finally:
        with pytest.raises(FederationError, match="cleanup_failed"):
            gateway.close()
    assert gateway._gateway is not None
    assert gateway._gateway.counts["synthetic__echo"]["attempted"] == 2


def test_disabled_dlp_passes_protected_content_but_preserves_schema_and_origin_gates() -> None:
    protected = "controlled protected phrase"
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())),
        environment={},
        forbidden=(protected,),
        run_id="a" * 32,
        dlp_enabled=False,
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            admitted = await client.call_tool("synthetic__echo", {"text": protected})
            assert admitted.content[0].text == protected
            assert (
                await client.call_tool(
                    "synthetic__echo", {"text": "https://foreign.invalid/record"}
                )
            ).is_error
            assert (await client.call_tool("synthetic__echo", {"text": "x" * 32768})).is_error

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["completed"] == 1
    assert counts["denied"] == 2
    assert counts["dlp_rejected"] == 0


@pytest.mark.parametrize("change", ["old", "extra", "alias", "relative", "https_local_only"])
def test_registry_rejects_unknown_or_ambiguous_authority(change: str) -> None:
    value = registry_value()
    profile = "local"
    if change == "old":
        value["version"] = 1
    elif change == "extra":
        value["overrides"] = {}
    elif change == "alias":
        value["servers"]["synthetic"]["tools"] = {"bad__name": {}}
    elif change == "relative":
        value["servers"]["synthetic"]["transport"]["command"] = "python"
    else:
        profile = "gitlab_mr"
    with pytest.raises(FederationError, match="registry_invalid"):
        parse_registry(json.dumps(value), profile=profile)


def test_cancelling_one_waiter_preserves_other_waiter() -> None:
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            first = asyncio.create_task(
                client.call_tool(
                    "synthetic__echo", {"text": "shared controlled result", "delay": 0.3}
                )
            )
            other = asyncio.create_task(
                client.call_tool(
                    "synthetic__echo", {"text": "shared controlled result", "delay": 0.3}
                )
            )
            await asyncio.sleep(0.1)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            result = await other
            assert result.content[0].text == "shared controlled result"

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["attempted"] == 2
    assert counts["completed"] == counts["failed"] == counts["single_flight"] == 1


def test_actual_call_deadline_is_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    import ocr_toolkit.federation.gateway as module

    monkeypatch.setattr(module, "CALL_SECONDS", 0.15)
    gateway = start_gateway(
        parse_registry(json.dumps(registry_value())), environment={}, run_id="a" * 32
    )

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            result = await client.call_tool(
                "synthetic__echo", {"text": "controlled result", "delay": 0.8}
            )
            assert result.is_error

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    counts = receipt["tools"]["synthetic__echo"]
    assert counts["attempted"] == counts["timed_out"] == 1


def test_optional_real_sdk_v1_v2_mixed_run() -> None:
    executable = os.environ.get("OCR_FEDERATION_V1_PYTHON")
    if not executable:
        pytest.skip("SDK v1 qualification uses its own explicit environment")
    value = registry_value()
    value["servers"]["legacy"] = {
        "transport": {
            "type": "stdio",
            "command": executable,
            "args": ["-I", str(PEER.with_name("sdk_v1_peer.py"))],
        },
        "tools": {"echo": {}},
    }
    gateway = start_gateway(parse_registry(json.dumps(value)), environment={}, run_id="a" * 32)
    assert gateway._gateway is not None
    assert gateway._gateway.tools["legacy__echo"].client.protocol_version == "2025-11-25"
    assert gateway._gateway.tools["synthetic__echo"].client.protocol_version == "2026-07-28"

    async def exercise() -> None:
        async with relay_client(gateway) as client:
            for alias in gateway.aliases:
                result = await client.call_tool(alias, {"text": "controlled mixed result"})
                assert result.content[0].text == "controlled mixed result"

    try:
        asyncio.run(exercise())
    finally:
        receipt = gateway.close()
    assert all(counts["completed"] == 1 for counts in receipt["tools"].values())
