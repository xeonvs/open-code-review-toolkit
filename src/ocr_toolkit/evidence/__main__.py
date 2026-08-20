"""Run the toolkit-owned repository evidence and optional context MCP server."""

import argparse
from pathlib import Path

from ocr_toolkit.evidence.artifacts import repository_artifacts
from ocr_toolkit.evidence.mcp import serve


def main() -> int:
    """Serve the fixed private evidence store for the current repository."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--context-store", type=Path)
    parser.add_argument("--context-run-id", default="")
    parser.add_argument("--context-policy-digest", default="")
    arguments = parser.parse_args()
    return serve(
        repository_artifacts().store,
        context_path=arguments.context_store,
        context_run_id=arguments.context_run_id,
        context_policy_digest=arguments.context_policy_digest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
