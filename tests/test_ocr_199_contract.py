"""Focused OCR 1.9.9 adaptation contracts."""

from __future__ import annotations

from ocr_toolkit import review_runner
from ocr_toolkit.posting.result import normalize_coverage_diagnostics
from ocr_toolkit.result_contract import parse_result_outcome


def _partial_result(reason: str) -> dict[str, object]:
    return {
        "status": "partial",
        "comments": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "partial",
            "coverage": {
                "selected": [{"item_id": "done"}, {"item_id": "stopped"}],
                "completed": [{"item_id": "done"}],
                "reused": [],
                "failed": [
                    {
                        "item_id": "stopped",
                        "path": "src/example.py",
                        "classification": "unknown",
                        "reason": reason,
                    }
                ],
                "waived": [],
            },
        },
    }


def test_named_main_loop_stop_reason_survives_result_projection_and_posting() -> None:
    reason = "stopped after repeated rounds without a usable tool result"
    result = _partial_result(reason)

    outcome = parse_result_outcome(result)
    projection = review_runner._canonical_result_projection(result)
    diagnostics = normalize_coverage_diagnostics(outcome, [])

    assert outcome.failed_items[0].reason == reason
    assert reason.encode() in projection
    assert diagnostics.records[0].reason == "unknown subtask failure"
    assert diagnostics.records[0].detail == reason


def test_named_main_loop_stop_reason_is_redacted_by_publication_dlp() -> None:
    reason = "stopped because context compression exceeded secret-marker"

    projected, publication, filtered = review_runner._publication_projection(
        _partial_result(reason),
        forbidden=("secret-marker",),
        allowed_tools=frozenset(),
    )

    assert filtered is True
    assert publication["state"] == "publication-filtered"
    assert reason not in str(projected)
