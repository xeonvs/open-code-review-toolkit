"""Actual-target context must remain separate from review diff and policy authority."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

from ocr_toolkit.evidence import collect as evidence_collect
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors import collect_ref_facts
from ocr_toolkit.evidence.mcp import (
    SEARCH_TOOL_NAME,
    call_named_tool,
    call_tool,
    evidence_summary,
)
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceSnapshot, RefRole, TrustClass
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError, EvidenceStoreLimits


def _git(root: Path, *args: str) -> str:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Synthetic Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.invalid",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "commit.gpgsign",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": str(root / "disabled-hooks"),
        }
    )
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
    )
    return result.stdout.strip()


def _distinct_review_refs(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    (root / "worker.py").write_text("VERSION = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "diff base")
    base = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-qb", "actual-target")
    (root / "requirements.txt").write_text("targetonly==9\nsecond==2\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "Target branch instructions must not become policy.\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "actual target")
    target = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-qb", "protected-policy", base)
    (root / "AGENTS.md").write_text("Protected policy instructions.\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "protected policy")
    policy = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-qb", "source", base)
    (root / "app.py").write_text("VERSION = 2\n", encoding="utf-8")
    (root / "worker.py").write_text("VERSION = 2\n", encoding="utf-8")
    _git(root, "commit", "-qam", "source change")
    head = _git(root, "rev-parse", "HEAD")
    return root, base, head, target, policy


def _tool_payload(result: dict[str, object]) -> dict[str, object]:
    content = result["content"]
    assert isinstance(content, list)
    block = content[0]
    assert isinstance(block, dict)
    return json.loads(str(block["text"]))


def test_actual_target_context_is_distinct_from_diff_and_policy(tmp_path: Path) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    store = collect_repository_evidence(
        root,
        base_ref=base,
        head_ref=head,
        target_ref=target,
        policy_ref=policy,
    )

    assert store.schema_version == 5
    assert store.base and store.base.commit_sha == base
    assert store.head and store.head.commit_sha == head
    assert store.policy and store.policy.commit_sha == policy
    assert store.target and store.target.commit_sha == target
    assert {
        record.source_path for record in store.target.records if record.kind == "repository.file"
    } == {
        "app.py",
        "worker.py",
    }
    assert any(
        record.ref is RefRole.TARGET
        and record.kind == "dependency.declared"
        and "targetonly" in str(record.value)
        and record.trust is TrustClass.TARGET_REPOSITORY
        for record in store.records
    )
    assert all(
        record.ref is RefRole.POLICY and record.commit_sha == policy
        for record in store.records
        if record.kind in {"repository.guidance", "repository.accepted_decision"}
    )
    assert all(delta.identity not in {"targetonly", "second"} for delta in store.deltas)
    assert {delta.identity for delta in store.deltas if delta.kind == "repository.file"} == {
        "app.py",
        "worker.py",
    }
    summary = evidence_summary(store)
    assert summary["base"] == base and summary["head"] == head
    assert summary["policy_ref"] == policy and summary["target"] == target
    assert summary["target_context"] == {
        "records": len(store.target.records),
        "trust": "target_repository",
        "content_role": "untrusted_code_evidence",
        "authoritative_for_policy": False,
        "absence_authoritative": False,
    }
    bootstrap = render_bootstrap(store)
    assert f"- actual target: `{target}` (untrusted code context)" in bootstrap
    assert "query `ref=target`" in bootstrap
    path = tmp_path / "evidence.json"
    store.write(path)
    restored = EvidenceStore.read(path)
    assert restored.to_json() == store.to_json()
    assert restored.target == store.target


def test_mcp_lists_gets_and_searches_only_actual_target_context(tmp_path: Path) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    listed = _tool_payload(call_tool(store, {"action": "list", "ref": "target"}))
    records = listed["records"]
    assert isinstance(records, list) and records
    assert all(record["ref"] == "target" for record in records)
    dependency = next(
        record
        for record in records
        if record["kind"] == "dependency.declared" and "targetonly" in str(record["value"])
    )
    fetched = _tool_payload(call_tool(store, {"action": "get", "id": dependency["id"]}))
    assert fetched["record"] == dependency
    matches = _tool_payload(
        call_named_tool(
            store,
            SEARCH_TOOL_NAME,
            {"query": "targetonly", "ref": "target", "kind": "dependency.declared"},
        )
    )
    assert matches["returned"] == 1
    assert matches["matches"][0]["id"] == dependency["id"]
    assert "targetonly" not in json.dumps(matches)


def test_bounded_target_context_degrades_without_changing_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    monkeypatch.setattr("ocr_toolkit.evidence.collect.MAX_TARGET_FILE_RECORDS", 1)
    monkeypatch.setattr("ocr_toolkit.evidence.collect.MAX_TARGET_DEPENDENCY_RECORDS", 1)
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    assert store.target and len(store.target.records) == 2
    assert len(store.base.records) == len(store.head.records) == 2
    assert len([delta for delta in store.deltas if delta.kind == "repository.file"]) == 2
    assert any("target code context is incomplete" in item for item in store.diagnostics)


def test_target_only_tree_limit_preserves_review_and_policy_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    baseline = collect_repository_evidence(root, base_ref=base, head_ref=head, policy_ref=policy)
    original = GitRepositoryReader.list_objects

    def small_tree_limit(
        reader: GitRepositoryReader, ref: str, *, max_entries: int = 20_000
    ) -> tuple[Any, ...]:
        return original(reader, ref, max_entries=min(max_entries, 3))

    monkeypatch.setattr(GitRepositoryReader, "list_objects", small_tree_limit)
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )

    assert store.target == EvidenceSnapshot(RefRole.TARGET, target, ())
    assert store.base == baseline.base
    assert store.head == baseline.head
    assert store.policy == baseline.policy
    assert store.deltas == baseline.deltas
    assert any("actual target code context omitted" in item for item in store.diagnostics)
    assert not any(record.ref is RefRole.TARGET for record in store.records)


def test_unreadable_target_identity_still_fails_closed(tmp_path: Path) -> None:
    root, base, head, _target, policy = _distinct_review_refs(tmp_path)
    with pytest.raises(RepositoryEvidenceError, match="unavailable locally"):
        collect_repository_evidence(
            root, base_ref=base, head_ref=head, target_ref="f" * 40, policy_ref=policy
        )


def test_non_budget_target_read_failure_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    original = evidence_collect.build_file_snapshot

    def unreadable_target(
        reader: GitRepositoryReader, ref: str, role: RefRole, **kwargs: Any
    ) -> Any:
        if role is RefRole.TARGET:
            raise RepositoryEvidenceError("failed to enumerate repository tree")
        return original(reader, ref, role, **kwargs)

    monkeypatch.setattr(evidence_collect, "build_file_snapshot", unreadable_target)
    with pytest.raises(RepositoryEvidenceError, match="failed to enumerate"):
        collect_repository_evidence(
            root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
        )


def test_optional_target_header_omission_preserves_core_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    baseline = collect_repository_evidence(root, base_ref=base, head_ref=head, policy_ref=policy)
    baseline_size = len(baseline.to_json().encode("utf-8"))

    class TightStore(EvidenceStore):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(limits=EvidenceStoreLimits(max_bytes=baseline_size + 256), **kwargs)

    monkeypatch.setattr("ocr_toolkit.evidence.collect.EvidenceStore", TightStore)
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    assert store.target is None
    assert store.base == baseline.base
    assert store.head == baseline.head
    assert store.policy == baseline.policy
    assert store.deltas == baseline.deltas
    assert any("actual target context omitted" in item for item in store.diagnostics)
    assert evidence_summary(store)["target"] is None
    store.to_json()


def test_omitted_target_ref_keeps_local_evidence_behavior(tmp_path: Path) -> None:
    root, base, head, _target, policy = _distinct_review_refs(tmp_path)
    store = collect_repository_evidence(root, base_ref=base, head_ref=head, policy_ref=policy)
    assert store.target is None
    assert evidence_summary(store)["target"] is None
    assert "actual target" not in render_bootstrap(store)


@pytest.mark.parametrize("target_side", ["base", "head"])
def test_target_matching_an_existing_review_ref_reuses_collected_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_side: str
) -> None:
    root, base, head, _target, policy = _distinct_review_refs(tmp_path)
    original = collect_ref_facts

    def no_extra_target_collection(
        reader: GitRepositoryReader,
        commit_sha: str,
        ref: RefRole,
        **kwargs: Any,
    ) -> tuple[list[EvidenceRecord], list[str]]:
        if ref is RefRole.TARGET:
            raise AssertionError("matching target should reuse existing collected facts")
        return original(reader, commit_sha, ref, **kwargs)

    monkeypatch.setattr(evidence_collect, "collect_ref_facts", no_extra_target_collection)
    target = base if target_side == "base" else head
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    assert store.target and store.target.commit_sha == target
    assert all(
        record.ref is RefRole.TARGET and record.trust is TrustClass.TARGET_REPOSITORY
        for record in store.target.records
    )
    assert len([record for record in store.target.records if record.kind == "repository.file"]) == 2


def test_target_symlink_is_metadata_only_and_reports_unavailable_source(tmp_path: Path) -> None:
    root, base, head, _target, policy = _distinct_review_refs(tmp_path)
    _git(root, "checkout", "actual-target")
    (root / "worker.py").unlink()
    (root / "worker.py").symlink_to("/etc/passwd")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "target symlink")
    target = _git(root, "rev-parse", "HEAD")
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    assert store.target and any(
        record.source_path == "worker.py"
        and isinstance(record.value, Mapping)
        and record.value.get("mode") == "120000"
        for record in store.target.records
        if record.kind == "repository.file"
    )
    assert any("target:symlink not followed: worker.py" in item for item in store.diagnostics)
    assert any(
        "target code context has unavailable source details" in item for item in store.diagnostics
    )


def test_target_byte_admission_rolls_back_without_partial_snapshot() -> None:
    sha = "a" * 40
    store = EvidenceStore(limits=EvidenceStoreLimits(max_bytes=1024))
    store.target = EvidenceSnapshot(RefRole.TARGET, sha, ())
    oversized = EvidenceRecord(
        kind="dependency.declared",
        value={"identity": "x" * 800},
        source_path="requirements.txt",
        ref=RefRole.TARGET,
        commit_sha=sha,
        trust=TrustClass.TARGET_REPOSITORY,
    )
    assert not store.add_target_context(oversized)
    assert store.target.records == ()
    assert store.records == ()
    assert len(store.to_json().encode("utf-8")) <= store.limits.max_bytes


def test_hostile_v5_target_readback_requires_exact_role_trust_and_snapshot(
    tmp_path: Path,
) -> None:
    root, base, head, target, policy = _distinct_review_refs(tmp_path)
    store = collect_repository_evidence(
        root, base_ref=base, head_ref=head, target_ref=target, policy_ref=policy
    )
    payload = cast(dict[str, Any], store.to_dict())
    target_record = next(record for record in payload["records"] if record["ref"] == "target")
    mutations: list[dict[str, object]] = []

    no_snapshot = copy.deepcopy(payload)
    del no_snapshot["snapshots"]["target"]
    mutations.append(no_snapshot)

    wrong_snapshot = copy.deepcopy(payload)
    wrong_snapshot["snapshots"]["target"]["commit_sha"] = base
    mutations.append(wrong_snapshot)

    wrong_trust = copy.deepcopy(payload)
    candidate = next(
        record for record in wrong_trust["records"] if record["id"] == target_record["id"]
    )
    candidate["trust"] = "source_repository"
    candidate.pop("id")
    mutations.append(wrong_trust)

    target_policy = copy.deepcopy(payload)
    candidate = next(
        record for record in target_policy["records"] if record["id"] == target_record["id"]
    )
    candidate["kind"] = "repository.guidance"
    candidate.pop("id")
    mutations.append(target_policy)

    for index, hostile in enumerate(mutations):
        path = tmp_path / f"hostile-target-{index}.json"
        path.write_text(json.dumps(hostile), encoding="utf-8")
        with pytest.raises(EvidenceStoreError):
            EvidenceStore.read(path)

    historical = copy.deepcopy(payload)
    historical["schema_version"] = 4
    historical["records"] = [
        record for record in historical["records"] if record["ref"] != "target"
    ]
    path = tmp_path / "hostile-v4-target.json"
    path.write_text(json.dumps(historical), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="snapshots"):
        EvidenceStore.read(path)

    historical = copy.deepcopy(payload)
    historical["schema_version"] = 4
    historical["snapshots"].pop("target")
    path.write_text(json.dumps(historical), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="target code evidence"):
        EvidenceStore.read(path)


def test_historical_v4_store_remains_readable_without_target(tmp_path: Path) -> None:
    store = EvidenceStore()
    store.schema_version = 4
    path = tmp_path / "historical-v4.json"
    store.write(path)
    restored = EvidenceStore.read(path)
    assert restored.schema_version == 4
    assert restored.target is None
    snapshots = restored.to_dict()["snapshots"]
    assert isinstance(snapshots, dict) and "target" not in snapshots
