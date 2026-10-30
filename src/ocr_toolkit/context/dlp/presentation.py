"""Standard Unicode presentation qualification without rewriting material."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

import emoji

_ASCII_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
_ASCII_DISPLAY = {code: " " if chr(code).isspace() else None for code in (*range(32), 127)}


def canonical_whitespace(value: str) -> str:
    """Canonicalize display controls with an equivalent C-level ASCII path."""

    if value.isascii():
        return value.translate(_ASCII_DISPLAY)
    return "".join(" " if c.isspace() else "" if is_display_control(c) else c for c in value)


def is_display_control(character: str) -> bool:
    return bool(
        (unicodedata.category(character) in {"Cc", "Cf", "Cs"} and not character.isspace())
        or "\ufe00" <= character <= "\ufe0f"
        or "\U000e0100" <= character <= "\U000e01ef"
    )


def _qualified_spans(value: str) -> Iterator[tuple[int, int]]:
    statuses = {
        emoji.STATUS["fully_qualified"],
        emoji.STATUS["minimally_qualified"],
        emoji.STATUS["unqualified"],
    }
    for token in emoji.analyze(value, non_emoji=False, join_emoji=False):
        match = token.value
        if (
            isinstance(match, emoji.EmojiMatch)
            and not isinstance(match, emoji.EmojiMatchZWJNonRGI)
            and match.data is not None
            and match.data.get("status") in statuses
            and value[match.start : match.end] == match.emoji
        ):
            yield match.start, match.end


def has_unsafe_controls(value: str, *, display: bool = False, allowed: str = "\n") -> bool:
    """Exempt controls only at their exact positions in standard sequences.

    Never rebuild input from emoji tokens: unmatched joiners may be skipped by
    the tokenizer. A streaming merge avoids a source-sized set of positions.
    """

    if value.isascii():
        return any(
            not match[0].isspace() if display else match[0] not in allowed
            for match in _ASCII_CONTROLS.finditer(value)
        )

    def suspect(character: str) -> bool:
        if display:
            return is_display_control(character)
        return (
            unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
            and character not in allowed
        )

    bad = ((i, c) for i, c in enumerate(value) if suspect(c))
    first = next(bad, None)
    if first is None:
        return False
    spans = iter(_qualified_spans(value))
    start = end = 0
    current = first
    while current is not None:
        index, character = current
        if unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}:
            return True
        while end <= index:
            try:
                start, end = next(spans)
            except StopIteration:
                return True
        if not start <= index < end:
            return True
        current = next(bad, None)
    return False
