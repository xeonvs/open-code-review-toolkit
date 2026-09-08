"""Characterize shared report facts independently of adapter delivery envelopes."""

from __future__ import annotations

import pytest

from ocr_toolkit.posting.formatting import summarize_result
from ocr_toolkit.providers.local import local_summary
from ocr_toolkit.reporting.model import ReviewReport
from ocr_toolkit.reporting.result import normalize_coverage_diagnostics
from ocr_toolkit.reporting.sections import report_sections
from ocr_toolkit.result_contract import ReviewOutcome


@pytest.mark.parametrize("partial", [False, True])
def test_adapters_share_finding_warning_coverage_and_usage_facts(partial: bool) -> None:
    comments = ({"path": "src/example.py", "severity": "high", "category": "bug"},)
    warnings = ({"file": "src/other.py", "message": "provider request failed"},)
    outcome = ReviewOutcome(
        status="completed_with_errors" if partial else "completed_with_warnings",
        kind="partial" if partial else "warning",
        budget_exceeded=False,
    )
    diagnostics = normalize_coverage_diagnostics(outcome, warnings)
    report = ReviewReport(
        outcome=outcome,
        comments=comments,
        warnings=warnings,
        diagnostics=diagnostics,
        tool_calls_summary="- all OCR tool calls: 1 total (`read_file`: 1)",
        token_usage_summary="- token usage: 100 total",
        mcp_usage_summary="- reconciled MCP attempts: 1 server(s) (`evidence`: 1)",
        publication={"state": "passed"},
    )
    local = local_summary(report)
    gitlab = summarize_result(
        total=1,
        inline_count=1,
        fallback_count=0,
        warning_count=1,
        comments=comments,
        warnings=warnings,
        outcome_status=outcome.status,
        coverage_diagnostics=diagnostics,
        tool_calls_summary=report.tool_calls_summary,
        token_usage_summary=report.token_usage_summary,
        mcp_usage_summary=report.mcp_usage_summary,
        emoji=False,
    )
    shared = "\n".join(report_sections(comments, diagnostics, warnings))
    assert shared and shared in local and shared in gitlab
    for detail in (
        report.tool_calls_summary,
        report.token_usage_summary,
        report.mcp_usage_summary,
    ):
        assert detail in local and detail in gitlab
    assert "1 finding published" in gitlab
    assert "1 finding published" not in local
    assert "<details>" in gitlab and "<details>" not in local
