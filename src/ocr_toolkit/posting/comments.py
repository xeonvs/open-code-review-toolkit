"""Posting facade for shared report value normalization."""

from ocr_toolkit.reporting.text import (
    clean_text,
    code_text,
    comment_line,
    compact_control_text,
    compact_escaped_text,
    compact_text,
    line_number,
)

__all__ = [
    "clean_text",
    "code_text",
    "comment_line",
    "compact_control_text",
    "compact_escaped_text",
    "compact_text",
    "line_number",
]
