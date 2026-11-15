"""Pure structural evidence sizing and closed resource-exhaustion facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

MAX_EVIDENCE_RECORDS = 100_000
MAX_EVIDENCE_BYTES = 20_000_000
MAX_TREE_ENTRIES = 20_000
MAX_CHANGED_PATHS = 10_000
MAX_TARGET_FILE_RECORDS = 64
MAX_TARGET_DEPENDENCY_RECORDS = 64
OPTIONAL_RECORDS = 4_096
OPTIONAL_RECORDS_PER_KIND = 512
# Invocation facts and normalized MR intent are added by the runner after collection.
INVOCATION_RECORD_RESERVE = 8
INVOCATION_BYTE_RESERVE = 128_000


class EvidenceBudgetExceeded(ValueError):
    """Carry only validated numeric resource facts, never source content."""

    def __init__(self, actual: int, limit: int, unit: str, *, message: str | None = None) -> None:
        """Bind a closed hard-limit diagnostic to validated numeric facts and a resource unit."""
        if (
            type(actual) is not int
            or type(limit) is not int
            or not 0 < limit < actual
            or not isinstance(unit, str)
            or unit not in {"records", "bytes", "entries"}
        ):
            raise ValueError("invalid evidence budget facts")
        self.actual, self.limit, self.unit = actual, limit, unit
        super().__init__(
            message or f"repository evidence budget exceeded: {actual} {unit}, limit {limit}"
        )


@dataclass(frozen=True, slots=True)
class StructuralBudget:
    """Keep structural capacity independent from optional fact allowances."""

    max_records: int
    max_records_per_kind: int
    optional_records: int
    max_bytes: int = MAX_EVIDENCE_BYTES


def structural_budget(
    counts: Mapping[str, int], coverage_count: int, *, include_target: bool = False
) -> StructuralBudget:
    """Size complete snapshot/category indexes, preserving a bounded optional pool."""

    if (
        type(coverage_count) is not int
        or coverage_count < 0
        or type(include_target) is not bool
        or any(type(count) is not int or count < 0 for count in counts.values())
    ):
        raise ValueError("invalid structural evidence counts")
    required = sum(counts.values()) + coverage_count + INVOCATION_RECORD_RESERVE
    if required > MAX_EVIDENCE_RECORDS:
        raise EvidenceBudgetExceeded(required, MAX_EVIDENCE_RECORDS, "records")
    return StructuralBudget(
        min(MAX_EVIDENCE_RECORDS, required + OPTIONAL_RECORDS),
        min(
            MAX_EVIDENCE_RECORDS,
            max(
                OPTIONAL_RECORDS_PER_KIND,
                max(counts.values(), default=0),
                counts.get("repository.file", 0)
                + (MAX_TARGET_FILE_RECORDS if include_target else 0),
            ),
        ),
        min(OPTIONAL_RECORDS, MAX_EVIDENCE_RECORDS - required),
    )
