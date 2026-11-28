"""Normalize OCR publication notes into content-free telemetry records."""

import re
from typing import Any

from .grammar import SEVERITIES
from .metrics import finding_counts, operational_signals, posting_counts, presentation_signals
from .signals import parse_ocr_federation, parse_ocr_publication_dlp_signal
from .status import (
    empty_ocr_result,
    has_current_summary_markers,
    has_summary_marker,
    is_ocr_summary,
    metadata_sections,
    ocr_canonical_header,
    parse_ocr_repository_coverage,
    parse_ocr_review_mode,
    parse_status_note,
    publication_body,
)
from .usage import parse_ocr_token_usage, parse_review_model, parse_usage


def _summary_outcome(status_text: str, layout: str) -> tuple[str, bool]:
    """Distinguish an explicit historical outcome from the shared current filtering heading."""

    outcome_match = re.search(
        r"\*\*(?:Review (complete with publication filtering|complete with warnings|complete|incomplete|stopped at token budget|skipped|failed)\b|(Analysis complete; output incomplete) — )",
        status_text,
        re.IGNORECASE,
    )
    outcome = {
        "complete": "complete",
        "complete with warnings": "complete_with_warnings",
        "complete with publication filtering": "complete_publication_filtered",
        "incomplete": "incomplete",
        "stopped at token budget": "budget_exceeded",
        "skipped": "skipped",
        "failed": "failed",
        "analysis complete; output incomplete": "complete_publication_filtered",
    }.get((outcome_match[1] or outcome_match[2]).lower() if outcome_match else "", "unknown")
    if outcome == "unknown":
        normalized = status_text.casefold()
        if "stopped after reaching its token budget" in normalized:
            outcome = "budget_exceeded"
        elif "no supported files changed" in normalized or "review skipped" in normalized:
            outcome = "skipped"
        elif (
            "review did not complete cleanly" in normalized
            or re.search(r"\b(partial coverage|partial review)\b", normalized)
            or "could not be reviewed due to errors" in normalized
        ):
            outcome = "incomplete"
        elif (
            "**warnings:**" in normalized
            or "reviewed with warnings" in normalized
            or (layout == "heading_status" and re.search(r"(?m)^\s*⚠️", status_text))
        ):
            outcome = "complete_with_warnings"
        elif layout == "heading_status" and re.search(
            r"(?m)^\s*\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}", status_text
        ):
            outcome = "skipped"
        elif layout == "heading_status" and re.search(r"(?m)^\s*❌", status_text):
            outcome = "incomplete"
        elif (
            (layout == "heading_status" and re.search(r"(?m)^\s*✅", status_text))
            or (
                layout == "heading_status"
                and re.search(
                    r"\b(?:Found [0-9]{1,12} issue(?:\(s\)|s)?|No issues found|No comments generated)\b",
                    status_text,
                    re.IGNORECASE,
                )
            )
            or (
                layout == "compact_no_findings"
                and re.search(r"\bNo (?:review )?comments generated\b", status_text, re.IGNORECASE)
            )
            or (
                layout == "compact_summary"
                and re.search(
                    r"\b(?:found \*\*[0-9]{1,12}\*\* issue(?:\(s\)|s)?|No issues found)\b",
                    status_text,
                    re.IGNORECASE,
                )
            )
        ):
            outcome = "complete"
    return outcome, bool(outcome_match and outcome_match[2])


def _summary_layout(body: str, stripped: str, canonical_status: bool) -> str:
    """Identify the renderer layout from the protected leading material."""

    if stripped.startswith("## Open Code Review\n") or has_summary_marker(body):
        layout = "canonical" if canonical_status else "split_status"
    elif re.search(r"(?m)^# Open Code Review summary\s*$", stripped):
        layout = "heading_status"
    elif stripped.startswith("**Open Code Review summary**"):
        layout = "compact_summary"
    elif stripped.startswith("**Open Code Review**\n\n"):
        layout = "compact_no_findings"
    else:
        layout = "unknown"
    return layout


def parse_publication(body: str) -> dict[str, Any] | None:
    """Parse historical and current OCR summary layouts into safe telemetry."""

    if len(body) > 128 * 1024:
        return None
    body = re.sub(
        r"\A<!-- open-code-review-bot head=[0-9a-f]{40} version=[1-9][0-9]{0,18} -->",
        "<!-- open-code-review-bot -->",
        body.replace("\r\n", "\n"),
    )
    if "\x00" in body or not is_ocr_summary(body):
        return None
    if status_note := parse_status_note(body):
        return status_note
    stripped = publication_body(body)
    canonical = ocr_canonical_header(stripped)
    current_summary = canonical is not None and has_current_summary_markers(body)
    if canonical is None and has_summary_marker(body):
        canonical = ocr_canonical_header(f"## Open Code Review\n\n{stripped}")
    visible, technical, signal_lines = metadata_sections(stripped)
    canonical_status = canonical is not None
    layout = _summary_layout(body, stripped, canonical_status)
    status_text = canonical[0] if canonical else "\n".join(visible.splitlines()[:12])
    metrics_text = visible if technical is None else technical
    outcome, shared_filtering_heading = _summary_outcome(status_text, layout)
    model_identity = (
        parse_review_model(technical)
        if current_summary and technical is not None and outcome != "skipped"
        else {}
    )
    publication_filter, invalid_publication_filter = parse_ocr_publication_dlp_signal(signal_lines)
    federation, invalid_federation = parse_ocr_federation(metrics_text)
    operational, invalid_operations = operational_signals(metrics_text, status_text)
    filtered_signal = (
        isinstance(publication_filter, dict)
        and publication_filter.get("state") == "publication-filtered"
    )
    if (
        outcome == "complete_publication_filtered"
        and shared_filtering_heading
        and publication_filter is None
    ):
        # An admission-filtered summary uses the same heading without a DLP signal.
        outcome = "incomplete"
    if (
        outcome == "unknown"
        or invalid_publication_filter
        or invalid_federation
        or invalid_operations
        or (outcome == "complete_publication_filtered" and not filtered_signal)
    ):
        result = empty_ocr_result("unknown", layout)
        result["recognized"] = False
        result["tokens"] = parse_ocr_token_usage(metrics_text)
        if model_identity.get("model_rejected") is True:
            result["model_rejected"] = True
        return result
    posting, coverage = posting_counts(metrics_text, canonical_status=canonical_status)
    findings, counts = finding_counts(status_text, visible, metrics_text)
    if outcome == "skipped":
        findings = None
    elif findings is None and {"inline", "fallback"} <= posting.keys():
        findings = posting["inline"] + posting["fallback"]
    review_mode, review_mode_invalid = parse_ocr_review_mode(body)
    repository_coverage, repository_coverage_invalid = parse_ocr_repository_coverage(body)
    return {
        "outcome": outcome,
        "recognized": layout != "unknown",
        "layout": layout,
        "result_kind": "model",
        "findings": findings,
        "findings_reported": findings is not None,
        "model_started": False if outcome == "skipped" else None,
        "severity": {key: value for key, value in counts.items() if key in SEVERITIES},
        "categories": {key: value for key, value in counts.items() if key not in SEVERITIES},
        "posting": posting,
        "coverage": coverage,
        "federation": federation,
        "publication_filter": publication_filter,
        "limited_comment_only": review_mode == "limited_comment_only",
        "review_mode": review_mode,
        "review_mode_invalid": review_mode_invalid,
        "repository_coverage": repository_coverage,
        "repository_coverage_invalid": repository_coverage_invalid,
        **model_identity,
        **parse_usage(metrics_text),
        **operational,
        **presentation_signals(metrics_text, visible),
    }
