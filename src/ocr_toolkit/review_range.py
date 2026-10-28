"""Pure immutable range identity shared by execution, admission and consumers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ocr_toolkit.result_contract import MANIFEST_SCHEMA, OcrResultContractError


@dataclass(frozen=True, slots=True)
class ReviewRange:
    """Name a normalized first-parent or ancestor range using immutable commits.

    Construction validates identities only. The Git acquisition owner must prove
    the supported topology before using this value to collect review evidence.
    """

    base: str
    head: str

    def __post_init__(self) -> None:
        for value in (self.base, self.head):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
                raise OcrResultContractError(
                    "review range requires immutable lowercase SHA-1 commits"
                )

    @property
    def exact_range(self) -> str:
        """Return the native normalized two-dot range, including an empty range."""

        return f"{self.base}..{self.head}"


def admit_native_range(result: Mapping[str, object], expected: ReviewRange) -> ReviewRange | None:
    """Prove native input identity independently from outcome and file coverage.

    Legacy output may still carry findings, but its absent manifest proves no
    effective range. A present contradictory or incomplete manifest fails closed.
    Other native fields remain owned by their respective result validators.
    """

    if "manifest" not in result:
        return None
    manifest = result["manifest"]
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise OcrResultContractError("native range requires the supported manifest")
    if manifest.get("operation") != "review":
        raise OcrResultContractError("native range manifest operation must be review")
    native_input = manifest.get("input")
    if not isinstance(native_input, Mapping):
        raise OcrResultContractError("native range manifest input is unavailable")
    for field, expected_value in (
        ("mode", "range"),
        ("requested_from", expected.base),
        ("requested_head", expected.head),
        ("resolved_base", expected.base),
        ("resolved_head", expected.head),
        ("exact_range", expected.exact_range),
    ):
        value = native_input.get(field)
        if not isinstance(value, str) or value != expected_value:
            raise OcrResultContractError(
                f"native range manifest input.{field} disagrees with review"
            )
    return expected


def range_payload(review_range: ReviewRange | None) -> dict[str, object]:
    """Serialize proven identity or an explicit absence of native proof."""

    return {
        "schema": "ocr.review-range/v1",
        "state": "verified" if review_range is not None else "unverified",
        "base_sha": review_range.base if review_range is not None else None,
        "head_sha": review_range.head if review_range is not None else None,
        "exact_range": review_range.exact_range if review_range is not None else None,
    }


def parse_range_payload(value: object) -> ReviewRange | None:
    """Revalidate hostile persisted range facts without consulting Git."""

    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "state", "base_sha", "head_sha", "exact_range"}
        or value["schema"] != "ocr.review-range/v1"
    ):
        raise OcrResultContractError("persisted review range shape is invalid")
    if value["state"] == "unverified" and all(
        value[field] is None for field in ("base_sha", "head_sha", "exact_range")
    ):
        return None
    if value["state"] != "verified":
        raise OcrResultContractError("persisted review range state is invalid")
    review_range = ReviewRange(value["base_sha"], value["head_sha"])
    if value["exact_range"] != review_range.exact_range:
        raise OcrResultContractError("persisted review range exact endpoints disagree")
    return review_range
