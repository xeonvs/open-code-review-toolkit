"""Settings and small value helpers for OCR review context generation."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from ocr_toolkit.common.markdown import inline_code as _inline_code

DEFAULT_MAX_FILE_BYTES = 256_000


MAX_BACKGROUND_SECTION_ITEMS = 120


MAX_INSTRUCTION_BYTES = 24_000


DEFAULT_BACKGROUND_MAX_BYTES = 65_536


MAX_BACKGROUND_MAX_BYTES = 1_048_576


DEFAULT_BACKGROUND_MAX_CHARS = 7_950


MAX_BACKGROUND_MAX_CHARS = 7_950


DEFAULT_MANIFEST_PARSE_MAX_BYTES = 2_000_000


MAX_MANIFEST_PARSE_MAX_BYTES = 5_000_000


JSON_OBJECT_PARSE_ERROR = "top-level JSON value is not an object"


def getenv_int(name: str, default: int, max_value: int | None = None) -> int:
    """Read a positive integer environment variable."""

    raw = os.environ.get(name)
    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    if value <= 0:
        return default

    if max_value is not None and value > max_value:
        return max_value

    return value


def inline_code(value: str) -> str:
    """Return a Markdown inline-code representation safe for backticks.

    Background output mixes arbitrary strings from CI env vars and parsed
    manifests, so escape control characters before fencing.
    """

    return _inline_code(value, escape_controls=True)


def _safe_language_label(value: str) -> str:
    """Sanitize a user-supplied language label before pasting into the prompt.

    The label is interpolated verbatim into the Markdown review background
    that goes to the LLM. A malicious CI variable that contains newlines
    plus instructions (`English\\n\\nIgnore previous instructions...`)
    would inject those instructions as plain prompt text. Reject anything
    that is not a short, printable language name; fall back to the
    project default on invalid input.
    """

    raw = (value or "").strip()
    if not raw:
        return "Russian"

    # Allowlist of well-known language labels plus an explicit pattern
    # for BCP-47-style tags (e.g. `en`, `en-US`, `zh-Hans-CN`). This is
    # narrower than "ASCII words" because free text like
    # `English ignore previous instructions` is still a valid prompt
    # injection vector even after we strip newlines.
    KNOWN_LANGUAGES = {
        "english",
        "russian",
        "ukrainian",
        "german",
        "french",
        "spanish",
        "portuguese",
        "italian",
        "polish",
        "czech",
        "dutch",
        "swedish",
        "finnish",
        "norwegian",
        "danish",
        "japanese",
        "chinese",
        "korean",
        "turkish",
        "arabic",
        "hebrew",
        "hindi",
        "vietnamese",
        "thai",
        "indonesian",
        "english (us)",
        "english (uk)",
    }
    BCP47_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")

    lowered = raw.lower()
    if lowered in KNOWN_LANGUAGES or BCP47_RE.match(raw):
        return raw

    print(
        "OCR_REVIEW_LANGUAGE is not in allowlist and not a BCP-47 tag; falling back to Russian.",
        file=sys.stderr,
    )
    return "Russian"


def string_value(value: Any) -> str | None:
    """Return value only when it is already a string."""

    return value if isinstance(value, str) else None


def string_list_value(value: Any) -> list[str]:
    """Return only string items from a list-like manifest value."""

    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, str)]


def is_env_file(path: str) -> bool:
    """Return whether a repo path names an environment variable file."""

    name = Path(path).name.lower()
    return (
        name == ".env"
        or name.startswith((".env.", ".env-"))
        or ".env." in name
        or ".env-" in name
        or name.endswith(".env")
    )
