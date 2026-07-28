"""Unified command-line interface for Open Code Review CI helpers."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from ocr_toolkit import configure, mcp_config, preflight, review_runner
from ocr_toolkit.context import render as context_render
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.mcp import serve as serve_evidence
from ocr_toolkit.evidence.parity import compare_legacy_projection, render_parity_json
from ocr_toolkit.evidence.project import render_bootstrap, render_json
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

    context_parser = subparsers.add_parser(
        "context", help="Generate bounded repository review context."
    )
    context_parser.add_argument(
        "--output",
        default=".review-context/dependencies.md",
        help="Output markdown path.",
    )
    evidence_build = subparsers.add_parser(
        "evidence-build", help="Build private evidence and a compact review bootstrap."
    )
    evidence_build.add_argument("--store", required=True, help="Private evidence JSON path.")
    evidence_build.add_argument(
        "--bootstrap", required=True, help="Compact background Markdown path."
    )
    evidence_build.add_argument(
        "--json", dest="json_output", help="Optional deterministic pretty JSON projection."
    )
    evidence_serve = subparsers.add_parser(
        "evidence-serve", help="Serve one private evidence store through read-only MCP."
    )
    evidence_serve.add_argument("--store", required=True, help="Private evidence JSON path.")
    evidence_parity = subparsers.add_parser(
        "evidence-parity", help="Compare temporary legacy facts with typed evidence."
    )
    evidence_parity.add_argument("--store", required=True, help="Private evidence JSON path.")

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
            return review_runner.run_review(Path(args.result), Path(args.stderr), ocr_args)
        except review_runner.ReviewRunnerError as exc:
            print(f"Cannot run Open Code Review: {exc}", file=sys.stderr)
            return 2
    if args.command == "context":
        return context_render.main(["--output", args.output])
    if args.command == "evidence-build":
        store = collect_repository_evidence()
        store.write(Path(args.store))
        _write_private(Path(args.bootstrap), render_bootstrap(store))
        if args.json_output:
            _write_private(Path(args.json_output), render_json(store, pretty=True))
        return 0
    if args.command == "evidence-serve":
        return serve_evidence(Path(args.store))
    if args.command == "evidence-parity":
        from ocr_toolkit.evidence.store import EvidenceStore

        store = EvidenceStore.read(Path(args.store))
        report = render_parity_json(store)
        sys.stdout.write(report)
        return 0 if compare_legacy_projection(store).complete else 1
    if args.command == "post":
        return posting_main([args.result, args.stderr])
    raise AssertionError(f"unhandled command: {args.command}")


def _write_private(path: Path, content: str) -> None:
    """Write one generated projection with owner-only permissions."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", opener=_private_opener) as descriptor:
        descriptor.write(content)


def _private_opener(path: str, flags: int) -> int:
    """Open a projection without a transient permissive mode."""

    return os.open(path, flags, 0o600)
