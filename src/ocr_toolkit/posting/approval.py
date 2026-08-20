"""Conservative policy and typed outcomes for GitLab automatic approval."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_TOOL_NAME_CHARS,
    MAX_TOOLKIT_MCP_TOOLS_PER_SERVER,
    MAX_TOOLKIT_MCP_USAGE_COUNT,
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
    elif toolkit_metadata["evidence"]["mandatory"] is not outcome.requires_evidence_mcp:
        reason = "the review-time approval receipt is missing or invalid"
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


def _positive_id(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def automatic_approval_metadata_reason(toolkit_metadata: Any) -> str:
    """Return the closed review-time receipt blocker for automatic approval."""

    invalid = "the review-time approval receipt is missing or invalid"
    if not isinstance(toolkit_metadata, dict):
        return invalid
    schema_version = toolkit_metadata.get("schema_version")
    if schema_version in {1, 2, 3}:
        return "the review-time approval receipt predates current eligibility controls"
    if schema_version != 4 or set(toolkit_metadata) != {
        "schema_version",
        "review",
        "context",
        "mcp",
        "evidence",
        "publication",
        "cleanup",
    }:
        return invalid

    review = toolkit_metadata.get("review")
    if not isinstance(review, dict) or set(review) != {"source_sha", "policy_sha", "mr_author_id"}:
        return invalid
    if not _full_sha(review.get("source_sha")) or not _full_sha(review.get("policy_sha")):
        return invalid
    if not _positive_id(review.get("mr_author_id")):
        return invalid

    context = toolkit_metadata.get("context")
    if not isinstance(context, dict) or set(context) != {
        "mode",
        "state",
        "classes",
        "policy_digest",
        "per_source",
        "degradation_counts",
        "required_degraded",
        "mutable_admitted",
        "tool_usage",
    }:
        return invalid
    mode = context.get("mode")
    state = context.get("state")
    classes = context.get("classes")
    expected_classes = {
        "off": [],
        "metadata": ["merge_request_metadata"],
        "enriched": ["merge_request_metadata", "forge_discussions", "external_records"],
    }.get(mode)
    policy_digest = context.get("policy_digest")
    per_source = context.get("per_source")
    degradation = context.get("degradation_counts")
    required_degraded = context.get("required_degraded")
    mutable_admitted = context.get("mutable_admitted")
    context_usage = context.get("tool_usage")
    if (
        mode not in {"off", "metadata", "enriched"}
        or state not in {"disabled", "complete", "degraded"}
        or classes != expected_classes
        or (mode == "off" and state != "disabled")
        or (mode in {"metadata", "enriched"} and state == "disabled")
        or (mode == "enriched") != _sha256(policy_digest)
        or not isinstance(per_source, dict)
        or len(per_source) > 64
        or any(
            not isinstance(source, str)
            or not source
            or len(source) > 256
            or source_state not in {"complete", "partial", "unavailable", "mutated"}
            for source, source_state in per_source.items()
        )
        or not isinstance(degradation, dict)
        or set(degradation) != {"invalid", "limit", "unavailable"}
        or any(
            not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 1_000_000
            for count in degradation.values()
        )
        or not isinstance(required_degraded, bool)
        or not isinstance(mutable_admitted, bool)
        or not isinstance(context_usage, dict)
        or set(context_usage) != {"context_get", "context_list"}
        or any(
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for count in context_usage.values()
        )
    ):
        return invalid
    if mode != "enriched" and (
        policy_digest is not None
        or per_source
        or any(degradation.values())
        or required_degraded
        or mutable_admitted
        or any(context_usage.values())
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
    tool_owners: set[str] = set()
    external = False
    builtin_server = "ocr_toolkit_evidence"
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
            or not 1 <= len(tools) <= MAX_TOOLKIT_MCP_TOOLS_PER_SERVER
            or any(
                not isinstance(tool, str) or not tool or len(tool) > MAX_TOOLKIT_MCP_TOOL_NAME_CHARS
                for tool in tools
            )
            or len(set(tools)) != len(tools)
            or any(tool in tool_owners for tool in tools)
            or (server == builtin_server) != (transport == "builtin")
            or (
                server == builtin_server
                and tools
                != (
                    [builtin_server, "context_list", "context_get"]
                    if mode == "enriched"
                    else [builtin_server]
                )
            )
        ):
            return invalid
        servers.add(server)
        tool_owners.update(tools)
        external = external or server != builtin_server
    if builtin_server not in servers:
        return invalid
    if any(
        not isinstance(server, str)
        or server not in servers
        or not isinstance(count, int)
        or isinstance(count, bool)
        or not 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
        for server, count in usage.items()
    ):
        return invalid

    evidence = toolkit_metadata.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"mandatory", "used", "calls"}:
        return invalid
    mandatory = evidence.get("mandatory")
    used = evidence.get("used")
    evidence_calls = evidence.get("calls")
    evidence_called = isinstance(evidence_calls, int) and evidence_calls > 0
    if (
        not isinstance(mandatory, bool)
        or not isinstance(used, bool)
        or not isinstance(evidence_calls, int)
        or isinstance(evidence_calls, bool)
        or not 0 <= evidence_calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or used is not evidence_called
        or (mandatory and not used)
        or usage.get(builtin_server, 0) != evidence_calls + sum(context_usage.values())
    ):
        return invalid
    publication = toolkit_metadata.get("publication")
    cleanup = toolkit_metadata.get("cleanup")
    if publication != {"dlp": "passed"} or cleanup != {"result": "passed"}:
        return invalid
    if context.get("state") == "degraded" or required_degraded:
        return "the selected review context was degraded"
    if mutable_admitted:
        return "mutable review context was admitted"
    if external:
        return "external MCP was configured for a comment-only review"
    return ""
