"""Canonical evidence identities and hostile real-file store readback."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.model import (
    CoverageRecord,
    CoverageState,
    EvidenceDelta,
    EvidenceRecord,
    RefRole,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from tests.fuzz.strategies import json_values
from tests.test_evidence_mcp import _store
from tests.test_evidence_model import coverage, record


@given(
    st.dictionaries(
        st.text(alphabet="abcxyz", min_size=1, max_size=8),
        st.text(alphabet="safe é漢😀", max_size=30),
        max_size=4,
    ),
    st.sampled_from(tuple(CoverageState)),
)
def test_valid_evidence_and_coverage_keep_ids_across_mapping_order_and_real_store_roundtrip(
    value, state
):
    first = record(value)
    reordered = record(dict(reversed(tuple(value.items()))))
    assert first.id == reordered.id
    changed_ref = record(value, ref=RefRole.BASE, sha="a" * 40)
    assert first.id != changed_ref.id
    store = EvidenceStore()
    assert store.add(first) and store.add_coverage(coverage(state))
    with TemporaryDirectory(prefix="ocr-evidence-roundtrip-") as directory:
        target = Path(directory) / "evidence.json"
        store.write(target)
        assert EvidenceStore.read(target).to_dict() == store.to_dict()


@given(
    st.sampled_from(("added", "removed", "changed", "unknown")),
    st.integers(0, 1000),
    st.integers(0, 1000),
)
def test_delta_identity_and_closed_projection_do_not_depend_on_mapping_order(change, before, after):
    first = EvidenceDelta(
        "dependency.version",
        "synthetic",
        "package",
        change,
        {"version": before, "scope": "safe"},
        {"version": after},
    )
    reordered = EvidenceDelta(
        "dependency.version",
        "synthetic",
        "package",
        change,
        {"scope": "safe", "version": before},
        {"version": after},
    )
    assert first.id == reordered.id
    assert first.to_mcp_dict() == reordered.to_mcp_dict()
    assert first.to_mcp_dict()["change"] == change


@given(st.booleans(), st.data(), json_values())
def test_record_and_coverage_field_variations_preserve_canonical_identity_or_reject(
    is_coverage, data, value
) -> None:
    original = coverage().to_dict() if is_coverage else record().to_dict()
    field = data.draw(st.sampled_from(tuple(original)))
    original[field] = value
    constructor = CoverageRecord.from_dict if is_coverage else EvidenceRecord.from_dict
    try:
        admitted = constructor(original)
    except ValueError:
        return
    assert constructor(admitted.to_dict()) == admitted
    assert admitted.id == constructor(admitted.to_dict()).id


FIELDS = (
    ("schema_version",),
    ("limits",),
    ("snapshots",),
    ("records",),
    ("coverage",),
    ("deltas",),
    ("diagnostics",),
    *(
        ("limits", field)
        for field in ("max_records", "max_bytes", "max_value_chars", "max_records_per_kind")
    ),
    *(
        ("records", 0, field)
        for field in ("id", "value", "kind", "ref", "trust", "source_path", "commit_sha")
    ),
)


@given(st.sampled_from(FIELDS), json_values())
def test_evidence_readback_rejects_hostile_nested_fields_without_partial_admission(
    path, value
) -> None:
    with TemporaryDirectory(prefix="ocr-evidence-readback-") as directory:
        target = Path(directory) / "evidence.json"
        original = _store().to_dict()
        parent = original
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = value
        target.write_text(json.dumps(original, ensure_ascii=True))
        try:
            admitted = EvidenceStore.read(target)
        except EvidenceStoreError:
            return
        admitted.write(target)
        assert EvidenceStore.read(target).to_dict() == admitted.to_dict()


@given(st.sampled_from(("schema_version", "records", "limits", "coverage")))
def test_duplicate_store_fields_cannot_silently_choose_a_different_authority(field) -> None:
    payload = _store().to_dict()
    token = json.dumps(field) + ":" + json.dumps(payload[field], separators=(",", ":"))
    wire = json.dumps(payload, separators=(",", ":")).replace(token, token + "," + token, 1)
    with TemporaryDirectory(prefix="ocr-evidence-duplicate-") as directory:
        target = Path(directory) / "evidence.json"
        target.write_text(wire)
        with pytest.raises(EvidenceStoreError):
            EvidenceStore.read(target)
