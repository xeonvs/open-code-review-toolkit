"""GitLab note payload size limiting and marker wrapping."""

from __future__ import annotations

from ocr_toolkit.common.markdown import markdown_code_block
from ocr_toolkit.posting.markers import build_marker
from ocr_toolkit.posting.settings import (
    MAX_INLINE_NOTE_CHARS,
    MAX_NOTE_CHARS,
    SUGGESTION_BLOCK_RE,
    TRUNCATION_NOTICE,
)


def _fits_limit(text: str, max_chars: int) -> bool:
    return len(text) <= max_chars and len(text.encode("utf-8")) <= max_chars


def _utf8_prefix(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")


def truncate_note_body(body: str, max_chars: int = MAX_NOTE_CHARS) -> str:
    """Truncate a GitLab note body without splitting Markdown structures."""

    if _fits_limit(body, max_chars):
        return body

    notice = f"{TRUNCATION_NOTICE}\n\nRaw Markdown excerpt follows."
    budget = max(0, max_chars - len(notice.encode("utf-8")) - 2)
    excerpt = _utf8_prefix(body, budget).rstrip()

    while excerpt:
        result = f"{notice}\n\n{markdown_code_block('markdown', excerpt)}"
        if _fits_limit(result, max_chars):
            return result

        overflow = max(len(result) - max_chars, len(result.encode("utf-8")) - max_chars)
        excerpt = _utf8_prefix(
            excerpt, max(0, len(excerpt.encode("utf-8")) - overflow - 1)
        ).rstrip()

    return notice[:max_chars]


def truncate_plain_text(text: str, max_chars: int) -> str:
    """Truncate plain text with a short notice."""

    if _fits_limit(text, max_chars):
        return text

    notice = "\n\nText was truncated before publishing to GitLab."
    if max_chars <= len(notice.encode("utf-8")):
        return _utf8_prefix(notice, max_chars)

    budget = max(0, max_chars - len(notice.encode("utf-8")))
    return _utf8_prefix(text, budget).rstrip() + notice


def truncate_code_text(text: str, max_chars: int) -> str:
    """Truncate code text while preserving indentation as much as possible."""

    if max_chars <= 0:
        return ""

    if _fits_limit(text, max_chars):
        return text

    notice = "\n# ... truncated before publishing to GitLab ..."
    if max_chars <= len(notice.encode("utf-8")):
        return _utf8_prefix(notice, max_chars)

    budget = max(0, max_chars - len(notice.encode("utf-8")))
    return _utf8_prefix(text, budget).rstrip("\n") + notice


def limit_inline_body(body: str, max_chars: int = MAX_INLINE_NOTE_CHARS) -> str:
    """Limit inline discussion body without breaking GitLab suggestion blocks.

    If the inline body is too large, drop the suggestion block first. If the
    plain body is still too large, truncate it as plain Markdown text.
    """

    if _fits_limit(body, max_chars):
        return body

    match = SUGGESTION_BLOCK_RE.search(body)
    if match:
        body_without_suggestion = body[: match.start()] + (
            "\n\nSuggestion block was omitted because the inline comment exceeded "
            "the safe GitLab note size."
        )
        if _fits_limit(body_without_suggestion, max_chars):
            return body_without_suggestion

        body = body_without_suggestion

    return truncate_plain_text(body, max_chars)


def limit_regular_note_body(body: str, max_chars: int = MAX_NOTE_CHARS) -> str:
    """Limit a regular MR note body before calling the GitLab API."""

    return truncate_note_body(body, max_chars=max_chars)


def note_body_budget(max_chars: int, fingerprint: str | None = None) -> int:
    """Return the body budget after reserving space for the bot marker."""

    return max(0, max_chars - len(build_marker(fingerprint)) - 1)


def build_marked_note_body(
    body: str,
    *,
    fingerprint: str | None = None,
    max_chars: int = MAX_NOTE_CHARS,
    inline: bool = False,
) -> str:
    """Build the exact GitLab note payload, including marker and size limit."""

    marker = build_marker(fingerprint)
    if max_chars < len(marker) + 1:
        raise ValueError("GitLab note payload budget is too small for OCR marker")

    budget = note_body_budget(max_chars, fingerprint)
    limited_body = (
        limit_inline_body(body, max_chars=budget)
        if inline
        else limit_regular_note_body(body, max_chars=budget)
    )
    payload = f"{marker}\n{limited_body}"
    if _fits_limit(payload, max_chars):
        return payload

    # Defensive fallback: the limiting helpers should already respect
    # the marker-aware budget, but never send an over-limit API payload.
    limited_body = truncate_plain_text(limited_body, budget)
    return f"{marker}\n{limited_body}"
