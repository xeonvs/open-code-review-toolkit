"""Bounded lexical completion of credential values; no source execution."""

from __future__ import annotations

import re

MAX_TAIL_CHARS = 4096
_LINE_END = re.compile(r"[\r\n\x85\u2028\u2029]")
_FIELD_HEAD = re.compile(
    r"(?:(?P<quote>['\"])[^'\"\\\r\n]{1,128}(?P=quote)|(?P<name>[^\s:='\"]{1,128}))"
    r"[ \t]*[:=]"
)


def _next_field(text: str, cursor: int, limit: int) -> bool:
    match = _FIELD_HEAD.match(text, cursor, limit)
    if match is None:
        return False
    name = match["name"]
    # isidentifier includes combining marks omitted by stdlib re's \w.
    # Dots/hyphens remain ordinary field punctuation, not source authority.
    return name is None or name.replace(".", "_").replace("-", "_").isidentifier()


def _spacing(text: str, cursor: int, limit: int) -> tuple[int, bool] | None:
    """Skip bounded whitespace/comments without treating them as termination."""

    newline = False
    while cursor < limit:
        if text[cursor].isspace():
            newline |= _LINE_END.match(text, cursor) is not None
            cursor += 1
        elif text.startswith(("#", "//"), cursor):
            ending = _LINE_END.search(text, cursor, limit)
            if ending is None:
                return (limit, newline) if limit == len(text) else None
            cursor = ending.end()
            newline = True
        elif text.startswith(("/*", "<!--"), cursor):
            closing = "*/" if text.startswith("/*", cursor) else "-->"
            end = text.find(closing, cursor + 2, limit)
            if end < 0:
                return None
            end += len(closing)
            newline |= _LINE_END.search(text, cursor, end) is not None
            cursor = end
        else:
            break
    if cursor == limit and limit < len(text):
        return None
    return cursor, newline


def complete_value(text: str, end: int) -> bool:
    """Require a delimiter, end, or a distinct field after source trivia."""

    limit = min(len(text), end + MAX_TAIL_CHARS)
    tail = _spacing(text, end, limit)
    if tail is None:
        return False
    cursor, _newline = tail
    return (
        cursor == len(text)
        or text[cursor] in ",;)]}"
        or (cursor > end and _next_field(text, cursor, limit))
    )


def complete_field(text: str, end: int) -> bool:
    """Qualify a declarative field without accepting an expression prefix."""

    limit = min(len(text), end + MAX_TAIL_CHARS)
    tail = _spacing(text, end, limit)
    if tail is None:
        return False
    cursor, newline = tail
    return (
        cursor == len(text)
        or (cursor > end and _next_field(text, cursor, limit))
        or (newline and text[cursor] in ",;)]}")
    )


def complete_carrier(text: str, end: int) -> bool:
    """Check a source carrier through trivia, closers and trailing separators."""

    limit = min(len(text), end + MAX_TAIL_CHARS)
    cursor = end
    while cursor < limit:
        tail = _spacing(text, cursor, limit)
        if tail is None:
            return False
        cursor, _newline = tail
        if cursor == len(text):
            return True
        if text[cursor] in ")]}":
            cursor += 1
        elif text[cursor] == ",":
            tail = _spacing(text, cursor + 1, limit)
            if tail is None:
                return False
            after, _newline = tail
            if after < len(text) and text[after] in ")]}":
                cursor = after
            else:
                return after == len(text) or text[after].isalnum() or text[after] in "_\"'([{"
        else:
            return text[cursor] == ";" or (cursor > end and _next_field(text, cursor, limit))
    return cursor == len(text)
