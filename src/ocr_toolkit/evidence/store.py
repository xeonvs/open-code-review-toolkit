"""Bounded, atomic persistence for schema-versioned repository evidence."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ocr_toolkit.common.redaction import (
    SENSITIVE_NAMED_KEY_PATTERN,
    redact_env_secret_values,
    redact_sensitive,
)
from ocr_toolkit.evidence.model import (
    CoverageRecord,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    EvidenceValue,
    RefRole,
    Sensitivity,
)

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, SCHEMA_VERSION}
MAX_SERIALIZED_BYTES = 20_000_000
KNOWN_KINDS = frozenset(
    {
        "repository.file",
        "repository.guidance",
        "repository.accepted_decision",
        "repository.manifest",
        "repository.change_category",
        "ansible.playbook",
        "ansible.role_metadata",
        "ansible.role_defaults",
        "ansible.role_vars",
        "ansible.inventory",
        "ansible.inventory_group",
        "review.ci_context",
        "dependency.declared",
        "dependency.locked",
        "runtime.declared",
        "runtime.detected",
        "container.image",
        "ci.image",
        "application.version",
        "diagnostic.coverage",
    }
)


class EvidenceStoreError(ValueError):
    """Report an invalid, unsafe, or over-limit evidence store operation."""


@dataclass(frozen=True, slots=True)
class EvidenceStoreLimits:
    """Declare deterministic record, per-kind, and serialized byte budgets."""

    max_records: int = 4096
    max_records_per_kind: int = 512
    max_bytes: int = 2_000_000
    max_value_chars: int = 64_000

    def __post_init__(self) -> None:
        """Reject unusable or unbounded limit configurations."""

        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (
                self.max_records,
                self.max_records_per_kind,
                self.max_bytes,
                self.max_value_chars,
            )
        ):
            raise EvidenceStoreError("evidence store limits must be integers")
        if not 1 <= self.max_records <= 100_000:
            raise EvidenceStoreError("max_records must be between 1 and 100000")
        if not 1 <= self.max_records_per_kind <= self.max_records:
            raise EvidenceStoreError(
                "max_records_per_kind must be positive and no greater than max_records"
            )
        if not 1024 <= self.max_bytes <= MAX_SERIALIZED_BYTES:
            raise EvidenceStoreError(f"max_bytes must be between 1024 and {MAX_SERIALIZED_BYTES}")
        if not 1 <= self.max_value_chars <= 1_000_000:
            raise EvidenceStoreError("max_value_chars must be between 1 and 1000000")


def _redact_value(value: EvidenceValue) -> EvidenceValue:
    """Recursively redact string leaves before evidence reaches persistent storage."""

    if isinstance(value, str):
        return redact_env_secret_values(redact_sensitive(value))
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            key: (
                "[REDACTED]"
                if re.fullmatch(SENSITIVE_NAMED_KEY_PATTERN, key, flags=re.IGNORECASE)
                else _redact_value(item)
            )
            for key, item in value.items()
        }
    return value


def _safe_value(value: EvidenceValue, max_chars: int) -> EvidenceValue:
    """Redact a nested value and enforce the schema's code-point budget."""

    redacted = _redact_value(value)
    if len(json.dumps(redacted, ensure_ascii=False)) > max_chars:
        raise EvidenceStoreError(f"evidence value exceeds {max_chars} characters")
    return redacted


def _safe_diagnostic(message: object) -> str:
    """Return one redacted diagnostic within the public schema limit."""

    if not isinstance(message, str) or not message or len(message) > 1024:
        raise EvidenceStoreError("evidence diagnostic must contain between 1 and 1024 characters")
    return redact_env_secret_values(redact_sensitive(message))


@dataclass(slots=True)
class EvidenceStore:
    """Own bounded snapshots, typed deltas, and explicit coverage diagnostics."""

    limits: EvidenceStoreLimits = field(default_factory=EvidenceStoreLimits)
    base: EvidenceSnapshot | None = None
    head: EvidenceSnapshot | None = None
    deltas: tuple[EvidenceDelta, ...] = ()
    diagnostics: list[str] = field(default_factory=list)
    _records: dict[str, EvidenceRecord] = field(default_factory=dict, init=False, repr=False)
    _coverage: dict[str, CoverageRecord] = field(default_factory=dict, init=False, repr=False)
    _kind_counts: Counter[str] = field(default_factory=Counter, init=False, repr=False)

    def add(self, record: EvidenceRecord) -> bool:
        """Redact and add one record, returning false when a deterministic bound omits it."""

        if record.kind not in KNOWN_KINDS:
            raise EvidenceStoreError(f"unregistered evidence kind: {record.kind}")
        try:
            redacted_value = _safe_value(record.value, self.limits.max_value_chars)
        except EvidenceStoreError:
            self._diagnose_once(f"omitted oversized {record.kind} evidence value")
            return False
        redacted = EvidenceRecord(
            kind=record.kind,
            value=redacted_value,
            source_path=record.source_path,
            ref=record.ref,
            commit_sha=record.commit_sha,
            component=record.component,
            provenance=record.provenance,
            confidence=record.confidence,
            trust=record.trust,
            sensitivity=(
                record.sensitivity
                if redacted_value == record.to_dict()["value"]
                else Sensitivity.REDACTED
            ),
            staleness=record.staleness,
        )
        if redacted.id in self._records:
            return True
        if len(self._records) >= self.limits.max_records:
            self._diagnose_once("global evidence record limit reached")
            return False
        if self._kind_counts[redacted.kind] >= self.limits.max_records_per_kind:
            self._diagnose_once(f"per-kind evidence record limit reached for {redacted.kind}")
            return False
        self._records[redacted.id] = redacted
        self._kind_counts[redacted.kind] += 1
        return True

    def _diagnose_once(self, message: str) -> None:
        """Append one deterministic diagnostic without repeated noise."""

        if message not in self.diagnostics:
            self.diagnostics.append(message)

    def add_coverage(self, record: CoverageRecord) -> bool:
        """Add one scoped coverage record within the shared record budget."""

        if record.id in self._coverage:
            return True
        if len(self._records) + len(self._coverage) >= self.limits.max_records:
            self._diagnose_once("global evidence record limit reached")
            return False
        self._coverage[record.id] = record
        return True

    def add_diagnostic(self, message: str) -> None:
        """Record one bounded public coverage notice without repeated noise."""

        self._diagnose_once(_safe_diagnostic(message))

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        """Return all records in deterministic public ordering."""

        return tuple(
            sorted(self._records.values(), key=lambda item: (item.kind, item.source_path, item.id))
        )

    @property
    def coverage(self) -> tuple[CoverageRecord, ...]:
        """Return scoped completeness records in deterministic ordering."""

        return tuple(
            sorted(
                self._coverage.values(),
                key=lambda item: (item.component, item.domain, item.scope, item.id),
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Return the complete versioned store representation."""

        snapshots: dict[str, object] = {}
        for name, snapshot in (("base", self.base), ("head", self.head)):
            if snapshot is not None:
                snapshots[name] = {
                    "ref": snapshot.ref.value,
                    "commit_sha": snapshot.commit_sha,
                    "record_ids": [record.id for record in snapshot.records],
                    "coverage_ids": [record.id for record in snapshot.coverage],
                    "diagnostics": [_safe_diagnostic(message) for message in snapshot.diagnostics],
                }
        return {
            "schema_version": SCHEMA_VERSION,
            "records": [record.to_dict() for record in self.records],
            "coverage": [record.to_dict() for record in self.coverage],
            "snapshots": snapshots,
            "deltas": [
                {
                    "kind": delta.kind,
                    "component": delta.component,
                    "identity": delta.identity,
                    "change": delta.change,
                    "before": _safe_value(delta.before, self.limits.max_value_chars),
                    "after": _safe_value(delta.after, self.limits.max_value_chars),
                }
                for delta in self.deltas
            ],
            "diagnostics": sorted(_safe_diagnostic(item) for item in self.diagnostics),
            "limits": {
                "max_records": self.limits.max_records,
                "max_records_per_kind": self.limits.max_records_per_kind,
                "max_bytes": self.limits.max_bytes,
                "max_value_chars": self.limits.max_value_chars,
            },
        }

    def to_json(self) -> str:
        """Serialize the store canonically while enforcing its byte budget."""

        serialized = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        if len((serialized + "\n").encode("utf-8")) > self.limits.max_bytes:
            raise EvidenceStoreError("serialized evidence store exceeds its byte budget")
        return serialized + "\n"

    def write(self, path: Path) -> None:
        """Atomically write a private store without exposing a partial file."""

        parent_created = not path.parent.exists()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Do not mutate a caller-owned shared ancestor such as /tmp or the
        # repository root. Newly created artifact directories remain private.
        if parent_created:
            os.chmod(path.parent, 0o700)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                handle.write(self.to_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    @classmethod
    def read(cls, path: Path) -> EvidenceStore:
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
        if not isinstance(raw, dict) or raw.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
            raise EvidenceStoreError("unsupported evidence store schema version")
        schema_version = cast(int, raw["schema_version"])
        limits_raw = raw.get("limits")
        if not isinstance(limits_raw, dict):
            raise EvidenceStoreError("evidence store limits must be an object")
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
        store = cls(limits=limits)
        records_raw = raw.get("records")
        if not isinstance(records_raw, list):
            raise EvidenceStoreError("evidence store records must be a list")
        try:
            for item in records_raw:
                if not store.add(EvidenceRecord.from_dict(item)):
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
        if not isinstance(diagnostics, list) or not all(
            isinstance(item, str) for item in diagnostics
        ):
            raise EvidenceStoreError("evidence store diagnostics must be strings")
        try:
            for diagnostic in cast(list[str], diagnostics):
                store.add_diagnostic(diagnostic)
        except EvidenceStoreError as exc:
            raise EvidenceStoreError("invalid evidence store diagnostic") from exc
        store._read_snapshots(raw.get("snapshots", {}))
        store._read_deltas(raw.get("deltas", []))
        return store

    def _read_snapshots(self, raw: object) -> None:
        """Validate snapshot references against already validated records."""

        if not isinstance(raw, dict):
            raise EvidenceStoreError("evidence snapshots must be an object")
        for name, role in (("base", RefRole.BASE), ("head", RefRole.HEAD)):
            item = raw.get(name)
            if item is None:
                continue
            if not isinstance(item, dict) or item.get("ref") != role.value:
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
                records = tuple(self._records[record_id] for record_id in ids)
                coverage = tuple(self._coverage[record_id] for record_id in coverage_ids)
                snapshot = EvidenceSnapshot(
                    ref=role,
                    commit_sha=commit_sha,
                    records=records,
                    diagnostics=tuple(
                        _safe_diagnostic(message) for message in cast(list[str], diagnostics)
                    ),
                    coverage=coverage,
                )
            except (EvidenceStoreError, KeyError, TypeError, ValueError) as exc:
                raise EvidenceStoreError(f"invalid {name} evidence snapshot") from exc
            setattr(self, name, snapshot)

    def _read_deltas(self, raw: object) -> None:
        """Validate typed deltas stored in an untrusted envelope."""

        if not isinstance(raw, list):
            raise EvidenceStoreError("evidence deltas must be a list")
        deltas = []
        try:
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("evidence delta must be an object")
                metadata: dict[str, str] = {}
                for name in ("kind", "component", "identity", "change"):
                    candidate = item.get(name)
                    if not isinstance(candidate, str):
                        raise ValueError(f"evidence delta field {name!r} must be a string")
                    metadata[name] = candidate
                deltas.append(
                    EvidenceDelta(
                        kind=metadata["kind"],
                        component=metadata["component"],
                        identity=metadata["identity"],
                        change=metadata["change"],
                        before=_safe_value(
                            cast(EvidenceValue, item.get("before")),
                            self.limits.max_value_chars,
                        ),
                        after=_safe_value(
                            cast(EvidenceValue, item.get("after")),
                            self.limits.max_value_chars,
                        ),
                    )
                )
        except (EvidenceStoreError, TypeError, ValueError) as exc:
            raise EvidenceStoreError("invalid evidence delta") from exc
        self.deltas = tuple(deltas)
