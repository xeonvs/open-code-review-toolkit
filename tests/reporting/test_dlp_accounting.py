"""Disjoint public and private DLP accounting at the shared report boundary."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ocr_toolkit.reporting.dlp import format_dlp_admission, publication_dlp_state


def _reasons(*, secret: int = 0) -> dict[str, int]:
    return {
        "forbidden": 0,
        "invalid_text": 0,
        "laundering": 0,
        "limit": 0,
        "pii": 0,
        "secret": secret,
    }


def _filtered(*, public_fields: int, private_fields: int) -> dict[str, Any]:
    return {
        "schema": "ocr.publication/v2",
        "state": "publication-filtered",
        "reason_counts": _reasons(secret=public_fields),
        "retained": {"comments": 2, "warnings": 0},
        "omitted": {"comments": 0, "warnings": 0, "fields": public_fields},
        "private_sanitization": {
            "fields": private_fields,
            "reason_counts": _reasons(secret=private_fields),
        },
        "original": {
            "outcome": "clean",
            "selected": 1,
            "completed": 1,
            "reused": 0,
            "failed": 0,
            "waived": 0,
        },
    }


def test_equal_legacy_aggregates_have_distinct_v2_attribution() -> None:
    four_public = _filtered(public_fields=4, private_fields=0)
    two_public_two_private = _filtered(public_fields=2, private_fields=2)
    assert publication_dlp_state(four_public) == "publication-filtered"
    assert publication_dlp_state(two_public_two_private) == "publication-filtered"
    first = format_dlp_admission(four_public)
    second = format_dlp_admission(two_public_two_private)
    assert "omitted 0 finding(s), 0 warning(s), 4 field(s)" in first
    assert "private-only sanitization: 0 field(s)" in first
    assert "omitted 0 finding(s), 0 warning(s), 2 field(s)" in second
    assert "private-only sanitization: 2 field(s)" in second
    assert "private reasons: secret: 2" in second


def test_legacy_aggregate_is_valid_but_unattributed() -> None:
    legacy = _filtered(public_fields=2, private_fields=2)
    legacy.pop("schema")
    legacy.pop("private_sanitization")
    legacy["omitted"]["fields"] = 4
    legacy["reason_counts"] = _reasons(secret=4)
    assert publication_dlp_state(legacy) == "publication-filtered"
    summary = format_dlp_admission(legacy)
    assert "4 aggregate omitted-or-sanitized field(s)" in summary
    assert "historical field attribution unavailable" in summary


def test_new_private_only_receipt_is_separate_from_public_omission() -> None:
    receipt = {
        "schema": "ocr.publication/v2",
        "state": "private-sanitized",
        "private_sanitization": {"fields": 2, "reason_counts": _reasons(secret=2)},
    }
    assert publication_dlp_state(receipt) == "private-sanitized"
    assert "admitted findings unchanged" in format_dlp_admission(receipt)
    assert "omitted" not in format_dlp_admission(receipt)


def test_malformed_disjoint_counts_fail_closed() -> None:
    valid = _filtered(public_fields=2, private_fields=2)
    for malformed in (
        {**valid, "schema": "ocr.publication/v3"},
        {**valid, "private_sanitization": {"fields": -1, "reason_counts": _reasons()}},
        {**valid, "private_sanitization": {"fields": 0, "reason_counts": _reasons(secret=2)}},
        {**valid, "private_sanitization": {"fields": 2, "reason_counts": {"secret": 2}}},
    ):
        assert publication_dlp_state(malformed) is None
    malformed = deepcopy(valid)
    malformed["private_sanitization"]["reason_counts"]["secret"] = True
    assert publication_dlp_state(malformed) is None
