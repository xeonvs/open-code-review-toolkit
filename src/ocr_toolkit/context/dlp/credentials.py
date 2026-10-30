"""Closed no-material credential roles; never a waiver for literal secrets."""

from __future__ import annotations

import re

from ocr_toolkit.common.redaction import SENSITIVE_NAMED_KEY_PATTERN
from ocr_toolkit.context.dlp.decoding import RepresentationLimit, _technical_decode, bounded_nfkc

MAX_CREDENTIAL_FIELDS = 4096

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
_ABSENT_FIELD = re.compile(
    rf"(?i)[ \t]*(?P<key>{SENSITIVE_NAMED_KEY_PATTERN}|"
    rf"(?P<key_quote>['\"]){SENSITIVE_NAMED_KEY_PATTERN}(?P=key_quote))"
    rf"[ \t]*[:=][ \t]*(?:{_REFERENCE}|\*\*\*|"
    rf"(?P<value_quote>['\"])(?:{_REFERENCE}|\*\*\*|)(?P=value_quote))[ \t]*"
)


def _encoded_absent_carriers(value: str) -> tuple[tuple[int, int, str], ...]:
    """Qualify original ordinary quoted carriers before decoding their payloads.

    Decoding a quoted encoded field as a whole can manufacture a quote run by
    joining its value quotes to the outer carrier. No filename or language
    supplies authority: the entire decoded payload must prove absent material.
    Triple/adjacent/unterminated carrier quoting and nonempty payloads never
    qualify. Surrounding source remains subject to ordinary continuation checks.
    """

    if "#" not in value and "&" not in value:
        return ()
    spans = []
    cursor = 0
    while cursor < len(value):
        quote = value[cursor]
        if quote not in "\"'" or (cursor and value[cursor - 1] in "\\\"'"):
            cursor += 1
            continue
        start = cursor + 1
        if start < len(value) and value[start] == quote:
            while cursor < len(value) and value[cursor] == quote:
                cursor += 1
            continue
        cursor = start
        while cursor < len(value) and value[cursor] not in {quote, "\r", "\n"}:
            cursor += 2 if value[cursor] == "\\" else 1
        if cursor >= len(value) or value[cursor] != quote:
            continue
        end = cursor
        cursor += 1
        if cursor < len(value) and value[cursor] == quote:
            continue
        payload = value[start:end]
        if "#" not in payload and "&" not in payload:
            continue
        decoded = bounded_nfkc(_technical_decode(payload))
        field = _ABSENT_FIELD.fullmatch(decoded)
        if decoded != payload and field is not None:
            if len(spans) >= MAX_CREDENTIAL_FIELDS:
                raise RepresentationLimit("credential carrier budget")
            key = field["key"][1:-1] if field["key_quote"] else field["key"]
            # Preserve the key and quoted-carrier association for subsequent
            # generic checks. Only the proven absent value is canonicalized;
            # source text, continuations and later decoding remain visible.
            spans.append((start - 1, cursor, "'" + key + '="***"' + "'"))
    return tuple(spans)


def credential_reference_spans(value: str) -> tuple[tuple[int, int], ...]:
    """Locate complete symbolic fields; application labels grant no value waiver."""

    spans = []
    for match in _NO_VALUE.finditer(value):
        if len(spans) >= MAX_CREDENTIAL_FIELDS:
            raise RepresentationLimit("credential field budget")
        spans.append(match.span("key"))
    return tuple(spans)


def credential_reference_view(value: str) -> str:
    """Refine proved no-material fields without hiding surrounding material.

    A map named permissions does not establish application-specific semantics.
    Literal values retain ordinary checks. Independent known-secret, bearer/JWT,
    PII and forbidden-origin checks still inspect the original.
    """

    parts = []
    previous = 0
    references = credential_reference_spans(value)
    carriers = _encoded_absent_carriers(value)
    if len(references) + len(carriers) > MAX_CREDENTIAL_FIELDS:
        raise RepresentationLimit("credential semantic span budget")
    spans = sorted((*((a, b, "x" * (b - a)) for a, b in references), *carriers))
    for start, end, replacement in spans:
        if start < previous:
            continue
        parts.extend((value[previous:start], replacement))
        previous = end
    parts.append(value[previous:])
    return "".join(parts)
