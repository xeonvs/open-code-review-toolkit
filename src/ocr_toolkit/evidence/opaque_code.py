"""Bounded immutable-source proof for optional OCR code fields.

This module establishes source identity only. Publication still needs to check
the complete original text for sensitive content and prove its renderer safe.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ocr_toolkit.context.code_text import CodeTextContext
from ocr_toolkit.evidence.source_syntax import (
    SourceSyntax,
    analyze_python_source,
)
from ocr_toolkit.posting.comments import line_number
from ocr_toolkit.posting.settings import (
    MAX_SUGGESTION_CODE_CHARS,
    MAX_SUGGESTION_SPAN_LINES,
)
from ocr_toolkit.posting.suggestions import (
    SuggestionState,
    evaluate_suggestion,
    normalize_replacement,
    safe_repository_path,
)

MAX_PROOF_SOURCE_CHARS = 256_000
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
    return _PreparedProofSource(
        source, tuple(source.replace("\r\n", "\n").replace("\r", "\n").splitlines())
    )


@dataclass(frozen=True, slots=True)
class OpaqueCodeProof:
    """Source facts and text-bound in-memory interpretation; never persisted."""

    existing_verified: bool = False
    suggestion_verified: bool = False
    existing_context: CodeTextContext | None = None
    suggestion_context: CodeTextContext | None = None


def _bounded_line(value: Any) -> int:
    """Parse an OCR line without admitting unbounded decimal conversion."""

    if isinstance(value, str) and len(value) > 12:
        return 0
    try:
        return line_number(value)
    except ValueError:
        return 0


def prove_opaque_code(
    comment: dict[str, Any],
    path: str,
    read_head_blob: Callable[[str], str | None],
    *,
    syntax_cache: SyntaxCache | None = None,
) -> OpaqueCodeProof:
    """Prove code against one exact, bounded range of the reviewed head.

    The caller owns the immutable commit binding of ``read_head_blob`` and the
    sink-specific rendering guarantee. A failed read or malformed model value
    returns only false proof facts, so it cannot open a publication exception.
    """

    existing = comment.get("existing_code")
    suggestion = comment.get("suggestion_code")
    if not isinstance(existing, str) or not existing:
        return OpaqueCodeProof()
    if len(existing) > MAX_SUGGESTION_CODE_CHARS:
        return OpaqueCodeProof()
    suggestion_well_formed = suggestion is None or (
        isinstance(suggestion, str) and len(suggestion) <= MAX_SUGGESTION_CODE_CHARS
    )
    if not isinstance(path, str) or len(path) > MAX_PROOF_PATH_CHARS:
        return OpaqueCodeProof()
    if not safe_repository_path(path):
        return OpaqueCodeProof()

    raw_start = comment.get("start_line")
    raw_end = comment.get("end_line")
    start = _bounded_line(comment.get("line") if raw_start is None else raw_start)
    end = _bounded_line(comment.get("line") if raw_end is None else raw_end)
    if start <= 0 or end < start or end - start > MAX_SUGGESTION_SPAN_LINES:
        return OpaqueCodeProof()

    try:
        source = read_head_blob(path)
    except Exception:  # External repository-reader failures must close the proof.
        return OpaqueCodeProof()
    if not isinstance(source, str) or len(source) > MAX_PROOF_SOURCE_CHARS:
        return OpaqueCodeProof()
    cached = syntax_cache.get(path) if syntax_cache is not None else None
    if cached is None or cached.source != source:
        cached = _prepare_source(source)
        if syntax_cache is not None:
            if path not in syntax_cache and len(syntax_cache) >= MAX_SYNTAX_CACHE_FILES:
                del syntax_cache[next(iter(syntax_cache))]
            syntax_cache[path] = cached
    lines = cached.lines
    if end > len(lines):
        return OpaqueCodeProof()
    selected = "\n".join(lines[start - 1 : end])
    if normalize_replacement(existing) != normalize_replacement(selected):
        return OpaqueCodeProof()

    context = None
    if not cached.analyzed:
        cached.syntax = analyze_python_source(source)
        cached.analyzed = True
    syntax = cached.syntax
    if syntax is not None:
        context = syntax.context(start, end, existing)

    if not suggestion or not suggestion_well_formed:
        return OpaqueCodeProof(existing_verified=True, existing_context=context)
    # A no-op is source-proven too, but cannot smuggle an authored fence into
    # a fallback rendering path. Actionable replacements use the evaluator's
    # stricter shape checks.
    if "```" in suggestion:
        return OpaqueCodeProof(existing_verified=True, existing_context=context)
    try:
        decision = evaluate_suggestion(comment, path, lambda _path: source)
    except (ValueError, TypeError):
        return OpaqueCodeProof(existing_verified=True, existing_context=context)
    return OpaqueCodeProof(
        existing_verified=True,
        suggestion_verified=decision.state in {SuggestionState.ACTIONABLE, SuggestionState.NO_OP},
        existing_context=context,
        suggestion_context=context if decision.state == SuggestionState.NO_OP else None,
    )
