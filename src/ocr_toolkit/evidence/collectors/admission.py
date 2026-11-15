"""Admit optional facts and deltas after the complete mandatory evidence envelope."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from ocr_toolkit.evidence.collectors.projections import fact_deltas
from ocr_toolkit.evidence.coverage import coverage_domains
from ocr_toolkit.evidence.model import CoverageState, EvidenceRecord
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from ocr_toolkit.evidence.store.contracts import EvidenceStoreBudgetError
from ocr_toolkit.evidence.store.serialization import encoded_size
from ocr_toolkit.evidence.store.values import delta_payload, safe_deltas, safe_diagnostic

BYTE_OMISSION = "typed evidence was truncated by store byte limit"


def _added_diagnostic_size(messages: list[str], before: int) -> int:
    """Count only newly appended notices, including their array separators."""
    return sum(
        encoded_size(safe_diagnostic(messages[index])) + int(index > 0)
        for index in range(before, len(messages))
    )


def _incomplete_coverage(store: EvidenceStore, kinds: set[str]) -> None:
    """Persist admission loss structurally, independently of redacted diagnostic prose."""
    domains = frozenset(domain for kind in kinds for domain in coverage_domains(kind))
    affected = {
        item.semantic_identity for item in store._coverage.values() if item.domain in domains
    }
    if not affected:
        return
    replacements = {
        item.id: replace(item, state=CoverageState.PARTIAL)
        for item in store._coverage.values()
        if item.domain in domains and item.state is CoverageState.COMPLETE
    }
    # Preserve the collector's source reasons. Admission only lowers completeness;
    # fixed-size content IDs and shorter state values cannot grow this envelope.
    store._coverage = {
        replacement.id: replacement
        for item in store._coverage.values()
        for replacement in (replacements.get(item.id, item),)
    }
    for name in ("base", "head"):
        snapshot = getattr(store, name)
        if snapshot is not None:
            setattr(
                store,
                name,
                replace(
                    snapshot,
                    coverage=tuple(replacements.get(item.id, item) for item in snapshot.coverage),
                ),
            )
    store.deltas = tuple(
        delta
        for delta in store.deltas
        if delta.kind != "repository.evidence_coverage" or delta.identity not in affected
    )


def admit_typed_facts(store: EvidenceStore, records: list[EvidenceRecord]) -> None:
    """Keep bounded prefixes, suppress incomplete comparisons, and validate once per batch."""
    # This validation precedes every optional mutation. Reserve one explicit
    # completeness notice as part of the mandatory envelope, not invocation space.
    original_diagnostics = list(store.diagnostics)
    original_deltas = store.deltas
    original_ids = set(store._records)
    original_optional_count = store._optional_count
    size = len(store.to_json().encode("utf-8"))
    if not records:
        return
    notice = safe_diagnostic(BYTE_OMISSION)
    notice_cost = encoded_size(notice) + int(bool(store.diagnostics))
    store.add_diagnostic(BYTE_OMISSION)
    store.to_json()
    store.diagnostics = original_diagnostics.copy()
    ceiling = store.limits.max_bytes - store.reserved_bytes - notice_cost
    groups: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        groups[record.kind].append(record)

    for kind, candidates in groups.items():
        complete = True
        for record in candidates:
            previous_diagnostics = list(store.diagnostics)
            previous_count = len(store._records)
            accepted = store.add_optional(record)
            diagnostic_cost = _added_diagnostic_size(store.diagnostics, len(previous_diagnostics))
            admitted = (
                store._records[next(reversed(store._records))]
                if len(store._records) > previous_count
                else None
            )
            cost = diagnostic_cost + (
                encoded_size(admitted.to_dict()) + int(previous_count > 0)
                if admitted is not None
                else 0
            )
            if size + cost > ceiling:
                if admitted is not None:
                    store._records.pop(admitted.id)
                    store._kind_counts[admitted.kind] -= 1
                    store._optional_count -= 1
                store.diagnostics = previous_diagnostics
                complete = False
                break
            size += cost
            if not accepted:
                complete = False
                if store.record_limit_state(kind, optional=True) is not None:
                    break
        if complete:
            kind_records = tuple(
                record for record in store._records.values() if record.kind == kind
            )
            try:
                deltas = safe_deltas(fact_deltas(kind_records), store.limits.max_value_chars)
            except EvidenceStoreError as exc:
                if str(exc) != f"evidence value exceeds {store.limits.max_value_chars} characters":
                    raise
                # Individually valid facts can form an oversized multi-source
                # comparison. This is an optional projection, not malformed Git.
                deltas = ()
                complete = False
            delta_cost = sum(encoded_size(delta_payload(delta)) + 1 for delta in deltas)
            # The extra first separator is a conservative one-byte allowance.
            if (
                complete
                and size + delta_cost <= ceiling
                and len(store.deltas) + len(deltas) <= store.limits.max_records
            ):
                store.deltas += deltas
                size += delta_cost
                continue
        if any(
            record.component == "ansible" and kind.startswith("ansible.") for record in candidates
        ):
            raise EvidenceStoreError(
                "Ansible topology facts exceed the atomic evidence store limits"
            ) from None
        # No semantic projection can claim a complete comparison for this kind,
        # even when a useful prefix of its records still fits.
        _incomplete_coverage(store, {kind})
        previous = list(store.diagnostics)
        store.add_diagnostic(f"typed {kind} comparison incomplete; unsafe semantic deltas omitted")
        extra = _added_diagnostic_size(store.diagnostics, len(previous))
        if size + extra <= ceiling:
            size += extra
        else:
            store.diagnostics = previous
            if notice not in store.diagnostics:
                store.add_diagnostic(BYTE_OMISSION)
                size += notice_cost
                ceiling += notice_cost
    store.deltas = tuple(
        sorted(store.deltas, key=lambda item: (item.kind, item.component, item.identity))
    )
    try:
        store.to_json()
    except EvidenceStoreBudgetError:
        # A changed serializer must not turn an optional estimate into a hard
        # review failure or leave dangling deltas. The mandatory envelope passed.
        if any(
            record.component == "ansible" and record.kind.startswith("ansible.")
            for record in records
        ):
            raise EvidenceStoreError(
                "Ansible topology facts exceed the atomic evidence store limits"
            ) from None
        for key in tuple(store._records):
            if key not in original_ids:
                record = store._records.pop(key)
                store._kind_counts[record.kind] -= 1
        store._optional_count = original_optional_count
        store.deltas = original_deltas
        _incomplete_coverage(store, set(groups))
        store.diagnostics = original_diagnostics
        store.add_diagnostic(BYTE_OMISSION)
        store.to_json()
