"""Contract tests for the bounded repository evidence model."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from ocr_toolkit.evidence import (
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    EvidenceStore,
    EvidenceStoreError,
    EvidenceStoreLimits,
    RefRole,
    TrustClass,
)

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


@pytest.mark.parametrize("path", ["", "/etc/passwd", "../secret", "safe/../secret", "./manifest"])
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
    path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
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


def test_store_round_trips_snapshots_and_typed_deltas(tmp_path: Path) -> None:
    """Persist immutable refs and explicit typed changes with the evidence records."""

    base_record = record("requests==2.31.0", ref=RefRole.BASE, sha=BASE_SHA)
    head_record = record("requests==2.32.0")
    store = EvidenceStore(
        base=EvidenceSnapshot(RefRole.BASE, BASE_SHA, (base_record,)),
        head=EvidenceSnapshot(RefRole.HEAD, HEAD_SHA, (head_record,)),
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
    path = tmp_path / "evidence.json"
    store.write(path)

    restored = EvidenceStore.read(path)
    assert restored.base == store.base
    assert restored.head == store.head
    assert restored.deltas == store.deltas


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
