"""Provider-neutral formatting of admitted OCR tool usage."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.common.markdown import inline_code as _inline_code
from ocr_toolkit.evidence.actions import EVIDENCE_ACTIONS
from ocr_toolkit.ocr_result import (
    MAX_TOOLKIT_MCP_USAGE_COUNT,
    MAX_TOOLKIT_MCP_USAGE_SERVERS,
    PUBLIC_REVIEW_TOOL_CALL_NAMES,
    TOOLKIT_MCP_SERVER_NAME_RE,
)
from ocr_toolkit.reporting.text import clean_text


def inline_code(value: str) -> str:
    """Escape controls and delimiters in report labels."""
    return _inline_code(value, escape_controls=True)


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
    """Return one bounded report line for admitted non-zero OCR tool counts."""

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


def format_verified_mcp_usage(*, mcp_usage: Any, evidence: Any) -> str:
    """Format execution-owner-verified facts, never model-supplied usage claims."""

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
    lines = [f"- reconciled MCP attempts: {len(used)} server(s) ({details})"]
    completed = validated_completed_actions(evidence)
    if completed is not None:
        positive = [action for action in EVIDENCE_ACTIONS if completed[action] > 0]
        if positive:
            lines.append(
                "- completed built-in evidence actions: "
                + ", ".join(f"{action}: {completed[action]}" for action in positive)
            )
    return "\n".join(lines)


def validated_completed_actions(evidence: Any) -> dict[str, int] | None:
    """Read exact execution action counts without consulting rendered prose."""

    actions = evidence.get("actions") if isinstance(evidence, dict) else None
    if isinstance(actions, dict) and set(actions) == {"state", "attempted", "completed"}:
        attempted = actions.get("attempted")
        completed = actions.get("completed")
        evidence_calls = evidence.get("calls") if isinstance(evidence, dict) else None
        mandatory = evidence.get("mandatory") if isinstance(evidence, dict) else None
        evidence_used = evidence.get("used") if isinstance(evidence, dict) else None
        if not (
            actions.get("state") == "verified"
            and isinstance(attempted, dict)
            and set(attempted) == {*EVIDENCE_ACTIONS, "unattributed"}
            and isinstance(completed, dict)
            and set(completed) == set(EVIDENCE_ACTIONS)
            and all(
                isinstance(count, int)
                and not isinstance(count, bool)
                and 0 <= count <= MAX_TOOLKIT_MCP_USAGE_COUNT
                for count in (*attempted.values(), *completed.values())
            )
            and isinstance(evidence_calls, int)
            and not isinstance(evidence_calls, bool)
            and 0 <= evidence_calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
            and isinstance(mandatory, bool)
            and isinstance(evidence_used, bool)
            and all(completed[action] <= attempted[action] for action in EVIDENCE_ACTIONS)
            and sum(attempted.values()) == evidence_calls
            and evidence_used is (sum(completed.values()) > 0)
            and (not mandatory or completed["summary"] >= 1)
        ):
            return None
        return dict(completed)
    return None
