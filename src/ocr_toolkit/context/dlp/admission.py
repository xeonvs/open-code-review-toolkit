"""Independent normalization and closed DLP checks for context projections."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec

import regex

from ocr_toolkit.common.redaction import (
    environment_secret_values,
    has_sensitive_material,
    redact_env_secret_values,
)
from ocr_toolkit.context.code_text import CodeTextContext, TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp.credentials import credential_reference_view
from ocr_toolkit.context.dlp.decoding import _html_decode, _mermaid_decode, bounded_nfkc
from ocr_toolkit.context.dlp.email import contains_email
from ocr_toolkit.context.dlp.markup import (
    RepresentationLimit,
    interpret_markdown,
    strip_format_markers,
)
from ocr_toolkit.context.dlp.numeric import (
    _contains_phone,
    _contains_phone_segments,
    _explicit_contact_phone,
    phone_markup_view,
)
from ocr_toolkit.context.dlp.presentation import canonical_whitespace, has_unsafe_controls
from ocr_toolkit.result_contract import FORBIDDEN_SOURCE_CLASSES

MARKDOWN_DEST_RE = re.compile(
    r"(?:\]\(\s*<?(?:https?://|mailto:)|^\s*\[[^\]\n]+\]:\s*<?(?:https?://|mailto:)|"
    r"<(?:https?://|mailto:))",
    re.IGNORECASE | re.MULTILINE,
)
HTML_COMMENT_RE = regex.compile(r"<!--[\s\S]*?-->")
HTML_TAG_RE = regex.compile(r"</?[A-Za-z][^>\n]*>")
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


def _semantic_secret_text(value: str) -> str:
    """Remove proven no-value assignments only from generic secret classification."""

    return credential_reference_view(value)


def _display_normalize(value: str) -> str:
    """Approximate closed text rendered by common Markdown/HTML constructs."""

    normalized = bounded_nfkc(_html_decode(value), original=value)
    normalized = interpret_markdown(normalized).visible
    normalized = MARKDOWN_ESCAPE_RE.sub(r"\1", normalized)
    normalized = canonical_whitespace(normalized)
    normalized = bounded_nfkc(normalized, original=value, fold=True)
    return DISPLAY_WHITESPACE_RE.sub(" ", normalized).strip()


def _source_normalize(value: str) -> str:
    """Normalize publishable source without discarding hidden HTML source text."""

    normalized = bounded_nfkc(_html_decode(value), original=value)
    normalized = MARKDOWN_ESCAPE_RE.sub(r"\1", normalized)
    normalized = strip_format_markers(normalized)
    normalized = canonical_whitespace(normalized)
    normalized = bounded_nfkc(normalized, original=value, fold=True)
    return DISPLAY_WHITESPACE_RE.sub(" ", normalized).strip()


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
    limited: bool = False

    @classmethod
    def compile(cls, values: tuple[str | ForbiddenValue, ...]) -> ForbiddenMatcher:
        registered: dict[str, set[str]] = {}
        for item in values:
            value = item.value if isinstance(item, ForbiddenValue) else item
            source = item.source_class if isinstance(item, ForbiddenValue) else "other"
            candidate = normalize_text(value, allow_horizontal_tabs=True)
            if not candidate:
                continue
            try:
                representations = (_display_normalize(candidate), _source_normalize(candidate))
            except (RepresentationLimit, TimeoutError):
                return cls((), (), limited=True)
            for representation in representations:
                if representation:
                    registered.setdefault(representation, set()).add(source)
        return cls(tuple(registered), tuple(frozenset(v) for v in registered.values()))

    def match_details(self, value: str) -> tuple[str | None, tuple[str, ...]]:
        """Return rejection and aggregate classes without retaining rejected content."""

        if self.limited:
            return "limit", ()
        if not self.exact:
            return None, ()
        matched: set[str] = set()
        try:
            representations = {_display_normalize(value), _source_normalize(value)}
        except (RepresentationLimit, TimeoutError):
            return "limit", ()
        for normalized in representations:
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
    if has_unsafe_controls(normalized, allowed=allowed_controls):
        return None
    return normalized.strip()


def _literal_normalize(value: str) -> str:
    """Security canonicalization for a fixed literal sink, preserving operators."""

    normalized = _html_decode(value)
    normalized = canonical_whitespace(normalized)
    return DISPLAY_WHITESPACE_RE.sub(
        " ", bounded_nfkc(normalized, original=value, fold=True)
    ).strip()


def _literal_contact_view(value: str, *, visible: bool, formatting: bool = True) -> str:
    """Sweep arbitrary markup in the already source-bound contact view."""

    normalized = bounded_nfkc(_html_decode(value), original=value)
    normalized = phone_markup_view(normalized, formatting=False)
    if visible:
        # Preserve actual formatting boundaries for contact detection. An
        # unmatched multiplication star stays literal; paired emphasis cannot
        # join an obfuscated phone into an apparently bare identifier.
        return _literal_normalize(interpret_markdown(normalized).contacts)
    return _source_normalize(phone_markup_view(normalized, formatting=formatting))


_P = ParamSpec("_P")


def _bounded_check(function: Callable[_P, DLPResult]) -> Callable[_P, DLPResult]:
    @wraps(function)
    def guarded(*args: _P.args, **kwargs: _P.kwargs) -> DLPResult:
        try:
            return function(*args, **kwargs)
        except (RepresentationLimit, TimeoutError):
            return DLPResult(False, None, "limit", "representation")

    return guarded


@_bounded_check
def check_text(
    value: object,
    *,
    budgets: TextBudgets,
    publication: bool = False,
    forbidden: tuple[str | ForbiddenValue, ...] = (),
    forbidden_matcher: ForbiddenMatcher | None = None,
    allow_horizontal_tabs: bool = False,
    allow_opaque_code: bool = False,
    code_context: CodeTextContext | None = None,
    sink: TextSink = TextSink.PROSE,
    enabled: bool | None = None,
) -> DLPResult:
    """Check original values independently of proven source roles and sink syntax."""

    normalized = normalize_text(value, allow_horizontal_tabs=allow_horizontal_tabs)
    if normalized is None or not isinstance(sink, TextSink):
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
    # One immutable snapshot per admission; later admissions see current env again.
    secrets = environment_secret_values()
    if (
        isinstance(value, str) and redact_env_secret_values(value, values=secrets) != value
    ) or redact_env_secret_values(normalized, values=secrets) != normalized:
        return DLPResult(False, None, "secret", "normalized")
    credential = (
        code_context.credential_view(normalized)
        if code_context is not None and allow_opaque_code
        else normalized
    )
    semantic = _semantic_secret_text(credential)
    if has_sensitive_material(normalized, credential_view=semantic, values=secrets):
        return DLPResult(False, None, "secret", "normalized")
    compatible = bounded_nfkc(normalized)
    if compatible != normalized and has_sensitive_material(
        compatible, credential_view=bounded_nfkc(semantic), values=secrets
    ):
        return DLPResult(False, None, "secret", "compatible")
    literal = sink != TextSink.PROSE or allow_opaque_code
    display_transform = _literal_normalize if literal else _display_normalize
    source_transform = _literal_normalize if literal else _source_normalize
    decoded = _html_decode(normalized) if publication else normalized
    decoded_semantic = _semantic_secret_text(_html_decode(semantic)) if publication else semantic
    if (
        decoded.replace("\r\n", "\n").replace("\r", "\n").strip().count("\n") + 1
        > budgets.max_lines
    ):
        return DLPResult(False, None, "limit", "lines")
    displayed = display_transform(normalized) if publication else normalized
    source = source_transform(normalized) if publication else normalized
    views = []
    if publication:
        views.extend(
            (
                ("decoded", decoded, decoded_semantic),
                ("displayed", displayed, display_transform(decoded_semantic)),
                ("source", source, source_transform(decoded_semantic)),
            )
        )
    mermaid = _mermaid_decode(decoded)
    has_mermaid = mermaid != decoded
    if has_mermaid:
        mermaid_original = _html_decode(mermaid)
        mermaid = normalize_text(mermaid_original, allow_horizontal_tabs=allow_horizontal_tabs)
        if mermaid is None:
            return DLPResult(False, None, "invalid_text", "mermaid")
        if mermaid.count("\n") + 1 > budgets.max_lines:
            return DLPResult(False, None, "limit", "lines")
        if redact_env_secret_values(mermaid_original, values=secrets) != mermaid_original:
            return DLPResult(False, None, "secret", "mermaid")
        if publication and has_unsafe_controls(mermaid, display=True):
            return DLPResult(False, None, "laundering", "display_control")
        mermaid_semantic = _semantic_secret_text(_html_decode(_mermaid_decode(decoded_semantic)))
        views.append(("mermaid", mermaid, mermaid_semantic))
        if publication:
            views.extend(
                (
                    (
                        "mermaid_displayed",
                        display_transform(mermaid),
                        display_transform(mermaid_semantic),
                    ),
                    (
                        "mermaid_source",
                        source_transform(mermaid),
                        source_transform(mermaid_semantic),
                    ),
                )
            )
    security_views = []
    if publication and literal:
        literal_views = [("literal", normalized, semantic)]
        if has_mermaid:
            literal_views.append(("literal_mermaid", mermaid, mermaid_semantic))
        for name, candidate, secret_view in literal_views:
            security_views.extend(
                (
                    (
                        name + "_displayed",
                        _display_normalize(candidate),
                        _display_normalize(secret_view),
                    ),
                    (
                        name + "_source",
                        _source_normalize(candidate),
                        _source_normalize(secret_view),
                    ),
                )
            )
    seen_secrets = {(normalized, semantic)}
    for representation, candidate, secret_view in (*views, *security_views):
        if (candidate, secret_view) in seen_secrets:
            continue
        seen_secrets.add((candidate, secret_view))
        if has_sensitive_material(candidate, credential_view=secret_view, values=secrets):
            return DLPResult(False, None, "secret", representation)
    seen_pii: set[str] = set()
    for representation, candidate in (
        ("normalized", normalized),
        ("compatible", compatible),
        *((name, text) for name, text, _ in views),
    ):
        if candidate in seen_pii:
            continue
        seen_pii.add(candidate)
        if contains_email(candidate, markdown=not literal):
            return DLPResult(False, None, "pii", f"email:{representation}")
        # Arbitrary marker removal supports strong-contact deobfuscation, but
        # cannot invent a weak phone candidate from literal punctuation.
        phone_check = (
            _explicit_contact_phone
            if representation in {"source", "mermaid_source"}
            else _contains_phone
        )
        if phone_check(candidate) or (
            not literal
            and phone_check(
                _literal_normalize(
                    interpret_markdown(phone_markup_view(candidate, formatting=False)).contacts
                )
            )
        ):
            return DLPResult(False, None, "pii", f"phone:{representation}")
    # Secret/email deobfuscation remains independent of literal rendering.
    # Strong contact signals also retain the stricter arbitrary-format sweep.
    for representation, candidate, _secret_view in security_views:
        if contains_email(candidate):
            return DLPResult(False, None, "pii", f"email:{representation}")
        if _explicit_contact_phone(candidate):
            return DLPResult(False, None, "pii", f"phone:{representation}")
    if publication and literal:
        context = code_context if allow_opaque_code and sink != TextSink.DIAGRAM_LABEL else None
        phone_original = context.phone_view(normalized) if context is not None else normalized
        phone_views = (
            (phone_original, _html_decode(_mermaid_decode(_html_decode(phone_original))))
            if has_mermaid
            else (phone_original,)
        )
        for candidate in phone_views:
            # A marker can obscure the boundary of a complete contact fragment
            # (e.g. an unmatched underscore); never concatenate numeric sides.
            if _contains_phone_segments(candidate):
                return DLPResult(False, None, "pii", "phone:literal_markup")
            for visible in (True, False):
                phone_check = _contains_phone if visible else _explicit_contact_phone
                if phone_check(
                    _literal_contact_view(
                        candidate,
                        visible=visible,
                        formatting=not (allow_opaque_code and sink == TextSink.LITERAL_CODE),
                    )
                ):
                    return DLPResult(False, None, "pii", "phone:literal_markup")
    matcher = forbidden_matcher or ForbiddenMatcher.compile(forbidden)
    matcher_reason, source_classes = matcher.match_details(normalized)
    if has_mermaid:
        mermaid_reason, mermaid_sources = matcher.match_details(mermaid)
        matcher_reason = matcher_reason or mermaid_reason
        source_classes = tuple(sorted(set(source_classes) | set(mermaid_sources)))
    if matcher_reason:
        return DLPResult(False, None, matcher_reason, "forbidden_matcher", source_classes)
    if publication and not (allow_opaque_code and sink == TextSink.LITERAL_CODE):
        laundering = (
            "markdown_destination"
            if MARKDOWN_DEST_RE.search(normalized)
            or MARKDOWN_DEST_RE.search(decoded)
            or MARKDOWN_DEST_RE.search(displayed)
            else "html_comment"
            if HTML_COMMENT_RE.search(decoded, timeout=0.05)
            else "html_tag"
            if HTML_TAG_RE.search(decoded, timeout=0.05)
            and not (allow_opaque_code and decoded == normalized)
            else "display_control"
            if has_unsafe_controls(decoded, display=True)
            else None
        )
        if laundering is not None:
            return DLPResult(False, None, "laundering", laundering)
    return DLPResult(True, normalized, "admitted")
