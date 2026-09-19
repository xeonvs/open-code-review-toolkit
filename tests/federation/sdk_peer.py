"""Controlled official SDK v2 peer, launched through the real production transport."""

import asyncio
import os

import mcp_types as types
from mcp.server import MCPServer

server = MCPServer("synthetic-peer")


@server.tool()
async def echo(text: str, delay: float = 0.0) -> str:
    """Return the selected synthetic text after a bounded test delay."""
    await asyncio.sleep(delay)
    return text


@server.tool()
def environment_probe() -> str:
    """Return a content-free assertion about the explicit child environment."""
    return (
        "isolated"
        if os.environ.get("SELECTED_VALUE") == "synthetic-selected-value"
        and "SYNTHETIC_UNSELECTED" not in os.environ
        and "HOME" not in os.environ
        else "unexpected"
    )


@server.tool()
def response_probe(kind: str) -> types.CallToolResult:
    """Return a controlled inadmissible result beyond the upstream transport boundary."""
    if kind == "items":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="controlled")] * 129
        )
    if kind == "image":
        return types.CallToolResult(
            content=[types.ImageContent(type="image", data="AA==", mime_type="image/png")]
        )
    text = "x" * (128 * 1024 + 1) if kind == "oversized" else "controlled protected response"
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)])


if __name__ == "__main__":
    server.run()
