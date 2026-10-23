"""Resolve one fail-closed reviewed source identity across review lifecycle owners."""

from __future__ import annotations

import re
from collections.abc import Mapping

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ZERO_SHA = "0" * 40


def full_sha(value: object) -> str:
    """Return one exact non-zero lowercase SHA-1 identity or an empty value."""

    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None or value == ZERO_SHA:
        return ""
    return value


def effective_reviewed_sha(environment: Mapping[str, str]) -> str:
    """Resolve an MR source head without treating a synthetic CI commit as source."""

    event_type = environment.get("CI_MERGE_REQUEST_EVENT_TYPE", "")
    if event_type != "detached":
        return ""

    commit_sha = full_sha(environment.get("CI_COMMIT_SHA", ""))
    if not commit_sha:
        return ""
    merge_request_sha = environment.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "")
    if merge_request_sha and merge_request_sha != ZERO_SHA:
        return commit_sha if full_sha(merge_request_sha) == commit_sha else ""
    return commit_sha


def validate_detached_merge_request_pipeline(
    environment: Mapping[str, str], *, expected_source_sha: str
) -> None:
    """Accept only a detached MR job whose checked-out commit is the live source."""

    event_type = environment.get("CI_MERGE_REQUEST_EVENT_TYPE", "")
    if event_type != "detached":
        raise ValueError(
            "GitLab MR review requires a detached merge-request pipeline; "
            "merged-results, merge-train and unknown pipeline forms are unsupported"
        )
    if not full_sha(expected_source_sha):
        raise ValueError("reviewed MR source must be an immutable full commit SHA")
    commit_sha = full_sha(environment.get("CI_COMMIT_SHA", ""))
    if commit_sha != expected_source_sha:
        raise ValueError("detached GitLab CI commit does not match the reviewed MR source")
    merge_request_sha = environment.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "")
    if (
        merge_request_sha
        and merge_request_sha != ZERO_SHA
        and full_sha(merge_request_sha) != expected_source_sha
    ):
        raise ValueError("GitLab CI MR source SHA contradicts the reviewed source")
