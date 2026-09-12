"""Terminal GitLab merge-request lifecycle regression tests."""

from __future__ import annotations

from typing import Any

import pytest

from ocr_toolkit import ocr_result
from ocr_toolkit.posting import gitlab, snapshot, workflow
from ocr_toolkit.posting.approval import ApprovalStatus
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.pre_execution import (
    GITLAB_MERGE_REQUEST_TERMINAL,
    STATUS_SCHEMA,
    PreExecutionStatus,
)
from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle, GitLabProviderError
from tests.support import gitlab_config, review_receipt_v8

SOURCE = "a" * 40
BASE = "b" * 40


def terminal_status(state: str = "merged") -> PreExecutionStatus:
    return PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=GITLAB_MERGE_REQUEST_TERMINAL,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=None,
        provider="gitlab",
        project_id="1",
        change_id="2",
        terminal_state=state,
    )


@pytest.mark.parametrize(("state", "emoji"), [("merged", True), ("closed", False)])
def test_terminal_pre_execution_status_creates_one_plain_verified_note(
    monkeypatch: pytest.MonkeyPatch, state: str, emoji: bool
) -> None:
    created: list[str] = []
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _config: [])
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, state),
    )
    monkeypatch.setattr(workflow, "post_emoji", lambda: emoji)
    monkeypatch.setattr(
        gitlab,
        "post_note",
        lambda _config, body: created.append(body) or {"id": 17},
    )
    monkeypatch.setattr(
        gitlab,
        "api_request",
        lambda *_args, **_kwargs: {
            "id": 17,
            "author": {"id": 7},
            "body": build_marked_note_body(created[0]),
        },
    )

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status(state)) == 0
    assert len(created) == 1
    assert created[0].splitlines()[0] == "<!-- open-code-review-terminal-merge-request -->"
    expected_heading = (
        f"⏭️ Open Code Review skipped — merge request is already {state}"
        if emoji
        else f"Open Code Review skipped — merge request is already {state}"
    )
    assert expected_heading in created[0]
    assert "No model review was run" in created[0]
    assert "No review findings were produced" in created[0]
    assert "Automatic approval was not attempted" in created[0]
    assert "Previous Open Code Review comments and reviewer state were preserved" in created[0]


def test_duplicate_terminal_job_updates_the_one_existing_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated: list[tuple[int, str]] = []
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _config: [17])
    monkeypatch.setattr(workflow, "post_emoji", lambda: True)
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, "merged"),
    )

    def update(_config: Any, note_id: int, body: str) -> gitlab.GitLabWriteResult:
        updated.append((note_id, body))
        return gitlab.GitLabWriteResult("posted")

    monkeypatch.setattr(workflow, "update_plain_note", update)
    monkeypatch.setattr(
        gitlab,
        "api_request",
        lambda *_args, **_kwargs: {
            "id": 17,
            "author": {"id": 7},
            "body": build_marked_note_body(updated[0][1]),
        },
    )
    monkeypatch.setattr(
        gitlab, "post_note", lambda *_args, **_kwargs: pytest.fail("duplicate note created")
    )

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status()) == 0
    assert updated == [(17, updated[0][1])]


def _complete_result(*, comments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "status": "complete",
        "comments": comments or [],
        "warnings": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "synthetic"}],
                "completed": [{"item_id": "synthetic"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
        ocr_result.TOOLKIT_RESULT_KEY: review_receipt_v8(),
    }


@pytest.mark.parametrize("state", ["merged", "closed"])
def test_admitted_terminal_result_publishes_normally_but_never_approves(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    notes: list[str] = []
    approvals: list[ApprovalStatus] = []
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, state),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda _config, _title, body, *_args: notes.append(body) or {"id": 19},
    )

    def finalize(*args: Any, **_kwargs: Any) -> int:
        eligibility = args[4]
        approvals.append(eligibility.result.status)
        return 0

    monkeypatch.setattr(workflow, "finalize_review_approval", finalize)

    assert workflow.post_results(gitlab_config(), _complete_result()) == 0
    assert approvals == [ApprovalStatus.SKIPPED]
    assert f"Merge request lifecycle at publication: `{state}`" in notes[0]
    assert f"merge request was already {state}" in notes[0]
    assert SOURCE in notes[0]


def test_admitted_result_lifecycle_failure_stops_before_first_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: (_ for _ in ()).throw(GitLabProviderError("head mismatch")),
    )
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda *_args, **_kwargs: pytest.fail("publication mutation reached"),
    )

    assert workflow.post_results(gitlab_config(), _complete_result()) == 1


def test_terminal_finding_result_checks_lifecycle_after_diff_read_and_keeps_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    notes: list[str] = []
    result = _complete_result(
        comments=[
            {
                "path": f"src/example-{index}.py",
                "line": 7,
                "content": "Keep the bounded branch.",
                "severity": "low",
                "category": "maintainability",
            }
            for index in range(2)
        ]
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow, "get_diff_refs", lambda _config: order.append("diff-read") or None
    )
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: (
            order.append("lifecycle-read")
            or GitLabMergeRequestLifecycle("1", "2", SOURCE, "closed")
        ),
    )
    monkeypatch.setattr(workflow, "max_post_comments", lambda: 1)
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda _config, title, body, *_args: (
            order.append("write") or notes.append(f"{title}\n{body}") or {"id": len(notes)}
        ),
    )
    monkeypatch.setattr(workflow, "finalize_review_approval", lambda *_args, **_kwargs: 0)

    assert workflow.post_results(gitlab_config(), result) == 0
    assert order[:3] == ["diff-read", "lifecycle-read", "write"]
    published = "\n".join(notes)
    assert "Open Code Review omitted comments" in published
    assert "1 omitted" in published
    assert "Merge request lifecycle at publication: `closed`" in published


def test_snapshot_classifies_only_owned_plain_terminal_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal_body = build_marked_note_body(
        "<!-- open-code-review-terminal-merge-request -->\n**Open Code Review skipped**\n\nstatus"
    )
    notes = [
        {"id": 17, "author": {"id": 7}, "body": terminal_body},
        {"id": 18, "author": {"id": 8}, "body": terminal_body},
    ]
    monkeypatch.setattr(
        snapshot,
        "api_get_paginated",
        lambda _config, endpoint, **_kwargs: notes if endpoint.startswith("/notes") else [],
    )
    monkeypatch.setattr(snapshot, "post_mode", lambda: "direct")

    refs = snapshot.collect_previous_bot_comment_refs(gitlab_config())

    assert refs is not None
    assert refs.terminal_plain_note_ids == [17]
    assert refs.plain_note_ids == [17]


def test_terminal_marker_inside_hostile_note_text_is_not_control_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = build_marked_note_body(
        "**Open Code Review fallback**\n\nFinding text\n"
        "<!-- open-code-review-terminal-merge-request -->\nmore text"
    )
    notes = [{"id": 31, "author": {"id": 7}, "body": hostile}]
    monkeypatch.setattr(
        snapshot,
        "api_get_paginated",
        lambda _config, endpoint, **_kwargs: notes if endpoint.startswith("/notes") else [],
    )
    monkeypatch.setattr(snapshot, "post_mode", lambda: "direct")

    refs = snapshot.collect_previous_bot_comment_refs(gitlab_config())

    assert refs is not None
    assert refs.terminal_plain_note_ids == []
    assert snapshot.collect_terminal_status_note_ids(gitlab_config()) == []
    assert refs.plain_note_ids == [31]


def test_reopened_merge_request_fails_before_terminal_note_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, "opened"),
    )
    monkeypatch.setattr(
        workflow,
        "collect_terminal_status_note_ids",
        lambda _config: pytest.fail("note collection reached after reopen"),
    )
    monkeypatch.setattr(
        gitlab, "post_note", lambda *_args: pytest.fail("note mutation reached after reopen")
    )

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status("closed")) == 1


def test_reopen_during_terminal_note_upsert_fails_final_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter(("closed", "opened"))
    created: list[str] = []
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, next(states)),
    )
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _config: [])
    monkeypatch.setattr(
        gitlab,
        "post_note",
        lambda _config, body: created.append(body) or {"id": 41},
    )
    monkeypatch.setattr(
        gitlab,
        "api_request",
        lambda *_args, **_kwargs: {
            "id": 41,
            "author": {"id": 7},
            "body": build_marked_note_body(created[0]),
        },
    )

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status("closed")) == 1


@pytest.mark.parametrize(("state", "expected"), [("merged", 0), ("closed", 1)])
def test_strict_gate_succeeds_only_for_irreversible_terminal_state(
    monkeypatch: pytest.MonkeyPatch, state: str, expected: int
) -> None:
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, state),
    )
    monkeypatch.setattr(workflow, "strict_posting", lambda: True)

    assert (
        workflow.terminal_status_exit(gitlab_config(), SOURCE, posting_succeeded=True) == expected
    )


def test_note_collection_failure_cannot_skip_final_reopen_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter(("closed", "opened"))
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, next(states)),
    )
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _config: None)
    monkeypatch.setattr(workflow, "strict_posting", lambda: False)

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status("closed")) == 1


def test_note_verification_failure_cannot_skip_final_reopen_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter(("closed", "opened"))
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, next(states)),
    )
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _config: [])
    monkeypatch.setattr(gitlab, "post_note", lambda *_args: None)
    monkeypatch.setattr(workflow, "strict_posting", lambda: False)

    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status("closed")) == 1


def test_partial_success_removes_only_stale_terminal_status_from_preserved_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    refs = snapshot.BotCommentRefs(terminal_plain_note_ids=[17], plain_note_ids=[17, 18])
    monkeypatch.setattr(
        workflow, "delete_previous_summary_notes", lambda *_args: calls.append("summary")
    )
    monkeypatch.setattr(
        workflow, "delete_previous_terminal_notes", lambda *_args: calls.append("terminal")
    )
    monkeypatch.setattr(
        workflow,
        "delete_previous_bot_comments_if_collected",
        lambda *_args: calls.append("all"),
    )
    monkeypatch.setattr(workflow, "resolve_requested_discussions", lambda *_args: None)

    workflow.finalize_previous_review_state(
        gitlab_config(),
        refs,
        workflow.ReviewOutcome(
            status="partial",
            kind="partial",
            manifest_present=True,
            selected_count=1,
            completed_count=0,
            reused_count=0,
            failed_count=1,
            waived_count=0,
            failed_items=(),
            budget_exceeded=False,
        ),
    )

    assert calls == ["summary", "terminal"]
