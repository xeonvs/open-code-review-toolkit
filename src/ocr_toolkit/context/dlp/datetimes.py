"""Bounded complete calendar timestamps, without source or disclosure authority."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

CALENDAR_DAY_PATTERN = r"(?:\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})"
_DATETIME = re.compile(
    rf"(?P<day>{CALENDAR_DAY_PATTERN})(?:T|[ \t]+)"
    r"(?P<clock>\d{2}:\d{2}(?::\d{2}(?:[.,]\d{1,9})?)?)"
    r"(?P<zone>Z|[ \t]+UTC|[+-]\d{2}:?\d{2})?",
    re.IGNORECASE,
)
_CONTINUED_ZONE = re.compile(r"(?:UTC|Z(?:$|[^a-z]))", re.IGNORECASE)
_WINDOW = 128


def calendar_day(value: str) -> str:
    """Validate ISO or dotted day/month/year with one calendar implementation."""

    value = "".join(str(int(char)) if char.isdecimal() else char for char in value)
    if "." in value:
        value = f"{value[6:10]}-{value[3:5]}-{value[:2]}"
    return date.fromisoformat(value).isoformat()


def _word_part(char: str) -> bool:
    """Recognize Unicode word continuations at numeric token boundaries."""
    return char.isalnum() or unicodedata.category(char).startswith("M")


def complete_datetime(value: str, start: int, end: int) -> bool:
    """Recognize a whole parsed timestamp containing this entire numeric candidate."""

    for block in _DATETIME.finditer(value, max(0, start - _WINDOW), min(len(value), end + _WINDOW)):
        if not block.start() <= start < end <= block.end():
            continue
        left = value[block.start() - 1] if block.start() else ""
        tail = value[block.end() : block.end() + _WINDOW]
        if block.end() + len(tail) < len(value) and "utc".startswith(tail.lstrip(" \t").casefold()):
            # Empty or partial zone tokens at the read boundary remain unknown.
            continue
        right = tail[:1]
        if left and (_word_part(left) or left in "_.:+/-"):
            continue
        if right and (_word_part(right) or right in "_+/-"):
            continue
        if right == ":":
            remainder = tail[1:]
            separated = bool(remainder) and (
                remainder[0].isspace()
                or (remainder.startswith("\\") and remainder[1:2] in {"n", "r", "t"})
            )
            # Prose punctuation may precede real or escaped whitespace. Do not
            # decode material or extend the proof span over that separator.
            if not separated and (remainder or not block["zone"]):
                continue
        if right == "." and len(tail) > 1 and (_word_part(tail[1]) or tail[1] in "_.:+/-"):
            continue
        if _CONTINUED_ZONE.match(tail.lstrip(" \t")):
            continue
        if int(block["clock"][:2]) > 23:
            # Some supported stdlib versions normalize 24:00 to the next day.
            # This grammar qualifies only an explicit same-day wall clock.
            continue
        zone = (block["zone"] or "").strip().upper()
        if zone in {"Z", "UTC"}:
            zone = "+00:00"
        elif zone:
            digits = zone[1:].replace(":", "")
            # fromisoformat normalizes offset minute overflow; reject it instead.
            if int(digits[:2]) > 23 or int(digits[2:]) > 59:
                continue
        try:
            token = f"{calendar_day(block['day'])}T{block['clock']}{zone}"
            # PHONE_RE recognizes every Unicode decimal digit. Preserve that
            # semantic domain while feeding the ASCII-only calendar parser;
            # no code-point positions are changed for containment checks.
            token = "".join(str(int(char)) if char.isdecimal() else char for char in token)
            datetime.fromisoformat(token)
        except ValueError:
            continue
        return True
    return False
