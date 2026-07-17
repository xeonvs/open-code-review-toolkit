"""Unified command-line interface for Open Code Review CI helpers."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ocr_toolkit import configure, mcp_config, preflight
from ocr_toolkit.context import render as context_render
from ocr_toolkit.posting.workflow import main as posting_main


def build_parser() -> argparse.ArgumentParser:
    """Build the stable top-level parser and subcommand surface."""

    parser = argparse.ArgumentParser(
        prog="ocr-ci",
        description="Safe CI integration helpers for Open Code Review.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight", help="Validate OCR, GitLab, and LLM access.")
    subparsers.add_parser("configure", help="Write the OCR runtime configuration.")
    subparsers.add_parser("mcp-config", help="Write OCR MCP server configuration.")

    context_parser = subparsers.add_parser(
        "context", help="Generate bounded repository review context."
    )
    context_parser.add_argument(
        "--output",
        default=".review-context/dependencies.md",
        help="Output markdown path.",
    )

    post_parser = subparsers.add_parser("post", help="Publish an OCR result artifact to GitLab.")
    post_parser.add_argument(
        "--result", default="/tmp/ocr-result.json", help="OCR JSON result path."
    )
    post_parser.add_argument("--stderr", default="/tmp/ocr-stderr.log", help="OCR stderr log path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one public subcommand and return its process exit code."""

    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        return preflight.main()
    if args.command == "configure":
        return configure.main()
    if args.command == "mcp-config":
        return mcp_config.configure_mcp_servers()
    if args.command == "context":
        return context_render.main(["--output", args.output])
    if args.command == "post":
        return posting_main([args.result, args.stderr])
    raise AssertionError(f"unhandled command: {args.command}")
