"""Conservative policy and typed outcomes for GitLab automatic approval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_USAGE_SERVERS,
    TOOLKIT_MCP_SERVER_NAME_RE,
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


def _full_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value)
    )


def _positive_id_or_none(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value > 0)


def automatic_approval_metadata_reason(toolkit_metadata: Any) -> str:
    """Return the closed review-time receipt blocker for automatic approval."""

    invalid = "the review-time approval receipt is missing or invalid"
    if not isinstance(toolkit_metadata, dict):
        return invalid
    schema_version = toolkit_metadata.get("schema_version")
    if schema_version in {1, 2}:
        return "the review-time approval receipt predates current eligibility controls"
    if schema_version != 3 or set(toolkit_metadata) != {
        "schema_version",
        "review",
        "context",
        "mcp",
        "evidence",
    }:
        return invalid

    review = toolkit_metadata.get("review")
    if not isinstance(review, dict) or set(review) != {"source_sha", "policy_sha", "mr_author_id"}:
        return invalid
    if not _full_sha(review.get("source_sha")) or not _full_sha(review.get("policy_sha")):
        return invalid
    if not _positive_id_or_none(review.get("mr_author_id")):
        return invalid

    context = toolkit_metadata.get("context")
    if not isinstance(context, dict) or set(context) != {"mode", "state", "classes"}:
        return invalid
    mode = context.get("mode")
    state = context.get("state")
    classes = context.get("classes")
    expected_classes = [] if mode == "off" else ["merge_request_metadata"]
    if (
        mode not in {"off", "metadata"}
        or state not in {"disabled", "complete", "degraded"}
        or classes != expected_classes
        or (mode == "off" and state != "disabled")
        or (mode == "metadata" and state == "disabled")
        or (mode == "metadata" and review.get("mr_author_id") is None)
    ):
        return invalid

    mcp = toolkit_metadata.get("mcp")
    if not isinstance(mcp, dict) or set(mcp) != {"capabilities", "usage"}:
        return invalid
    capabilities = mcp.get("capabilities")
    usage = mcp.get("usage")
    if (
        not isinstance(capabilities, list)
        or not 1 <= len(capabilities) <= MAX_TOOLKIT_MCP_USAGE_SERVERS
        or not isinstance(usage, dict)
        or len(usage) > MAX_TOOLKIT_MCP_USAGE_SERVERS
    ):
        return invalid
    servers: set[str] = set()
    external = False
    for capability in capabilities:
        if not isinstance(capability, dict) or set(capability) != {"server", "transport", "tools"}:
            return invalid
        server = capability.get("server")
        transport = capability.get("transport")
        tools = capability.get("tools")
        if (
            not isinstance(server, str)
            or TOOLKIT_MCP_SERVER_NAME_RE.fullmatch(server) is None
            or server in servers
            or transport not in {"builtin", "stdio", "remote"}
            or not isinstance(tools, list)
            or not tools
            or any(
                not isinstance(tool, str) or TOOLKIT_MCP_SERVER_NAME_RE.fullmatch(tool) is None
                for tool in tools
            )
            or len(set(tools)) != len(tools)
        ):
            return invalid
        servers.add(server)
        external = external or transport != "builtin"
    if "ocr_toolkit_evidence" not in servers:
        return invalid
    if any(
        not isinstance(server, str)
        or server not in servers
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        for server, count in usage.items()
    ):
        return invalid

    evidence = toolkit_metadata.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"mandatory", "used"}:
        return invalid
    mandatory = evidence.get("mandatory")
    used = evidence.get("used")
    if not isinstance(mandatory, bool) or not isinstance(used, bool) or (mandatory and not used):
        return invalid
    if context.get("state") == "degraded":
        return "the selected review context was degraded"
    if external:
        return "external MCP was configured for a comment-only review"
    return ""
