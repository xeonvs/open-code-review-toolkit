"""Bounded immutable-source proof for optional OCR code fields.

This module establishes source identity only. Publication still needs to check
the complete original text for sensitive content and prove its renderer safe.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True, slots=True)
class OpaqueCodeProof:
    """Only closed proof facts; no source text, hash, or rejected value."""

    existing_verified: bool = False
    suggestion_verified: bool = False


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
    lines = source.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if end > len(lines):
        return OpaqueCodeProof()
    selected = "\n".join(lines[start - 1 : end])
    if normalize_replacement(existing) != normalize_replacement(selected):
        return OpaqueCodeProof()

    if not suggestion or not suggestion_well_formed:
        return OpaqueCodeProof(existing_verified=True)
    # A no-op is source-proven too, but cannot smuggle an authored fence into
    # a fallback rendering path. Actionable replacements use the evaluator's
    # stricter shape checks.
    if "```" in suggestion:
        return OpaqueCodeProof(existing_verified=True)
    try:
        decision = evaluate_suggestion(comment, path, lambda _path: source)
    except (ValueError, TypeError):
        return OpaqueCodeProof(existing_verified=True)
    return OpaqueCodeProof(
        existing_verified=True,
        suggestion_verified=decision.state in {SuggestionState.ACTIONABLE, SuggestionState.NO_OP},
    )
