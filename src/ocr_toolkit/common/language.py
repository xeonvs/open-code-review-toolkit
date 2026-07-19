"""Resolve the single public language setting used by OCR review flows."""

from __future__ import annotations

import os
import re
import sys

DEFAULT_REVIEW_LANGUAGE = "English"
REVIEW_LANGUAGE_ENV = "OCR_REVIEW_LANGUAGE"

KNOWN_LANGUAGES = frozenset(
    {
        "arabic",
        "chinese",
        "czech",
        "danish",
        "dutch",
        "english",
        "english (uk)",
        "english (us)",
        "finnish",
        "french",
        "german",
        "hebrew",
        "hindi",
        "indonesian",
        "italian",
        "japanese",
        "korean",
        "norwegian",
        "polish",
        "portuguese",
        "russian",
        "spanish",
        "swedish",
        "thai",
        "turkish",
        "ukrainian",
        "vietnamese",
    }
)
BCP47_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")


def resolve_review_language(value: str | None = None) -> str:
    """Return one safe language label for OCR config and review context."""

    raw = (os.environ.get(REVIEW_LANGUAGE_ENV, "") if value is None else value).strip()
    if not raw:
        return DEFAULT_REVIEW_LANGUAGE
    if raw.lower() in KNOWN_LANGUAGES or BCP47_RE.fullmatch(raw):
        return raw

    print(
        f"{REVIEW_LANGUAGE_ENV} is not an allowed language label or BCP-47 tag; "
        f"falling back to {DEFAULT_REVIEW_LANGUAGE}.",
        file=sys.stderr,
    )
    return DEFAULT_REVIEW_LANGUAGE
