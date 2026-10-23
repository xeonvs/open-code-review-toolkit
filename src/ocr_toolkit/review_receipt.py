"""Construct and hostile-validate closed toolkit review receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ocr_toolkit.evidence.actions import ACTION_RECEIPT_BUCKETS, EVIDENCE_ACTIONS
from ocr_toolkit.evidence.invocation import MAX_CI_IDENTIFIER_CHARS
from ocr_toolkit.evidence.mcp import COVERAGE_TOOL_NAME, SEARCH_TOOL_NAME, TOOL_NAME
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_TOOL_NAME_CHARS,
    MAX_TOOLKIT_MCP_TOOLS_PER_SERVER,
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    MAX_TOOLKIT_MCP_USAGE_SERVERS,
    PARTIAL_TOOLKIT_RESULT_SCHEMA_VERSION,
    SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS,
    TOOLKIT_MCP_SERVER_NAME_RE,
)
from ocr_toolkit.reporting.dlp import publication_dlp_state as publication_dlp_state
from ocr_toolkit.reporting.dlp import (
    publication_outcome_for_summary as publication_outcome_for_summary,
)
from ocr_toolkit.reporting.federation import valid_reconciliation
from ocr_toolkit.repository_coverage import RepositoryCoverageError, parse_repository_coverage

INVALID_APPROVAL_RECEIPT_REASON = "the review-time approval receipt is missing or invalid"
# Keep historical wire shapes explicit; changing the current producer version
# must never reinterpret a persisted v11 receipt as a future format.
RECEIPT_V11 = 11
RECEIPT_V12 = PARTIAL_TOOLKIT_RESULT_SCHEMA_VERSION
_FEDERATION_SCHEMA_BY_RECEIPT_VERSION = {
    9: "ocr.federation/v1",
    10: "ocr.federation/v2",
    RECEIPT_V11: "ocr.federation/v2",
    RECEIPT_V12: "ocr.federation/v2",
}
_PUBLICATION_SCHEMA_BY_RECEIPT_VERSION = {
    9: None,
    10: "ocr.publication/v2",
    RECEIPT_V11: "ocr.publication/v2",
    RECEIPT_V12: "ocr.publication/v2",
}
UNPROTECTED_APPROVAL_REASON = (
    "the GitLab target branch was unprotected; limited reviews are comment-only"
)
AUTO_UNPROTECTED_APPROVAL_REASON = (
    "the GitLab target branch was unprotected; automatic approval is unavailable"
)


@dataclass(frozen=True, slots=True)
class ReceiptReviewIdentity:
    """Carry immutable provider facts from one fully validated receipt."""

    source_sha: str
    target_sha: str
    target_protection: str
    mr_author_id: int
    schema_version: int
    policy_sha: str
    project_id: str | None = None
    merge_request_iid: str | None = None
    diff_base_sha: str | None = None
    diff_start_sha: str | None = None
    diff_head_sha: str | None = None
    diff_version_id: int | None = None
    target_branch: str | None = None
    policy_project_id: str | None = None
    policy_branch: str | None = None
    policy_protection: str | None = None
    protection_mode: str | None = None
    ci_job_id: str | None = None


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


def _decimal_identifier(value: Any) -> bool:
    """Match canonical bounded GitLab project and MR identifiers."""

    return (
        isinstance(value, str)
        and value.isascii()
        and value.isdecimal()
        and 1 <= len(value) <= MAX_CI_IDENTIFIER_CHARS
        and value[0] != "0"
    )


def _branch(value: Any) -> bool:
    """Accept only a bounded Git branch suitable for an encoded provider lookup."""

    if not isinstance(value, str):
        return False
    try:
        byte_length = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return False
    return not (
        not 1 <= len(value) <= 512
        or byte_length > 2_048
        or value == "@"
        or value.startswith("-")
        or value.endswith(("/", "."))
        or ".." in value
        or "@{" in value
        or any(
            character == "\x7f" or ord(character) < 32 or character in " ~^:?*[\\"
            for character in value
        )
        or any(
            not part or part.startswith(".") or part.endswith(".lock") for part in value.split("/")
        )
    )


_LEGACY_REVIEW_KEYS = frozenset(
    {"source_sha", "policy_sha", "target_sha", "target_protection", "mr_author_id"}
)
_V11_REVIEW_KEYS = frozenset(
    {
        "source_sha",
        "diff_base_sha",
        "diff_start_sha",
        "diff_head_sha",
        "diff_version_id",
        "project_id",
        "merge_request_iid",
        "target_branch",
        "target_sha",
        "target_protection",
        "policy_project_id",
        "policy_branch",
        "policy_sha",
        "policy_protection",
        "protection_mode",
        "mr_author_id",
    }
)


def _parse_review_identity(review: Any, receipt_version: int) -> ReceiptReviewIdentity | None:
    """Hostile-parse one versioned review section without upgrading legacy authority."""

    if not isinstance(review, dict):
        return None
    if receipt_version in {9, 10}:
        if (
            set(review) != _LEGACY_REVIEW_KEYS
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
            schema_version=receipt_version,
            policy_sha=review["policy_sha"],
        )
    if receipt_version not in {RECEIPT_V11, RECEIPT_V12} or set(review) not in {
        _V11_REVIEW_KEYS,
        _V11_REVIEW_KEYS | {"ci_job_id"},
    }:
        return None
    if (
        not all(
            _full_sha(review.get(field)) and review.get(field) != "0" * 40
            for field in (
                "source_sha",
                "diff_base_sha",
                "diff_start_sha",
                "diff_head_sha",
                "target_sha",
                "policy_sha",
            )
        )
        or review["source_sha"] != review["diff_head_sha"]
        or not _positive_id(review.get("diff_version_id"))
        or not _decimal_identifier(review.get("project_id"))
        or not _decimal_identifier(review.get("merge_request_iid"))
        or not _decimal_identifier(review.get("policy_project_id"))
        or review["policy_project_id"] != review["project_id"]
        or not _branch(review.get("target_branch"))
        or not _branch(review.get("policy_branch"))
        or not isinstance(review.get("target_protection"), str)
        or review.get("target_protection") not in {"protected", "unprotected"}
        or not isinstance(review.get("policy_protection"), str)
        or review.get("policy_protection") not in {"protected", "unprotected"}
        or not isinstance(review.get("protection_mode"), str)
        or review.get("protection_mode") not in {"auto", "required", "unprotected"}
        or not _positive_id(review.get("mr_author_id"))
        or ("ci_job_id" in review and not _decimal_identifier(review.get("ci_job_id")))
    ):
        return None

    target_protected = review["target_protection"] == "protected"
    if target_protected or review["protection_mode"] == "unprotected":
        if (
            review["policy_branch"] != review["target_branch"]
            or review["policy_sha"] != review["target_sha"]
            or review["policy_protection"] != review["target_protection"]
        ):
            return None
    elif (
        review["protection_mode"] != "auto"
        or review["policy_branch"] == review["target_branch"]
        or review["policy_protection"] != "protected"
    ):
        return None

    return ReceiptReviewIdentity(
        source_sha=review["source_sha"],
        target_sha=review["target_sha"],
        target_protection=review["target_protection"],
        mr_author_id=review["mr_author_id"],
        schema_version=receipt_version,
        policy_sha=review["policy_sha"],
        project_id=review["project_id"],
        merge_request_iid=review["merge_request_iid"],
        diff_base_sha=review["diff_base_sha"],
        diff_start_sha=review["diff_start_sha"],
        diff_head_sha=review["diff_head_sha"],
        diff_version_id=review["diff_version_id"],
        target_branch=review["target_branch"],
        policy_project_id=review["policy_project_id"],
        policy_branch=review["policy_branch"],
        policy_protection=review["policy_protection"],
        protection_mode=review["protection_mode"],
        ci_job_id=review.get("ci_job_id"),
    )


def automatic_approval_metadata_reason(toolkit_metadata: Any) -> str:
    """Return the closed review-time receipt blocker for automatic approval."""

    invalid = INVALID_APPROVAL_RECEIPT_REASON
    if not isinstance(toolkit_metadata, dict):
        return invalid
    receipt_version = toolkit_metadata.get("schema_version")
    if (
        type(receipt_version) is not int
        or receipt_version not in SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS
        or receipt_version not in _FEDERATION_SCHEMA_BY_RECEIPT_VERSION
        or receipt_version not in _PUBLICATION_SCHEMA_BY_RECEIPT_VERSION
        or set(toolkit_metadata)
        != {
            "schema_version",
            "review",
            "context",
            "mcp",
            "evidence",
            "dlp",
            "publication",
            "tool_execution",
            "cleanup",
        }
        | ({"repository_coverage"} if receipt_version == RECEIPT_V12 else set())
    ):
        return invalid

    review_identity = _parse_review_identity(toolkit_metadata.get("review"), receipt_version)
    if review_identity is None:
        return invalid
    if receipt_version == RECEIPT_V12:
        try:
            parse_repository_coverage(
                toolkit_metadata["repository_coverage"], required_state="partial"
            )
        except RepositoryCoverageError:
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
        "legacy_policy",
        "tool_usage",
    }:
        return invalid
    if type(context.get("legacy_policy")) is not bool:
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
    if not isinstance(mcp, dict) or set(mcp) != {"capabilities", "usage", "federation"}:
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

    federation = mcp.get("federation")
    if external:
        if not valid_reconciliation(federation):
            return invalid
        expected_federation_schema = _FEDERATION_SCHEMA_BY_RECEIPT_VERSION[receipt_version]
        if federation["receipt"]["schema"] != expected_federation_schema:
            return invalid
        expected = {
            tool: cap["server"]
            for cap in capabilities
            if cap["transport"] != "builtin"
            for tool in cap["tools"]
        }
        if set(federation["receipt"]["tools"]) != set(expected):
            return invalid
        for tool, server in expected.items():
            if federation["receipt"]["tools"][tool]["server"] != server:
                return invalid
        if any(
            sum(
                count
                for alias, count in federation["ocr_attempts"].items()
                if expected[alias] == server
            )
            != usage.get(server, 0)
            for server in set(expected.values())
        ):
            return invalid
    elif federation is not None:
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
    dlp = toolkit_metadata.get("dlp")
    if not isinstance(dlp, dict) or set(dlp) != {"enabled"} or type(dlp.get("enabled")) is not bool:
        return invalid
    publication = toolkit_metadata.get("publication")
    expected_publication_schema = _PUBLICATION_SCHEMA_BY_RECEIPT_VERSION[receipt_version]
    if not isinstance(publication, dict) or (
        (expected_publication_schema is None and "schema" in publication)
        or (
            expected_publication_schema is not None
            and publication.get("schema") != expected_publication_schema
        )
    ):
        return invalid
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
    if not dlp["enabled"]:
        if publication_state != "disabled":
            return invalid
        dlp_reason = "DLP was disabled by OCR_DLP_ENABLED; the review is comment-only"
    elif publication_state == "disabled":
        return invalid
    else:
        dlp_reason = ""
    if review_identity.target_protection == "unprotected":
        if review_identity.policy_protection != "protected" and (
            mode not in {"off", "metadata"} or external
        ):
            return invalid
        if review_identity.protection_mode == "auto":
            return AUTO_UNPROTECTED_APPROVAL_REASON
        return UNPROTECTED_APPROVAL_REASON
    if dlp_reason:
        return dlp_reason
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
    if external and federation["state"] == "degraded":
        return "external MCP use was advisory, incomplete or accounting-mismatched"
    if receipt_version == RECEIPT_V12:
        return "changed Git submodule pointers were not reviewed; automatic approval is unavailable"
    return ""


def toolkit_receipt_is_valid(toolkit_metadata: Any) -> bool:
    """Return whether metadata is an exact current receipt, including valid blockers."""

    return automatic_approval_metadata_reason(toolkit_metadata) != INVALID_APPROVAL_RECEIPT_REASON


def receipt_review_identity(toolkit_metadata: Any) -> ReceiptReviewIdentity | None:
    """Parse the exact immutable identity section without granting approval authority."""

    if (
        not isinstance(toolkit_metadata, dict)
        or type(toolkit_metadata.get("schema_version")) is not int
        or toolkit_metadata.get("schema_version") not in SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS
    ):
        return None
    return _parse_review_identity(
        toolkit_metadata.get("review"), toolkit_metadata["schema_version"]
    )


def validated_review_identity(toolkit_metadata: Any) -> ReceiptReviewIdentity | None:
    """Return immutable review facts only after complete hostile receipt validation."""

    if not toolkit_receipt_is_valid(toolkit_metadata):
        return None
    return receipt_review_identity(toolkit_metadata)


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
