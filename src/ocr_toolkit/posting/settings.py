"""Environment-derived settings and limits for OCR posting."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
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


MAX_REVIEWER_GUIDE_COMMENTS = 6


MAX_REVIEWER_GUIDE_LABEL_CHARS = 80


MAX_REVIEWER_GUIDE_LOCATION_CHARS = 180


MAX_REVIEWER_GUIDE_TEXT_CHARS = 360


TRUNCATION_NOTICE = (
    "Output was truncated because the fallback note exceeded the safe GitLab note size. "
    "Check the CI logs or OCR output artifact for the complete result."
)


TRUE_BOOLEAN_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_BOOLEAN_VALUES = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True, slots=True)
class BooleanSetting:
    """One typed environment boolean and whether its source was valid."""

    enabled: bool
    valid: bool = True


def parse_boolean_setting(
    name: str,
    *,
    default: bool,
    invalid_default: bool,
) -> BooleanSetting:
    """Parse the shared boolean vocabulary without logging the raw value."""

    raw = getenv(name).strip().lower()
    if not raw:
        return BooleanSetting(default)
    if raw in TRUE_BOOLEAN_VALUES:
        return BooleanSetting(True)
    if raw in FALSE_BOOLEAN_VALUES:
        return BooleanSetting(False)
    print(
        f"{name} must be one of true/false, 1/0, yes/no, or on/off; "
        f"using {'enabled' if invalid_default else 'disabled'}.",
        file=sys.stderr,
    )
    return BooleanSetting(invalid_default, valid=False)


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

    return parse_boolean_setting("OCR_POST_EMOJI", default=True, invalid_default=True).enabled


@cache
def post_badges() -> str:
    """Return the finding metadata presentation mode."""

    mode = getenv("OCR_POST_BADGES", "text").strip().lower()
    if mode in {"text", "shields"}:
        return mode
    print("OCR_POST_BADGES must be text or shields; using text.", file=sys.stderr)
    return "text"


@cache
def auto_approve() -> BooleanSetting:
    """Return fail-closed automatic approval configuration."""

    return parse_boolean_setting("OCR_AUTO_APPROVE", default=True, invalid_default=False)


def strict_posting() -> bool:
    """Return whether posting failures should make this script fail."""

    return parse_boolean_setting("OCR_STRICT_POSTING", default=False, invalid_default=False).enabled


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
