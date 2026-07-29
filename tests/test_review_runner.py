"""Regression tests for safe local OCR execution diagnostics."""

from __future__ import annotations

import io
import os
import stat
import subprocess
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from tests.support import patched_attr, patched_env


def test_run_review_writes_private_artifacts_and_returns_success() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert argv == ["ocr", "review", "--from", "base", "--to", "head"]
        kwargs["stdout"].write(b'{"comments": []}\n')  # type: ignore[union-attr]
        kwargs["stderr"].write(b"review complete\n")  # type: ignore[union-attr]
        return subprocess.CompletedProcess(argv, 0)

    with TemporaryDirectory() as tmp, patched_attr(review_runner.subprocess, "run", fake_run):
        result_path = Path(tmp) / "artifacts" / "result.json"
        stderr_path = Path(tmp) / "artifacts" / "stderr.log"
        exit_code = review_runner.run_review(
            result_path, stderr_path, ["--from", "base", "--to", "head"]
        )

        assert exit_code == 0
        assert result_path.read_text(encoding="utf-8") == '{"comments": []}\n'
        assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(stderr_path.stat().st_mode) == 0o600


def test_run_review_logs_only_bounded_redacted_failure_details() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        kwargs["stderr"].write(  # type: ignore[union-attr]
            b"Authorization: Bearer synthetic-secret-value\nprovider timeout\n"
        )
        return subprocess.CompletedProcess(argv, 1)

    output = io.StringIO()
    with (
        TemporaryDirectory() as tmp,
        patched_env(OCR_LLM_TOKEN="synthetic-secret-value"),
        patched_attr(review_runner.subprocess, "run", fake_run),
        redirect_stderr(output),
    ):
        exit_code = review_runner.run_review(
            Path(tmp) / "result.json", Path(tmp) / "stderr.log", ["--from", "base"]
        )

    assert exit_code == 1
    assert "provider timeout" in output.getvalue()
    assert "synthetic-secret-value" not in output.getvalue()
    assert "Authorization: ***" in output.getvalue()


def test_run_review_rejects_symlink_artifact() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        target.write_text("preserve", encoding="utf-8")
        result_path = Path(tmp) / "result.json"
        os.symlink(target, result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="must not be a symlink"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])

        assert target.read_text(encoding="utf-8") == "preserve"


def test_run_review_tightens_existing_artifact_permissions() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0)

    with TemporaryDirectory() as tmp, patched_attr(review_runner.subprocess, "run", fake_run):
        result_path = Path(tmp) / "result.json"
        stderr_path = Path(tmp) / "stderr.log"
        result_path.write_text("old", encoding="utf-8")
        stderr_path.write_text("old", encoding="utf-8")
        result_path.chmod(0o644)
        stderr_path.chmod(0o644)

        assert review_runner.run_review(result_path, stderr_path, ["--from", "base"]) == 0
        assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(stderr_path.stat().st_mode) == 0o600


def test_run_review_rejects_same_result_and_stderr_path() -> None:
    with TemporaryDirectory() as tmp:
        artifact = Path(tmp) / "artifact"
        with pytest.raises(review_runner.ReviewRunnerError, match="must be different"):
            review_runner.run_review(artifact, artifact, ["--from", "base"])


def test_run_review_rejects_hard_link_artifact_without_truncating() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        target.write_text("preserve", encoding="utf-8")
        result_path = Path(tmp) / "result.json"
        os.link(target, result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="must not have hard links"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])

        assert target.read_text(encoding="utf-8") == "preserve"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO support is unavailable")
def test_run_review_rejects_fifo_artifact_without_blocking() -> None:
    with TemporaryDirectory() as tmp:
        result_path = Path(tmp) / "result.json"
        os.mkfifo(result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="private result artifact"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])


def test_review_refs_require_one_immutable_diff_mode() -> None:
    assert review_runner._review_refs(["--from", "base", "--to=head"]) == (
        review_runner.ReviewRefs("base", "head")
    )
    assert review_runner._review_refs(["-c", "abc123"]) == review_runner.ReviewRefs(
        "abc123^", "abc123"
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="immutable"):
        review_runner._review_refs([])
    with pytest.raises(review_runner.ReviewRunnerError, match="cannot be combined"):
        review_runner._review_refs(["--commit", "abc123", "--from", "base"])


def test_review_rejects_caller_owned_background_file() -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="managed by ocr-ci"):
        review_runner._reject_owned_background(["--background-file", "other.md"])


def test_evidence_review_prepares_internal_context_before_ocr(tmp_path: Path) -> None:
    events: list[object] = []
    artifacts = review_runner.repository_artifacts(tmp_path)

    class Store:
        def write(self, path: Path) -> None:
            events.append(("write", path))

    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), builtin=True),
        ),
        external_servers=(),
        secret_values=(),
    )

    def collect(**kwargs: str) -> Store:
        events.append(("collect", kwargs))
        return Store()

    def run(result: Path, stderr: Path, args: list[str]) -> int:
        events.append(("ocr", result, stderr, args))
        return 7

    with (
        patched_attr(review_runner, "repository_artifacts", lambda: artifacts),
        patched_attr(review_runner, "collect_repository_evidence", collect),
        patched_attr(review_runner.mcp_config, "build_mcp_composition", lambda: composition),
        patched_attr(
            review_runner.mcp_config,
            "apply_mcp_composition",
            lambda _composition: events.append("apply"),
        ),
        patched_attr(review_runner, "render_bootstrap", lambda *_args, **_kwargs: "bootstrap"),
        patched_attr(
            review_runner,
            "write_private_text",
            lambda path, content: events.append(("bootstrap", path, content)),
        ),
        patched_attr(
            review_runner,
            "evidence_summary",
            lambda *_args: {"base": "a" * 40, "head": "b" * 40, "records": 3},
        ),
        patched_attr(review_runner, "run_review", run),
    ):
        result = review_runner.run_evidence_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            ["--from", "base", "--to", "head", "--format", "json"],
        )

    assert result == 7
    assert events[0] == ("collect", {"base_ref": "base", "head_ref": "head"})
    assert events[1] == ("write", artifacts.store)
    assert events[2] == ("bootstrap", artifacts.bootstrap, "bootstrap")
    assert events[3] == "apply"
    assert events[4][0] == "ocr"  # type: ignore[index]
    assert events[4][3][-2:] == [  # type: ignore[index]
        "--background-file",
        str(artifacts.bootstrap),
    ]
