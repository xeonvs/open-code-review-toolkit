"""Independent normalization and closed DLP checks for context projections."""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
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
DLP_ENV_NAME = "OCR_DLP_ENABLED"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_DLP_ENABLED: ContextVar[bool] = ContextVar("ocr_dlp_enabled", default=True)


@dataclass(frozen=True, slots=True)
class DLPResult:
    """Return admitted normalized text or one closed failure reason."""

    admitted: bool
    text: str | None
    reason: str
    detector: str | None = None
    source_classes: tuple[str, ...] = ()


def resolve_dlp_enabled(environment: Mapping[str, str]) -> bool:
    """Resolve the public DLP switch once without exposing its raw value."""

    raw = environment.get(DLP_ENV_NAME, "").strip().lower()
    if not raw:
        return True
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise ValueError(f"{DLP_ENV_NAME} must be one of true/false, 1/0, yes/no, or on/off")


@contextmanager
def dlp_mode(enabled: bool) -> Iterator[None]:
    """Apply one already-resolved DLP mode to synchronous review boundaries."""

    token = _DLP_ENABLED.set(enabled)
    try:
        yield
    finally:
        _DLP_ENABLED.reset(token)


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


FORBIDDEN_SOURCE_CLASSES = frozenset(
    {
        "forge_discussions",
        "remediation_threads",
        "ci_outcomes",
        "external_context",
        "operator_secret",
        "other",
    }
)


@dataclass(frozen=True, slots=True)
class ForbiddenValue:
    """Attribute a private value when its owning source registers it."""

    value: str
    source_class: str

    def __post_init__(self) -> None:
        if self.source_class not in FORBIDDEN_SOURCE_CLASSES:
            raise ValueError("unknown forbidden source class")


@dataclass(frozen=True, slots=True)
class ForbiddenMatcher:
    """Compile protected values and their closed provenance once."""

    exact: tuple[str, ...]
    sources: tuple[frozenset[str], ...] = ()

    @classmethod
    def compile(cls, values: tuple[str | ForbiddenValue, ...]) -> ForbiddenMatcher:
        registered: dict[str, set[str]] = {}
        for item in values:
            value = item.value if isinstance(item, ForbiddenValue) else item
            source = item.source_class if isinstance(item, ForbiddenValue) else "other"
            candidate = normalize_text(value, allow_horizontal_tabs=True)
            if not candidate:
                continue
            for representation in (_display_normalize(candidate), _source_normalize(candidate)):
                if representation:
                    registered.setdefault(representation, set()).add(source)
        return cls(tuple(registered), tuple(frozenset(v) for v in registered.values()))

    def match_details(self, value: str) -> tuple[str | None, tuple[str, ...]]:
        """Return rejection and aggregate classes without retaining rejected content."""

        matched: set[str] = set()
        for normalized in {_display_normalize(value), _source_normalize(value)}:
            comparison_cost = max(1, len(normalized)) * sum(
                max(1, len(candidate)) for candidate in self.exact
            )
            if comparison_cost > MAX_EXCERPT_SEARCH_COST:
                return "limit", ()
            long_indices = tuple(
                i
                for i, candidate in enumerate(self.exact)
                if len(candidate) >= MIN_EXACT_EXCERPT_CHARS
            )
            windows = max(0, len(normalized) - MIN_EXACT_EXCERPT_CHARS + 1)
            if windows * sum(len(self.exact[i]) for i in long_indices) > MAX_EXCERPT_SEARCH_COST:
                return "limit", ()
            for i, candidate in enumerate(self.exact):
                found = candidate == normalized or candidate in normalized
                if not found and windows and len(candidate) >= MIN_EXACT_EXCERPT_CHARS:
                    found = normalized in candidate or any(
                        normalized[j : j + MIN_EXACT_EXCERPT_CHARS] in candidate
                        for j in range(windows)
                    )
                if found:
                    matched.update(self.sources[i] if self.sources else {"other"})
        return ("forbidden", tuple(sorted(matched))) if matched else (None, ())

    def match_reason(self, value: str) -> str | None:
        return self.match_details(value)[0]

    def matches(self, value: str) -> bool:
        return self.match_reason(value) is not None


def normalize_text(value: object, *, allow_horizontal_tabs: bool = False) -> str | None:
    """Normalize NFC/newlines and reject unsupported controls."""

    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    allowed_controls = "\n\t" if allow_horizontal_tabs else "\n"
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        and character not in allowed_controls
        for character in normalized
    ):
        return None
    return normalized.strip()


def check_text(
    value: object,
    *,
    budgets: TextBudgets,
    publication: bool = False,
    forbidden: tuple[str | ForbiddenValue, ...] = (),
    forbidden_matcher: ForbiddenMatcher | None = None,
    allow_horizontal_tabs: bool = False,
    enabled: bool | None = None,
) -> DLPResult:
    """Apply independent units, redaction, PII, and optional publication checks."""

    normalized = normalize_text(value, allow_horizontal_tabs=allow_horizontal_tabs)
    if normalized is None:
        return DLPResult(False, None, "invalid_text", "type_or_control")
    normalized_bytes = normalized.encode("utf-8")
    if (
        len(normalized) > budgets.max_chars
        or len(normalized_bytes) > budgets.max_bytes
        or normalized.count("\n") + 1 > budgets.max_lines
    ):
        detector = (
            "characters"
            if len(normalized) > budgets.max_chars
            else "bytes"
            if len(normalized_bytes) > budgets.max_bytes
            else "lines"
        )
        return DLPResult(False, None, "limit", detector)
    if not (_DLP_ENABLED.get() if enabled is None else enabled):
        return DLPResult(True, normalized, "disabled")
    redacted = redact_env_secret_values(redact_sensitive(normalized))
    if redacted != normalized:
        return DLPResult(False, None, "secret", "normalized")
    decoded = _html_decode(normalized) if publication else normalized
    displayed = _display_normalize(normalized) if publication else normalized
    source = _source_normalize(normalized) if publication else normalized
    if publication and redact_env_secret_values(redact_sensitive(displayed)) != displayed:
        return DLPResult(False, None, "secret", "displayed")
    if publication and redact_env_secret_values(redact_sensitive(source)) != source:
        return DLPResult(False, None, "secret", "source")
    pii_candidates = (("normalized", normalized),)
    if publication:
        pii_candidates += (("decoded", decoded), ("displayed", displayed), ("source", source))
    for representation, candidate in pii_candidates:
        if EMAIL_RE.search(candidate):
            return DLPResult(False, None, "pii", f"email:{representation}")
        if _contains_phone(candidate):
            return DLPResult(False, None, "pii", f"phone:{representation}")
    matcher = forbidden_matcher or ForbiddenMatcher.compile(forbidden)
    matcher_reason, source_classes = matcher.match_details(normalized)
    if matcher_reason:
        return DLPResult(False, None, matcher_reason, "forbidden_matcher", source_classes)
    if publication:
        laundering = (
            "markdown_destination"
            if MARKDOWN_DEST_RE.search(normalized)
            or MARKDOWN_DEST_RE.search(decoded)
            or MARKDOWN_DEST_RE.search(displayed)
            else "html_comment"
            if HTML_COMMENT_RE.search(decoded)
            else "html_tag"
            if HTML_TAG_RE.search(decoded)
            else "display_control"
            if any(_is_display_control(character) for character in decoded)
            else None
        )
        if laundering is not None:
            return DLPResult(False, None, "laundering", laundering)
    return DLPResult(True, normalized, "admitted")
