"""Validate and match the closed repository-relative policy glob grammar."""

from __future__ import annotations

import re
from functools import lru_cache
from itertools import pairwise

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
    if any(left == right == "**" for left, right in pairwise(parts)):
        raise PolicyScopeError("adjacent double-star segments are ambiguous")
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

    if not is_safe_repository_path(path):
        return False
    return _scope_regex(pattern).fullmatch(path) is not None


def is_safe_repository_path(path: object) -> bool:
    """Recognize one normalized repository-relative path without Git I/O."""

    return (
        isinstance(path, str)
        and bool(path)
        and not path.startswith(("/", "-"))
        and "\\" not in path
        and all(part not in {"", ".", ".."} for part in path.split("/"))
        and not any(character == "\x7f" or ord(character) < 32 for character in path)
    )
