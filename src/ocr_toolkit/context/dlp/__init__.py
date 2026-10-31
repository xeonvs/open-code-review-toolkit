"""Shared DLP facade; acquisition, storage and reporting belong to their callers."""

from ocr_toolkit.context.dlp.admission import (
    HTML_COMMENT_RE,
    HTML_TAG_RE,
    DLPResult,
    ForbiddenMatcher,
    ForbiddenValue,
    check_text,
    dlp_mode,
    normalize_text,
    resolve_dlp_enabled,
)
from ocr_toolkit.context.dlp.decoding import _html_decode as _html_decode
from ocr_toolkit.result_contract import FORBIDDEN_SOURCE_CLASSES

__all__ = [
    "FORBIDDEN_SOURCE_CLASSES",
    "HTML_COMMENT_RE",
    "HTML_TAG_RE",
    "DLPResult",
    "ForbiddenMatcher",
    "ForbiddenValue",
    "check_text",
    "dlp_mode",
    "normalize_text",
    "resolve_dlp_enabled",
]
