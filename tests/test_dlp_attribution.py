"""Registration-time provenance and stage-aware public DLP projection."""

import json
from collections import Counter

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import (
    FORBIDDEN_SOURCE_CLASSES,
    ForbiddenMatcher,
    ForbiddenValue,
    check_text,
    dlp_mode,
    resolve_dlp_enabled,
)
from ocr_toolkit.posting.formatting import format_publication_dlp_details, publication_dlp_signal
from ocr_toolkit.reporting.dlp import admission_dlp_state, admitted_outcome_for_summary
from ocr_toolkit.result_contract import parse_result_outcome


def test_dlp_switch_is_default_on_strict_and_content_only() -> None:
    assert resolve_dlp_enabled({}) is True
    assert resolve_dlp_enabled({"OCR_DLP_ENABLED": "false"}) is False
    assert resolve_dlp_enabled({"OCR_DLP_ENABLED": "OFF"}) is False
    with pytest.raises(ValueError, match="OCR_DLP_ENABLED must be one of"):
        resolve_dlp_enabled({"OCR_DLP_ENABLED": "private-value"})

    budgets = TextBudgets(100, 400, 3)
    with dlp_mode(False):
        admitted = check_text("synthetic@example.invalid", budgets=budgets)
        assert admitted.admitted and admitted.reason == "disabled"
        assert not check_text("x" * 101, budgets=budgets).admitted
        assert not check_text("unsafe\x00control", budgets=budgets).admitted
    assert not check_text("synthetic@example.invalid", budgets=budgets).admitted


def test_disabled_publication_dlp_preserves_result_and_emits_closed_state() -> None:
    payload = {
        "status": "success",
        "comments": [{"content": "synthetic@example.invalid"}],
        "warnings": [],
        "tool_calls": {"total": 0, "by_tool": {}},
    }
    projected, publication, filtered = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset(),
        dlp_enabled=False,
    )
    assert projected is payload
    assert publication == {"state": "disabled"}
    assert filtered is False
    signal = publication_dlp_signal(publication)
    assert signal == {
        "schema_version": "ocr.publication-dlp-signal/v3",
        "state": "disabled",
    }
    details = format_publication_dlp_details(signal)
    assert "DLP disabled: sensitive-data risk" in details
    assert "Automatic approval is blocked" in details


def test_registration_merges_normalized_source_classes_without_rejected_content() -> None:
    matcher = ForbiddenMatcher.compile(
        (
            ForbiddenValue("Protected synthetic discussion sentence", "forge_discussions"),
            ForbiddenValue("Protected synthetic discussion sentence", "external_context"),
        )
    )
    checked = check_text(
        "Protected synthetic discussion sentence",
        publication=True,
        budgets=TextBudgets(1000, 4000, 30),
        forbidden_matcher=matcher,
    )
    assert not checked.admitted
    assert checked.text is None
    assert checked.source_classes == ("external_context", "forge_discussions")
    with pytest.raises(ValueError, match="unknown forbidden source"):
        ForbiddenValue("data", "operator-chosen-label")


def test_complete_ocr_is_not_partial_coverage_after_publication_filtering() -> None:
    text = "Validate the synthetic configuration value before rendering"
    payload = {
        "status": "success",
        "comments": [{"path": "src/sample.py", "line": 2, "content": text}],
        "warnings": [],
        "tool_calls": {"total": 0, "by_tool": {}},
    }
    projected, publication, filtered = review_runner._publication_projection(
        payload,
        forbidden=(
            ForbiddenValue(text, "forge_discussions"),
            ForbiddenValue(text, "external_context"),
        ),
        allowed_tools=frozenset(),
    )
    assert filtered
    assert projected["comments"] == []
    assert publication["omitted"]["comments"] == 1
    assert publication["source_attribution"]["counts"]["forge_discussions"] == 1
    assert publication["source_attribution"]["counts"]["external_context"] == 1
    assert admission_dlp_state(publication) == "publication-filtered"
    assert (
        admitted_outcome_for_summary(parse_result_outcome(projected), publication).kind == "clean"
    )
    public = json.dumps(publication)
    assert text not in public and "src/sample.py" not in public


def test_item_attribution_deduplicates_multiple_fields() -> None:
    text = "Protected synthetic discussion sentence"
    sources: set[str] = set()
    reasons = review_runner._dlp_reasons(
        {"first": text, "second": text},
        budgets=TextBudgets(1000, 4000, 30),
        matcher=ForbiddenMatcher.compile((ForbiddenValue(text, "forge_discussions"),)),
        source_classes=sources,
    )
    assert reasons["forbidden"] == 2
    assert Counter(sources) == {"forge_discussions": 1}


def test_unknown_or_unbounded_attribution_cannot_reach_signal() -> None:
    publication = {
        "state": "private-sanitized",
        "sanitized_fields": 1,
        "reason_counts": {k: int(k == "forbidden") for k in review_runner.DLP_REASONS},
        "source_attribution": {
            "schema": "ocr.forbidden-sources/v1",
            "counts": {k: int(k == "forge_discussions") for k in FORBIDDEN_SOURCE_CLASSES},
        },
    }
    signal = publication_dlp_signal(publication)
    assert signal["schema_version"] == "ocr.publication-dlp-signal/v3"
    assert signal["source_attribution"] == publication["source_attribution"]
    publication["source_attribution"]["counts"]["operator-label"] = 1
    assert publication_dlp_signal(publication) is None
