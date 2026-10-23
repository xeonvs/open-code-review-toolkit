"""Publication and approval boundaries for the exact v11 GitLab review identity."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.posting import formatting, freshness, gitlab, gitlab_approval, workflow
from ocr_toolkit.posting.approval import (
    ApprovalEligibility,
    ApprovalResult,
    ApprovalStatus,
)
from ocr_toolkit.posting.snapshot import BotCommentRefs
from ocr_toolkit.posting.transaction import PostingTransaction
from ocr_toolkit.pre_execution import (
    EVIDENCE_PREFLIGHT_STAGE,
    GITLINK_PREVIEW_UNSUPPORTED,
    OCR_PREVIEW_STAGE,
    PROTECTED_POLICY_RULE_PATH_PENDING,
    STATUS_SCHEMA,
    PreExecutionStatus,
)
from ocr_toolkit.providers.gitlab import (
    GitLabMergeRequestLifecycle,
    GitLabMergeRequestTerminal,
    GitLabProviderError,
)
from ocr_toolkit.result_contract import ReviewOutcome
from ocr_toolkit.review_receipt import ReceiptReviewIdentity, validated_review_identity
from tests.support import gitlab_config, review_receipt_v8
from tests.test_review_receipt_v11 import _receipt_v11


def _identity(*, unprotected: bool = False) -> ReceiptReviewIdentity:
    receipt = _receipt_v11(target_protection="unprotected" if unprotected else "protected")
    identity = validated_review_identity(receipt)
    assert identity is not None
    return identity


def _outcome(kind: str) -> ReviewOutcome:
    return ReviewOutcome(
        status="failed" if kind == "failed" else "partial" if kind == "partial" else "complete",
        kind=kind,  # type: ignore[arg-type]
        budget_exceeded=False,
        manifest_present=True,
        selected_count=1,
        completed_count=0 if kind == "failed" else 1,
        failed_count=1 if kind in {"partial", "failed"} else 0,
    )


def _result(kind: str, *, comments: bool = False) -> dict[str, Any]:
    return {
        "status": "failed" if kind == "failed" else "complete",
        "comments": (
            [{"path": "module.py", "line": 1, "content": "Review this line."}] if comments else []
        ),
        "warnings": [],
        "_ocr_toolkit": _receipt_v11(),
    }


def _pre_execution_status(reason: str) -> PreExecutionStatus:
    review = _receipt_v11()["review"]
    assert isinstance(review, dict)
    return PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        stage=(
            OCR_PREVIEW_STAGE if reason == GITLINK_PREVIEW_UNSUPPORTED else EVIDENCE_PREFLIGHT_STAGE
        ),
        review=review,
    )


@pytest.mark.parametrize(
    ("kind", "has_comments"),
    (("clean", False), ("clean", True), ("partial", False), ("failed", False)),
)
@pytest.mark.parametrize("drift", ("target_changed", "policy_changed", "diff_changed"))
def test_stale_v11_result_never_reaches_normal_or_failure_write(
    kind: str, has_comments: bool, drift: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same-H target, policy, or diff drift preserves the previous review."""

    calls: list[str] = []
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome(kind))
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: (_ for _ in ()).throw(freshness.ReviewFreshnessStale(drift)),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: calls.append("note"),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_discussion",
        lambda *_args, **_kwargs: calls.append("discussion"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: calls.append("cleanup"),
    )

    assert workflow.post_results(gitlab_config(), _result(kind, comments=has_comments)) == 1
    assert calls == []


def test_invalid_schema_with_valid_v11_receipt_is_job_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid receipt cannot authorize notes for a malformed result body."""

    result = _result("clean")
    result["comments"] = "invalid"
    monkeypatch.setattr(
        workflow, "post_review_note_bounded", lambda *_a, **_k: pytest.fail("write")
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda *_a: pytest.fail("read")
    )
    monkeypatch.setenv("OCR_STRICT_POSTING", "false")

    assert workflow.post_results(gitlab_config(), result) == 1


def test_other_job_result_cannot_be_published_after_shared_handoff_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A's post rejects B's valid same-revision receipt before any provider write."""

    result = _result("clean")
    result["_ocr_toolkit"]["review"]["ci_job_id"] = "22"
    monkeypatch.setenv("CI_JOB_ID", "11")
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("clean"))
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
    )
    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: pytest.fail("provider contacted for another job's result"),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: pytest.fail("another job's result was published"),
    )

    assert workflow.post_results(gitlab_config(), result) == 1


def test_receiptless_direct_result_still_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the legacy direct valid-result entry point operational."""

    writes: list[str] = []
    for key in (
        "GITLAB_CI",
        "CI_PROJECT_ID",
        "CI_COMMIT_SHA",
        "CI_MERGE_REQUEST_EVENT_TYPE",
        "CI_MERGE_REQUEST_IID",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda _config: BotCommentRefs(),
    )
    monkeypatch.setattr(
        workflow,
        "publication_lifecycle_or_exit",
        lambda *_args: (GitLabMergeRequestLifecycle("1", "2", "a" * 40, "opened"), None),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: writes.append("summary") or {"id": 1},
    )
    monkeypatch.setattr(
        workflow,
        "finalize_review_approval",
        lambda *_args, **_kwargs: writes.append("finalize") or 0,
    )

    assert workflow.post_results(gitlab_config(), {"comments": [], "warnings": []}) == 0
    assert writes == ["summary", "finalize"]


@pytest.mark.parametrize(
    "ci_marker", (None, "GITLAB_CI", "CI_MERGE_REQUEST_EVENT_TYPE", "CI_PIPELINE_ID")
)
def test_cli_receiptless_result_distinguishes_standalone_from_ci(
    ci_marker: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target config alone permits direct posting; any CI marker requires v11."""

    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"comments": [], "warnings": []}), encoding="utf-8")
    for key in (
        "GITLAB_CI",
        "CI_COMMIT_SHA",
        "CI_MERGE_REQUEST_EVENT_TYPE",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA",
        "CI_PIPELINE_ID",
        "CI_JOB_ID",
        "CI_PIPELINE_SOURCE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CI_SERVER_URL", "https://gitlab.example.com")
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.setenv("GITLAB_API_TOKEN", "synthetic-token")
    monkeypatch.setenv("OCR_EXIT_CODE", "0")
    monkeypatch.setenv("OCR_STRICT_POSTING", "false")
    if ci_marker is not None:
        monkeypatch.setenv(ci_marker, "" if ci_marker == "CI_MERGE_REQUEST_EVENT_TYPE" else "true")
    monkeypatch.setattr(gitlab, "fetch_posting_identity", lambda *_args: (7, "ocr_bot"))
    writes: list[str] = []
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda _config: writes.append("snapshot") or BotCommentRefs(),
    )
    monkeypatch.setattr(
        workflow,
        "publication_lifecycle_or_exit",
        lambda *_args: (GitLabMergeRequestLifecycle("1", "2", "a" * 40, "opened"), None),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: writes.append("summary") or {"id": 1},
    )
    monkeypatch.setattr(
        workflow,
        "finalize_review_approval",
        lambda *_args, **_kwargs: writes.append("finalize") or 0,
    )

    actual = workflow.main([str(result_path), str(tmp_path / "stderr.log")])
    if ci_marker is None:
        assert actual == 0
        assert writes == ["snapshot", "summary", "finalize"]
    else:
        assert actual == 1
        assert writes == []


@pytest.mark.parametrize("event_type", ("detached", "merged_result", ""))
def test_receiptless_ci_result_cannot_post_with_same_source_head(
    event_type: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without v11, even a malformed CI job cannot prove B, target, or diff version."""

    monkeypatch.setenv("CI_MERGE_REQUEST_EVENT_TYPE", event_type)
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.setenv("CI_COMMIT_SHA", "a" * 40)
    monkeypatch.setenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "a" * 40)
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", "c" * 40)
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda *_args: pytest.fail("old state must not be read"),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: pytest.fail("no result note is authorized"),
    )
    monkeypatch.setattr(
        workflow,
        "publication_lifecycle_or_exit",
        lambda *_args: pytest.fail("H-only lifecycle check is insufficient"),
    )
    monkeypatch.setenv("OCR_STRICT_POSTING", "false")

    assert workflow.post_results(gitlab_config(), {"comments": [], "warnings": []}) == 1


def test_v11_findings_use_exact_receipt_diff_tuple_and_protected_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inline positions use the reviewed B/start/H, even when B differs from T."""

    receipt = _receipt_v11(target_protection="unprotected")
    identity = validated_review_identity(receipt)
    assert identity is not None
    observed_refs: list[dict[str, str]] = []
    notes: list[str] = []
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("clean"))
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult(identity.policy_sha, False),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow,
        "get_diff_refs",
        lambda _config: pytest.fail("v11 must not choose a version by head SHA alone"),
    )

    def discussion(*_args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
        observed_refs.append(kwargs["refs"])
        return gitlab.GitLabWriteResult("posted")

    def note(_config: Any, _title: str, body: str, _transaction: Any) -> dict[str, int]:
        notes.append(body)
        return {"id": len(notes)}

    monkeypatch.setattr(workflow, "post_review_discussion", discussion)
    monkeypatch.setattr(workflow, "post_review_note_bounded", note)
    monkeypatch.setattr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0)
    result = _result("clean", comments=True)
    result["_ocr_toolkit"] = receipt

    assert workflow.post_results(gitlab_config(), result) == 0
    assert observed_refs == [
        {
            "base_sha": identity.diff_base_sha,
            "start_sha": identity.diff_start_sha,
            "head_sha": identity.diff_head_sha,
        }
    ]
    assert identity.diff_base_sha != identity.target_sha
    assert len(notes) == 1
    assert "protected policy anchor" in notes[0]
    assert identity.policy_sha in notes[0]
    assert "comment-only" in notes[0]
    assert "limited, comment-only mode" not in notes[0]
    assert identity.policy_branch is not None
    assert identity.policy_branch not in notes[0]


def test_v11_no_findings_summary_uses_protected_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clean fallback still explains target protection and immutable authority."""

    receipt = _receipt_v11(target_protection="unprotected")
    notes: list[str] = []
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("clean"))
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult("f" * 40, True),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
    )

    def note(_config: Any, _title: str, body: str, _transaction: Any) -> dict[str, int]:
        notes.append(body)
        return {"id": 1}

    monkeypatch.setattr(workflow, "post_review_note_bounded", note)
    monkeypatch.setattr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0)
    result = _result("clean")
    result["_ocr_toolkit"] = receipt

    assert workflow.post_results(gitlab_config(), result) == 0
    assert len(notes) == 1
    assert "protected policy anchor" in notes[0]
    assert receipt["review"]["policy_sha"] in notes[0]
    assert "f" * 40 not in notes[0]
    assert "limited, comment-only mode" not in notes[0]


def test_current_partial_v11_posts_summary_without_replacing_old_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A current partial review can report coverage while keeping prior findings."""

    calls: list[str] = []
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("partial"))
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult("b" * 40, False),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: BotCommentRefs()
    )

    def note(*_args: Any) -> dict[str, int]:
        calls.append("summary")
        return {"id": 1}

    monkeypatch.setattr(workflow, "post_review_note_bounded", note)
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)

    def preserve(_config: Any, _previous: Any, outcome: ReviewOutcome, **_kwargs: Any) -> None:
        calls.append(f"finalize-{outcome.kind}")

    monkeypatch.setattr(workflow, "finalize_previous_review_state", preserve)

    assert workflow.post_results(gitlab_config(), _result("partial")) == 0
    assert calls == ["summary", "finalize-partial"]


def test_current_failed_v11_is_job_only_after_freshness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed result status is bound to the live tuple and does not collect old notes."""

    calls: list[str] = []
    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("failed"))
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: calls.append("freshness"),
    )
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda _config: pytest.fail("failed result must not collect old review state"),
    )

    def failure_note(*_args: Any) -> dict[str, int]:
        calls.append("failure-note")
        return {"id": 1}

    monkeypatch.setattr(workflow, "post_review_note_bounded", failure_note)
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)

    assert workflow.post_results(gitlab_config(), _result("failed")) == 1
    assert calls == ["freshness"]


@pytest.mark.parametrize(
    "changes",
    (
        {"CI_MERGE_REQUEST_EVENT_TYPE": "merged_result"},
        {"CI_MERGE_REQUEST_EVENT_TYPE": "merge_train"},
        {"CI_COMMIT_SHA": "f" * 40},
        {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "f" * 40},
        {"CI_MERGE_REQUEST_DIFF_BASE_SHA": "f" * 40},
        {"CI_PROJECT_ID": "99"},
        {"CI_MERGE_REQUEST_IID": "99"},
    ),
)
def test_transferred_receipt_is_rejected_before_provider_read(
    changes: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid receipt cannot travel to another job, MR, CI diff, or pipeline kind."""

    identity = _identity()
    environment = {
        "CI_PROJECT_ID": "1",
        "CI_MERGE_REQUEST_IID": "2",
        "CI_MERGE_REQUEST_EVENT_TYPE": "detached",
        "CI_COMMIT_SHA": identity.source_sha,
        "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA": identity.diff_base_sha,
    }
    for key, value in (environment | changes).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: pytest.fail("CI mismatch must stop before provider read"),
    )

    assert workflow.publication_freshness_or_exit(gitlab_config(), identity) == 1


@pytest.mark.parametrize(
    "error",
    (
        GitLabProviderError("missing diff facts"),
        GitLabMergeRequestTerminal(GitLabMergeRequestLifecycle("1", "2", "a" * 40, "merged")),
    ),
)
def test_missing_provider_facts_or_terminal_mr_block_normal_write(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unavailable provider identity and terminal MR preserve the old publication."""

    identity = _identity()
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.setenv("CI_MERGE_REQUEST_EVENT_TYPE", "detached")
    monkeypatch.setenv("CI_COMMIT_SHA", identity.source_sha)
    monkeypatch.setenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "")
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", identity.diff_base_sha or "")
    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    assert workflow.publication_freshness_or_exit(gitlab_config(), identity) == 1


def test_config_receipt_mismatch_stops_before_provider_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _identity()
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: pytest.fail("config mismatch must stop before provider read"),
    )
    wrong = replace(gitlab_config(), project_id="99")
    assert workflow.publication_freshness_or_exit(wrong, identity) == 1


@pytest.mark.parametrize("reason", ("target_changed", "diff_changed", "authority_changed"))
def test_approval_rechecks_staleness_after_sync_before_write(
    reason: freshness.FreshnessReason, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retarget, diff, or protection drift cannot create an approval."""

    calls: list[str] = []

    def synchronized(
        *_args: Any, **_kwargs: Any
    ) -> tuple[gitlab_approval.GitLabApprovalState, None]:
        calls.append("sync")
        return gitlab_approval.GitLabApprovalState(False, 41), None

    monkeypatch.setattr(gitlab_approval, "wait_for_synchronized_approval_state", synchronized)
    monkeypatch.setattr(
        gitlab,
        "approve_merge_request",
        lambda *_args: calls.append("approve"),
    )

    def stale() -> None:
        calls.append("freshness")
        raise freshness.ReviewFreshnessStale(reason)

    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=_identity(),
        freshness_check=stale,
    )

    assert calls == ["sync", "freshness"]
    assert result.result.status is ApprovalStatus.SKIPPED
    assert result.preserve_previous_review


def test_approval_unavailable_or_terminal_never_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider uncertainty after sync has the same previous-review ownership boundary."""

    writes: list[str] = []
    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: (gitlab_approval.GitLabApprovalState(False, 41), None),
    )
    monkeypatch.setattr(
        gitlab,
        "approve_merge_request",
        lambda *_args: writes.append("approve"),
    )
    for error in (
        freshness.ReviewFreshnessUnavailable("provider_unavailable"),
        GitLabMergeRequestTerminal(GitLabMergeRequestLifecycle("1", "2", "a" * 40, "closed")),
    ):

        def unavailable() -> None:
            raise error

        result = gitlab_approval.execute_approval(
            gitlab_config(),
            ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
            "a" * 40,
            41,
            review_identity=_identity(),
            freshness_check=unavailable,
        )
        assert result.preserve_previous_review
    assert writes == []


def test_unprotected_target_cannot_approve_even_if_eligibility_is_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: pytest.fail("unprotected target must not sync approval"),
    )
    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=_identity(unprotected=True),
        freshness_check=lambda: None,
    )
    assert result.result.status is ApprovalStatus.SKIPPED
    assert "unprotected" in result.result.reason


@pytest.mark.parametrize("receipt", (None, review_receipt_v8()))
def test_eligible_approval_requires_current_v11_identity_before_sync_or_write(
    receipt: dict[str, Any] | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy receipts and missing identity cannot bypass the adapter directly."""

    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: pytest.fail("missing v11 identity must stop before sync"),
    )
    monkeypatch.setattr(
        gitlab,
        "approve_merge_request",
        lambda *_args: pytest.fail("missing v11 identity must never approve"),
    )
    identity = validated_review_identity(receipt)
    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=identity,
        freshness_check=lambda: None,
    )
    assert result.result.status is ApprovalStatus.FAILED
    assert result.preserve_previous_review


def test_current_protected_approval_checks_freshness_between_sync_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The only approval path rechecks the exact receipt before SHA-bound PUT."""

    calls: list[str] = []

    def synchronized(
        *_args: Any, **_kwargs: Any
    ) -> tuple[gitlab_approval.GitLabApprovalState, None]:
        calls.append("sync")
        own_approved = calls.count("sync") == 2
        return gitlab_approval.GitLabApprovalState(own_approved, 41), None

    def approved(*_args: Any) -> gitlab.GitLabWriteResult:
        calls.append("approve")
        return gitlab.GitLabWriteResult("posted")

    monkeypatch.setattr(gitlab_approval, "wait_for_synchronized_approval_state", synchronized)
    monkeypatch.setattr(gitlab, "approve_merge_request", approved)
    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=_identity(),
        freshness_check=lambda: calls.append("freshness"),
    )

    assert calls == ["sync", "freshness", "approve", "sync"]
    assert result.result.status is ApprovalStatus.APPROVED
    assert not result.preserve_previous_review


@pytest.mark.parametrize(("sha", "author"), (("f" * 40, 41), ("a" * 40, 99)))
def test_approval_refuses_receipt_source_or_author_substitution(
    sha: str, author: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: pytest.fail("substitution must stop before sync"),
    )
    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        sha,
        author,
        review_identity=_identity(),
        freshness_check=lambda: None,
    )
    assert result.preserve_previous_review
    assert result.result.status is ApprovalStatus.SKIPPED


def test_late_stale_approval_rolls_back_only_current_run_and_keeps_prior_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def publish(*_args: Any) -> bool:
        calls.append("publish")
        return True

    monkeypatch.setattr(workflow, "finalize_posting", publish)
    monkeypatch.setattr(workflow, "publication_freshness_or_exit", lambda *_args: None)
    monkeypatch.setattr(
        workflow,
        "execute_approval",
        lambda *_args, **_kwargs: gitlab_approval.ApprovalExecution(
            ApprovalResult(ApprovalStatus.SKIPPED, "stale"), preserve_previous_review=True
        ),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: calls.append("rollback-current"),
    )
    monkeypatch.setattr(
        workflow,
        "replace_current_summary",
        lambda *_args: pytest.fail("stale result must not update summary"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("prior review must be preserved"),
    )
    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(),
            _outcome("clean"),
            PostingTransaction(),
            ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
            "a" * 40,
            41,
            "f" * 32,
            lambda _approval: "summary",
            review_identity=_identity(),
        )
        == 1
    )
    assert calls == ["publish", "rollback-current"]


@pytest.mark.parametrize("next_write", ("fallback", "omitted", "summary"))
def test_mid_publication_drift_stops_next_write_and_rolls_back_current_run(
    next_write: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live v11 drift between notes cannot publish the rest of an old review."""

    stale = False
    writes: list[str] = []
    previous = BotCommentRefs(plain_note_ids=[91])

    def freshness_check(*_args: Any) -> None:
        if stale:
            raise freshness.ReviewFreshnessStale("target_changed")

    def discussion(*_args: Any, **_kwargs: Any) -> gitlab.GitLabWriteResult:
        nonlocal stale
        writes.append("inline")
        stale = True
        return gitlab.GitLabWriteResult("posted")

    def note(*_args: Any, **_kwargs: Any) -> dict[str, int]:
        writes.append("note")
        return {"id": 1}

    monkeypatch.setattr(workflow, "parse_result_outcome", lambda _result: _outcome("clean"))
    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda _config: previous)
    monkeypatch.setattr(workflow, "post_review_discussion", discussion)
    monkeypatch.setattr(workflow, "post_review_note_bounded", note)
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda _config, refs, _transaction: writes.append(
            "rollback-current" if refs is previous else "wrong-baseline"
        ),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("stale review must preserve previous notes"),
    )
    comments = [
        {"path": "module.py", "line": 1, "content": "First finding."},
    ]
    if next_write == "fallback":
        comments.append({"path": "module.py", "content": "Fallback finding."})
    elif next_write == "omitted":
        comments.append({"path": "module.py", "line": 2, "content": "Omitted finding."})
        monkeypatch.setattr(workflow, "max_post_comments", lambda: 1)
    result = _result("clean")
    result["comments"] = comments

    assert workflow.post_results(gitlab_config(), result) == 1
    assert writes == ["inline", "rollback-current"]


@pytest.mark.parametrize("cleanup_confirmed", [True, False])
def test_drift_between_draft_publications_stops_remaining_writes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cleanup_confirmed: bool,
) -> None:
    stale = False
    writes: list[str] = []
    transaction = PostingTransaction()
    assert transaction.record_draft(11)
    assert transaction.record_draft(12)

    def freshness_check(*_args: Any) -> None:
        if stale:
            raise freshness.ReviewFreshnessStale("source_changed")

    def publish(_config: Any, note_id: int) -> bool:
        nonlocal stale
        writes.append(f"publish-{note_id}")
        stale = True
        return True

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(workflow, "post_mode", lambda: "draft")
    monkeypatch.setattr(workflow.gitlab_api, "publish_draft_note", publish)
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_draft_note",
        lambda _config, note_id: writes.append(f"delete-draft-{note_id}") or cleanup_confirmed,
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda _config, _previous, current: writes.append(f"rollback-{current.draft_note_ids!r}"),
    )
    monkeypatch.setattr(
        workflow,
        "execute_approval",
        lambda *_args, **_kwargs: pytest.fail("stale review must not approve"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("stale review must preserve previous notes"),
    )

    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(plain_note_ids=[91]),
            _outcome("clean"),
            transaction,
            ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
            "a" * 40,
            41,
            "f" * 32,
            lambda _approval: "summary",
            review_identity=_identity(),
        )
        == 1
    )
    assert writes == ["publish-11", "delete-draft-12"]
    assert ("unattempted draft cleanup could not be confirmed" in capsys.readouterr().err) is (
        not cleanup_confirmed
    )


def test_draft_publish_failure_after_first_visible_note_preserves_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = PostingTransaction()
    assert transaction.record_draft(11)
    assert transaction.record_draft(12)
    assert transaction.record_draft(13)
    writes: list[str] = []
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult("b" * 40, False),
    )
    monkeypatch.setattr(workflow, "post_mode", lambda: "draft")
    monkeypatch.setattr(
        workflow.gitlab_api,
        "publish_draft_note",
        lambda _config, note_id: writes.append(f"publish-{note_id}") or note_id == 11,
    )
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_draft_note",
        lambda _config, note_id: writes.append(f"delete-draft-{note_id}") or True,
    )
    monkeypatch.setattr(
        workflow,
        "publish_failure_exit",
        lambda _config, current: writes.append(f"failure-{current.draft_note_ids!r}") or 1,
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("failed publish must preserve prior notes"),
    )
    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(plain_note_ids=[91]),
            _outcome("clean"),
            transaction,
            ApprovalEligibility(False, ApprovalResult(ApprovalStatus.NOT_ELIGIBLE, "partial")),
            "a" * 40,
            41,
            "f" * 32,
            lambda _approval: "summary",
            review_identity=_identity(),
        )
        == 1
    )
    assert writes == ["publish-11", "publish-12", "delete-draft-13"]


def test_first_draft_publish_failure_retains_ambiguous_attempt_and_cleans_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = PostingTransaction()
    assert transaction.record_draft(11)
    assert transaction.record_draft(12)
    writes: list[str] = []
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult("b" * 40, False),
    )
    monkeypatch.setattr(workflow, "post_mode", lambda: "draft")
    monkeypatch.setattr(
        workflow.gitlab_api,
        "publish_draft_note",
        lambda _config, note_id: writes.append(f"publish-{note_id}") or False,
    )
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_draft_note",
        lambda _config, note_id: writes.append(f"delete-draft-{note_id}") or True,
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: pytest.fail("attempted publication cannot be rolled back by draft ID"),
    )

    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(plain_note_ids=[91]),
            _outcome("clean"),
            transaction,
            ApprovalEligibility(False, ApprovalResult(ApprovalStatus.NOT_ELIGIBLE, "partial")),
            "a" * 40,
            41,
            "f" * 32,
            lambda _approval: "summary",
            review_identity=_identity(),
        )
        == 1
    )
    assert writes == ["publish-11", "delete-draft-12"]


def test_drift_during_summary_lookup_blocks_final_update_and_old_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = False
    writes: list[str] = []

    def freshness_check(*_args: Any) -> None:
        if stale:
            raise freshness.ReviewFreshnessStale("target_changed")

    def lookup(*_args: Any) -> int:
        nonlocal stale
        stale = True
        return 21

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(
        workflow,
        "execute_approval",
        lambda *_args, **_kwargs: gitlab_approval.ApprovalExecution(
            ApprovalResult(ApprovalStatus.APPROVED, "approved")
        ),
    )
    monkeypatch.setattr(workflow, "find_current_summary_note", lookup)
    monkeypatch.setattr(
        workflow,
        "update_plain_note",
        lambda *_args: pytest.fail("stale summary must not be updated"),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: writes.append("rollback-current"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("previous review must be preserved"),
    )

    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(plain_note_ids=[91]),
            _outcome("clean"),
            PostingTransaction(),
            ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
            "a" * 40,
            41,
            "f" * 32,
            lambda approval: approval.status.value,
            review_identity=_identity(),
        )
        == 1
    )
    assert writes == ["rollback-current"]


def test_v11_unconfirmed_summary_update_preserves_previous_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A final summary write failure cannot certify old-note replacement."""

    writes: list[str] = []
    monkeypatch.setattr(workflow, "post_mode", lambda: "direct")
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(workflow, "publication_freshness_or_exit", lambda *_args: None)
    monkeypatch.setattr(
        workflow,
        "execute_approval",
        lambda *_args, **_kwargs: gitlab_approval.ApprovalExecution(
            ApprovalResult(ApprovalStatus.SKIPPED, "already approved")
        ),
    )
    monkeypatch.setattr(
        workflow,
        "replace_current_summary",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: writes.append("rollback-current"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("old state must be preserved"),
    )
    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(plain_note_ids=[91]),
            _outcome("clean"),
            PostingTransaction(),
            ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
            "a" * 40,
            41,
            "f" * 32,
            lambda approval: approval.status.value,
            review_identity=_identity(),
        )
        == 1
    )
    assert writes == ["rollback-current"]


def test_drift_before_previous_cleanup_preserves_old_notes_and_resolutions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale = True
    writes: list[str] = []
    previous = BotCommentRefs(plain_note_ids=[91], discussions_to_resolve=["prior-thread"])

    def freshness_check(*_args: Any) -> None:
        if stale:
            raise freshness.ReviewFreshnessStale("target_changed")

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda *_args: pytest.fail("stale review must not delete old notes"),
    )
    monkeypatch.setattr(
        workflow,
        "resolve_discussion",
        lambda *_args: pytest.fail("stale review must not resolve old discussions"),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: writes.append("rollback-current"),
    )
    assert not workflow.finalize_previous_review_state(
        gitlab_config(),
        previous,
        _outcome("clean"),
        review_identity=_identity(),
        transaction=PostingTransaction(),
    )
    assert writes == ["rollback-current"]


def test_drift_between_previous_cleanup_writes_stops_remaining_mutations(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stale = False
    writes: list[str] = []
    previous = BotCommentRefs(plain_note_ids=[91, 92], discussions_to_resolve=["prior-thread"])

    def freshness_check(*_args: Any) -> None:
        if stale:
            raise freshness.ReviewFreshnessStale("source_changed")

    def delete_plain(_config: Any, note_id: int) -> bool:
        nonlocal stale
        writes.append(f"delete-{note_id}")
        stale = True
        return True

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(workflow.gitlab_api, "delete_plain_note", delete_plain)
    monkeypatch.setattr(
        workflow,
        "resolve_discussion",
        lambda *_args: pytest.fail("stale review must not resolve old discussions"),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: writes.append("rollback-current"),
    )
    assert not workflow.finalize_previous_review_state(
        gitlab_config(),
        previous,
        _outcome("clean"),
        review_identity=_identity(),
        transaction=PostingTransaction(),
    )
    assert writes == ["delete-91"]
    error = capsys.readouterr().err
    assert "previous review cleanup is partial; current-run comments retained" in error
    assert "previous review preserved" not in error


def test_unconfirmed_previous_cleanup_retains_current_review_and_stops(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    writes: list[str] = []
    previous = BotCommentRefs(plain_note_ids=[91, 92], discussions_to_resolve=["prior-thread"])
    monkeypatch.setattr(workflow, "validate_review_freshness", lambda *_args: None)
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda _config, note_id: writes.append(f"delete-{note_id}") or False,
    )
    monkeypatch.setattr(
        workflow,
        "resolve_discussion",
        lambda *_args: pytest.fail("unconfirmed cleanup must stop before resolving"),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: pytest.fail("an attempted delete cannot be rolled back"),
    )
    assert not workflow.finalize_previous_review_state(
        gitlab_config(),
        previous,
        _outcome("clean"),
        review_identity=_identity(),
        transaction=PostingTransaction(),
    )
    assert writes == ["delete-91"]
    assert "provider did not confirm the mutation" in capsys.readouterr().err


def test_confirmed_previous_cleanup_checks_freshness_before_each_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[str] = []
    previous = BotCommentRefs(plain_note_ids=[91, 92], discussions_to_resolve=["prior-thread"])
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: writes.append("fresh") or None,
    )
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda _config, note_id: writes.append(f"delete-{note_id}") or True,
    )
    monkeypatch.setattr(
        workflow,
        "resolve_discussion",
        lambda _config, discussion_id: writes.append(f"resolve-{discussion_id}") or True,
    )
    assert workflow.finalize_previous_review_state(
        gitlab_config(),
        previous,
        _outcome("clean"),
        review_identity=_identity(),
        transaction=PostingTransaction(),
    )
    assert writes == ["fresh", "delete-91", "fresh", "delete-92", "fresh", "resolve-prior-thread"]


def test_pre_execution_status_requires_full_live_tuple_and_exact_setup_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = _pre_execution_status(PROTECTED_POLICY_RULE_PATH_PENDING)
    gitlink = _pre_execution_status(GITLINK_PREVIEW_UNSUPPORTED)
    calls: list[str] = []

    def advanced(*_args: Any) -> freshness.ReviewFreshnessResult:
        calls.append("freshness")
        return freshness.ReviewFreshnessResult("f" * 40, True)

    monkeypatch.setattr(workflow, "validate_review_freshness", advanced)
    assert (
        workflow.pre_execution_status_fresh_or_exit(
            gitlab_config(), replace(setup, review=None), exact_policy=True
        )
        == 1
    )
    assert calls == []
    assert (
        workflow.pre_execution_status_fresh_or_exit(gitlab_config(), setup, exact_policy=True) == 1
    )
    assert workflow.pre_execution_status_fresh_or_exit(gitlab_config(), gitlink) is None
    assert calls == ["freshness", "freshness"]


def test_setup_status_drift_before_old_note_cleanup_preserves_previous_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = _pre_execution_status(PROTECTED_POLICY_RULE_PATH_PENDING)
    previous = BotCommentRefs(setup_plain_note_ids=[91])
    stale = False
    writes: list[str] = []

    def freshness_check(*_args: Any) -> freshness.ReviewFreshnessResult:
        if stale:
            raise freshness.ReviewFreshnessStale("target_changed")
        return freshness.ReviewFreshnessResult(status.policy_sha or "", False)

    def publish(*_args: Any) -> bool:
        nonlocal stale
        writes.append("publish-current")
        stale = True
        return True

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", status.source_sha, "opened"),
    )
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda _config: previous)
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args: writes.append("create-current") or {"id": 11},
    )
    monkeypatch.setattr(workflow, "finalize_posting", publish)
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda *_args: pytest.fail("stale status must not delete old setup note"),
    )
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda _config, refs, _transaction: writes.append(
            "rollback-current" if refs is previous else "wrong-baseline"
        ),
    )

    assert workflow.post_pre_execution_status(gitlab_config(), status) == 1
    assert writes == ["create-current", "publish-current", "rollback-current"]


@pytest.mark.parametrize("confirmed", [True, False])
def test_setup_cleanup_retains_replacement_after_first_delete_attempt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], confirmed: bool
) -> None:
    status = _pre_execution_status(PROTECTED_POLICY_RULE_PATH_PENDING)
    previous = BotCommentRefs(setup_plain_note_ids=[91, 92])
    stale = False
    writes: list[str] = []

    def freshness_check(*_args: Any) -> freshness.ReviewFreshnessResult:
        if stale:
            raise freshness.ReviewFreshnessStale("target_changed")
        return freshness.ReviewFreshnessResult(status.policy_sha or "", False)

    def delete(_config: Any, note_id: int) -> bool:
        nonlocal stale
        writes.append(f"delete-{note_id}")
        stale = True
        return confirmed

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", status.source_sha, "opened"),
    )
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda _config: previous)
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args: writes.append("create-current") or {"id": 11},
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(workflow.gitlab_api, "delete_plain_note", delete)
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: pytest.fail("replacement must survive attempted old-note cleanup"),
    )

    assert workflow.post_pre_execution_status(gitlab_config(), status) == 1
    assert writes == ["create-current", "delete-91"]
    assert "cleanup is partial" in capsys.readouterr().err


def test_setup_draft_drift_after_publish_keeps_visible_partial_and_old_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A published setup draft has no proven visible-note ID for rollback."""

    status = _pre_execution_status(PROTECTED_POLICY_RULE_PATH_PENDING)
    previous = BotCommentRefs(setup_plain_note_ids=[91])
    stale = False
    writes: list[str] = []

    def freshness_check(*_args: Any) -> freshness.ReviewFreshnessResult:
        if stale:
            raise freshness.ReviewFreshnessStale("policy_changed")
        return freshness.ReviewFreshnessResult(status.policy_sha or "", False)

    def create(
        _config: Any, _title: str, _body: str, transaction: PostingTransaction
    ) -> dict[str, int]:
        assert transaction.record_draft(11)
        writes.append("create-draft")
        return {"id": 11}

    def publish(*_args: Any) -> bool:
        nonlocal stale
        writes.append("publish-draft")
        stale = True
        return True

    monkeypatch.setattr(workflow, "validate_review_freshness", freshness_check)
    monkeypatch.setattr(workflow, "post_mode", lambda: "draft")
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", status.source_sha, "opened"),
    )
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda _config: previous)
    monkeypatch.setattr(workflow, "post_review_note_bounded", create)
    monkeypatch.setattr(workflow, "finalize_posting", publish)
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: pytest.fail("published draft must not use draft-ID rollback"),
    )
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda *_args: pytest.fail("old setup note must be preserved"),
    )

    assert workflow.post_pre_execution_status(gitlab_config(), status) == 1
    assert writes == ["create-draft", "publish-draft"]


def test_setup_draft_ambiguous_publish_failure_does_not_delete_draft_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed PUT may have published, so draft-ID DELETE is not a rollback."""

    status = _pre_execution_status(PROTECTED_POLICY_RULE_PATH_PENDING)
    transaction_ids: list[tuple[int, ...]] = []
    monkeypatch.setattr(
        workflow,
        "validate_review_freshness",
        lambda *_args: freshness.ReviewFreshnessResult(status.policy_sha or "", False),
    )
    monkeypatch.setattr(workflow, "post_mode", lambda: "draft")
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", status.source_sha, "opened"),
    )
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda _config: BotCommentRefs(setup_plain_note_ids=[91]),
    )

    def create(
        _config: Any, _title: str, _body: str, transaction: PostingTransaction
    ) -> dict[str, int]:
        assert transaction.record_draft(11)
        return {"id": 11}

    def publish(_config: Any, transaction: PostingTransaction) -> bool:
        transaction_ids.append(transaction.draft_note_ids)
        return False

    monkeypatch.setattr(workflow, "post_review_note_bounded", create)
    monkeypatch.setattr(workflow, "finalize_posting", publish)
    monkeypatch.setattr(
        workflow,
        "publish_failure_exit",
        lambda *_args: pytest.fail("ambiguous published draft cannot be rolled back by ID"),
    )
    monkeypatch.setattr(
        workflow.gitlab_api,
        "delete_plain_note",
        lambda *_args: pytest.fail("old setup note must be preserved"),
    )

    assert workflow.post_pre_execution_status(gitlab_config(), status) == 1
    assert transaction_ids == [(11,)]


def test_noneligible_review_rechecks_after_draft_publication_before_old_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Comment-only and partial reviews cannot replace old state after a late retarget."""

    calls: list[str] = []
    freshness_results = iter((None, 1))
    monkeypatch.setattr(
        workflow,
        "publication_freshness_or_exit",
        lambda *_args: next(freshness_results),
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(
        workflow,
        "rollback_current_run_comments",
        lambda *_args: calls.append("rollback-current"),
    )
    monkeypatch.setattr(
        workflow,
        "finalize_previous_review_state",
        lambda *_args, **_kwargs: pytest.fail("prior review must be preserved"),
    )
    decision = ApprovalEligibility(
        False,
        ApprovalResult(ApprovalStatus.NOT_ELIGIBLE, "partial coverage"),
    )

    assert (
        workflow.finalize_review_approval(
            gitlab_config(),
            BotCommentRefs(),
            _outcome("partial"),
            PostingTransaction(),
            decision,
            "a" * 40,
            41,
            "f" * 32,
            lambda _approval: "summary",
            review_identity=_identity(unprotected=True),
        )
        == 1
    )
    assert calls == ["rollback-current"]


def test_existing_approval_does_not_skip_second_identity_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An already approved state never excuses a stale target or policy authority."""

    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: (gitlab_approval.GitLabApprovalState(True, 41), None),
    )

    def stale() -> None:
        raise freshness.ReviewFreshnessStale("target_changed")

    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=_identity(),
        freshness_check=stale,
    )
    assert result.preserve_previous_review
    assert result.result.status is ApprovalStatus.SKIPPED


def test_provider_rejection_of_stale_approval_preserves_previous_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 409 after the last read is classified as provider-confirmed drift."""

    monkeypatch.setattr(
        gitlab_approval,
        "wait_for_synchronized_approval_state",
        lambda *_args, **_kwargs: (gitlab_approval.GitLabApprovalState(False, 41), None),
    )
    monkeypatch.setattr(
        gitlab,
        "approve_merge_request",
        lambda *_args: gitlab.GitLabWriteResult("write_failed", http_status=409),
    )
    result = gitlab_approval.execute_approval(
        gitlab_config(),
        ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "pending")),
        "a" * 40,
        41,
        review_identity=_identity(),
        freshness_check=lambda: None,
    )
    assert result.result.status is ApprovalStatus.SKIPPED
    assert result.preserve_previous_review


def test_historical_receipt_is_readback_only_for_current_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A v9 receipt cannot be reinterpreted as a v11 current-review identity."""

    receipt = review_receipt_v8()
    assert validated_review_identity(receipt) is not None
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: pytest.fail("historical receipt cannot cause new writes"),
    )
    assert workflow.post_results(gitlab_config(), {"_ocr_toolkit": receipt}) == 1


def test_formatting_only_displays_validated_policy_sha_without_branch_name() -> None:
    identity = _identity(unprotected=True)
    summary = formatting.summarize_result(
        total=0,
        inline_count=0,
        fallback_count=0,
        warning_count=0,
        protected_policy_anchor_sha=identity.policy_sha,
    )
    assert "protected policy anchor" in summary
    assert identity.policy_sha in summary
    assert identity.policy_branch is not None
    assert identity.policy_branch not in summary
    assert "limited, comment-only mode" not in summary
