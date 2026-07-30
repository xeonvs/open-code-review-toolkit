"""Bounded, atomic persistence for schema-versioned repository evidence."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ocr_toolkit.common.redaction import (
    SENSITIVE_NAMED_KEY_PATTERN,
    redact_env_secret_values,
    redact_sensitive,
)
from ocr_toolkit.evidence.model import (
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    EvidenceValue,
    RefRole,
    Sensitivity,
)

SCHEMA_VERSION = 1
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

        if not 1 <= self.max_records <= 100_000:
            raise EvidenceStoreError("max_records must be between 1 and 100000")
        if not 1 <= self.max_records_per_kind <= self.max_records:
            raise EvidenceStoreError(
                "max_records_per_kind must be positive and no greater than max_records"
            )
        if not 1024 <= self.max_bytes <= 20_000_000:
            raise EvidenceStoreError("max_bytes must be between 1024 and 20000000")
        if not 1 <= self.max_value_chars <= 1_000_000:
            raise EvidenceStoreError("max_value_chars must be between 1 and 1000000")


def _redact_value(value: EvidenceValue) -> EvidenceValue:
    """Recursively redact string leaves before evidence reaches persistent storage."""

    if isinstance(value, str):
        return redact_env_secret_values(redact_sensitive(value))
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if re.fullmatch(SENSITIVE_NAMED_KEY_PATTERN, key, flags=re.IGNORECASE)
                else _redact_value(item)
            )
            for key, item in value.items()
        }
    return value


@dataclass(slots=True)
class EvidenceStore:
    """Own bounded snapshots, typed deltas, and explicit coverage diagnostics."""

    limits: EvidenceStoreLimits = field(default_factory=EvidenceStoreLimits)
    base: EvidenceSnapshot | None = None
    head: EvidenceSnapshot | None = None
    deltas: tuple[EvidenceDelta, ...] = ()
    diagnostics: list[str] = field(default_factory=list)
    _records: dict[str, EvidenceRecord] = field(default_factory=dict, init=False, repr=False)
    _kind_counts: Counter[str] = field(default_factory=Counter, init=False, repr=False)

    def add(self, record: EvidenceRecord) -> bool:
        """Redact and add one record, returning false when a deterministic bound omits it."""

        if record.kind not in KNOWN_KINDS:
            raise EvidenceStoreError(f"unregistered evidence kind: {record.kind}")
        redacted_value = _redact_value(record.value)
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
                record.sensitivity if redacted_value == record.value else Sensitivity.REDACTED
            ),
            staleness=record.staleness,
        )
        if len(json.dumps(redacted.value, ensure_ascii=False)) > self.limits.max_value_chars:
            self._diagnose_once(f"omitted oversized {redacted.kind} evidence value")
            return False
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

    def add_diagnostic(self, message: str) -> None:
        """Record one bounded public coverage notice without repeated noise."""

        if not message or len(message) > 1024:
            raise EvidenceStoreError(
                "evidence diagnostic must contain between 1 and 1024 characters"
            )
        self._diagnose_once(redact_env_secret_values(redact_sensitive(message)))

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        """Return all records in deterministic public ordering."""

        return tuple(
            sorted(self._records.values(), key=lambda item: (item.kind, item.source_path, item.id))
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
                    "diagnostics": list(snapshot.diagnostics),
                }
        return {
            "schema_version": SCHEMA_VERSION,
            "records": [record.to_dict() for record in self.records],
            "snapshots": snapshots,
            "deltas": [
                {
                    "kind": delta.kind,
                    "component": delta.component,
                    "identity": delta.identity,
                    "change": delta.change,
                    "before": delta.before,
                    "after": delta.after,
                }
                for delta in self.deltas
            ],
            "diagnostics": sorted(self.diagnostics),
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
        if len(serialized.encode("utf-8")) > self.limits.max_bytes:
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

        raw_bytes = path.read_bytes()
        if len(raw_bytes) > 20_000_000:
            raise EvidenceStoreError("evidence store exceeds the hard read limit")
        try:
            raw = json.loads(raw_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise EvidenceStoreError("evidence store is not valid bounded JSON") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise EvidenceStoreError("unsupported evidence store schema version")
        limits_raw = raw.get("limits")
        if not isinstance(limits_raw, dict):
            raise EvidenceStoreError("evidence store limits must be an object")
        try:
            limits = EvidenceStoreLimits(
                max_records=int(limits_raw["max_records"]),
                max_records_per_kind=int(limits_raw["max_records_per_kind"]),
                max_bytes=int(limits_raw["max_bytes"]),
                max_value_chars=int(limits_raw["max_value_chars"]),
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
        diagnostics = raw.get("diagnostics", [])
        if not isinstance(diagnostics, list) or not all(
            isinstance(item, str) for item in diagnostics
        ):
            raise EvidenceStoreError("evidence store diagnostics must be strings")
        store.diagnostics = list(cast(list[str], diagnostics))
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
            diagnostics = item.get("diagnostics", [])
            if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
                raise EvidenceStoreError(f"invalid {name} snapshot record ids")
            if not isinstance(diagnostics, list) or not all(
                isinstance(value, str) for value in diagnostics
            ):
                raise EvidenceStoreError(f"invalid {name} snapshot diagnostics")
            try:
                records = tuple(self._records[str(record_id)] for record_id in ids)
                snapshot = EvidenceSnapshot(
                    ref=role,
                    commit_sha=str(item["commit_sha"]),
                    records=records,
                    diagnostics=tuple(cast(list[str], diagnostics)),
                )
            except (KeyError, TypeError, ValueError) as exc:
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
                deltas.append(
                    EvidenceDelta(
                        kind=str(item["kind"]),
                        component=str(item["component"]),
                        identity=str(item["identity"]),
                        change=str(item["change"]),
                        before=cast(EvidenceValue, item.get("before")),
                        after=cast(EvidenceValue, item.get("after")),
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise EvidenceStoreError("invalid evidence delta") from exc
        self.deltas = tuple(deltas)
