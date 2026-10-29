"""Run Open Code Review with private artifacts and safe CI diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, replace
from io import BufferedWriter
from pathlib import Path

from ocr_toolkit import configure, local_chatgpt, mcp_config, preflight
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, update_ocr_config
from ocr_toolkit.context.broker import (
    ContextOrigin,
    prepare_discussion_records,
    prepare_remediation_records,
)
from ocr_toolkit.context.ci_outcomes import prepare_ci_outcome_records
from ocr_toolkit.context.contracts import (
    CI_OUTCOME_MODEL_FIELD,
    ContextContractError,
    ContextPolicy,
    TextBudgets,
)
from ocr_toolkit.context.dlp import (
    FORBIDDEN_SOURCE_CLASSES,
    ForbiddenMatcher,
    ForbiddenValue,
    check_text,
    dlp_mode,
    resolve_dlp_enabled,
)
from ocr_toolkit.context.policy import load_protected_policy
from ocr_toolkit.context.store import (
    ContextRecord,
    ContextStore,
    ContextStoreError,
    PendingContextRecord,
)
from ocr_toolkit.diagrams.contracts import (
    DiagramError,
    DiagramMode,
    DiagramResult,
    diagram_requested,
    parse_diagram_mode,
)
from ocr_toolkit.diagrams.lifecycle import DiagramExecution, diagram_warning
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.diagrams.persistence import diagram_payload
from ocr_toolkit.evidence.actions import read_action_receipt
from ocr_toolkit.evidence.artifacts import (
    EvidenceArtifacts,
    ReviewRunBusy,
    locked_review_run,
    prepare_artifact_directory,
    remove_private_artifact,
    repository_artifacts,
    write_private_bytes,
    write_private_text,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.gitlink_projection import (
    GitlinkProjection,
    RawDiffEntry,
    gitlink_selection_proof,
    make_gitlink_projection,
    qualify_gitlink_manifest,
    qualify_gitlink_preview,
    verify_gitlink_projection,
)
from ocr_toolkit.evidence.gitlinks import changed_gitlinks, plan_gitlink_input
from ocr_toolkit.evidence.invocation import collect_invocation_evidence
from ocr_toolkit.evidence.mcp import (
    COVERAGE_TOOL_NAME,
    SEARCH_TOOL_NAME,
    TOOL_NAME,
    call_tool,
    evidence_summary,
)
from ocr_toolkit.evidence.opaque_code import OpaqueCodeProof, prove_opaque_code
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    ShallowAncestryUnavailable,
    normalize_repo_path,
)
from ocr_toolkit.evidence.review_context import (
    MergeRequestContext,
    ReviewContextModeError,
    merge_request_context_record,
    parse_review_context_mode,
)
from ocr_toolkit.evidence.review_range import resolve_review_range
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from ocr_toolkit.federation import start_gateway
from ocr_toolkit.federation.contracts import Registry
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    PARTIAL_TOOLKIT_RESULT_SCHEMA_VERSION,
    PUBLIC_REVIEW_TOOL_CALL_NAMES,
    TOOLKIT_ADVISORY_KEY,
    TOOLKIT_GITLINK_SELECTION_KEY,
    TOOLKIT_PRIVATE_DIAGNOSTIC_KEY,
    TOOLKIT_RESULT_KEY,
    TOOLKIT_RESULT_SCHEMA_VERSION,
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    OcrToolkitAdvisory,
    background_recommended_advisory,
    inspect_ocr_result,
    load_ocr_result,
    toolkit_advisory_payload,
    transform_ocr_result,
)
from ocr_toolkit.posting.comments import compact_text
from ocr_toolkit.posting.result import ocr_warning_text
from ocr_toolkit.pre_execution import (
    BACKGROUND_CHARACTER_LIMIT_REASON,
    BACKGROUND_FILE_SIZE_LIMIT_REASON,
    GITLAB_MERGE_REQUEST_TERMINAL,
    GITLINK_NO_REVIEWABLE_FILES,
    GITLINK_PROJECTION_UNQUALIFIED,
    GITLINK_STATUS_SCHEMA,
    OCR_PREVIEW_STAGE,
    PROTECTED_POLICY_RULE_PATH_PENDING,
    PROTECTED_TARGET_RULE_PATH_PENDING,
    REVIEW_IDENTITY_UNAVAILABLE,
    REVIEWED_REVISION_NO_LONGER_CURRENT,
    STATUS_SCHEMA,
    UNCLASSIFIED_PREVIEW_DIAGNOSTICS,
    PreExecutionStatus,
    PreExecutionStatusError,
    write_pre_execution_status,
)
from ocr_toolkit.provider_config import REASONING_EFFORTS
from ocr_toolkit.provider_failure import (
    ProviderFailureProjection,
    provider_failure_projection,
    render_provider_diagnostics,
)
from ocr_toolkit.providers.gitlab import (
    GitLabMergeRequestStale,
    GitLabMergeRequestTerminal,
    GitLabProviderError,
    acquire_review_snapshot,
    invocation_identifiers,
    is_merge_request_environment,
)
from ocr_toolkit.providers.gitlab_ci import acquire_gitlab_ci_outcomes
from ocr_toolkit.providers.gitlab_discussions import acquire_gitlab_context
from ocr_toolkit.providers.local import (
    local_report_parts,
    prepare_local_report_path,
    publish_local_report,
    write_local_report,
)
from ocr_toolkit.providers.local_config import validate_local_context
from ocr_toolkit.reporting.federation import reconcile as reconcile_federation
from ocr_toolkit.reporting.model import (
    ExecutionFacts,
    FailureStage,
    ReviewReport,
    failed_report,
    report_from_result,
)
from ocr_toolkit.repository_coverage import RepositoryCoverage, coverage_from_projection
from ocr_toolkit.result_contract import OcrResultContractError, ReviewOutcome, parse_result_outcome
from ocr_toolkit.result_usage import normalize_token_usage, token_usage_mapping
from ocr_toolkit.review_debug import DebugBundle, DebugStatus
from ocr_toolkit.review_identity import validate_detached_merge_request_pipeline
from ocr_toolkit.review_progress import ReviewProgress, progress_enabled
from ocr_toolkit.review_range import ReviewRange, admit_native_range, range_payload
from ocr_toolkit.review_receipt import toolkit_receipt_is_valid, verified_evidence_actions

STDERR_PROBE_BYTES = 64 * 1024
BACKGROUND_PREVIEW_STDERR_BYTES = 64 * 1024
DEFAULT_DIAGNOSTIC_CHARS = 4_000
DLP_REASONS = ("forbidden", "invalid_text", "laundering", "limit", "pii", "secret")
PRIVATE_DLP_DECISIONS_SCHEMA = "ocr.private-dlp-decisions/v1"
PRIVATE_DLP_MAX_DECISIONS = 1_000
PRIVATE_DLP_MAX_PATH_DEPTH = 32
PRIVATE_DLP_PATH_SEGMENT_BUDGETS = TextBudgets(max_chars=256, max_bytes=1_024, max_lines=1)
BACKGROUND_SOFT_WARNING_RE = re.compile(
    r"\[ocr\] --background-file content is ([0-9]{1,12}) characters, exceeding the "
    r"recommended ([0-9]{1,12}) \(continuing but review quality might be impacted\)\n?\Z"
)
MAX_TOOLS_NORMALIZATION_RE = re.compile(
    r"\[ocr\] --max-tools ([0-9]{1,12}) is below minimum ([0-9]{1,12}), "
    r"using ([0-9]{1,12})\n?\Z"
)
BACKGROUND_HARD_CHARACTER_RE = re.compile(
    r"Error: background content is ([0-9]{1,12}) characters, exceeding the hard limit of "
    r"([0-9]{1,12}) \(aborting\)\n?\Z"
)
BACKGROUND_HARD_FILE_RE = re.compile(
    r'Error: background file "[^"\r\n]+" is ([0-9]{1,12}) bytes, exceeding the maximum '
    r"of ([0-9]{1,12}) bytes; please provide a smaller file\n?\Z"
)
QUARANTINE_COMMENT_FIELDS = frozenset(
    {
        "category",
        "content",
        "end_line",
        "existing_code",
        "line",
        "old_path",
        "path",
        "priority",
        "rule_id",
        "severity",
        "start_line",
        "suggestion_code",
    }
)
PROVIDER_PRIVATE_RESULT_KEYS = frozenset(
    {
        "encrypted_content",
        "native_payload",
        "reasoning_content",
        "redacted_thinking",
        "thinking",
        "tool_choice",
    }
)
OCR_RAW_LOGGING_ENV = "OCR_RAW_LOGGING"
MAX_TOOL_FAILURE_DETAILS_LOGGED = 20
MAX_TOOL_FAILURE_NAME_CHARS = 256
MAX_TOOL_FAILURE_PATH_CHARS = 4_096
MAX_TOOL_FAILURE_ERROR_CHARS = 32_768
MAX_TOOL_FAILURE_ARGUMENT_CHARS = 32_768
MAX_TOOL_FAILURE_ARGUMENT_BYTES = 131_072
MAX_TOOL_FAILURE_LOG_FIELD_CHARS = 500


class ReviewRunnerError(Exception):
    """OCR execution or result admission failed safely."""


class ReviewRunnerNoHandoff(ReviewRunnerError):
    """Review setup stopped before this run could invalidate prior handoff state."""


class ReviewRunnerBusy(ReviewRunnerNoHandoff):
    """Another review owns this checkout's fixed private review artifacts."""


class ReviewRejected(ReviewRunnerError):
    """Carry closed admission facts without guessing the execution cause."""

    def __init__(self, reason: str, outcome: ReviewOutcome, calls: int | None) -> None:
        self.reason = reason
        self.calls = calls
        self.outcome = outcome
        reported = "unavailable" if calls is None else str(calls)
        detail = (
            "required evidence use was not confirmed by OCR result telemetry"
            if reason == "evidence-use-unconfirmed"
            else "mandatory evidence summary action attribution was not confirmed"
            if outcome.requires_evidence_mcp
            else "evidence action attribution was not confirmed"
        )
        super().__init__(
            f"{detail} (reported calls: {reported}; reason={reason}). "
            "Result not accepted for publication or automatic approval."
        )

    def diagnostic(self) -> str:
        """Render only parser-validated outcome and coverage counters."""
        coverage = self.outcome.coverage_summary
        return f"Review rejected: {self} outcome={self.outcome.kind}" + (
            f"; {coverage}" if coverage else ""
        )


@dataclass(frozen=True, slots=True)
class ToolFailureDetail:
    """Carry one validated OCR diagnostic before bounded CI rendering."""

    number: int
    tool: str
    path: str | None
    error: str


@dataclass(frozen=True, slots=True)
class ToolFailureTelemetry:
    """Separate additive OCR diagnostics from the authoritative review result."""

    present: bool
    valid: bool
    failed: int | None
    by_tool: dict[str, int]
    details: tuple[ToolFailureDetail, ...]


def _ocr_child_environment() -> dict[str, str]:
    """Keep configured OCR inputs while disabling unowned raw provider capture."""

    environment = dict(os.environ)
    environment.pop(OCR_RAW_LOGGING_ENV, None)
    return environment


@dataclass(frozen=True, slots=True)
class BackgroundQualification:
    """Carry closed toolkit-authored projections of installed OCR diagnostics."""

    advisory: OcrToolkitAdvisory | None = None
    operator_notices: tuple[str, ...] = ()
    selected_diff: tuple[RawDiffEntry, ...] = ()


class BackgroundQualificationRejected(ReviewRunnerError):
    """Carry only a closed installed-OCR background rejection."""

    def __init__(self, *, reason: str, actual: int, limit: int, unit: str) -> None:
        super().__init__("installed OCR rejected the review background before model execution")
        self.reason = reason
        self.actual = actual
        self.limit = limit
        self.unit = unit


class BackgroundPreviewUnclassified(ReviewRunnerError):
    """One bounded, unqualified pre-model preview diagnostic outcome."""

    def __init__(self, diagnostic_count: int) -> None:
        super().__init__("OCR background preview diagnostics could not be qualified")
        self.diagnostic_count = max(1, min(diagnostic_count, 1024))


def _install_termination_handlers() -> dict[int, object]:
    """Translate default process termination into an unwind through private cleanup."""

    if threading.current_thread() is not threading.main_thread():
        return {}
    previous_handlers: dict[int, object] = {}

    def interrupt(signum: int, _frame: object) -> None:
        raise ReviewRunnerError(f"OCR review interrupted by signal {signum}")

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous = signal.getsignal(signum)
        if previous not in {signal.SIG_DFL, signal.default_int_handler}:
            continue
        try:
            signal.signal(signum, interrupt)
        except (OSError, ValueError):
            continue
        previous_handlers[int(signum)] = previous
    return previous_handlers


def _restore_termination_handlers(previous_handlers: dict[int, object]) -> None:
    """Restore every process handler replaced for one review invocation."""

    for signum, previous in previous_handlers.items():
        try:
            signal.signal(signum, previous)  # type: ignore[arg-type]
        except (OSError, ValueError):
            # Cleanup must still run if the host changes signal ownership mid-review.
            continue


def _block_termination_signals() -> set[int | signal.Signals] | None:
    """Defer termination until private cleanup and result projection are complete."""

    if threading.current_thread() is not threading.main_thread() or not hasattr(
        signal, "pthread_sigmask"
    ):
        return None
    try:
        return signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    except (OSError, ValueError):
        return None


def _restore_signal_mask(previous_mask: set[int | signal.Signals] | None) -> None:
    """Restore the caller's signal mask after cleanup has reached a safe state."""

    if previous_mask is None or not hasattr(signal, "pthread_sigmask"):
        return
    try:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    except (OSError, ValueError):
        return


@dataclass(frozen=True, slots=True)
class ReviewRefs:
    """Name the immutable base and head refs represented by one OCR review."""

    base: str
    head: str


@dataclass(slots=True)
class ReviewRunState:
    """Track the actual execution owner reached and its admitted report."""

    local: bool = False
    stage: FailureStage = "configuration"
    reviewed_sha: str = ""
    report: ReviewReport | None = None
    debug: DebugBundle | None = None
    progress: ReviewProgress | None = None
    repository_coverage: RepositoryCoverage | None = None
    gitlink_unqualified: bool = False
    diagram_mode: DiagramMode = "on"

    def enter(self, stage: FailureStage) -> None:
        """Enter a real execution phase and notify the optional progress observer."""

        self.stage = stage
        if self.progress is not None:
            self.progress.phase(stage)

    def observe(
        self, stage: FailureStage, status: DebugStatus, *, facts: dict[str, object] | None = None
    ) -> None:
        """Record a result only when the production owner reaches that branch."""

        if self.debug is not None:
            self.debug.phase(stage, status, facts=facts)

    def admit_report(self, report: ReviewReport) -> None:
        """Accept only the finalizer's result after its atomic safe replacement."""

        self.report = report


@dataclass(frozen=True, slots=True)
class ReviewIdentity:
    """Bind immutable review/provider identities to context selection."""

    source_sha: str
    policy_sha: str
    mr_author_id: int | None
    context_mode: str
    context: MergeRequestContext | None
    target_sha: str
    target_protection: str
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

    @property
    def context_state(self) -> str:
        if self.context_mode == "off":
            return "disabled"
        return self.context.state if self.context is not None else "degraded"

    @property
    def has_protected_policy(self) -> bool:
        return self.policy_protection == "protected" or (
            self.policy_protection is None and self.target_protection == "protected"
        )

    @property
    def limited_unprotected(self) -> bool:
        return self.target_protection == "unprotected" and not self.has_protected_policy


def _status_review(identity: ReviewIdentity) -> dict[str, object] | None:
    """Carry the exact authenticated current tuple for a possible GitLab note."""

    if identity.mr_author_id is None:
        return None
    return {
        "source_sha": identity.source_sha,
        "diff_base_sha": identity.diff_base_sha,
        "diff_start_sha": identity.diff_start_sha,
        "diff_head_sha": identity.diff_head_sha,
        "diff_version_id": identity.diff_version_id,
        "project_id": identity.project_id,
        "merge_request_iid": identity.merge_request_iid,
        "target_branch": identity.target_branch,
        "target_sha": identity.target_sha,
        "target_protection": identity.target_protection,
        "policy_project_id": identity.policy_project_id,
        "policy_branch": identity.policy_branch,
        "policy_sha": identity.policy_sha,
        "policy_protection": identity.policy_protection,
        "protection_mode": identity.protection_mode,
        "mr_author_id": identity.mr_author_id,
        **({"ci_job_id": identity.ci_job_id} if identity.ci_job_id is not None else {}),
    }


@dataclass(frozen=True, slots=True)
class EnrichmentReceipt:
    """Carry closed context facts after acquisition and cleanup."""

    policy_digest: str
    completeness: dict[str, str]
    degradation_counts: dict[str, int]
    required_degraded: bool
    mutable_admitted: bool
    forbidden_publication: tuple[str, ...]
    bootstrap_hints: dict[str, int]
    forbidden_sources: tuple[ForbiddenValue, ...] = ()
    legacy_policy: bool = False


def _write_isolated_runtime_config(
    *, debug: DebugBundle | None = None, local: bool = False
) -> None:
    """Rebuild only validated runtime settings inside the fresh OCR home."""

    updates = configure.build_config_updates(**({"local": True} if local else {}))
    update_ocr_config(updates)
    if debug is not None:
        native = updates.get("providers.chatgpt")
        native = native if isinstance(native, dict) else None
        protocol = "openai-responses" if native is not None else updates["llm.protocol"]
        body = native.get("extra_body") if native is not None else updates.get("llm.extra_body")
        model = native.get("model", "") if native is not None else updates["llm.model"]
        reasoning = body.get("reasoning") if isinstance(body, dict) else None
        effort = (
            reasoning.get("effort")
            if protocol == "openai-responses" and isinstance(reasoning, dict)
            else body.get("reasoning_effort")
            if protocol == "openai" and isinstance(body, dict)
            else None
        )
        debug.phase(
            "configuration",
            "passed",
            facts={
                "provider": "local",
                "context_mode": "off",
                "output_format": "json",
                "audience": "agent",
                "llm_protocol": protocol,
                "review_effort": updates["effort"],
                "language": updates["language"],
                "llm_model_sha256": hashlib.sha256(model.encode("utf-8")).hexdigest(),
                "extra_body_present": body is not None,
                "extra_headers_present": "llm.extra_headers" in updates,
                "telemetry_enabled": updates["telemetry.enabled"],
                "content_logging": updates["telemetry.content_logging"],
                **(
                    {"reasoning_effort": effort}
                    if isinstance(effort, str) and effort in REASONING_EFFORTS
                    else {}
                ),
            },
        )


def _verify_evidence_mcp(store: EvidenceStore) -> None:
    """Exercise summary, paginated list, and stable-ID get before starting OCR."""

    summary = call_tool(store, {"action": "summary"})
    if summary.get("isError") is True:
        raise ReviewRunnerError("OCR evidence MCP summary self-query failed")
    listed = call_tool(store, {"action": "list", "ref": "head", "page_size": 1})
    if listed.get("isError") is True:
        raise ReviewRunnerError("OCR evidence MCP list self-query failed")
    content = listed.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned an invalid envelope")
    text = content[0].get("text")
    if not isinstance(text, str):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid text")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid JSON") from exc
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid records")
    if records:
        record_id = records[0].get("id") if isinstance(records[0], dict) else None
        fetched = call_tool(store, {"action": "get", "id": record_id})
        if fetched.get("isError") is True:
            raise ReviewRunnerError("OCR evidence MCP get self-query failed")


def _review_receipt(
    payload: dict[str, object],
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
    enrichment: EnrichmentReceipt | None = None,
    evidence_action_counts: dict[str, dict[str, int]] | None = None,
    *,
    dlp_enabled: bool = True,
    review_range: ReviewRange | None = None,
    diagram: DiagramResult | None = None,
) -> dict[str, object]:
    """Return a closed privacy-safe receipt tied to review-time facts."""

    try:
        outcome = parse_result_outcome(payload)
    except OcrResultContractError as exc:
        raise ReviewRunnerError(f"OCR result has an unsupported outcome contract: {exc}") from exc

    tool_calls = payload.get("tool_calls")
    if tool_calls is None and "tool_calls" in payload:
        raise ReviewRunnerError("OCR result has malformed MCP usage telemetry")
    if tool_calls is None and outcome.requires_evidence_mcp:
        raise ReviewRejected("evidence-use-unconfirmed", outcome, None)
    by_tool = tool_calls.get("by_tool") if isinstance(tool_calls, dict) else None
    total_calls = tool_calls.get("total") if isinstance(tool_calls, dict) else None
    if tool_calls is None and outcome.kind == "failed":
        by_tool = {}
        total_calls = 0
    elif not isinstance(tool_calls, dict) or not isinstance(by_tool, dict):
        raise ReviewRunnerError("OCR result has inconsistent aggregate MCP usage")
    failure_telemetry = _tool_failure_telemetry(tool_calls)
    if outcome.kind == "skipped":
        legacy_message_invalid = (
            not outcome.manifest_present and payload.get("message") != "No supported files changed."
        )
        if (
            legacy_message_invalid
            or payload.get("comments") != []
            or not isinstance(tool_calls, dict)
            or tool_calls.get("total") != 0
            or by_tool != {}
        ):
            raise ReviewRunnerError(
                "OCR skipped result does not match the pinned no-supported-files contract"
            )

    owners = {
        tool: capability.server
        for capability in composition.capabilities
        for tool in capability.tools
    }
    usage: dict[str, int] = {}
    if isinstance(by_tool, dict):
        for tool, count in by_tool.items():
            if not isinstance(tool, str) or tool not in owners:
                continue
            if (
                not isinstance(count, int)
                or isinstance(count, bool)
                or not (
                    0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
                    if tool == TOOL_NAME
                    else 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
                )
            ):
                raise ReviewRunnerError("OCR result has an invalid known MCP usage count")
            owner = owners[tool]
            aggregate = usage.get(owner, 0) + count
            if aggregate > MAX_TOOLKIT_MCP_USAGE_COUNT:
                raise ReviewRunnerError("OCR result exceeds the per-server MCP usage bound")
            usage[owner] = aggregate
    known_usage_total = sum(usage.values())
    if (
        not isinstance(total_calls, int)
        or isinstance(total_calls, bool)
        or not 0 <= total_calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or total_calls < known_usage_total
    ):
        raise ReviewRunnerError("OCR result has inconsistent aggregate MCP usage")
    evidence_by_tool = {
        name: by_tool.get(name, 0) if isinstance(by_tool, dict) else 0
        for name in (TOOL_NAME, SEARCH_TOOL_NAME, COVERAGE_TOOL_NAME)
    }
    evidence_calls = sum(evidence_by_tool.values())
    if outcome.requires_evidence_mcp and not evidence_by_tool[TOOL_NAME]:
        reported = 0 if total_calls == 0 else by_tool.get(TOOL_NAME)
        raise ReviewRejected("evidence-use-unconfirmed", outcome, reported)
    try:
        action_attribution = verified_evidence_actions(
            evidence_by_tool,
            evidence_action_counts,
            mandatory=outcome.requires_evidence_mcp,
        )
    except ValueError as exc:
        raise ReviewRejected(
            "evidence-action-attribution-invalid", outcome, evidence_by_tool[TOOL_NAME]
        ) from exc
    completed = action_attribution.get("completed")
    failure_state = (
        "absent"
        if not failure_telemetry.present
        else "invalid"
        if not failure_telemetry.valid
        else "verified"
    )
    if failure_telemetry.valid and failure_telemetry.present and isinstance(completed, dict):
        completed_by_tool = {
            TOOL_NAME: sum(completed.get(name, 0) for name in ("summary", "list", "get")),
            SEARCH_TOOL_NAME: completed.get("search", 0),
            COVERAGE_TOOL_NAME: completed.get("coverage", 0),
        }
        if any(
            completed_by_tool[name]
            > evidence_by_tool[name] - failure_telemetry.by_tool.get(name, 0)
            for name in completed_by_tool
        ):
            # The private action receipt is recorded by the toolkit MCP owner and
            # remains the authority for completed evidence. OCR's additive
            # diagnostic counters must not discard a valid review when the two
            # observations disagree.
            failure_state = "conflicting"
    completed_actions = action_attribution.get("completed")
    evidence_used = (
        isinstance(completed_actions, dict)
        and all(isinstance(count, int) for count in completed_actions.values())
        and sum(completed_actions.values()) > 0
    )
    capabilities = [
        {
            "server": capability.server,
            "transport": "builtin" if capability.builtin else capability.transport,
            "tools": list(capability.tools),
        }
        for capability in composition.capabilities
    ]
    context_classes = []
    if identity.context_mode in {"metadata", "enriched"}:
        context_classes.append("merge_request_metadata")
    if identity.context_mode == "enriched":
        context_classes.extend(("forge_discussions", "external_records"))
    context_receipt: dict[str, object] = {
        "mode": identity.context_mode,
        "state": identity.context_state,
        "classes": context_classes,
        "policy_digest": None,
        "per_source": {},
        "degradation_counts": {"invalid": 0, "limit": 0, "unavailable": 0},
        "required_degraded": False,
        "mutable_admitted": False,
        "legacy_policy": False,
        "tool_usage": {"context_get": 0, "context_list": 0},
    }
    if enrichment is not None:
        context_receipt.update(
            {
                "state": "degraded" if enrichment.required_degraded else "complete",
                "policy_digest": enrichment.policy_digest,
                "per_source": enrichment.completeness,
                "degradation_counts": enrichment.degradation_counts,
                "required_degraded": enrichment.required_degraded,
                "mutable_admitted": enrichment.mutable_admitted,
                "legacy_policy": enrichment.legacy_policy,
                "tool_usage": {
                    "context_get": (
                        by_tool.get("context_get", 0) if isinstance(by_tool, dict) else 0
                    ),
                    "context_list": (
                        by_tool.get("context_list", 0) if isinstance(by_tool, dict) else 0
                    ),
                },
            }
        )
    return {
        "review": {
            "source_sha": identity.source_sha,
            "diff_base_sha": identity.diff_base_sha,
            "diff_start_sha": identity.diff_start_sha,
            "diff_head_sha": identity.diff_head_sha,
            "diff_version_id": identity.diff_version_id,
            "project_id": identity.project_id,
            "merge_request_iid": identity.merge_request_iid,
            "target_branch": identity.target_branch,
            "policy_sha": identity.policy_sha,
            "target_sha": identity.target_sha,
            "target_protection": identity.target_protection,
            "policy_project_id": identity.policy_project_id,
            "policy_branch": identity.policy_branch,
            "policy_protection": identity.policy_protection,
            "protection_mode": identity.protection_mode,
            "mr_author_id": identity.mr_author_id,
            **({"ci_job_id": identity.ci_job_id} if identity.ci_job_id is not None else {}),
        },
        "context": context_receipt,
        "mcp": {
            "capabilities": capabilities,
            "usage": dict(sorted(usage.items())),
            "federation": (
                reconcile_federation(
                    composition.federation_receipt,
                    by_tool,
                    {
                        tool
                        for cap in composition.capabilities
                        if not cap.builtin
                        for tool in cap.tools
                    },
                )
                if composition.external_servers
                else None
            ),
        },
        "evidence": {
            "mandatory": outcome.requires_evidence_mcp,
            "used": evidence_used,
            "calls": evidence_calls,
            "actions": action_attribution,
        },
        "dlp": {"enabled": dlp_enabled},
        "publication": {"state": "passed"},
        "tool_execution": {
            "state": failure_state,
            "failed": failure_telemetry.failed if failure_state == "verified" else None,
        },
        "cleanup": {"result": "passed"},
        "range": range_payload(review_range),
        "diagram": diagram_payload(diagram or DiagramResult("off", "disabled")),
    }


def _dlp_reasons(
    value: object,
    *,
    budgets: TextBudgets,
    matcher: ForbiddenMatcher,
    allow_horizontal_tabs: bool = False,
    allow_opaque_code: bool = False,
    debug: DebugBundle | None = None,
    path: tuple[object, ...] = (),
    action: str = "detect-sink",
    source_classes: set[str] | None = None,
) -> Counter[str]:
    """Count closed DLP failures without retaining hostile strings or locations."""

    reasons: Counter[str] = Counter()
    stack = [(value, path)]
    while stack:
        nested, nested_path = stack.pop()
        if isinstance(nested, dict):
            for key, value in nested.items():
                if isinstance(key, str) and key in PROVIDER_PRIVATE_RESULT_KEYS:
                    reasons["invalid_text"] += 1
                    if debug is not None:
                        debug.decision(
                            path=(*nested_path, key),
                            action=action,
                            reason="invalid_text",
                            detector="reserved_field",
                            value=key,
                        )
                stack.extend(((key, (*nested_path, key)), (value, (*nested_path, key))))
        elif isinstance(nested, list):
            stack.extend((item, (*nested_path, index)) for index, item in enumerate(nested))
        elif isinstance(nested, str):
            checked = check_text(
                nested,
                budgets=budgets,
                publication=True,
                forbidden_matcher=matcher,
                allow_horizontal_tabs=allow_horizontal_tabs,
                allow_opaque_code=allow_opaque_code,
            )
            if not checked.admitted:
                reasons[checked.reason] += 1
                if source_classes is not None:
                    source_classes.update(checked.source_classes)
                if debug is not None:
                    debug.decision(
                        path=nested_path,
                        action=action,
                        reason=checked.reason,
                        detector=checked.detector,
                        value=nested,
                    )
    return reasons


def _code_field_allows_horizontal_tabs(path: tuple[object, ...]) -> bool:
    """Allow HTAB only in the two closed code-bearing finding fields."""

    return bool(
        len(path) == 3
        and path[0] == "comments"
        and isinstance(path[1], int)
        and path[2] in {"existing_code", "suggestion_code"}
    )


def _private_dlp_decisions(
    payload: dict[str, object], *, forbidden: tuple[str, ...]
) -> dict[str, object]:
    """Attribute rejected DLP values without retaining their content."""

    budgets = TextBudgets(max_chars=2_000_000, max_bytes=8_000_000, max_lines=100_000)
    matcher = ForbiddenMatcher.compile(forbidden)
    decisions: list[dict[str, object]] = []
    rejected = 0

    def bounded_path(path: tuple[object, ...], component: object) -> tuple[object, ...]:
        if len(path) < PRIVATE_DLP_MAX_PATH_DEPTH:
            return (*path, component)
        return (*path[: PRIVATE_DLP_MAX_PATH_DEPTH - 1], "<truncated-path>")

    def add_decision(decision: dict[str, object]) -> None:
        nonlocal rejected
        rejected += 1
        if len(decisions) < PRIVATE_DLP_MAX_DECISIONS:
            decisions.append(decision)

    stack: list[tuple[object, tuple[object, ...]]] = [(payload, ())]
    while stack:
        value, path = stack.pop()
        if isinstance(value, dict):
            for key, nested in value.items():
                checked_key = check_text(
                    key,
                    budgets=PRIVATE_DLP_PATH_SEGMENT_BUDGETS,
                    publication=True,
                    forbidden_matcher=matcher,
                )
                safe_key = key if checked_key.admitted else "<rejected-key>"
                child_path = bounded_path(path, safe_key)
                if not checked_key.admitted:
                    encoded = key.encode("utf-8")
                    add_decision(
                        {
                            "path": list(child_path),
                            "scope": "key",
                            "action": "reject-key",
                            "reason": checked_key.reason,
                            "detector": checked_key.detector,
                            "value_type": "string",
                            "characters": len(key),
                            "bytes": len(encoded),
                            "lines": key.count("\n") + 1,
                            "sha256": hashlib.sha256(encoded).hexdigest(),
                        }
                    )
                stack.append((nested, child_path))
            continue
        if isinstance(value, list):
            stack.extend((nested, bounded_path(path, index)) for index, nested in enumerate(value))
            continue
        if not isinstance(value, str):
            continue
        checked = check_text(
            value,
            budgets=budgets,
            publication=True,
            forbidden_matcher=matcher,
            allow_horizontal_tabs=_code_field_allows_horizontal_tabs(path),
        )
        if checked.admitted:
            continue
        encoded = value.encode("utf-8")
        add_decision(
            {
                "path": list(path),
                "scope": "value",
                "action": "reject-value",
                "reason": checked.reason,
                "detector": checked.detector,
                "value_type": "string",
                "characters": len(value),
                "bytes": len(encoded),
                "lines": value.count("\n") + 1,
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }
        )
    return {
        "schema_version": PRIVATE_DLP_DECISIONS_SCHEMA,
        "truncated": rejected > len(decisions),
        "omitted_decisions": rejected - len(decisions),
        "decisions": sorted(
            decisions,
            key=lambda item: json.dumps(item["path"], separators=(",", ":")),
        ),
    }


def _write_private_dlp_decisions(
    result_path: Path,
    artifact_path: Path,
    *,
    forbidden: tuple[str, ...],
) -> None:
    """Write the local-only pre-publication DLP attribution sidecar."""

    try:
        payload = inspect_ocr_result(result_path)
        if not isinstance(payload, dict):
            raise OcrResultMalformed("OCR result JSON must be an object")
        decisions = _private_dlp_decisions(payload, forbidden=forbidden)
        write_private_bytes(
            artifact_path,
            json.dumps(
                decisions,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
        )
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge, OSError) as exc:
        raise ReviewRunnerError("OCR private DLP diagnostics could not be written") from exc


def _publication_sinks(payload: dict[str, object]) -> list[tuple[object, bool, tuple[object, ...]]]:
    """Select only OCR-controlled values that the posting owner can render."""

    sinks: list[tuple[object, bool, tuple[object, ...]]] = []
    message = payload.get("message")
    if message is not None:
        sinks.append((message, False, ("message",)))
    comments = payload.get("comments")
    if isinstance(comments, list):
        for index, item in enumerate(comments):
            if not isinstance(item, dict):
                continue
            sinks.extend(
                (
                    value,
                    isinstance(value, str) and key in {"existing_code", "suggestion_code"},
                    ("comments", index, key),
                )
                for key, value in item.items()
                if key in QUARANTINE_COMMENT_FIELDS
            )
    warnings = payload.get("warnings")
    if warnings is not None:
        sinks.append((warnings, False, ("warnings",)))
    manifest = payload.get("manifest")
    coverage = manifest.get("coverage") if isinstance(manifest, dict) else None
    failed = coverage.get("failed") if isinstance(coverage, dict) else None
    if isinstance(failed, list):
        for index, item in enumerate(failed):
            if isinstance(item, dict):
                sinks.extend(
                    (item[key], False, ("manifest", "coverage", "failed", index, key))
                    for key in ("path", "reason")
                    if key in item
                )
    return sinks


def _is_publication_sink_path(path: tuple[object, ...]) -> bool:
    """Return whether one result path can reach toolkit GitLab rendering."""

    if path == ("message",) or (path and path[0] == "warnings"):
        return True
    if (
        len(path) >= 3
        and path[0] == "comments"
        and isinstance(path[1], int)
        and path[2] in QUARANTINE_COMMENT_FIELDS
    ):
        return True
    return bool(
        len(path) >= 5
        and path[:3] == ("manifest", "coverage", "failed")
        and isinstance(path[3], int)
        and path[4] in {"path", "reason"}
    )


def _is_static_public_tool_key_path(path: tuple[object, ...]) -> bool:
    """Return whether a map key is one compile-time public tool label."""

    return bool(
        len(path) == 3
        and path[:2] == ("tool_calls", "by_tool")
        and path[2] in PUBLIC_REVIEW_TOOL_CALL_NAMES
    )


def _sanitize_nonpublication_fields(
    payload: dict[str, object],
    *,
    budgets: TextBudgets,
    matcher: ForbiddenMatcher,
    debug: DebugBundle | None = None,
    source_counts: Counter[str] | None = None,
) -> tuple[dict[str, object], Counter[str], int]:
    """Redact unsafe private result fields without changing publication sinks."""

    sanitized: dict[str, object] = {}
    reasons: Counter[str] = Counter()
    replacements: dict[str, str] = {}
    redacted_fields = 0
    stack: list[
        tuple[
            dict[str, object] | list[object], dict[str, object] | list[object], tuple[object, ...]
        ]
    ] = [(payload, sanitized, ())]
    while stack:
        source, target, path = stack.pop()
        items = source.items() if isinstance(source, dict) else enumerate(source)
        for key, value in items:
            child_path = (*path, key)
            if isinstance(source, dict):
                assert isinstance(key, str)
                if key in PROVIDER_PRIVATE_RESULT_KEYS and not _is_publication_sink_path(
                    child_path
                ):
                    redacted_fields += 1
                    if debug is not None:
                        debug.decision(
                            path=child_path,
                            action="remove-private-field",
                            reason="invalid_text",
                            detector="reserved_field",
                            value=key,
                        )
                    continue
                if not _is_publication_sink_path(
                    child_path
                ) and not _is_static_public_tool_key_path(child_path):
                    checked_key = check_text(
                        key,
                        budgets=budgets,
                        publication=True,
                        forbidden_matcher=matcher,
                    )
                    if not checked_key.admitted:
                        reasons[checked_key.reason] += 1
                        if source_counts is not None:
                            source_counts.update(checked_key.source_classes)
                        redacted_fields += 1
                        if debug is not None:
                            debug.decision(
                                path=child_path,
                                action="reject-key",
                                reason=checked_key.reason,
                                detector=checked_key.detector,
                                value=key,
                            )
                        continue
            if isinstance(value, dict):
                nested: dict[str, object] = {}
                if isinstance(target, dict):
                    target[key] = nested
                else:
                    target.append(nested)
                stack.append((value, nested, child_path))
                continue
            if isinstance(value, list):
                nested_list: list[object] = []
                if isinstance(target, dict):
                    target[key] = nested_list
                else:
                    target.append(nested_list)
                stack.append((value, nested_list, child_path))
                continue
            projected = value
            if isinstance(value, str) and not _is_publication_sink_path(child_path):
                checked = check_text(
                    value,
                    budgets=budgets,
                    publication=True,
                    forbidden_matcher=matcher,
                )
                if not checked.admitted:
                    reasons[checked.reason] += 1
                    if source_counts is not None:
                        source_counts.update(checked.source_classes)
                    redacted_fields += 1
                    if debug is not None:
                        debug.decision(
                            path=child_path,
                            action="redact-value",
                            reason=checked.reason,
                            detector=checked.detector,
                            value=value,
                        )
                    projected = replacements.setdefault(
                        value, f"ocr-redacted-{len(replacements) + 1:06d}"
                    )
            if isinstance(target, dict):
                target[key] = projected
            else:
                target.append(projected)
    return sanitized, reasons, redacted_fields


def _safe_publication_comments(
    value: object,
    *,
    budgets: TextBudgets,
    matcher: ForbiddenMatcher,
    opaque_fields: frozenset[tuple[int, str]] = frozenset(),
    debug: DebugBundle | None = None,
) -> tuple[list[dict[str, object]], int, int]:
    """Retain safe finding fields and omit only findings with unsafe content."""

    if not isinstance(value, list):
        return [], 0, 0
    retained: list[dict[str, object]] = []
    omitted_fields = 0
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        projected: dict[str, object] = {}
        content_unsafe = False
        for key, field_value in item.items():
            if not isinstance(key, str) or key not in QUARANTINE_COMMENT_FIELDS:
                continue
            if _dlp_reasons(
                field_value,
                budgets=budgets,
                matcher=matcher,
                allow_horizontal_tabs=(
                    isinstance(field_value, str) and key in {"existing_code", "suggestion_code"}
                ),
                allow_opaque_code=(index, key) in opaque_fields,
                debug=debug,
                path=("comments", index, key),
                action="omit-field",
            ):
                omitted_fields += 1
                content_unsafe = content_unsafe or key == "content"
                continue
            projected[key] = field_value
        if projected and not content_unsafe:
            retained.append(projected)
        elif debug is not None:
            debug.decision(
                path=("comments", index),
                action="omit-finding",
                reason="unsafe_content" if content_unsafe else "empty_projection",
                detector=None,
                value=None,
            )
    return retained, len(value) - len(retained), omitted_fields


def _safe_publication_warnings(
    value: object,
    *,
    budgets: TextBudgets,
    matcher: ForbiddenMatcher,
    debug: DebugBundle | None = None,
) -> tuple[list[object], int]:
    """Retain DLP-safe warnings while dropping unsafe or malformed items atomically."""

    if not isinstance(value, list):
        return [], 0
    retained = [
        item
        for index, item in enumerate(value)
        if not _dlp_reasons(
            item,
            budgets=budgets,
            matcher=matcher,
            debug=debug,
            path=("warnings", index),
            action="omit-warning",
        )
    ]
    return retained, len(value) - len(retained)


def _bounded_tool_failure_arguments(value: object) -> bool:
    """Validate opaque private arguments without retaining or interpreting their content."""

    if not isinstance(value, str) or len(value) > MAX_TOOL_FAILURE_ARGUMENT_CHARS:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_TOOL_FAILURE_ARGUMENT_BYTES
    except UnicodeEncodeError:
        return False


def _tool_failure_telemetry(value: object) -> ToolFailureTelemetry:
    """Parse additive OCR diagnostics without granting them result authority."""

    if not isinstance(value, dict):
        return ToolFailureTelemetry(False, True, None, {}, ())
    present = {name for name in ("failure", "failure_by_tool", "failure_details") if name in value}
    if not present:
        return ToolFailureTelemetry(False, True, None, {}, ())
    if present != {"failure", "failure_by_tool", "failure_details"}:
        return ToolFailureTelemetry(True, False, None, {}, ())
    total = value.get("total")
    by_tool = value.get("by_tool")
    failed = value.get("failure")
    failed_by_tool = value.get("failure_by_tool")
    details = value.get("failure_details")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or not 0 <= total <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or not isinstance(by_tool, dict)
        or not isinstance(failed, int)
        or isinstance(failed, bool)
        or not 0 <= failed <= total
        or not isinstance(failed_by_tool, dict)
        or len(failed_by_tool) > MAX_TOOLKIT_MCP_USAGE_COUNT
        or not isinstance(details, list)
        or len(details) != failed
    ):
        return ToolFailureTelemetry(True, False, None, {}, ())
    normalized: dict[str, int] = {}
    for name, count in failed_by_tool.items():
        attempted = by_tool.get(name)
        if (
            not isinstance(name, str)
            or not name
            or len(name) > MAX_TOOL_FAILURE_NAME_CHARS
            or not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            or not isinstance(attempted, int)
            or isinstance(attempted, bool)
            or count > attempted
        ):
            return ToolFailureTelemetry(True, False, None, {}, ())
        normalized[name] = count
    if sum(normalized.values()) != failed:
        return ToolFailureTelemetry(True, False, None, {}, ())
    detail_counts: Counter[str] = Counter()
    call_numbers: set[int] = set()
    normalized_details: list[ToolFailureDetail] = []
    for detail in details:
        if not isinstance(detail, dict) or set(detail) not in (
            {"tool_call_number", "tool_name", "error"},
            {"tool_call_number", "tool_name", "file_path", "error"},
            {"tool_call_number", "tool_name", "arguments", "error"},
            {"tool_call_number", "tool_name", "file_path", "arguments", "error"},
        ):
            return ToolFailureTelemetry(True, False, None, {}, ())
        if "arguments" in detail and not _bounded_tool_failure_arguments(detail["arguments"]):
            return ToolFailureTelemetry(True, False, None, {}, ())
        number = detail.get("tool_call_number")
        name = detail.get("tool_name")
        error = detail.get("error")
        file_path = detail.get("file_path")
        if (
            not isinstance(number, int)
            or isinstance(number, bool)
            or not 1 <= number <= total
            or number in call_numbers
            or not isinstance(name, str)
            or name not in normalized
            or not isinstance(error, str)
            or not error
            or len(error) > MAX_TOOL_FAILURE_ERROR_CHARS
            or (
                file_path is not None
                and (not isinstance(file_path, str) or len(file_path) > MAX_TOOL_FAILURE_PATH_CHARS)
            )
        ):
            return ToolFailureTelemetry(True, False, None, {}, ())
        call_numbers.add(number)
        detail_counts[name] += 1
        normalized_details.append(ToolFailureDetail(number, name, file_path, error))
    if dict(detail_counts) != normalized:
        return ToolFailureTelemetry(True, False, None, {}, ())
    normalized_details.sort(key=lambda detail: detail.number)
    return ToolFailureTelemetry(True, True, failed, normalized, tuple(normalized_details))


def _safe_tool_failure_log_field(value: str) -> str:
    """Redact and compact one OCR-controlled field before CI console output."""

    return compact_text(redact_sensitive(value), MAX_TOOL_FAILURE_LOG_FIELD_CHARS)


def _render_tool_failure_diagnostics(telemetry: ToolFailureTelemetry) -> tuple[str, ...]:
    """Render bounded diagnostics for the local/CI console, never MR publication."""

    if not telemetry.present:
        return ()
    if not telemetry.valid:
        return (
            "OCR tool failure diagnostics: malformed additive telemetry ignored; "
            "authoritative review result retained.",
        )
    if not telemetry.failed:
        return ()
    lines = [f"OCR tool failures: {telemetry.failed} failed call(s)."]
    for detail in telemetry.details[:MAX_TOOL_FAILURE_DETAILS_LOGGED]:
        tool = _safe_tool_failure_log_field(detail.tool)
        path = (
            f" path={_safe_tool_failure_log_field(detail.path)}" if detail.path is not None else ""
        )
        error = _safe_tool_failure_log_field(detail.error)
        lines.append(f"- call={detail.number} tool={tool}{path} error={error}")
    omitted = telemetry.failed - min(telemetry.failed, MAX_TOOL_FAILURE_DETAILS_LOGGED)
    if omitted:
        lines.append(f"- ... {omitted} additional failed call(s) omitted")
    return tuple(lines)


def _print_tool_failure_diagnostics(telemetry: ToolFailureTelemetry | None) -> None:
    """Write safe failed-tool detail to the current process stderr/CI job log."""

    if telemetry is None:
        return
    for line in _render_tool_failure_diagnostics(telemetry):
        print(line, file=sys.stderr)


def _closed_tool_calls(
    value: object,
    *,
    allowed_tools: frozenset[str],
    failures: ToolFailureTelemetry | None = None,
) -> dict[str, object]:
    """Project only bounded counters needed to prove model-side toolkit use."""

    if not isinstance(value, dict):
        return {"total": 0, "by_tool": {}}
    total = value.get("total")
    by_tool = value.get("by_tool")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or not 0 <= total <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or not isinstance(by_tool, dict)
    ):
        return {"total": 0, "by_tool": {}}
    projected = {
        tool: count
        for tool, count in by_tool.items()
        if tool in allowed_tools
        and tool in PUBLIC_REVIEW_TOOL_CALL_NAMES
        and isinstance(count, int)
        and not isinstance(count, bool)
        and 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
    }
    closed: dict[str, object] = {
        "total": total,
        "by_tool": dict(sorted(projected.items())),
    }
    if failures is not None and failures.present and failures.valid:
        closed["failure"] = failures.failed
    return closed


def _canonical_result_projection(
    payload: dict[str, object], *, failures: ToolFailureTelemetry | None = None
) -> bytes:
    """Serialize every publication and approval input into one closed comparison."""

    outcome = parse_result_outcome(payload)
    comments = payload.get("comments", [])
    warnings = payload.get("warnings", [])
    if not isinstance(comments, list) or not isinstance(warnings, list):
        raise OcrResultContractError("finding and warning collections must be lists")
    if any(not isinstance(comment, dict) for comment in comments):
        raise OcrResultContractError("every finding must be an object")
    normalized_usage = normalize_token_usage(payload)
    if token_usage_mapping(payload) is not None and normalized_usage is None:
        raise OcrResultContractError("token telemetry is malformed or contradictory")
    projected_comments = [
        {key: value for key, value in comment.items() if key in QUARANTINE_COMMENT_FIELDS}
        if isinstance(comment, dict)
        else comment
        for comment in comments
    ]
    projected_tool_calls = _closed_tool_calls(
        payload.get("tool_calls"),
        allowed_tools=PUBLIC_REVIEW_TOOL_CALL_NAMES,
        failures=failures,
    )
    projection = {
        "outcome": {
            "status": outcome.status,
            "kind": outcome.kind,
            "message": "" if payload.get("message") is None else str(payload["message"]).strip(),
            "budget_exceeded": outcome.budget_exceeded,
            "manifest_present": outcome.manifest_present,
            "selected": outcome.selected_count,
            "completed": outcome.completed_count,
            "reused": outcome.reused_count,
            "failed": outcome.failed_count,
            "waived": outcome.waived_count,
            "failed_items": [
                {
                    "item_id": failure.item_id,
                    "path": failure.path,
                    "classification": failure.classification,
                    "reason": failure.reason,
                }
                for failure in outcome.failed_items
            ],
        },
        "comments": projected_comments,
        "warnings": [ocr_warning_text(warning) for warning in warnings],
        "tool_calls": projected_tool_calls,
        "token_usage": normalized_usage,
    }
    try:
        return json.dumps(
            projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise OcrResultContractError("canonical publication projection is malformed") from exc


def _publication_projection(
    payload: dict[str, object],
    *,
    forbidden: tuple[str | ForbiddenValue, ...],
    allowed_tools: frozenset[str],
    dlp_enabled: bool = True,
    code_proof: Callable[[dict[str, object]], OpaqueCodeProof] | None = None,
    debug: DebugBundle | None = None,
) -> tuple[dict[str, object], dict[str, object], bool]:
    """Return a DLP-safe result plus one disjoint v2 publication state."""

    failures = _tool_failure_telemetry(payload.get("tool_calls"))
    if not dlp_enabled:
        projected = payload
        if failures.present:
            projected = dict(payload)
            projected["tool_calls"] = _closed_tool_calls(
                payload.get("tool_calls"), allowed_tools=allowed_tools, failures=failures
            )
        return projected, {"schema": "ocr.publication/v2", "state": "disabled"}, False

    budgets = TextBudgets(max_chars=2_000_000, max_bytes=8_000_000, max_lines=100_000)
    matcher = ForbiddenMatcher.compile(forbidden)
    opaque_fields: set[tuple[int, str]] = set()
    if code_proof is not None and isinstance(payload.get("comments"), list):
        for index, comment in enumerate(payload["comments"]):
            if not isinstance(comment, dict):
                continue
            proof = code_proof(comment)
            if proof.existing_verified:
                opaque_fields.add((index, "existing_code"))
            if proof.suggestion_verified:
                opaque_fields.add((index, "suggestion_code"))
    verified_opaque_fields = frozenset(opaque_fields)
    sink_reasons: Counter[str] = Counter()
    source_units: dict[tuple[object, ...], set[str]] = {}
    source_counts: Counter[str] = Counter()
    for sink, allow_horizontal_tabs, sink_path in _publication_sinks(payload):
        unit = (
            sink_path[:2] if sink_path and sink_path[0] in {"comments", "warnings"} else sink_path
        )
        sources = source_units.setdefault(unit, set())
        sink_reasons.update(
            _dlp_reasons(
                sink,
                budgets=budgets,
                matcher=matcher,
                allow_horizontal_tabs=allow_horizontal_tabs,
                allow_opaque_code=(
                    len(sink_path) == 3
                    and sink_path[0] == "comments"
                    and (sink_path[1], sink_path[2]) in verified_opaque_fields
                ),
                debug=debug,
                path=sink_path,
                source_classes=sources,
            )
        )
    for sources in source_units.values():
        source_counts.update(sources)
    sanitization_payload = payload
    raw_tool_calls = payload.get("tool_calls")
    if failures.present and isinstance(raw_tool_calls, dict):
        # The details are a validated local/CI diagnostic channel, not an MR
        # publication sink or approval input. Remove them before generic DLP;
        # their dedicated console renderer applies redaction and tighter bounds.
        sanitization_payload = dict(payload)
        sanitization_payload["tool_calls"] = {
            key: value
            for key, value in raw_tool_calls.items()
            if key not in {"failure", "failure_by_tool", "failure_details"}
        }
    sanitized, private_reasons, redacted_fields = _sanitize_nonpublication_fields(
        sanitization_payload,
        budgets=budgets,
        matcher=matcher,
        debug=debug,
        source_counts=source_counts,
    )
    attribution = {
        "schema": "ocr.forbidden-sources/v1",
        "counts": {name: source_counts[name] for name in sorted(FORBIDDEN_SOURCE_CLASSES)},
    }
    if failures.present:
        sanitized["tool_calls"] = _closed_tool_calls(
            payload.get("tool_calls"), allowed_tools=allowed_tools, failures=failures
        )
    if not sink_reasons and not private_reasons and redacted_fields == 0:
        return (
            sanitized if failures.present else payload,
            {"schema": "ocr.publication/v2", "state": "passed"},
            False,
        )

    try:
        original_projection = _canonical_result_projection(payload, failures=failures)
    except OcrResultContractError:
        original_projection = None
    outcome = parse_result_outcome(payload)
    publication_changed = bool(sink_reasons)
    if not publication_changed:
        try:
            publication_changed = original_projection != _canonical_result_projection(
                sanitized, failures=failures
            )
        except OcrResultContractError:
            publication_changed = True
    if publication_changed:
        comments, omitted_comments, omitted_fields = _safe_publication_comments(
            payload.get("comments"),
            budgets=budgets,
            matcher=matcher,
            opaque_fields=verified_opaque_fields,
            debug=debug,
        )
        warnings, omitted_warnings = _safe_publication_warnings(
            payload.get("warnings"), budgets=budgets, matcher=matcher, debug=debug
        )
        projected: dict[str, object] = {
            "status": "budget_exceeded" if outcome.budget_exceeded else "completed_with_errors",
            "message": (
                "Publication projection is incomplete. Independently safe "
                "findings may be published, but the result must not be treated as a complete "
                "review."
            ),
            "comments": comments,
            "warnings": warnings,
            "tool_calls": _closed_tool_calls(
                payload.get("tool_calls"), allowed_tools=allowed_tools, failures=failures
            ),
        }
        if outcome.budget_exceeded:
            projected["summary"] = {"budget_exceeded": True}
    else:
        reasons = sink_reasons + private_reasons
        if not reasons:
            return sanitized, {"schema": "ocr.publication/v2", "state": "passed"}, False
        return (
            sanitized,
            {
                "schema": "ocr.publication/v2",
                "state": "private-sanitized",
                "private_sanitization": {
                    "fields": redacted_fields,
                    "reason_counts": {
                        reason: private_reasons.get(reason, 0) for reason in DLP_REASONS
                    },
                },
                "source_attribution": attribution,
            },
            False,
        )
    publication: dict[str, object] = {
        "schema": "ocr.publication/v2",
        "state": "publication-filtered",
        "source_attribution": attribution,
        "reason_counts": {reason: sink_reasons.get(reason, 0) for reason in DLP_REASONS},
        "private_sanitization": {
            "fields": redacted_fields,
            "reason_counts": {reason: private_reasons.get(reason, 0) for reason in DLP_REASONS},
        },
        "retained": {"comments": len(comments), "warnings": len(warnings)},
        "omitted": {
            "comments": omitted_comments,
            "warnings": omitted_warnings,
            "fields": omitted_fields,
        },
        "original": {
            "outcome": outcome.kind,
            "selected": outcome.selected_count,
            "completed": outcome.completed_count,
            "reused": outcome.reused_count,
            "failed": outcome.failed_count,
            "waived": outcome.waived_count,
        },
    }
    return projected, publication, True


def _retain_private_diagnostic_result(result_path: Path, *, reason: str) -> bool:
    """Mark bounded rejected execution data without granting publication authority."""

    try:
        transform_ocr_result(
            result_path,
            lambda payload: {
                TOOLKIT_PRIVATE_DIAGNOSTIC_KEY: {"reason": reason},
                "result": payload,
            },
        )
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge, OSError):
        print(
            "OCR private diagnostic retention failed; original failure preserved.",
            file=sys.stderr,
        )
        try:
            result_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    print(
        "OCR rejected result retained as private diagnostics; not posting-eligible.",
        file=sys.stderr,
    )
    return True


def _verify_gitlink_after_execution(
    result_path: Path, projection: GitlinkProjection, *, preserve_authorized: bool
) -> None:
    """Reject drift and dispose of raw model output before any publication DLP work."""

    try:
        verify_gitlink_projection(GitRepositoryReader(Path.cwd()), projection)
    except (RepositoryEvidenceError, OSError, subprocess.TimeoutExpired) as exc:
        if preserve_authorized:
            _retain_private_diagnostic_result(result_path, reason="gitlink-input-drift")
        else:
            try:
                result_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise ReviewRunnerError("OCR gitlink inputs drifted during model execution") from exc


def _finalize_ocr_result(
    result_path: Path,
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
    enrichment: EnrichmentReceipt | None,
    evidence_action_counts: dict[str, dict[str, int]] | None = None,
    *,
    forbidden: tuple[str | ForbiddenValue, ...],
    dlp_enabled: bool = True,
    toolkit_advisory: OcrToolkitAdvisory | None = None,
    report_consumer: Callable[[ReviewReport], None] | None = None,
    state: ReviewRunState | None = None,
    private_diagnostics: bool = False,
    projection: GitlinkProjection | None = None,
    selected_diff: tuple[RawDiffEntry, ...] = (),
    expected_range: ReviewRange | None = None,
    diagram_execution: DiagramExecution | None = None,
) -> tuple[dict[str, int], bool, dict[str, object]]:
    """Validate, DLP-project, and receipt-bind one result in one atomic read/replace."""

    filtered = False
    publication: dict[str, object] = {"state": "passed"}
    usage: dict[str, int] = {}
    failure_telemetry = ToolFailureTelemetry(False, True, None, {}, ())
    allowed_tools = PUBLIC_REVIEW_TOOL_CALL_NAMES
    report: ReviewReport | None = None
    source_reader = GitRepositoryReader(Path.cwd())
    source_cache: dict[str, str | None] = {}
    if expected_range is None and projection is not None:
        expected_range = ReviewRange(projection.plan.base_sha, projection.plan.head_sha)
    if expected_range is not None and (
        expected_range.head != identity.source_sha
        or (
            identity.target_protection != "local"
            and (identity.diff_base_sha, identity.diff_head_sha)
            != (expected_range.base, expected_range.head)
        )
    ):
        raise ReviewRunnerError("review range disagrees with the execution identity")

    def read_source(path: str) -> str | None:
        """Read immutable text without sharing optional-channel failure state."""

        try:
            blob = source_reader.read_blob(identity.source_sha, path)
            return blob.decode("utf-8") if blob is not None else None
        except (
            RepositoryEvidenceError,
            UnicodeDecodeError,
            OSError,
            subprocess.TimeoutExpired,
        ):
            return None

    def read_reviewed_head(path: str) -> str | None:
        if path not in source_cache:
            source_cache[path] = read_source(path)
        return source_cache[path]

    def code_proof(comment: dict[str, object]) -> OpaqueCodeProof:
        path = comment.get("path")
        if not isinstance(path, str):
            return OpaqueCodeProof()
        return prove_opaque_code(comment, path, read_reviewed_head)

    def finalize(payload: dict[str, object]) -> dict[str, object]:
        nonlocal failure_telemetry, filtered, publication, usage, report
        for reserved in (
            TOOLKIT_RESULT_KEY,
            TOOLKIT_ADVISORY_KEY,
            TOOLKIT_PRIVATE_DIAGNOSTIC_KEY,
            TOOLKIT_GITLINK_SELECTION_KEY,
        ):
            if reserved in payload:
                raise OcrResultMalformed(f"OCR result contains reserved field {reserved!r}")
        warnings = payload.get("warnings", [])
        if not isinstance(warnings, list):
            raise OcrResultMalformed("OCR result warnings must be a list")
        admitted_range = None
        if expected_range is not None:
            try:
                admitted_range = admit_native_range(payload, expected_range)
            except OcrResultContractError as exc:
                raise ReviewRunnerError(
                    "OCR native manifest did not prove the review range"
                ) from exc
        if projection is not None:
            try:
                qualify_gitlink_manifest(projection, selected_diff, payload)
            except RepositoryEvidenceError as exc:
                raise ReviewRunnerError("OCR gitlink manifest did not prove selected work") from exc
        failure_telemetry = _tool_failure_telemetry(payload.get("tool_calls"))
        if state is not None:
            state.enter("mcp-use")
        metadata = _review_receipt(
            payload,
            composition,
            identity,
            enrichment,
            evidence_action_counts,
            dlp_enabled=dlp_enabled,
            review_range=admitted_range,
        )
        admitted_diagram = DiagramResult("off", "disabled")
        if diagram_execution is not None:
            raw_tools = payload.get("tool_calls")
            raw_counts = raw_tools.get("by_tool", {}) if isinstance(raw_tools, dict) else {}
            calls = raw_counts.get(DIAGRAM_TOOL_NAME, 0) if isinstance(raw_counts, dict) else 0
            failed = (
                failure_telemetry.by_tool.get(DIAGRAM_TOOL_NAME, 0)
                if failure_telemetry.valid
                else 0
            )
            admitted_diagram = diagram_execution.finish(
                review_range=admitted_range,
                calls=calls,
                failed_calls=failed,
                read_source=read_source,
                forbidden_matcher=ForbiddenMatcher.compile(forbidden),
                dlp_enabled=dlp_enabled,
            )
            metadata["diagram"] = diagram_payload(admitted_diagram)
        if state is not None:
            evidence = metadata.get("evidence")
            actions = evidence.get("actions") if isinstance(evidence, dict) else None
            completed = actions.get("completed") if isinstance(actions, dict) else None
            facts = None
            if isinstance(evidence, dict) and isinstance(completed, dict):
                facts = {
                    "used": evidence.get("used"),
                    "summary_completed": completed.get("summary"),
                }
            state.observe("mcp-use", "passed", facts=facts)
            state.enter("dlp")
        projected, publication, filtered = _publication_projection(
            payload,
            forbidden=forbidden,
            allowed_tools=allowed_tools,
            dlp_enabled=dlp_enabled,
            code_proof=code_proof,
            **({"debug": state.debug} if state is not None and state.debug is not None else {}),
        )
        if state is not None:
            state.observe(
                "dlp",
                "degraded" if publication.get("state") != "passed" else "passed",
                facts={"dlp_state": publication["state"]},
            )
            state.enter("result-validation")
        metadata["publication"] = publication
        effective_coverage: RepositoryCoverage | None = None
        if projection is not None:
            effective_coverage = coverage_from_projection(
                projection, selected_diff, state="partial"
            )
            metadata["repository_coverage"] = effective_coverage.payload()
            metadata["schema_version"] = PARTIAL_TOOLKIT_RESULT_SCHEMA_VERSION
        else:
            metadata["schema_version"] = TOOLKIT_RESULT_SCHEMA_VERSION
        provider_receipt = identity.target_protection in {"protected", "unprotected"}
        if provider_receipt:
            if not toolkit_receipt_is_valid(metadata):
                raise ReviewRunnerError("toolkit generated an invalid review receipt")
        elif identity.target_protection != "local" or identity.mr_author_id is not None:
            raise ReviewRunnerError("toolkit generated an invalid review identity")
        mcp = metadata.get("mcp")
        raw_usage = mcp.get("usage") if isinstance(mcp, dict) else None
        usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
        finalized = {**projected, TOOLKIT_RESULT_KEY: metadata} if provider_receipt else projected
        if projection is not None and filtered and provider_receipt:
            finalized[TOOLKIT_GITLINK_SELECTION_KEY] = gitlink_selection_proof(
                projection, selected_diff
            )
        if toolkit_advisory is not None and provider_receipt:
            finalized[TOOLKIT_ADVISORY_KEY] = toolkit_advisory_payload(toolkit_advisory)
        if report_consumer is not None and (
            not private_diagnostics
            or (identity.target_protection == "local" and identity.mr_author_id is None)
        ):
            evidence = metadata.get("evidence")
            if not isinstance(evidence, dict):
                raise ReviewRunnerError("verified evidence facts are unavailable")
            try:
                report = report_from_result(
                    projected,
                    execution=ExecutionFacts(
                        usage,
                        evidence,
                        publication,
                        toolkit_advisory,
                        mcp.get("federation") if isinstance(mcp, dict) else None,
                        enrichment.legacy_policy if enrichment is not None else False,
                        effective_coverage,
                        review_range=admitted_range,
                        diagram=admitted_diagram,
                    ),
                    reviewed_sha=identity.source_sha,
                )
            except OcrResultContractError as exc:
                raise ReviewRunnerError("admitted review report is inconsistent") from exc
        if private_diagnostics:
            return {**payload, TOOLKIT_PRIVATE_DIAGNOSTIC_KEY: {"reason": "private-retention"}}
        return finalized

    try:
        transform_ocr_result(result_path, finalize)
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge) as exc:
        if private_diagnostics:
            try:
                result_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise ReviewRunnerError("OCR result is not valid bounded JSON") from exc
    except ReviewRunnerError as exc:
        if isinstance(exc, ReviewRejected):
            print(exc.diagnostic(), file=sys.stderr)
        retained = False
        if private_diagnostics:
            reason = exc.reason if isinstance(exc, ReviewRejected) else "result-validation-failed"
            retained = _retain_private_diagnostic_result(result_path, reason=reason)
        if not retained:
            try:
                result_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    _print_tool_failure_diagnostics(failure_telemetry)
    if state is not None:
        state.observe("result-validation", "passed")
    if report_consumer is not None and report is not None:
        report_consumer(report)
    return usage, filtered, publication


def _record_ocr_result_mcp_usage(
    result_path: Path,
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
    enrichment: EnrichmentReceipt | None = None,
    evidence_action_counts: dict[str, dict[str, int]] | None = None,
) -> dict[str, int]:
    """Verify MCP use and bind the closed review-time receipt to the result."""

    usage, filtered, _publication = _finalize_ocr_result(
        result_path,
        composition,
        identity,
        enrichment,
        evidence_action_counts,
        forbidden=(),
    )
    if filtered:
        raise ReviewRunnerError("OCR result failed publication DLP")
    return usage


def _option_values(args: list[str], name: str, short: str | None = None) -> list[str]:
    """Return values for one bounded OCR option form."""

    values: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument == name or (short is not None and argument == short):
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                raise ReviewRunnerError(f"OCR option {argument} requires a value")
            values.append(args[index + 1])
            index += 2
            continue
        prefix = f"{name}="
        if argument.startswith(prefix):
            value = argument[len(prefix) :]
            if not value:
                raise ReviewRunnerError(f"OCR option {name} requires a value")
            values.append(value)
        index += 1
    return values


def _one_option(args: list[str], name: str, short: str | None = None) -> str | None:
    """Return one unique OCR option value or reject ambiguous duplicates."""

    values = _option_values(args, name, short)
    if len(values) > 1:
        raise ReviewRunnerError(f"OCR option {name} must be provided at most once")
    return values[0] if values else None


def _without_diff_options(args: list[str]) -> list[str]:
    """Return OCR arguments without caller-supplied diff selectors."""

    remaining: list[str] = []
    index = 0
    valued = {"--from", "--to", "--commit", "-c"}
    while index < len(args):
        item = args[index]
        if item in valued:
            index += 2
            continue
        if item.startswith(("--from=", "--to=", "--commit=")):
            index += 1
            continue
        remaining.append(item)
        index += 1
    return remaining


def _review_refs(args: list[str]) -> ReviewRefs:
    """Derive immutable evidence refs from the exact OCR diff arguments."""

    base = _one_option(args, "--from")
    head = _one_option(args, "--to")
    commit = _one_option(args, "--commit", "-c")
    if commit is not None:
        if base is not None or head is not None:
            raise ReviewRunnerError("OCR --commit cannot be combined with --from or --to")
        return ReviewRefs(f"{commit}^", commit)
    if (base is None) != (head is None):
        raise ReviewRunnerError("OCR evidence review requires both --from and --to")
    if base is None or head is None:
        raise ReviewRunnerError(
            "OCR evidence review requires immutable --from/--to refs or --commit"
        )
    return ReviewRefs(base, head)


def _immutable_review_refs(refs: ReviewRefs) -> ReviewRefs:
    """Resolve both OCR and evidence collection to one immutable commit pair."""

    reader = GitRepositoryReader(Path.cwd())
    resolved = resolve_review_range(reader, refs.base, refs.head)
    return ReviewRefs(resolved.base, resolved.head)


def _reject_owned_review_options(args: list[str]) -> None:
    """Reject caller attempts to compete with toolkit-owned review artifacts."""

    background_files = _option_values(args, "--background-file")
    backgrounds = _option_values(args, "--background")
    if background_files or backgrounds:
        option = "--background-file" if background_files else "--background"
        raise ReviewRunnerError(
            f"{option} is managed by ocr-ci review; repository evidence and selected context "
            "must use toolkit-owned inputs"
        )
    if any(
        argument in {"--preview", "-p"} or argument.startswith("--preview=") for argument in args
    ):
        raise ReviewRunnerError(
            "--preview is managed by ocr-ci review as a pre-model background qualification"
        )
    if any(
        argument in {"--output", "-o"}
        or argument.startswith("--output=")
        or (argument.startswith("-o") and len(argument) > 2)
        for argument in args
    ):
        raise ReviewRunnerError(
            "--output is managed by ocr-ci review; OCR stdout must use the toolkit-owned "
            "private result artifact"
        )


def _read_bounded_artifact(path: Path, *, limit: int, label: str) -> bytes:
    """Read one process artifact through a fixed regular-file byte boundary."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > limit:
            raise ReviewRunnerError(f"OCR background preview {label} is unsafe")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > limit:
            raise ReviewRunnerError(f"OCR background preview {label} exceeds its byte limit")
        return payload
    except OSError as exc:
        raise ReviewRunnerError(f"OCR background preview {label} is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _parse_background_preview(*, returncode: int, stderr: bytes) -> BackgroundQualification:
    """Classify only exact installed-OCR preview diagnostics consumed by the toolkit."""

    try:
        text = stderr.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BackgroundPreviewUnclassified(1) from exc
    lines = [line for line in text.splitlines(keepends=True) if line.strip()]
    soft_matches = [
        match for line in lines if (match := BACKGROUND_SOFT_WARNING_RE.fullmatch(line)) is not None
    ]
    max_tools_matches = [
        match for line in lines if (match := MAX_TOOLS_NORMALIZATION_RE.fullmatch(line)) is not None
    ]
    hard_character = BACKGROUND_HARD_CHARACTER_RE.fullmatch(text)
    hard_file = BACKGROUND_HARD_FILE_RE.fullmatch(text)
    if returncode == 0:
        if (
            len(soft_matches) + len(max_tools_matches) != len(lines)
            or len(soft_matches) > 1
            or len(max_tools_matches) > 1
        ):
            raise BackgroundPreviewUnclassified(len(lines))
        advisory: OcrToolkitAdvisory | None = None
        if soft_matches:
            actual, limit = (int(value) for value in soft_matches[0].groups())
            if not 0 < limit < actual:
                raise BackgroundPreviewUnclassified(len(lines))
            advisory = background_recommended_advisory(
                actual=actual,
                recommended=limit,
            )
        operator_notices: tuple[str, ...] = ()
        if max_tools_matches:
            requested, minimum, normalized = (int(value) for value in max_tools_matches[0].groups())
            if not 0 < requested < minimum or normalized != minimum:
                raise BackgroundPreviewUnclassified(len(lines))
            operator_notices = (
                "Installed OCR reported "
                f"--max-tools {requested} below its CLI minimum and a normalization target "
                f"of {normalized}; the installed OCR template remains authoritative for the "
                "effective tool-call limit.",
            )
        return BackgroundQualification(
            advisory=advisory,
            operator_notices=operator_notices,
        )
    if hard_character is not None:
        actual, limit = (int(value) for value in hard_character.groups())
        if not 0 < limit < actual:
            raise BackgroundPreviewUnclassified(len(lines))
        raise BackgroundQualificationRejected(
            reason=BACKGROUND_CHARACTER_LIMIT_REASON,
            actual=actual,
            limit=limit,
            unit="characters",
        )
    if hard_file is not None:
        actual, limit = (int(value) for value in hard_file.groups())
        if not 0 < limit < actual:
            raise BackgroundPreviewUnclassified(len(lines))
        raise BackgroundQualificationRejected(
            reason=BACKGROUND_FILE_SIZE_LIMIT_REASON,
            actual=actual,
            limit=limit,
            unit="bytes",
        )
    raise BackgroundPreviewUnclassified(len(lines))


def _qualify_review_background(
    ocr_args: list[str],
    *,
    ocr_binary: str,
    session_home: Path,
    projection: GitlinkProjection | None = None,
) -> BackgroundQualification:
    """Ask the installed qualified OCR to classify the exact production background."""

    preview_directory = Path(tempfile.mkdtemp(prefix="background-preview-", dir=session_home))
    preview_directory.chmod(0o700)
    stdout_path = preview_directory / "stdout.json"
    stderr_path = preview_directory / "stderr.log"
    previous_umask = os.umask(0o077)
    try:
        try:
            with ExitStack() as stack:
                stdout_file = stack.enter_context(
                    _open_private_artifact(stdout_path, "background preview stdout")
                )
                stderr_file = stack.enter_context(
                    _open_private_artifact(stderr_path, "background preview stderr")
                )
                completed = subprocess.run(
                    [ocr_binary, "review", *ocr_args, "--preview"],
                    check=False,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    env=(
                        projection.child_environment()
                        if projection is not None
                        else _ocr_child_environment()
                    ),
                )
        except OSError as exc:
            raise ReviewRunnerError(f"could not execute OCR background preview: {exc}") from exc
        stdout = _read_bounded_artifact(stdout_path, limit=2_000_000, label="stdout")
        stderr = _read_bounded_artifact(
            stderr_path, limit=BACKGROUND_PREVIEW_STDERR_BYTES, label="stderr"
        )
        qualification = _parse_background_preview(returncode=completed.returncode, stderr=stderr)
        if projection is not None:
            try:
                selected = qualify_gitlink_preview(projection, stdout)
            except RepositoryEvidenceError as exc:
                raise ReviewRunnerError(
                    "OCR gitlink preview did not match the ordinary diff"
                ) from exc
            return replace(qualification, selected_diff=selected)
        return qualification
    finally:
        active_error = sys.exception()
        os.umask(previous_umask)
        try:
            shutil.rmtree(preview_directory)
        except OSError as exc:
            cleanup_error = ReviewRunnerError("OCR background preview cleanup failed")
            if active_error is not None:
                raise active_error from cleanup_error
            raise cleanup_error from exc


def _run_background_qualified_review(
    result_path: Path,
    stderr_path: Path,
    production_args: list[str],
    *,
    ocr_binary: str,
    session_home: Path,
    artifacts: EvidenceArtifacts,
    refs: ReviewRefs,
    identity: ReviewIdentity,
    gitlink_detected: bool = False,
    projection: GitlinkProjection | None = None,
    state: ReviewRunState | None = None,
) -> tuple[int, BackgroundQualification]:
    """Run the model review only after installed OCR accepts its background."""

    status_review = _status_review(identity)
    if gitlink_detected:
        if state is not None:
            state.gitlink_unqualified = True
        if status_review is not None:
            write_pre_execution_status(
                artifacts.pre_execution_status,
                PreExecutionStatus(
                    schema_version=GITLINK_STATUS_SCHEMA,
                    reason=GITLINK_PROJECTION_UNQUALIFIED,
                    diff_base_sha=refs.base,
                    source_sha=refs.head,
                    policy_sha=identity.policy_sha,
                    review=status_review,
                    stage=OCR_PREVIEW_STAGE,
                ),
            )
        if state is not None:
            state.observe("preview", "failed")
        print(
            "OCR preview qualification: changed gitlink is unsupported; model review did not run",
            file=sys.stderr,
        )
        return 2, BackgroundQualification()
    try:
        qualification = _qualify_review_background(
            production_args,
            ocr_binary=ocr_binary,
            session_home=session_home,
            **({"projection": projection} if projection is not None else {}),
        )
    except BackgroundQualificationRejected as exc:
        if state is not None:
            state.observe("preview", "failed")
        try:
            if status_review is not None:
                write_pre_execution_status(
                    artifacts.pre_execution_status,
                    PreExecutionStatus(
                        schema_version=STATUS_SCHEMA,
                        reason=exc.reason,
                        diff_base_sha=refs.base,
                        source_sha=refs.head,
                        policy_sha=identity.policy_sha,
                        review=status_review,
                        stage=OCR_PREVIEW_STAGE,
                        actual=exc.actual,
                        limit=exc.limit,
                        unit=exc.unit,
                    ),
                )
        except PreExecutionStatusError as status_exc:
            raise ReviewRunnerError(
                "OCR background rejection status could not be persisted safely"
            ) from status_exc
        print(
            "OCR background qualification: rejected by installed OCR "
            f"actual={exc.actual} limit={exc.limit} unit={exc.unit}; "
            "model review did not run",
            file=sys.stderr,
        )
        return 2, BackgroundQualification()
    except BackgroundPreviewUnclassified as exc:
        if state is not None:
            state.observe("preview", "failed")
        if status_review is not None:
            write_pre_execution_status(
                artifacts.pre_execution_status,
                PreExecutionStatus(
                    schema_version=STATUS_SCHEMA,
                    reason=UNCLASSIFIED_PREVIEW_DIAGNOSTICS,
                    diff_base_sha=refs.base,
                    source_sha=refs.head,
                    policy_sha=identity.policy_sha,
                    review=status_review,
                    stage=OCR_PREVIEW_STAGE,
                    diagnostic_count=exc.diagnostic_count,
                ),
            )
        print(
            "OCR preview qualification: diagnostics unclassified; model review did not run",
            file=sys.stderr,
        )
        return 2, BackgroundQualification()
    if qualification.advisory is not None:
        print(
            "OCR core advisory: "
            f"background {qualification.advisory.actual} characters; recommended "
            f"{qualification.advisory.recommended} characters; accepted by OCR core",
            file=sys.stderr,
        )
    for notice in qualification.operator_notices:
        print(f"OCR argument qualification notice: {notice}", file=sys.stderr)
    if state is not None:
        state.observe("preview", "degraded" if qualification.advisory is not None else "passed")
    if projection is not None:
        if not qualification.selected_diff:
            coverage = coverage_from_projection(projection, (), state="not_started")
            if state is not None:
                state.repository_coverage = coverage
            if status_review is not None:
                try:
                    write_pre_execution_status(
                        artifacts.pre_execution_status,
                        PreExecutionStatus(
                            schema_version=GITLINK_STATUS_SCHEMA,
                            reason=GITLINK_NO_REVIEWABLE_FILES,
                            diff_base_sha=refs.base,
                            source_sha=refs.head,
                            policy_sha=identity.policy_sha,
                            review=status_review,
                            stage=OCR_PREVIEW_STAGE,
                            repository_coverage=coverage.payload(),
                        ),
                    )
                except PreExecutionStatusError as exc:
                    raise ReviewRunnerError(
                        "OCR gitlink no-model status could not be persisted safely"
                    ) from exc
            print(
                "OCR gitlink qualification: no ordinary files selected; model review did not run",
                file=sys.stderr,
            )
            return 2, qualification
        try:
            verify_gitlink_projection(GitRepositoryReader(Path.cwd()), projection)
        except (RepositoryEvidenceError, OSError, subprocess.TimeoutExpired) as exc:
            raise ReviewRunnerError("OCR gitlink inputs drifted before model execution") from exc
    if state is not None:
        state.enter("subprocess")
    try:
        code = run_review(
            result_path,
            stderr_path,
            production_args,
            ocr_binary=ocr_binary,
            **(
                {"child_environment": projection.child_environment()}
                if projection is not None
                else {}
            ),
        )
    finally:
        if state is not None and state.debug is not None:
            state.debug.capture("raw-result.json", result_path)
            state.debug.capture("raw-stderr.log", stderr_path)
    if state is not None:
        state.observe("subprocess", "passed" if code == 0 else "failed", facts={"exit_code": code})
    return code, qualification


def _prepare_review_output_artifacts(result_path: Path, stderr_path: Path) -> None:
    """Validate and empty public handoff artifacts before the preview gate."""

    if result_path.absolute() == stderr_path.absolute():
        raise ReviewRunnerError("result and stderr paths must be different")
    for path, label in ((result_path, "result"), (stderr_path, "stderr")):
        if path.is_symlink():
            raise ReviewRunnerError(f"{label} path must not be a symlink: {path}")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    previous_umask = os.umask(0o077)
    try:
        with ExitStack() as stack:
            result_file = stack.enter_context(_open_private_artifact(result_path, "result"))
            stderr_file = stack.enter_context(_open_private_artifact(stderr_path, "stderr"))
            if os.path.samestat(os.fstat(result_file.fileno()), os.fstat(stderr_file.fileno())):
                raise ReviewRunnerError("result and stderr paths must be different")
    finally:
        os.umask(previous_umask)


def _replace_rule_argument(args: list[str], old_value: str, new_value: str) -> list[str]:
    """Replace only the one parsed repository-owned OCR rule argument."""

    replaced: list[str] = []
    index = 0
    matches = 0
    while index < len(args):
        item = args[index]
        if item == "--rule":
            if index + 1 >= len(args):
                raise ReviewRunnerError("OCR option --rule requires a value")
            value = args[index + 1]
            replaced.extend((item, new_value if value == old_value else value))
            matches += value == old_value
            index += 2
            continue
        if item.startswith("--rule="):
            value = item.removeprefix("--rule=")
            replaced.append(f"--rule={new_value}" if value == old_value else item)
            matches += value == old_value
            index += 1
            continue
        replaced.append(item)
        index += 1
    if matches != 1:
        raise ReviewRunnerError("repository-owned OCR rule input is ambiguous")
    return replaced


def _repository_rule_path(value: str, root: Path) -> str | None:
    """Return a normalized in-repository rule path or None for explicit external input."""

    candidate = Path(value)
    if candidate.is_absolute():
        try:
            value = candidate.relative_to(root).as_posix()
        except ValueError:
            return None
    try:
        return normalize_repo_path(value)
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError("OCR --rule repository path is unsafe") from exc


def _record_rules_path_setup(
    reader: GitRepositoryReader,
    artifacts: EvidenceArtifacts,
    *,
    refs: ReviewRefs,
    policy_sha: str,
    repository_path: str,
    identity: ReviewIdentity,
    setup_reason: str = PROTECTED_TARGET_RULE_PATH_PENDING,
) -> bool:
    """Record only a bounded regular-blob introduction without reading source content."""

    if reader.object_at(refs.base, repository_path) is not None:
        return False
    source = reader.object_at(refs.head, repository_path)
    if source is None:
        return False
    reader.bounded_regular_blob_size(source)
    write_pre_execution_status(
        artifacts.pre_execution_status,
        PreExecutionStatus(
            schema_version=STATUS_SCHEMA,
            reason=setup_reason,
            diff_base_sha=refs.base,
            source_sha=refs.head,
            policy_sha=policy_sha,
            review=_status_review(identity),
        ),
    )
    return True


def _record_unavailable_review_identity(artifacts: EvidenceArtifacts, refs: ReviewRefs) -> None:
    """Keep an unproven provider boundary as a private, job-only outcome."""

    write_pre_execution_status(
        artifacts.pre_execution_status,
        PreExecutionStatus(
            schema_version=STATUS_SCHEMA,
            reason=REVIEW_IDENTITY_UNAVAILABLE,
            diff_base_sha=refs.base,
            source_sha=refs.head,
            policy_sha=None,
        ),
    )


def _prepare_policy_context(
    refs: ReviewRefs, ocr_args: list[str], artifacts: EvidenceArtifacts, *, local: bool = False
) -> tuple[ReviewIdentity, list[str]]:
    """Capture policy identity and selected context, then materialize rules."""

    try:
        context_mode = parse_review_context_mode(os.environ.get("OCR_REVIEW_CONTEXT_MODE"))
    except ReviewContextModeError as exc:
        raise ReviewRunnerError(str(exc)) from exc
    if local:
        try:
            validate_local_context(os.environ)
        except ValueError as exc:
            raise ReviewRunnerError(str(exc)) from exc
    reader = GitRepositoryReader(Path.cwd())
    context = None
    author_id = None
    target_protection = "local"
    snapshot = None
    if not local and not is_merge_request_environment(os.environ):
        _record_unavailable_review_identity(artifacts, refs)
        raise ReviewRunnerError(
            "GitLab merge-request identity is required; use --local for a standalone review"
        )
    if not local:
        try:
            snapshot = acquire_review_snapshot(
                os.environ,
                expected_head=refs.head,
                include_metadata=context_mode in {"metadata", "enriched"},
            )
        except GitLabMergeRequestStale as exc:
            write_pre_execution_status(
                artifacts.pre_execution_status,
                PreExecutionStatus(
                    schema_version=STATUS_SCHEMA,
                    reason=REVIEWED_REVISION_NO_LONGER_CURRENT,
                    diff_base_sha=refs.base,
                    source_sha=refs.head,
                    policy_sha=None,
                    provider="gitlab",
                    project_id=exc.project_id,
                    change_id=exc.merge_request_iid,
                ),
            )
            raise ReviewRunnerError("reviewed merge request revision is no longer current") from exc
        except GitLabMergeRequestTerminal as exc:
            lifecycle = exc.lifecycle
            write_pre_execution_status(
                artifacts.pre_execution_status,
                PreExecutionStatus(
                    schema_version=STATUS_SCHEMA,
                    reason=GITLAB_MERGE_REQUEST_TERMINAL,
                    diff_base_sha=refs.base,
                    source_sha=refs.head,
                    policy_sha=None,
                    provider="gitlab",
                    project_id=lifecycle.project_id,
                    change_id=lifecycle.merge_request_iid,
                    terminal_state=lifecycle.state,
                ),
            )
            raise ReviewRunnerError(str(exc)) from exc
        except GitLabProviderError as exc:
            _record_unavailable_review_identity(artifacts, refs)
            raise ReviewRunnerError(
                "GitLab review identity or policy authority is unavailable"
            ) from exc
        if snapshot.diff_base_sha != refs.base or snapshot.diff_head_sha != refs.head:
            write_pre_execution_status(
                artifacts.pre_execution_status,
                PreExecutionStatus(
                    schema_version=STATUS_SCHEMA,
                    reason=REVIEWED_REVISION_NO_LONGER_CURRENT,
                    diff_base_sha=refs.base,
                    source_sha=refs.head,
                    policy_sha=None,
                    provider="gitlab",
                    project_id=snapshot.project_id,
                    change_id=snapshot.merge_request_iid,
                ),
            )
            raise ReviewRunnerError(
                "reviewed refs do not match the authenticated current GitLab MR diff"
            )
        try:
            reader.fetch_commit(snapshot.target_sha)
            target_sha = reader.resolve_commit(snapshot.target_sha)
            if snapshot.policy_sha != snapshot.target_sha:
                reader.fetch_commit(snapshot.policy_sha)
            policy_sha = reader.resolve_commit(snapshot.policy_sha)
        except RepositoryEvidenceError as exc:
            _record_unavailable_review_identity(artifacts, refs)
            raise ReviewRunnerError(
                "captured GitLab target or policy object is unavailable"
            ) from exc
        context = snapshot.context
        author_id = snapshot.author_id
        target_protection = snapshot.target_protection
        if snapshot.policy_protection == "unprotected":
            if context_mode == "enriched":
                raise ReviewRunnerError(
                    "enriched review context requires a protected GitLab target branch"
                )
            if os.environ.get("OCR_REVIEW_CONTEXT_ADAPTERS_JSON") is not None:
                raise ReviewRunnerError("unprotected-target reviews do not allow context adapters")
    else:
        if context_mode in {"metadata", "enriched"}:
            raise ReviewRunnerError(
                f"{context_mode} review context requires a GitLab merge request"
            )
        policy_sha = refs.base
        target_sha = policy_sha
    identity = ReviewIdentity(
        source_sha=refs.head,
        policy_sha=policy_sha,
        mr_author_id=author_id,
        context_mode=context_mode,
        context=context,
        target_sha=target_sha,
        target_protection=target_protection,
        project_id=snapshot.project_id if snapshot is not None else None,
        merge_request_iid=snapshot.merge_request_iid if snapshot is not None else None,
        diff_base_sha=snapshot.diff_base_sha if snapshot is not None else None,
        diff_start_sha=snapshot.diff_start_sha if snapshot is not None else None,
        diff_head_sha=snapshot.diff_head_sha if snapshot is not None else None,
        diff_version_id=snapshot.diff_version_id if snapshot is not None else None,
        target_branch=snapshot.target_branch if snapshot is not None else None,
        policy_project_id=snapshot.project_id if snapshot is not None else None,
        policy_branch=snapshot.policy_branch if snapshot is not None else None,
        policy_protection=snapshot.policy_protection if snapshot is not None else None,
        protection_mode=snapshot.protection_mode if snapshot is not None else None,
        ci_job_id=os.environ.get("CI_JOB_ID") if snapshot is not None else None,
    )
    rule = _one_option(ocr_args, "--rule")
    if rule is None:
        if target_protection == "unprotected":
            raise ReviewRunnerError(
                "unprotected-target reviews require repository rules from the captured policy commit"
            )
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    repository_path = _repository_rule_path(rule, reader.root)
    if repository_path is None:
        if target_protection == "unprotected":
            raise ReviewRunnerError(
                "unprotected-target reviews require repository rules from the captured policy commit"
            )
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    try:
        content = reader.read_blob(policy_sha, repository_path)
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError("target OCR rule is unavailable or unsafe") from exc
    if content is None:
        if author_id is not None and identity.has_protected_policy:
            protected_branch_label = (
                "protected policy"
                if identity.target_protection == "unprotected"
                else "protected target"
            )
            try:
                setup_pending = _record_rules_path_setup(
                    reader,
                    artifacts,
                    refs=refs,
                    policy_sha=policy_sha,
                    repository_path=repository_path,
                    identity=identity,
                    setup_reason=(
                        PROTECTED_POLICY_RULE_PATH_PENDING
                        if identity.protection_mode == "auto"
                        and identity.target_protection == "unprotected"
                        and identity.policy_protection == "protected"
                        else PROTECTED_TARGET_RULE_PATH_PENDING
                    ),
                )
            except (PreExecutionStatusError, RepositoryEvidenceError) as exc:
                raise ReviewRunnerError(
                    f"{protected_branch_label} OCR rule does not exist and the source candidate is unsafe"
                ) from exc
            if setup_pending:
                raise ReviewRunnerError(f"{protected_branch_label} OCR rule path setup is pending")
        authority_kind = "protected policy" if identity.has_protected_policy else "target"
        raise ReviewRunnerError(f"{authority_kind} OCR rule does not exist")
    policy_rules = artifacts.policy_rules
    write_private_bytes(policy_rules, content)
    return identity, _replace_rule_argument(ocr_args, rule, str(policy_rules))


def _context_texts(context: MergeRequestContext) -> tuple[str, ...]:
    """Return only already-admitted MR metadata text for fixed recognizers."""

    values: list[str] = []
    for name in ("title", "description", "source_branch"):
        field = context.fields.get(name)
        value = field.get("value") if isinstance(field, dict) else None
        if isinstance(value, str):
            values.append(value)
    labels = context.fields.get("labels")
    label_values = labels.get("values") if isinstance(labels, dict) else None
    if isinstance(label_values, list):
        values.extend(value for value in label_values if isinstance(value, str))
    return tuple(values)


def _bounded_combined_records(
    records: list[PendingContextRecord], policy: ContextPolicy
) -> tuple[list[PendingContextRecord], set[str]]:
    """Apply aggregate units across forge and adapter records together."""

    admitted: list[PendingContextRecord] = []
    chars = bytes_count = lines = 0
    limited_sources: set[str] = set()
    for record in records:
        model = record.projections.get("model", {})
        texts: list[str] = []
        text = model.get("text")
        if isinstance(text, str):
            texts.append(text)
        remediation = model.get("remediation_thread")
        if isinstance(remediation, dict):
            root = remediation.get("root")
            root_text = root.get("text") if isinstance(root, dict) else None
            if isinstance(root_text, str):
                texts.append(root_text)
            replies = remediation.get("replies")
            if isinstance(replies, list):
                for reply in replies:
                    reply_text = reply.get("text") if isinstance(reply, dict) else None
                    if isinstance(reply_text, str):
                        texts.append(reply_text)
        ci_outcome = model.get(CI_OUTCOME_MODEL_FIELD)
        if isinstance(ci_outcome, dict):
            stack: list[object] = [ci_outcome]
            while stack:
                nested = stack.pop()
                if isinstance(nested, dict):
                    stack.extend(nested.values())
                elif isinstance(nested, list):
                    stack.extend(nested)
                elif isinstance(nested, str):
                    texts.append(nested)
        record_chars = sum(len(value) for value in texts)
        record_bytes = sum(len(value.encode()) for value in texts)
        record_lines = sum(value.count("\n") + 1 for value in texts)
        next_chars = chars + record_chars
        next_bytes = bytes_count + record_bytes
        next_lines = lines + record_lines
        if (
            len(admitted) >= policy.budgets.max_records
            or next_chars > policy.budgets.max_chars
            or next_bytes > policy.budgets.max_bytes
            or next_lines > policy.budgets.max_lines
        ):
            limited_sources.add(record.source)
            continue
        admitted.append(record)
        chars, bytes_count, lines = next_chars, next_bytes, next_lines
    return admitted, limited_sources


def _remediation_mutable_admitted(records: Sequence[ContextRecord]) -> bool:
    """Report only admitted remediation as the receipt-v8 comment-only condition."""

    return any(
        record.mutable and record.resource_class == "remediation_thread" for record in records
    )


def _prepare_enrichment(
    identity: ReviewIdentity,
    artifacts: EvidenceArtifacts,
    reader: GitRepositoryReader,
    *,
    dlp_enabled: bool = True,
) -> tuple[mcp_config.MCPContextConfig | None, EnrichmentReceipt | None]:
    """Acquire forge context; legacy references are parsed but never executed."""

    if os.environ.get("OCR_REVIEW_CONTEXT_ADAPTERS_JSON") is not None:
        raise ReviewRunnerError(
            "OCR_REVIEW_CONTEXT_ADAPTERS_JSON was removed; configure governed MCP"
        )

    if identity.limited_unprotected:
        if identity.context_mode == "enriched":
            raise ReviewRunnerError(
                "enriched review context requires a protected GitLab target branch"
            )
        if os.environ.get("OCR_REVIEW_CONTEXT_ADAPTERS_JSON") is not None:
            raise ReviewRunnerError("unprotected-target reviews do not allow context adapters")
        remove_private_artifact(artifacts.context_store)
        return None, None
    if identity.context_mode != "enriched":
        remove_private_artifact(artifacts.context_store)
        return None, None
    if identity.context is None:
        raise ReviewRunnerError("enriched review context requires validated MR metadata")
    policy = load_protected_policy(reader.read_blob, policy_sha=identity.policy_sha)
    legacy_policy = policy.schema_version != "ocr.review-context-policy/v4"
    if legacy_policy:
        print(
            "OCR context policy migration v1: legacy policy consumed; references not executed",
            file=sys.stderr,
        )
    now = int(time.time())
    acquisition_deadline = time.monotonic() + policy.budgets.timeout_ms / 1000
    run_id = secrets.token_urlsafe(24)
    completeness: dict[str, str] = {}
    degradation = {"invalid": 0, "limit": 0, "unavailable": 0}
    required_degraded = False
    pending: list[PendingContextRecord] = []
    adapter_secrets: tuple[str, ...] = ()
    discussion_policy = policy.forge_discussions
    remediation_policy = policy.remediation_threads
    ci_policy = policy.ci_outcomes
    discussion_origin = ContextOrigin(
        source="forge:gitlab_discussions", adapter="gitlab", tenant="project"
    )
    remediation_origin = ContextOrigin(
        source="forge:gitlab_remediation_threads", adapter="gitlab", tenant="project"
    )
    if discussion_policy is not None or remediation_policy is not None:
        try:
            snapshot = acquire_gitlab_context(
                os.environ,
                project_id=identity.context.project_id,
                merge_request_iid=identity.context.merge_request_iid,
                source_sha=identity.source_sha,
                run_id=run_id,
                discussion_policy=discussion_policy,
                remediation_policy=remediation_policy,
                now=now,
                deadline=acquisition_deadline,
                forbidden=adapter_secrets,
            )
        except GitLabProviderError:
            for origin, source_policy in (
                (discussion_origin, discussion_policy),
                (remediation_origin, remediation_policy),
            ):
                if source_policy is None:
                    continue
                completeness[origin.source] = "unavailable"
                degradation["unavailable"] += 1
                required_degraded = required_degraded or source_policy.required
        else:
            if discussion_policy is not None and snapshot.discussions is not None:
                discussion_snapshot = snapshot.discussions
                completeness[discussion_origin.source] = discussion_snapshot.state
                if discussion_snapshot.state != "complete":
                    if discussion_snapshot.state == "mutated":
                        degradation["invalid"] += 1
                    else:
                        if discussion_snapshot.omitted > discussion_snapshot.dlp_rejected:
                            degradation["limit"] += 1
                        degradation["invalid"] += discussion_snapshot.dlp_rejected
                    required_degraded = required_degraded or discussion_policy.required
                    required_degraded = required_degraded or discussion_snapshot.dlp_rejected > 0
                discussion_records = prepare_discussion_records(
                    discussion_snapshot.records,
                    policy=discussion_policy,
                    origin=discussion_origin,
                    expiry=now + 3_600,
                    forbidden=adapter_secrets,
                )
                if len(discussion_records) != len(discussion_snapshot.records):
                    completeness[discussion_origin.source] = "partial"
                    degradation["invalid"] += len(discussion_snapshot.records) - len(
                        discussion_records
                    )
                    # A DLP/shape rejection cannot silently make automatic approval eligible.
                    required_degraded = True
                pending.extend(discussion_records)
            if remediation_policy is not None and snapshot.remediation_threads is not None:
                remediation_snapshot = snapshot.remediation_threads
                completeness[remediation_origin.source] = remediation_snapshot.state
                if remediation_snapshot.state != "complete":
                    if remediation_snapshot.state == "mutated":
                        degradation["invalid"] += 1
                    else:
                        if remediation_snapshot.omitted > remediation_snapshot.dlp_rejected:
                            degradation["limit"] += 1
                        degradation["invalid"] += remediation_snapshot.dlp_rejected
                    required_degraded = required_degraded or remediation_policy.required
                    required_degraded = required_degraded or remediation_snapshot.dlp_rejected > 0
                remediation_records = prepare_remediation_records(
                    remediation_snapshot.records,
                    policy=remediation_policy,
                    origin=remediation_origin,
                    expiry=now + 3_600,
                    forbidden=adapter_secrets,
                )
                if len(remediation_records) != len(remediation_snapshot.records):
                    completeness[remediation_origin.source] = "partial"
                    degradation["invalid"] += len(remediation_snapshot.records) - len(
                        remediation_records
                    )
                    required_degraded = True
                pending.extend(remediation_records)
    ci_origin = "forge:ci_outcomes"
    if ci_policy is not None:
        try:
            ci_snapshot = acquire_gitlab_ci_outcomes(
                os.environ,
                project_id=identity.context.project_id,
                source_sha=identity.source_sha,
                policy=ci_policy,
                now=now,
                deadline=acquisition_deadline,
            )
        except GitLabProviderError:
            completeness[ci_origin] = "unavailable"
            degradation["unavailable"] += 1
            required_degraded = required_degraded or ci_policy.required
        else:
            completeness[ci_origin] = ci_snapshot.state
            if ci_snapshot.state != "complete":
                degradation["invalid"] += max(1, ci_snapshot.invalid)
                degradation["limit"] += int(ci_snapshot.omitted > 0)
                required_degraded = required_degraded or ci_policy.required
            ci_records = prepare_ci_outcome_records(
                ci_snapshot,
                policy=ci_policy,
                now=now,
                forbidden=adapter_secrets,
            )
            if len(ci_records) != len(ci_snapshot.records):
                completeness[ci_origin] = "partial"
                degradation["invalid"] += len(ci_snapshot.records) - len(ci_records)
                required_degraded = required_degraded or ci_policy.required
            pending.extend(ci_records)
    if policy.references:
        completeness["legacy:references"] = "unavailable"
        required_degraded = (
            any(reference.required for reference in policy.references) or required_degraded
        )
        if required_degraded:
            degradation["unavailable"] += 1
    admitted, limited_sources = _bounded_combined_records(pending, policy)
    if limited_sources:
        degradation["limit"] += 1
        required_sources = {
            f"reference:{reference.adapter}:{reference.tenant}:{reference.resource_class}"
            for reference in policy.references
            if reference.required
        }
        if policy.forge_discussions is not None and policy.forge_discussions.required:
            required_sources.add("forge:gitlab_discussions")
        if policy.remediation_threads is not None and policy.remediation_threads.required:
            required_sources.add("forge:gitlab_remediation_threads")
        if policy.ci_outcomes is not None and policy.ci_outcomes.required:
            required_sources.add("forge:ci_outcomes")
        required_degraded = required_degraded or bool(limited_sources & required_sources)
        for source in limited_sources:
            completeness[source] = "partial"
    store_expiry = max((record.expiry for record in admitted), default=now + 3_600)
    context_store = ContextStore.commit(
        artifacts.context_store,
        run_id=run_id,
        policy_digest=policy.digest,
        completeness=completeness,
        records=admitted,
        created_at=now,
        expiry=store_expiry,
    )
    forbidden_values: list[str] = []
    forbidden_sources = [ForbiddenValue(v, "operator_secret") for v in adapter_secrets]
    for record in context_store.records:
        source_class = (
            "remediation_threads"
            if record.resource_class == "remediation_thread"
            else "ci_outcomes"
            if record.resource_class == "ci_outcome"
            else "forge_discussions"
            if record.source.startswith("forge:")
            else "external_context"
        )
        published = record.projections["publish"]
        for field, value in record.projections["model"].items():
            if field in published:
                continue
            if field == CI_OUTCOME_MODEL_FIELD and isinstance(value, dict):
                scope = value.get("scope")
                value = {
                    "check": value.get("check"),
                    "path_prefixes": (
                        scope.get("path_prefixes") if isinstance(scope, dict) else None
                    ),
                }
            stack: list[tuple[object, tuple[str, ...]]] = [(value, ())]
            while stack:
                nested, path = stack.pop()
                if isinstance(nested, dict):
                    stack.extend(
                        (item, (*path, key if isinstance(key, str) else "<non-string>"))
                        for key, item in nested.items()
                    )
                elif isinstance(nested, list):
                    stack.extend((item, path) for item in nested)
                elif isinstance(nested, str) and nested:
                    if (
                        source_class == "remediation_threads"
                        and field == "remediation_thread"
                        and (
                            (
                                path == ("anchor_state",)
                                and nested in {"current", "outdated", "unpositioned"}
                            )
                            or (path == ("completeness",) and nested in {"complete", "partial"})
                            or (
                                path == ("replies", "author_class")
                                and nested in {"user", "automation"}
                            )
                        )
                    ):
                        # These fixed broker labels describe structure, not protected source text.
                        continue
                    forbidden_values.append(nested)
                    forbidden_sources.append(ForbiddenValue(nested, source_class))
    forbidden = (*adapter_secrets, *forbidden_values)
    ci_hints: dict[str, int] = {}
    for record in context_store.records:
        model = record.projections["model"].get(CI_OUTCOME_MODEL_FIELD)
        if not isinstance(model, dict):
            continue
        status = model.get("status")
        requirement = model.get("requirement")
        if isinstance(status, str) and isinstance(requirement, str):
            key = f"{requirement}_{status}"
            ci_hints[key] = ci_hints.get(key, 0) + 1
    receipt = EnrichmentReceipt(
        policy_digest=policy.digest,
        completeness=dict(sorted(completeness.items())),
        degradation_counts=dict(sorted(degradation.items())),
        required_degraded=required_degraded,
        mutable_admitted=_remediation_mutable_admitted(context_store.records),
        forbidden_publication=forbidden,
        forbidden_sources=tuple(forbidden_sources),
        legacy_policy=legacy_policy,
        bootstrap_hints=dict(sorted(ci_hints.items())),
    )
    return (
        mcp_config.MCPContextConfig(
            store_path=str(artifacts.context_store.resolve()),
            run_id=run_id,
            policy_digest=policy.digest,
            dlp_enabled=dlp_enabled,
        ),
        receipt,
    )


def _authorize_private_artifact_preservation(identity: ReviewIdentity, *, requested: bool) -> bool:
    """Allow sensitive diagnostic retention only outside GitLab MR execution."""

    if requested and identity.mr_author_id is not None:
        raise ReviewRunnerError("private artifact preservation is available for local reviews only")
    return requested


def _remove_ephemeral_review_artifacts(artifacts: EvidenceArtifacts) -> None:
    """Remove every ordinary-run private input while preserving static handoff state."""

    cleanup_error: OSError | None = None
    for path in (
        artifacts.store,
        artifacts.bootstrap,
        artifacts.policy_rules,
        artifacts.context_store,
        artifacts.action_receipt,
        artifacts.action_receipt_lock,
        artifacts.dlp_decisions,
    ):
        try:
            remove_private_artifact(path)
        except OSError as exc:
            cleanup_error = cleanup_error or exc
    _remove_optional_diagram_artifacts(artifacts)
    if cleanup_error is not None:
        raise cleanup_error


def _remove_optional_diagram_artifacts(artifacts: EvidenceArtifacts) -> None:
    """Optional output cleanup must not change mandatory review delivery."""

    for path in (artifacts.diagram, artifacts.diagram_lock):
        try:
            remove_private_artifact(path)
        except Exception:
            diagram_warning()


def run_evidence_review(
    result_path: Path,
    stderr_path: Path,
    ocr_args: list[str],
    *,
    preserve_private_artifacts: bool = False,
    local: bool = False,
    report_path: Path | None = None,
    debug_dir: Path | None = None,
) -> int:
    """Run the review and deliver an admitted local report or a closed failure summary."""

    state = ReviewRunState(local=local)
    report_destination: Path | None = None
    local_input_error: ReviewRunnerError | None = None
    review_lock = ExitStack()
    try:
        try:
            state.diagram_mode = parse_diagram_mode(
                os.environ.get("OCR_REVIEW_DIAGRAM_MODE"), local=local
            )
        except DiagramError as exc:
            raise ReviewRunnerError(str(exc)) from exc
        if local:
            # Local-only context refusal precedes even private artifact I/O.
            try:
                validate_local_context(os.environ)
            except ValueError as exc:
                raise ReviewRunnerError(str(exc)) from exc
        try:
            artifacts = repository_artifacts()
            review_lock.enter_context(locked_review_run(artifacts))
            remove_private_artifact(artifacts.pre_execution_status)
        except ReviewRunBusy as exc:
            # This process owns no review artifacts. A failure report at the
            # caller's shared destination could preempt the active review.
            report_destination = None
            raise ReviewRunnerBusy("another review is already running in this repository") from exc
        except (OSError, RuntimeError) as exc:
            report_destination = None
            raise ReviewRunnerNoHandoff("OCR private pre-execution state is unsafe") from exc
        if local:
            if debug_dir is not None and preserve_private_artifacts:
                raise ReviewRunnerError("--debug-dir requires --local without legacy retention")
            try:
                ocr_args = _local_review_options(ocr_args)
                destination = report_path or Path(str(result_path) + ".md")
                try:
                    prepare_local_report_path(destination, other_outputs=(result_path, stderr_path))
                except (OSError, ValueError, RuntimeError) as exc:
                    raise ReviewRunnerError(
                        "local report destination is unavailable or unsafe"
                    ) from exc
                report_destination = destination
            except ReviewRunnerError as exc:
                if debug_dir is None:
                    raise
                # A requested debug journal records early local refusal only
                # after this run has safely claimed the private handoff.
                local_input_error = exc
        if debug_dir is not None:
            if not local:
                raise ReviewRunnerError("--debug-dir requires --local without legacy retention")
            try:
                state.debug = DebugBundle(
                    debug_dir,
                    other_outputs=(
                        result_path,
                        stderr_path,
                        report_path or Path(str(result_path) + ".md"),
                    ),
                )
                state.debug.flush()
            except (OSError, ValueError, RuntimeError) as exc:
                raise ReviewRunnerError("debug directory could not be prepared safely") from exc
        if local_input_error is not None:
            raise local_input_error
        try:
            mode = local_chatgpt.auth_mode(os.environ, local=local)
            if mode == "chatgpt":
                local_chatgpt.provider_entry(os.environ)
                if any(
                    argument == "--provider" or argument.startswith("--provider=")
                    for argument in ocr_args
                ):
                    raise local_chatgpt.LocalChatGPTError(
                        "--provider cannot override explicit ChatGPT authentication"
                    )
        except local_chatgpt.LocalChatGPTError as exc:
            raise ReviewRunnerError(str(exc)) from exc
        try:
            dlp_enabled = resolve_dlp_enabled(os.environ)
        except ValueError as exc:
            raise ReviewRunnerError(str(exc)) from exc
        if not dlp_enabled:
            print(
                "WARNING: OCR DLP IS DISABLED by OCR_DLP_ENABLED. Sensitive context or "
                "model output may be sent to configured services and written to local or "
                "GitLab output; automatic approval is blocked for this run.",
                file=sys.stderr,
            )
        try:
            enabled = progress_enabled(os.environ.get("OCR_REVIEW_PROGRESS", ""))
        except ValueError as exc:
            raise ReviewRunnerError(str(exc)) from exc
        if enabled:
            state.progress = ReviewProgress(sys.stderr)
            state.progress.start()
        if report_path is not None and not local:
            raise ReviewRunnerError("--report requires --local")
        with dlp_mode(dlp_enabled):
            code = _run_evidence_review(
                result_path,
                stderr_path,
                ocr_args,
                preserve_private_artifacts=preserve_private_artifacts,
                state=state,
                dlp_enabled=dlp_enabled,
            )
        if local:
            if code == 0 and state.report is None:
                raise ReviewRunnerError("local review did not produce an admitted report")
            report = (
                state.report
                if code == 0
                else failed_report(
                    state.stage,
                    reviewed_sha=state.reviewed_sha,
                    repository_coverage=state.repository_coverage,
                    gitlink_unqualified=state.gitlink_unqualified,
                )
            )
            assert report is not None
            state.enter("reporting")
            try:
                assert report_destination is not None
                publish_local_report(report, report_destination)
                if state.debug is not None:
                    state.debug.capture("summary.md", report_destination)
            except (OSError, ValueError) as exc:
                failure = failed_report("reporting")
                if state.debug is not None:
                    state.debug.capture_parts("summary.md", local_report_parts(failure))
                try:
                    write_local_report(failure, sys.stdout)
                except (OSError, ValueError):
                    pass
                raise ReviewRunnerError("local report artifact output failed") from exc
            try:
                write_local_report(report, sys.stdout)
            except (OSError, ValueError) as exc:
                raise ReviewRunnerError("local report output failed") from exc
            state.observe("reporting", "passed", facts={"report_artifact": True, "console": True})
        return code
    except Exception:
        state.observe(state.stage, "failed")
        if local and state.stage != "reporting":
            failure = failed_report(state.stage, reviewed_sha=state.reviewed_sha)
            artifact_delivered = False
            console_delivered = False
            if state.debug is not None:
                state.debug.capture_parts("summary.md", local_report_parts(failure))
            if report_destination is not None:
                try:
                    publish_local_report(failure, report_destination)
                    artifact_delivered = True
                    if state.debug is not None:
                        state.debug.capture("summary.md", report_destination)
                except (OSError, ValueError):
                    try:
                        print("Local failure report artifact output failed.", file=sys.stderr)
                    except (OSError, ValueError):
                        pass
            try:
                write_local_report(failure, sys.stdout)
                console_delivered = True
            except (OSError, ValueError):
                try:
                    print("Local failure summary output failed.", file=sys.stderr)
                except (OSError, ValueError):
                    pass
            state.observe(
                "reporting",
                "passed"
                if console_delivered and (report_destination is None or artifact_delivered)
                else "failed",
                facts={"report_artifact": artifact_delivered, "console": console_delivered},
            )
        raise
    finally:
        try:
            if state.progress is not None:
                state.progress.close()
            if state.debug is not None:
                try:
                    if state.report is not None:
                        state.debug.capture("safe-result.json", result_path)
                    state.debug.flush(complete=True)
                except (OSError, ValueError):
                    try:
                        print("Local debug journal output failed.", file=sys.stderr)
                    except (OSError, ValueError):
                        pass
                finally:
                    state.debug.close()
        finally:
            review_lock.close()


def _local_review_options(args: list[str]) -> list[str]:
    """Require JSON/agent output and refuse competing local execution inputs."""

    for option in ("--repo", "--resume", "--background", "--background-file"):
        if _option_values(args, option):
            raise ReviewRunnerError(f"{option} is not supported by standalone local review")
    if any(arg.startswith(("-b", "-B")) and not arg.startswith("--") for arg in args):
        raise ReviewRunnerError("local review background is managed by the toolkit")
    formats = _option_values(args, "--format", "-f")
    formats.extend(
        arg[2:].removeprefix("=") for arg in args if arg.startswith("-f") and len(arg) > 2
    )
    if any(value != "json" for value in formats):
        raise ReviewRunnerError("local review requires --format json")
    if any(value != "agent" for value in _option_values(args, "--audience")):
        raise ReviewRunnerError("local review requires --audience agent")
    return [*args, "--format", "json", "--audience", "agent"]


def _run_evidence_review(
    result_path: Path,
    stderr_path: Path,
    ocr_args: list[str],
    *,
    preserve_private_artifacts: bool,
    state: ReviewRunState,
    dlp_enabled: bool,
) -> int:
    """Prepare private evidence and run OCR through the composed MCP context."""

    native_store = None
    native_binary = None
    native_version: str | None = None
    try:
        if local_chatgpt.auth_mode(os.environ, local=state.local) == "chatgpt":
            local_chatgpt.provider_entry(os.environ)
            native_binary = _resolve_ocr_binary()
            version = preflight.validate_ocr_binary(executable=native_binary, announce=False)
            native_version = version
            local_chatgpt.require_supported_version(version)
            native_store = local_chatgpt.native_store(os.environ)
    except (local_chatgpt.LocalChatGPTError, preflight.PreflightError) as exc:
        raise ReviewRunnerError(str(exc)) from exc
    artifacts = repository_artifacts()
    try:
        prepare_artifact_directory(artifacts)
        remove_private_artifact(artifacts.action_receipt)
        remove_private_artifact(artifacts.action_receipt_lock)
        remove_private_artifact(artifacts.dlp_decisions)
    except OSError as exc:
        raise ReviewRunnerError("OCR private pre-execution state is unsafe") from exc
    _remove_optional_diagram_artifacts(artifacts)
    state.enter("identity")
    try:
        refs = _immutable_review_refs(_review_refs(ocr_args))
    except ShallowAncestryUnavailable as exc:
        raise ReviewRunnerError(
            "immutable review range could not be proved in a shallow repository; "
            "fetch sufficient history before review"
        ) from exc
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError(
            "immutable review range could not be proved; require resolvable commits "
            "with base an ancestor of head"
        ) from exc
    state.reviewed_sha = refs.head
    effective_range = ReviewRange(refs.base, refs.head)
    if not state.local and not is_merge_request_environment(os.environ):
        _record_unavailable_review_identity(artifacts, refs)
        raise ReviewRunnerError(
            "GitLab merge-request identity is required; use --local for a standalone review"
        )
    if not state.local:
        try:
            validate_detached_merge_request_pipeline(os.environ, expected_source_sha=refs.head)
        except ValueError as exc:
            _record_unavailable_review_identity(artifacts, refs)
            raise ReviewRunnerError(str(exc)) from exc
    _reject_owned_review_options(ocr_args)
    _prepare_review_output_artifacts(result_path, stderr_path)
    print("OCR evidence preflight: collecting immutable review refs", file=sys.stderr)
    previous_home = os.environ.get("HOME")
    session_home = Path(tempfile.mkdtemp(prefix="ocr-toolkit-session-"))
    session_home.chmod(0o700)
    os.environ["HOME"] = str(session_home)
    cleanup_error: OSError | None = None
    exit_code = 2
    enrichment: EnrichmentReceipt | None = None
    usage: dict[str, int] = {}
    publication_filtered = False
    publication: dict[str, object] = {"state": "passed"}
    evidence_action_counts: dict[str, dict[str, int]] | None = None
    background_qualification = BackgroundQualification()
    gateway = None
    federation_forbidden: tuple[str, ...] = ()
    preserve_authorized = False
    diagram_execution: DiagramExecution | None = None
    previous_handlers = _install_termination_handlers()
    try:
        try:
            state.enter("configuration")
            if diagram_requested(state.diagram_mode, local=state.local) and native_version is None:
                native_binary = native_binary or _resolve_ocr_binary()
                try:
                    native_version = preflight.validate_ocr_binary(
                        executable=native_binary, announce=False
                    )
                except Exception:
                    # Capability probing is optional; mandatory native preview
                    # and gitlink qualification retain their existing gates.
                    diagram_warning()
            _write_isolated_runtime_config(
                **({"debug": state.debug} if state.debug is not None else {}),
                **({"local": True} if native_store is not None else {}),
            )
            if native_store is not None:
                try:
                    local_chatgpt.link_native_store(native_store, session_home)
                except local_chatgpt.LocalChatGPTError as exc:
                    raise ReviewRunnerError(str(exc)) from exc
            state.enter("identity")
            identity, effective_ocr_args = _prepare_policy_context(
                refs, ocr_args, artifacts, **({"local": True} if state.local else {})
            )
            preserve_authorized = _authorize_private_artifact_preservation(
                identity, requested=preserve_private_artifacts
            )
            state.observe(
                "identity",
                "passed",
                facts={
                    "base_sha": refs.base,
                    "head_sha": refs.head,
                    "policy_sha": identity.policy_sha,
                },
            )
            state.enter("evidence")
            store = collect_repository_evidence(
                base_ref=refs.base,
                head_ref=refs.head,
                policy_ref=identity.policy_sha,
                target_ref=identity.target_sha if not state.local else None,
                include_policy_records=state.local or identity.has_protected_policy,
            )
            head_sha = store.head.commit_sha if store.head else ""
            identifiers = () if state.local else invocation_identifiers(os.environ)
            for record in collect_invocation_evidence(identifiers, head_sha=head_sha):
                if not store.add(record):
                    store.add_diagnostic("review invocation evidence was truncated by store limits")
                    break
            if identity.context is not None and not store.add(
                merge_request_context_record(identity.context)
            ):
                store.add_diagnostic("merge-request context was truncated by store limits")
            store.write(artifacts.store)
            context_config, enrichment = _prepare_enrichment(
                identity,
                artifacts,
                GitRepositoryReader(Path.cwd()),
                dlp_enabled=dlp_enabled,
            )
            if state.debug is not None:
                diagnostic_count = len(store.diagnostics) + sum(
                    len(snapshot.diagnostics)
                    for snapshot in (store.base, store.head, store.policy, store.target)
                    if snapshot is not None
                )
                state.observe(
                    "evidence",
                    "degraded" if diagnostic_count else "passed",
                    facts={"diagnostic_count": diagnostic_count},
                )
            state.enter("mcp-preflight")
            diagram_execution = DiagramExecution.prepare(
                state.diagram_mode,
                local=state.local,
                native_version=native_version,
                review_range=effective_range,
                path=artifacts.diagram,
            )
            profile = "gitlab_mr" if identity.mr_author_id is not None else "local"
            servers = mcp_config.parse_mcp_servers(profile=profile)
            if servers and identity.limited_unprotected:
                raise mcp_config.MCPConfigError(
                    "unprotected-target reviews do not allow external MCP"
                )
            if servers:
                gateway = start_gateway(
                    Registry(tuple(servers)),
                    environment=dict(os.environ),
                    forbidden=enrichment.forbidden_publication if enrichment is not None else (),
                    dlp_enabled=dlp_enabled,
                    run_id=secrets.token_hex(16),
                )
            composition = mcp_config.build_mcp_composition(
                profile="gitlab_mr" if identity.mr_author_id is not None else "local",
                context=context_config,
                allow_external=not identity.limited_unprotected,
                **({"gateway": gateway} if gateway is not None else {}),
                **(
                    {"diagram_run_id": diagram_execution.collector.run_id}
                    if diagram_execution.collector is not None
                    else {}
                ),
            )
            if diagram_execution.collector is not None and not any(
                DIAGRAM_TOOL_NAME in capability.tools for capability in composition.capabilities
            ):
                diagram_execution.unavailable()
            bootstrap = render_bootstrap(
                store,
                capabilities=composition.capabilities,
                context_hints=enrichment.bootstrap_hints if enrichment is not None else None,
                unprotected_target=identity.limited_unprotected,
                protected_policy_fallback=(
                    identity.target_protection == "unprotected" and identity.has_protected_policy
                ),
            )
            write_private_text(artifacts.bootstrap, bootstrap)
            mcp_config.apply_mcp_composition(composition)
            mcp_config.verify_mcp_composition(composition)
            summary = evidence_summary(store)
            _verify_evidence_mcp(store)
        except (
            ContextContractError,
            ContextStoreError,
            EvidenceStoreError,
            OCRConfigError,
            OSError,
            configure.OCRRuntimeConfigError,
            GitLabProviderError,
            RepositoryEvidenceError,
            ValueError,
            mcp_config.MCPConfigError,
        ) as exc:
            raise ReviewRunnerError(
                f"OCR evidence preflight failed: {redact_sensitive(str(exc))}"
            ) from exc
        records = summary.get("records")
        if not isinstance(records, int) or isinstance(records, bool) or records < 0:
            raise ReviewRunnerError("OCR evidence preflight returned an invalid MCP summary")
        state.observe(
            "mcp-preflight",
            "passed",
            facts={
                "record_count": records,
                "server_count": len(composition.capabilities),
            },
        )
        print(
            "OCR evidence preflight: ready "
            f"base={summary.get('base')} head={summary.get('head')} records={records} "
            f"mcp_servers={len(composition.capabilities)} builtin_tool={TOOL_NAME}",
            file=sys.stderr,
        )
        print(
            "OCR MCP registry: ready "
            f"servers={len(composition.capabilities)} mandatory={TOOL_NAME} self_query=summary",
            file=sys.stderr,
        )
        production_args = [
            "--from",
            refs.base,
            "--to",
            refs.head,
            *_without_diff_options(effective_ocr_args),
            "--background-file",
            str(artifacts.bootstrap),
        ]
        state.enter("preview")
        ocr_binary = native_binary or _resolve_ocr_binary()
        projection: GitlinkProjection | None = None
        gitlink_detected = False
        gitlink_plan = None
        try:
            reader = GitRepositoryReader(Path.cwd())
            gitlink_plan = plan_gitlink_input(reader, refs.base, refs.head)
            if gitlink_plan is not None:
                if native_version is None:
                    try:
                        native_version = preflight.validate_ocr_binary(
                            executable=ocr_binary, announce=False
                        )
                    except preflight.PreflightError as exc:
                        raise ReviewRunnerError(str(exc)) from exc
                if native_version == "1.13.3":
                    projection = make_gitlink_projection(reader, gitlink_plan)
                else:
                    gitlink_detected = True
        except RepositoryEvidenceError as exc:
            if gitlink_plan is not None:
                gitlink_detected = True
            else:
                try:
                    gitlink_detected = bool(changed_gitlinks(reader, refs.base, refs.head))
                except RepositoryEvidenceError:
                    raise ReviewRunnerError(
                        "changed gitlink evidence could not be qualified"
                    ) from exc
            if not gitlink_detected:
                raise ReviewRunnerError("changed gitlink evidence could not be qualified") from exc
            print(
                "OCR gitlink qualification: immutable changed pointer is outside the "
                "qualified subset; model review did not run",
                file=sys.stderr,
            )
        exit_code, background_qualification = _run_background_qualified_review(
            result_path,
            stderr_path,
            production_args,
            ocr_binary=ocr_binary,
            session_home=session_home,
            artifacts=artifacts,
            refs=refs,
            identity=identity,
            gitlink_detected=gitlink_detected,
            projection=projection,
            **({"state": state} if state.local or state.progress is not None else {}),
        )
    finally:
        previous_mask = _block_termination_signals()
        try:
            if gateway is not None:
                try:
                    federation_forbidden = gateway.forbidden_publication
                    receipt = gateway.close()
                    composition = replace(composition, federation_receipt=receipt)
                except (ValueError, OSError):
                    cleanup_error = OSError("federation cleanup could not be verified")
            if state.progress is not None:
                state.progress.phase("cleanup")
            if exit_code == 0:
                evidence_action_counts = read_action_receipt(artifacts.action_receipt)
                if diagram_execution is not None:
                    diagram_execution.capture()
            if not preserve_authorized:
                try:
                    _remove_ephemeral_review_artifacts(artifacts)
                except OSError as exc:
                    cleanup_error = cleanup_error or exc
                try:
                    shutil.rmtree(session_home)
                except OSError as exc:
                    cleanup_error = cleanup_error or exc
                state.observe("cleanup", "failed" if cleanup_error is not None else "passed")
            if previous_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = previous_home
            if cleanup_error is None and exit_code == 0:
                state.enter("result-validation")
                forbidden: tuple[str | ForbiddenValue, ...] = tuple(
                    ForbiddenValue(v, "operator_secret") for v in composition.secret_values
                )
                forbidden += tuple(
                    ForbiddenValue(v, "external_context") for v in federation_forbidden
                )
                if enrichment is not None:
                    forbidden += enrichment.forbidden_sources or tuple(
                        ForbiddenValue(v, "other") for v in enrichment.forbidden_publication
                    )
                if projection is not None:
                    _verify_gitlink_after_execution(
                        result_path, projection, preserve_authorized=preserve_authorized
                    )
                try:
                    usage, publication_filtered, publication = _finalize_ocr_result(
                        result_path,
                        composition,
                        identity,
                        enrichment,
                        evidence_action_counts,
                        forbidden=forbidden,
                        dlp_enabled=dlp_enabled,
                        toolkit_advisory=background_qualification.advisory,
                        expected_range=effective_range,
                        diagram_execution=diagram_execution,
                        **(
                            {
                                "projection": projection,
                                "selected_diff": background_qualification.selected_diff,
                            }
                            if projection is not None
                            else {}
                        ),
                        **({"private_diagnostics": True} if preserve_authorized else {}),
                        **({"report_consumer": state.admit_report} if state.local else {}),
                        **({"state": state} if state.local or state.progress is not None else {}),
                    )
                except ReviewRunnerError:
                    # Authorized diagnostic retention is owned by finalization.
                    if not preserve_authorized:
                        try:
                            result_path.unlink(missing_ok=True)
                        except OSError:
                            pass
                    raise
            if cleanup_error is None and exit_code != 0 and preserve_authorized:
                _retain_private_diagnostic_result(result_path, reason="execution-failed")
            if cleanup_error is None and exit_code == 0 and preserve_authorized:
                forbidden = tuple(
                    ForbiddenValue(v, "operator_secret") for v in composition.secret_values
                )
                forbidden += tuple(
                    ForbiddenValue(v, "external_context") for v in federation_forbidden
                )
                if enrichment is not None:
                    forbidden += enrichment.forbidden_sources or tuple(
                        ForbiddenValue(v, "other") for v in enrichment.forbidden_publication
                    )
                _write_private_dlp_decisions(
                    result_path,
                    artifacts.dlp_decisions,
                    forbidden=forbidden,
                )
        finally:
            _restore_termination_handlers(previous_handlers)
            _restore_signal_mask(previous_mask)
    if cleanup_error is not None:
        state.enter("cleanup")
        try:
            result_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ReviewRunnerError("OCR private session cleanup failed") from cleanup_error
    if preserve_authorized:
        print(
            "OCR private session artifacts retained; no posting-eligible result handoff "
            f"session_home={session_home} artifact_directory={artifacts.directory}",
            file=sys.stderr,
        )
    elif exit_code == 0:
        calls = usage.get(mcp_config.BUILTIN_EVIDENCE_SERVER, 0)
        if calls > 0:
            print(
                f"OCR evidence usage: verified tool={TOOL_NAME} calls={calls}",
                file=sys.stderr,
            )
        else:
            print("OCR evidence usage: skipped no-supported-files review", file=sys.stderr)
        if publication_filtered:
            counts = publication.get("reason_counts")
            closed_counts = counts if isinstance(counts, dict) else {}
            print(
                "OCR publication DLP: publication-filtered; safe partial result retained "
                + " ".join(f"{reason}={closed_counts.get(reason, 0)}" for reason in DLP_REASONS),
                file=sys.stderr,
            )
        elif publication.get("state") == "private-sanitized":
            counts = publication.get("reason_counts")
            closed_counts = counts if isinstance(counts, dict) else {}
            print(
                "OCR publication DLP: private-sanitized; canonical publication unchanged "
                + " ".join(f"{reason}={closed_counts.get(reason, 0)}" for reason in DLP_REASONS),
                file=sys.stderr,
            )
    return exit_code


def _open_private_artifact(path: Path, label: str) -> BufferedWriter:
    """Open one regular artifact without following a final-component symlink."""

    flags = os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        # The pre-check gives a clear error; O_NOFOLLOW closes the replacement race
        # between that check and open on platforms that expose the flag.
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        # Opening a pre-created FIFO for writing could otherwise block the CI job
        # before the descriptor can be rejected as a non-artifact sink.
        flags |= os.O_NONBLOCK
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ReviewRunnerError(f"private {label} artifact must be a regular file: {path}")
        if file_stat.st_nlink > 1:
            raise ReviewRunnerError(f"private {label} artifact must not have hard links: {path}")
        os.fchmod(descriptor, 0o600)
        # Delay truncation until the descriptor has passed type and link checks.
        os.ftruncate(descriptor, 0)
    except ReviewRunnerError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ReviewRunnerError(f"could not open private {label} artifact: {exc}") from exc
    return open(descriptor, "wb", closefd=True)


def read_stderr_excerpt(stderr_path: Path, max_chars: int = DEFAULT_DIAGNOSTIC_CHARS) -> str:
    """Read a bounded, redacted excerpt of an OCR stderr artifact."""

    if not stderr_path.exists():
        return ""
    try:
        with stderr_path.open("rb") as handle:
            chunk = handle.read(STDERR_PROBE_BYTES)
    except OSError:
        return ""

    text = chunk.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    # Redact before truncation so a secret crossing the display boundary is
    # matched against its complete environment value or credential pattern.
    return redact_sensitive(text)[:max_chars]


def _closed_provider_failure_projection(
    result_path: Path,
) -> ProviderFailureProjection | None:
    """Return only validated retry-report diagnostics from one private result."""

    try:
        result = load_ocr_result(result_path)
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge):
        return None
    return provider_failure_projection(result)


def _resolve_ocr_binary() -> str:
    """Resolve one exact executable before entering the repository-owned process cwd."""

    search_path = os.environ.get("PATH", "")
    entries = search_path.split(os.pathsep)
    if not entries or any(not entry or not Path(entry).is_absolute() for entry in entries):
        raise ReviewRunnerError("OCR executable search path is unsafe")
    candidate = shutil.which("ocr")
    if candidate is None:
        raise ReviewRunnerError("could not resolve the OCR executable")
    resolved = Path(candidate).resolve(strict=True)
    metadata = resolved.stat()
    repository = Path.cwd().resolve()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not os.access(resolved, os.X_OK)
        or resolved == repository
        or repository in resolved.parents
    ):
        raise ReviewRunnerError("resolved OCR executable is unsafe")
    return str(resolved)


def run_review(
    result_path: Path,
    stderr_path: Path,
    ocr_args: list[str],
    *,
    ocr_binary: str = "ocr",
    child_environment: dict[str, str] | None = None,
) -> int:
    """Execute `ocr review`, retain private artifacts, and report safe failures."""

    if not ocr_args:
        raise ReviewRunnerError("at least one OCR review argument is required after --")
    if result_path.absolute() == stderr_path.absolute():
        raise ReviewRunnerError("result and stderr paths must be different")
    for path, label in ((result_path, "result"), (stderr_path, "stderr")):
        if path.is_symlink():
            raise ReviewRunnerError(f"{label} path must not be a symlink: {path}")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Use explicit argv and file descriptors: OCR-controlled output never crosses
    # a shell, while umask 077 keeps both artifacts private on shared runners.
    previous_umask = os.umask(0o077)
    try:
        with ExitStack() as stack:
            result_file = stack.enter_context(_open_private_artifact(result_path, "result"))
            stderr_file = stack.enter_context(_open_private_artifact(stderr_path, "stderr"))
            if os.path.samestat(os.fstat(result_file.fileno()), os.fstat(stderr_file.fileno())):
                raise ReviewRunnerError("result and stderr paths must be different")
            completed = subprocess.run(
                [ocr_binary, "review", *ocr_args],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=result_file,
                stderr=stderr_file,
                env=child_environment
                if child_environment is not None
                else _ocr_child_environment(),
            )
    except OSError as exc:
        raise ReviewRunnerError(f"could not execute OCR: {exc}") from exc
    finally:
        os.umask(previous_umask)

    if completed.returncode != 0:
        print(f"Open Code Review exited with code {completed.returncode}.", file=sys.stderr)
        provider_projection = _closed_provider_failure_projection(result_path)
        if provider_projection is not None:
            print(render_provider_diagnostics(provider_projection), file=sys.stderr)
        else:
            excerpt = read_stderr_excerpt(stderr_path)
            if excerpt:
                print("Safe OCR stderr excerpt:", file=sys.stderr)
                print(excerpt, file=sys.stderr)
            else:
                print("OCR did not provide a readable stderr diagnostic.", file=sys.stderr)
    return completed.returncode
