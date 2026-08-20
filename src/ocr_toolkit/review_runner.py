"""Run Open Code Review with private artifacts and safe CI diagnostics."""

from __future__ import annotations

import json
import os
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
from contextlib import ExitStack
from dataclasses import dataclass
from io import BufferedWriter
from pathlib import Path

from ocr_toolkit import configure, mcp_config
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, update_ocr_config
from ocr_toolkit.context.adapters import (
    ContextAdapterError,
    configured_secret_values,
    parse_adapter_config,
)
from ocr_toolkit.context.broker import (
    BrokerResult,
    CandidateSelection,
    acquire_external_records,
    prepare_discussion_records,
)
from ocr_toolkit.context.contracts import ContextContractError, ContextPolicy, TextBudgets
from ocr_toolkit.context.dlp import ForbiddenMatcher, check_text
from ocr_toolkit.context.policy import load_protected_policy
from ocr_toolkit.context.recognizers import recognize
from ocr_toolkit.context.store import ContextStore, ContextStoreError, PendingContextRecord
from ocr_toolkit.evidence.artifacts import (
    EvidenceArtifacts,
    prepare_artifact_directory,
    remove_private_artifact,
    repository_artifacts,
    write_private_bytes,
    write_private_text,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.invocation import collect_invocation_evidence
from ocr_toolkit.evidence.mcp import TOOL_NAME, call_tool, evidence_summary
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    normalize_repo_path,
)
from ocr_toolkit.evidence.review_context import (
    MergeRequestContext,
    ReviewContextModeError,
    merge_request_context_record,
    parse_review_context_mode,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    TOOLKIT_RESULT_KEY,
    TOOLKIT_RESULT_SCHEMA_VERSION,
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    inspect_ocr_result,
    transform_ocr_result,
)
from ocr_toolkit.pre_execution import (
    PROTECTED_TARGET_RULE_PATH_PENDING,
    STATUS_SCHEMA,
    PreExecutionStatus,
    PreExecutionStatusError,
    write_pre_execution_status,
)
from ocr_toolkit.providers.gitlab import (
    GitLabProviderError,
    acquire_review_snapshot,
    invocation_identifiers,
    is_merge_request_environment,
)
from ocr_toolkit.providers.gitlab_discussions import acquire_discussions
from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

STDERR_PROBE_BYTES = 64 * 1024
DEFAULT_DIAGNOSTIC_CHARS = 4_000
DLP_REASONS = ("forbidden", "invalid_text", "laundering", "limit", "pii", "secret")
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


class ReviewRunnerError(Exception):
    """The local OCR review process could not be started safely."""


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


@dataclass(frozen=True, slots=True)
class ReviewIdentity:
    """Bind immutable review/provider identities to context selection."""

    source_sha: str
    policy_sha: str
    mr_author_id: int | None
    context_mode: str
    context: MergeRequestContext | None

    @property
    def context_state(self) -> str:
        if self.context_mode == "off":
            return "disabled"
        return self.context.state if self.context is not None else "degraded"


@dataclass(frozen=True, slots=True)
class EnrichmentReceipt:
    """Carry closed context facts after acquisition and cleanup."""

    policy_digest: str
    completeness: dict[str, str]
    degradation_counts: dict[str, int]
    required_degraded: bool
    mutable_admitted: bool
    forbidden_publication: tuple[str, ...]


def _write_isolated_runtime_config() -> None:
    """Rebuild only validated runtime settings inside the fresh OCR home."""

    update_ocr_config(configure.build_config_updates())


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
) -> dict[str, object]:
    """Return a closed privacy-safe receipt tied to review-time facts."""

    try:
        outcome = parse_result_outcome(payload)
    except OcrResultContractError as exc:
        raise ReviewRunnerError(f"OCR result has an unsupported outcome contract: {exc}") from exc

    tool_calls = payload.get("tool_calls")
    by_tool = tool_calls.get("by_tool") if isinstance(tool_calls, dict) else None
    total_calls = tool_calls.get("total") if isinstance(tool_calls, dict) else None
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
                or not 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            ):
                raise ReviewRunnerError("OCR result has an invalid known MCP usage count")
            owner = owners[tool]
            aggregate = usage.get(owner, 0) + count
            if aggregate > MAX_TOOLKIT_MCP_USAGE_COUNT:
                raise ReviewRunnerError("OCR result exceeds the per-server MCP usage bound")
            usage[owner] = aggregate
    known_usage_total = sum(usage.values())
    if tool_calls is None and outcome.kind == "failed":
        total_calls = 0
    if (
        not isinstance(total_calls, int)
        or isinstance(total_calls, bool)
        or total_calls < known_usage_total
    ):
        raise ReviewRunnerError("OCR result has inconsistent aggregate MCP usage")
    evidence_calls = by_tool.get(TOOL_NAME, 0) if isinstance(by_tool, dict) else 0
    evidence_used = isinstance(evidence_calls, int) and evidence_calls > 0
    if outcome.requires_evidence_mcp and not evidence_used:
        raise ReviewRunnerError(f"OCR review did not call the mandatory {TOOL_NAME} tool")
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
            "policy_sha": identity.policy_sha,
            "mr_author_id": identity.mr_author_id,
        },
        "context": context_receipt,
        "mcp": {
            "capabilities": capabilities,
            "usage": dict(sorted(usage.items())),
        },
        "evidence": {
            "mandatory": outcome.requires_evidence_mcp,
            "used": evidence_used,
            "calls": evidence_calls,
        },
        "publication": {"dlp": "passed"},
        "cleanup": {"result": "passed"},
    }


def _dlp_reasons(
    value: object, *, budgets: TextBudgets, matcher: ForbiddenMatcher
) -> Counter[str]:
    """Count closed DLP failures without retaining hostile strings or locations."""

    reasons: Counter[str] = Counter()
    stack = [value]
    while stack:
        nested = stack.pop()
        if isinstance(nested, dict):
            stack.extend(nested.keys())
            stack.extend(nested.values())
        elif isinstance(nested, list):
            stack.extend(nested)
        elif isinstance(nested, str):
            checked = check_text(
                nested,
                budgets=budgets,
                publication=True,
                forbidden_matcher=matcher,
            )
            if not checked.admitted:
                reasons[checked.reason] += 1
    return reasons


def _safe_publication_comments(
    value: object, *, budgets: TextBudgets, matcher: ForbiddenMatcher
) -> tuple[list[dict[str, object]], int, int]:
    """Retain safe finding fields and omit only findings with unsafe content."""

    if not isinstance(value, list):
        return [], 0, 0
    retained: list[dict[str, object]] = []
    omitted_fields = 0
    for item in value:
        if not isinstance(item, dict):
            continue
        projected: dict[str, object] = {}
        content_unsafe = False
        for key, field_value in item.items():
            if not isinstance(key, str) or key not in QUARANTINE_COMMENT_FIELDS:
                continue
            if _dlp_reasons(field_value, budgets=budgets, matcher=matcher):
                omitted_fields += 1
                content_unsafe = content_unsafe or key == "content"
                continue
            projected[key] = field_value
        if projected and not content_unsafe:
            retained.append(projected)
    return retained, len(value) - len(retained), omitted_fields


def _safe_publication_warnings(
    value: object, *, budgets: TextBudgets, matcher: ForbiddenMatcher
) -> tuple[list[object], int]:
    """Retain DLP-safe warnings while dropping unsafe or malformed items atomically."""

    if not isinstance(value, list):
        return [], 0
    retained = [
        item for item in value if not _dlp_reasons(item, budgets=budgets, matcher=matcher)
    ]
    return retained, len(value) - len(retained)


def _closed_tool_calls(
    value: object, *, allowed_tools: frozenset[str]
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
        and isinstance(count, int)
        and not isinstance(count, bool)
        and 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
    }
    return {"total": total, "by_tool": dict(sorted(projected.items()))}


def _publication_projection(
    payload: dict[str, object],
    *,
    forbidden: tuple[str, ...],
    allowed_tools: frozenset[str],
) -> tuple[dict[str, object], dict[str, object], bool]:
    """Return the original result or a DLP-safe partial publication result."""

    budgets = TextBudgets(max_chars=2_000_000, max_bytes=8_000_000, max_lines=100_000)
    matcher = ForbiddenMatcher.compile(forbidden)
    reasons = _dlp_reasons(payload, budgets=budgets, matcher=matcher)
    if not reasons:
        return payload, {"dlp": "passed"}, False

    comments, omitted_comments, omitted_fields = _safe_publication_comments(
        payload.get("comments"), budgets=budgets, matcher=matcher
    )
    warnings, omitted_warnings = _safe_publication_warnings(
        payload.get("warnings"), budgets=budgets, matcher=matcher
    )
    outcome = parse_result_outcome(payload)
    publication: dict[str, object] = {
        "dlp": "filtered",
        "reason_counts": {reason: reasons.get(reason, 0) for reason in DLP_REASONS},
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
    partial_result: dict[str, object] = {
        "status": "completed_with_errors",
        "message": (
            "Publication policy produced a safe partial OCR result. Independently safe findings "
            "may be published, but the result must not be treated as a complete review."
        ),
        "comments": comments,
        "warnings": warnings,
        "tool_calls": _closed_tool_calls(payload.get("tool_calls"), allowed_tools=allowed_tools),
    }
    return partial_result, publication, True


def _finalize_ocr_result(
    result_path: Path,
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
    enrichment: EnrichmentReceipt | None,
    *,
    forbidden: tuple[str, ...],
) -> tuple[dict[str, int], bool, dict[str, object]]:
    """Validate, DLP-project, and receipt-bind one result in one atomic read/replace."""

    filtered = False
    publication: dict[str, object] = {"dlp": "passed"}
    usage: dict[str, int] = {}
    allowed_tools = frozenset(
        tool for capability in composition.capabilities for tool in capability.tools
    )

    def finalize(payload: dict[str, object]) -> dict[str, object]:
        nonlocal filtered, publication, usage
        if TOOLKIT_RESULT_KEY in payload:
            raise OcrResultMalformed(
                f"OCR result contains reserved field {TOOLKIT_RESULT_KEY!r}"
            )
        metadata = _review_receipt(payload, composition, identity, enrichment)
        projected, publication, filtered = _publication_projection(
            payload, forbidden=forbidden, allowed_tools=allowed_tools
        )
        metadata["publication"] = publication
        metadata["schema_version"] = TOOLKIT_RESULT_SCHEMA_VERSION
        mcp = metadata.get("mcp")
        raw_usage = mcp.get("usage") if isinstance(mcp, dict) else None
        usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
        return {**projected, TOOLKIT_RESULT_KEY: metadata}

    try:
        transform_ocr_result(result_path, finalize)
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge) as exc:
        raise ReviewRunnerError("OCR result is not valid bounded JSON") from exc
    return usage, filtered, publication


def _record_ocr_result_mcp_usage(
    result_path: Path,
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
    enrichment: EnrichmentReceipt | None = None,
) -> dict[str, int]:
    """Verify MCP use and bind the closed review-time receipt to the result."""

    usage, filtered, _publication = _finalize_ocr_result(
        result_path,
        composition,
        identity,
        enrichment,
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
    return ReviewRefs(reader.resolve_commit(refs.base), reader.resolve_commit(refs.head))


def _reject_owned_background(args: list[str]) -> None:
    """Reject caller attempts to replace the toolkit-owned bootstrap file."""

    if _option_values(args, "--background-file"):
        raise ReviewRunnerError(
            "--background-file is managed by ocr-ci review; use --background for extra context"
        )


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
            reason=PROTECTED_TARGET_RULE_PATH_PENDING,
            diff_base_sha=refs.base,
            source_sha=refs.head,
            policy_sha=policy_sha,
        ),
    )
    return True


def _prepare_policy_context(
    refs: ReviewRefs, ocr_args: list[str], artifacts: EvidenceArtifacts
) -> tuple[ReviewIdentity, list[str]]:
    """Capture policy identity and selected context, then materialize rules."""

    try:
        context_mode = parse_review_context_mode(os.environ.get("OCR_REVIEW_CONTEXT_MODE"))
    except ReviewContextModeError as exc:
        raise ReviewRunnerError(str(exc)) from exc
    reader = GitRepositoryReader(Path.cwd())
    context = None
    author_id = None
    if is_merge_request_environment(os.environ):
        snapshot = acquire_review_snapshot(
            os.environ,
            expected_head=refs.head,
            include_metadata=context_mode in {"metadata", "enriched"},
        )
        reader.fetch_commit(snapshot.target_sha)
        policy_sha = reader.resolve_commit(snapshot.target_sha)
        context = snapshot.context
        author_id = snapshot.author_id
    else:
        if context_mode in {"metadata", "enriched"}:
            raise ReviewRunnerError(
                f"{context_mode} review context requires a GitLab merge request"
            )
        policy_sha = refs.base
    identity = ReviewIdentity(refs.head, policy_sha, author_id, context_mode, context)
    rule = _one_option(ocr_args, "--rule")
    if rule is None:
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    repository_path = _repository_rule_path(rule, reader.root)
    if repository_path is None:
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    try:
        content = reader.read_blob(policy_sha, repository_path)
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError("protected-target OCR rule is unavailable or unsafe") from exc
    if content is None:
        if author_id is not None:
            try:
                setup_pending = _record_rules_path_setup(
                    reader,
                    artifacts,
                    refs=refs,
                    policy_sha=policy_sha,
                    repository_path=repository_path,
                )
            except (PreExecutionStatusError, RepositoryEvidenceError) as exc:
                raise ReviewRunnerError(
                    "protected-target OCR rule does not exist and the source candidate is unsafe"
                ) from exc
            if setup_pending:
                raise ReviewRunnerError("protected-target OCR rule path setup is pending")
        raise ReviewRunnerError("protected-target OCR rule does not exist")
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
        text = record.projections.get("model", {}).get("text", "")
        text = text if isinstance(text, str) else ""
        next_chars = chars + len(text)
        next_bytes = bytes_count + len(text.encode())
        next_lines = lines + (text.count("\n") + 1 if text else 0)
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


def _select_reference_candidates(
    policy: ContextPolicy, candidate_texts: list[str]
) -> list[CandidateSelection]:
    """Bind each distinct syntax candidate to its independent protected source."""

    selections: list[CandidateSelection] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for reference in policy.references:
        for text in candidate_texts:
            for candidate in recognize(
                text,
                resource_class=reference.resource_class,
                policy=reference.recognizer,
            ):
                key = (
                    reference.adapter,
                    reference.tenant,
                    reference.resource_class,
                    candidate.recognizer,
                    candidate.value,
                )
                if key not in seen:
                    seen.add(key)
                    selections.append(CandidateSelection(reference, candidate))
    return selections


def _prepare_enrichment(
    identity: ReviewIdentity,
    artifacts: EvidenceArtifacts,
    reader: GitRepositoryReader,
) -> tuple[mcp_config.MCPContextConfig | None, EnrichmentReceipt | None]:
    """Acquire all external context before the one OCR model loop and commit it locally."""

    if identity.context_mode != "enriched":
        remove_private_artifact(artifacts.context_store)
        return None, None
    if identity.context is None:
        raise ReviewRunnerError("enriched review context requires validated MR metadata")
    policy = load_protected_policy(reader.read_blob, policy_sha=identity.policy_sha)
    now = int(time.time())
    acquisition_deadline = time.monotonic() + policy.budgets.timeout_ms / 1000
    run_id = secrets.token_urlsafe(24)
    completeness: dict[str, str] = {}
    degradation = {"invalid": 0, "limit": 0, "unavailable": 0}
    required_degraded = False
    pending: list[PendingContextRecord] = []
    candidate_texts = list(_context_texts(identity.context))
    adapters = parse_adapter_config(os.environ.get("OCR_REVIEW_CONTEXT_ADAPTERS_JSON"))
    adapter_secrets = configured_secret_values(adapters, os.environ)
    if policy.forge_discussions is not None:
        discussion_policy = policy.forge_discussions
        source = "forge:gitlab_discussions"
        try:
            snapshot = acquire_discussions(
                os.environ,
                project_id=identity.context.project_id,
                merge_request_iid=identity.context.merge_request_iid,
                source_sha=identity.source_sha,
                run_id=run_id,
                policy=discussion_policy,
                now=now,
                deadline=acquisition_deadline,
                forbidden=adapter_secrets,
            )
        except GitLabProviderError:
            completeness[source] = "unavailable"
            degradation["unavailable"] += 1
            required_degraded = discussion_policy.required
        else:
            completeness[source] = snapshot.state
            if snapshot.state != "complete":
                degradation["invalid" if snapshot.state == "mutated" else "limit"] += 1
                required_degraded = required_degraded or discussion_policy.required
            pending.extend(
                prepare_discussion_records(
                    snapshot.records,
                    policy=discussion_policy,
                    expiry=now + 3_600,
                )
            )
            candidate_texts.extend(record.body for record in snapshot.records)
    selections = _select_reference_candidates(policy, candidate_texts)
    external: BrokerResult = acquire_external_records(
        policy=policy,
        adapters=adapters,
        selections=selections,
        run_id=run_id,
        now=now,
        environment=os.environ,
        forbidden=adapter_secrets,
        deadline=acquisition_deadline,
    )
    pending.extend(external.records)
    completeness.update(external.completeness)
    for reason, count in external.degradation_counts.items():
        degradation[reason] += count
    required_degraded = required_degraded or external.required_degraded
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
    for record in context_store.records:
        published = record.projections["publish"]
        for field, value in record.projections["model"].items():
            if field in published:
                continue
            stack = [value]
            while stack:
                nested = stack.pop()
                if isinstance(nested, dict):
                    stack.extend(nested.values())
                elif isinstance(nested, list):
                    stack.extend(nested)
                elif isinstance(nested, str) and nested:
                    forbidden_values.append(nested)
    forbidden = (*adapter_secrets, *forbidden_values)
    receipt = EnrichmentReceipt(
        policy_digest=policy.digest,
        completeness=dict(sorted(completeness.items())),
        degradation_counts=dict(sorted(degradation.items())),
        required_degraded=required_degraded,
        mutable_admitted=any(record.mutable for record in context_store.records),
        forbidden_publication=forbidden,
    )
    return (
        mcp_config.MCPContextConfig(
            store_path=str(artifacts.context_store.resolve()),
            run_id=run_id,
            policy_digest=policy.digest,
        ),
        receipt,
    )


def _publication_dlp(path: Path, *, forbidden: tuple[str, ...]) -> None:
    """Reject any unsafe OCR-controlled string before result acceptance."""

    payload = inspect_ocr_result(path)
    stack = [payload]
    budgets = TextBudgets(max_chars=2_000_000, max_bytes=8_000_000, max_lines=100_000)
    matcher = ForbiddenMatcher.compile(forbidden)
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, str):
            checked = check_text(
                value,
                budgets=budgets,
                publication=True,
                forbidden_matcher=matcher,
            )
            if not checked.admitted:
                raise ReviewRunnerError("OCR result failed publication DLP")


def run_evidence_review(result_path: Path, stderr_path: Path, ocr_args: list[str]) -> int:
    """Prepare private evidence and run OCR through the composed MCP context."""

    artifacts = repository_artifacts()
    try:
        prepare_artifact_directory(artifacts)
        remove_private_artifact(artifacts.pre_execution_status)
    except OSError as exc:
        raise ReviewRunnerError("OCR private pre-execution state is unsafe") from exc
    refs = _immutable_review_refs(_review_refs(ocr_args))
    _reject_owned_background(ocr_args)
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
    publication: dict[str, object] = {"dlp": "passed"}
    previous_handlers = _install_termination_handlers()
    try:
        try:
            _write_isolated_runtime_config()
            identity, effective_ocr_args = _prepare_policy_context(refs, ocr_args, artifacts)
            store = collect_repository_evidence(
                base_ref=refs.base, head_ref=refs.head, policy_ref=identity.policy_sha
            )
            head_sha = store.head.commit_sha if store.head else ""
            identifiers = invocation_identifiers(os.environ)
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
                identity, artifacts, GitRepositoryReader(Path.cwd())
            )
            composition = mcp_config.build_mcp_composition(
                profile="gitlab_mr" if identity.mr_author_id is not None else "local",
                context=context_config,
            )
            bootstrap = render_bootstrap(store, capabilities=composition.capabilities)
            write_private_text(artifacts.bootstrap, bootstrap)
            mcp_config.apply_mcp_composition(composition)
            mcp_config.verify_mcp_composition(composition)
            summary = evidence_summary(store)
            _verify_evidence_mcp(store)
        except (
            ContextAdapterError,
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
        exit_code = run_review(
            result_path,
            stderr_path,
            [
                "--from",
                refs.base,
                "--to",
                refs.head,
                *_without_diff_options(effective_ocr_args),
                "--background-file",
                str(artifacts.bootstrap),
            ],
            ocr_binary=_resolve_ocr_binary(),
        )
    finally:
        previous_mask = _block_termination_signals()
        try:
            try:
                remove_private_artifact(artifacts.context_store)
            except OSError as exc:
                cleanup_error = exc
            try:
                shutil.rmtree(session_home)
            except OSError as exc:
                cleanup_error = cleanup_error or exc
            finally:
                if previous_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = previous_home
            if cleanup_error is None and exit_code == 0:
                forbidden = (*composition.secret_values,)
                if enrichment is not None:
                    forbidden += enrichment.forbidden_publication
                try:
                    usage, publication_filtered, publication = _finalize_ocr_result(
                        result_path,
                        composition,
                        identity,
                        enrichment,
                        forbidden=forbidden,
                    )
                except ReviewRunnerError:
                    try:
                        result_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise
        finally:
            _restore_termination_handlers(previous_handlers)
            _restore_signal_mask(previous_mask)
    if cleanup_error is not None:
        try:
            result_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ReviewRunnerError("OCR private session cleanup failed") from cleanup_error
    if exit_code == 0:
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
                "OCR publication DLP: filtered; safe partial result retained "
                + " ".join(
                    f"{reason}={closed_counts.get(reason, 0)}" for reason in DLP_REASONS
                ),
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


def _resolve_ocr_binary() -> str:
    """Resolve one exact executable before entering the repository-owned process cwd."""

    candidate = shutil.which("ocr")
    if candidate is None:
        raise ReviewRunnerError("could not resolve the OCR executable")
    resolved = Path(candidate).resolve(strict=True)
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode) or not os.access(resolved, os.X_OK):
        raise ReviewRunnerError("resolved OCR executable is unsafe")
    return str(resolved)


def run_review(
    result_path: Path,
    stderr_path: Path,
    ocr_args: list[str],
    *,
    ocr_binary: str = "ocr",
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
            )
    except OSError as exc:
        raise ReviewRunnerError(f"could not execute OCR: {exc}") from exc
    finally:
        os.umask(previous_umask)

    if completed.returncode != 0:
        print(f"Open Code Review exited with code {completed.returncode}.", file=sys.stderr)
        excerpt = read_stderr_excerpt(stderr_path)
        if excerpt:
            print("Safe OCR stderr excerpt:", file=sys.stderr)
            print(excerpt, file=sys.stderr)
        else:
            print("OCR did not provide a readable stderr diagnostic.", file=sys.stderr)
    return completed.returncode
