"""Pure review health and finding-visibility presentation for output adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FindingVisibility:
    """Describe adapter-owned delivery without changing review health."""

    count: int
    published: bool = False
    omitted: int = 0
    suppressed: int = 0


def review_outcome_line(
    *,
    findings: FindingVisibility,
    warning_count: int,
    outcome_status: str,
    outcome_message: str,
    unreviewed_file_count: int | None = None,
    emoji: bool = False,
) -> str:
    """Render one shared decision line; publication facts belong to the adapter."""

    budget_stop = outcome_status == "budget_exceeded" or (
        outcome_status == "partial" and "budget" in outcome_message.casefold()
    )
    partial_result = outcome_status in {"partial", "completed_with_errors", "budget_exceeded"}
    has_finding_state = findings.count > 0 or findings.omitted > 0 or findings.suppressed > 0
    if outcome_status == "skipped":
        marker, status_text = "ℹ️", "Review skipped"  # noqa: RUF001
        result_text = "no supported files changed"
    elif outcome_status == "failed":
        marker, status_text = "❌", "Review failed"
        result_text = "no reliable review result was produced"
    else:
        if budget_stop:
            marker, status_text = "⚠️", "Review stopped at token budget"
        elif partial_result:
            marker, status_text = "⚠️", "Review incomplete"
        elif outcome_status == "publication-filtered":
            marker, status_text = "⚠️", "Review complete with publication filtering"
        elif outcome_status == "admission-filtered":
            marker, status_text = "⚠️", "Review complete with DLP filtering"
        elif outcome_status in {"warning", "completed_with_warnings"} or warning_count:
            marker, status_text = "⚠️", "Review complete with warnings"
        elif has_finding_state:
            marker, status_text = "🔎", "Review complete"
        else:
            marker, status_text = "✅", "Review complete"

        delivered = " published" if findings.published else ""
        if findings.count:
            noun = "finding" if findings.count == 1 else "findings"
            result_text = f"{findings.count} {noun}{delivered}"
            if partial_result:
                result_text += " from reviewed files"
        elif findings.omitted:
            result_text = f"no findings{delivered}"
            if partial_result:
                result_text += " from reviewed files"
        elif findings.suppressed:
            result_text = f"no new findings{delivered}"
            if partial_result:
                result_text += " from reviewed files"
        elif partial_result:
            result_text = "no findings in reviewed files"
        else:
            result_text = "no findings"

        if findings.omitted:
            noun = "finding" if findings.omitted == 1 else "findings"
            result_text += f"; {findings.omitted} {noun} omitted by posting limit"
        if findings.suppressed:
            noun = "finding" if findings.suppressed == 1 else "findings"
            result_text += f"; {findings.suppressed} {noun} matched prior reviewer decisions"
        if partial_result and unreviewed_file_count is not None:
            noun = "file" if unreviewed_file_count == 1 else "files"
            result_text += f"; {unreviewed_file_count} {noun} not reviewed"

    prefix = f"{marker} " if emoji else ""
    return f"{prefix}**{status_text} — {result_text}**"
