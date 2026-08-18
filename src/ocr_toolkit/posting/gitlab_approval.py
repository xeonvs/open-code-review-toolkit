"""GitLab adapter for exact-SHA automatic approval management."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.posting import gitlab
from ocr_toolkit.posting.approval import (
    ApprovalEligibility,
    ApprovalResult,
    ApprovalStatus,
)

SYNC_ATTEMPTS = 10
SYNC_INTERVAL_SECONDS = 2.0
PENDING_MERGE_STATUSES = frozenset({"checking", "approvals_syncing"})


@dataclass(frozen=True, slots=True)
class ApprovalExecution:
    """Final provider result after exact-SHA synchronization and readback."""

    result: ApprovalResult


@dataclass(frozen=True, slots=True)
class GitLabApprovalState:
    """One synchronized current-head, author, and current-user approval snapshot."""

    own_approved: bool
    author_id: int


def _full_sha(value: Any) -> str:
    """Return a full Git object ID or an empty string for malformed input."""

    if not isinstance(value, str):
        return ""
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else ""


def _current_user_approved(payload: Any, current_user_id: int) -> bool | None:
    """Read only the authenticated user's approval from the bounded API result."""

    if not isinstance(payload, dict):
        return None
    approved_by = payload.get("approved_by")
    if not isinstance(approved_by, list):
        return None
    own_approved = False
    for item in approved_by:
        if not isinstance(item, dict):
            return None
        user = item.get("user")
        if not isinstance(user, dict):
            return None
        user_id = user.get("id")
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            return None
        own_approved = own_approved or user_id == current_user_id
    return own_approved


def _latest_diff_version(config: gitlab.GitLabConfig) -> dict[str, Any] | None:
    """Return the highest validated GitLab diff-version id from bounded pages."""

    versions = gitlab.api_get_paginated(config, "/versions", max_pages=20)
    if not isinstance(versions, list) or not versions:
        return None
    candidates: list[tuple[int, dict[str, Any]]] = []
    for version in versions:
        if not isinstance(version, dict):
            return None
        version_id = version.get("id")
        if isinstance(version_id, bool) or not isinstance(version_id, int) or version_id <= 0:
            return None
        candidates.append((version_id, version))
    return max(candidates, key=lambda item: item[0])[1]


def wait_for_synchronized_approval_state(
    config: gitlab.GitLabConfig,
    expected_sha: str,
    *,
    attempts: int = SYNC_ATTEMPTS,
    interval_seconds: float = SYNC_INTERVAL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[GitLabApprovalState | None, ApprovalResult | None]:
    """Wait for GitLab diff/approval synchronization and verify the exact head."""

    if config.current_user_id is None or not _full_sha(expected_sha):
        return None, ApprovalResult(
            ApprovalStatus.SKIPPED,
            "the reviewed commit or toolkit user could not be verified",
        )

    for attempt in range(attempts):
        merge_request = gitlab.api_request(config, "", method="GET")
        latest = _latest_diff_version(config)
        if not isinstance(merge_request, dict) or latest is None:
            return None, ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab synchronization state was unavailable",
            )

        mr_sha = _full_sha(merge_request.get("sha"))
        diff_sha = _full_sha(latest.get("head_commit_sha"))
        if not mr_sha or not diff_sha:
            return None, ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab returned malformed merge-request head metadata",
            )
        if mr_sha != expected_sha or diff_sha != expected_sha:
            return None, ApprovalResult(
                ApprovalStatus.SKIPPED,
                "the merge-request head no longer matches the reviewed commit",
            )
        if merge_request.get("state") != "opened":
            return None, ApprovalResult(
                ApprovalStatus.SKIPPED,
                "the merge request is not open",
            )
        author = merge_request.get("author")
        author_id = author.get("id") if isinstance(author, dict) else None
        if isinstance(author_id, bool) or not isinstance(author_id, int) or author_id <= 0:
            return None, ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab returned malformed merge-request author metadata",
            )

        detailed_status = merge_request.get("detailed_merge_status")
        patch_id = _full_sha(latest.get("patch_id_sha"))
        if not isinstance(detailed_status, str) or not detailed_status:
            return None, ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab returned malformed merge synchronization metadata",
            )
        if detailed_status not in PENDING_MERGE_STATUSES and patch_id:
            approvals = gitlab.api_request(config, "/approvals", method="GET")
            own_approved = _current_user_approved(approvals, config.current_user_id)
            if own_approved is None:
                return None, ApprovalResult(
                    ApprovalStatus.FAILED,
                    "GitLab returned malformed approval state",
                )
            return GitLabApprovalState(own_approved, author_id), None

        if attempt + 1 < attempts:
            sleep(interval_seconds)

    return None, ApprovalResult(
        ApprovalStatus.SKIPPED,
        "GitLab did not finish diff and approval synchronization in time",
    )


def _write_rejection(result: gitlab.GitLabWriteResult, action: str) -> ApprovalResult:
    """Classify a non-retried provider write without exposing its response body."""

    if result.http_status == 409:
        return ApprovalResult(
            ApprovalStatus.SKIPPED,
            "GitLab rejected a stale merge-request head",
        )
    if result.http_status is not None and 400 <= result.http_status < 500:
        return ApprovalResult(
            ApprovalStatus.SKIPPED,
            f"GitLab did not permit the toolkit user to {action}",
        )
    return ApprovalResult(
        ApprovalStatus.FAILED,
        f"the GitLab {action} result was not safely confirmed",
    )


def execute_approval(
    config: gitlab.GitLabConfig,
    eligibility: ApprovalEligibility,
    expected_sha: str,
    expected_author_id: int | None = None,
    *,
    attempts: int = SYNC_ATTEMPTS,
    interval_seconds: float = SYNC_INTERVAL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> ApprovalExecution:
    """Apply exact-SHA approval without ever removing an existing approval."""

    if not eligibility.eligible:
        return ApprovalExecution(eligibility.result)

    state, synchronization_result = wait_for_synchronized_approval_state(
        config,
        expected_sha,
        attempts=attempts,
        interval_seconds=interval_seconds,
        sleep=sleep,
    )
    if state is None:
        return ApprovalExecution(
            synchronization_result
            or ApprovalResult(ApprovalStatus.FAILED, "GitLab synchronization failed"),
        )
    if expected_author_id is None or state.author_id != expected_author_id:
        return ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.SKIPPED,
                "the merge-request author no longer matches the reviewed identity",
            )
        )
    if config.current_user_id == state.author_id:
        return ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.SKIPPED,
                "the toolkit user is the merge-request author; no approval was attempted",
            )
        )

    if state.own_approved:
        return ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.SKIPPED,
                "the toolkit user already approved; no approval state was changed",
            )
        )

    write = gitlab.approve_merge_request(config, expected_sha)
    if not write.posted:
        return ApprovalExecution(_write_rejection(write, "approve"))
    confirmed, confirmation_error = wait_for_synchronized_approval_state(
        config,
        expected_sha,
        attempts=1,
        interval_seconds=0,
        sleep=sleep,
    )
    if confirmed is None:
        return ApprovalExecution(
            confirmation_error
            or ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab approval readback did not confirm the toolkit user",
            ),
        )
    if confirmed.author_id != expected_author_id or config.current_user_id == confirmed.author_id:
        return ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.FAILED,
                "the post-write merge-request author no longer matches the reviewed identity",
            )
        )
    if not confirmed.own_approved:
        return ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.FAILED,
                "GitLab approval readback did not confirm the toolkit user",
            )
        )
    return ApprovalExecution(
        ApprovalResult(
            ApprovalStatus.APPROVED,
            "GitLab confirmed the toolkit user's exact-SHA approval",
        )
    )
