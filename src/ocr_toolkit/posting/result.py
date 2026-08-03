"""OCR result artifact loading and provider failure classification."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from ocr_toolkit.common.markdown import neutralize_quick_actions
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.ocr_result import (
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    load_ocr_result,
)
from ocr_toolkit.posting.comments import clean_text, compact_escaped_text
from ocr_toolkit.result_contract import ReviewOutcome

__all__ = [
    "OcrResultMalformed",
    "OcrResultMissing",
    "OcrResultTooLarge",
    "llm_billing_failure_warnings",
    "load_ocr_result",
    "normalize_coverage_diagnostics",
    "ocr_warning_text",
]

LLM_BILLING_FAILURE_RE = re.compile(
    r"(?i)\b("
    r"(?:http\s*)?status(?:[_\s]*code)?[\"']?\s*[:=]\s*[\"']?402|"
    r"code[\"']?\s*[:=]\s*[\"']?402|payment required|insufficient[_ -]?funds|insufficient user balance|"
    r"insufficient balance|insufficient[_ -]?quota|quota[_ -]?exceeded|"
    r"out of credits|credit balance"
    r")\b"
)

MAX_COVERAGE_DIAGNOSTICS = 10
MAX_COVERAGE_DETAIL_CHARS = 240
FAILURE_REASON_LABELS = {
    "timeout": "review timed out",
    "provider": "provider request failed",
    "cancelled": "review cancelled",
    "configuration": "configuration failed",
    "input": "input could not be reviewed",
    "budget": "token limit reached",
    "panic": "unknown subtask failure",
    "unknown": "unknown subtask failure",
}


@dataclass(frozen=True, slots=True)
class CoverageDiagnostic:
    """Hold one safe actionable failed-file receipt."""

    path: str
    reason: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CoverageDiagnostics:
    """Hold bounded diagnostics and explicit information loss counters."""

    records: tuple[CoverageDiagnostic, ...]
    omitted: int
    invalid: int
    failed_total: int
    unique_file_count: int

    @property
    def file_count(self) -> int | None:
        """Return a safe unique-file count only when every failure has a path."""

        return self.unique_file_count if self.unique_file_count > 0 and self.invalid == 0 else None


def _safe_repository_path(value: object) -> str:
    """Return one normalized repository-relative path or an empty value."""

    if not isinstance(value, str) or not value or len(value) > 1_024 or "\\" in value:
        return ""
    parts = value.split("/")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        return ""
    if any(character == "\x7f" or ord(character) < 32 for character in value):
        return ""
    return path.as_posix()


def _legacy_reason(warning: Any) -> str:
    """Map legacy warning shapes into a closed reviewer-facing vocabulary."""

    warning_type = clean_text(warning.get("type")) if isinstance(warning, dict) else ""
    text = f"{warning_type}\n{ocr_warning_text(warning)}".casefold()
    if "timeout" in text or "timed out" in text:
        return "review timed out"
    if "budget" in text or "token limit" in text:
        return "token limit reached"
    if "provider" in text or "request" in text:
        return "provider request failed"
    if "tool" in text and "loop" in text:
        return "tool loop failed"
    if "parse" in text or "invalid result" in text:
        return "result could not be parsed"
    return "unknown subtask failure"


def _safe_detail(value: object, reason: str) -> str:
    """Return optional redacted Markdown-neutral detail within a small budget."""

    text = compact_escaped_text(
        neutralize_quick_actions(redact_sensitive(clean_text(value))),
        MAX_COVERAGE_DETAIL_CHARS,
    )
    return "" if not text or text.casefold() == reason.casefold() else text


def normalize_coverage_diagnostics(
    outcome: ReviewOutcome, warnings: Sequence[Any]
) -> CoverageDiagnostics:
    """Normalize manifest failures or legacy warnings once at the posting boundary."""

    candidates: list[tuple[object, str, object]] = []
    if outcome.manifest_present:
        candidates.extend(
            (
                item.path,
                FAILURE_REASON_LABELS.get(item.classification, "unknown subtask failure"),
                item.reason,
            )
            for item in outcome.failed_items
        )
    elif outcome.kind == "partial":
        for warning in warnings:
            path = warning.get("file") or warning.get("path") if isinstance(warning, dict) else None
            candidates.append((path, _legacy_reason(warning), ocr_warning_text(warning)))

    records: list[CoverageDiagnostic] = []
    seen: set[tuple[str, str]] = set()
    invalid = 0
    for raw_path, reason, raw_detail in candidates:
        path = _safe_repository_path(raw_path)
        if not path:
            invalid += 1
            continue
        key = (path, reason)
        if key in seen:
            continue
        seen.add(key)
        records.append(CoverageDiagnostic(path, reason, _safe_detail(raw_detail, reason)))
    records.sort(key=lambda item: (item.path, item.reason, item.detail))
    omitted = max(0, len(records) - MAX_COVERAGE_DIAGNOSTICS)
    unique_file_count = len({record.path for record in records})
    return CoverageDiagnostics(
        records=tuple(records[:MAX_COVERAGE_DIAGNOSTICS]),
        omitted=omitted,
        invalid=invalid,
        failed_total=len(seen) + invalid,
        unique_file_count=unique_file_count,
    )


def ocr_warning_text(warning: Any, *, _seen: set[int] | None = None) -> str:
    """Return warning text relevant for provider failure classification."""

    if _seen is None:
        _seen = set()
    if isinstance(warning, (dict, list)):
        marker = id(warning)
        if marker in _seen:
            return ""
        _seen.add(marker)
    if isinstance(warning, dict):
        parts: list[str] = []
        for key in ("type", "message", "code", "status", "status_code", "detail"):
            text = clean_text(warning.get(key))
            if text:
                parts.append(f"{key}: {text}" if key in {"code", "status", "status_code"} else text)
        for key in ("error", "details"):
            nested = warning.get(key)
            if isinstance(nested, dict):
                text = ocr_warning_text(nested, _seen=_seen)
                if text:
                    parts.append(text)
            else:
                text = clean_text(nested)
                if text:
                    parts.append(text)
        return "\n".join(parts)[:4000]
    if isinstance(warning, list):
        return "\n".join(
            text for value in warning[:40] if (text := ocr_warning_text(value, _seen=_seen))
        )[:4000]
    return clean_text(warning)


def llm_billing_failure_warnings(warnings: Sequence[Any]) -> list[str]:
    """Return OCR warnings that indicate LLM provider billing/quota failure."""

    matches: list[str] = []
    for warning in warnings:
        text = ocr_warning_text(warning)
        if text and LLM_BILLING_FAILURE_RE.search(text):
            matches.append(text)
    return matches
