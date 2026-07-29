"""OCR result artifact loading and provider failure classification."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from ocr_toolkit.ocr_result import (
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    load_ocr_result,
)
from ocr_toolkit.posting.comments import clean_text

__all__ = [
    "OcrResultMalformed",
    "OcrResultMissing",
    "OcrResultTooLarge",
    "load_ocr_result",
]

LLM_BILLING_FAILURE_RE = re.compile(
    r"(?i)\b("
    r"(?:http\s*)?status(?:[_\s]*code)?[\"']?\s*[:=]\s*[\"']?402|"
    r"code[\"']?\s*[:=]\s*[\"']?402|payment required|insufficient[_ -]?funds|insufficient user balance|"
    r"insufficient balance|insufficient[_ -]?quota|quota[_ -]?exceeded|"
    r"out of credits|credit balance"
    r")\b"
)


def ocr_warning_text(warning: Any) -> str:
    """Return warning text relevant for provider failure classification."""

    if isinstance(warning, dict):
        parts: list[str] = []
        for key in ("type", "message", "code", "status", "status_code", "detail"):
            text = clean_text(warning.get(key))
            if text:
                parts.append(f"{key}: {text}" if key in {"code", "status", "status_code"} else text)
        for key in ("error", "details"):
            nested = warning.get(key)
            if isinstance(nested, dict):
                text = ocr_warning_text(nested)
                if text:
                    parts.append(text)
            else:
                text = clean_text(nested)
                if text:
                    parts.append(text)
        return "\n".join(parts)[:4000]
    if isinstance(warning, list):
        return "\n".join(text for value in warning[:40] if (text := ocr_warning_text(value)))[:4000]
    return clean_text(warning)


def llm_billing_failure_warnings(warnings: Sequence[Any]) -> list[str]:
    """Return OCR warnings that indicate LLM provider billing/quota failure."""

    matches: list[str] = []
    for warning in warnings:
        text = ocr_warning_text(warning)
        if text and LLM_BILLING_FAILURE_RE.search(text):
            matches.append(text)
    return matches
