"""Public CLI parser and dispatch contracts."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ocr_toolkit import __version__, cli
from tests.support import patched_attr


class CliTests(unittest.TestCase):
    def test_required_subcommands_parse(self) -> None:
        parser = cli.build_parser()

        self.assertEqual(parser.parse_args(["preflight"]).command, "preflight")
        self.assertEqual(parser.parse_args(["configure"]).command, "configure")
        self.assertEqual(parser.parse_args(["mcp-config"]).command, "mcp-config")
        self.assertEqual(parser.parse_args(["post"]).command, "post")

    def test_review_parses_local_private_artifact_preservation(self) -> None:
        parser = cli.build_parser()

        args = parser.parse_args(
            [
                "review",
                "--result",
                "result.json",
                "--stderr",
                "ocr.log",
                "--preserve-private-artifacts",
                "--",
                "--from",
                "base",
                "--to",
                "head",
            ]
        )

        self.assertTrue(args.preserve_private_artifacts)
        self.assertEqual(args.ocr_args, ["--", "--from", "base", "--to", "head"])

    def test_review_dispatch_forwards_private_artifact_preservation(self) -> None:
        calls: list[tuple[Path, Path, list[str], bool]] = []

        def run_review(
            result: Path,
            stderr: Path,
            arguments: list[str],
            *,
            preserve_private_artifacts: bool,
        ) -> int:
            calls.append((result, stderr, arguments, preserve_private_artifacts))
            return 0

        with patched_attr(cli.review_runner, "run_evidence_review", run_review):
            result = cli.main(
                [
                    "review",
                    "--result",
                    "result.json",
                    "--stderr",
                    "ocr.log",
                    "--preserve-private-artifacts",
                    "--",
                    "--from",
                    "base",
                    "--to",
                    "head",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            calls,
            [(Path("result.json"), Path("ocr.log"), ["--from", "base", "--to", "head"], True)],
        )

    def test_top_level_version_uses_centralized_package_metadata(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            cli.main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(stdout.getvalue().strip(), f"ocr-ci {__version__}")

    def test_post_dispatch_forwards_artifact_paths(self) -> None:
        calls: list[list[str]] = []
        with patched_attr(cli, "posting_main", lambda args: calls.append(args) or 3):
            result = cli.main(["post", "--result", "result.json", "--stderr", "ocr.log"])

        self.assertEqual(result, 3)
        self.assertEqual(calls, [["result.json", "ocr.log"]])

    def test_raw_source_checkout_import_has_no_duplicate_release_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "ocr_toolkit"
            package.mkdir()
            source = Path(__file__).resolve().parents[1] / "src" / "ocr_toolkit" / "__init__.py"
            (package / "__init__.py").write_text(
                source.read_text(encoding="utf-8"), encoding="utf-8"
            )
            command = (
                "import sys; "
                f"sys.path.insert(0, {directory!r}); "
                "import ocr_toolkit; print(ocr_toolkit.__version__)"
            )
            completed = subprocess.run(
                [sys.executable, "-c", command],
                capture_output=True,
                check=True,
                text=True,
            )

        self.assertEqual(completed.stdout.strip(), "0+unknown")


if __name__ == "__main__":
    unittest.main()
