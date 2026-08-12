"""Contract tests for the bounded repository evidence model."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from ocr_toolkit.evidence import (
    CoverageRecord,
    CoverageState,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    EvidenceStore,
    EvidenceStoreError,
    EvidenceStoreLimits,
    RefRole,
    TrustClass,
)
from ocr_toolkit.evidence.coverage import CoverageObservation, compose_coverage

BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def record(
    value: object = "requests==2.32.0",
    *,
    kind: str = "dependency.declared",
    ref: RefRole = RefRole.HEAD,
    sha: str = HEAD_SHA,
) -> EvidenceRecord:
    """Build one deterministic synthetic evidence record."""

    return EvidenceRecord(
        kind=kind,
        value=value,  # type: ignore[arg-type]
        source_path="requirements.txt",
        ref=ref,
        commit_sha=sha,
        component="api",
        provenance="python.requirements",
        trust=TrustClass.SOURCE_REPOSITORY,
    )


def coverage(
    state: CoverageState = CoverageState.COMPLETE,
    *,
    ref: RefRole = RefRole.HEAD,
    sha: str = HEAD_SHA,
) -> CoverageRecord:
    """Build one deterministic synthetic scoped-coverage record."""

    return CoverageRecord(
        component="synthetic",
        domain="catalog.entries",
        scope="catalog/primary",
        state=state,
        reasons=("bounded-static-source",),
        ref=ref,
        commit_sha=sha,
    )


def test_record_id_is_canonical_and_content_addressed() -> None:
    """Keep identities stable across mapping order and sensitive to origin."""

    first = record({"name": "requests", "version": "2.32.0"})
    reordered = record({"version": "2.32.0", "name": "requests"})
    base = record(first.value, ref=RefRole.BASE, sha=BASE_SHA)

    assert first.id == reordered.id
    assert first.id.startswith("ev1_")
    assert first.id != base.id


def test_record_nested_values_are_immutable_and_serialization_is_detached() -> None:
    """Keep content-addressed identity aligned with nested JSON content."""

    source = {"items": ["one", {"nested": "two"}]}
    evidence = record(source)  # type: ignore[arg-type]
    source["items"].append("changed")  # type: ignore[union-attr]
    serialized = evidence.to_dict()
    serialized_value = serialized["value"]
    assert isinstance(serialized_value, dict)
    serialized_value["items"] = ["changed"]

    assert evidence.to_dict()["value"] == {"items": ["one", {"nested": "two"}]}
    with pytest.raises(TypeError):
        evidence.value["items"] = []  # type: ignore[index]


@pytest.mark.parametrize("field,value", [("kind", 7), ("component", {})])
def test_record_rejects_non_string_metadata(field: str, value: object) -> None:
    """Reject type-confused metadata instead of coercing untrusted JSON."""

    payload = record().to_dict()
    payload[field] = value  # type: ignore[assignment]

    with pytest.raises(ValueError, match="must be a string"):
        EvidenceRecord.from_dict(payload)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc/passwd",
        "../secret",
        "safe/../secret",
        "./manifest",
        "tab\tmanifest",
        "line\nmanifest",
    ],
)
def test_record_rejects_unsafe_source_paths(path: str) -> None:
    """Prevent evidence provenance from escaping the repository namespace."""

    with pytest.raises(ValueError, match="source_path"):
        EvidenceRecord(
            kind="repository.file",
            value=True,
            source_path=path,
            ref=RefRole.HEAD,
            commit_sha=HEAD_SHA,
        )


def test_snapshot_deduplicates_orders_and_rejects_mixed_refs() -> None:
    """Make snapshot ordering deterministic and authority boundaries explicit."""

    one = record("z")
    two = record("a", kind="runtime.declared")
    snapshot = EvidenceSnapshot(RefRole.HEAD, HEAD_SHA, (one, two, one))

    assert snapshot.records == tuple(
        sorted((one, two), key=lambda item: (item.kind, item.source_path, item.id))
    )
    with pytest.raises(ValueError, match="match the snapshot"):
        EvidenceSnapshot(RefRole.BASE, BASE_SHA, (one,))


def test_scoped_coverage_is_versioned_and_composes_monotonically() -> None:
    """Allow negative inference only for an explicitly complete semantic scope."""

    complete = compose_coverage(
        component="synthetic",
        domain="catalog.entries",
        scope="catalog/primary",
        observations=(CoverageObservation(CoverageState.COMPLETE, "bounded-static-source", True),),
        ref=RefRole.HEAD,
        commit_sha=HEAD_SHA,
    )
    mixed = compose_coverage(
        component="synthetic",
        domain="catalog.entries",
        scope="catalog/primary",
        observations=(
            CoverageObservation(CoverageState.COMPLETE, "bounded-static-source", True),
            CoverageObservation(CoverageState.UNAVAILABLE, "bounded-read-omission"),
        ),
        ref=RefRole.HEAD,
        commit_sha=HEAD_SHA,
    )

    assert complete.state is CoverageState.COMPLETE
    assert mixed.state is CoverageState.PARTIAL
    assert CoverageRecord.from_dict(mixed.to_dict()) == mixed
    assert mixed.id.startswith("cov1_")


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": "repository.evidence-coverage/v2"},
        {"reasons": ("secret=value",)},
        {"reasons": ("UPPERCASE",)},
        {"state": "complete"},
    ],
)
def test_coverage_rejects_open_or_secret_bearing_metadata(changes: dict[str, object]) -> None:
    """Keep completeness metadata a closed machine-readable contract."""

    values: dict[str, object] = {
        "component": "synthetic",
        "domain": "catalog.entries",
        "scope": "catalog/primary",
        "state": CoverageState.COMPLETE,
        "reasons": ("bounded-static-source",),
        "ref": RefRole.HEAD,
        "commit_sha": HEAD_SHA,
    }
    values.update(changes)

    with pytest.raises(ValueError, match="coverage"):
        CoverageRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["kind", "schema_version"])
def test_coverage_requires_its_versioned_persisted_contract(field: str) -> None:
    """Do not infer the coverage schema from missing untrusted fields."""

    payload = coverage().to_dict()
    payload.pop(field)

    with pytest.raises(ValueError, match="fields are invalid"):
        CoverageRecord.from_dict(payload)


def test_store_round_trips_coverage_and_legacy_v1_fails_closed(tmp_path: Path) -> None:
    """Persist v2 coverage while treating a v1 store's missing metadata as unknown."""

    store = EvidenceStore()
    assert store.add_coverage(coverage())
    path = tmp_path / "coverage.json"
    store.write(path)
    restored = EvidenceStore.read(path)

    assert restored.coverage == (coverage(),)
    assert restored.to_dict()["schema_version"] == 2

    legacy = store.to_dict()
    legacy["schema_version"] = 1
    legacy.pop("coverage")
    snapshots = legacy["snapshots"]
    assert isinstance(snapshots, dict)
    for snapshot in snapshots.values():
        assert isinstance(snapshot, dict)
        snapshot.pop("coverage_ids", None)
    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
    loaded_legacy = EvidenceStore.read(legacy_path)

    assert loaded_legacy.coverage == ()
    assert any("missing facts are unknown" in item for item in loaded_legacy.diagnostics)


def test_store_redacts_before_persistence_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure raw environment credentials cannot enter serialized evidence."""

    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-secret-token-value")
    store = EvidenceStore()
    assert store.add(
        record("url=https://user:pass@example.invalid token=synthetic-secret-token-value")
    )
    path = tmp_path / "private" / "evidence.json"
    store.write(path)

    serialized = path.read_text(encoding="utf-8")
    assert "synthetic-secret-token-value" not in serialized
    assert "user:pass" not in serialized
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    restored = EvidenceStore.read(path)
    assert restored.to_json() == serialized
    assert restored.records[0].sensitivity.value == "redacted"


def test_store_redacts_sensitive_mapping_keys() -> None:
    """Remove credentials whose key declares sensitivity even when the value is novel."""

    store = EvidenceStore()
    assert store.add(record({"api_key": "short-novel-value", "name": "safe"}))

    assert store.records[0].value == {"api_key": "[REDACTED]", "name": "safe"}
    assert store.records[0].sensitivity.value == "redacted"


def test_store_preserves_public_sensitivity_for_safe_nested_arrays() -> None:
    """Do not mistake immutable JSON containers for a redaction change."""

    store = EvidenceStore()
    assert store.add(record({"items": ["one", {"nested": "two"}]}))

    assert store.records[0].sensitivity.value == "public"


def test_store_does_not_change_existing_parent_permissions(tmp_path: Path) -> None:
    """Keep caller-owned shared artifact directories unchanged."""

    parent = tmp_path / "shared-artifacts"
    parent.mkdir(mode=0o755)
    parent.chmod(0o755)

    EvidenceStore().write(parent / "evidence.json")

    assert stat.S_IMODE(parent.stat().st_mode) == 0o755


def test_store_deduplicates_and_reports_deterministic_limits() -> None:
    """Omit over-budget facts explicitly without corrupting accepted records."""

    store = EvidenceStore(
        EvidenceStoreLimits(max_records=2, max_records_per_kind=1, max_bytes=4096)
    )
    first = record("first")
    assert store.add(first)
    assert store.add(first)
    assert not store.add(record("second"))
    assert store.add(record("3.12", kind="runtime.declared"))
    assert not store.add(record("python", kind="repository.change_category"))

    assert len(store.records) == 2
    assert store.diagnostics == [
        "per-kind evidence record limit reached for dependency.declared",
        "global evidence record limit reached",
    ]


def test_store_rejects_unknown_kinds_and_schema_versions(tmp_path: Path) -> None:
    """Fail closed for unregistered kinds and incompatible envelopes."""

    store = EvidenceStore()
    with pytest.raises(EvidenceStoreError, match="unregistered"):
        store.add(record("x", kind="future.unknown"))

    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"schema_version": 3}), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="schema"):
        EvidenceStore.read(path)


@pytest.mark.parametrize("value", ["4096", True, 4.5])
def test_store_rejects_type_confused_persisted_limits(tmp_path: Path, value: object) -> None:
    """Keep untrusted limit fields numeric without permissive coercion."""

    path = tmp_path / "evidence.json"
    payload = EvidenceStore().to_dict()
    limits = payload["limits"]
    assert isinstance(limits, dict)
    limits["max_records"] = value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="limits are invalid"):
        EvidenceStore.read(path)


def test_store_detects_tampered_record_identity(tmp_path: Path) -> None:
    """Reject a serialized record whose stable ID no longer matches content."""

    store = EvidenceStore()
    store.add(record())
    raw = store.to_dict()
    raw["records"][0]["id"] = "ev1_" + "0" * 64  # type: ignore[index]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="id does not match"):
        EvidenceStore.read(path)


def test_record_rejects_non_string_persisted_identity() -> None:
    """Reject type-confused IDs before comparing them with canonical identity."""

    raw = record().to_dict()
    raw["id"] = []

    with pytest.raises(ValueError, match="id must be a string"):
        EvidenceRecord.from_dict(raw)


def test_store_byte_budget_includes_serialized_trailing_newline(tmp_path: Path) -> None:
    """Enforce the exact byte count emitted by ``to_json`` and ``write``."""

    constrained = EvidenceStore(EvidenceStoreLimits(max_bytes=1024))
    size = len(constrained.to_json().encode("utf-8"))
    padding = "x" * (1024 - size - 1)
    constrained.add_diagnostic(padding)
    without_newline = json.dumps(
        constrained.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert len(without_newline.encode("utf-8")) == 1024

    with pytest.raises(EvidenceStoreError, match="byte budget"):
        constrained.write(tmp_path / "evidence.json")


def test_delta_id_and_mcp_projection_are_canonical_and_detached() -> None:
    """Bind the stable delta ID to semantic content without sharing mutable output."""

    first = EvidenceDelta(
        kind="framework.detected",
        component="services/api",
        identity="go-web:echo",
        change="changed",
        before={"version": "old", "paths": ["go.mod"]},
        after={"version": "new"},
    )
    reordered = EvidenceDelta(
        kind="framework.detected",
        component="services/api",
        identity="go-web:echo",
        change="changed",
        before={"paths": ["go.mod"], "version": "old"},
        after={"version": "new"},
    )

    projection = first.to_mcp_dict()
    assert first.id == reordered.id
    assert first.id.startswith("del1_")
    assert projection["schema_version"] == "repository.evidence-delta/v1"
    before = projection["before"]
    assert isinstance(before, dict)
    before["version"] = "mutated"
    assert first.to_mcp_dict()["before"] == {"paths": ["go.mod"], "version": "old"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "invalid kind"),
        ("component", "x" * 257),
        ("identity", "line\nbreak"),
        ("change", 1),
    ],
)
def test_delta_rejects_unsafe_or_unbounded_metadata(field: str, value: object) -> None:
    """Keep delta metadata bounded before it can reach persistence or MCP."""

    arguments = {
        "kind": "framework.detected",
        "component": "services/api",
        "identity": "go-web:echo",
        "change": "added",
        "before": None,
        "after": {},
    }
    arguments[field] = value
    with pytest.raises(ValueError, match="delta"):
        EvidenceDelta(**arguments)  # type: ignore[arg-type]


def test_store_round_trips_snapshots_and_typed_deltas(tmp_path: Path) -> None:
    """Persist immutable refs and explicit typed changes with the evidence records."""

    base_record = record("requests==2.31.0", ref=RefRole.BASE, sha=BASE_SHA)
    head_record = record("requests==2.32.0")
    base_coverage = coverage(ref=RefRole.BASE, sha=BASE_SHA)
    head_coverage = coverage(state=CoverageState.PARTIAL)
    store = EvidenceStore(
        base=EvidenceSnapshot(RefRole.BASE, BASE_SHA, (base_record,), coverage=(base_coverage,)),
        head=EvidenceSnapshot(RefRole.HEAD, HEAD_SHA, (head_record,), coverage=(head_coverage,)),
        deltas=(
            EvidenceDelta(
                kind="dependency.declared",
                component="api",
                identity="requests",
                change="changed",
                before="2.31.0",
                after="2.32.0",
            ),
        ),
    )
    store.add(base_record)
    store.add(head_record)
    store.add_coverage(base_coverage)
    store.add_coverage(head_coverage)
    path = tmp_path / "evidence.json"
    store.write(path)

    restored = EvidenceStore.read(path)
    assert restored.base == store.base
    assert restored.head == store.head
    assert restored.deltas == store.deltas


def test_store_rejects_tampered_snapshot_coverage_reference(tmp_path: Path) -> None:
    """Keep snapshot coverage indexes atomic with accepted coverage records."""

    item = coverage()
    store = EvidenceStore(head=EvidenceSnapshot(RefRole.HEAD, HEAD_SHA, (), coverage=(item,)))
    assert store.add_coverage(item)
    payload = store.to_dict()
    snapshots = payload["snapshots"]
    assert isinstance(snapshots, dict)
    head = snapshots["head"]
    assert isinstance(head, dict)
    head["coverage_ids"] = ["cov1_" + "0" * 64]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="invalid head evidence snapshot"):
        EvidenceStore.read(path)


def test_store_redacts_and_detaches_delta_values_on_round_trip(tmp_path: Path) -> None:
    """Treat persisted delta payloads as untrusted evidence values."""

    source = {"token": "synthetic-sensitive-value", "items": ["one"]}
    store = EvidenceStore(
        deltas=(
            EvidenceDelta(
                kind="dependency.declared",
                component="api",
                identity="requests",
                change="changed",
                before=source,  # type: ignore[arg-type]
                after={"token": "safe"},
            ),
        )
    )
    source["items"].append("changed")  # type: ignore[union-attr]
    path = tmp_path / "evidence.json"
    store.write(path)

    restored = EvidenceStore.read(path)
    serialized = restored.to_dict()
    deltas = serialized["deltas"]
    assert isinstance(deltas, list)
    delta = deltas[0]
    assert isinstance(delta, dict)
    before = delta["before"]
    assert before == {"items": ["one"], "token": "[REDACTED]"}
    assert isinstance(before, dict)
    before["items"] = ["changed"]
    assert restored.to_dict()["deltas"][0]["before"] == {  # type: ignore[index]
        "items": ["one"],
        "token": "[REDACTED]",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", 1),
        ("component", ["api"]),
        ("identity", None),
        ("change", {"state": "changed"}),
    ],
)
def test_store_rejects_non_string_delta_metadata(tmp_path: Path, field: str, value: object) -> None:
    """Reject type-confused persisted delta metadata instead of coercing it."""

    path = tmp_path / "evidence.json"
    payload = EvidenceStore(
        deltas=(
            EvidenceDelta(
                kind="dependency.declared",
                component="api",
                identity="requests",
                change="changed",
                before=None,
                after="2.32.0",
            ),
        )
    ).to_dict()
    deltas = payload["deltas"]
    assert isinstance(deltas, list)
    delta = deltas[0]
    assert isinstance(delta, dict)
    delta[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="invalid evidence delta"):
        EvidenceStore.read(path)


def test_store_rejects_unregistered_in_memory_delta_kind() -> None:
    """Apply the closed delta vocabulary before serialization or MCP projection."""

    store = EvidenceStore(
        deltas=(
            EvidenceDelta(
                kind="synthetic.unregistered",
                component="services/api",
                identity="synthetic",
                change="added",
                before=None,
                after={},
            ),
        )
    )

    with pytest.raises(EvidenceStoreError, match="delta kind is unregistered"):
        _ = store.safe_deltas


def test_store_rejects_unregistered_persisted_delta_kind(tmp_path: Path) -> None:
    """Keep delta queries inside the registered evidence-domain vocabulary."""

    payload = EvidenceStore(
        deltas=(
            EvidenceDelta(
                kind="framework.detected",
                component="services/api",
                identity="go-web:echo",
                change="added",
                before=None,
                after={},
            ),
        )
    ).to_dict()
    deltas = payload["deltas"]
    assert isinstance(deltas, list) and isinstance(deltas[0], dict)
    deltas[0]["kind"] = "synthetic.unregistered"
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="invalid evidence delta"):
        EvidenceStore.read(path)


def test_store_redacts_persisted_delta_metadata_during_load(tmp_path: Path) -> None:
    """Normalize hostile persisted metadata before it enters the in-memory store."""

    payload = EvidenceStore().to_dict()
    payload["deltas"] = [
        {
            "kind": "framework.detected",
            "component": "services/token=first-sensitive-value",
            "identity": "go-web:echo?token=second-sensitive-value",
            "change": "added",
            "before": None,
            "after": {},
        }
    ]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    restored = EvidenceStore.read(path)

    assert restored.deltas[0].component == "services/token=***"
    assert restored.deltas[0].identity == "go-web:echo?token=***"
    assert restored.safe_deltas == restored.deltas


def test_store_rejects_unknown_persisted_delta_fields(tmp_path: Path) -> None:
    """Keep the persisted delta object closed before MCP projection."""

    payload = EvidenceStore(
        deltas=(
            EvidenceDelta(
                kind="framework.detected",
                component="services/api",
                identity="go-web:echo",
                change="added",
                before=None,
                after={},
            ),
        )
    ).to_dict()
    deltas = payload["deltas"]
    assert isinstance(deltas, list) and isinstance(deltas[0], dict)
    deltas[0]["unknown"] = True
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match="invalid evidence delta"):
        EvidenceStore.read(path)


def test_store_rejects_oversized_delta_values_on_write_and_read(tmp_path: Path) -> None:
    """Apply the configured value budget before any delta is emitted or accepted."""

    limits = EvidenceStoreLimits(max_value_chars=8)
    store = EvidenceStore(
        limits=limits,
        deltas=(
            EvidenceDelta(
                kind="dependency.declared",
                component="api",
                identity="requests",
                change="added",
                before=None,
                after="too-large",
            ),
        ),
    )
    with pytest.raises(EvidenceStoreError, match="exceeds 8 characters"):
        store.to_json()

    path = tmp_path / "evidence.json"
    payload = EvidenceStore().to_dict()
    persisted_limits = payload["limits"]
    assert isinstance(persisted_limits, dict)
    persisted_limits["max_value_chars"] = 8
    payload["deltas"] = [
        {
            "kind": "dependency.declared",
            "component": "api",
            "identity": "requests",
            "change": "added",
            "before": None,
            "after": "too-large",
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="invalid evidence delta"):
        EvidenceStore.read(path)


def test_store_rejects_deltas_beyond_the_declared_record_budget(tmp_path: Path) -> None:
    """Bound delta iteration separately from the serialized byte budget."""

    limits = EvidenceStoreLimits(max_records=1, max_records_per_kind=1)
    deltas = tuple(
        EvidenceDelta(
            kind="framework.detected",
            component="services/api",
            identity=f"go-web:framework-{index}",
            change="added",
            before=None,
            after={},
        )
        for index in range(2)
    )
    store = EvidenceStore(limits=limits, deltas=deltas)
    with pytest.raises(EvidenceStoreError, match="record budget"):
        store.to_json()

    payload = EvidenceStore(limits=limits).to_dict()
    payload["deltas"] = [
        {
            "kind": delta.kind,
            "component": delta.component,
            "identity": delta.identity,
            "change": delta.change,
            "before": None,
            "after": {},
        }
        for delta in deltas
    ]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="deltas exceed declared limits"):
        EvidenceStore.read(path)


def test_store_revalidates_diagnostics_on_read(tmp_path: Path) -> None:
    """Redact accepted diagnostics and reject invalid top-level text."""

    path = tmp_path / "evidence.json"
    payload = EvidenceStore().to_dict()
    payload["diagnostics"] = ["token=synthetic-sensitive-value"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    restored = EvidenceStore.read(path)
    assert restored.diagnostics == ["token=***"]

    payload["diagnostics"] = ["x" * 1025]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="invalid evidence store diagnostic"):
        EvidenceStore.read(path)


def test_store_revalidates_snapshot_diagnostics_on_read(tmp_path: Path) -> None:
    """Apply the diagnostic contract to nested persisted snapshot notices."""

    path = tmp_path / "evidence.json"
    payload = EvidenceStore(
        head=EvidenceSnapshot(
            RefRole.HEAD,
            HEAD_SHA,
            (),
            ("token=synthetic-sensitive-value",),
        )
    ).to_dict()
    path.write_text(json.dumps(payload), encoding="utf-8")
    restored = EvidenceStore.read(path)
    assert restored.head is not None
    assert restored.head.diagnostics == ("token=***",)

    snapshots = payload["snapshots"]
    assert isinstance(snapshots, dict)
    head = snapshots["head"]
    assert isinstance(head, dict)
    head["diagnostics"] = [1]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="invalid head snapshot diagnostics"):
        EvidenceStore.read(path)

    head["diagnostics"] = []
    head["record_ids"] = [1]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceStoreError, match="invalid head snapshot record ids"):
        EvidenceStore.read(path)
