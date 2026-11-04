"""Bounded immutable-source proof for optional OCR code fields.

This module establishes source identity only. Publication still needs to check
the complete original text for sensitive content and prove its renderer safe.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from ocr_toolkit.context.code_text import CodeTextContext
from ocr_toolkit.evidence.source_syntax import (
    SourceSyntax,
    analyze_python_source,
)
from ocr_toolkit.evidence.text_contracts import (
    MAX_SYNTAX_CHARS,
    RepositoryTextExcerpt,
    SourceReadReason,
    SourceReadResult,
    source_lines,
)
from ocr_toolkit.posting.settings import (
    MAX_SUGGESTION_CODE_CHARS,
    MAX_SUGGESTION_SPAN_LINES,
)
from ocr_toolkit.posting.suggestions import (
    SuggestionState,
    bounded_source_range,
    evaluate_suggestion,
    normalize_replacement,
    safe_repository_path,
)

MAX_PROOF_SOURCE_CHARS = MAX_SYNTAX_CHARS
MAX_PROOF_PATH_CHARS = 1_024
MAX_SYNTAX_CACHE_FILES = 4


@dataclass(slots=True)
class _PreparedProofSource:
    source: str = field(repr=False)
    lines: tuple[str, ...] = field(repr=False)
    syntax: SourceSyntax | None = None
    analyzed: bool = False


SyntaxCache = dict[str, _PreparedProofSource]


def _prepare_source(source: str) -> _PreparedProofSource:
    return _PreparedProofSource(source, source_lines(source))


@dataclass(frozen=True, slots=True)
class OpaqueCodeProof:
    """Source facts and text-bound in-memory interpretation; never persisted."""

    existing_verified: bool = False
    suggestion_verified: bool = False
    existing_context: CodeTextContext | None = None
    suggestion_context: CodeTextContext | None = None
    source_reason: (
        SourceReadReason
        | Literal[
            "verified",
            "not-requested",
            "invalid-request",
            "excerpt-limit",
            "line-mismatch",
            "excerpt-unavailable",
        ]
    ) = field(default="not-requested", compare=False)
    syntax_reason: Literal[
        "not-requested", "qualified", "not-qualified", "source-limit", "not-retained"
    ] = field(default="not-requested", compare=False)


def code_source_request(comment: dict[str, Any], path: str) -> tuple[int, int] | None:
    """Select a bounded immutable-source request without performing I/O."""

    existing = comment.get("existing_code")
    if not isinstance(existing, str) or not existing or len(existing) > MAX_SUGGESTION_CODE_CHARS:
        return None
    if (
        not isinstance(path, str)
        or len(path) > MAX_PROOF_PATH_CHARS
        or not safe_repository_path(path)
    ):
        return None
    span = bounded_source_range(comment)
    if span is None or span[1] - span[0] > MAX_SUGGESTION_SPAN_LINES:
        return None
    return span


def _cached_source(source: str, path: str, cache: SyntaxCache | None) -> _PreparedProofSource:
    cached = cache.get(path) if cache is not None else None
    if cached is None or cached.source != source:
        cached = _prepare_source(source)
        if cache is not None:
            if path not in cache and len(cache) >= MAX_SYNTAX_CACHE_FILES:
                del cache[next(iter(cache))]
            cache[path] = cached
    return cached


def prove_opaque_code(
    comment: dict[str, Any],
    path: str,
    read_head_blob: Callable[[str], str | None] | None = None,
    *,
    read_head_excerpt: Callable[[str, int, int], SourceReadResult] | None = None,
    syntax_cache: SyntaxCache | None = None,
) -> OpaqueCodeProof:
    """Prove exact source identity separately from optional full-source syntax.

    The caller binds either reader to the immutable source. Captured fragments
    never become a synthetic full source for syntax analysis. Missing, malformed
    or failed reads cannot open a publication exception.
    """

    existing = comment.get("existing_code")
    request = code_source_request(comment, path)
    if request is None:
        if existing is None or existing == "":
            return OpaqueCodeProof()
        return OpaqueCodeProof(
            source_reason=(
                "excerpt-limit"
                if isinstance(existing, str) and len(existing) > MAX_SUGGESTION_CODE_CHARS
                else "invalid-request"
            )
        )
    assert isinstance(existing, str)
    start, end = request
    cache_key = path
    source: str | None
    syntax_reason: Literal[
        "not-requested", "qualified", "not-qualified", "source-limit", "not-retained"
    ]
    if read_head_excerpt is not None:
        try:
            result = read_head_excerpt(path, start, end)
            metadata = result.metadata
            if metadata is None:
                return OpaqueCodeProof(
                    source_reason=result.reason if result.reason != "none" else "unavailable"
                )
            if type(metadata.line_count) is not int or end > metadata.line_count:
                return OpaqueCodeProof(source_reason="line-mismatch")
            cache_key = metadata.object_sha
            piece = next(
                (item for item in metadata.excerpts if (item.start_line, item.end_line) == request),
                None,
            )
            if piece is None:
                return OpaqueCodeProof(source_reason="excerpt-unavailable")
            if piece.text is None:
                return OpaqueCodeProof(
                    source_reason="excerpt-limit" if piece.reason == "limit" else "line-mismatch"
                )
            if not isinstance(piece.text, str):
                return OpaqueCodeProof(source_reason="unavailable")
            selected, total_lines = piece.text, metadata.line_count
            source = result.syntax_source
            if source is not None and not isinstance(source, str):
                return OpaqueCodeProof(source_reason="unavailable")
            syntax_reason = "source-limit" if result.syntax_limited else "not-retained"
        except Exception:
            return OpaqueCodeProof(source_reason="unavailable")
        if source is not None and len(source) > MAX_PROOF_SOURCE_CHARS:
            source, syntax_reason = None, "source-limit"
    else:
        try:
            source = read_head_blob(path) if read_head_blob is not None else None
        except Exception:
            return OpaqueCodeProof(source_reason="unavailable")
        if not isinstance(source, str):
            return OpaqueCodeProof(source_reason="missing-source")
        if len(source) > MAX_PROOF_SOURCE_CHARS:
            return OpaqueCodeProof(source_reason="source-limit")
        cached = _cached_source(source, cache_key, syntax_cache)
        total_lines = len(cached.lines)
        if end > total_lines:
            return OpaqueCodeProof(source_reason="line-mismatch")
        selected = "\n".join(cached.lines[start - 1 : end])
        syntax_reason = "not-qualified"
    if normalize_replacement(existing) != normalize_replacement(selected):
        return OpaqueCodeProof(source_reason="line-mismatch")

    context = None
    if source is not None:
        cached = _cached_source(source, cache_key, syntax_cache)
        if not cached.analyzed:
            cached.syntax = analyze_python_source(source)
            cached.analyzed = True
        syntax = cached.syntax
        if syntax is not None:
            context = syntax.context(start, end, existing)
        syntax_reason = "qualified" if context is not None else "not-qualified"
    proof = OpaqueCodeProof(
        existing_verified=True,
        existing_context=context,
        source_reason="verified",
        syntax_reason=syntax_reason,
    )
    suggestion = comment.get("suggestion_code")
    if (
        not isinstance(suggestion, str)
        or not suggestion
        or len(suggestion) > MAX_SUGGESTION_CODE_CHARS
        or "```" in suggestion
    ):
        return proof
    try:
        decision = evaluate_suggestion(
            comment,
            path,
            excerpt=RepositoryTextExcerpt(start, end, selected),
            source_line_count=total_lines,
        )
    except (ValueError, TypeError):
        return proof
    return replace(
        proof,
        suggestion_verified=decision.state in {SuggestionState.ACTIONABLE, SuggestionState.NO_OP},
        suggestion_context=context if decision.state == SuggestionState.NO_OP else None,
    )
