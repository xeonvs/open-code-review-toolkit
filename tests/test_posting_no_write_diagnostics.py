"""No-write diagnostics for unavailable review and receipt identities."""

from __future__ import annotations

import io
import os
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.posting import workflow
from ocr_toolkit.posting.snapshot import BotCommentRefs
from ocr_toolkit.pre_execution import (
    PROTECTED_POLICY_RULE_PATH_PENDING,
    REVIEW_IDENTITY_UNAVAILABLE,
    STATUS_SCHEMA,
    PreExecutionStatus,
    PreExecutionStatusError,
    write_pre_execution_status,
)
from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle, GitLabProviderError
from tests.support import gitlab_config
from tests.test_review_receipt_v11 import _receipt_v11

BASE = "a" * 40
SOURCE = "b" * 40
POLICY = "c" * 40


def _status(reason: str, policy_sha: str | None = None) -> PreExecutionStatus:
    review = _receipt_v11()["review"] if reason == PROTECTED_POLICY_RULE_PATH_PENDING else None
    assert review is None or isinstance(review, dict)
    if review is not None:
        review = {
            **review,
            "source_sha": SOURCE,
            "diff_base_sha": BASE,
            "diff_head_sha": SOURCE,
            "diff_start_sha": POLICY,
            "target_sha": POLICY,
            "policy_sha": POLICY,
        }
    return PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=policy_sha,
        review=review,
    )


def _forbid_write(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("unavailable identity must not write to the merge request")


@pytest.mark.parametrize("receipt", [None, {}, {"schema_version": 11}])
def test_present_invalid_receipt_is_job_only(
    receipt: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", _forbid_write)
    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_results(
            gitlab_config(),
            {
                "status": "complete",
                "comments": [],
                "warnings": [],
                "_ocr_toolkit": receipt,
            },
        )
    assert code == 1
    assert "receipt is invalid" in stderr.getvalue()


def test_missing_ci_source_identity_is_job_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", BASE)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: "")
    monkeypatch.setattr(workflow, "repository_artifacts", _forbid_write)
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)
    assert code == 1
    assert "identity is unavailable" in stderr.getvalue()


def test_no_handoff_exit_never_reads_another_reviews_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_path = tmp_path / "pre-execution-status.json"
    write_pre_execution_status(status_path, _status(PROTECTED_POLICY_RULE_PATH_PENDING, POLICY))
    previous = status_path.read_bytes()
    monkeypatch.setenv("OCR_EXIT_CODE", str(os.EX_TEMPFAIL))
    monkeypatch.setattr(workflow, "load_gitlab_config", _forbid_write)
    monkeypatch.setattr(workflow, "repository_artifacts", _forbid_write)
    monkeypatch.setattr(workflow, "read_pre_execution_status", _forbid_write)
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.main([str(tmp_path / "result.json"), str(tmp_path / "stderr.log")])

    assert code == 1
    assert status_path.read_bytes() == previous
    assert "handoff was not claimed" in stderr.getvalue()


def test_previous_job_cannot_publish_later_jobs_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A's post must reject B's same-revision status after B acquired the lock."""

    status_path = tmp_path / "pre-execution-status.json"
    status = _status(PROTECTED_POLICY_RULE_PATH_PENDING, POLICY)
    assert status.review is not None
    status = PreExecutionStatus(
        schema_version=status.schema_version,
        reason=status.reason,
        diff_base_sha=status.diff_base_sha,
        source_sha=status.source_sha,
        policy_sha=status.policy_sha,
        review={**status.review, "ci_job_id": "22"},
    )
    write_pre_execution_status(status_path, status)
    monkeypatch.setenv("CI_JOB_ID", "11")
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", BASE)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: SOURCE)
    monkeypatch.setattr(
        workflow,
        "repository_artifacts",
        lambda: type("Artifacts", (), {"pre_execution_status": status_path})(),
    )
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)

    assert code == 1
    assert "invocation_changed" in stderr.getvalue()


def test_unavailable_authenticated_diff_status_is_job_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", BASE)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: SOURCE)
    monkeypatch.setattr(
        workflow,
        "repository_artifacts",
        lambda: type(
            "Artifacts", (), {"pre_execution_status": tmp_path / "pre-execution-status.json"}
        )(),
    )
    monkeypatch.setattr(
        workflow,
        "read_pre_execution_status",
        lambda *_args, **_kwargs: _status(REVIEW_IDENTITY_UNAVAILABLE),
    )
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)
    assert code == 1
    assert "diff identity could not be validated" in stderr.getvalue()


@pytest.mark.parametrize("base", ["", "B" * 40, "0" * 40])
def test_unverifiable_ci_diff_base_is_job_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base: str
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", base)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: SOURCE)
    monkeypatch.setattr(workflow, "repository_artifacts", _forbid_write)
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)
    assert code == 1
    assert "identity is unavailable" in stderr.getvalue()


def test_present_invalid_handoff_never_falls_through_to_generic_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "pre-execution-status.json"
    path.write_text("malformed", encoding="utf-8")
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", BASE)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: SOURCE)
    monkeypatch.setattr(
        workflow,
        "repository_artifacts",
        lambda: type("Artifacts", (), {"pre_execution_status": path})(),
    )
    monkeypatch.setattr(
        workflow,
        "read_pre_execution_status",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PreExecutionStatusError("identity does not match")
        ),
    )
    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", _forbid_write)
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)
    assert code == 1
    assert "could not be authenticated" in stderr.getvalue()


@pytest.mark.parametrize("state", ["stale", "unavailable", "closed"])
def test_failure_note_requires_current_open_mr_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", BASE)
    monkeypatch.setattr(workflow, "reviewed_sha", lambda: SOURCE)
    monkeypatch.setattr(
        workflow,
        "repository_artifacts",
        lambda: type("Artifacts", (), {"pre_execution_status": tmp_path / "absent-status.json"})(),
    )

    def lifecycle(*_args: object) -> GitLabMergeRequestLifecycle:
        if state != "closed":
            raise GitLabProviderError("unavailable or changed head")
        return GitLabMergeRequestLifecycle("1", "2", SOURCE, "closed")

    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", lifecycle)
    monkeypatch.setattr(workflow, "post_review_note_bounded", _forbid_write)
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", _forbid_write)
    with redirect_stderr(io.StringIO()) as stderr:
        code = workflow.post_ocr_failure(gitlab_config(), tmp_path / "stderr.log", 2)
    assert code == 1
    assert "Previous review preserved" in stderr.getvalue()


def test_auto_fallback_setup_note_names_protected_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes: list[str] = []

    def capture_note(
        _config: object, _title: str, body: str, _transaction: object
    ) -> dict[str, int]:
        notes.append(body)
        return {"id": 1}

    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, "opened"),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda *_args: BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        capture_note,
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: workflow.ReviewFreshnessResult(POLICY, False),
    )
    monkeypatch.setenv("OCR_STRICT_POSTING", "false")
    assert (
        workflow.post_pre_execution_status(
            gitlab_config(), _status(PROTECTED_POLICY_RULE_PATH_PENDING, POLICY)
        )
        == 0
    )
    assert len(notes) == 1
    assert "protected default-branch policy commit" in notes[0]
    assert "protected default branch" in notes[0]
    assert "protected-target commit" not in notes[0]
