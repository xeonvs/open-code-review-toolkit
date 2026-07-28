"""Collect bounded repository context into the common evidence store."""

from __future__ import annotations

import os
from pathlib import Path

from ocr_toolkit.context.categorize import categorize_files
from ocr_toolkit.context.render import build_context
from ocr_toolkit.evidence.collectors import collect_ref_facts, fact_deltas
from ocr_toolkit.evidence.model import Confidence, EvidenceRecord, RefRole, TrustClass
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    build_file_snapshot,
    file_deltas,
)
from ocr_toolkit.evidence.store import EvidenceStore


def _commit_refs(reader: GitRepositoryReader) -> tuple[str, str]:
    """Resolve explicit CI refs, falling back to the local parent and HEAD."""

    head_ref = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA") or os.environ.get(
        "CI_COMMIT_SHA", "HEAD"
    )
    base_ref = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
    if not base_ref:
        try:
            base_ref = reader.resolve_commit(f"{head_ref}^")
        except RepositoryEvidenceError:
            base_ref = reader.resolve_commit(head_ref)
    return reader.resolve_commit(base_ref), reader.resolve_commit(head_ref)


def _component_for_path(path: str) -> str:
    """Return the stable first-directory component or repository root."""

    return path.split("/", 1)[0] if "/" in path else "repository"


def _legacy_projection(markdown: str, *, sha: str) -> EvidenceRecord:
    """Retain legacy Markdown only as a temporary parity projection."""

    return EvidenceRecord(
        kind="repository.context",
        value=markdown,
        source_path=".review-context/legacy-background.md",
        ref=RefRole.HEAD,
        commit_sha=sha,
        provenance="legacy.context_projection",
        confidence=Confidence.DERIVED,
        trust=TrustClass.DERIVED,
    )


def collect_repository_evidence(root: Path | None = None) -> EvidenceStore:
    """Build one evidence store from immutable refs and existing bounded collectors."""

    reader = GitRepositoryReader(root or Path.cwd())
    base_sha, head_sha = _commit_refs(reader)
    changed = reader.changed_paths(base_sha, head_sha)
    base = build_file_snapshot(reader, base_sha, RefRole.BASE, paths=changed)
    head = build_file_snapshot(reader, head_sha, RefRole.HEAD, paths=changed)
    store = EvidenceStore(base=base, head=head, deltas=file_deltas(base, head))
    base_facts, base_fact_diagnostics = collect_ref_facts(
        reader, base_sha, RefRole.BASE, changed_paths=changed
    )
    head_facts, head_fact_diagnostics = collect_ref_facts(
        reader, head_sha, RefRole.HEAD, changed_paths=changed
    )
    typed_facts = [*base_facts, *head_facts]
    store.deltas = tuple(
        sorted(
            (*store.deltas, *fact_deltas(typed_facts)),
            key=lambda item: (item.kind, item.component, item.identity),
        )
    )
    for record in (*base.records, *head.records):
        store.add(record)
    for record in typed_facts:
        if not store.add(record):
            store.add_diagnostic("typed evidence was truncated by store limits")
            break
    categories = categorize_files(list(changed))
    for category, paths in sorted(categories.items()):
        for path in paths:
            store.add(
                EvidenceRecord(
                    kind="component.kind",
                    value=category,
                    source_path=path,
                    ref=RefRole.HEAD,
                    commit_sha=head_sha,
                    component=_component_for_path(path),
                    provenance="context.categorize",
                    trust=TrustClass.SOURCE_REPOSITORY,
                )
            )
    store.add(_legacy_projection(build_context(), sha=head_sha))
    for diagnostic in (
        *base.diagnostics,
        *head.diagnostics,
        *base_fact_diagnostics,
        *head_fact_diagnostics,
    ):
        store.add_diagnostic(diagnostic)
    return store
