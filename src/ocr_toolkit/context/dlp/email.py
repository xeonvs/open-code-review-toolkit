"""Bounded internationalized address candidates, not registration validation."""

from __future__ import annotations

import regex

from ocr_toolkit.context.dlp.markup import RepresentationLimit, interpret_markdown

MAX_SOURCE_SEARCH = 8_000_000

_LOCAL = r"""(?:[a-z0-9.!#$%&'*+/=?^_`{|}~\p{L}\p{N}\p{M}-]{1,64}|"(?:[^"\\\r\n]|\\.){1,64}")"""
_LABEL = r"[\p{L}\p{N}](?:[\p{L}\p{N}\p{M}-]{0,61}[\p{L}\p{N}\p{M}])?"
# SMTP literal forms are dotted numeric addresses or tagged address literals,
# not arbitrary bracketed text (e.g. a regex character class after @ref).
# Keep malformed numeric/tagged contacts conservative; no DNS/IANA lookup.
_DOMAIN_LITERAL = (
    r"(?:[0-9]{1,3}(?:\.[0-9]{1,3}){3}|[A-Za-z0-9][A-Za-z0-9-]{0,31}:[^\[\]\\\s]{1,80})"
)
EMAIL_RE = regex.compile(
    rf"(?i)(?<![\w.+-])(?P<local>{_LOCAL})@"
    rf"(?:(?:{_LABEL}\.)+(?:[\p{{L}}\p{{M}}]{{1,63}}|xn--[a-z0-9-]{{1,59}})|"
    rf"\[{_DOMAIN_LITERAL}\])(?![\w-])",
)


def contains_email(value: str, *, markdown: bool = False) -> bool:
    if "@" not in value:
        return False
    sources: set[tuple[str, str]] | None = None
    search_cost = 0
    for match in EMAIL_RE.finditer(value, timeout=0.05):
        local = match["local"]
        if markdown and local and not local.strip("`"):
            if sources is None:
                sources = set(interpret_markdown(value).code_sources)
            lexeme = match[0] + local
            search_cost += len(value)
            if search_cost > MAX_SOURCE_SEARCH:
                raise RepresentationLimit("code-span source search budget")
            # The parser records the exact source lexeme. Only a unique exact
            # occurrence can establish its original position; ambiguity stays
            # protected. Code fences and escaped delimiters supply no waiver.
            if (
                (lexeme, match[0][len(local) :]) in sources
                and value.find(lexeme) == match.start()
                and value.rfind(lexeme) == match.start()
            ):
                continue
        return True
    return False
