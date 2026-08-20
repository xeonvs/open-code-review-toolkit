"""Independent normalization and closed DLP checks for context projections."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ocr_toolkit.common.redaction import redact_env_secret_values, redact_sensitive
from ocr_toolkit.context.contracts import TextBudgets

EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])[\w.+-]{1,64}@[a-z0-9.-]{1,190}\.[a-z]{2,63}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?[1-9][\d .()/-]{7,24}\d)(?!\d)")
MARKDOWN_DEST_RE = re.compile(r"\]\(\s*(?:https?://|mailto:)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DLPResult:
    """Return admitted normalized text or one closed failure reason."""

    admitted: bool
    text: str | None
    reason: str


def normalize_text(value: object) -> str | None:
    """Normalize NFC/newlines and reject unsupported controls."""

    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"} and character != "\n"
        for character in normalized
    ):
        return None
    return normalized.strip()


def check_text(
    value: object,
    *,
    budgets: TextBudgets,
    publication: bool = False,
    forbidden: tuple[str, ...] = (),
) -> DLPResult:
    """Apply independent units, redaction, PII, and optional publication checks."""

    normalized = normalize_text(value)
    if normalized is None:
        return DLPResult(False, None, "invalid_text")
    if (
        len(normalized) > budgets.max_chars
        or len(normalized.encode("utf-8")) > budgets.max_bytes
        or normalized.count("\n") + 1 > budgets.max_lines
    ):
        return DLPResult(False, None, "limit")
    redacted = redact_env_secret_values(redact_sensitive(normalized))
    if redacted != normalized:
        return DLPResult(False, None, "secret")
    if EMAIL_RE.search(normalized) or PHONE_RE.search(normalized):
        return DLPResult(False, None, "pii")
    folded = unicodedata.normalize("NFKC", normalized).casefold()
    for value in forbidden:
        candidate = normalize_text(value)
        if candidate and unicodedata.normalize("NFKC", candidate).casefold() in folded:
            return DLPResult(False, None, "forbidden")
    if publication and (MARKDOWN_DEST_RE.search(normalized) or "\u202e" in normalized):
        return DLPResult(False, None, "laundering")
    return DLPResult(True, normalized, "admitted")
