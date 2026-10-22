"""Hostile-read validation for content-free federation accounting."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.reporting.federation import format_federation, reconcile, valid_receipt


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


def test_v2_stage_accounting_and_legacy_unavailable_attribution() -> None:
    modern = _receipt()
    modern["schema"] = "ocr.federation/v2"
    entry = modern["tools"]["docs__read"]
    entry.update(attempted=2, completed=1, denied=1, dlp_rejected=1)
    entry["dlp_gates"] = {
        gate: dict.fromkeys(("forbidden", "invalid_text", "limit", "pii", "secret"), 0)
        for gate in ("arguments", "result")
    }
    entry["dlp_gates"]["result"]["pii"] = 1
    assert valid_receipt(modern)
    summary = format_federation(reconcile(modern, {"docs__read": 2}, {"docs__read"}))
    assert "1 call attempt(s) denied at response admission by DLP" in summary
    assert "person@example.test" not in summary

    legacy = _receipt()
    legacy_entry = legacy["tools"]["docs__read"]
    legacy_entry.update(attempted=1, denied=1, dlp_rejected=1)
    assert valid_receipt(legacy)
    summary = format_federation(reconcile(legacy, {"docs__read": 1}, {"docs__read"}))
    assert "exact boundary/reason unavailable" in summary
    assert "response admission" not in summary


def test_v2_rejects_foreign_or_inconsistent_gate_counts() -> None:
    receipt = _receipt()
    receipt["schema"] = "ocr.federation/v2"
    entry = receipt["tools"]["docs__read"]
    entry["dlp_gates"] = {
        gate: dict.fromkeys(("forbidden", "invalid_text", "limit", "pii", "secret"), 0)
        for gate in ("arguments", "result")
    }
    assert valid_receipt(receipt)
    entry["dlp_gates"]["result"]["pii"] = 1
    assert not valid_receipt(receipt)
    entry.update(attempted=1, denied=1, dlp_rejected=1)
    assert valid_receipt(receipt)
    entry["dlp_gates"]["result"]["pii"] = True
    assert not valid_receipt(receipt)
