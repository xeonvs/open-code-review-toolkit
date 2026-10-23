"""Collect bounded repository context into the common evidence store."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

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
from ocr_toolkit.evidence.store.contracts import POLICY_KINDS, TARGET_CONTEXT_KINDS

MAX_TARGET_FILE_RECORDS = 64
MAX_TARGET_DEPENDENCY_RECORDS = 64
MAX_TARGET_DIAGNOSTICS = 32


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


def _relevant_target_dependency(path: str, changed_paths: tuple[str, ...]) -> bool:
    """Select manifests in a changed path's own directory or an ancestor."""

    parent = PurePosixPath(path).parent.as_posix()
    return any(
        changed == path or parent == "." or changed.startswith(parent + "/")
        for changed in changed_paths
    )


def _add_target_diagnostic(store: EvidenceStore, message: str) -> bool:
    """Keep an optional target notice only when the base evidence still serializes."""

    prior_diagnostics = list(store.diagnostics)
    try:
        store.add_diagnostic(message)
        store.to_json()
    except EvidenceStoreError as exc:
        store.diagnostics = prior_diagnostics
        if str(exc) not in {
            "serialized evidence store exceeds its byte budget",
            "evidence diagnostic must contain between 1 and 1024 characters",
        }:
            raise
        return False
    return True


def _as_target_record(record: EvidenceRecord, target_sha: str) -> EvidenceRecord:
    """Reuse a collected code fact without inheriting its old ref or trust label."""

    return EvidenceRecord(
        kind=record.kind,
        value=record.value,
        source_path=record.source_path,
        ref=RefRole.TARGET,
        commit_sha=target_sha,
        component=record.component,
        provenance=record.provenance,
        confidence=record.confidence,
        trust=TrustClass.TARGET_REPOSITORY,
        sensitivity=record.sensitivity,
        staleness=record.staleness,
    )


def collect_repository_evidence(
    root: Path | None = None,
    *,
    base_ref: str | None = None,
    head_ref: str | None = None,
    policy_ref: str | None = None,
    target_ref: str | None = None,
    include_policy_records: bool = True,
) -> EvidenceStore:
    """Build B/H diff evidence, separate P policy, and optional untrusted T context."""

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
    if target_ref is not None:
        # The actual target may differ from both the historical diff base and
        # the protected policy branch. Its facts are optional code context and
        # must never consume the budget reserved for B/H/P or alter their deltas.
        store.to_json()  # A pre-existing B/H/P budget failure remains a normal error.
        target_sha = reader.resolve_commit(target_ref)
        store.target = EvidenceSnapshot(RefRole.TARGET, target_sha, ())
        try:
            header_size = len(store.to_json().encode("utf-8"))
        except EvidenceStoreError as exc:
            if str(exc) != "serialized evidence store exceeds its byte budget":
                raise
            header_size = store.limits.max_bytes
        if header_size > store.limits.max_bytes - 256:
            store.target = None
            _add_target_diagnostic(store, "actual target context omitted by evidence byte limit")
            return store
        if target_sha in {base_sha, head_sha}:
            # The common unchanged-target case needs no third repository scan.
            prior = base if target_sha == base_sha else head
            prior_facts = base_facts if target_sha == base_sha else head_facts
            target_files = EvidenceSnapshot(
                RefRole.TARGET,
                target_sha,
                tuple(_as_target_record(record, target_sha) for record in prior.records),
                diagnostics=prior.diagnostics,
            )
            target_facts = [_as_target_record(record, target_sha) for record in prior_facts]
            target_fact_diagnostics: list[str] = []
        else:
            try:
                target_files = build_file_snapshot(
                    reader, target_sha, RefRole.TARGET, paths=changed
                )
                target_facts, target_fact_diagnostics = collect_ref_facts(
                    reader, target_sha, RefRole.TARGET, changed_paths=changed
                )
            except RepositoryEvidenceError as exc:
                if str(exc) != "repository tree exceeds the bounded entry limit":
                    raise
                # T's commit identity was resolved before this optional scan.
                # A target-only tree limit cannot change B/H/P or their deltas.
                _add_target_diagnostic(
                    store, "actual target code context omitted by repository tree entry limit"
                )
                return store
        diagnostics = (*target_files.diagnostics, *target_fact_diagnostics)
        target_diagnostics = diagnostics[:MAX_TARGET_DIAGNOSTICS]
        files = target_files.records[:MAX_TARGET_FILE_RECORDS]
        dependencies = tuple(
            record
            for record in target_facts
            if record.kind in TARGET_CONTEXT_KINDS - {"repository.file"}
            and _relevant_target_dependency(record.source_path, changed)
        )
        dependencies = tuple(
            sorted(dependencies, key=lambda item: (item.kind, item.source_path, item.id))
        )
        selected_dependencies = dependencies[:MAX_TARGET_DEPENDENCY_RECORDS]
        omitted = (
            len(target_files.records) > MAX_TARGET_FILE_RECORDS
            or len(dependencies) > MAX_TARGET_DEPENDENCY_RECORDS
        )
        for record in (*files, *selected_dependencies):
            if not store.add_target_context(record):
                omitted = True
        if omitted:
            _add_target_diagnostic(
                store, "target code context is incomplete due to bounded evidence limits"
            )
        if diagnostics:
            _add_target_diagnostic(store, "target code context has unavailable source details")
        for diagnostic in target_diagnostics:
            if not _add_target_diagnostic(store, f"target:{diagnostic}"):
                break
        if len(diagnostics) > MAX_TARGET_DIAGNOSTICS:
            _add_target_diagnostic(store, "target collection diagnostics were truncated")
    return store
