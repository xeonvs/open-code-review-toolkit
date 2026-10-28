"""Reporting admits only bounded factual counts, including legacy call shapes."""

import math

import pytest

from ocr_toolkit.evidence.actions import EVIDENCE_ACTIONS
from ocr_toolkit.ocr_result import MAX_TOOLKIT_MCP_USAGE_COUNT as LIMIT
from ocr_toolkit.reporting import usage


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (None, None),
        (True, None),
        (-1, None),
        (2, 2),
        (2.0, 2),
        (2.5, None),
        (math.inf, None),
        (math.nan, None),
        (" 3 ", 3),
        ("-2", None),
        ("invalid", None),
        ([], None),
    ),
)
def test_nonnegative_numbers_keep_numeric_units_and_reject_coercions(value, expected) -> None:
    assert usage.nonnegative_int(value) == expected


@pytest.mark.parametrize(
    "value",
    (
        "file_read",
        {"name": "file_read"},
        {"tool": "file_read"},
        {"tool_name": "file_read"},
        {"function": {"name": "file_read"}},
    ),
)
def test_legacy_call_shapes_have_one_closed_public_name(value) -> None:
    assert usage.tool_call_name(value) == "file_read"


@pytest.mark.parametrize(
    "value",
    (
        None,
        3,
        [],
        "private-tool",
        {"name": "private-tool"},
        {"function": {"name": "private-tool"}},
        {"function": []},
    ),
)
def test_unknown_or_malformed_tools_cannot_become_public_labels(value) -> None:
    assert usage.tool_call_name(value) == ""


@pytest.mark.parametrize(
    "value",
    (
        None,
        [],
        ["private-tool"],
        {"total": True},
        {"total": 0},
        {"total": LIMIT + 1},
        {"by_tool": {"file_read": True}},
        {"by_tool": {"file_read": LIMIT, "ocr_toolkit_evidence": 1}},
        {"total": 1, "by_tool": {"file_read": 2}},
        {"calls": ["private-tool"]},
    ),
)
def test_unknown_invalid_and_over_budget_counts_never_render_as_fact(value) -> None:
    assert usage.format_tool_calls_summary(value) == ""


@pytest.mark.parametrize(
    "value",
    (
        ["file_read"],
        {"calls": ["file_read"]},
        {"by_tool": {"file_read": 1}},
        {"total": 1, "by_tool": {"file_read": 1, "private-tool": 999}},
    ),
)
def test_admitted_legacy_and_current_shapes_render_the_same_counts(value) -> None:
    assert (
        usage.format_tool_calls_summary(value) == "- all OCR tool calls: 1 total (`file_read`: 1)"
    )


def evidence():
    attempted = dict.fromkeys((*EVIDENCE_ACTIONS, "unattributed"), 0)
    completed = dict.fromkeys(EVIDENCE_ACTIONS, 0)
    attempted["summary"] = completed["summary"] = 1
    return {
        "calls": 1,
        "mandatory": True,
        "used": True,
        "actions": {"state": "verified", "attempted": attempted, "completed": completed},
    }


@pytest.mark.parametrize(
    "change", ("bool", "unattributed", "completed", "used", "mandatory", "state")
)
def test_action_claims_require_complete_counter_reconciliation(change) -> None:
    value = evidence()
    if change == "bool":
        value["actions"]["attempted"]["summary"] = True
    elif change == "unattributed":
        value["actions"]["attempted"]["unattributed"] = 1
    elif change == "completed":
        value["actions"]["completed"]["summary"] = 2
    elif change == "used":
        value["used"] = False
    elif change == "mandatory":
        value["actions"]["attempted"]["summary"] = value["actions"]["completed"]["summary"] = value[
            "calls"
        ] = 0
        value["used"] = False
    else:
        value["actions"]["state"] = "unverified"
    assert usage.validated_completed_actions(value) is None


def test_verified_usage_keeps_only_complete_actions_and_legacy_notice() -> None:
    result = usage.format_verified_mcp_usage(
        mcp_usage={"ocr_toolkit_evidence": 1}, evidence=evidence(), legacy_policy=True
    )
    assert "summary: 1" in result and "legacy policy; references not executed" in result
    assert usage.validated_completed_actions(evidence())["summary"] == 1
    assert usage.format_verified_mcp_usage(mcp_usage={}, evidence=None) == ""
