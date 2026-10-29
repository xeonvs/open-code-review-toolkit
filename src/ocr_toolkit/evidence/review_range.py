"""Resolve and prove the Git topology supported by the native range engine."""

from __future__ import annotations

from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.review_range import ReviewRange


def resolve_review_range(reader: GitRepositoryReader, base_ref: str, head_ref: str) -> ReviewRange:
    """Resolve once and reject ranges whose merge base cannot equal their base.

    A proven ancestor remains usable in a shallow checkout. An unproven shallow
    relation is rejected by the existing isolated ancestry reader, without any
    implicit fetch or fallback to a different range.
    """

    review_range = ReviewRange(reader.resolve_commit(base_ref), reader.resolve_commit(head_ref))
    if not reader.is_ancestor(review_range.base, review_range.head):
        raise RepositoryEvidenceError(
            "native range review requires base to be an ancestor of head; "
            "sibling, reverse and unrelated ranges are unsupported"
        )
    return review_range
