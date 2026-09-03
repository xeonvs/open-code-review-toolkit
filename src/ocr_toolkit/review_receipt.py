"""Construct and hostile-validate closed toolkit review receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ocr_toolkit.evidence.actions import ACTION_RECEIPT_BUCKETS, EVIDENCE_ACTIONS
from ocr_toolkit.evidence.mcp import COVERAGE_TOOL_NAME, SEARCH_TOOL_NAME, TOOL_NAME
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_TOOL_NAME_CHARS,
    MAX_TOOLKIT_MCP_TOOLS_PER_SERVER,
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    MAX_TOOLKIT_MCP_USAGE_SERVERS,
    TOOLKIT_MCP_SERVER_NAME_RE,
)
from ocr_toolkit.result_contract import OcrResultContractError, ReviewOutcome

INVALID_APPROVAL_RECEIPT_REASON = "the review-time approval receipt is missing or invalid"
UNPROTECTED_APPROVAL_REASON = (
    "the GitLab target branch was unprotected; limited reviews are comment-only"
)


@dataclass(frozen=True, slots=True)
class ReceiptReviewIdentity:
    """Carry immutable provider facts from one fully validated receipt."""

    source_sha: str
    target_sha: str
    target_protection: str
    mr_author_id: int


def verified_evidence_actions(
    evidence_by_tool: dict[str, int],
    action_counts: dict[str, dict[str, int]] | None,
    *,
    mandatory: bool,
) -> dict[str, object]:
    """Build exact action attribution or reject a positive incomplete receipt."""

    evidence_calls = sum(evidence_by_tool.values())
    if action_counts is None:
        if evidence_calls:
            raise ValueError("evidence action attribution is unavailable")
        action_counts = {
            "attempted": dict.fromkeys(ACTION_RECEIPT_BUCKETS, 0),
            "completed": dict.fromkeys(EVIDENCE_ACTIONS, 0),
        }
    if set(action_counts) != {"attempted", "completed"}:
        raise ValueError("evidence action attribution is unavailable")
    attempted = action_counts.get("attempted")
    completed = action_counts.get("completed")
    if (
        not isinstance(attempted, dict)
        or not isinstance(completed, dict)
        or set(attempted) != set(ACTION_RECEIPT_BUCKETS)
        or set(completed) != set(EVIDENCE_ACTIONS)
    ):
        raise ValueError("evidence action attribution is unavailable")
    all_counts = (*attempted.values(), *completed.values())
    if any(
        not isinstance(count, int)
        or isinstance(count, bool)
        or not 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
        for count in all_counts
    ):
        raise ValueError("evidence action attribution is unavailable")
    if any(completed[action] > attempted[action] for action in EVIDENCE_ACTIONS):
        raise ValueError("evidence action attribution is unavailable")
    if mandatory and completed["summary"] < 1:
        raise ValueError("OCR review did not call the mandatory evidence summary action")
    primary_received = sum(attempted[action] for action in ("summary", "list", "get"))
    received_by_tool = {
        TOOL_NAME: primary_received + attempted["unattributed"],
        SEARCH_TOOL_NAME: attempted["search"],
        COVERAGE_TOOL_NAME: attempted["coverage"],
    }
    if any(received_by_tool[tool] > evidence_by_tool[tool] for tool in received_by_tool):
        raise ValueError("evidence action attribution does not match OCR tool usage")
    # OCR accounts for a dynamic tool attempt before its JSON arguments are parsed.
    # Such a request never reaches the MCP owner, so retain only the count-only
    # residual as unattributed and never let it establish successful evidence use.
    undispatched = sum(evidence_by_tool[tool] - received_by_tool[tool] for tool in received_by_tool)
    return {
        "state": "verified",
        "attempted": {
            **{action: attempted[action] for action in EVIDENCE_ACTIONS},
            "unattributed": attempted["unattributed"] + undispatched,
        },
        "completed": {action: completed[action] for action in EVIDENCE_ACTIONS},
    }


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


def publication_dlp_state(value: Any) -> str | None:
    """Validate the exact current publication-policy receipt."""

    if value == {"state": "passed"}:
        return "passed"
    if not isinstance(value, dict):
        return None
    if value.get("state") == "private-sanitized":
        if set(value) != {"state", "reason_counts", "sanitized_fields"}:
            return None
        reason_counts = value.get("reason_counts")
        sanitized_fields = value.get("sanitized_fields")
        if (
            not _valid_dlp_reason_counts(reason_counts)
            or not any(reason_counts.values())
            or not isinstance(sanitized_fields, int)
            or isinstance(sanitized_fields, bool)
            or not 0 < sanitized_fields <= MAX_TOOLKIT_MCP_USAGE_COUNT
        ):
            return None
        return "private-sanitized"
    if not isinstance(value, dict) or set(value) != {
        "state",
        "reason_counts",
        "retained",
        "omitted",
        "original",
    }:
        return None
    if value.get("state") != "publication-filtered":
        return None
    reason_counts = value.get("reason_counts")
    retained = value.get("retained")
    omitted = value.get("omitted")
    original = value.get("original")
    if (
        not _valid_dlp_reason_counts(reason_counts)
        or not any(reason_counts.values())
        or not isinstance(retained, dict)
        or set(retained) != {"comments", "warnings"}
        or not isinstance(omitted, dict)
        or set(omitted) != {"comments", "warnings", "fields"}
        or any(
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for counts in (retained, omitted)
            for count in counts.values()
        )
        or not isinstance(original, dict)
        or set(original) != {"outcome", "selected", "completed", "reused", "failed", "waived"}
        or original.get("outcome") not in {"clean", "warning", "partial", "failed", "skipped"}
        or any(
            not isinstance(original.get(field), int)
            or isinstance(original.get(field), bool)
            or not 0 <= original[field] <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for field in ("selected", "completed", "reused", "failed", "waived")
        )
    ):
        return None
    selected = original["selected"]
    completed = original["completed"]
    reused = original["reused"]
    failed = original["failed"]
    waived = original["waived"]
    outcome = original["outcome"]
    derived_outcomes = {"failed"} | (
        {"skipped"}
        if selected == 0
        else {"clean", "warning"}
        if failed == 0
        else {"failed"}
        if failed == selected
        else {"partial"}
    )
    if selected != completed + reused + failed + waived or outcome not in derived_outcomes:
        return None
    return "publication-filtered"


def _valid_dlp_reason_counts(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and set(value) == {"forbidden", "invalid_text", "laundering", "limit", "pii", "secret"}
        and all(
            isinstance(count, int)
            and not isinstance(count, bool)
            and 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for count in value.values()
        )
    )


def automatic_approval_metadata_reason(toolkit_metadata: Any) -> str:
    """Return the closed review-time receipt blocker for automatic approval."""

    invalid = INVALID_APPROVAL_RECEIPT_REASON
    if not isinstance(toolkit_metadata, dict):
        return invalid
    if toolkit_metadata.get("schema_version") != 8 or set(toolkit_metadata) != {
        "schema_version",
        "review",
        "context",
        "mcp",
        "evidence",
        "publication",
        "tool_execution",
        "cleanup",
    }:
        return invalid

    review = toolkit_metadata.get("review")
    if not isinstance(review, dict) or set(review) != {
        "source_sha",
        "policy_sha",
        "target_sha",
        "target_protection",
        "mr_author_id",
    }:
        return invalid
    if (
        not _full_sha(review.get("source_sha"))
        or not _full_sha(review.get("policy_sha"))
        or not _full_sha(review.get("target_sha"))
        or review.get("policy_sha") != review.get("target_sha")
        or not isinstance(review.get("target_protection"), str)
        or review.get("target_protection") not in {"protected", "unprotected"}
    ):
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
    builtin_server = TOOL_NAME
    builtin_tools = [TOOL_NAME, SEARCH_TOOL_NAME, COVERAGE_TOOL_NAME]
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
                    [*builtin_tools, "context_list", "context_get"]
                    if mode == "enriched"
                    else builtin_tools
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
    if not isinstance(evidence, dict) or set(evidence) != {
        "mandatory",
        "used",
        "calls",
        "actions",
    }:
        return invalid
    mandatory = evidence.get("mandatory")
    used = evidence.get("used")
    evidence_calls = evidence.get("calls")
    evidence_actions = evidence.get("actions")
    evidence_completed = _completed_evidence_calls(evidence_actions)
    if (
        not isinstance(mandatory, bool)
        or not isinstance(used, bool)
        or not isinstance(evidence_calls, int)
        or isinstance(evidence_calls, bool)
        or not 0 <= evidence_calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or used is not (evidence_completed > 0)
        or (mandatory and not used)
        or usage.get(builtin_server, 0) != evidence_calls + sum(context_usage.values())
        or not _valid_evidence_actions(evidence_actions, evidence_calls, mandatory=mandatory)
    ):
        return invalid
    publication = toolkit_metadata.get("publication")
    tool_execution = toolkit_metadata.get("tool_execution")
    cleanup = toolkit_metadata.get("cleanup")
    publication_state = publication_dlp_state(publication)
    failure_state = tool_execution.get("state") if isinstance(tool_execution, dict) else None
    failed_tools = tool_execution.get("failed") if isinstance(tool_execution, dict) else None
    if (
        publication_state is None
        or not isinstance(tool_execution, dict)
        or set(tool_execution) != {"state", "failed"}
        or failure_state not in {"absent", "invalid", "conflicting", "verified"}
        or (
            failure_state == "verified"
            and (
                not isinstance(failed_tools, int)
                or isinstance(failed_tools, bool)
                or not 0 <= failed_tools <= MAX_TOOLKIT_MCP_USAGE_COUNT
            )
        )
        or (failure_state != "verified" and failed_tools is not None)
        or cleanup != {"result": "passed"}
    ):
        return invalid
    if review.get("target_protection") == "unprotected":
        if mode not in {"off", "metadata"} or external:
            return invalid
        return UNPROTECTED_APPROVAL_REASON
    if publication_state == "publication-filtered":
        return "publication DLP filtered the complete review result"
    if failure_state in {"invalid", "conflicting"}:
        return "OCR tool failure diagnostics were malformed or contradictory"
    if failure_state == "verified" and failed_tools:
        return "one or more OCR tool calls failed"
    if context.get("state") == "degraded" or required_degraded:
        return "the selected review context was degraded"
    if mutable_admitted:
        return "mutable review context was admitted"
    if external:
        return "external MCP was configured for a comment-only review"
    return ""


def toolkit_receipt_is_valid(toolkit_metadata: Any) -> bool:
    """Return whether metadata is an exact current receipt, including valid blockers."""

    return automatic_approval_metadata_reason(toolkit_metadata) != INVALID_APPROVAL_RECEIPT_REASON


def receipt_review_identity(toolkit_metadata: Any) -> ReceiptReviewIdentity | None:
    """Parse the exact immutable identity section without granting approval authority."""

    if not isinstance(toolkit_metadata, dict) or toolkit_metadata.get("schema_version") != 8:
        return None
    review = toolkit_metadata.get("review")
    if (
        not isinstance(review, dict)
        or set(review)
        != {
            "source_sha",
            "policy_sha",
            "target_sha",
            "target_protection",
            "mr_author_id",
        }
        or not _full_sha(review.get("source_sha"))
        or not _full_sha(review.get("policy_sha"))
        or not _full_sha(review.get("target_sha"))
        or review.get("policy_sha") != review.get("target_sha")
        or not isinstance(review.get("target_protection"), str)
        or review.get("target_protection") not in {"protected", "unprotected"}
        or not _positive_id(review.get("mr_author_id"))
    ):
        return None
    return ReceiptReviewIdentity(
        source_sha=review["source_sha"],
        target_sha=review["target_sha"],
        target_protection=review["target_protection"],
        mr_author_id=review["mr_author_id"],
    )


def validated_review_identity(toolkit_metadata: Any) -> ReceiptReviewIdentity | None:
    """Return immutable review facts only after complete hostile receipt validation."""

    if not toolkit_receipt_is_valid(toolkit_metadata):
        return None
    return receipt_review_identity(toolkit_metadata)


def publication_outcome_for_summary(outcome: ReviewOutcome, publication: Any) -> ReviewOutcome:
    """Recover only validated original coverage facts from a filtered receipt."""

    if publication_dlp_state(publication) != "publication-filtered":
        return outcome
    if outcome.kind != "partial" or outcome.manifest_present:
        raise OcrResultContractError(
            "publication-filtered receipt is not bound to a safe result projection"
        )
    original = publication["original"]
    kind = original["outcome"]
    if outcome.budget_exceeded and kind != "partial":
        raise OcrResultContractError(
            "publication-filtered receipt contradicts the result budget state"
        )
    counts = {
        field: original[field] for field in ("selected", "completed", "reused", "failed", "waived")
    }
    manifest_present = any(counts.values())
    status = {
        "clean": "complete" if manifest_present else "success",
        "warning": "completed_with_warnings",
        "partial": "budget_exceeded" if outcome.budget_exceeded else "completed_with_errors",
        "failed": "failed",
        "skipped": "skipped",
    }[kind]
    return ReviewOutcome(
        status=status,
        kind=kind,
        budget_exceeded=outcome.budget_exceeded and kind == "partial",
        manifest_present=manifest_present,
        selected_count=counts["selected"],
        completed_count=counts["completed"],
        reused_count=counts["reused"],
        failed_count=counts["failed"],
        waived_count=counts["waived"],
    )


def _completed_evidence_calls(value: Any) -> int:
    """Return the closed completed-action subtotal or a non-validating sentinel."""

    if not isinstance(value, dict):
        return -1
    completed = value.get("completed")
    if not isinstance(completed, dict) or set(completed) != set(EVIDENCE_ACTIONS):
        return 0 if value == {"state": "unavailable"} else -1
    values = completed.values()
    if any(
        not isinstance(count, int)
        or isinstance(count, bool)
        or not 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
        for count in values
    ):
        return -1
    return sum(completed.values())


def _valid_evidence_actions(value: Any, evidence_calls: Any, *, mandatory: bool) -> bool:
    """Validate verified counts or an explicit unavailable attribution state."""

    if value == {"state": "unavailable"}:
        return evidence_calls == 0
    expected = {"state", "attempted", "completed"}
    if not isinstance(value, dict) or set(value) != expected:
        return False
    attempted = value.get("attempted")
    completed = value.get("completed")
    if (
        not isinstance(attempted, dict)
        or set(attempted) != set(ACTION_RECEIPT_BUCKETS)
        or not isinstance(completed, dict)
        or set(completed) != set(EVIDENCE_ACTIONS)
    ):
        return False
    counts = [*attempted.values(), *completed.values()]
    return bool(
        value.get("state") == "verified"
        and all(
            isinstance(count, int)
            and not isinstance(count, bool)
            and 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for count in counts
        )
        and all(completed[action] <= attempted[action] for action in EVIDENCE_ACTIONS)
        and sum(attempted.values()) == evidence_calls
        and (not mandatory or completed["summary"] >= 1)
    )
