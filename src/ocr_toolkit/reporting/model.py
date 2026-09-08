"""Compose admitted review data independently of provider acquisition and delivery."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, get_args

from ocr_toolkit.ocr_result import OcrToolkitAdvisory
from ocr_toolkit.reporting.dlp import publication_dlp_state, publication_outcome_for_summary
from ocr_toolkit.reporting.metadata import format_token_usage_summary
from ocr_toolkit.reporting.result import CoverageDiagnostics, normalize_coverage_diagnostics
from ocr_toolkit.reporting.usage import (
    format_tool_calls_summary,
    format_verified_mcp_usage,
    validated_completed_actions,
)
from ocr_toolkit.result_contract import OcrResultContractError, ReviewOutcome, parse_result_outcome

FailureStage = Literal[
    "configuration",
    "identity",
    "evidence",
    "mcp-preflight",
    "preview",
    "subprocess",
    "result-validation",
    "mcp-use",
    "dlp",
    "cleanup",
    "reporting",
]


@dataclass(frozen=True, slots=True)
class ExecutionFacts:
    """Carry execution-owner facts separately from model output or forge receipts.

    Only the runner's successful evidence reconciliation and DLP finalization may
    supply these values. Rendering does not confer authority on input claims.
    """

    mcp_usage: dict[str, int]
    evidence: dict[str, Any]
    publication: dict[str, Any]
    advisory: OcrToolkitAdvisory | None = None


@dataclass(frozen=True, slots=True)
class ReviewReport:
    """Snapshot common review facts before an adapter applies delivery policy."""

    outcome: ReviewOutcome
    comments: tuple[dict[str, Any], ...]
    warnings: tuple[Any, ...]
    diagnostics: CoverageDiagnostics
    reviewed_sha: str = ""
    outcome_message: str = ""
    tool_calls_summary: str = ""
    token_usage_summary: str = ""
    mcp_usage_summary: str = ""
    publication: dict[str, Any] | None = None
    advisory: OcrToolkitAdvisory | None = None
    failure_stage: FailureStage | None = None


def report_from_result(
    result: dict[str, Any], *, execution: ExecutionFacts, reviewed_sha: str = ""
) -> ReviewReport:
    """Snapshot an already admitted result and separately verified execution facts."""

    if reviewed_sha and re.fullmatch(r"[0-9a-f]{40}", reviewed_sha) is None:
        raise OcrResultContractError("report reviewed commit is not an immutable SHA")
    comments = result.get("comments", [])
    warnings = result.get("warnings", [])
    if not isinstance(comments, list) or any(not isinstance(item, dict) for item in comments):
        raise OcrResultContractError("report comments must be a list of objects")
    if not isinstance(warnings, list):
        raise OcrResultContractError("report warnings must be a list")
    state = publication_dlp_state(execution.publication)
    if state is None:
        raise OcrResultContractError("report DLP admission facts are unavailable")
    outcome = publication_outcome_for_summary(parse_result_outcome(result), execution.publication)
    mcp_summary = format_verified_mcp_usage(
        mcp_usage=execution.mcp_usage, evidence=execution.evidence
    )
    completed = validated_completed_actions(execution.evidence)
    if outcome.requires_evidence_mcp and (
        not mcp_summary
        or completed is None
        or completed["summary"] < 1
        or execution.evidence.get("mandatory") is not True
    ):
        raise OcrResultContractError("report verified evidence usage is unavailable")
    message = result.get("message")
    return ReviewReport(
        outcome=outcome,
        comments=tuple(deepcopy(comments)),
        warnings=tuple(deepcopy(warnings)),
        diagnostics=normalize_coverage_diagnostics(
            outcome, warnings, legacy_warning_fallback=state != "publication-filtered"
        ),
        reviewed_sha=reviewed_sha,
        outcome_message=message if isinstance(message, str) else "",
        tool_calls_summary=format_tool_calls_summary(result.get("tool_calls")),
        token_usage_summary=format_token_usage_summary(result),
        mcp_usage_summary=mcp_summary,
        publication=deepcopy(execution.publication),
        advisory=execution.advisory,
    )


def failed_report(stage: FailureStage, *, reviewed_sha: str = "") -> ReviewReport:
    """Represent unavailable review data without rendering raw exceptions or output."""

    if stage not in get_args(FailureStage):
        raise OcrResultContractError("report failure stage is unsupported")
    safe_sha = reviewed_sha if re.fullmatch(r"[0-9a-f]{40}", reviewed_sha) else ""
    return ReviewReport(
        outcome=ReviewOutcome(status="failed", kind="failed", budget_exceeded=False),
        comments=(),
        warnings=(),
        diagnostics=CoverageDiagnostics((), 0, 0, 0, 0),
        reviewed_sha=safe_sha,
        failure_stage=stage,
    )
