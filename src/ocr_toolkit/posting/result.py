"""OCR result artifact loading and provider failure classification."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ocr_toolkit.common.redaction import sanitize_ocr_value
from ocr_toolkit.posting.comments import clean_text
from ocr_toolkit.posting.settings import max_result_bytes


class OcrResultMissing(Exception):
    """The OCR result artifact is missing or unreadable on disk."""


class OcrResultMalformed(Exception):
    """The OCR result artifact exists but is not valid JSON."""


class OcrResultTooLarge(Exception):
    """The OCR result artifact exceeds the configured safety limit."""


def load_ocr_result(path: Path) -> Any:
    """Load OCR JSON result from disk.

    Raises `OcrResultMissing` when the artifact is absent or
    unreadable, `OcrResultTooLarge` before reading a runaway artifact,
    and `OcrResultMalformed` when the contents are not valid JSON. The
    caller routes these failure modes differently: a missing artifact
    looks like an OCR crash, while an oversized or malformed artifact is
    a controlled OCR output contract violation.
    """

    try:
        size = path.stat().st_size
    except FileNotFoundError as exc:
        raise OcrResultMissing(str(exc)) from exc
    except OSError as exc:
        raise OcrResultMissing(str(exc)) from exc

    limit = max_result_bytes()
    if size > limit:
        raise OcrResultTooLarge(
            f"OCR result JSON is {size} bytes, above OCR_MAX_RESULT_BYTES={limit}"
        )

    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except FileNotFoundError as exc:
        raise OcrResultMissing(str(exc)) from exc
    except OSError as exc:
        raise OcrResultMissing(str(exc)) from exc
    if len(data) > limit:
        raise OcrResultTooLarge(f"OCR result JSON grew above OCR_MAX_RESULT_BYTES={limit}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OcrResultMalformed(str(exc)) from exc

    try:
        return sanitize_ocr_value(json.loads(text))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise OcrResultMalformed(str(exc)) from exc


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
