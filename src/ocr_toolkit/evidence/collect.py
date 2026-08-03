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
    root: Path | None = None, *, base_ref: str | None = None, head_ref: str | None = None
) -> EvidenceStore:
    """Build one evidence store from immutable refs and existing bounded collectors."""

    reader = GitRepositoryReader(root or Path.cwd())
    base_sha, head_sha = _commit_refs(reader, base_ref, head_ref)
    changed = reader.changed_paths(base_sha, head_sha)
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
    store = EvidenceStore(base=base, head=head, deltas=file_deltas(base, head))
    typed_facts = [*base_facts, *head_facts]
    store.deltas = tuple(
        sorted(
            (*store.deltas, *fact_deltas(typed_facts), *coverage_deltas(all_coverage)),
            key=lambda item: (item.kind, item.component, item.identity),
        )
    )
    rejected_snapshot_records = [
        record for record in (*base.records, *head.records) if not store.add(record)
    ]
    if rejected_snapshot_records:
        # Snapshots and their record-id indexes are one atomic contract. Persisting a
        # partial record set would create an artifact that cannot be loaded safely.
        raise EvidenceStoreError(
            "repository snapshot records exceed the configured evidence store limits"
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
    for record in ordered_typed_facts:
        if not store.add(record):
            if record.component == "ansible" and record.kind.startswith("ansible."):
                raise EvidenceStoreError(
                    "Ansible topology facts exceed the atomic evidence store limits"
                )
            store.add_diagnostic("typed evidence was truncated by store limits")
            break
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
    ):
        store.add_diagnostic(diagnostic)
    return store
