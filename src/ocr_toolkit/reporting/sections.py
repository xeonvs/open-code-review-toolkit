"""Pure shared finding, coverage and warning summary sections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ocr_toolkit.common.markdown import inline_code as _inline_code
from ocr_toolkit.common.markdown import neutralize_quick_actions
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.reporting.metadata import (
    CATEGORY_EMOJI,
    OCR_FINDING_CATEGORY_ORDER,
    OCR_FINDING_SEVERITY_ORDER,
    SEVERITY_EMOJI,
    finding_metadata,
)
from ocr_toolkit.reporting.result import CoverageDiagnostics, ocr_warning_text
from ocr_toolkit.reporting.text import compact_escaped_text


def inline_code(value: str) -> str:
    """Escape controls and delimiters in report labels."""
    return _inline_code(value, escape_controls=True)


def report_sections(
    comments: Sequence[dict[str, Any]],
    diagnostics: CoverageDiagnostics,
    warnings: Sequence[Any],
    *,
    use_emoji: bool = False,
) -> list[str]:
    """Render the same bounded diagnostic sections for every output adapter."""
    lines: list[str] = []
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for comment in comments:
        severity, category = finding_metadata(comment)
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    if severity_counts or category_counts:
        lines.extend(["", "### Findings", ""])
        for value in OCR_FINDING_SEVERITY_ORDER:
            count = severity_counts.get(value, 0)
            if count:
                icon = f"{SEVERITY_EMOJI[value]} " if use_emoji else ""
                lines.append(f"- {icon}{inline_code(value)}: {count}")
        for value in OCR_FINDING_CATEGORY_ORDER:
            count = category_counts.get(value, 0)
            if count:
                icon = f"{CATEGORY_EMOJI[value]} " if use_emoji else ""
                lines.append(f"- {icon}{inline_code(value)}: {count}")

    if diagnostics.records or diagnostics.invalid or diagnostics.omitted:
        lines.extend(["", "### Incomplete coverage", ""])
        for diagnostic in diagnostics.records:
            detail = f" — {diagnostic.detail}" if diagnostic.detail else ""
            lines.append(f"- {inline_code(diagnostic.path)} — {diagnostic.reason}{detail}")
        if diagnostics.invalid:
            lines.append(
                f"- {diagnostics.invalid} failed item(s) had no safe repository-relative path"
            )
        if diagnostics.omitted:
            lines.append(f"- ... and {diagnostics.omitted} more failed file record(s)")

    safe_warnings = []
    for warning in warnings[:10]:
        safe = compact_escaped_text(
            neutralize_quick_actions(redact_sensitive(ocr_warning_text(warning))), 500
        )
        if safe:
            safe_warnings.append(safe)
    if safe_warnings and not diagnostics.records:
        lines.extend(["", "### Review warnings", ""])
        lines.extend(f"- {warning}" for warning in safe_warnings)
        if len(warnings) > len(safe_warnings):
            lines.append(f"- ... and {len(warnings) - len(safe_warnings)} more warning(s)")

    return lines
