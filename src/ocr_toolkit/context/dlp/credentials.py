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


def credential_reference_spans(value: str) -> tuple[tuple[int, int], ...]:
    """Locate complete symbolic fields; application labels grant no value waiver."""

    return tuple(match.span("key") for match in _NO_VALUE.finditer(value))


def credential_reference_view(value: str) -> str:
    """Keep material outside exact no-value keys visible to generic checks.

    A map named permissions does not establish application-specific semantics.
    Literal values retain ordinary checks. Independent known-secret, bearer/JWT,
    PII and forbidden-origin checks still inspect the original.
    """

    parts = []
    previous = 0
    for start, end in credential_reference_spans(value):
        parts.extend((value[previous:start], "x" * (end - start)))
        previous = end
    parts.append(value[previous:])
    return "".join(parts)
