"""Bounded display-entity decoding shared by independent DLP representations."""

from __future__ import annotations

import html
import re
import unicodedata


class RepresentationLimit(ValueError):
    """An independent representation cannot be completed within its work bound."""


def bounded_nfkc(value: str, *, original: str | None = None, fold: bool = False) -> str:
    """Bound compatibility expansion before subsequent Python/parser allocation."""

    original = value if original is None else original
    maximum = 4 * len(original) + 4096
    normalized = value if value.isascii() else unicodedata.normalize("NFKC", value)
    if len(normalized) > maximum:
        raise RepresentationLimit("normalization character expansion")
    if fold:
        normalized = normalized.casefold()
        if len(normalized) > maximum:
            raise RepresentationLimit("normalization character expansion")
    try:
        source_bytes = len(original) if original.isascii() else len(original.encode())
        result_bytes = len(normalized) if normalized.isascii() else len(normalized.encode())
    except UnicodeError as exc:
        raise RepresentationLimit("normalization Unicode input") from exc
    if result_bytes > 4 * source_bytes + 4096:
        raise RepresentationLimit("normalization byte expansion")
    return normalized


_MERMAID_ENTITY_RE = re.compile(r"(?<!&)#([0-9]+);")


_HTML_NUMERIC_ENTITY_RE = re.compile(r"&#([xX][0-9a-fA-F]+|[0-9]+);?")


def _html_decode(value: str) -> str:
    """Decode the bounded entity layers a browser can display as text."""

    def bounded_number(match: re.Match[str]) -> str:
        number = match[1]
        hexadecimal = number[:1].lower() == "x"
        digits = (number[1:] if hexadecimal else number).lstrip("0") or "0"
        if len(digits) > (6 if hexadecimal else 7):
            return "&#1114112;"  # Let html.unescape apply its invalid-scalar mapping.
        return f"&#{'x' if hexadecimal else ''}{digits};"

    normalized = value
    for _iteration in range(2):
        # Preserve HTML's scalar/legacy mappings without an unbounded decimal
        # integer conversion or changing Python's process-wide integer limit.
        prepared = (
            _HTML_NUMERIC_ENTITY_RE.sub(bounded_number, normalized)
            if "&#" in normalized
            else normalized
        )
        decoded = html.unescape(prepared)
        if decoded == normalized:
            break
        normalized = decoded
    return normalized


def _mermaid_decode(value: str) -> str:
    """Decode one layer of the renderer's decimal entities without expansion."""

    def character(match: re.Match[str]) -> str:
        digits = match[1].lstrip("0") or "0"
        if len(digits) > 7:
            return match[0]
        code = int(digits)
        return chr(code) if code <= 0x10FFFF and not 0xD800 <= code <= 0xDFFF else match[0]

    return _MERMAID_ENTITY_RE.sub(character, value)


def _technical_decode(value: str) -> str:
    """Resolve bounded HTML/one-Mermaid/HTML context without recursive Mermaid."""

    return _html_decode(_mermaid_decode(_html_decode(value)))
