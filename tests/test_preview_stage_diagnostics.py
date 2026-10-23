"""Proven pre-model preview failures have closed identity-bound outcomes."""

from __future__ import annotations

from pathlib import Path

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts


def test_unclassified_preview_diagnostics_never_start_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    calls: list[str] = []
    monkeypatch.setattr(
        review_runner,
        "_qualify_review_background",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            review_runner.BackgroundPreviewUnclassified(2)
        ),
    )
    monkeypatch.setattr(
        review_runner,
        "run_review",
        lambda *_args, **_kwargs: calls.append("model"),
    )
    base, head, policy = "a" * 40, "b" * 40, "c" * 40
    code, _qualification = review_runner._run_background_qualified_review(
        tmp_path / "result.json",
        tmp_path / "stderr.log",
        [],
        ocr_binary="/private/ocr",
        session_home=home,
        artifacts=artifacts,
        refs=review_runner.ReviewRefs(base, head),
        identity=review_runner.ReviewIdentity(head, policy, None, "off", None, policy, "local"),
    )
    assert code == 2 and not calls
    assert not artifacts.pre_execution_status.exists()


def test_unknown_success_stderr_is_not_a_qualified_preview() -> None:
    with pytest.raises(review_runner.BackgroundPreviewUnclassified) as error:
        review_runner._parse_background_preview(
            returncode=0,
            stderr=b"[ocr] WARNING: cannot read file source at ref unknown: exit status 128\n",
        )
    assert error.value.diagnostic_count == 1
