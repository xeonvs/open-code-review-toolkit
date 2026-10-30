"""Independent normalization and closed DLP checks for context projections."""

from __future__ import annotations

import html
import ipaddress
import re
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date

from ocr_toolkit.common.redaction import (
    SENSITIVE_NAMED_KEY_PATTERN,
    redact_env_secret_values,
    redact_sensitive,
)
from ocr_toolkit.context.contracts import TextBudgets

EMAIL_RE = re.compile(
    r"(?i)(?<![\w.+-])[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}"
    r"@(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}(?![a-z0-9_-])"
)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?[1-9][\d .()/-]{7,24}\d)(?!\w)")
PURE_CREDENTIAL_ASSIGNMENT_RE = re.compile(
    rf"(?im)^[ \t]*(?:(?P<key_quote>['\"]){SENSITIVE_NAMED_KEY_PATTERN}"
    rf"(?P=key_quote)|{SENSITIVE_NAMED_KEY_PATTERN})[ \t]*:[ \t]*"
    r"(?:(?P<quote>['\"])\{\{[ \t]*[A-Za-z_][A-Za-z0-9_]*[ \t]*\}\}(?P=quote)|"
    r"(?P<empty>\"\"|''))[ \t]*$"
)
ISO_DATE_RE = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
_MERMAID_ENTITY_RE = re.compile(r"(?<!&)#([0-9]+);")
_HTML_NUMERIC_ENTITY_RE = re.compile(r"&#([xX][0-9a-fA-F]+|[0-9]+);?")
_NETWORK_TOKEN_CHARS = frozenset("0123456789abcdefABCDEF:./")
_TECHNICAL_SEPARATOR = r"(?:[ \t]+|[ \t]*(?:[<>]=?|[=!]=|=|[≤≥≠])[ \t]*)"
VERSION_CONTEXT_RE = re.compile(
    rf"(?i)\b(?:version|release|build|pin){_TECHNICAL_SEPARATOR}(?:v)?$"
)
DATE_CONTEXT_RE = re.compile(
    rf"(?i)\b(?:date|dated|on|since|until|before|after|expires)"
    rf"(?:[ \t]+on)?{_TECHNICAL_SEPARATOR}$"
)
IP_CONTEXT_RE = re.compile(
    r"(?i)(?:\b|_)(?:ipv4|ip|cidr|subnet|address|host|loginhost|listen|allow|network)\b"
)
PHONE_CONTEXT_RE = re.compile(r"(?i)\b(?:call|phone|tel|contact)[ \t]*$")
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

    def bounded_number(match: re.Match[str]) -> str:
        number = match[1]
        hexadecimal = number[:1].lower() == "x"
        digits = (number[1:] if hexadecimal else number).lstrip("0") or "0"
        if len(digits) > (6 if hexadecimal else 7):
            return "&#1114112;"  # Let html.unescape apply its invalid-scalar mapping.
        return f"&#{'x' if hexadecimal else ''}{digits};"

    normalized = value
    for _iteration in range(2):
        # Preserve HTML's scalar/legacy mappings without an unbounded decimal
        # integer conversion or changing Python's process-wide integer limit.
        prepared = (
            _HTML_NUMERIC_ENTITY_RE.sub(bounded_number, normalized)
            if "&#" in normalized
            else normalized
        )
        decoded = html.unescape(prepared)
        if decoded == normalized:
            break
        normalized = decoded
    return normalized


def _mermaid_decode(value: str) -> str:
    """Decode one layer of the renderer's decimal entities without expansion."""

    def character(match: re.Match[str]) -> str:
        digits = match[1].lstrip("0") or "0"
        if len(digits) > 7:
            return match[0]
        code = int(digits)
        return chr(code) if code <= 0x10FFFF and not 0xD800 <= code <= 0xDFFF else match[0]

    return _MERMAID_ENTITY_RE.sub(character, value)


def _technical_decode(value: str) -> str:
    """Resolve bounded HTML/one-Mermaid/HTML context without recursive Mermaid."""

    return _html_decode(_mermaid_decode(_html_decode(value)))


def _is_display_control(character: str) -> bool:
    return bool(
        (unicodedata.category(character) in {"Cc", "Cf", "Cs"} and not character.isspace())
        or "\ufe00" <= character <= "\ufe0f"
        or "\U000e0100" <= character <= "\U000e01ef"
    )


def _contains_phone(value: str) -> bool:
    """Recognize formatted phone-like values without classifying bare identifiers."""

    return any(
        (
            match.group(0).startswith("+")
            or any(separator in match.group(0) for separator in " .()/-")
        )
        and not _technical_number(value, match)
        for match in PHONE_RE.finditer(value)
    )


def _network_number(value: str, start: int, end: int) -> bool:
    """Parse a complete bounded network, not a phone-regex-sized fragment."""

    candidate_start = start
    while start and end - start < 64 and value[start - 1] in _NETWORK_TOKEN_CHARS:
        start -= 1
    prefix = value[start:candidate_start]
    label_separator = False
    # Separate log labels such as IP: without splitting a genuine IPv6 prefix.
    if prefix.count(":") == 1:
        start += prefix.index(":") + 1
        label_separator = True
    elif value[start : start + 1] == ":" and start and value[start - 1].isalnum():
        start += 1
        label_separator = True
    while end < len(value) and end - start < 64 and value[end] in _NETWORK_TOKEN_CHARS:
        end += 1
    contact_prefix = value[max(0, start - 25) : start].rstrip(": \t")
    if PHONE_CONTEXT_RE.search(contact_prefix):
        return False
    left = value[start - 1] if start and not label_separator else ""
    for neighbor in (left, value[end : end + 1]):
        if neighbor and (neighbor.isalnum() or neighbor in "_:./%-"):
            return False
    token = value[start:end]
    if "/" not in token:
        return False
    if token.endswith("."):
        # Remove one prose period; dotted/word continuations still fail parsing.
        token = token[:-1]
    try:
        ipaddress.ip_network(token, strict=False)
    except ValueError:
        return False
    return True


def _decoded_network_number(before: str, candidate: str, after: str) -> bool:
    """Bind an encoded fragment to its complete parsed network, not another value."""

    # A 64-character token and contact prefix fit here even with decimal escapes.
    raw_before, raw_after = before[-1024:], after[:1024]
    if not any(marker in raw_before or marker in raw_after for marker in ("#", "&")):
        return False
    decoded_before = _technical_decode(raw_before)
    decoded_after = _technical_decode(raw_after)
    if decoded_before == raw_before and decoded_after == raw_after:
        return False
    start = len(decoded_before)
    return _network_number(
        decoded_before + candidate + decoded_after, start, start + len(candidate)
    )


def _technical_number(value: str, match: re.Match[str]) -> bool:
    """Exclude only bounded, parsed technical syntax from phone candidates."""

    candidate = match.group(0)
    if candidate.startswith("+") or candidate != candidate.strip():
        return False
    before, after = value[: match.start()], value[match.end() :]
    if PHONE_CONTEXT_RE.search(before[-24:]):
        return False
    network = "/" in candidate or re.match(r"/[+-]?[0-9]", after) is not None
    if network and _network_number(value, *match.span()):
        return True
    if _decoded_network_number(before, candidate, after):
        return True
    if network:
        return False
    if before.endswith((".", "/", "-")) or re.match(r"(?:[./-]\d)", after):
        return False
    try:
        if isinstance(ipaddress.ip_address(candidate), ipaddress.IPv4Address):
            if after.startswith(":"):
                port = re.match(r":(\d{1,5})\b", after)
                return bool(port and 1 <= int(port[1]) <= 65535)
            return bool(IP_CONTEXT_RE.search(before[-96:]))
    except ValueError:
        pass
    # Only the bounded technical prefix is decoded/normalized: other representations and
    # the complete unit still pass all secret, contact and laundering checks.
    technical_prefix = unicodedata.normalize("NFKC", _technical_decode(before[-64:]))
    if ISO_DATE_RE.fullmatch(candidate) and DATE_CONTEXT_RE.search(technical_prefix):
        try:
            date(int(candidate[:4]), int(candidate[5:7]), int(candidate[8:10]))
        except ValueError:
            return False
        return True
    if re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,3}", candidate):
        return bool(VERSION_CONTEXT_RE.search(technical_prefix))
    if re.fullmatch(r"\d+\.\d+", candidate):
        return bool(
            re.search(r"(?i)\bdecimal\([ \t]*['\"]$", technical_prefix)
            and (
                re.match(r"['\"][ \t]*\)", after)
                or re.match(r"['\"][ \t]*\)", _technical_decode(after[:64]))
            )
        )
    return False


def _semantic_secret_text(value: str) -> str:
    """Remove proven no-value assignments only from generic secret classification."""

    return PURE_CREDENTIAL_ASSIGNMENT_RE.sub("safe_reference_assignment", value)


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
    allow_opaque_code: bool = False,
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
    # Exact environment values retain priority even when they resemble a reference.
    if redact_env_secret_values(normalized) != normalized:
        return DLPResult(False, None, "secret", "normalized")
    semantic = _semantic_secret_text(normalized)
    if redact_sensitive(semantic) != semantic:
        return DLPResult(False, None, "secret", "normalized")
    decoded = _html_decode(normalized) if publication else normalized
    decoded_lines = decoded.replace("\r\n", "\n").replace("\r", "\n").strip().count("\n") + 1
    if decoded_lines > budgets.max_lines:
        return DLPResult(False, None, "limit", "lines")
    displayed = _display_normalize(normalized) if publication else normalized
    source = _source_normalize(normalized) if publication else normalized
    # Check decoded keys before Markdown normalization can remove underscores
    # from credential names. Preserve the exact empty/template grammar at this
    # representation too; decoding alone does not make a value sensitive.
    decoded_semantic = _semantic_secret_text(decoded) if publication else semantic
    if publication and (
        redact_env_secret_values(decoded) != decoded
        or redact_sensitive(decoded_semantic) != decoded_semantic
    ):
        return DLPResult(False, None, "secret", "decoded")
    semantic_displayed = _display_normalize(decoded_semantic) if publication else semantic
    semantic_source = _source_normalize(decoded_semantic) if publication else semantic
    if publication and (
        redact_env_secret_values(displayed) != displayed
        or redact_sensitive(semantic_displayed) != semantic_displayed
    ):
        return DLPResult(False, None, "secret", "displayed")
    if publication and (
        redact_env_secret_values(source) != source
        or redact_sensitive(semantic_source) != semantic_source
    ):
        return DLPResult(False, None, "secret", "source")
    # A technical-number exception must not hide another value encoded with the
    # renderer's decimal syntax. Inspect the complete additional representation,
    # preserving the original unit and its existing checks/output.
    mermaid = _mermaid_decode(decoded)
    mermaid_views: tuple[tuple[str, str, str], ...] = ()
    if mermaid != decoded:
        mermaid = _html_decode(mermaid)
        checked_mermaid = normalize_text(mermaid, allow_horizontal_tabs=allow_horizontal_tabs)
        if checked_mermaid is None:
            return DLPResult(False, None, "invalid_text", "mermaid")
        mermaid = checked_mermaid
        if mermaid.count("\n") + 1 > budgets.max_lines:
            return DLPResult(False, None, "limit", "lines")
        if publication and any(_is_display_control(character) for character in mermaid):
            return DLPResult(False, None, "laundering", "display_control")
        semantic_mermaid = _semantic_secret_text(mermaid)
        mermaid_views = (("mermaid", mermaid, semantic_mermaid),)
        if publication:
            mermaid_views += (
                (
                    "mermaid_displayed",
                    _display_normalize(mermaid),
                    _display_normalize(semantic_mermaid),
                ),
                ("mermaid_source", _source_normalize(mermaid), _source_normalize(semantic_mermaid)),
            )
        for representation, candidate, secret_view in mermaid_views:
            if (
                redact_env_secret_values(candidate) != candidate
                or redact_sensitive(secret_view) != secret_view
            ):
                return DLPResult(False, None, "secret", representation)
    pii_candidates = (("normalized", normalized),)
    if publication:
        pii_candidates += (("decoded", decoded), ("displayed", displayed), ("source", source))
    pii_candidates += tuple((name, candidate) for name, candidate, _semantic in mermaid_views)
    for representation, candidate in pii_candidates:
        if EMAIL_RE.search(candidate):
            return DLPResult(False, None, "pii", f"email:{representation}")
        if _contains_phone(candidate):
            return DLPResult(False, None, "pii", f"phone:{representation}")
    matcher = forbidden_matcher or ForbiddenMatcher.compile(forbidden)
    matcher_reason, source_classes = matcher.match_details(normalized)
    if mermaid_views:
        mermaid_reason, mermaid_sources = matcher.match_details(mermaid)
        matcher_reason = matcher_reason or mermaid_reason
        source_classes = tuple(sorted(set(source_classes) | set(mermaid_sources)))
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
            if HTML_TAG_RE.search(decoded) and not (allow_opaque_code and decoded == normalized)
            else "display_control"
            if any(_is_display_control(character) for character in decoded)
            else None
        )
        if laundering is not None:
            return DLPResult(False, None, "laundering", laundering)
    return DLPResult(True, normalized, "admitted")
