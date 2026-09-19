"""Hostile-read validation for content-free federation accounting."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.reporting.federation import valid_receipt


def _receipt() -> dict[str, Any]:
    return {
        "schema": "ocr.federation/v1",
        "run_id": "a" * 32,
        "state": "finalized",
        "cleanup": "clean",
        "tools": {
            "docs__read": {
                "server": "docs",
                "assurance": "review_read",
                "attempted": 0,
                "completed": 0,
                "denied": 0,
                "failed": 0,
                "timed_out": 0,
                "dlp_rejected": 0,
                "oversized": 0,
                "cache_hits": 0,
                "single_flight": 0,
            }
        },
    }


def test_non_string_assurance_is_rejected_without_exception() -> None:
    receipt = _receipt()
    receipt["tools"]["docs__read"]["assurance"] = []
    assert valid_receipt(receipt) is False
