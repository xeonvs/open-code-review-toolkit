"""Revalidate a reviewed GitLab code and policy snapshot before provider writes."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    ShallowAncestryUnavailable,
)
from ocr_toolkit.ocr_result import TOOLKIT_RESULT_SCHEMA_VERSION
from ocr_toolkit.providers.gitlab import (
    GitLabMergeRequestStale,
    GitLabMergeRequestTerminal,
    GitLabProviderError,
    acquire_review_snapshot,
)
from ocr_toolkit.review_identity import validate_detached_merge_request_pipeline
from ocr_toolkit.review_receipt import ReceiptReviewIdentity

FreshnessReason = Literal[
    "receipt_unavailable",
    "invocation_changed",
    "source_changed",
    "diff_changed",
    "target_changed",
    "authority_changed",
    "policy_rewritten",
    "provider_unavailable",
    "ancestry_unavailable",
]


class ReviewFreshnessError(ValueError):
    """Carry one safe, closed reason for blocking a stale or unverified write."""

    def __init__(self, reason: FreshnessReason) -> None:
        self.reason = reason
        super().__init__(reason.replace("_", " "))


class ReviewFreshnessStale(ReviewFreshnessError):
    """The authenticated current MR no longer matches the reviewed identity."""


class ReviewFreshnessUnavailable(ReviewFreshnessError):
    """The current identity or local ancestry cannot be proven safely."""


@dataclass(frozen=True, slots=True)
class ReviewFreshnessResult:
    """Report only policy movement while keeping the reviewed P immutable."""

    current_policy_sha: str
    policy_advanced: bool


def validate_review_freshness(
    environment: Mapping[str, str], identity: ReceiptReviewIdentity, root: Path
) -> ReviewFreshnessResult:
    """Require the current receipt tuple or a proven policy fast-forward."""

    if identity.schema_version != TOOLKIT_RESULT_SCHEMA_VERSION or any(
        value is None
        for value in (
            identity.project_id,
            identity.merge_request_iid,
            identity.diff_base_sha,
            identity.diff_start_sha,
            identity.diff_head_sha,
            identity.diff_version_id,
            identity.target_branch,
            identity.policy_project_id,
            identity.policy_branch,
            identity.policy_protection,
            identity.protection_mode,
        )
    ):
        raise ReviewFreshnessUnavailable("receipt_unavailable")
    if (
        environment.get("CI_PROJECT_ID") != identity.project_id
        or environment.get("CI_MERGE_REQUEST_IID") != identity.merge_request_iid
        or environment.get("CI_JOB_ID") != identity.ci_job_id
    ):
        raise ReviewFreshnessStale("invocation_changed")
    try:
        validate_detached_merge_request_pipeline(
            environment, expected_source_sha=identity.source_sha
        )
    except ValueError as exc:
        raise ReviewFreshnessStale("invocation_changed") from exc
    ci_diff_base = environment.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", "")
    if ci_diff_base and ci_diff_base != identity.diff_base_sha:
        raise ReviewFreshnessStale("diff_changed")

    try:
        current = acquire_review_snapshot(
            environment, expected_head=identity.source_sha, include_metadata=False
        )
    except GitLabMergeRequestTerminal:
        raise
    except GitLabMergeRequestStale as exc:
        raise ReviewFreshnessStale("source_changed") from exc
    except GitLabProviderError as exc:
        raise ReviewFreshnessUnavailable("provider_unavailable") from exc

    if (
        current.project_id != identity.project_id
        or current.merge_request_iid != identity.merge_request_iid
        or current.author_id != identity.mr_author_id
    ):
        raise ReviewFreshnessStale("invocation_changed")
    if current.source_sha != identity.source_sha:
        raise ReviewFreshnessStale("source_changed")
    if (
        current.diff_base_sha != identity.diff_base_sha
        or current.diff_start_sha != identity.diff_start_sha
        or current.diff_head_sha != identity.diff_head_sha
        or current.diff_version_id != identity.diff_version_id
    ):
        raise ReviewFreshnessStale("diff_changed")
    if (
        current.target_branch != identity.target_branch
        or current.target_sha != identity.target_sha
        or current.target_protection != identity.target_protection
    ):
        raise ReviewFreshnessStale("target_changed")
    if (
        current.project_id != identity.policy_project_id
        or current.policy_branch != identity.policy_branch
        or current.policy_protection != identity.policy_protection
        or current.protection_mode != identity.protection_mode
    ):
        raise ReviewFreshnessStale("authority_changed")

    if current.policy_sha == identity.policy_sha:
        return ReviewFreshnessResult(current_policy_sha=current.policy_sha, policy_advanced=False)

    # Only the separately selected protected default authority may advance.
    if (
        identity.protection_mode != "auto"
        or identity.target_protection != "unprotected"
        or identity.policy_protection != "protected"
        or identity.policy_branch == identity.target_branch
    ):
        raise ReviewFreshnessStale("authority_changed")

    try:
        reader = GitRepositoryReader(root)
        reader.fetch_commit(identity.policy_sha)
        reader.fetch_commit(current.policy_sha)
        try:
            policy_is_ancestor = reader.is_ancestor(identity.policy_sha, current.policy_sha)
        except ShallowAncestryUnavailable:
            reader.fetch_commit_history(current.policy_sha)
            policy_is_ancestor = reader.is_ancestor(identity.policy_sha, current.policy_sha)
        if not policy_is_ancestor:
            raise ReviewFreshnessStale("policy_rewritten")
    except (OSError, RepositoryEvidenceError, subprocess.TimeoutExpired) as exc:
        raise ReviewFreshnessUnavailable("ancestry_unavailable") from exc
    return ReviewFreshnessResult(current_policy_sha=current.policy_sha, policy_advanced=True)
