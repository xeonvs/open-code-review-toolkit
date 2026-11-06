"""Bounded internationalized address candidates, not registration validation."""

from __future__ import annotations

from collections.abc import Callable

import regex

from ocr_toolkit.context.dlp.markup import interpret_markdown

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


def contains_email(
    value: str,
    *,
    markdown: bool = False,
    original: str | None = None,
    transform: Callable[[str], str] | None = None,
) -> bool:
    if "@" not in value:
        return False
    openings: dict[int, int] | None = None
    for match in EMAIL_RE.finditer(value, timeout=0.05):
        local = match["local"]
        if markdown and local and not local.strip("`"):
            if openings is None:
                source = value if original is None else original
                proven = interpret_markdown(source).code_openings
                openings = {start + width: start for start, width in proven}
                if original is not None and transform is not None:
                    # Transform disjoint source slices once, never search for
                    # a repeated lexeme. Backticks form normalization boundaries.
                    # Equality verifies compositionality before adopting offsets.
                    parts: list[str] = []
                    mapped: dict[int, int] = {}
                    cursor = position = 0
                    for start, width in proven:
                        part = transform(source[cursor:start])
                        parts.append(part)
                        position += len(part)
                        mapped[position + width] = position
                        cursor = start
                    parts.append(transform(source[cursor:]))
                    openings = mapped if "".join(parts) == value else {}
            # Only the actual opening delimiter can masquerade as a local
            # part. Repetition and the rest of the command do not change it.
            opening = openings.get(match.start() + len(local))
            if opening is not None and opening <= match.start():
                continue
        return True
    return False
