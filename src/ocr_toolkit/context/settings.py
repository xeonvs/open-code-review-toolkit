"""Settings and small value helpers for OCR review context generation."""

from __future__ import annotations

import os
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
