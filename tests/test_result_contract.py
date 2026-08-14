"""Contracts for legacy and versioned OCR result outcomes."""

from __future__ import annotations

from typing import Any

import pytest

from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome


def manifest_result(
    status: str,
    *,
    selected: list[str],
    completed: list[str] | None = None,
    reused: list[str] | None = None,
    failed: list[tuple[str, str]] | None = None,
    waived: list[str] | None = None,
    run_failure: str = "",
    budget_exceeded: bool = False,
) -> dict[str, Any]:
    """Build a compact synthetic v1 result fixture."""

    completed = completed or []
    reused = reused or []
    failed = failed or []
    waived = waived or []
    manifest: dict[str, Any] = {
        "schema_version": "ocr.run-manifest/v1",
        "run_id": "synthetic-run",
        "operation": "review",
        "terminal_state": status,
        "coverage": {
            "selected": [{"item_id": item} for item in selected],
            "completed": [{"item_id": item} for item in completed],
            "reused": [{"item_id": item} for item in reused],
            "failed": [
                {"item_id": item, "classification": classification}
                for item, classification in failed
            ],
            "waived": [{"item_id": item, "reason": "accepted risk"} for item in waived],
        },
    }
    if run_failure:
        manifest["run_failure"] = {"classification": run_failure}
    return {
        "status": status,
        "summary": {"budget_exceeded": budget_exceeded},
        "manifest": manifest,
    }


@pytest.mark.parametrize(
    ("status", "expected_kind"),
    [
        ("success", "clean"),
        ("completed_with_warnings", "warning"),
        ("completed_with_errors", "partial"),
        ("skipped", "skipped"),
    ],
)
def test_legacy_statuses_remain_supported(status: str, expected_kind: str) -> None:
    """Preserve the pre-manifest result vocabulary during migration."""

    outcome = parse_result_outcome({"status": status})

    assert outcome.kind == expected_kind
    assert not outcome.manifest_present


def test_manifest_complete_exposes_bounded_coverage_summary() -> None:
    """Normalize a fully covered manifest without exposing item paths or reasons."""

    outcome = parse_result_outcome(
        manifest_result(
            "complete",
            selected=["a", "b", "c"],
            completed=["a"],
            reused=["b"],
            waived=["c"],
        )
    )

    assert outcome.kind == "clean"
    assert outcome.manifest_present
    assert outcome.coverage_summary == (
        "Coverage: selected 3; completed 1; reused 1; failed 0; waived 1."
    )


def test_manifest_partial_and_budget_failure_are_supported() -> None:
    """Publish completed findings while clearly identifying incomplete coverage."""

    outcome = parse_result_outcome(
        manifest_result(
            "partial",
            selected=["a", "b"],
            completed=["a"],
            failed=[("b", "budget")],
            budget_exceeded=True,
        )
    )

    assert outcome.kind == "partial"
    assert outcome.budget_exceeded
    assert outcome.failed_count == 1


def test_manifest_run_failure_forces_failed_outcome() -> None:
    """A run-level stop remains failed even when some items completed."""

    outcome = parse_result_outcome(
        manifest_result(
            "failed",
            selected=["a", "b"],
            completed=["a"],
            failed=[("b", "unknown")],
            run_failure="internal",
        )
    )

    assert outcome.kind == "failed"
    assert not outcome.requires_evidence_mcp


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda result: result["manifest"].update({"terminal_state": "complete"}),
            "terminal_state",
        ),
        (
            lambda result: result["manifest"]["coverage"]["failed"].append(
                {"item_id": "a", "classification": "provider"}
            ),
            "not disjoint",
        ),
        (
            lambda result: result["manifest"]["coverage"]["failed"][0].update(
                {"classification": "surprise"}
            ),
            "classification",
        ),
    ],
)
def test_manifest_contradictions_fail_closed(mutate: Any, message: str) -> None:
    """Reject status, partition, and enum variants that could hide lost coverage."""

    result = manifest_result(
        "partial",
        selected=["a", "b"],
        completed=["a"],
        failed=[("b", "provider")],
    )
    mutate(result)

    with pytest.raises(OcrResultContractError, match=message):
        parse_result_outcome(result)


def test_new_terminal_status_requires_supported_manifest() -> None:
    """Never infer new status semantics when the versioned evidence is absent."""

    with pytest.raises(OcrResultContractError, match="requires a supported manifest"):
        parse_result_outcome({"status": "partial"})


def test_budget_flag_requires_matching_manifest_failure() -> None:
    """Reject an aggregate budget claim without machine-readable attribution."""

    result = manifest_result(
        "partial",
        selected=["a", "b"],
        completed=["a"],
        failed=[("b", "provider")],
        budget_exceeded=True,
    )

    with pytest.raises(OcrResultContractError, match="no matching manifest budget failure"):
        parse_result_outcome(result)


def test_additive_retry_report_does_not_change_outcome_semantics() -> None:
    """Keep OCR 1.9.3 retry observability outside the review-health contract."""

    result = manifest_result(
        "complete",
        selected=["a"],
        completed=["a"],
    )
    result["retry_report"] = {
        "schema_version": "ocr.llm-retry-report/v1",
        "total_requests": 2,
        "retried_requests": 1,
        "requests": [{"file_path": "private/example.py"}],
    }

    outcome = parse_result_outcome(result)

    assert outcome.kind == "clean"
    assert outcome.manifest_present
