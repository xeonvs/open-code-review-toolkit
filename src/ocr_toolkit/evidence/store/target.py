"""Incremental admission of optional target facts after mandatory snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocr_toolkit.evidence.budgets import (
    MAX_TARGET_DEPENDENCY_RECORDS,
    MAX_TARGET_FILE_RECORDS,
    OPTIONAL_RECORDS_PER_KIND,
)
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceSnapshot, RefRole
from ocr_toolkit.evidence.store.contracts import EvidenceStoreBudgetError, EvidenceStoreError
from ocr_toolkit.evidence.store.serialization import encoded_size
from ocr_toolkit.evidence.store.values import safe_diagnostic

if TYPE_CHECKING:
    from ocr_toolkit.evidence.store.core import EvidenceStore


def add_target_records(store: EvidenceStore, records: tuple[EvidenceRecord, ...]) -> bool:
    """Check each incremental canonical cost and validate the whole batch once."""

    if store.target is None:
        raise EvidenceStoreError("target context requires its target snapshot")
    if len(records) > MAX_TARGET_FILE_RECORDS + MAX_TARGET_DEPENDENCY_RECORDS:
        raise EvidenceStoreError("target context batch exceeds its record limit")
    for record in records:
        if record.ref is not RefRole.TARGET:
            raise EvidenceStoreError("target context requires its target snapshot")
        if record.commit_sha != store.target.commit_sha:
            raise EvidenceStoreError("target context commit does not match its snapshot")
    original_target = store.target
    original_diagnostics = list(store.diagnostics)
    # Optional admission cannot hide a pre-existing mandatory budget failure.
    size = len(store.to_json().encode("utf-8"))
    additions: list[EvidenceRecord] = []
    complete = True
    for record in records:
        if record.id in store._records:
            continue
        if len(store._records) + len(
            store._coverage
        ) >= store.limits.max_records - store.reserved_records or (
            record.kind != "repository.file"
            and store._kind_counts[record.kind] >= OPTIONAL_RECORDS_PER_KIND
        ):
            complete = False
            continue
        previous_diagnostics = list(store.diagnostics)
        previous_count = len(store._records)
        accepted = store.add(record)
        # add() appends only bounded unique diagnostics; they share the byte pool.
        diagnostic_cost = sum(
            encoded_size(safe_diagnostic(item)) + int(index > 0)
            for index, item in enumerate(store.diagnostics)
            if index >= len(previous_diagnostics)
        )
        if not accepted:
            complete = False
            if size + diagnostic_cost <= store.limits.max_bytes - store.reserved_bytes - 256:
                size += diagnostic_cost
            else:
                store.diagnostics = previous_diagnostics
            continue
        if len(store._records) == previous_count:
            continue
        admitted = store._records[next(reversed(store._records))]
        cost = (
            encoded_size(admitted.to_dict())
            + int(previous_count > 0)
            + encoded_size(admitted.id)
            + int(bool(store.target.records))
            + diagnostic_cost
        )
        if size + cost > store.limits.max_bytes - store.reserved_bytes - 256:
            store._records.pop(admitted.id)
            store._kind_counts[admitted.kind] -= 1
            store.diagnostics = previous_diagnostics
            complete = False
            continue
        additions.append(admitted)
        store.target = EvidenceSnapshot(
            RefRole.TARGET,
            store.target.commit_sha,
            (*store.target.records, admitted),
            diagnostics=store.target.diagnostics,
        )
        size += cost
    try:
        store.to_json()
    except EvidenceStoreBudgetError:
        # A changed presentation/redaction cannot leave a partial atomic envelope.
        for admitted in additions:
            store._records.pop(admitted.id)
            store._kind_counts[admitted.kind] -= 1
        store.target = original_target
        store.diagnostics = original_diagnostics
        return False
    return complete
