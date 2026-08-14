"""Decode hostile evidence envelopes into a bounded in-memory store."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar, cast

from ocr_toolkit.evidence.model import (
    CoverageRecord,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    EvidenceValue,
    RefRole,
)
from ocr_toolkit.evidence.store.contracts import (
    KNOWN_KINDS,
    MAX_SERIALIZED_BYTES,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceStoreError,
    EvidenceStoreLimits,
)
from ocr_toolkit.evidence.store.values import safe_delta_metadata, safe_diagnostic, safe_value


class ReadbackStore(Protocol):
    """Declare the narrow admission surface required by hostile readback."""

    limits: EvidenceStoreLimits
    base: EvidenceSnapshot | None
    head: EvidenceSnapshot | None
    deltas: tuple[EvidenceDelta, ...]
    _records: dict[str, EvidenceRecord]
    _coverage: dict[str, CoverageRecord]

    def _add(self, record: EvidenceRecord, *, structured_policy: bool) -> bool: ...

    def add_coverage(self, record: CoverageRecord) -> bool: ...

    def add_diagnostic(self, message: str) -> None: ...

    def _validate_policy_snapshot_bindings(self) -> None: ...


StoreT = TypeVar("StoreT", bound=ReadbackStore)


def read_store(path: Path, factory: Callable[[EvidenceStoreLimits], StoreT]) -> StoreT:
    """Read and strictly validate an untrusted serialized store."""

    hard_read_limit = MAX_SERIALIZED_BYTES
    with path.open("rb") as handle:
        raw_bytes = handle.read(hard_read_limit + 1)
    if len(raw_bytes) > hard_read_limit:
        raise EvidenceStoreError("evidence store exceeds the hard read limit")
    try:
        raw = json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise EvidenceStoreError("evidence store is not valid bounded JSON") from exc
    if not isinstance(raw, dict):
        raise EvidenceStoreError("unsupported evidence store schema version")
    schema_version_raw = raw.get("schema_version")
    if (
        not isinstance(schema_version_raw, int)
        or isinstance(schema_version_raw, bool)
        or schema_version_raw not in SUPPORTED_SCHEMA_VERSIONS
    ):
        raise EvidenceStoreError("unsupported evidence store schema version")
    schema_version = schema_version_raw
    expected_top_level = {
        "schema_version",
        "records",
        "snapshots",
        "deltas",
        "diagnostics",
        "limits",
    }
    if schema_version >= 2:
        expected_top_level.add("coverage")
    if set(raw) != expected_top_level:
        raise EvidenceStoreError("evidence store fields are invalid for its schema version")
    limits_raw = raw.get("limits")
    if not isinstance(limits_raw, dict) or set(limits_raw) != {
        "max_records",
        "max_records_per_kind",
        "max_bytes",
        "max_value_chars",
    }:
        raise EvidenceStoreError("evidence store limits must be an exact object")
    try:
        limits = EvidenceStoreLimits(
            max_records=limits_raw["max_records"],
            max_records_per_kind=limits_raw["max_records_per_kind"],
            max_bytes=limits_raw["max_bytes"],
            max_value_chars=limits_raw["max_value_chars"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceStoreError("evidence store limits are invalid") from exc
    if len(raw_bytes) > limits.max_bytes:
        raise EvidenceStoreError("evidence store exceeds its declared byte budget")
    store = factory(limits)
    records_raw = raw.get("records")
    if not isinstance(records_raw, list):
        raise EvidenceStoreError("evidence store records must be a list")
    try:
        for item in records_raw:
            if not store._add(
                EvidenceRecord.from_dict(item),
                structured_policy=schema_version >= 3,
            ):
                raise EvidenceStoreError("evidence store records exceed declared limits")
    except (TypeError, ValueError) as exc:
        raise EvidenceStoreError(str(exc)) from exc
    coverage_raw = raw.get("coverage", [])
    if not isinstance(coverage_raw, list):
        raise EvidenceStoreError("evidence coverage must be a list")
    if schema_version == 1 and coverage_raw:
        raise EvidenceStoreError("schema v1 evidence cannot contain coverage records")
    try:
        for item in coverage_raw:
            if not store.add_coverage(CoverageRecord.from_dict(item)):
                raise EvidenceStoreError("evidence coverage exceeds declared limits")
    except (TypeError, ValueError) as exc:
        raise EvidenceStoreError(str(exc)) from exc
    if schema_version == 1:
        store.add_diagnostic(
            "legacy evidence store has no completeness metadata; missing facts are unknown"
        )
    diagnostics = raw.get("diagnostics", [])
    if not isinstance(diagnostics, list) or not all(isinstance(item, str) for item in diagnostics):
        raise EvidenceStoreError("evidence store diagnostics must be strings")
    try:
        for diagnostic in cast(list[str], diagnostics):
            store.add_diagnostic(diagnostic)
    except EvidenceStoreError as exc:
        raise EvidenceStoreError("invalid evidence store diagnostic") from exc
    read_snapshots(store, raw.get("snapshots", {}), schema_version=schema_version)
    if schema_version >= 3:
        store._validate_policy_snapshot_bindings()
    read_deltas(store, raw.get("deltas", []))
    return store


def read_snapshots(store: ReadbackStore, raw: object, *, schema_version: int) -> None:
    """Validate exact historical snapshot shapes and accepted references."""

    if not isinstance(raw, dict) or not set(raw) <= {"base", "head"}:
        raise EvidenceStoreError("evidence snapshots must be a closed object")
    for name, role in (("base", RefRole.BASE), ("head", RefRole.HEAD)):
        item = raw.get(name)
        if item is None:
            continue
        expected_snapshot_fields = {"ref", "commit_sha", "record_ids", "diagnostics"}
        if schema_version >= 2:
            expected_snapshot_fields.add("coverage_ids")
        if (
            not isinstance(item, dict)
            or set(item) != expected_snapshot_fields
            or item.get("ref") != role.value
        ):
            raise EvidenceStoreError(f"invalid {name} evidence snapshot")
        ids = item.get("record_ids", [])
        coverage_ids = item.get("coverage_ids", [])
        diagnostics = item.get("diagnostics", [])
        if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
            raise EvidenceStoreError(f"invalid {name} snapshot record ids")
        if not isinstance(coverage_ids, list) or not all(
            isinstance(value, str) for value in coverage_ids
        ):
            raise EvidenceStoreError(f"invalid {name} snapshot coverage ids")
        if not isinstance(diagnostics, list) or not all(
            isinstance(value, str) for value in diagnostics
        ):
            raise EvidenceStoreError(f"invalid {name} snapshot diagnostics")
        try:
            commit_sha = item.get("commit_sha")
            if not isinstance(commit_sha, str):
                raise ValueError("snapshot commit_sha must be a string")
            records = tuple(store._records[record_id] for record_id in ids)
            coverage = tuple(store._coverage[record_id] for record_id in coverage_ids)
            snapshot = EvidenceSnapshot(
                ref=role,
                commit_sha=commit_sha,
                records=records,
                diagnostics=tuple(
                    safe_diagnostic(message) for message in cast(list[str], diagnostics)
                ),
                coverage=coverage,
            )
        except (EvidenceStoreError, KeyError, TypeError, ValueError) as exc:
            raise EvidenceStoreError(f"invalid {name} evidence snapshot") from exc
        setattr(store, name, snapshot)


def read_deltas(store: ReadbackStore, raw: object) -> None:
    """Validate typed deltas stored in an untrusted envelope."""

    if not isinstance(raw, list):
        raise EvidenceStoreError("evidence deltas must be a list")
    if len(raw) > store.limits.max_records:
        raise EvidenceStoreError("evidence deltas exceed declared limits")
    deltas = []
    try:
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("evidence delta must be an object")
            fields = {"kind", "component", "identity", "change", "before", "after"}
            if set(item) != fields:
                raise ValueError("evidence delta fields are invalid")
            metadata: dict[str, str] = {}
            for name in ("kind", "component", "identity", "change"):
                candidate = item.get(name)
                if not isinstance(candidate, str):
                    raise ValueError(f"evidence delta field {name!r} must be a string")
                metadata[name] = candidate
            if metadata["kind"] not in KNOWN_KINDS | {"repository.evidence_coverage"}:
                raise ValueError("evidence delta kind is unregistered")
            deltas.append(
                EvidenceDelta(
                    kind=metadata["kind"],
                    component=safe_delta_metadata(
                        metadata["component"], name="component", max_chars=256
                    ),
                    identity=safe_delta_metadata(
                        metadata["identity"], name="identity", max_chars=4096
                    ),
                    change=metadata["change"],
                    before=safe_value(
                        cast(EvidenceValue, item.get("before")),
                        store.limits.max_value_chars,
                    ),
                    after=safe_value(
                        cast(EvidenceValue, item.get("after")),
                        store.limits.max_value_chars,
                    ),
                )
            )
    except (EvidenceStoreError, TypeError, ValueError) as exc:
        raise EvidenceStoreError("invalid evidence delta") from exc
    store.deltas = tuple(deltas)
