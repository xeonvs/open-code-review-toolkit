"""Public CLI parser and dispatch contracts."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ocr_toolkit import __version__, cli
from tests.support import patched_attr


class CliTests(unittest.TestCase):
    """Bind public command parsing and dispatch to the intended runtime owner."""

    def test_required_subcommands_parse(self) -> None:
        parser = cli.build_parser()

        self.assertEqual(parser.parse_args(["preflight"]).command, "preflight")
        self.assertEqual(parser.parse_args(["configure"]).command, "configure")
        self.assertEqual(parser.parse_args(["mcp-config"]).command, "mcp-config")
        self.assertEqual(parser.parse_args(["post"]).command, "post")
        self.assertEqual(
            parser.parse_args(
                ["dlp-audit", "--state-dir", "/synthetic", "scan", "--stdin"]
            ).command,
            "dlp-audit",
        )

    def test_invalid_top_level_command_keeps_normal_cli_error(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()) as stderr,
            self.assertRaises(SystemExit) as raised,
        ):
            cli.main(["unknown-command"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_review_rejects_removed_private_retention_option(self) -> None:
        """Keep the obsolete retention interface absent without a compatibility alias."""
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(
                [
                    "review",
                    "--result",
                    "result.json",
                    "--stderr",
                    "ocr.log",
                    "--preserve-private-artifacts",
                ]
            )
        self.assertEqual(raised.exception.code, 2)

    def test_review_dispatch_forwards_local_debug_directory(self) -> None:
        """Forward one explicit local diagnostics directory through the normal runner."""
        calls: list[tuple[Path, Path, list[str], bool, Path]] = []

        def run_review(
            result: Path, stderr: Path, arguments: list[str], *, local: bool, debug_dir: Path
        ) -> int:
            """Observe the public CLI handoff without executing a model review."""
            calls.append((result, stderr, arguments, local, debug_dir))
            return 0

        with patched_attr(cli.review_runner, "run_evidence_review", run_review):
            result = cli.main(
                [
                    "review",
                    "--result",
                    "result.json",
                    "--stderr",
                    "ocr.log",
                    "--local",
                    "--debug-dir",
                    "private-debug",
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
            [
                (
                    Path("result.json"),
                    Path("ocr.log"),
                    ["--from", "base", "--to", "head"],
                    True,
                    Path("private-debug"),
                )
            ],
        )

    def test_review_without_private_handoff_has_distinct_exit(self) -> None:
        def no_handoff(*_args: object, **_kwargs: object) -> int:
            raise cli.review_runner.ReviewRunnerNoHandoff("another review owns this checkout")

        with (
            patched_attr(cli.review_runner, "run_evidence_review", no_handoff),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            result = cli.main(["review", "--result", "result.json", "--stderr", "ocr.log"])

        self.assertEqual(result, os.EX_TEMPFAIL)
        self.assertIn("another review owns this checkout", stderr.getvalue())

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
