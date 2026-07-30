"""Markdown formatting for OCR findings and summary notes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from ocr_toolkit.common.markdown import (
    escape_control_chars,
    markdown_code_block,
    neutralize_quick_actions,
    neutralize_suggestion_fences,
)
from ocr_toolkit.common.markdown import (
    inline_code as _inline_code,
)
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.ocr_result import TOOLKIT_RESULT_SCHEMA_VERSION
from ocr_toolkit.posting.comments import (
    clean_text,
    code_text,
    comment_line,
    compact_control_text,
    compact_escaped_text,
    line_number,
)
from ocr_toolkit.posting.payloads import truncate_code_text, truncate_note_body
from ocr_toolkit.posting.settings import (
    FALLBACK_NOTE_CHUNK_BUDGET,
    MAX_FALLBACK_CODE_DETAILS_CHARS,
    MAX_REVIEWER_GUIDE_COMMENTS,
    MAX_REVIEWER_GUIDE_LABEL_CHARS,
    MAX_REVIEWER_GUIDE_LOCATION_CHARS,
    MAX_REVIEWER_GUIDE_TEXT_CHARS,
    MAX_SUGGESTION_CODE_CHARS,
    MAX_SUGGESTION_SPAN_LINES,
    MAX_TOOL_CALL_NAME_CHARS,
    MAX_TOOL_CALL_SUMMARY_TOOLS,
    SUGGESTION_HEADER,
    post_emoji,
    post_mode,
)

OCR_FINDING_CATEGORIES = {
    "bug",
    "security",
    "performance",
    "maintainability",
    "test",
    "style",
    "documentation",
    "other",
}

OCR_FINDING_SEVERITIES = {"critical", "high", "medium", "low"}
OCR_FINDING_SEVERITY_ORDER = ("critical", "high", "medium", "low")
OCR_FINDING_CATEGORY_ORDER = (
    "security",
    "bug",
    "performance",
    "maintainability",
    "test",
    "documentation",
    "style",
    "other",
)

SEVERITY_EMOJI = {
    "critical": "❌",
    "high": "🚨",
    "medium": "⚠️",
    "low": "ℹ️",  # noqa: RUF001 - intentional information emoji
}
CATEGORY_EMOJI = {
    "bug": "🐛",
    "security": "🔒",
    "performance": "⚡",
    "maintainability": "🛠️",
    "test": "🧪",
    "style": "🎨",
    "documentation": "📚",
    "other": "📌",
}


def suggestion_range_suffix(comment: dict[str, Any]) -> str:
    """Return a GitLab suggestion range suffix."""

    end_line = line_number(comment.get("end_line") or comment.get("line"))
    start_line = line_number(comment.get("start_line") or comment.get("line") or end_line)

    if start_line <= 0 or end_line <= 0 or start_line > end_line:
        return ""

    span = end_line - start_line
    if span > MAX_SUGGESTION_SPAN_LINES:
        return ""

    return f"-0+{span}"


def inline_code(value: str) -> str:
    """Return a Markdown inline-code representation safe for backticks."""

    return _inline_code(value, escape_controls=True)


def normalized_ocr_metadata(value: Any, allowed_values: set[str]) -> str:
    """Return a whitelisted OCR metadata value suitable for display."""

    text = clean_text(value).casefold()
    return text if text in allowed_values else ""


def finding_metadata(comment: dict[str, Any]) -> tuple[str, str]:
    """Return structured OCR category/severity metadata from a finding."""

    severity = normalized_ocr_metadata(
        comment.get("severity"), OCR_FINDING_SEVERITIES
    ) or normalized_ocr_metadata(comment.get("priority"), OCR_FINDING_SEVERITIES)
    category = normalized_ocr_metadata(comment.get("category"), OCR_FINDING_CATEGORIES)
    return severity, category


def format_finding_tags(comment: dict[str, Any], *, emoji: bool | None = None) -> str:
    """Return GitLab-visible tags for structured OCR finding metadata."""

    severity, category = finding_metadata(comment)
    tags = []
    use_emoji = post_emoji() if emoji is None else emoji
    if severity:
        prefix = f"{SEVERITY_EMOJI[severity]} " if use_emoji else ""
        tags.append(prefix + inline_code(f"severity:{severity}"))
    if category:
        prefix = f"{CATEGORY_EMOJI[category]} " if use_emoji else ""
        tags.append(prefix + inline_code(f"category:{category}"))
    return f"**OCR tags:** {' '.join(tags)}" if tags else ""


def format_suggestion_block(comment: dict[str, Any]) -> str:
    """Return a GitLab suggestion block if OCR supplied replacement code."""

    suggestion = code_text(comment.get("suggestion_code"))
    if not suggestion.strip():
        return ""

    if "```" in suggestion:
        return ""

    if any(line.lstrip().startswith("/") for line in suggestion.splitlines()):
        return ""

    if len(suggestion) > MAX_SUGGESTION_CODE_CHARS:
        return (
            "\n\nSuggestion block was omitted because the generated replacement "
            "was too large to publish safely."
        )

    range_suffix = suggestion_range_suffix(comment)
    if not range_suffix:
        return ""

    return f"\n\n{SUGGESTION_HEADER}\n```suggestion:{range_suffix}\n{suggestion}\n```"


def format_inline_comment(
    comment: dict[str, Any], include_suggestion: bool = True, *, emoji: bool | None = None
) -> str:
    """Format one OCR comment as Markdown for an inline GitLab discussion."""

    raw_content = clean_text(comment.get("content")) or "Open Code Review reported an issue here."
    content = neutralize_suggestion_fences(neutralize_quick_actions(raw_content))
    content = "\n".join(escape_control_chars(line) for line in content.split("\n"))
    tags = format_finding_tags(comment, emoji=emoji)
    body = f"{tags}\n\n{content}" if tags else content
    if include_suggestion:
        body += format_suggestion_block(comment)

    return body


def format_fallback_comment(comment: dict[str, Any], *, emoji: bool | None = None) -> str:
    """Format an OCR comment for a fallback non-inline MR note."""

    path = clean_text(comment.get("path")) or "unknown"
    # Parse line fields as integers. Without this a malformed OCR
    # payload (`"line": "10\n/quickaction"`) would inject a new
    # Markdown heading line into the fallback note.
    start_line = line_number(comment.get("start_line") or comment.get("line"))
    end_line = line_number(comment.get("end_line") or comment.get("line"))

    location = ""
    if start_line > 0 and end_line > 0 and start_line <= end_line:
        location = f" L{start_line}" if start_line == end_line else f" L{start_line}-L{end_line}"
    elif end_line > 0:
        location = f" L{end_line}"
    elif start_line > 0:
        location = f" L{start_line}"

    safe_path = _inline_code(path, escape_controls=True)
    body = (
        f"### {safe_path}{location}\n\n"
        f"{format_inline_comment(comment, include_suggestion=False, emoji=emoji)}"
    )

    existing = code_text(comment.get("existing_code"))
    suggestion = code_text(comment.get("suggestion_code"))

    if existing.strip() and suggestion.strip():
        body += "\n\n<details><summary>Suggested change details</summary>\n\n"
        body += "**Before:**\n"
        body += markdown_code_block(
            "text",
            neutralize_quick_actions(truncate_code_text(existing, MAX_FALLBACK_CODE_DETAILS_CHARS)),
        )
        body += "\n\n"

        body += "**After:**\n"
        body += markdown_code_block(
            "text",
            neutralize_quick_actions(
                truncate_code_text(suggestion, MAX_FALLBACK_CODE_DETAILS_CHARS)
            ),
        )
        body += "\n\n"
        body += "</details>"

    return body


def format_fallback_comment_chunks(
    comments: Sequence[dict[str, Any]], *, emoji: bool | None = None
) -> list[str]:
    """Split fallback comments into safe chunks before publishing MR notes."""

    chunks: list[str] = []
    current = ""

    for comment in comments:
        item = truncate_note_body(
            format_fallback_comment(comment, emoji=emoji), max_chars=FALLBACK_NOTE_CHUNK_BUDGET
        )
        separator = "\n\n---\n\n" if current else ""

        if current and len(current) + len(separator) + len(item) > FALLBACK_NOTE_CHUNK_BUDGET:
            chunks.append(current)
            current = item
        else:
            current += separator + item

    if current:
        chunks.append(current)

    return chunks


def format_omitted_comments_summary(
    publishable_total: int, publish_limit: int, omitted: int
) -> str:
    """Return a bounded note body for comments omitted by the publish cap."""

    return (
        "**Open Code Review omitted comments**\n\n"
        f"After reviewer suppression filters, Open Code Review has "
        f"{publishable_total} publishable comment(s). This CI job publishes "
        f"at most {publish_limit} comment(s) per run. The remaining {omitted} "
        "comment(s) were "
        "omitted to avoid excessive GitLab API calls and MR noise. Raise "
        "`OCR_MAX_POST_COMMENTS` deliberately and rerun if more comments need "
        "to be expanded in the MR."
    )


def format_metadata_counts(
    comments: Sequence[dict[str, Any]], field: str, ordered_values: Sequence[str]
) -> str:
    """Return compact counts for structured OCR finding metadata."""

    allowed = set(ordered_values)
    counts: dict[str, int] = {}
    for comment in comments:
        severity, category = finding_metadata(comment)
        value = severity if field == "severity" else category
        if value in allowed:
            counts[value] = counts.get(value, 0) + 1

    parts = [
        f"{inline_code(value)}: {counts[value]}"
        for value in ordered_values
        if counts.get(value, 0) > 0
    ]
    return ", ".join(parts)


def nonnegative_int(value: Any) -> int | None:
    """Parse a non-negative integer from OCR JSON, ignoring malformed values."""

    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float):
        if value.is_integer() and value >= 0:
            return int(value)
        return None

    if isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            return None
        return parsed if parsed >= 0 else None

    return None


def truncate_tool_call_name(name: str) -> str:
    """Return a compact tool name for one-line MR summaries."""

    if len(name) <= MAX_TOOL_CALL_NAME_CHARS:
        return name

    return name[: MAX_TOOL_CALL_NAME_CHARS - 3].rstrip() + "..."


def tool_call_name(value: Any) -> str:
    """Extract a displayable tool name from common OCR tool-call shapes."""

    if isinstance(value, str):
        return clean_text(value)

    if not isinstance(value, dict):
        return ""

    for key in ("name", "tool", "tool_name"):
        name = clean_text(value.get(key))
        if name:
            return name

    function_value = value.get("function")
    if isinstance(function_value, dict):
        return clean_text(function_value.get("name"))

    return ""


def tool_call_counts_from_items(
    items: list[Any],
) -> tuple[int | None, list[tuple[str, int]]]:
    """Summarize a list-style OCR tool_calls payload."""

    counts: dict[str, int] = {}
    for item in items:
        name = tool_call_name(item)
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1

    total = sum(counts.values())
    if total == 0 and items:
        return None, []

    return total, list(counts.items())


def format_tool_calls_summary(tool_calls: Any) -> str:
    """Return one bounded MR summary line for OCR tool-call statistics."""

    entries: list[tuple[str, int]]
    total: int | None
    scalar_total = nonnegative_int(tool_calls)
    if scalar_total is not None:
        total = scalar_total
        entries = []
    elif isinstance(tool_calls, list):
        total, entries = tool_call_counts_from_items(tool_calls)
    elif isinstance(tool_calls, dict):
        by_tool_value = tool_calls.get("by_tool")
        entries = []
        by_tool_total = 0
        valid_by_tool_count = False

        if isinstance(by_tool_value, dict):
            for raw_name, raw_count in by_tool_value.items():
                count = nonnegative_int(raw_count)
                if count is None:
                    continue
                name = clean_text(raw_name)
                if not name:
                    continue
                valid_by_tool_count = True
                by_tool_total += count
                if count > 0:
                    entries.append((name, count))

        calls_value = tool_calls.get("calls")
        if valid_by_tool_count:
            list_total = None
        elif isinstance(calls_value, list):
            list_total, entries = tool_call_counts_from_items(calls_value)
        else:
            list_total = None

        total = nonnegative_int(tool_calls.get("total"))
        if total is None:
            if valid_by_tool_count:
                total = by_tool_total
            elif list_total is not None:
                total = list_total
            elif by_tool_value == {}:
                total = 0
            else:
                return ""
    else:
        return ""

    if total is None:
        return ""
    if total == 0:
        return ""

    line = f"- tool calls: {total} total"
    if not entries:
        return line

    entries.sort(key=lambda item: (-item[1], item[0]))
    shown_entries = entries[:MAX_TOOL_CALL_SUMMARY_TOOLS]
    detail_parts = [
        f"{inline_code(truncate_tool_call_name(name))}: {count}" for name, count in shown_entries
    ]
    omitted_entries = len(entries) - len(shown_entries)
    if omitted_entries > 0:
        detail_parts.append(f"+{omitted_entries} more")

    return f"{line} ({', '.join(detail_parts)})"


def format_mcp_usage_summary(toolkit_metadata: Any) -> str:
    """Report MCP servers from the safe receipt produced by `ocr-ci review`."""

    if (
        not isinstance(toolkit_metadata, dict)
        or toolkit_metadata.get("schema_version") != TOOLKIT_RESULT_SCHEMA_VERSION
    ):
        return ""
    mcp_usage = toolkit_metadata.get("mcp_usage")
    if not isinstance(mcp_usage, dict):
        return ""
    used: list[tuple[str, int]] = []
    for raw_server, raw_count in sorted(mcp_usage.items()):
        server = clean_text(raw_server)
        count = nonnegative_int(raw_count)
        if not server or count is None or count <= 0:
            continue
        used.append((server, count))
    if not used:
        return ""
    details = ", ".join(f"{inline_code(server)}: {count}" for server, count in used)
    return f"- MCP used: {len(used)} server(s) ({details})"


TOKEN_USAGE_KEYS = (
    "usage",
    "token_usage",
    "tokenUsage",
    "token_usage_summary",
    "tokenUsageSummary",
)


TOKEN_USAGE_CONTAINER_KEYS = (
    *TOKEN_USAGE_KEYS,
    "summary",
    "project_summary",
    "metadata",
    "stats",
    "statistics",
)


TOKEN_TOTAL_KEYS = ("total_tokens", "totalTokens", "tokens", "total")


TOKEN_EXPLICIT_TOTAL_KEYS = ("total_tokens", "totalTokens", "tokens")


TOKEN_PROMPT_KEYS = (
    "prompt_tokens",
    "input_tokens",
    "promptTokens",
    "inputTokens",
    "prompt",
    "input",
)


TOKEN_COMPLETION_KEYS = (
    "completion_tokens",
    "output_tokens",
    "completionTokens",
    "outputTokens",
    "completion",
    "output",
)


TOKEN_CACHED_KEYS = (
    "cached_tokens",
    "cache_read_input_tokens",
    "cachedInputTokens",
    "cacheReadInputTokens",
)


def first_nonnegative_int(mapping: dict[str, Any], keys: Sequence[str]) -> int | None:
    """Return the first non-negative integer from known OCR usage keys."""

    for key in keys:
        value = nonnegative_int(mapping.get(key))
        if value is not None:
            return value
    return None


def token_usage_mapping(
    value: Any, max_depth: int = 8, *, explicit_container: bool = False
) -> dict[str, Any] | None:
    """Find the first dict-shaped token usage object in OCR result metadata."""

    if max_depth <= 0:
        return None

    if isinstance(value, dict):
        if any(
            key in value
            for key in (TOKEN_TOTAL_KEYS if explicit_container else TOKEN_EXPLICIT_TOTAL_KEYS)
            + TOKEN_PROMPT_KEYS
            + TOKEN_COMPLETION_KEYS
            + TOKEN_CACHED_KEYS
        ):
            return value
        for key in TOKEN_USAGE_CONTAINER_KEYS:
            nested = value.get(key)
            if isinstance(nested, dict):
                found = token_usage_mapping(
                    nested,
                    max_depth=max_depth - 1,
                    explicit_container=key in TOKEN_USAGE_KEYS,
                )
                if found is not None:
                    return found
    return None


def format_token_usage_summary(result: dict[str, Any]) -> str:
    """Return one bounded MR summary line for structured OCR token usage."""

    usage = token_usage_mapping(result)
    if usage is None:
        return ""

    total = first_nonnegative_int(usage, TOKEN_TOTAL_KEYS)
    prompt = first_nonnegative_int(usage, TOKEN_PROMPT_KEYS)
    completion = first_nonnegative_int(usage, TOKEN_COMPLETION_KEYS)
    cached = first_nonnegative_int(usage, TOKEN_CACHED_KEYS)

    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)
    if total is None and cached is not None:
        total = cached
    if total is None:
        return ""

    details: list[str] = []
    if prompt is not None:
        details.append(f"prompt: {prompt}")
    if completion is not None:
        details.append(f"completion: {completion}")
    if cached is not None:
        details.append(f"cached: {cached}")

    line = f"- token usage: {total} total"
    if details:
        line += f" ({', '.join(details)})"
    return line


SECURITY_SIGNAL_RE = re.compile(
    r"(?i)\b("
    r"security|credential|secret|token|password|private[_ -]?token|"
    r"client[_ -]?secret|api[_ -]?key|authorization|auth|"
    r"injection|xss|csrf|ssrf|rce|path traversal|host header|"
    r"privilege|permission|access control|vault|leak"
    r")\b"
)


HIGH_SIGNAL_RE = re.compile(r"(?i)\b(high|critical|blocker|security)\b")


def comment_signal_text(comment: dict[str, Any]) -> str:
    """Return fields useful for conservative guide classification."""

    values = [
        clean_text(comment.get("priority") or comment.get("severity")),
        clean_text(comment.get("category")),
        clean_text(comment.get("rule_id")),
        clean_text(comment.get("content")),
    ]
    return "\n".join(value for value in values if value)


def comment_has_security_signal(comment: dict[str, Any]) -> bool:
    """Return true only when OCR text explicitly carries security wording."""

    return bool(SECURITY_SIGNAL_RE.search(comment_signal_text(comment)))


def comment_is_high_signal(comment: dict[str, Any]) -> bool:
    """Return true for explicit high/critical/security OCR metadata."""

    return bool(HIGH_SIGNAL_RE.search(comment_signal_text(comment)))


def estimate_review_effort(comments: Sequence[dict[str, Any]], omitted_count: int) -> int:
    """Estimate review effort from visible OCR findings without inventing context."""

    total = len(comments) + omitted_count
    if total <= 0:
        return 1

    security_count = sum(1 for comment in comments if comment_has_security_signal(comment))
    high_count = sum(1 for comment in comments if comment_is_high_signal(comment))

    if total <= 2 and security_count == 0 and high_count == 0:
        return 1
    if total <= 5 and high_count <= 1 and security_count <= 1:
        return 2
    if total <= 10:
        return 3
    if total <= 25:
        return 4
    return 5


def guide_comment_label(comment: dict[str, Any]) -> str:
    """Return compact severity/category label for the reviewer guide."""

    parts = [
        clean_text(comment.get("priority") or comment.get("severity")),
        clean_text(comment.get("category")),
    ]
    parts = [part for part in parts if part]
    if not parts:
        return "review finding"
    return _inline_code(
        compact_control_text(", ".join(parts[:2]), MAX_REVIEWER_GUIDE_LABEL_CHARS),
    )


def guide_comment_location(comment: dict[str, Any]) -> str:
    """Return a compact path/line label for the reviewer guide."""

    path = clean_text(comment.get("path")) or "unknown"
    line = comment_line(comment)
    location = f"{path}:L{line}" if line > 0 else path
    location = compact_control_text(location, MAX_REVIEWER_GUIDE_LOCATION_CHARS)
    return _inline_code(location)


def guide_comment_snippet(comment: dict[str, Any]) -> str:
    """Return one Markdown-neutral summary snippet for an OCR finding."""

    content = neutralize_suggestion_fences(
        neutralize_quick_actions(clean_text(comment.get("content")))
    )
    excerpt = compact_escaped_text(content, MAX_REVIEWER_GUIDE_TEXT_CHARS)
    if not excerpt:
        return "Open Code Review reported an issue here."

    return excerpt


def format_reviewer_guide(comments: Sequence[dict[str, Any]], omitted_count: int) -> str:
    """Build a bounded reviewer guide from already published OCR findings."""

    if not comments and omitted_count <= 0:
        return ""

    effort = estimate_review_effort(comments, omitted_count)
    security_comments = [comment for comment in comments if comment_has_security_signal(comment)]

    lines = [""]
    if security_comments:
        lines.append("## Security review focus")
        lines.append(
            f"- **Security signal:** {len(security_comments)} published OCR finding(s) explicitly mention security-sensitive terms."
        )
        lines.append(
            "- Prioritize these findings before ordinary reliability or maintainability items."
        )

    lines.extend(
        [
            "",
            "## Reviewer guide",
            f"- Estimated effort to review: {effort}/5",
        ]
    )

    if not security_comments and omitted_count:
        lines.append(
            "- Security signal: none in published OCR findings; omitted findings were not inspected for this guide."
        )
    elif not security_comments:
        lines.append(
            "- Security signal: no security-sensitive findings detected in the published OCR comments."
        )

    if omitted_count:
        lines.append(
            f"- Visibility: {omitted_count} finding(s) omitted by `OCR_MAX_POST_COMMENTS`; rerun with a higher limit if needed."
        )

    guide_comments = list(comments[:MAX_REVIEWER_GUIDE_COMMENTS])
    if guide_comments:
        lines.append("")
        lines.append("### Recommended focus areas")
        lines.append(
            "These are abbreviated navigation snippets; read the posted inline or fallback OCR discussions for the full findings."
        )
        for comment in guide_comments:
            lines.append(
                f"- {guide_comment_label(comment)}; affected path: "
                f"{guide_comment_location(comment)}; snippet: {guide_comment_snippet(comment)}"
            )

        remaining = len(comments) - len(guide_comments)
        if remaining > 0:
            lines.append(f"- ... and {remaining} more published finding(s).")

    return "\n".join(lines)


def summarize_result(
    total: int,
    inline_count: int,
    fallback_count: int,
    warning_count: int,
    *,
    comments: Sequence[dict[str, Any]] = (),
    omitted_count: int = 0,
    tool_calls_summary: str = "",
    mcp_usage_summary: str = "",
    token_usage_summary: str = "",
    reviewer_guide: str = "",
    fallback_reasons: Mapping[str, int] | None = None,
    reviewed_sha: str = "",
    mr_head_sha: str = "",
    outcome_status: str = "success",
    outcome_message: str = "",
    emoji: bool | None = None,
) -> str:
    """Build a compact summary note for the MR."""

    use_emoji = post_emoji() if emoji is None else emoji
    status_markers = {
        "success": "✅",
        "skipped": "ℹ️",  # noqa: RUF001 - intentional information emoji
        "completed_with_warnings": "⚠️",
        "completed_with_errors": "❌",
    }
    marker = f"{status_markers.get(outcome_status, '❌')} " if use_emoji else ""
    safe_message = neutralize_quick_actions(
        compact_control_text(redact_sensitive(outcome_message), max_chars=500)
    )
    if not safe_message:
        safe_message = f"Found {total} issue(s)." if total else "No issues found."
    lines = [
        "# Open Code Review summary",
        f"{marker}{safe_message}",
        "",
        f"- posting mode: `{post_mode()}`",
    ]
    if inline_count:
        lines.append(f"- {inline_count} posted as inline discussion(s)")
    if fallback_count:
        lines.append(f"- {fallback_count} posted as fallback summary item(s)")

    if reviewed_sha:
        lines.append(f"- reviewed SHA: {_inline_code(reviewed_sha)}")
    if mr_head_sha and mr_head_sha != reviewed_sha:
        lines.append(f"- MR head SHA: {_inline_code(mr_head_sha)}")

    severity_counts = format_metadata_counts(comments, "severity", OCR_FINDING_SEVERITY_ORDER)
    if severity_counts:
        lines.append(f"- severity tags: {severity_counts}")

    category_counts = format_metadata_counts(comments, "category", OCR_FINDING_CATEGORY_ORDER)
    if category_counts:
        lines.append(f"- category tags: {category_counts}")

    if fallback_reasons:
        reason_parts = [
            f"{_inline_code(reason)}: {count}"
            for reason, count in sorted(fallback_reasons.items())
            if count > 0
        ]
        if reason_parts:
            lines.append(f"- fallback reasons: {', '.join(reason_parts)}")

    if omitted_count:
        lines.append(f"- {omitted_count} omitted by `OCR_MAX_POST_COMMENTS`")

    if warning_count:
        lines.append(f"- {warning_count} warning(s) reported by OCR")

    if tool_calls_summary:
        lines.append(tool_calls_summary)

    if mcp_usage_summary:
        lines.append(mcp_usage_summary)

    if token_usage_summary:
        lines.append(token_usage_summary)

    if reviewer_guide:
        lines.append(reviewer_guide)

    return "\n".join(lines)
