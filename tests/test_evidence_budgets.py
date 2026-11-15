"""Real snapshot, bounded persistence and isolated optional-budget regressions."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from ocr_toolkit.evidence.budgets import (
    INVOCATION_RECORD_RESERVE,
    MAX_EVIDENCE_RECORDS,
    EvidenceBudgetExceeded,
    structural_budget,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.mcp import MAX_PAGE_SIZE, call_tool
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceSnapshot, RefRole, TrustClass
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError, EvidenceStoreLimits
from tests.test_evidence_repository import git


def _record(kind: str, value: str, path: str) -> EvidenceRecord:
    """Build a complete synthetic structural record with immutable provenance."""
    return EvidenceRecord(kind, value, path, RefRole.HEAD, "a" * 40)


@pytest.mark.parametrize("count", [255, 256, 257, 260, 413, 513, 1000])
def test_complete_large_snapshot_survives_real_store_and_mcp(tmp_path: Path, count: int) -> None:
    """Cross Git, persistence and paginated MCP with a complete large snapshot."""
    git(tmp_path, "init", "-q")
    for index in range(count):
        (tmp_path / f"file-{index:04}.txt").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    for index in range(count):
        (tmp_path / f"file-{index:04}.txt").write_text("head\n")
    git(tmp_path, "commit", "-qam", "head")
    head = git(tmp_path, "rev-parse", "HEAD")
    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    assert Counter(r.kind for r in store.records) == {
        "repository.file": 2 * count,
        "repository.change_category": count,
    }
    assert len(store.deltas) == count and not store.diagnostics
    assert store.base is not None and store.head is not None
    assert len(store.base.records) == len(store.head.records) == count
    target = tmp_path / "private" / "store.json"
    store.write(target)
    loaded = EvidenceStore.read(target)
    assert loaded.to_json() == store.to_json()
    assert len(json.loads(target.read_text())["snapshots"]["head"]["record_ids"]) == count
    cursor = None
    ids = set()
    while True:
        args = {
            "action": "list",
            "kind": "repository.file",
            "ref": "head",
            "page_size": MAX_PAGE_SIZE,
        }
        if cursor is not None:
            args["cursor"] = cursor
        result = call_tool(loaded, args)
        assert not result.get("isError"), result
        payload = json.loads(result["content"][0]["text"])
        ids.update(record["id"] for record in payload["records"])
        cursor = payload.get("next_cursor")
        if cursor is None:
            break
    assert ids == {r.id for r in store.head.records}


def test_target_never_borrows_reserved_late_invocation_records():
    """Protect invocation headroom from optional target records."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_records=10, max_records_per_kind=10),
        target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()),
        reserved_records=8,
    )
    assert store.add(_record("repository.manifest", "first", "first"))
    assert store.add(_record("repository.manifest", "second", "second"))
    assert not store.add_target_context((_target_record(0),))
    store.reserved_records = 0
    for i in range(8):
        assert store.add(_record("review.ci_context", f"value-{i}", f"late-{i}"))
    assert len(store.records) == 10


def test_target_does_not_borrow_structural_capacity_for_dependency_kind():
    """Keep structural per-kind growth separate from optional dependency capacity."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_records=2000, max_records_per_kind=1500),
        target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()),
    )
    for i in range(512):
        assert store.add_optional(_record("dependency.declared", f"value-{i}", f"decl-{i}"))
    assert not store.add_target_context((_target_record(0),))
    assert len(store.records) == 512 and not store.target.records


def test_large_structural_budget_keeps_bounded_target_file_room():
    """Reserve bounded optional target capacity beside a large structural snapshot."""
    counts = {"repository.file": 2000, "repository.change_category": 1000}
    budget = structural_budget(counts, 0, include_target=True)
    assert budget.max_records_per_kind == 2064
    limits = EvidenceStoreLimits(
        max_records=budget.max_records,
        max_records_per_kind=budget.max_records_per_kind,
        max_bytes=budget.max_bytes,
    )
    store = EvidenceStore(limits, target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()))
    for i in range(2000):
        assert store.add(_record("repository.file", "metadata", f"source-{i}"))
    targets = tuple(
        EvidenceRecord(
            "repository.file",
            "metadata",
            f"source-{i}",
            RefRole.TARGET,
            "b" * 40,
            trust=TrustClass.TARGET_REPOSITORY,
        )
        for i in range(64)
    )
    assert store.add_target_context(targets)
    assert len(store.target.records) == 64


def test_structural_capacity_never_expands_optional_per_kind_budget() -> None:
    """Keep typed fact admission capped independently of structural file growth."""
    store = EvidenceStore(EvidenceStoreLimits(max_records=10000, max_records_per_kind=5000))
    for index in range(512):
        assert store.add_optional(
            EvidenceRecord(
                kind="dependency.declared",
                value={"name": f"package-{index}"},
                source_path=f"manifest-{index}",
                ref=RefRole.HEAD,
                commit_sha="a" * 40,
            )
        )
    record = EvidenceRecord(
        kind="dependency.declared",
        value={"name": "another"},
        source_path="another-manifest",
        ref=RefRole.HEAD,
        commit_sha="a" * 40,
    )
    assert not store.add_optional(record)
    assert store.record_limit_state(record.kind, optional=True) == "kind"
    assert store.record_limit_state(record.kind) is None
    assert store.add_optional(next(r for r in store.records if r.source_path == "manifest-0"))
    assert len(store.records) == 512


def test_optional_pool_exhaustion_does_not_consume_structural_capacity() -> None:
    """Preserve structural admission when optional typed capacity is exhausted."""
    store = EvidenceStore(optional_records=1)
    record = _record("runtime.declared", "one", "one")
    assert store.add_optional(record)
    assert not store.add_optional(_record("container.image", "two", "two"))
    assert store.record_limit_state("container.image", optional=True) == "global"
    assert store.add(_record("repository.change_category", "category", "two"))
    assert len(store.records) == 2


def test_structural_budget_reserves_late_facts_at_absolute_record_ceiling() -> None:
    """Retain late invocation headroom at the absolute record limit."""
    budget = structural_budget(
        {"repository.file": MAX_EVIDENCE_RECORDS - INVOCATION_RECORD_RESERVE}, 0
    )
    assert budget.max_records == MAX_EVIDENCE_RECORDS and budget.optional_records == 0
    with pytest.raises(EvidenceBudgetExceeded) as error:
        structural_budget({"repository.file": MAX_EVIDENCE_RECORDS}, 1)
    assert error.value.unit == "records"
    assert error.value.actual == MAX_EVIDENCE_RECORDS + INVOCATION_RECORD_RESERVE + 1


@pytest.mark.parametrize(
    "counts,coverage", [({"file": True}, 0), ({"file": -1}, 0), ({}, True), ({}, -1)]
)
def test_invalid_structural_counts_have_no_budget_claim(counts, coverage) -> None:
    """Reject invalid sizing inputs before computing structural capacity."""
    with pytest.raises(ValueError, match="invalid structural"):
        structural_budget(counts, coverage)


@pytest.mark.parametrize(
    "actual,limit,unit",
    [(True, 1, "bytes"), (2, True, "bytes"), (1, 1, "bytes"), (2, 0, "records"), (2, 1, "paths")],
)
def test_invalid_budget_exception_facts_are_rejected(actual, limit, unit) -> None:
    """Keep resource diagnostics numeric, ordered and restricted to supported units."""
    with pytest.raises(ValueError, match="invalid evidence budget"):
        EvidenceBudgetExceeded(actual, limit, unit)


@pytest.mark.parametrize("scope", ["tree", "diff"])
def test_entry_overflow_is_typed_and_keeps_actual_reader_limit(tmp_path: Path, scope: str) -> None:
    """Preserve the exact tree or changed-path ceiling in reader failures."""
    git(tmp_path, "init", "-q")
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "tree")
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text("changed " + name)
    git(tmp_path, "commit", "-qam", "change")
    with pytest.raises(RepositoryEvidenceError) as error:
        reader = GitRepositoryReader(tmp_path)
        if scope == "tree":
            reader.list_objects("HEAD", max_entries=2)
        else:
            reader.changed_paths("HEAD~1", "HEAD", max_paths=2)
    assert isinstance(error.value, EvidenceBudgetExceeded)
    assert (error.value.actual, error.value.limit, error.value.unit) == (3, 2, "entries")


def test_streamed_byte_overflow_preserves_the_previous_private_file(tmp_path: Path) -> None:
    """Keep an existing private store intact when bounded serialization fails."""
    target = tmp_path / "store.json"
    target.write_text("old state")
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=1024))
    assert store.add(_record("repository.manifest", "界" * 800, "manifest"))
    with pytest.raises(EvidenceStoreError) as error:
        store.write(target)
    assert isinstance(error.value, EvidenceBudgetExceeded)
    assert error.value.actual > error.value.limit == 1024
    assert error.value.unit == "bytes"
    assert target.read_text() == "old state"
    assert list(tmp_path.iterdir()) == [target]


def test_byte_reserve_is_consumed_only_after_runner_releases_it() -> None:
    """Protect late byte headroom until orchestration explicitly releases it."""
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=2048), reserved_bytes=1500)
    assert store.add(_record("repository.manifest", "x" * 400, "manifest"))
    with pytest.raises(EvidenceBudgetExceeded):
        store.to_json()
    store.reserved_bytes = 0
    assert len(store.to_json().encode()) < 2048


def _target_record(index: int, value="bounded") -> EvidenceRecord:
    """Build a target-owned record bound to an immutable actual-target revision."""
    return EvidenceRecord(
        "dependency.declared",
        value,
        f"manifest-{index}",
        RefRole.TARGET,
        "b" * 40,
        trust=TrustClass.TARGET_REPOSITORY,
    )


@pytest.mark.parametrize("count", [1, 8, 64])
def test_target_batch_checks_canonical_store_only_twice(tmp_path, monkeypatch, count):
    """Verify target batches avoid per-record whole-store serialization."""
    store = EvidenceStore(target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()))
    calls = []
    original = EvidenceStore.to_json

    def observe(self):
        """Count real canonical serialization calls while preserving their behavior."""
        calls.append(len(self.records))
        return original(self)

    monkeypatch.setattr(EvidenceStore, "to_json", observe)
    assert store.add_target_context(tuple(_target_record(i, '界\\"' * 10) for i in range(count)))
    assert calls == [0, count]
    assert len(store.target.records) == count
    path = tmp_path / "store.json"
    store.write(path)
    assert EvidenceStore.read(path).target == store.target
    assert store.add_target_context((store.target.records[0],))
    assert len(store.records) == count


@pytest.mark.parametrize("case", ["missing", "role", "sha", "count"])
def test_target_batch_rejects_invalid_input_before_any_admission(case):
    """Reject malformed target batches before modifying shared store state."""
    store = EvidenceStore(target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()))
    records = (_target_record(0),)
    if case == "missing":
        store.target = None
    elif case == "role":
        records += (_record("dependency.declared", "bad", "other"),)
    elif case == "sha":
        records += (
            EvidenceRecord("dependency.declared", "bad", "other", RefRole.TARGET, "c" * 40),
        )
    else:
        records *= 129
    with pytest.raises(EvidenceStoreError):
        store.add_target_context(records)
    assert not store.records


def test_target_rejection_and_byte_limit_leave_consistent_indexes(tmp_path):
    """Preserve coherent records and indexes after target admission fails."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=2048), target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ())
    )
    assert not store.add_target_context((_target_record(0), _target_record(1, "界" * 3000)))
    assert len(store.records) == len(store.target.records) == 1
    path = tmp_path / "store.json"
    store.write(path)
    assert EvidenceStore.read(path).to_dict() == store.to_dict()
    assert len(path.read_bytes()) <= 2048


def test_target_oversized_value_rejection_retains_bounded_diagnostic():
    """Keep a useful bounded diagnostic when an optional target value is rejected."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_value_chars=8),
        target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()),
    )
    assert not store.add_target_context((_target_record(0, "x" * 40),))
    assert not store.records and store.diagnostics
    assert store.to_json()


def test_target_final_byte_guard_rolls_back_an_underestimated_batch(monkeypatch):
    """Roll back target additions if the final canonical size check fails."""
    from ocr_toolkit.evidence.store import target

    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=1200), target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ())
    )
    previous = store.to_dict()
    # Inject a failed size estimator; the actual final serializer remains real.
    monkeypatch.setattr(target, "encoded_size", lambda value: 0)
    assert not store.add_target_context(tuple(_target_record(i, "界" * 300) for i in range(4)))
    assert store.to_dict() == previous


def test_target_never_hides_a_preexisting_mandatory_byte_failure():
    """Propagate mandatory-store failure before considering optional target degradation."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=1024), target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ())
    )
    assert store.add(_record("repository.manifest", "x" * 1500, "manifest"))
    with pytest.raises(EvidenceBudgetExceeded):
        store.add_target_context((_target_record(0),))
    assert not store.target.records


def test_target_diagnostic_cannot_displace_prior_valid_state():
    """Prevent optional omission diagnostics from consuming protected prior capacity."""
    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=1024, max_value_chars=8),
        target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()),
        diagnostics=["x" * 500],
    )
    assert len(store.to_json().encode()) <= 1024
    previous = store.to_dict()
    assert not store.add_target_context((_target_record(0, "x" * 40),))
    assert store.to_dict() == previous


def test_target_redacted_duplicates_share_one_canonical_index(monkeypatch):
    """Deduplicate equivalent redacted target records before consuming admission budget."""
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-first-value")
    monkeypatch.setenv("GITLAB_API_TOKEN", "synthetic-second-value")
    store = EvidenceStore(target=EvidenceSnapshot(RefRole.TARGET, "b" * 40, ()))
    assert store.add_target_context(
        (_target_record(0, "synthetic-first-value"), _target_record(0, "synthetic-second-value"))
    )
    assert len(store.records) == len(store.target.records) == 1
    assert "synthetic-first-value" not in store.to_json()
    assert "synthetic-second-value" not in store.to_json()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"optional_records": True},
        {"optional_records": -1},
        {"optional_records": 4097},
        {"reserved_bytes": True},
        {"reserved_bytes": -1},
        {"reserved_bytes": 2000000},
    ],
)
def test_invalid_runtime_reserves_cannot_disable_bounding(kwargs):
    """Reject invalid runtime reserves rather than silently disabling headroom controls."""
    with pytest.raises(EvidenceStoreError, match="reserve"):
        EvidenceStore(**kwargs)
