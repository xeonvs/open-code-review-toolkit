"""Provider-neutral validation of DLP admission and original coverage facts."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.ocr_result import MAX_TOOLKIT_MCP_USAGE_COUNT
from ocr_toolkit.result_contract import OcrResultContractError, ReviewOutcome


def format_dlp_admission(publication: Any) -> str:
    """Render only closed DLP facts, without implying a provider mutation."""

    state = publication_dlp_state(publication)
    if state is None:
        return "- DLP admission: unavailable"
    if state == "passed":
        return "- DLP admission: passed"
    reasons = ", ".join(
        f"{reason}: {count}"
        for reason, count in sorted(publication["reason_counts"].items())
        if count > 0
    )
    if state == "private-sanitized":
        return (
            f"- DLP admission: private fields sanitized ({publication['sanitized_fields']}); "
            f"admitted findings unchanged; reasons: {reasons}"
        )
    retained, omitted = publication["retained"], publication["omitted"]
    return (
        f"- DLP admission: filtered; retained {retained['comments']} finding(s), "
        f"{retained['warnings']} warning(s); omitted {omitted['comments']} finding(s), "
        f"{omitted['warnings']} warning(s), {omitted['fields']} field(s); reasons: {reasons}"
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
