"""Markdown formatting for OCR findings and summary notes."""

from __future__ import annotations

import json
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
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    MAX_TOOLKIT_MCP_USAGE_SERVERS,
    PUBLIC_REVIEW_TOOL_CALL_NAMES,
    SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS,
    TOOLKIT_MCP_SERVER_NAME_RE,
    OcrToolkitAdvisory,
)
from ocr_toolkit.posting.approval import (
    ApprovalResult,
    approval_summary_line,
    publication_dlp_state,
)
from ocr_toolkit.posting.comments import (
    clean_text,
    code_text,
    comment_line,
    compact_control_text,
    compact_escaped_text,
    line_number,
)
from ocr_toolkit.posting.payloads import truncate_code_text, truncate_note_body
from ocr_toolkit.posting.result import CoverageDiagnostics, ocr_warning_text
from ocr_toolkit.posting.settings import (
    FALLBACK_NOTE_CHUNK_BUDGET,
    MAX_FALLBACK_CODE_DETAILS_CHARS,
    MAX_REVIEWER_GUIDE_COMMENTS,
    MAX_REVIEWER_GUIDE_LABEL_CHARS,
    MAX_REVIEWER_GUIDE_LOCATION_CHARS,
    MAX_REVIEWER_GUIDE_TEXT_CHARS,
    SUGGESTION_HEADER,
    post_badges,
    post_emoji,
    post_mode,
)
from ocr_toolkit.posting.suggestions import (
    SuggestionDecision,
    SuggestionState,
    safe_repository_path,
)
from ocr_toolkit.result_usage import normalize_token_usage

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

SHIELDS_BADGE_BASE_URL = "https://img.shields.io/badge"
SHIELDS_SEVERITY_COLORS = {
    "critical": "darkred",
    "high": "red",
    "medium": "orange",
    "low": "green",
}
SHIELDS_CATEGORY_COLOR = "blue"


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


def _finding_badge_label(*, severity: str, category: str) -> str:
    """Return a compact label built only from normalized closed enums."""

    return " · ".join(value for value in (category, severity) if value)


def _format_shields_badge(*, severity: str, category: str) -> str:
    """Project normalized metadata into one fixed-host static image badge."""

    label = _finding_badge_label(severity=severity, category=category)
    if not label:
        return ""
    if category and severity:
        path_label = f"{category}-{severity}"
    elif category:
        path_label = f"category-{category}"
    else:
        path_label = f"severity-{severity}"
    color = SHIELDS_SEVERITY_COLORS.get(severity, SHIELDS_CATEGORY_COLOR)
    return f"![{label}]({SHIELDS_BADGE_BASE_URL}/{path_label}-{color})"


def format_finding_tags(
    comment: dict[str, Any],
    *,
    emoji: bool | None = None,
    badge_mode: str | None = None,
) -> str:
    """Return GitLab-visible metadata for one structured OCR finding."""

    severity, category = finding_metadata(comment)
    mode = post_badges() if badge_mode is None else badge_mode
    if mode == "shields":
        return _format_shields_badge(severity=severity, category=category)
    tags = []
    if severity:
        tags.append(f"**Severity:** {inline_code(severity)}")
    if category:
        tags.append(f"**Category:** {inline_code(category)}")
    return " · ".join(tags)


def format_suggestion_block(decision: SuggestionDecision) -> str:
    """Render one previously validated GitLab suggestion decision."""

    if decision.state in {SuggestionState.ABSENT, SuggestionState.NO_OP}:
        return ""
    if decision.state is SuggestionState.OMITTED:
        return f"\n\nSuggestion block was omitted because {decision.omission_message}."
    return (
        f"\n\n{SUGGESTION_HEADER}\n```suggestion:{decision.range_suffix}\n"
        f"{decision.replacement}\n```"
    )


def format_suggestion_omission(decision: SuggestionDecision) -> str:
    """Render a bounded explanation for a withheld actionable suggestion."""

    if decision.state is not SuggestionState.OMITTED:
        return ""
    return f"\n\nSuggestion block was omitted because {decision.omission_message}."


def format_inline_comment(
    comment: dict[str, Any],
    include_suggestion: bool = True,
    *,
    suggestion_decision: SuggestionDecision | None = None,
    emoji: bool | None = None,
    badge_mode: str | None = None,
) -> str:
    """Format one OCR comment as Markdown for an inline GitLab discussion."""

    raw_content = clean_text(comment.get("content")) or "Open Code Review reported an issue here."
    content = neutralize_suggestion_fences(neutralize_quick_actions(raw_content))
    content = "\n".join(escape_control_chars(line) for line in content.split("\n"))
    tags = format_finding_tags(comment, emoji=emoji, badge_mode=badge_mode)
    body = f"{tags}\n\n{content}" if tags else content
    if include_suggestion:
        body += format_suggestion_block(
            suggestion_decision or SuggestionDecision(SuggestionState.ABSENT)
        )

    return body


def format_fallback_comment(
    comment: dict[str, Any],
    *,
    suggestion_decision: SuggestionDecision | None = None,
    emoji: bool | None = None,
    badge_mode: str | None = None,
) -> str:
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
        f"{format_inline_comment(comment, include_suggestion=False, emoji=emoji, badge_mode=badge_mode)}"
    )

    decision = suggestion_decision or SuggestionDecision(SuggestionState.ABSENT)
    body += format_suggestion_omission(decision)

    existing = code_text(comment.get("existing_code"))
    suggestion = code_text(comment.get("suggestion_code"))

    if existing.strip() and suggestion.strip() and decision.state is not SuggestionState.NO_OP:
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
    comments: Sequence[tuple[dict[str, Any], SuggestionDecision]],
    *,
    emoji: bool | None = None,
    badge_mode: str | None = None,
) -> list[str]:
    """Split fallback comments into safe chunks before publishing MR notes."""

    chunks: list[str] = []
    current = ""

    for comment, suggestion_decision in comments:
        item = truncate_note_body(
            format_fallback_comment(
                comment,
                suggestion_decision=suggestion_decision,
                emoji=emoji,
                badge_mode=badge_mode,
            ),
            max_chars=FALLBACK_NOTE_CHUNK_BUDGET,
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


def tool_call_name(value: Any) -> str:
    """Extract one closed public tool name from common OCR call shapes."""

    if isinstance(value, str):
        name = clean_text(value)
        return name if name in PUBLIC_REVIEW_TOOL_CALL_NAMES else ""

    if not isinstance(value, dict):
        return ""

    for key in ("name", "tool", "tool_name"):
        name = clean_text(value.get(key))
        if name in PUBLIC_REVIEW_TOOL_CALL_NAMES:
            return name

    function_value = value.get("function")
    if isinstance(function_value, dict):
        name = clean_text(function_value.get("name"))
        return name if name in PUBLIC_REVIEW_TOOL_CALL_NAMES else ""

    return ""


def tool_call_counts_from_items(
    items: list[Any],
) -> tuple[int | None, list[tuple[str, int]]]:
    """Summarize admitted calls from a legacy list-style OCR payload."""

    counts: dict[str, int] = {}
    for item in items:
        name = tool_call_name(item)
        if not name:
            continue
        count = counts.get(name, 0) + 1
        if count > MAX_TOOLKIT_MCP_USAGE_COUNT:
            return None, []
        counts[name] = count

    total = sum(counts.values())
    if total == 0 and items:
        return None, []

    return total, list(counts.items())


def format_tool_calls_summary(tool_calls: Any) -> str:
    """Return one bounded MR line for admitted non-zero OCR tool counts."""

    entries: list[tuple[str, int]]
    total: int | None
    if isinstance(tool_calls, list):
        total, entries = tool_call_counts_from_items(tool_calls)
    elif isinstance(tool_calls, dict):
        by_tool_value = tool_calls.get("by_tool")
        entries = []
        admitted_total = 0

        if isinstance(by_tool_value, dict):
            for raw_name, raw_count in by_tool_value.items():
                if not isinstance(raw_name, str) or raw_name not in PUBLIC_REVIEW_TOOL_CALL_NAMES:
                    continue
                if (
                    not isinstance(raw_count, int)
                    or isinstance(raw_count, bool)
                    or not 0 < raw_count <= MAX_TOOLKIT_MCP_USAGE_COUNT
                ):
                    continue
                admitted_total += raw_count
                if admitted_total > MAX_TOOLKIT_MCP_USAGE_COUNT:
                    return ""
                entries.append((raw_name, raw_count))

        calls_value = tool_calls.get("calls")
        if not by_tool_value and isinstance(calls_value, list):
            list_total, entries = tool_call_counts_from_items(calls_value)
        else:
            list_total = None

        if "total" in tool_calls:
            raw_total = tool_calls["total"]
            if (
                not isinstance(raw_total, int)
                or isinstance(raw_total, bool)
                or not 0 < raw_total <= MAX_TOOLKIT_MCP_USAGE_COUNT
            ):
                return ""
            total = raw_total
        else:
            if list_total is not None:
                total = list_total
            elif entries:
                total = admitted_total
            else:
                return ""
    else:
        return ""

    if total is None:
        return ""
    if total == 0 or not entries:
        return ""
    if sum(count for _name, count in entries) > total:
        return ""

    line = f"- all OCR tool calls: {total} total"
    entries.sort(key=lambda item: (-item[1], item[0]))
    detail_parts = [f"{inline_code(name)}: {count}" for name, count in entries]

    return f"{line} ({', '.join(detail_parts)})"


def format_mcp_usage_summary(toolkit_metadata: Any) -> str:
    """Report MCP servers from the safe receipt produced by `ocr-ci review`."""

    if (
        not isinstance(toolkit_metadata, dict)
        or toolkit_metadata.get("schema_version") not in SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS
    ):
        return ""
    mcp = toolkit_metadata.get("mcp")
    mcp_usage = mcp.get("usage") if isinstance(mcp, dict) else None
    if (
        not isinstance(mcp_usage, dict)
        or len(mcp_usage) > MAX_TOOLKIT_MCP_USAGE_SERVERS
        or any(
            not isinstance(server, str)
            or TOOLKIT_MCP_SERVER_NAME_RE.fullmatch(server) is None
            or not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 < count <= MAX_TOOLKIT_MCP_USAGE_COUNT
            for server, count in mcp_usage.items()
        )
    ):
        return ""
    used = sorted(mcp_usage.items())
    if not used:
        return ""
    details = ", ".join(f"{inline_code(server)}: {count}" for server, count in used)
    lines = [f"- verified MCP calls: {len(used)} server(s) ({details})"]
    evidence = toolkit_metadata.get("evidence")
    actions = evidence.get("actions") if isinstance(evidence, dict) else None
    if actions == {"state": "unavailable"}:
        lines.append("- built-in evidence actions: unavailable")
    elif isinstance(actions, dict) and set(actions) == {"state", "summary", "list", "get"}:
        action_counts = [actions[action] for action in ("summary", "list", "get")]
        evidence_calls = evidence.get("calls") if isinstance(evidence, dict) else None
        if not (
            actions.get("state") == "verified"
            and all(
                isinstance(count, int)
                and not isinstance(count, bool)
                and 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
                for count in action_counts
            )
            and isinstance(evidence_calls, int)
            and not isinstance(evidence_calls, bool)
            and 0 <= evidence_calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
            and sum(action_counts) == evidence_calls
        ):
            return "\n".join(lines)
        lines.append(
            "- built-in evidence actions: "
            + ", ".join(f"{action}: {actions[action]}" for action in ("summary", "list", "get"))
        )
    return "\n".join(lines)


def publication_dlp_signal(
    publication: Any, *, carried_forward_comments: int = 0
) -> dict[str, Any] | None:
    """Return one low-cardinality signal from an exact v5 DLP receipt."""

    state = publication_dlp_state(publication)
    if (
        state not in {"private-sanitized", "publication-filtered"}
        or not isinstance(carried_forward_comments, int)
        or isinstance(carried_forward_comments, bool)
        or carried_forward_comments < 0
        or (state == "private-sanitized" and carried_forward_comments != 0)
    ):
        return None
    signal: dict[str, Any] = {
        "schema_version": "ocr.publication-dlp-signal/v2",
        "state": state,
        "reason_counts": dict(publication["reason_counts"]),
    }
    if state == "private-sanitized":
        signal["sanitized_fields"] = publication["sanitized_fields"]
    else:
        signal.update(
            {
                "retained": dict(publication["retained"]),
                "omitted": dict(publication["omitted"]),
                "original": dict(publication["original"]),
                "carried_forward_comments": carried_forward_comments,
            }
        )
    return signal


def format_publication_dlp_details(signal: dict[str, Any] | None) -> str:
    """Render a human-visible spoiler plus one stable machine-readable marker."""

    if signal is None:
        return ""
    marker = json.dumps(signal, sort_keys=True, separators=(",", ":"))
    if signal["state"] == "private-sanitized":
        return "\n".join(
            [
                "<details>",
                "<summary>Private result sanitization signal</summary>",
                "",
                (
                    f"Redacted {signal['sanitized_fields']} non-rendered result field(s). "
                    "The canonical published and approval-relevant review is unchanged."
                ),
                "",
                f"<!-- ocr-toolkit-signal {marker} -->",
                "",
                "</details>",
            ]
        )
    retained = signal["retained"]
    omitted = signal["omitted"]
    carried = signal["carried_forward_comments"]
    completeness = (
        "One or more public projection units were omitted. OCR coverage is reported "
        "separately, and automatic approval remains unavailable."
        if omitted["comments"] or omitted["warnings"]
        else "The public projection changed, so automatic approval remains unavailable."
    )
    return "\n".join(
        [
            "<details>",
            "<summary>Publication filtering signal</summary>",
            "",
            (
                f"Published safe subset: {retained['comments']} finding(s) and "
                f"{retained['warnings']} warning(s). Omitted: {omitted['comments']} "
                f"finding(s), {omitted['warnings']} warning(s), and {omitted['fields']} "
                "result field(s)."
            ),
            (f"{carried} matching finding(s) remain in the previous OCR review. {completeness}"),
            "",
            f"<!-- ocr-toolkit-signal {marker} -->",
            "",
            "</details>",
        ]
    )


def format_token_usage_summary(result: dict[str, Any]) -> str:
    """Return one bounded MR summary line for structured OCR token usage."""

    usage = normalize_token_usage(result)
    if usage is None:
        return ""

    total = usage.get("total")
    details: list[str] = []
    for bucket in ("input", "output", "cached", "reasoning", "other"):
        if (count := usage.get(bucket)) is not None and count > 0:
            details.append(f"{bucket}: {count}")

    if total is None:
        return f"- token usage: {', '.join(details)}" if details else ""
    line = f"- token usage: {total} total"
    if details:
        line += f" ({', '.join(details)})"
    return line


SECURITY_SIGNAL_RE = re.compile(
    r"(?i)\b("
    r"security|credential|secret|token|password|private[_ -]?token|"
    r"client[_ -]?secret|api[_ -]?key|authorization|auth|"
    r"xss|csrf|ssrf|rce|path traversal|host header|"
    r"privilege|permission|access control|vault|leak"
    r")\b"
)
SECURITY_INJECTION_RE = re.compile(
    r"(?i)(?<!\w)(?:"
    r"(?:os[\s_-]+)?command|shell(?:[\s_-]+command)?|sql|nosql|code|"
    r"(?:server[\s_-]+side[\s_-]+)?template|prompt|ldap|xpath|crlf|"
    r"(?:http[\s_-]+)?header|log|html|script|expression"
    r")[\s_\-\u2010-\u2015]+injection(?!\w)"
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

    text = comment_signal_text(comment)
    return bool(SECURITY_SIGNAL_RE.search(text) or SECURITY_INJECTION_RE.search(text))


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


def _guide_comment_rank(comment: dict[str, Any], ordinal: int) -> tuple[object, ...]:
    """Return the closed deterministic priority key for one published finding."""

    severity = clean_text(comment.get("severity") or comment.get("priority")).casefold()
    category = clean_text(comment.get("category")).casefold()
    raw_path = comment.get("path")
    path = raw_path if isinstance(raw_path, str) and safe_repository_path(raw_path) else None
    start = line_number(comment.get("start_line") or comment.get("line"))
    end = line_number(comment.get("end_line") or comment.get("line")) or start
    valid_range = start > 0 and end >= start
    raw_fingerprint = comment.get("_ocr_fingerprint")
    fingerprint = (
        raw_fingerprint
        if isinstance(raw_fingerprint, str) and re.fullmatch(r"[0-9a-f]{32}", raw_fingerprint)
        else None
    )
    canonical = json.dumps(comment, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        OCR_FINDING_SEVERITY_ORDER.index(severity)
        if severity in OCR_FINDING_SEVERITY_ORDER
        else len(OCR_FINDING_SEVERITY_ORDER),
        OCR_FINDING_CATEGORY_ORDER.index(category)
        if category in OCR_FINDING_CATEGORY_ORDER
        else len(OCR_FINDING_CATEGORY_ORDER),
        (0, path) if path is not None else (1, ""),
        (0, start, end) if valid_range else (1, 0, 0),
        (0, fingerprint) if fingerprint is not None else (1, ""),
        canonical,
        ordinal,
    )


def format_reviewer_guide(
    comments: Sequence[dict[str, Any]],
    omitted_count: int,
    *,
    outcome_status: str = "success",
    coverage_summary: str = "",
) -> str:
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
    if outcome_status in {"budget_exceeded", "partial"}:
        lines.append(
            "- Review scope: OCR reported partial coverage; treat all findings as a partial review."
        )
    if coverage_summary:
        lines.append(f"- Review coverage: {coverage_summary}")

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

    ranked_comments = sorted(
        enumerate(comments),
        key=lambda item: _guide_comment_rank(item[1], item[0]),
    )
    guide_comments = (
        [comment for _, comment in ranked_comments[:MAX_REVIEWER_GUIDE_COMMENTS]]
        if len(comments) >= 2
        else []
    )
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


def _review_outcome_line(
    *,
    total: int,
    omitted_count: int,
    suppressed_count: int,
    warning_count: int,
    outcome_status: str,
    outcome_message: str,
    diagnostics: CoverageDiagnostics,
    emoji: bool,
) -> str:
    """Combine review health and finding publication into one visible status."""

    budget_stop = outcome_status == "budget_exceeded" or (
        outcome_status == "partial" and "budget" in outcome_message.casefold()
    )
    partial_result = outcome_status in {"partial", "completed_with_errors", "budget_exceeded"}
    has_finding_state = total > 0 or omitted_count > 0 or suppressed_count > 0
    if outcome_status == "skipped":
        marker, status_text = "ℹ️", "Review skipped"  # noqa: RUF001
        result_text = "no supported files changed"
    elif outcome_status == "failed":
        marker, status_text = "❌", "Review failed"
        result_text = "no reliable review result was produced"
    else:
        if budget_stop:
            marker, status_text = "⚠️", "Review stopped at token budget"
        elif partial_result:
            marker, status_text = "⚠️", "Review incomplete"
        elif outcome_status == "publication-filtered":
            marker, status_text = "⚠️", "Review complete with publication filtering"
        elif outcome_status in {"warning", "completed_with_warnings"} or warning_count:
            marker, status_text = "⚠️", "Review complete with warnings"
        elif has_finding_state:
            marker, status_text = "🔎", "Review complete"
        else:
            marker, status_text = "✅", "Review complete"

        if total:
            noun = "finding" if total == 1 else "findings"
            result_text = f"{total} {noun} published"
            if partial_result:
                result_text += " from reviewed files"
        elif omitted_count:
            result_text = (
                "no findings published from reviewed files"
                if partial_result
                else "no findings published"
            )
        elif suppressed_count:
            result_text = (
                "no new findings published from reviewed files"
                if partial_result
                else "no new findings published"
            )
        elif partial_result:
            result_text = "no findings in reviewed files"
        else:
            result_text = "no findings"

        if omitted_count:
            noun = "finding" if omitted_count == 1 else "findings"
            result_text += f"; {omitted_count} {noun} omitted by posting limit"
        if suppressed_count:
            noun = "finding" if suppressed_count == 1 else "findings"
            result_text += f"; {suppressed_count} {noun} matched prior reviewer decisions"
        if partial_result and diagnostics.file_count is not None:
            noun = "file" if diagnostics.file_count == 1 else "files"
            result_text += f"; {diagnostics.file_count} {noun} not reviewed"

    prefix = f"{marker} " if emoji else ""
    return f"{prefix}**{status_text} — {result_text}**"


def format_ocr_core_advisory(advisory: OcrToolkitAdvisory | None) -> str:
    """Render one validated numeric OCR advisory for Technical details only."""

    if advisory is None:
        return ""
    return (
        f"- OCR core advisory: background {advisory.actual} characters; recommended "
        f"{advisory.recommended} characters; accepted by OCR core"
    )


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
    ocr_core_advisory_summary: str = "",
    publication_dlp_details: str = "",
    reviewer_guide: str = "",
    fallback_reasons: Mapping[str, int] | None = None,
    reviewed_sha: str = "",
    mr_head_sha: str = "",
    outcome_status: str = "success",
    outcome_message: str = "",
    coverage_summary: str = "",
    coverage_diagnostics: CoverageDiagnostics | None = None,
    warnings: Sequence[Any] = (),
    suppressed_count: int = 0,
    approval_result: ApprovalResult | None = None,
    emoji: bool | None = None,
) -> str:
    """Build one decision-first summary for every validated OCR outcome."""

    use_emoji = post_emoji() if emoji is None else emoji
    diagnostics = coverage_diagnostics or CoverageDiagnostics((), 0, 0, 0, 0)
    outcome_line = _review_outcome_line(
        total=total,
        omitted_count=omitted_count,
        suppressed_count=suppressed_count,
        warning_count=warning_count,
        outcome_status=outcome_status,
        outcome_message=outcome_message,
        diagnostics=diagnostics,
        emoji=use_emoji,
    )
    lines = ["## Open Code Review", "", outcome_line]
    if outcome_status == "failed":
        lines.extend(
            [
                "",
                "Normal review comments were not published. Previous OCR review comments were preserved.",
            ]
        )

    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for comment in comments:
        severity, category = finding_metadata(comment)
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    if severity_counts or category_counts:
        lines.extend(["", "### Findings", ""])
        for value in OCR_FINDING_SEVERITY_ORDER:
            count = severity_counts.get(value, 0)
            if count:
                icon = f"{SEVERITY_EMOJI[value]} " if use_emoji else ""
                lines.append(f"- {icon}{inline_code(value)}: {count}")
        for value in OCR_FINDING_CATEGORY_ORDER:
            count = category_counts.get(value, 0)
            if count:
                icon = f"{CATEGORY_EMOJI[value]} " if use_emoji else ""
                lines.append(f"- {icon}{inline_code(value)}: {count}")

    if diagnostics.records or diagnostics.invalid or diagnostics.omitted:
        lines.extend(["", "### Incomplete coverage", ""])
        for diagnostic in diagnostics.records:
            detail = f" — {diagnostic.detail}" if diagnostic.detail else ""
            lines.append(f"- {inline_code(diagnostic.path)} — {diagnostic.reason}{detail}")
        if diagnostics.invalid:
            lines.append(
                f"- {diagnostics.invalid} failed item(s) had no safe repository-relative path"
            )
        if diagnostics.omitted:
            lines.append(f"- ... and {diagnostics.omitted} more failed file record(s)")

    safe_warnings = []
    for warning in warnings[:10]:
        safe = compact_escaped_text(
            neutralize_quick_actions(redact_sensitive(ocr_warning_text(warning))), 500
        )
        if safe:
            safe_warnings.append(safe)
    if safe_warnings and not diagnostics.records:
        lines.extend(["", "### Review warnings", ""])
        lines.extend(f"- {warning}" for warning in safe_warnings)
        if len(warnings) > len(safe_warnings):
            lines.append(f"- ... and {len(warnings) - len(safe_warnings)} more warning(s)")

    if reviewer_guide:
        lines.extend(["", reviewer_guide.strip()])

    if publication_dlp_details:
        lines.extend(["", publication_dlp_details])

    technical: list[str] = []
    if reviewed_sha:
        technical.append(f"- Reviewed commit: {_inline_code(reviewed_sha)}")
    if mr_head_sha and mr_head_sha != reviewed_sha:
        technical.append(f"- MR head commit: {_inline_code(mr_head_sha)}")
    technical.append(
        f"- Posting: {inline_count} inline, {fallback_count} fallback, {omitted_count} omitted"
    )
    if approval_result is not None:
        technical.append(approval_summary_line(approval_result))
    if suppressed_count:
        technical.append(f"- Reviewer suppression: {suppressed_count}")
    if coverage_summary:
        technical.append(f"- {coverage_summary}")
    if fallback_reasons:
        reasons = ", ".join(
            f"{inline_code(reason)}: {count}"
            for reason, count in sorted(fallback_reasons.items())
            if count > 0
        )
        if reasons:
            technical.append(f"- Fallback reasons: {reasons}")
    for summary in (
        mcp_usage_summary,
        tool_calls_summary,
        token_usage_summary,
        ocr_core_advisory_summary,
    ):
        if summary:
            technical.append(summary)
    technical.append(f"- Review mode: `{post_mode()}`")
    lines.extend(
        ["", "<details>", "<summary>Technical details</summary>", "", *technical, "", "</details>"]
    )
    return "\n".join(lines)
