#!/usr/bin/env python3
"""Probe the installed federation runtime through a real bounded MCP exchange."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server import MCPServer

from ocr_toolkit.federation import admission, parse_registry, start_gateway, transport
from ocr_toolkit.federation import gateway as gateway_module

peer = MCPServer("installed-runtime-smoke-peer")


@peer.tool()
def schema_probe(value: str) -> str:
    """Return one controlled value through the admitted gateway schema."""

    return f"admitted:{value}"


def _registry() -> str:
    """Describe the private synthetic peer with one explicitly admitted tool."""

    return json.dumps(
        {
            "version": 2,
            "servers": {
                "synthetic": {
                    "transport": {
                        "type": "stdio",
                        "command": sys.executable,
                        "args": ["-I", str(Path(__file__).resolve()), "--peer"],
                    },
                    "tools": {"schema_probe": {"assurance": "review_read"}},
                }
            },
        }
    )


def _relay_client(running: Any) -> Client:
    """Connect to the installed private relay with the official SDK client."""

    return Client(
        StdioServerParameters(
            command=running.ocr_server["command"], args=running.ocr_server["args"]
        ),
        cache=None,
    )


async def _exercise(running: Any) -> None:
    """Negotiate MCP, validate the exported schema, and call one real tool."""

    async with asyncio.timeout(30):
        async with _relay_client(running) as client:
            listing = await client.list_tools()
            if len(listing.tools) != 1 or listing.tools[0].name != "synthetic__schema_probe":
                raise RuntimeError("installed gateway exported an unexpected tool inventory")
            schema = listing.tools[0].input_schema
            if (
                schema.get("type") != "object"
                or schema.get("required") != ["value"]
                or schema.get("properties", {}).get("value", {}).get("type") != "string"
            ):
                raise RuntimeError("installed gateway exported an unexpected tool schema")
            result = await client.call_tool("synthetic__schema_probe", {"value": "controlled"})
            if (
                result.is_error
                or len(result.content) != 1
                or result.content[0].text != "admitted:controlled"
            ):
                raise RuntimeError("installed gateway returned an unexpected tool result")


def main() -> int:
    """Import every federation boundary and complete one installed runtime probe."""

    if len(sys.argv) == 2 and sys.argv[1] == "--peer":
        peer.run()
        return 0
    if len(sys.argv) != 1:
        raise SystemExit("usage: installed_runtime_smoke.py")
    for module in (admission, gateway_module, transport):
        if not module.__name__.startswith("ocr_toolkit.federation."):
            raise RuntimeError("installed federation module import was not canonical")
    running = start_gateway(parse_registry(_registry()), environment={}, run_id="0" * 32)
    try:
        asyncio.run(_exercise(running))
    finally:
        receipt = running.close()
    counts = receipt["tools"]["synthetic__schema_probe"]
    if (
        receipt.get("schema") != "ocr.federation/v1"
        or counts["attempted"] != 1
        or counts["completed"] != 1
    ):
        raise RuntimeError("installed gateway produced an unexpected receipt")
    print(json.dumps({"installed_runtime_smoke": "ok"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
