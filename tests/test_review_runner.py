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
