"""Small helpers for OCR comment value normalization."""

from __future__ import annotations

import re
from typing import Any

from ocr_toolkit.common.markdown import escape_control_chars

MARKDOWN_INLINE_SPECIAL_RE = re.compile(r"([`*_{}\[\]()+.!|~-])")


def clean_text(value: Any) -> str:
    """Convert a JSON value to a stripped string."""

    return "" if value is None else str(value).strip()


def compact_text(value: str, max_chars: int) -> str:
    """Collapse whitespace and bound text for one-line MR summaries."""

    if max_chars <= 0:
        return ""

    collapsed = " ".join(value.split())
    if len(collapsed) <= max_chars:
        return collapsed

    if max_chars <= 3:
        return "." * max_chars

    return collapsed[: max_chars - 3].rstrip() + "..."


def compact_escaped_text(value: str, max_chars: int) -> str:
    """Escape Markdown-sensitive text before compacting MR summary snippets."""

    escaped = escape_control_chars(value)
    escaped = escaped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = escaped.replace("@", "&#64;")
    escaped = MARKDOWN_INLINE_SPECIAL_RE.sub(r"\\\1", escaped)
    return compact_text(escaped, max_chars)


def compact_control_text(value: str, max_chars: int) -> str:
    """Escape controls only before compacting text rendered inside inline code."""

    return compact_text(escape_control_chars(value), max_chars)


def code_text(value: Any) -> str:
    """Convert a JSON value to text while preserving code indentation."""

    if value is None:
        return ""
    return str(value).rstrip("\n")


def line_number(value: Any) -> int:
    """Parse a line number, returning zero when invalid."""

    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdecimal():
            return 0
        parsed = int(text)
    else:
        return 0
    return parsed if parsed > 0 else 0


def comment_line(comment: dict[str, Any]) -> int:
    """Return the best new-line number for a GitLab inline discussion.

    Anchor on the start of the range so multi-line findings highlight the
    first problematic line rather than the end of the span.
    """

    for key in ("start_line", "line", "end_line"):
        parsed = line_number(comment.get(key))
        if parsed > 0:
            return parsed
    return 0
