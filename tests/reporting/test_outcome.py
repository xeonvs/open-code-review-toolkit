"""Shared review health must not imply a forge publication for local output."""

import pytest

from ocr_toolkit.reporting.outcome import FindingVisibility, review_outcome_line


@pytest.mark.parametrize("published", [False, True])
@pytest.mark.parametrize(
    ("status", "count", "warnings", "expected"),
    [
        ("success", 0, 0, "Review complete — no findings"),
        ("success", 2, 0, "Review complete — 2 findings{delivery}"),
        ("warning", 0, 1, "Review complete with warnings — no findings"),
        ("partial", 2, 0, "Review incomplete — 2 findings{delivery} from reviewed files"),
        (
            "budget_exceeded",
            0,
            0,
            "Review stopped at token budget — no findings in reviewed files",
        ),
        ("failed", 2, 0, "Review failed — no reliable review result was produced"),
        ("skipped", 0, 0, "Review skipped — no supported files changed"),
    ],
)
def test_shared_health_and_adapter_delivery(
    published: bool, status: str, count: int, warnings: int, expected: str
) -> None:
    rendered = review_outcome_line(
        findings=FindingVisibility(count=count, published=published),
        warning_count=warnings,
        outcome_status=status,
        outcome_message="",
    )
    assert rendered == "**" + expected.format(delivery=" published" if published else "") + "**"
    if not published:
        assert "published" not in rendered


def test_gitlab_visibility_preserves_partial_and_suppression_counts() -> None:
    assert review_outcome_line(
        findings=FindingVisibility(count=0, published=True, omitted=1, suppressed=2),
        warning_count=0,
        outcome_status="partial",
        outcome_message="token budget exhausted",
        unreviewed_file_count=3,
    ) == (
        "**Review stopped at token budget — no findings published from reviewed files; "
        "1 finding omitted by posting limit; 2 findings matched prior reviewer decisions; "
        "3 files not reviewed**"
    )
