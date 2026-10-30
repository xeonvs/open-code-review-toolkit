"""Closed no-material credential roles; never a waiver for literal secrets."""

from __future__ import annotations

import re

from ocr_toolkit.common.redaction import SENSITIVE_NAMED_KEY_PATTERN

# Only symbolic member references: no calls, defaults, interpolation fragments,
# quoted arguments, arithmetic or concatenation can prove an absent value.
_NAME = r"[A-Za-z_][A-Za-z0-9_]{0,127}"
_MEMBER = rf"{_NAME}(?:\.{_NAME}){{0,7}}"
_REFERENCE = rf"(?:\$?\{{\{{[ \t]*{_MEMBER}[ \t]*\}}\}}|\$\{{{_NAME}\}})"
_NO_VALUE = re.compile(
    rf"(?im)^[ \t]*(?P<key>['\"]?{SENSITIVE_NAMED_KEY_PATTERN}['\"]?)[ \t]*[:=][ \t]*"
    rf"(?P<value>{_REFERENCE}|(?P<quote>['\"])(?:{_REFERENCE}|)(?P=quote))"
    r"(?=[ \t]*$)"
)
_PERMISSION_BLOCK = re.compile(r"^(?P<indent> *)permissions:[ \t]*$")
_PERMISSION = re.compile(
    r"^(?P<indent> *)(?P<key>[A-Za-z][A-Za-z0-9_-]{0,127}):[ \t]*(?:read|write|none)[ \t]*$"
)


def credential_reference_spans(value: str) -> tuple[tuple[int, int], ...]:
    """Locate only complete symbolic fields and enclosing permission roles."""

    spans = [match.span("key") for match in _NO_VALUE.finditer(value)]
    parent: int | None = None
    offset = 0
    for line in value.splitlines(keepends=True):
        text = line.rstrip("\r\n")
        left = offset
        offset += len(line)
        heading = _PERMISSION_BLOCK.fullmatch(text)
        if heading:
            parent = len(heading["indent"])
            continue
        if not text.strip():
            continue
        indent = len(text) - len(text.lstrip(" "))
        if parent is None or indent <= parent:
            parent = None
            continue
        permission = _PERMISSION.fullmatch(text)
        if permission:
            start, end = permission.span("key")
            spans.append((left + start, left + end))
        else:
            # Nested/quoted/unknown syntax does not inherit authority.
            parent = None
    return tuple(sorted(spans))


def credential_reference_view(value: str) -> str:
    """Keep material outside exact no-value keys visible to generic checks.

    A permission role requires the enclosing indentation block, never its name
    or a bare value such as ``token: write`` alone. Independent known-secret,
    bearer/JWT, PII and forbidden-origin checks still inspect the original.
    """

    parts = []
    previous = 0
    for start, end in credential_reference_spans(value):
        parts.extend((value[previous:start], "x" * (end - start)))
        previous = end
    parts.append(value[previous:])
    return "".join(parts)
