"""Immutable text facts and bounded excerpts, independent of Git/process I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TextSpan = tuple[int, int]
MAX_EXCERPT_CHARS = 12_000
MAX_EXCERPT_SPAN_LINES = 200
MAX_EXCERPT_SOURCE_CHARS = MAX_EXCERPT_CHARS + MAX_EXCERPT_SPAN_LINES + 1
MAX_EXCERPT_BYTES = 4 * MAX_EXCERPT_CHARS + MAX_EXCERPT_SPAN_LINES + 1
MAX_SYNTAX_CHARS = 256_000
MAX_SYNTAX_CACHE_FILES = 4
MAX_SOURCE_BYTES = 5_000_000
MAX_TOTAL_SOURCE_BYTES = 32_000_000
SOURCE_SECONDS = 30

SourceReadReason = Literal[
    "none", "missing-source", "source-limit", "budget", "invalid-source", "unavailable"
]


@dataclass(frozen=True, slots=True)
class RepositoryTextExcerpt:
    start_line: int
    end_line: int
    text: str | None = field(repr=False)
    reason: Literal["none", "range", "limit"] = "none"


@dataclass(frozen=True, slots=True)
class RepositoryTextMetadata:
    object_sha: str
    byte_count: int
    line_count: int
    excerpts: tuple[RepositoryTextExcerpt, ...] = ()
    source: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class SourceReadResult:
    metadata: RepositoryTextMetadata | None = None
    reason: SourceReadReason = "unavailable"
    syntax_source: str | None = field(default=None, repr=False)
    syntax_limited: bool = False


def normalize_fragment(value: str) -> str:
    """Normalize transport line endings and one optional terminal newline."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized[:-1] if normalized.endswith("\n") else normalized


def source_lines(value: str) -> tuple[str, ...]:
    """Match Git's LF line addresses, including one unterminated final line."""

    if not value:
        return ()
    lines = value.split("\n")
    return tuple(lines[:-1] if value.endswith("\n") else lines)


def excerpt_from_lines(lines: tuple[str, ...], start: int, end: int) -> RepositoryTextExcerpt:
    """Select from already authenticated bounded text without a large join."""

    if not 1 <= start <= end <= len(lines):
        return RepositoryTextExcerpt(start, end, None, "range")
    if end - start > MAX_EXCERPT_SPAN_LINES:
        return RepositoryTextExcerpt(start, end, None, "limit")
    parts = lines[start - 1 : end]
    if sum(map(len, parts)) + end - start > MAX_EXCERPT_SOURCE_CHARS:
        return RepositoryTextExcerpt(start, end, None, "limit")
    text = "\n".join(parts)
    if len(normalize_fragment(text)) > MAX_EXCERPT_CHARS or len(text.encode()) > MAX_EXCERPT_BYTES:
        return RepositoryTextExcerpt(start, end, None, "limit")
    return RepositoryTextExcerpt(start, end, text)
