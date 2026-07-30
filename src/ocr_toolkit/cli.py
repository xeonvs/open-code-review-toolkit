"""Unified command-line interface for Open Code Review CI helpers."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ocr_toolkit import configure, mcp_config, preflight, review_runner
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
    review_parser = subparsers.add_parser(
        "review", help="Run OCR with private artifacts and safe failure diagnostics."
    )
    review_parser.add_argument("--result", required=True, help="OCR JSON output path.")
    review_parser.add_argument("--stderr", required=True, help="Full OCR stderr artifact path.")
    review_parser.add_argument(
        "ocr_args", nargs=argparse.REMAINDER, help="OCR review arguments after --."
    )

    post_parser = subparsers.add_parser("post", help="Publish an OCR result artifact to GitLab.")
    post_parser.add_argument(
        # The public GitLab example writes this fixed path inside an isolated CI job.
        "--result",
        default="/tmp/ocr-result.json",  # nosec B108
        help="OCR JSON result path.",
    )
    post_parser.add_argument(
        # The file contains only the current job's OCR stderr and is never shared.
        "--stderr",
        default="/tmp/ocr-stderr.log",  # nosec B108
        help="OCR stderr log path.",
    )
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
    if args.command == "review":
        ocr_args = args.ocr_args[1:] if args.ocr_args[:1] == ["--"] else args.ocr_args
        try:
            return review_runner.run_evidence_review(Path(args.result), Path(args.stderr), ocr_args)
        except review_runner.ReviewRunnerError as exc:
            print(f"Cannot run Open Code Review: {exc}", file=sys.stderr)
            return 2
    if args.command == "post":
        return posting_main([args.result, args.stderr])
    raise AssertionError(f"unhandled command: {args.command}")
