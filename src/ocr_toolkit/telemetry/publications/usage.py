"""Decode a bounded token-usage line from an OCR summary."""

import re
from collections import Counter
from collections.abc import Set
from typing import Any

from ocr_toolkit.ocr_result import PUBLIC_REVIEW_TOOL_CALL_NAMES
from ocr_toolkit.review_model import admitted_model

from .grammar import OCR_EVIDENCE_ACTION_MAX_COUNT, OCR_EVIDENCE_ACTIONS, OCR_MCP_KINDS


def parse_review_model(technical: str) -> dict[str, str | bool]:
    """Read one identifier, distinguishing unavailable and rejected model lines."""

    lines = re.findall(r"(?m)^- Review model v[0-9]+(?=$|[ \t:])[^\n]*", technical)
    if not lines:
        return {}
    if len(lines) == 1:
        match = re.fullmatch(r"- Review model v1: `([^`\r\n]+)`", lines[0])
        if match and (model := admitted_model(match[1])) is not None:
            return {"model": model, "model_source": "ocr_selected"}
    return {"model_rejected": True}


def parse_ocr_token_usage(body: str) -> dict[str, int]:
    """Normalize one published token line into validated provider-neutral buckets."""

    matches = re.findall(r"^- token usage: *([^\r\n]+)$", body, re.I | re.M)
    if len(matches) != 1:
        return {}
    line = matches[0].strip()
    total_match = re.match(r"([0-9]{1,12})\s+total(?:\s*\(([^)]*)\))?$", line, re.IGNORECASE)
    if total_match:
        total = int(total_match.group(1))
        details = total_match.group(2) or ""
    else:
        total = None
        details = line
    pairs = [part.strip() for part in details.split(",") if part.strip()]
    raw: dict[str, int] = {}
    for part in pairs:
        counter = re.fullmatch(
            r"(prompt|completion|input|output|cached|reasoning|other):\s*([0-9]{1,12})",
            part,
            re.IGNORECASE,
        )
        if not counter:
            return {}
        key = counter.group(1).casefold()
        if key in raw:
            return {}
        raw[key] = int(counter.group(2))
    if details and not pairs:
        return {}
    input_values = {raw[key] for key in ("prompt", "input") if key in raw}
    output_values = {raw[key] for key in ("completion", "output") if key in raw}
    if (
        len(input_values) > 1
        or len(output_values) > 1
        or {"prompt", "input"} <= raw.keys()
        or {"completion", "output"} <= raw.keys()
    ):
        return {}
    input_tokens = next(iter(input_values), None)
    output_tokens = next(iter(output_values), None)
    cached = raw.get("cached")
    reasoning = raw.get("reasoning")
    if cached is not None and (input_tokens is None or cached > input_tokens):
        return {}
    if reasoning is not None and (output_tokens is None or reasoning > output_tokens):
        return {}
    primary = (input_tokens or 0) + (output_tokens or 0)
    if total is not None and total < primary:
        return {}
    if total is None and input_tokens is not None and output_tokens is not None:
        total = primary
    if "other" in raw and (total is None or raw["other"] != total - primary):
        return {}
    normalized = {
        key: value
        for key, value in (
            ("input", input_tokens),
            ("output", output_tokens),
            ("cached", cached),
            ("reasoning", reasoning),
            ("other", raw.get("other")),
            ("total", total),
        )
        if value is not None
    }
    if total is not None and input_tokens is not None and output_tokens is not None:
        other = total - input_tokens - output_tokens
        if other:
            normalized["other"] = other
    return normalized


def named_counts(value: str | None, allowed: Set[str]) -> tuple[int, dict[str, int]]:
    pairs = re.findall(r"`([^`]+)`: ([0-9]{1,12})", value or "")
    names = [name for name, _count in pairs]
    if (
        len(pairs) > 128
        or len(set(names)) != len(names)
        or ", ".join(f"`{name}`: {count}" for name, count in pairs) != (value or "")
    ):
        return 0, {}
    counts: Counter[str] = Counter()
    for name, count in pairs:
        counts[name if name in allowed else "other"] += int(count)
    return len(names), dict(counts)


def parse_usage(metrics_text: str) -> dict[str, Any]:
    """Read numeric usage and evidence counts while aggregating external names."""

    tool_calls_match = re.search(
        r"(?m)^- (?:all OCR )?tool calls: ([0-9]{1,12}) total(?: \(([^\n]*)\))?$",
        metrics_text,
    )
    mcp_match = re.search(
        r"(?m)^- (MCP used|verified MCP calls|reconciled MCP attempts): "
        r"([0-9]{1,12}) server\(s\) \(([^\r\n]*)\)$",
        metrics_text,
    )

    _, tool_calls_by_name = named_counts(
        tool_calls_match.group(2) if tool_calls_match else None, PUBLIC_REVIEW_TOOL_CALL_NAMES
    )
    mcp: dict[str, Any] | None = None
    if mcp_match:
        servers, mcp_calls_by_name = named_counts(
            mcp_match.group(3), {"ocr_toolkit_evidence", "ocr_toolkit_federation"}
        )
        declared_servers = int(mcp_match.group(2))
        if (declared_servers > 0 and servers == declared_servers) or (
            declared_servers == 0 and not mcp_match.group(3)
        ):
            mcp = {
                "kind": OCR_MCP_KINDS[mcp_match.group(1)],
                "servers": servers,
                "calls": sum(mcp_calls_by_name.values()),
                "calls_by_name": mcp_calls_by_name,
            }
    evidence_match = re.search(
        r"(?m)^- (?:completed )?built-in evidence actions: ([^\r\n]+)$",
        metrics_text,
    )
    completed_evidence_actions: dict[str, Any] | None = None
    if evidence_match and evidence_match.group(1) == "unavailable":
        completed_evidence_actions = {"state": "unavailable"}
    elif evidence_match:
        detail = evidence_match.group(1)
        pairs = re.findall(r"([a-z]+): ([0-9]{1,12})", detail)
        rendered = ", ".join(f"{action}: {value}" for action, value in pairs)
        actions = tuple(action for action, _value in pairs)
        values = {action: int(value) for action, value in pairs}
        bounded = all(0 <= values[action] <= OCR_EVIDENCE_ACTION_MAX_COUNT for action in actions)
        legacy_shape = actions == OCR_EVIDENCE_ACTIONS[:3] and bounded
        current_shape = (
            bool(actions)
            and actions == tuple(action for action in OCR_EVIDENCE_ACTIONS if action in actions)
            and bounded
            and all(values[action] > 0 for action in actions)
            and values.get("summary", 0) >= 1
        )
        if rendered == detail and (legacy_shape or current_shape):
            completed_evidence_actions = {"state": "available", **values}
    total = int(tool_calls_match.group(1)) if tool_calls_match else None
    if total is not None and sum(tool_calls_by_name.values()) > total:
        tool_calls_by_name = {}
    return {
        "tokens": parse_ocr_token_usage(metrics_text),
        "tool_calls": total,
        "tool_calls_by_name": tool_calls_by_name,
        "mcp": mcp,
        "completed_evidence_actions": completed_evidence_actions,
    }
