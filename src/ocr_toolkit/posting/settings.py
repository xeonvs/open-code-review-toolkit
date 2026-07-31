"""Environment-derived settings and limits for OCR posting."""

from __future__ import annotations

import os
import re
import sys
from functools import cache

from ocr_toolkit.ocr_result import (  # noqa: F401 -- retained import contract
    DEFAULT_MAX_RESULT_BYTES,
    MAX_RESULT_BYTES_HARD_LIMIT,
    max_result_bytes,
)

SUGGESTION_HEADER = "**Suggestion:**"


SUGGESTION_BLOCK_RE = re.compile(r"\n\n" + re.escape(SUGGESTION_HEADER) + r"\n`{3,}suggestion[:\n]")


DEFAULT_HTTP_TIMEOUT_SECONDS = 25


MAX_NOTE_CHARS = 55_000


MAX_INLINE_NOTE_CHARS = 20_000


MAX_API_ERROR_BODY_BYTES = 64 * 1024


MAX_API_RESPONSE_BODY_BYTES = MAX_NOTE_CHARS * 120


MAX_SUGGESTION_CODE_CHARS = 12_000


MAX_FALLBACK_CODE_DETAILS_CHARS = 20_000


FALLBACK_NOTE_CHUNK_BUDGET = MAX_NOTE_CHARS - 1_000


MAX_SUGGESTION_SPAN_LINES = 200


DEFAULT_MAX_POST_COMMENTS = 50


MAX_POST_COMMENTS_HARD_LIMIT = 200


MAX_TOOL_CALL_SUMMARY_TOOLS = 6


MAX_TOOL_CALL_NAME_CHARS = 48


MAX_REVIEWER_GUIDE_COMMENTS = 6


MAX_REVIEWER_GUIDE_LABEL_CHARS = 80


MAX_REVIEWER_GUIDE_LOCATION_CHARS = 180


MAX_REVIEWER_GUIDE_TEXT_CHARS = 360


TRUNCATION_NOTICE = (
    "Output was truncated because the fallback note exceeded the safe GitLab note size. "
    "Check the CI logs or OCR output artifact for the complete result."
)


def getenv(name: str, default: str = "") -> str:
    """Return an environment variable or a default string."""

    return os.environ.get(name, default)


@cache
def post_mode() -> str:
    """Return posting mode.

    Defaults to draft mode. The old direct mode is retained as an emergency
    override via OCR_POST_MODE=direct, but no CI variable is required.
    """

    raw_mode = getenv("OCR_POST_MODE", "draft").strip()
    mode = raw_mode.lower()
    if mode in {"draft", "direct"}:
        return mode
    print("Invalid OCR_POST_MODE value; using draft mode.", file=sys.stderr)
    return "draft"


@cache
def post_emoji() -> bool:
    """Return whether toolkit-added status and finding emoji are enabled."""

    value = getenv("OCR_POST_EMOJI", "true").strip().lower()
    if not value:
        value = "true"
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    print("OCR_POST_EMOJI must be boolean; using enabled by default.", file=sys.stderr)
    return True


def strict_posting() -> bool:
    """Return whether posting failures should make this script fail."""

    return getenv("OCR_STRICT_POSTING", "false").strip().lower() in {"1", "true", "yes"}


def max_post_comments() -> int:
    """Return the maximum number of OCR comments to publish individually."""

    raw = getenv("OCR_MAX_POST_COMMENTS", str(DEFAULT_MAX_POST_COMMENTS)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        print(
            f"OCR_MAX_POST_COMMENTS is not an integer; using default {DEFAULT_MAX_POST_COMMENTS}.",
            file=sys.stderr,
        )
        return DEFAULT_MAX_POST_COMMENTS

    if parsed < 0:
        print(
            "OCR_MAX_POST_COMMENTS must be zero or greater; "
            f"using default {DEFAULT_MAX_POST_COMMENTS}.",
            file=sys.stderr,
        )
        return DEFAULT_MAX_POST_COMMENTS

    if parsed > MAX_POST_COMMENTS_HARD_LIMIT:
        print(
            f"OCR_MAX_POST_COMMENTS exceeds hard limit {MAX_POST_COMMENTS_HARD_LIMIT}; "
            f"using {MAX_POST_COMMENTS_HARD_LIMIT}.",
            file=sys.stderr,
        )
        return MAX_POST_COMMENTS_HARD_LIMIT

    return parsed


def ocr_exit_code() -> int:
    """Return OCR process exit code passed by CI."""

    raw = getenv("OCR_EXIT_CODE", "0").strip()
    try:
        return int(raw)
    except ValueError:
        print(
            "OCR_EXIT_CODE is not an integer; treating as failure (1).",
            file=sys.stderr,
        )
        return 1
