"""Run the toolkit-owned repository evidence MCP server."""

from ocr_toolkit.evidence.artifacts import repository_artifacts
from ocr_toolkit.evidence.mcp import serve


def main() -> int:
    """Serve the fixed private evidence store for the current repository."""

    return serve(repository_artifacts().store)


if __name__ == "__main__":
    raise SystemExit(main())
