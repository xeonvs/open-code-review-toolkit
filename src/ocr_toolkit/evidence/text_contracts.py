"""Immutable text facts and bounded excerpts, independent of Git/process I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TextSpan = tuple[int, int]
MAX_EXCERPT_CHARS = 12_000
MAX_EXCERPT_BYTES = 48_000
MAX_EXCERPT_SPAN_LINES = 200
MAX_SYNTAX_CHARS = 256_000


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
