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
PHONE_RE = re.compile(r"(?<!\w)(?:\+?[1-9][\d .()/-]{7,24}\d)(?!\w)")
MARKDOWN_DEST_RE = re.compile(
    r"(?:\]\(\s*<?(?:https?://|mailto:)|^\s*\[[^\]\n]+\]:\s*<?(?:https?://|mailto:)|"
    r"<(?:https?://|mailto:))",
    re.IGNORECASE | re.MULTILINE,
)
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


def _contains_phone(value: str) -> bool:
    """Recognize formatted phone-like values without classifying bare identifiers."""

    return any(
        match.group(0).startswith("+") or any(separator in match.group(0) for separator in " .()/-")
        for match in PHONE_RE.finditer(value)
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


def _source_normalize(value: str) -> str:
    """Normalize publishable source without discarding hidden HTML source text."""

    normalized = _html_decode(value)
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
        seen: set[str] = set()
        for value in values:
            candidate = normalize_text(value)
            if not candidate:
                continue
            for representation in (_display_normalize(candidate), _source_normalize(candidate)):
                if representation and representation not in seen:
                    seen.add(representation)
                    exact.append(representation)
        return cls(tuple(exact))

    def match_reason(self, value: str) -> str | None:
        """Return a closed exact-match or work-bound failure reason."""

        for normalized in {_display_normalize(value), _source_normalize(value)}:
            if any(candidate == normalized for candidate in self.exact):
                return "forbidden"
            comparison_cost = max(1, len(normalized)) * sum(
                max(1, len(candidate)) for candidate in self.exact
            )
            if comparison_cost > MAX_EXCERPT_SEARCH_COST:
                # Bound every containment direction, not only the sliding-window phase.
                return "limit"
            if any(candidate in normalized for candidate in self.exact):
                return "forbidden"
            if len(normalized) < MIN_EXACT_EXCERPT_CHARS:
                continue
            candidates = tuple(
                candidate for candidate in self.exact if len(candidate) >= MIN_EXACT_EXCERPT_CHARS
            )
            if any(normalized in candidate for candidate in candidates):
                return "forbidden"
            windows = len(normalized) - MIN_EXACT_EXCERPT_CHARS + 1
            if windows * sum(len(candidate) for candidate in candidates) > MAX_EXCERPT_SEARCH_COST:
                # The publication owner cannot prove non-disclosure inside its hard work bound.
                return "limit"
            if any(
                normalized[index : index + MIN_EXACT_EXCERPT_CHARS] in candidate
                for index in range(windows)
                for candidate in candidates
            ):
                return "forbidden"
        return None

    def matches(self, value: str) -> bool:
        """Return whether exact disclosure or work uncertainty blocks the value."""

        return self.match_reason(value) is not None


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
    decoded = _html_decode(normalized) if publication else normalized
    displayed = _display_normalize(normalized) if publication else normalized
    source = _source_normalize(normalized) if publication else normalized
    if publication and redact_env_secret_values(redact_sensitive(displayed)) != displayed:
        return DLPResult(False, None, "secret")
    if publication and redact_env_secret_values(redact_sensitive(source)) != source:
        return DLPResult(False, None, "secret")
    if (
        EMAIL_RE.search(normalized)
        or _contains_phone(normalized)
        or (
            publication
            and (
                EMAIL_RE.search(decoded)
                or _contains_phone(decoded)
                or EMAIL_RE.search(displayed)
                or _contains_phone(displayed)
                or EMAIL_RE.search(source)
                or _contains_phone(source)
            )
        )
    ):
        return DLPResult(False, None, "pii")
    matcher = forbidden_matcher or ForbiddenMatcher.compile(forbidden)
    if matcher_reason := matcher.match_reason(normalized):
        return DLPResult(False, None, matcher_reason)
    if publication and (
        MARKDOWN_DEST_RE.search(normalized)
        or MARKDOWN_DEST_RE.search(decoded)
        or MARKDOWN_DEST_RE.search(displayed)
        or HTML_COMMENT_RE.search(decoded)
        or HTML_TAG_RE.search(decoded)
        or any(_is_display_control(character) for character in decoded)
    ):
        return DLPResult(False, None, "laundering")
    return DLPResult(True, normalized, "admitted")
