"""Public CLI parser and dispatch contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

from ocr_toolkit import cli
from tests.support import patched_attr


class CliTests(unittest.TestCase):
    def test_required_subcommands_parse(self) -> None:
        parser = cli.build_parser()

        self.assertEqual(parser.parse_args(["preflight"]).command, "preflight")
        self.assertEqual(parser.parse_args(["configure"]).command, "configure")
        self.assertEqual(parser.parse_args(["mcp-config"]).command, "mcp-config")
        self.assertEqual(parser.parse_args(["evidence-serve"]).command, "evidence-serve")
        self.assertEqual(parser.parse_args(["post"]).command, "post")

    def test_post_dispatch_forwards_artifact_paths(self) -> None:
        calls: list[list[str]] = []
        with patched_attr(cli, "posting_main", lambda args: calls.append(args) or 3):
            result = cli.main(["post", "--result", "result.json", "--stderr", "ocr.log"])

        self.assertEqual(result, 3)
        self.assertEqual(calls, [["result.json", "ocr.log"]])

    def test_evidence_serve_dispatches_toolkit_owned_store_path(self) -> None:
        calls: list[Path] = []
        with patched_attr(cli, "serve_evidence", lambda path: calls.append(path) or 4):
            result = cli.main(["evidence-serve"])

        self.assertEqual(result, 4)
        self.assertEqual(calls, [Path.cwd() / ".review-context" / "evidence.json"])


if __name__ == "__main__":
    unittest.main()
