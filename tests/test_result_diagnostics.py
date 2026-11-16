"""Closed diagnostics must never render hostile result names or values."""

import pytest

from ocr_toolkit.result_diagnostics import result_diagnostic
from tests.test_review_runner import SUMMARY_ACTION_COUNTS


@pytest.mark.parametrize(
    ("telemetry", "state", "total", "primary"),
    [
        (None, "null", None, None),
        ([], "invalid", None, None),
        ({"total": True, "by_tool": {}}, "invalid", None, None),
        ({"total": -1, "by_tool": {}}, "invalid", None, None),
        ({"total": 1_000_000_001, "by_tool": {}}, "invalid", None, None),
        ({"total": 2, "by_tool": []}, "invalid", 2, None),
        ({"total": 0, "by_tool": {"ocr_toolkit_evidence": 1}}, "invalid", 0, None),
        ({"total": 2, "by_tool": {"ocr_toolkit_evidence": False}}, "invalid", 2, None),
        ({"total": 2, "by_tool": {"private-tool": 2}}, "present", 2, 0),
        ({"total": 2, "by_tool": {"ocr_toolkit_evidence": 1}}, "present", 2, 1),
    ],
)
def test_telemetry_projection(telemetry, state, total, primary):
    facts = result_diagnostic({"tool_calls": telemetry}, exit_code=0, action_counts=None)
    assert (facts.tool_calls, facts.total, facts.evidence_calls) == (state, total, primary)
    assert "private-tool" not in facts.render()


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({}, "missing-field"),
        ({"tool_calls": None}, "explicit-null"),
        ({"tool_calls": []}, "not-object"),
        ({"tool_calls": {"total": True}}, "total-invalid"),
        ({"tool_calls": {"total": 0, "by_tool": []}}, "by-tool-not-object"),
        (
            {"tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": False}}},
            "evidence-count-invalid",
        ),
        (
            {"tool_calls": {"total": 0, "by_tool": {"ocr_toolkit_evidence": 1}}},
            "evidence-exceeds-total",
        ),
        ({"tool_calls": {"total": 1, "by_tool": {"file_read": 1}}}, "evidence-entry-absent"),
        ({"tool_calls": {"total": 0, "by_tool": {"ocr_toolkit_evidence": 0}}}, "evidence-zero"),
        ({"tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}}, "evidence-reported"),
    ],
)
def test_closed_cause_codes(payload, detail):
    assert result_diagnostic(payload, exit_code=0, action_counts=None).telemetry_detail == detail


@pytest.mark.parametrize("status", [[], {}, "private-status\nsecret", 1, None])
def test_hostile_names_and_values_never_reach_the_log(status):
    facts = result_diagnostic(
        {"status": status, "private-key\nsecret": "private-value", "manifest": "private-manifest"},
        exit_code=True,
        action_counts=None,
    )
    rendered = facts.render()
    assert facts.status == "unknown" and facts.unknown_keys == 1
    assert facts.keys == ("manifest", "status") and facts.manifest_present
    assert "private" not in rendered and "secret" not in rendered
    assert "ocr_exit_code=unavailable" in rendered and "summary_receipt=unavailable" in rendered


def test_independent_receipt_is_diagnostic_even_when_ocr_telemetry_is_missing():
    facts = result_diagnostic(
        {"status": "success"}, exit_code=-15, action_counts=SUMMARY_ACTION_COUNTS
    )
    assert facts.summary_attempted == facts.summary_completed == 1
    assert facts.evidence_calls is None and facts.tool_calls == "missing"
    assert "summary_receipt=available summary_attempted=1 summary_completed=1" in facts.render()
    assert "ocr_exit_code=-15" in facts.render()


@pytest.mark.parametrize(
    "counts",
    [
        {},
        {"attempted": {}, "completed": {}},
        {"attempted": {"summary": True}, "completed": {"summary": 1}},
    ],
)
def test_invalid_receipt_is_unavailable_not_zero(counts):
    facts = result_diagnostic({}, exit_code=None, action_counts=counts)
    assert facts.summary_attempted is None and facts.summary_completed is None


def test_invalid_process_identity_is_not_rendered():
    assert (
        "ocr_exit_code=unavailable"
        in result_diagnostic({}, exit_code=10**100, action_counts=None).render()
    )
