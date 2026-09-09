"""Closed finding metadata and token presentation shared by all adapters."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.ocr_result import OcrToolkitAdvisory
from ocr_toolkit.reporting.text import clean_text
from ocr_toolkit.result_usage import normalize_token_usage

OCR_FINDING_SEVERITY_ORDER = ("critical", "high", "medium", "low")
OCR_FINDING_CATEGORY_ORDER = (
    "security",
    "bug",
    "performance",
    "maintainability",
    "test",
    "documentation",
    "style",
    "other",
)
OCR_FINDING_SEVERITIES = set(OCR_FINDING_SEVERITY_ORDER)
OCR_FINDING_CATEGORIES = set(OCR_FINDING_CATEGORY_ORDER)


def normalized_ocr_metadata(value: Any, allowed_values: set[str]) -> str:
    """Return a whitelisted OCR metadata value suitable for display."""

    text = clean_text(value).casefold()
    return text if text in allowed_values else ""


def finding_metadata(comment: dict[str, Any]) -> tuple[str, str]:
    """Return structured OCR category/severity metadata from a finding."""

    severity = normalized_ocr_metadata(
        comment.get("severity"), OCR_FINDING_SEVERITIES
    ) or normalized_ocr_metadata(comment.get("priority"), OCR_FINDING_SEVERITIES)
    category = normalized_ocr_metadata(comment.get("category"), OCR_FINDING_CATEGORIES)
    return severity, category


def format_token_usage_summary(result: dict[str, Any]) -> str:
    """Return one bounded summary line for structured OCR token usage."""

    usage = normalize_token_usage(result)
    if usage is None:
        return ""

    total = usage.get("total")
    details: list[str] = []
    for bucket in ("input", "output", "cached", "reasoning", "other"):
        if (count := usage.get(bucket)) is not None and count > 0:
            details.append(f"{bucket}: {count}")

    if total is None:
        return f"- token usage: {', '.join(details)}" if details else ""
    line = f"- token usage: {total} total"
    if details:
        line += f" ({', '.join(details)})"
    return line


def format_ocr_core_advisory(advisory: OcrToolkitAdvisory | None) -> str:
    """Render one validated numeric OCR advisory for Technical details only."""

    if advisory is None:
        return ""
    return (
        f"- OCR core advisory: background {advisory.actual} characters; recommended "
        f"{advisory.recommended} characters; accepted by OCR core"
    )


SEVERITY_EMOJI = {
    "critical": "❌",
    "high": "🚨",
    "medium": "⚠️",
    "low": "ℹ️",  # noqa: RUF001 - intentional information emoji
}
CATEGORY_EMOJI = {
    "bug": "🐛",
    "security": "🔒",
    "performance": "⚡",
    "maintainability": "🛠️",
    "test": "🧪",
    "style": "🎨",
    "documentation": "📚",
    "other": "📌",
}
