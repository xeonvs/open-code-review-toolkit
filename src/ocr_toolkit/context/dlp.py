"""Independent normalization and closed DLP checks for context projections."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

from ocr_toolkit.common.redaction import redact_env_secret_values, redact_sensitive
from ocr_toolkit.context.contracts import TextBudgets

EMAIL_RE = re.compile(
    r"(?i)(?<![\w.+-])[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}"
    r"@(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}(?![a-z0-9_-])"
)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?[1-9][\d .()/-]{7,24}\d)(?!\d)")
MARKDOWN_DEST_RE = re.compile(r"\]\(\s*(?:https?://|mailto:)", re.IGNORECASE)
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>\n]*>")
MARKDOWN_ESCAPE_RE = re.compile(r"\\([\\`*{}\[\]()#+\-.!_>~|])")
MARKDOWN_FORMAT_RE = re.compile(r"[`*_~]")
DISPLAY_WHITESPACE_RE = re.compile(r"\s+")
MIN_EXACT_EXCERPT_CHARS = 24
MAX_EXCERPT_SEARCH_COST = 50_000_000


@dataclass(frozen=True, slots=True)
class DLPResult:
    """Return admitted normalized text or one closed failure reason."""

    admitted: bool
    text: str | None
    reason: str


def _html_decode(value: str) -> str:
    """Decode the bounded entity layers a browser can display as text."""

    normalized = value
    for _iteration in range(2):
        decoded = html.unescape(normalized)
        if decoded == normalized:
            break
        normalized = decoded
    return normalized


def _is_display_control(character: str) -> bool:
    return bool(
        (unicodedata.category(character) in {"Cc", "Cf", "Cs"} and not character.isspace())
        or "\ufe00" <= character <= "\ufe0f"
        or "\U000e0100" <= character <= "\U000e01ef"
    )


def _display_normalize(value: str) -> str:
    """Approximate closed text rendered by common Markdown/HTML constructs."""

    normalized = _html_decode(value)
    normalized = HTML_COMMENT_RE.sub("", normalized)
    normalized = HTML_TAG_RE.sub("", normalized)
    normalized = MARKDOWN_ESCAPE_RE.sub(r"\1", normalized)
    normalized = MARKDOWN_FORMAT_RE.sub("", normalized)
    normalized = "".join(
        " " if character.isspace() else "" if _is_display_control(character) else character
        for character in normalized
    )
    normalized = unicodedata.normalize("NFKC", normalized).casefold()
    return DISPLAY_WHITESPACE_RE.sub(" ", normalized).strip()


@dataclass(frozen=True, slots=True)
class ForbiddenMatcher:
    """Compile non-publishable values once for bounded result-string checks."""

    exact: tuple[str, ...]

    @classmethod
    def compile(cls, values: tuple[str, ...]) -> ForbiddenMatcher:
        exact: list[str] = []
        for value in values:
            candidate = normalize_text(value)
            if not candidate:
                continue
            displayed = _display_normalize(candidate)
            if not displayed:
                continue
            exact.append(displayed)
        return cls(tuple(exact))

    def matches(self, value: str) -> bool:
        """Detect whole fields or conservative exact excerpts after display normalization."""

        displayed = _display_normalize(value)
        if any(candidate in displayed for candidate in self.exact):
            return True
        if len(displayed) < MIN_EXACT_EXCERPT_CHARS:
            return False
        candidates = tuple(
            candidate for candidate in self.exact if len(candidate) >= MIN_EXACT_EXCERPT_CHARS
        )
        if any(displayed in candidate for candidate in candidates):
            return True
        windows = len(displayed) - MIN_EXACT_EXCERPT_CHARS + 1
        if windows * sum(len(candidate) for candidate in candidates) > MAX_EXCERPT_SEARCH_COST:
            # The publication owner cannot prove non-disclosure inside its hard work bound.
            return True
        return any(
            displayed[index : index + MIN_EXACT_EXCERPT_CHARS] in candidate
            for index in range(windows)
            for candidate in candidates
        )


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
    forbidden_matcher: ForbiddenMatcher | None = None,
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
    displayed = _display_normalize(normalized) if publication else normalized
    if publication and redact_env_secret_values(redact_sensitive(displayed)) != displayed:
        return DLPResult(False, None, "secret")
    if (
        EMAIL_RE.search(normalized)
        or PHONE_RE.search(normalized)
        or (publication and (EMAIL_RE.search(displayed) or PHONE_RE.search(displayed)))
    ):
        return DLPResult(False, None, "pii")
    matcher = forbidden_matcher or ForbiddenMatcher.compile(forbidden)
    if matcher.matches(normalized):
        return DLPResult(False, None, "forbidden")
    if publication and (
        MARKDOWN_DEST_RE.search(normalized)
        or MARKDOWN_DEST_RE.search(displayed)
        or any(_is_display_control(character) for character in _html_decode(normalized))
    ):
        return DLPResult(False, None, "laundering")
    return DLPResult(True, normalized, "admitted")
