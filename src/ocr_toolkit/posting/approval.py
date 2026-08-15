"""Conservative policy and typed outcomes for GitLab automatic approval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ocr_toolkit.ocr_result import (
    AUTOMATIC_APPROVAL_BLOCK_REASON,
    SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS,
)
from ocr_toolkit.posting.settings import BooleanSetting
from ocr_toolkit.result_contract import ReviewOutcome

ALLOWED_CATEGORIES = frozenset({"style", "documentation", "maintainability"})
MAX_APPROVABLE_FINDINGS = 3


class ApprovalStatus(str, Enum):
    """Closed public states for one automatic-approval transaction."""

    APPROVED = "approved"
    NOT_ELIGIBLE = "not eligible"
    DISABLED = "disabled"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    """Bounded status rendered in the review summary and runner log."""

    status: ApprovalStatus
    reason: str


@dataclass(frozen=True, slots=True)
class ApprovalEligibility:
    """Policy conclusion before provider state is consulted."""

    eligible: bool
    result: ApprovalResult


def evaluate_approval_policy(
    setting: BooleanSetting,
    outcome: ReviewOutcome,
    comments: list[dict[str, Any]],
    warnings: list[Any],
    omitted_count: int,
    toolkit_metadata: Any = None,
) -> ApprovalEligibility:
    """Evaluate the fixed v0.4.7 policy from authoritative OCR data."""

    if not setting.enabled:
        reason = (
            "configuration was invalid and failed closed"
            if not setting.valid
            else "disabled by OCR_AUTO_APPROVE"
        )
        return ApprovalEligibility(
            False,
            ApprovalResult(ApprovalStatus.DISABLED, reason),
        )
    metadata_reason = automatic_approval_metadata_reason(toolkit_metadata)
    if metadata_reason:
        reason = metadata_reason
    elif not outcome.manifest_present:
        reason = "the OCR result has no authoritative coverage manifest"
    elif outcome.kind != "clean" or outcome.budget_exceeded:
        reason = "the OCR review did not complete cleanly"
    elif outcome.failed_count or outcome.waived_count:
        reason = "coverage contained failed or waived items"
    elif warnings:
        reason = "the OCR review reported warnings"
    elif omitted_count:
        reason = "one or more findings were omitted from publication"
    elif len(comments) > MAX_APPROVABLE_FINDINGS:
        reason = f"the review reported more than {MAX_APPROVABLE_FINDINGS} findings"
    else:
        reason = ""

    if reason:
        return ApprovalEligibility(
            False,
            ApprovalResult(ApprovalStatus.NOT_ELIGIBLE, reason),
        )

    for comment in comments:
        severity = comment.get("severity")
        category = comment.get("category")
        if severity != "low":
            return ApprovalEligibility(
                False,
                ApprovalResult(
                    ApprovalStatus.NOT_ELIGIBLE,
                    "a finding had a blocking or malformed severity",
                ),
            )
        if not isinstance(category, str) or category not in ALLOWED_CATEGORIES:
            return ApprovalEligibility(
                False,
                ApprovalResult(
                    ApprovalStatus.NOT_ELIGIBLE,
                    "a finding had a blocking or malformed category",
                ),
            )

    return ApprovalEligibility(
        True,
        ApprovalResult(
            ApprovalStatus.SKIPPED,
            "awaiting post-publication SHA verification",
        ),
    )


def approval_summary_line(result: ApprovalResult) -> str:
    """Render exactly one bounded automatic-approval state line."""

    return f"- Automatic approval: `{result.status.value}` — {result.reason}."


def provisional_approval_result(eligibility: ApprovalEligibility) -> ApprovalResult:
    """Return a fail-closed state safe to publish before provider readback."""

    if not eligibility.eligible:
        return eligibility.result
    return ApprovalResult(
        ApprovalStatus.FAILED,
        "automatic approval has not yet been confirmed",
    )


def automatic_approval_metadata_reason(toolkit_metadata: Any) -> str:
    """Return one toolkit-authored blocker while preserving readable v1 receipts."""

    if not isinstance(toolkit_metadata, dict):
        return "the review-time approval receipt is missing or invalid"
    schema_version = toolkit_metadata.get("schema_version")
    if schema_version not in SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS:
        return "the review-time approval receipt is missing or invalid"
    if schema_version == 1:
        return "the review-time approval receipt predates current eligibility controls"
    if set(toolkit_metadata) != {"schema_version", "mcp_usage", "automatic_approval"}:
        return "the review-time approval receipt is missing or invalid"
    constraint = toolkit_metadata.get("automatic_approval")
    if not isinstance(constraint, dict) or set(constraint) != {"eligible", "reason"}:
        return "the review-time approval receipt is missing or invalid"
    eligible = constraint.get("eligible")
    reason = constraint.get("reason")
    if eligible is True and reason is None:
        return ""
    if eligible is False and reason == AUTOMATIC_APPROVAL_BLOCK_REASON:
        return AUTOMATIC_APPROVAL_BLOCK_REASON
    return "the review-time approval receipt is missing or invalid"
