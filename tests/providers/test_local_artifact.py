"""Real local report persistence and failure-path delivery boundaries."""

import io
import os
from pathlib import Path

import pytest

from ocr_toolkit import cli, review_runner
from ocr_toolkit.providers import local
from ocr_toolkit.reporting.model import failed_report


def test_atomic_private_artifact_matches_console(tmp_path: Path) -> None:
    report = failed_report("identity")
    console = io.StringIO()
    local.write_local_report(report, console)
    destination = tmp_path / "report.md"
    local.publish_local_report(report, destination)
    assert destination.read_text() == console.getvalue()
    assert destination.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("kind", ["file", "symlink", "hardlink", "directory", "fifo"])
def test_existing_report_target_is_preserved(tmp_path: Path, kind: str) -> None:
    original = tmp_path / "original"
    original.write_text("caller data")
    destination = tmp_path / "report.md"
    if kind == "file":
        destination.write_text("caller report")
    elif kind == "symlink":
        destination.symlink_to(original)
    elif kind == "hardlink":
        destination.hardlink_to(original)
    elif kind == "directory":
        destination.mkdir()
    else:
        os.mkfifo(destination)
    with pytest.raises(ValueError, match="fresh"):
        local.publish_local_report(failed_report("identity"), destination)
    assert original.read_text() == "caller data"
    assert destination.exists()
    assert not list(tmp_path.glob(".ocr-report-*"))


def test_parent_symlink_is_rejected(tmp_path: Path) -> None:
    parent = tmp_path / "link"
    parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="parent"):
        local.publish_local_report(failed_report("identity"), parent / "report.md")


def test_partial_render_is_never_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(local, "write_local_report", fail)
    with pytest.raises(OSError, match="write failed"):
        local.publish_local_report(failed_report("identity"), tmp_path / "report.md")
    assert list(tmp_path.iterdir()) == []


def test_link_race_preserves_new_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "report.md"
    real_link = os.link

    def race(source: str, target: Path) -> None:
        target.write_text("concurrent caller")
        real_link(source, target)

    monkeypatch.setattr(local.os, "link", race)
    with pytest.raises(FileExistsError):
        local.publish_local_report(failed_report("identity"), destination)
    assert destination.read_text() == "concurrent caller"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("target", ["result.json", "stderr.log"])
def test_output_collision_rejected_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    monkeypatch.setattr(
        review_runner, "_run_evidence_review", lambda *_a, **_kw: pytest.fail("run")
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="destination"):
        review_runner.run_evidence_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            [],
            local=True,
            report_path=tmp_path / target,
        )
    assert list(tmp_path.iterdir()) == []


def test_explicit_report_persists_closed_execution_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(*_args: object, **_kwargs: object) -> int:
        raise review_runner.ReviewRunnerError("execution rejected")

    monkeypatch.setattr(review_runner, "_run_evidence_review", fail)
    destination = tmp_path / "report.md"
    assert (
        cli.main(
            [
                "review",
                "--local",
                "--result",
                str(tmp_path / "result.json"),
                "--stderr",
                str(tmp_path / "stderr.log"),
                "--report",
                str(destination),
            ]
        )
        == 2
    )
    assert destination.read_text() == capsys.readouterr().out
    assert "Review failed" in destination.read_text()


def test_report_requires_local(tmp_path: Path) -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="requires --local"):
        review_runner.run_evidence_review(
            tmp_path / "result", tmp_path / "stderr", [], report_path=tmp_path / "report"
        )
    assert list(tmp_path.iterdir()) == []


def test_artifact_delivery_failure_has_closed_console_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def complete(*_args: object, state: review_runner.ReviewRunState, **_kwargs: object) -> int:
        state.report = failed_report("identity")
        return 0

    def reject(*_args: object) -> None:
        raise OSError("private path detail")

    monkeypatch.setattr(review_runner, "_run_evidence_review", complete)
    monkeypatch.setattr(review_runner, "publish_local_report", reject)
    with pytest.raises(review_runner.ReviewRunnerError, match="artifact output failed"):
        review_runner.run_evidence_review(tmp_path / "result", tmp_path / "stderr", [], local=True)
    output = capsys.readouterr().out
    assert "Stopped at: `reporting`" in output
    assert "private path detail" not in output
    assert list(tmp_path.iterdir()) == []


def test_console_delivery_failure_preserves_complete_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def complete(*_args: object, state: review_runner.ReviewRunState, **_kwargs: object) -> int:
        state.report = failed_report("identity")
        return 0

    def reject(*_args: object) -> None:
        raise BrokenPipeError("closed console")

    monkeypatch.setattr(review_runner, "_run_evidence_review", complete)
    monkeypatch.setattr(review_runner, "write_local_report", reject)
    with pytest.raises(review_runner.ReviewRunnerError, match="report output failed"):
        review_runner.run_evidence_review(tmp_path / "result", tmp_path / "stderr", [], local=True)
    assert "Stopped at: `identity`" in (tmp_path / "result.md").read_text()
