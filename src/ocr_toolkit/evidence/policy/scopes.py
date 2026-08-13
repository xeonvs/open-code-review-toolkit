"""Validate and match the closed repository-relative policy glob grammar."""

from __future__ import annotations

import re
from functools import lru_cache

_FORBIDDEN = frozenset("[]{}!()|@+\\")


class PolicyScopeError(ValueError):
    """Report an unsafe or unsupported policy scope."""


def validate_scope(pattern: str) -> str:
    """Return a validated case-sensitive repository-relative POSIX glob."""

    if (
        not pattern
        or pattern.startswith("/")
        or any(char in _FORBIDDEN or char == "\x7f" or ord(char) < 32 for char in pattern)
    ):
        raise PolicyScopeError("scope uses unsafe syntax")
    parts = pattern.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PolicyScopeError("scope must use normalized repository-relative segments")
    if any("**" in part and part != "**" for part in parts):
        raise PolicyScopeError("double-star is allowed only as a complete segment")
    return pattern


def _segment_regex(segment: str) -> str:
    """Translate one validated non-recursive segment into a regular expression."""

    translated = []
    for char in segment:
        translated.append("[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char))
    return "".join(translated)


@lru_cache(maxsize=1024)
def _scope_regex(pattern: str) -> re.Pattern[str]:
    """Compile a validated scope while giving `**` whole-segment semantics."""

    parts = validate_scope(pattern).split("/")
    expression = "^"
    for index, part in enumerate(parts):
        if part == "**":
            if index == len(parts) - 1:
                expression += "(?:/[^/]+)*" if index else "(?:[^/]+(?:/|$))*"
            else:
                expression += "(?:/[^/]+)*/" if index else "(?:[^/]+/)*"
            continue
        if index and parts[index - 1] != "**":
            expression += "/"
        expression += _segment_regex(part)
    return re.compile(expression + "$")


def matches_scope(pattern: str, path: str) -> bool:
    """Return whether one normalized repository path matches a safe scope."""

    if not path or path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")):
        return False
    return _scope_regex(pattern).fullmatch(path) is not None
