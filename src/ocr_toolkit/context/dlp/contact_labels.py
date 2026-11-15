"""Recognize bounded contact labels without evaluating source-language expressions."""

from __future__ import annotations

import re
import unicodedata

_CONTACT_HINT = re.compile(r"phone|tel|contact|call", re.IGNORECASE)
_CONTACT_WORDS = frozenset({"call", "phone", "telephone", "tel", "contact"})
_QUOTES = {'"': '"', "'": "'", "\u201c": "\u201d", "\u2018": "\u2019"}
_LABEL_WINDOW = 256


def _contact_context(prefix: str) -> bool:
    """Recognize contact words in human labels and identifier components."""

    prefix = prefix[-64:].rstrip(" \t")
    if not prefix or not prefix[-1].isalnum() or _CONTACT_HINT.search(prefix) is None:
        return False
    parts: list[str] = []
    word = ""
    for index, char in enumerate(prefix):
        if not char.isalnum():
            if word:
                parts.append(word.casefold())
                word = ""
            continue
        previous = prefix[index - 1] if index else ""
        camel_boundary = (
            bool(word)
            and char.isupper()
            and (
                not previous.isupper() or (index + 1 < len(prefix) and prefix[index + 1].islower())
            )
        )
        if camel_boundary:
            parts.append(word.casefold())
            word = ""
        word += char
    parts.append(word.casefold())
    last = parts[-1]
    if last in {"number", "no"} and len(parts) > 1:
        return parts[-2] in _CONTACT_WORDS
    return last in _CONTACT_WORDS or any(
        last.endswith(suffix) and last[: -len(suffix)] in _CONTACT_WORDS
        for suffix in ("number", "no")
    )


def _key_label(key: str) -> str | None:
    """Read a literal or bare key; computed and interpolated keys are not labels."""
    key = key.strip()
    if not key or len(key) > 64:
        return None
    quoted = key[0] in _QUOTES
    if quoted:
        if key[-1] != _QUOTES[key[0]] or len(key) < 3:
            return None
        key = key[1:-1]
    separators = "_-. \t" if quoted else "_"
    if not key or not all(char.isalnum() or char in separators for char in key):
        return None
    return key


def _closed_label(target: str, *, left_complete: bool) -> bool:
    """Read the terminal key, allowing ordinal postfixes but not calls or expressions."""
    target = target.rstrip()
    while target.endswith("]"):
        opening = target.rfind("[")
        if opening < 0:
            return False
        key = _key_label(target[opening + 1 : -1])
        if key is None:
            return False
        if not key.isdecimal():
            return _contact_context(key)
        target = target[:opening].rstrip()
    if target.endswith(")"):
        opening = target.rfind("(")
        preceding = target[:opening].rstrip()
        if (
            opening < 0
            or (preceding and (preceding[-1].isalnum() or preceding[-1] in "_])"))
            or (not preceding and not left_complete)
        ):
            return False
        key = _key_label(target[opening + 1 : -1])
        return key is not None and _contact_context(key)
    # A terminal non-contact field must not inherit an earlier contact selector.
    cursor = len(target)
    while cursor and (target[cursor - 1].isalnum() or target[cursor - 1] in "_.-"):
        cursor -= 1
    return _contact_context(target[cursor:])


def _structured_label(prefix: str, *, left_complete: bool) -> bool:
    """Require an adjacent binding separator before traversing a closed target."""
    cursor = len(prefix)
    while cursor and (prefix[cursor - 1].isspace() or prefix[cursor - 1] in "\"'\u201c\u2018([{"):
        cursor -= 1
    if not cursor or prefix[cursor - 1] not in "=:":
        return False
    separator = cursor - 1
    # Comparisons, arrows and compound operators do not establish label intent.
    if separator and prefix[separator - 1] in "=!<>+-*/%&|^?:":
        return False
    return _closed_label(prefix[:separator], left_complete=left_complete)


def _explicit_context(value: str, start: int) -> bool:
    """Bind a candidate to a nearby human label or a closed structured label target."""
    lower = max(0, start - _LABEL_WINDOW)
    if _structured_label(value[lower:start], left_complete=lower == 0):
        return True
    cursor = start
    while cursor > lower:
        char = value[cursor - 1]
        category = unicodedata.category(char)
        if (
            char in "+-/*%&\\!,;?"
            or category == "Pe"
            or not (char in "\t=" or category.startswith("P") or category == "Zs")
        ):
            break
        cursor -= 1
    return _contact_context(value[max(lower, cursor - 64) : cursor])
