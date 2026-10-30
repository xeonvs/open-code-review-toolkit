"""Producer receipts distinguish public omissions from private cleanup."""

from __future__ import annotations

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.posting.formatting import (
    format_publication_dlp_details,
    publication_dlp_signal,
)


def _payload(*, public_fields: int) -> dict[str, object]:
    comments = [
        {
            "path": "src/example.py",
            "content": "Review this safe declaration.",
            "existing_code": "login_password: 'synthetic-secret-value'",
        }
        for _ in range(2)
    ]
    payload: dict[str, object] = {
        "status": "complete",
        "warnings": [],
        "comments": comments,
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "one"}],
                "completed": [{"item_id": "one"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }
    if public_fields == 4:
        for comment in comments:
            comment["suggestion_code"] = "login_password: 'synthetic-secret-value'"
    else:
        payload["private_one"] = "login_password: 'synthetic-secret-value'"
        payload["private_two"] = "login_password: 'synthetic-secret-value'"
    return payload


def test_equal_legacy_aggregate_shapes_have_disjoint_v2_producer_counts() -> None:
    receipts = []
    projected_results = []
    for public_fields in (4, 2):
        projected, receipt, filtered = review_runner._publication_projection(
            _payload(public_fields=public_fields),
            forbidden=(),
            allowed_tools=frozenset(),
        )
        assert filtered
        assert receipt["schema"] == "ocr.publication/v2"
        assert receipt["state"] == "publication-filtered"
        assert receipt["omitted"] == {"comments": 0, "warnings": 0, "fields": public_fields}
        assert receipt["private_sanitization"]["fields"] == 4 - public_fields
        assert receipt["reason_counts"]["secret"] == public_fields
        assert receipt["private_sanitization"]["reason_counts"]["secret"] == 4 - public_fields
        signal = publication_dlp_signal(receipt)
        assert signal is not None
        assert signal["schema_version"] == "ocr.publication-dlp-signal/v4"
        assert signal["omitted"]["fields"] == public_fields
        assert signal["private_sanitization"]["fields"] == 4 - public_fields
        assert f"{public_fields} public field(s)" in format_publication_dlp_details(signal)
        receipts.append(receipt)
        projected_results.append(projected)
    assert projected_results[0]["comments"] == projected_results[1]["comments"]
    assert receipts[0]["omitted"] != receipts[1]["omitted"]


@pytest.mark.parametrize(
    "technical",
    (
        "version #60; 2020.1.10",
        "network ::ffff:192.0.2.1/96",
        "network 192.0.2.100/255.255.255.255",
    ),
)
@pytest.mark.parametrize(
    "suffix",
    (
        "",
        "; Call +1 202 555 0142",
        "; person&#64;example.invalid",
        '; login_password: "synthetic-secret"',
    ),
)
def test_technical_finding_survives_publication_without_exempting_contacts(technical, suffix):
    comment = {
        "path": "src/example.py",
        "content": f"Assert the technical value `{technical}` independently." + suffix,
        "existing_code": "assert comparison == expected",
        "start_line": 1,
        "end_line": 1,
    }
    payload = {
        "status": "complete",
        "comments": [comment],
        "warnings": [],
        "manifest": _payload(public_fields=2)["manifest"],
    }
    projected, receipt, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    if suffix:
        assert filtered and receipt["state"] == "publication-filtered"
        assert projected["comments"] == [] and receipt["omitted"]["comments"] == 1
    else:
        assert not filtered and receipt["state"] == "passed"
        assert projected["comments"] == [comment]
