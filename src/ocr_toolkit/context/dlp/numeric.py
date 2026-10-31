"""Bounded phone candidates and complete technical-number interpretation."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
import uuid
from datetime import date

import regex

from ocr_toolkit.context.dlp.decoding import _technical_decode, bounded_nfkc

_DIGIT_MARKS = regex.compile(r"(?<=\p{Nd})\p{M}+")
_ESCAPED_PUNCTUATION = re.compile(r"\\([\\`*{}\[\]()#+\-.!_>~|])")


def phone_markup_view(value: str, *, formatting: bool = True) -> str:
    """Preserve separators when removing decoration instead of joining an ID."""

    value = bounded_nfkc(value)
    value = _ESCAPED_PUNCTUATION.sub(r"\1", value)
    if formatting:
        # CommonMark does not activate intra-word underscores. Treating numeric
        # separators as emphasis invents contacts such as 1_000_000.
        value = re.sub(r"[`*~]|(?<!\w)_|_(?!\w)", " ", value)
    return _DIGIT_MARKS.sub(" ", value, timeout=0.05)


PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{5,62}\d)(?!\w)")
MIN_PHONE_DIGITS = 7


def _phone_shape(value: str, match: re.Match[str]) -> bool:
    """Keep legacy long six-digit layouts and recognize short national phones."""

    if match[0].startswith("+") or _explicit_context(value, match.start()):
        return True
    digits = sum(c.isdecimal() for c in match[0])
    return digits >= MIN_PHONE_DIGITS or (digits >= 6 and len(match[0]) >= 9)


ISO_DATE_RE = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")


_NETWORK_TOKEN_CHARS = frozenset("0123456789abcdefABCDEF:./")


_NETWORK_LABEL_RE = re.compile(
    r"(?i)(?<![\w:])(?:ip(?:v[46])?|cidr|subnet|address|host|listen|allow|network|prefix):$"
)


_TECHNICAL_SEPARATOR = r"(?:[ \t]+|[ \t]*(?:[<>]=?|[=!]=|=|[≤≥≠])[ \t]*)"


VERSION_CONTEXT_RE = re.compile(
    rf"(?i)\b(?:version|release|build|pin){_TECHNICAL_SEPARATOR}(?:v)?$"
)


DATE_CONTEXT_RE = re.compile(
    rf"(?i)\b(?:date|dated|on|since|until|before|after|expires)"
    rf"(?:[ \t]+on)?{_TECHNICAL_SEPARATOR}$"
)


IP_CONTEXT_RE = re.compile(
    r"(?i)(?:\b|_)(?:ipv4|ip|cidr|subnet|address|host|loginhost|listen|allow|network)\b"
)


PHONE_CONTEXT_RE = re.compile(r"(?i)\b(?:call|phone|tel|contact)[ \t]*$")

_VERSION = r"(?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,2})){1,3}"
_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
_TECHNICAL_BLOCK = re.compile(
    rf"(?<![\w.])(?:"
    rf"(?P<uuid>[0-9a-f]{{8}}-(?:[0-9a-f]{{4}}-){{3}}[0-9a-f]{{12}})|"
    rf"(?P<version_date>{_VERSION}[ \t]+[-\u2013\u2014][ \t]+(?P<release_date>{_DATE}))|"
    rf"(?P<versions>{_VERSION}(?:/|-|\.\.\.){_VERSION})|"
    r"(?P<iteration>for[ \t]+[A-Za-z_][A-Za-z0-9_]{0,63}[ \t]+in[ \t]+"
    r"[0-9](?:[ \t]+[0-9]){1,31}[ \t]*;[ \t]*do)|"
    rf"(?P<date>{_DATE})"
    rf")(?!\w)",
    re.IGNORECASE,
)


def _explicit_context(value: str, start: int) -> bool:
    cursor = start
    while cursor and value[cursor - 1] in " \t'\"=:[{(":
        cursor -= 1
    return PHONE_CONTEXT_RE.search(value[max(0, cursor - 64) : cursor]) is not None


def _complete_technical_block(value: str, start: int, end: int) -> bool:
    """Require complete bounded typed syntax around the whole phone candidate."""

    left, right = max(0, start - 128), min(len(value), end + 128)
    for block in _TECHNICAL_BLOCK.finditer(value[left:right]):
        if not left + block.start() <= start <= end <= left + block.end():
            continue
        try:
            if block["uuid"]:
                uuid.UUID(block["uuid"])
            elif block["date"] or block["release_date"]:
                date.fromisoformat(block["date"] or block["release_date"])
            elif block["iteration"]:
                return True
            else:
                versions = re.split(r"/|-|\.\.\.", block["versions"])
                # Each side is a short dotted version, not a whole phone.
                if any(sum(c.isdecimal() for c in part) >= MIN_PHONE_DIGITS for part in versions):
                    continue
            return True
        except ValueError:
            continue
    return False


def _contains_phone(value: str) -> bool:
    """Recognize formatted phone-like values without classifying bare identifiers."""

    return any(
        (
            match.group(0).startswith("+")
            or _explicit_context(value, match.start())
            or any(separator in match.group(0) for separator in " .()/-")
        )
        and _phone_shape(value, match)
        and not _technical_number(value, match)
        for match in PHONE_RE.finditer(value)
    )


def _network_number(value: str, start: int, end: int) -> bool:
    """Parse a complete bounded network, not a phone-regex-sized fragment."""

    candidate_start = start
    while start and end - start < 64 and value[start - 1] in _NETWORK_TOKEN_CHARS:
        start -= 1
    label_separator = False
    # Only a recognized delimited label may precede the complete network.
    # A lone hextet such as ffff: must not grant an IPv4-tail exception.
    colon = value.find(":", start, candidate_start)
    if colon >= 0 and _NETWORK_LABEL_RE.search(value[max(0, colon - 16) : colon + 1]):
        start = colon + 1
        label_separator = True
    while end < len(value) and end - start < 64 and value[end] in _NETWORK_TOKEN_CHARS:
        end += 1
    contact_prefix = value[max(0, start - 25) : start].rstrip(": \t")
    if PHONE_CONTEXT_RE.search(contact_prefix):
        return False
    left = value[start - 1] if start and not label_separator else ""
    for neighbor in (left, value[end : end + 1]):
        if neighbor and (neighbor.isalnum() or neighbor in "_:./%-"):
            return False
    token = value[start:end]
    if "/" not in token:
        return False
    if token.endswith("."):
        # Remove one prose period; dotted/word continuations still fail parsing.
        token = token[:-1]
    try:
        ipaddress.ip_network(token, strict=False)
    except ValueError:
        return False
    return True


def _decoded_network_number(before: str, candidate: str, after: str) -> bool:
    """Bind an encoded fragment to its complete parsed network, not another value."""

    # A 64-character token and contact prefix fit here even with decimal escapes.
    raw_before, raw_after = before[-1024:], after[:1024]
    if not any(marker in raw_before or marker in raw_after for marker in ("#", "&")):
        return False
    decoded_before = _technical_decode(raw_before)
    decoded_after = _technical_decode(raw_after)
    if decoded_before == raw_before and decoded_after == raw_after:
        return False
    start = len(decoded_before)
    return _network_number(
        decoded_before + candidate + decoded_after, start, start + len(candidate)
    )


def _technical_number(value: str, match: re.Match[str]) -> bool:
    """Exclude only bounded, parsed technical syntax from phone candidates."""

    candidate = match.group(0)
    if (
        candidate.startswith("+")
        or candidate != candidate.strip()
        or _explicit_context(value, match.start())
    ):
        return False
    if _complete_technical_block(value, match.start(), match.end()):
        return True
    # All contextual grammars below are bounded. Do not copy the complete
    # document per candidate when a file contains many valid technical tokens.
    before = value[max(0, match.start() - 1024) : match.start()]
    after = value[match.end() : match.end() + 1024]
    if PHONE_CONTEXT_RE.search(before[-24:]):
        return False
    network = "/" in candidate or re.match(r"/[+-]?[0-9]", after) is not None
    if network and _network_number(value, *match.span()):
        return True
    if _decoded_network_number(before, candidate, after):
        return True
    if network:
        return False
    if before.endswith((".", "/", "-")) or re.match(r"(?:[./-]\d)", after):
        return False
    try:
        if isinstance(ipaddress.ip_address(candidate), ipaddress.IPv4Address):
            if after.startswith(":"):
                port = re.match(r":(\d{1,5})\b", after)
                return bool(port and 1 <= int(port[1]) <= 65535)
            return bool(IP_CONTEXT_RE.search(before[-96:]))
    except ValueError:
        pass
    # Only the bounded technical prefix is decoded/normalized: other representations and
    # the complete unit still pass all secret, contact and laundering checks.
    technical_prefix = unicodedata.normalize("NFKC", _technical_decode(before[-64:]))
    if (
        VERSION_CONTEXT_RE.search(technical_prefix.rstrip("'\""))
        and len(candidate) <= 64
        and re.fullmatch(r"[0-9]+(?:\.[0-9]+){2,7}", candidate)
    ):
        return True
    if ISO_DATE_RE.fullmatch(candidate) and DATE_CONTEXT_RE.search(technical_prefix):
        try:
            date(int(candidate[:4]), int(candidate[5:7]), int(candidate[8:10]))
        except ValueError:
            return False
        return True
    if re.fullmatch(r"\d{4}\.\d{1,2}\.\d{1,3}", candidate):
        return bool(VERSION_CONTEXT_RE.search(technical_prefix))
    if re.fullmatch(r"\d+\.\d+", candidate):
        return bool(
            re.search(r"(?i)\bdecimal\([ \t]*['\"]$", technical_prefix)
            and (
                re.match(r"['\"][ \t]*\)", after)
                or re.match(r"['\"][ \t]*\)", _technical_decode(after[:64]))
            )
        )
    return False


def _explicit_contact_phone(value: str) -> bool:
    for match in PHONE_RE.finditer(value):
        candidate = match.group(0)
        if (
            candidate.startswith("+") or _explicit_context(value, match.start())
        ) and not _technical_number(value, match):
            return True
    return False
