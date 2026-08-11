"""Validate OCR replacements before rendering actionable GitLab suggestions."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any

from ocr_toolkit.posting.comments import line_number
from ocr_toolkit.posting.settings import (
    MAX_SUGGESTION_CODE_CHARS,
    MAX_SUGGESTION_SPAN_LINES,
)


class SuggestionState(str, Enum):
    """Closed rendering states for an OCR-provided replacement."""

    ABSENT = "absent"
    ACTIONABLE = "actionable"
    NO_OP = "no_op"
    OMITTED = "omitted"


class SuggestionOmission(str, Enum):
    """Non-sensitive reasons why an actionable suggestion was withheld."""

    INVALID_PATH = "invalid_path"
    INVALID_RANGE = "invalid_range"
    RANGE_TOO_LARGE = "range_too_large"
    SOURCE_UNAVAILABLE = "source_unavailable"
    RANGE_OUT_OF_BOUNDS = "range_out_of_bounds"
    MISSING_EXISTING_CODE = "missing_existing_code"
    EXISTING_CODE_MISMATCH = "existing_code_mismatch"
    MALFORMED_REPLACEMENT = "malformed_replacement"
    REPLACEMENT_TOO_LARGE = "replacement_too_large"
    SYNTHETIC_OMISSION = "synthetic_omission"
    DIFF_PREFIXED = "diff_prefixed"
    UNSAFE_MARKDOWN = "unsafe_markdown"
    QUICK_ACTION = "quick_action"


OMISSION_MESSAGES = {
    SuggestionOmission.INVALID_PATH: "the repository path could not be verified",
    SuggestionOmission.INVALID_RANGE: "the source range was invalid",
    SuggestionOmission.RANGE_TOO_LARGE: "the source range exceeded the safe line limit",
    SuggestionOmission.SOURCE_UNAVAILABLE: "the reviewed source blob was unavailable",
    SuggestionOmission.RANGE_OUT_OF_BOUNDS: "the source range was outside the reviewed blob",
    SuggestionOmission.MISSING_EXISTING_CODE: "the original source text was missing",
    SuggestionOmission.EXISTING_CODE_MISMATCH: (
        "the original source text did not match the reviewed range"
    ),
    SuggestionOmission.MALFORMED_REPLACEMENT: "the replacement text was malformed",
    SuggestionOmission.REPLACEMENT_TOO_LARGE: "the replacement exceeded the safe size limit",
    SuggestionOmission.SYNTHETIC_OMISSION: (
        "the replacement contained a synthetic omission marker"
    ),
    SuggestionOmission.DIFF_PREFIXED: "the replacement looked like unified diff content",
    SuggestionOmission.UNSAFE_MARKDOWN: "the replacement contained an unsafe Markdown fence",
    SuggestionOmission.QUICK_ACTION: "the replacement contained a GitLab quick action",
}


@dataclass(frozen=True, slots=True)
class SuggestionDecision:
    """A validated decision consumed by GitLab Markdown rendering."""

    state: SuggestionState
    replacement: str = ""
    range_suffix: str = ""
    omission: SuggestionOmission | None = None

    def __post_init__(self) -> None:
        """Reject impossible state combinations at the renderer boundary."""

        if self.state is SuggestionState.ACTIONABLE:
            if not self.replacement or not re.fullmatch(r"-0\+\d+", self.range_suffix):
                raise ValueError("actionable suggestion requires replacement and range")
            if self.omission is not None:
                raise ValueError("actionable suggestion cannot carry an omission")
            return
        if self.state is SuggestionState.OMITTED:
            if self.omission is None or self.replacement or self.range_suffix:
                raise ValueError("omitted suggestion requires only a closed omission reason")
            return
        if self.replacement or self.range_suffix or self.omission is not None:
            raise ValueError("absent and no-op suggestions cannot carry rendering fields")

    @property
    def omission_message(self) -> str:
        """Return a bounded public explanation without repository content."""

        if self.omission is None:
            return ""
        return OMISSION_MESSAGES[self.omission]


ELLIPSIS_BRIDGE_RE = re.compile(
    r"^(?:(?:#|//|;|--|/\*|\*|<!--|\(\*)\s*)?"
    r"(?:\.{3,}|…)"
    r"(?:\s*(?:\*/|-->|\*\)))?$"
)


def normalize_replacement(value: str) -> str:
    """Normalize transport line endings and one optional terminal newline."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized[:-1] if normalized.endswith("\n") else normalized


def safe_repository_path(path: str) -> bool:
    """Return whether an OCR path is safe after an immutable Git revision."""

    parts = path.split("/")
    pure = PurePosixPath(path)
    return bool(
        path
        and not pure.is_absolute()
        and "\\" not in path
        and all(part not in {"", ".", ".."} for part in parts)
        and not any(character == "\x7f" or ord(character) < 32 for character in path)
    )


def _omitted(reason: SuggestionOmission) -> SuggestionDecision:
    """Build an omitted decision from the closed reason vocabulary."""

    return SuggestionDecision(SuggestionState.OMITTED, omission=reason)


def _replacement_shape_omission(replacement: str) -> SuggestionOmission | None:
    """Return why replacement text cannot represent one safe contiguous edit."""

    if len(replacement) > MAX_SUGGESTION_CODE_CHARS:
        return SuggestionOmission.REPLACEMENT_TOO_LARGE
    if "```" in replacement:
        return SuggestionOmission.UNSAFE_MARKDOWN

    lines = replacement.splitlines()
    if any(ELLIPSIS_BRIDGE_RE.fullmatch(line.strip()) for line in lines):
        return SuggestionOmission.SYNTHETIC_OMISSION
    if any(line.lstrip().startswith("/") for line in lines):
        return SuggestionOmission.QUICK_ACTION

    nonblank = [line for line in lines if line.strip()]
    if nonblank:
        diff_prefixed = all(line.startswith(("+", "-")) for line in nonblank)
        unified_diff_markers = sum(
            line.startswith(("diff --git ", "index ", "--- ", "+++ ", "@@")) for line in nonblank
        )
        if diff_prefixed or unified_diff_markers >= 2:
            return SuggestionOmission.DIFF_PREFIXED
    return None


def evaluate_suggestion(
    comment: dict[str, Any],
    path: str,
    read_head_blob: Callable[[str], str | None],
) -> SuggestionDecision:
    """Prove an OCR replacement applies to one range in the reviewed head blob."""

    raw_replacement = comment.get("suggestion_code")
    if raw_replacement is None or raw_replacement == "":
        return SuggestionDecision(SuggestionState.ABSENT)
    if not isinstance(raw_replacement, str) or not raw_replacement.strip():
        return _omitted(SuggestionOmission.MALFORMED_REPLACEMENT)

    if not safe_repository_path(path):
        return _omitted(SuggestionOmission.INVALID_PATH)

    raw_start = comment.get("start_line")
    raw_end = comment.get("end_line")
    start = line_number(comment.get("line") if raw_start is None else raw_start)
    end = line_number(comment.get("line") if raw_end is None else raw_end)
    if start <= 0 or end < start:
        return _omitted(SuggestionOmission.INVALID_RANGE)
    span = end - start
    if span > MAX_SUGGESTION_SPAN_LINES:
        return _omitted(SuggestionOmission.RANGE_TOO_LARGE)

    source = read_head_blob(path)
    if source is None:
        return _omitted(SuggestionOmission.SOURCE_UNAVAILABLE)
    source_lines = source.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if end > len(source_lines):
        return _omitted(SuggestionOmission.RANGE_OUT_OF_BOUNDS)

    selected = "\n".join(source_lines[start - 1 : end])
    replacement = normalize_replacement(raw_replacement)
    if replacement == normalize_replacement(selected):
        return SuggestionDecision(SuggestionState.NO_OP)

    raw_existing = comment.get("existing_code")
    if not isinstance(raw_existing, str) or not raw_existing:
        return _omitted(SuggestionOmission.MISSING_EXISTING_CODE)
    if normalize_replacement(raw_existing) != normalize_replacement(selected):
        return _omitted(SuggestionOmission.EXISTING_CODE_MISMATCH)

    shape_omission = _replacement_shape_omission(replacement)
    if shape_omission is not None:
        return _omitted(shape_omission)

    return SuggestionDecision(
        SuggestionState.ACTIONABLE,
        replacement=replacement,
        range_suffix=f"-0+{span}",
    )
