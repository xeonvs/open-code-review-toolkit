"""Optional facts and semantic deltas cannot exhaust mandatory evidence or invocation space."""

import json
from dataclasses import replace

import pytest

from ocr_toolkit.evidence import collect
from ocr_toolkit.evidence.collectors.admission import BYTE_OMISSION, admit_typed_facts
from ocr_toolkit.evidence.mcp import COVERAGE_TOOL_NAME, call_named_tool
from ocr_toolkit.evidence.model import (
    CoverageRecord,
    CoverageState,
    EvidenceRecord,
    EvidenceSnapshot,
    RefRole,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError, EvidenceStoreLimits
from tests.test_evidence_repository import git


def fact(index=0, *, kind="dependency.declared", size=300, role=RefRole.HEAD, component="app"):
    """Create a UTF-8-heavy typed fact with an immutable semantic identity."""
    return EvidenceRecord(
        kind,
        {"identity": f"package-{index}", "fact": "界" * size},
        "manifest",
        role,
        "a" * 40,
        component=component,
    )


@pytest.mark.parametrize("limit", [2000, 2400, 4000])
def test_optional_bytes_include_records_deltas_and_diagnostics(tmp_path, limit):
    """Persist coherent bounded prefixes, without unsafe deltas for incomplete kinds."""
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=limit), reserved_bytes=128)
    admit_typed_facts(store, [fact(i) for i in range(8)])
    assert store.records and len(store.records) < 8
    assert not store.deltas
    assert any("comparison incomplete" in message for message in store.diagnostics)
    path = tmp_path / "store"
    store.write(path)
    assert len(path.read_bytes()) <= limit - 128
    assert EvidenceStore.read(path).to_json() == store.to_json()
    store.reserved_bytes = 0
    assert store.add(
        EvidenceRecord("review.ci_context", "late", "context", RefRole.SHARED, "a" * 40)
    )
    assert len(store.to_json().encode()) <= limit


def test_delta_bytes_can_exhaust_capacity_even_when_all_records_fit():
    """Reject the complete-delta claim when its values exceed the remaining byte pool."""
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=2000))
    admit_typed_facts(store, [fact()])
    assert len(store.records) == 1
    assert not store.deltas
    assert any("comparison incomplete" in message for message in store.diagnostics)
    assert store.to_json()


def test_independent_later_kind_survives_an_oversized_optional_kind():
    """Do not stop independent small domains when a preceding value cannot fit."""
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=2400))
    admit_typed_facts(store, [fact(size=1000), fact(kind="runtime.declared", size=3)])
    assert [record.kind for record in store.records] == ["runtime.declared"]
    assert [delta.kind for delta in store.deltas] == ["runtime.declared"]
    assert store.to_json()


def test_final_size_guard_rolls_back_optional_records_and_deltas(monkeypatch):
    """A faulty incremental estimate still leaves the validated mandatory envelope intact."""
    from ocr_toolkit.evidence.collectors import admission

    store = EvidenceStore(EvidenceStoreLimits(max_bytes=1600))
    monkeypatch.setattr(admission, "encoded_size", lambda _value: 0)
    admit_typed_facts(store, [fact(i) for i in range(3)])
    assert not store.records and not store.deltas
    assert store.diagnostics == [BYTE_OMISSION]
    assert store.to_json()


def test_ordinary_optional_errors_are_not_converted_into_budget_omission():
    """An unregistered kind remains an invalid producer contract."""
    store = EvidenceStore()
    with pytest.raises(EvidenceStoreError, match="unregistered"):
        admit_typed_facts(store, [fact(kind="unregistered")])


def test_ansible_topology_remains_atomic_on_optional_byte_overflow():
    """Ansible topology cannot be presented as a silently incomplete prefix."""
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=1600))
    with pytest.raises(EvidenceStoreError, match="Ansible topology"):
        admit_typed_facts(store, [fact(kind="ansible.playbook", component="ansible")])


def test_optional_admission_avoids_per_record_full_serialization(monkeypatch):
    """A larger batch still crosses the canonical serializer a fixed number of times."""
    original = EvidenceStore.to_json
    calls = []

    def observed(store):
        """Observe the actual serialization boundary, preserving its checks."""
        calls.append(len(store.records))
        return original(store)

    monkeypatch.setattr(EvidenceStore, "to_json", observed)
    store = EvidenceStore()
    admit_typed_facts(store, [fact(i, size=3) for i in range(100)])
    assert calls == [0, 0, 100]
    assert len(store.deltas) == 100


def test_count_limit_and_rejected_values_share_byte_accounting_without_hiding_other_kinds():
    """Keep per-kind count degradation independent of other domains and invalid values."""
    store = EvidenceStore(EvidenceStoreLimits(max_records=10, max_records_per_kind=2))
    admit_typed_facts(
        store, [fact(i, size=3) for i in range(3)] + [fact(kind="runtime.declared", size=3)]
    )
    assert len(store.records) == 3
    assert [delta.kind for delta in store.deltas] == ["runtime.declared"]
    limited = EvidenceStore(EvidenceStoreLimits(max_value_chars=100))
    admit_typed_facts(limited, [fact(size=300), fact(1, size=3)])
    assert len(limited.records) == 1 and not limited.deltas
    assert any("omitted oversized" in message for message in limited.diagnostics)
    assert limited.to_json()


def test_minimal_global_notice_fits_when_a_per_kind_notice_does_not():
    """Preserve explicit unknown completeness at the final few available bytes."""
    probe = EvidenceStore()
    assert probe.add(fact(size=500))
    limit = len(probe.to_json().encode()) + len(BYTE_OMISSION) + 8
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=limit))
    admit_typed_facts(store, [fact(size=500), fact(1, kind="runtime.declared", size=1000)])
    assert store.records and not store.deltas
    assert store.diagnostics == [BYTE_OMISSION]
    assert len(store.to_json().encode()) <= limit


def test_empty_optional_batch_and_real_mandatory_failure_are_distinct():
    """An empty batch is inert; an already oversized mandatory envelope still fails."""
    from ocr_toolkit.evidence.budgets import EvidenceBudgetExceeded

    store = EvidenceStore(EvidenceStoreLimits(max_bytes=1024))
    before = store.to_dict()
    admit_typed_facts(store, [])
    assert store.to_dict() == before
    assert store.add(fact(size=500))
    with pytest.raises(EvidenceBudgetExceeded):
        admit_typed_facts(store, [fact(1, size=3)])
    assert len(store.records) == 1 and not store.diagnostics


def test_fallback_preserves_mandatory_records_and_atomic_ansible_errors(monkeypatch):
    """Estimator failure never drops prior records or silently degrades atomic topology."""
    from ocr_toolkit.evidence.collectors import admission

    monkeypatch.setattr(admission, "encoded_size", lambda _value: 0)
    store = EvidenceStore(EvidenceStoreLimits(max_bytes=2000))
    original = fact(99, kind="repository.manifest", size=3)
    assert store.add(original)
    admit_typed_facts(store, [fact(i) for i in range(3)])
    assert store.records == (original,) and store.diagnostics == [BYTE_OMISSION]
    atomic = EvidenceStore(EvidenceStoreLimits(max_bytes=2000))
    with pytest.raises(EvidenceStoreError, match="Ansible topology"):
        admit_typed_facts(
            atomic, [fact(i, kind="ansible.playbook", component="ansible") for i in range(3)]
        )


def test_oversized_composed_delta_withholds_comparison_without_losing_records():
    """Two valid source facts can exceed the independent delta-value budget."""
    store = EvidenceStore(EvidenceStoreLimits(max_value_chars=30_000))
    left = fact(size=20_000)
    right = replace(left, source_path="another-manifest")
    admit_typed_facts(store, [left, right])
    assert len(store.records) == 2 and not store.deltas
    assert any("comparison incomplete" in message for message in store.diagnostics)
    assert store.to_json()


def test_redacted_omission_notice_cannot_restore_authoritative_absence(tmp_path, monkeypatch):
    """Persisted scoped coverage remains partial even if a configured secret redacts the marker."""
    from ocr_toolkit.evidence.collectors import admission

    coverage = CoverageRecord(
        component="app",
        domain="dependency.declared",
        scope="manifest",
        state=CoverageState.COMPLETE,
        reasons=("bounded-source-complete",),
        ref=RefRole.HEAD,
        commit_sha="a" * 40,
    )
    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=2000),
        base=EvidenceSnapshot(RefRole.BASE, "b" * 40, ()),
        head=EvidenceSnapshot(RefRole.HEAD, "a" * 40, (), coverage=(coverage,)),
    )
    assert store.add_coverage(coverage)
    monkeypatch.setenv("OCR_LLM_TOKEN", "typed evidence")
    monkeypatch.setattr(admission, "encoded_size", lambda _value: 0)
    admit_typed_facts(store, [fact(i) for i in range(3)])
    assert not store.records
    path = tmp_path / "store"
    store.write(path)
    assert "typed evidence" not in path.read_text()
    monkeypatch.delenv("OCR_LLM_TOKEN")
    loaded = EvidenceStore.read(path)
    assert loaded.head.coverage == loaded.coverage
    result = call_named_tool(
        loaded,
        COVERAGE_TOOL_NAME,
        {"kind": "dependency.declared", "component": "app", "ref": "head", "path": "manifest"},
    )
    payload = json.loads(result["content"][0]["text"])
    assert payload["coverage_states"] == {"partial": 1}
    assert payload["state"] == "unknown" and not payload["absence_authoritative"]


@pytest.mark.parametrize(
    "domain",
    [
        "framework.declaration",
        "framework.resolution",
        "framework.configuration",
        "template.inventory",
    ],
)
def test_derived_coverage_domains_remain_partial_when_their_facts_are_omitted(
    tmp_path, monkeypatch, domain
):
    """A coverage domain need not share the spelling of its associated record kind."""
    from ocr_toolkit.evidence.collectors import admission
    from ocr_toolkit.evidence.frameworks.schema import FRAMEWORK_SCHEMA, TEMPLATE_SCHEMA

    template = domain == "template.inventory"
    kind = "template.file" if template else "framework.detected"
    scope = (
        "jinja2"
        if template
        else "aspnet-core"
        if domain == "framework.declaration"
        else "aspnet-core:aspnet-core"
    )
    records = []
    for path in ("one", "two", "three"):
        value = (
            {
                "schema_version": TEMPLATE_SCHEMA,
                "plugin": "jinja2",
                "engine": "jinja2",
                "detection": "jinja-extension",
                "rendered_extension": ".html",
                "object_sha": "b" * 40,
            }
            if template
            else {
                "schema_version": FRAMEWORK_SCHEMA,
                "plugin": "aspnet-core",
                "framework": "aspnet-core",
                "ecosystem": "dotnet",
                "category": "framework",
                "declarations": [
                    {
                        "package": "Microsoft.NET.Sdk.Web",
                        "scope": "web-sdk",
                        "declared_value": "unspecified",
                        "source_path": path,
                    }
                ],
                "resolutions": [],
                "version_state": "declared-only",
                "configuration_state": "complete",
                "configuration_paths": [path],
                "related": [],
                "replacement": None,
            }
        )
        records.append(
            EvidenceRecord(
                kind,
                {"identity": path if template else "aspnet-core:aspnet-core", "fact": value},
                path,
                RefRole.HEAD,
                "a" * 40,
                component=path,
            )
        )
    coverage = CoverageRecord(
        "one",
        domain,
        scope,
        CoverageState.COMPLETE,
        ("bounded-source-complete",),
        RefRole.HEAD,
        "a" * 40,
    )
    retained = EvidenceStore()
    assert retained.add_coverage(coverage)
    for record in records:
        assert retained.add(record)
    for queried in (domain, kind):
        query = {"kind": queried, "component": "one", "ref": "head", "path": scope}
        payload = json.loads(
            call_named_tool(retained, COVERAGE_TOOL_NAME, query)["content"][0]["text"]
        )
        assert payload["state"] == "complete" and payload["matches"] == 1
        assert not payload["absence_authoritative"]
        query["path"] = "unrelated-plugin"
        unrelated = json.loads(
            call_named_tool(retained, COVERAGE_TOOL_NAME, query)["content"][0]["text"]
        )
        assert unrelated["state"] == "unknown" and unrelated["matches"] == 0
    store = EvidenceStore(
        EvidenceStoreLimits(max_bytes=2000),
        base=EvidenceSnapshot(RefRole.BASE, "b" * 40, ()),
        head=EvidenceSnapshot(RefRole.HEAD, "a" * 40, (), coverage=(coverage,)),
    )
    assert store.add_coverage(coverage)
    monkeypatch.setenv("OCR_LLM_TOKEN", "typed evidence")
    monkeypatch.setattr(admission, "encoded_size", lambda _value: 0)
    admit_typed_facts(store, records)
    assert not store.records
    path = tmp_path / "store"
    store.write(path)
    monkeypatch.delenv("OCR_LLM_TOKEN")
    loaded = EvidenceStore.read(path)
    for queried in (domain, kind):
        result = call_named_tool(
            loaded,
            COVERAGE_TOOL_NAME,
            {"kind": queried, "component": "one", "ref": "head", "path": scope},
        )
        payload = json.loads(result["content"][0]["text"])
        assert payload["state"] == "unknown" and not payload["absence_authoritative"]


def test_real_git_collection_preserves_atomic_snapshots_and_unknown_mcp_coverage(
    tmp_path, monkeypatch
):
    """Cross real Git acquisition, optional admission, persistence and scoped MCP completeness."""
    git(tmp_path, "init", "-q")
    (tmp_path / "package.json").write_text('{"dependencies":{"package-a":"1.0.0"}}')
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    (tmp_path / "package.json").write_text('{"dependencies":{"package-a":"2.0.0"}}')
    git(tmp_path, "commit", "-qam", "head")
    real_collect = collect.collect_ref_facts
    real_budget = collect.structural_budget

    def large_facts(*args, **kwargs):
        """Expand a controlled producer payload while preserving its real Git identity."""
        records, diagnostics = real_collect(*args, **kwargs)
        for record in records:
            if record.kind == "dependency.declared" and kwargs.get("coverage_sink") is not None:
                kwargs["coverage_sink"].append(
                    CoverageRecord(
                        component=record.component,
                        domain=record.kind,
                        scope=record.source_path,
                        state=CoverageState.COMPLETE,
                        reasons=("bounded-source-complete",),
                        ref=record.ref,
                        commit_sha=record.commit_sha,
                    )
                )
        return [
            replace(record, value={"identity": f"id-{i}", "fact": "界" * 10_000})
            for record in records
            for i in range(20)
        ], diagnostics

    monkeypatch.setattr(collect, "collect_ref_facts", large_facts)
    monkeypatch.setattr(
        collect,
        "structural_budget",
        lambda *args, **kwargs: replace(real_budget(*args, **kwargs), max_bytes=300_000),
    )
    store = collect.collect_repository_evidence(tmp_path, base_ref="HEAD~1", head_ref="HEAD")
    assert len(store.base.records) == len(store.head.records) == 1
    assert {
        record.id
        for snapshot in (store.base, store.head, store.policy)
        for record in snapshot.records
    } <= {record.id for record in store.records}
    assert len([delta for delta in store.deltas if delta.kind == "repository.file"]) == 1
    assert not any(delta.kind == "dependency.declared" for delta in store.deltas)
    path = tmp_path / "private-store"
    store.write(path)
    loaded = EvidenceStore.read(path)
    coverage = next(
        item
        for item in loaded.coverage
        if item.domain == "dependency.declared" and item.ref is RefRole.HEAD
    )
    assert coverage.state.value == "partial"
    response = call_named_tool(
        loaded,
        COVERAGE_TOOL_NAME,
        {
            "kind": "dependency.declared",
            "ref": "head",
            "component": coverage.component,
            "path": "package.json",
        },
    )
    assert not response.get("isError"), response
    result = json.loads(response["content"][0]["text"])
    assert result["state"] == "unknown"
    assert not result["absence_authoritative"]
