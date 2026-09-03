"""Collect bounded repository context into the common evidence store."""

from __future__ import annotations

import os
from pathlib import Path

from ocr_toolkit.evidence.categorize import categorize_paths
from ocr_toolkit.evidence.collectors import collect_ref_facts, fact_deltas
from ocr_toolkit.evidence.coverage import coverage_deltas
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceSnapshot, RefRole, TrustClass
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    build_file_snapshot,
    file_deltas,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from ocr_toolkit.evidence.store.contracts import POLICY_KINDS


def _commit_refs(
    reader: GitRepositoryReader, base_ref: str | None = None, head_ref: str | None = None
) -> tuple[str, str]:
    """Resolve explicit CI refs, falling back to the local parent and HEAD."""

    head_ref = (
        head_ref
        or os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA")
        or os.environ.get("CI_COMMIT_SHA", "HEAD")
    )
    base_ref = base_ref or os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
    if not base_ref:
        try:
            base_ref = reader.resolve_commit(f"{head_ref}^")
        except RepositoryEvidenceError:
            base_ref = reader.resolve_commit(head_ref)
    return reader.resolve_commit(base_ref), reader.resolve_commit(head_ref)


def _component_for_path(path: str) -> str:
    """Return the stable first-directory component or repository root."""

    return path.split("/", 1)[0] if "/" in path else "repository"


def collect_repository_evidence(
    root: Path | None = None,
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
    policy_ref: str | None = None,
    include_policy_records: bool = True,
) -> EvidenceStore:
    """Build evidence, optionally omitting target-derived policy authority records."""

    reader = GitRepositoryReader(root or Path.cwd())
    base_sha, head_sha = _commit_refs(reader, base_ref, head_ref)
    changed = reader.changed_paths(base_sha, head_sha)
    policy_sha = reader.resolve_commit(policy_ref) if policy_ref is not None else base_sha
    base = build_file_snapshot(reader, base_sha, RefRole.BASE, paths=changed)
    head = build_file_snapshot(reader, head_sha, RefRole.HEAD, paths=changed)
    base_paths = {record.source_path for record in base.records}
    head_paths = {record.source_path for record in head.records}
    base_coverage = []
    head_coverage = []
    base_facts, base_fact_diagnostics = collect_ref_facts(
        reader,
        base_sha,
        RefRole.BASE,
        changed_paths=changed,
        coverage_sink=base_coverage,
    )
    if include_policy_records:
        policy_facts, policy_diagnostics = collect_ref_facts(
            reader,
            policy_sha,
            RefRole.POLICY,
            changed_paths=changed,
        )
        policy_facts = [record for record in policy_facts if record.kind in POLICY_KINDS]
    else:
        policy_facts, policy_diagnostics = [], []
    policy = EvidenceSnapshot(
        RefRole.POLICY,
        policy_sha,
        tuple(policy_facts),
        diagnostics=tuple(policy_diagnostics),
    )
    head_facts, head_fact_diagnostics = collect_ref_facts(
        reader,
        head_sha,
        RefRole.HEAD,
        changed_paths=changed,
        coverage_sink=head_coverage,
    )
    base = EvidenceSnapshot(
        base.ref,
        base.commit_sha,
        base.records,
        diagnostics=base.diagnostics,
        coverage=tuple(base_coverage),
    )
    head = EvidenceSnapshot(
        head.ref,
        head.commit_sha,
        head.records,
        diagnostics=head.diagnostics,
        coverage=tuple(head_coverage),
    )
    all_coverage = tuple((*base.coverage, *head.coverage))
    snapshot_deltas = file_deltas(base, head)
    store = EvidenceStore(base=base, head=head, policy=policy)
    typed_facts = [*base_facts, *head_facts]
    rejected_snapshot_records = [
        record
        for record in (*base.records, *head.records, *policy.records)
        if not store.add(record)
    ]
    if rejected_snapshot_records:
        # Snapshots and their record-id indexes are one atomic contract. Persisting a
        # partial record set would create an artifact that cannot be loaded safely.
        raise EvidenceStoreError(
            "repository snapshot records exceed the configured evidence store limits"
        )
    store.policy = EvidenceSnapshot(
        RefRole.POLICY,
        policy_sha,
        tuple(
            record
            for record in store.records
            if record.ref is RefRole.POLICY and record.commit_sha == policy_sha
        ),
        diagnostics=policy.diagnostics,
    )
    for coverage in all_coverage:
        if not store.add_coverage(coverage):
            raise EvidenceStoreError(
                "repository snapshot coverage exceeds the configured evidence store limits"
            )
    ordered_typed_facts = sorted(
        typed_facts,
        key=lambda record: (
            0 if record.component == "ansible" and record.kind.startswith("ansible.") else 1,
            record.kind,
            record.source_path,
            record.id,
        ),
    )
    exhausted_kinds: set[str] = set()
    incomplete_delta_kinds: set[str] = set()
    for index, record in enumerate(ordered_typed_facts):
        if record.kind in exhausted_kinds:
            continue
        if not store.add(record):
            incomplete_delta_kinds.add(record.kind)
            if record.component == "ansible" and record.kind.startswith("ansible."):
                raise EvidenceStoreError(
                    "Ansible topology facts exceed the atomic evidence store limits"
                )
            limit_state = store.record_limit_state(record.kind)
            if limit_state == "global":
                store.add_diagnostic("typed evidence was truncated by the global store limit")
                incomplete_delta_kinds.update(
                    candidate.kind for candidate in ordered_typed_facts[index:]
                )
                break
            if limit_state == "kind":
                # A per-kind omission must not suppress later independent domains.
                store.add_diagnostic(f"typed {record.kind} evidence was truncated by store limits")
                exhausted_kinds.add(record.kind)
    for kind in sorted(incomplete_delta_kinds):
        store.add_diagnostic(f"typed {kind} comparison incomplete; unsafe semantic deltas omitted")
    # Deltas are projections of canonical accepted store records, never raw facts
    # or references to values that redaction, deduplication, or a budget omitted.
    store.deltas = tuple(
        sorted(
            (
                *snapshot_deltas,
                *fact_deltas(store.records, incomplete_kinds=incomplete_delta_kinds),
                *coverage_deltas(all_coverage),
            ),
            key=lambda item: (item.kind, item.component, item.identity),
        )
    )
    categories = categorize_paths(list(changed))
    categories_truncated = False
    for category, paths in sorted(categories.items()):
        for path in paths:
            in_head = path in head_paths
            in_base = path in base_paths
            if not in_head and not in_base:
                continue
            ref = RefRole.HEAD if in_head else RefRole.BASE
            if not store.add(
                EvidenceRecord(
                    kind="repository.change_category",
                    value={"category": category, "path": path},
                    source_path=path,
                    ref=ref,
                    commit_sha=head_sha if ref == RefRole.HEAD else base_sha,
                    component=_component_for_path(path),
                    provenance="evidence.categorize",
                    trust=(
                        TrustClass.SOURCE_REPOSITORY
                        if ref == RefRole.HEAD
                        else TrustClass.TARGET_REPOSITORY
                    ),
                )
            ):
                categories_truncated = True
    if categories_truncated:
        store.add_diagnostic("change-category evidence was truncated by store limits")
    for diagnostic in (
        *base.diagnostics,
        *head.diagnostics,
        *base_fact_diagnostics,
        *head_fact_diagnostics,
        *policy_diagnostics,
    ):
        store.add_diagnostic(diagnostic)
    return store
