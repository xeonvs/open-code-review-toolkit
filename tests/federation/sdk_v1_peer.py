"""Controlled SDK v1 peer for a separate explicitly selected qualification environment."""

from mcp.server.fastmcp import FastMCP

server = FastMCP("synthetic-v1-peer")


@server.tool()
def echo(text: str) -> str:
    """Return the selected controlled text."""
    return text


if __name__ == "__main__":
    server.run()
