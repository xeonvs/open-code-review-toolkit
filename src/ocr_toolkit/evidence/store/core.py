"""Bounded, atomic persistence for schema-versioned repository evidence."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ocr_toolkit.evidence.budgets import OPTIONAL_RECORDS, OPTIONAL_RECORDS_PER_KIND
from ocr_toolkit.evidence.frameworks.schema import validate_plugin_record
from ocr_toolkit.evidence.model import (
    CoverageRecord,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    RefRole,
    Sensitivity,
)
from ocr_toolkit.evidence.policy.contracts import policy_value_within_budget
from ocr_toolkit.evidence.policy.schema import (
    is_legacy_policy_value,
    validate_policy_applicability,
    validate_policy_record,
)
from ocr_toolkit.evidence.review_context import (
    CONTEXT_KIND,
    CONTEXT_SOURCE,
    context_provenance,
    validate_merge_request_context,
)
from ocr_toolkit.evidence.store.atomic import atomic_write
from ocr_toolkit.evidence.store.contracts import (
    KNOWN_KINDS,
    POLICY_KINDS,
    SCHEMA_VERSION,
    TARGET_CONTEXT_KINDS,
    EvidenceStoreError,
    EvidenceStoreLimits,
)
from ocr_toolkit.evidence.store.readback import read_store
from ocr_toolkit.evidence.store.serialization import bounded_json
from ocr_toolkit.evidence.store.target import add_target_records
from ocr_toolkit.evidence.store.values import (
    EvidenceValueRedactionError,
    safe_delta_metadata,
    safe_diagnostic,
    safe_value,
)


@dataclass(slots=True)
class EvidenceStore:
    """Own bounded snapshots, typed deltas, and explicit coverage diagnostics."""

    limits: EvidenceStoreLimits = field(default_factory=EvidenceStoreLimits)
    optional_records: int = field(default=OPTIONAL_RECORDS, kw_only=True)
    reserved_bytes: int = field(default=0, kw_only=True)
    reserved_records: int = field(default=0, kw_only=True)
    base: EvidenceSnapshot | None = None
    head: EvidenceSnapshot | None = None
    policy: EvidenceSnapshot | None = None
    target: EvidenceSnapshot | None = None
    deltas: tuple[EvidenceDelta, ...] = ()
    schema_version: int = field(default=SCHEMA_VERSION, init=False)
    diagnostics: list[str] = field(default_factory=list)
    _records: dict[str, EvidenceRecord] = field(default_factory=dict, init=False, repr=False)
    _coverage: dict[str, CoverageRecord] = field(default_factory=dict, init=False, repr=False)
    _kind_counts: Counter[str] = field(default_factory=Counter, init=False, repr=False)
    _optional_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate runtime headroom independently of persisted store limits."""
        if (
            type(self.optional_records) is not int
            or not 0 <= self.optional_records <= OPTIONAL_RECORDS
            or type(self.reserved_bytes) is not int
            or not 0 <= self.reserved_bytes < self.limits.max_bytes
            or type(self.reserved_records) is not int
            or not 0 <= self.reserved_records < self.limits.max_records
        ):
            raise EvidenceStoreError("invalid evidence invocation/optional reserve")

    def add_optional(self, record: EvidenceRecord) -> bool:
        """Admit typed facts without borrowing the structural snapshot allowance."""

        if record.id in self._records:
            return self.add(record)
        state = self.record_limit_state(record.kind, optional=True)
        if state is not None:
            self._diagnose_once(
                "global evidence record limit reached"
                if state == "global"
                else f"per-kind evidence record limit reached for {record.kind}"
            )
            return False
        before = len(self._records)
        admitted = self.add(record)
        self._optional_count += len(self._records) - before
        return admitted

    def add(self, record: EvidenceRecord) -> bool:
        """Redact and add one current-schema record within deterministic bounds."""

        return self._add(
            record,
            structured_policy=self.schema_version >= 3,
            policy_role=(
                RefRole.POLICY
                if self.schema_version >= 4
                else RefRole.BASE
                if self.schema_version == 3
                else None
            ),
        )

    def _add(
        self,
        record: EvidenceRecord,
        *,
        structured_policy: bool,
        policy_role: RefRole | None = None,
    ) -> bool:
        """Admit a record while preserving explicit legacy read semantics."""

        if record.kind not in KNOWN_KINDS:
            raise EvidenceStoreError(f"unregistered evidence kind: {record.kind}")
        if record.ref is RefRole.TARGET and (
            self.schema_version < 5
            or record.kind not in TARGET_CONTEXT_KINDS
            or record.trust.value != "target_repository"
        ):
            raise EvidenceStoreError("target code evidence has invalid role, kind, or trust")
        try:
            if record.kind == CONTEXT_KIND:
                validate_merge_request_context(record.value)
            redacted_value = safe_value(record.value, self.limits.max_value_chars)
            if record.kind == CONTEXT_KIND and redacted_value != record.to_dict()["value"]:
                raise ValueError("merge-request context changed during redaction")
            if record.kind in {"framework.detected", "template.file"}:
                validate_plugin_record(record.kind, redacted_value)
            if record.kind == CONTEXT_KIND:
                if record.id in self._records:
                    return True
                if any(item.kind == CONTEXT_KIND for item in self._records.values()):
                    raise ValueError("only one merge-request context record is allowed")
                if (
                    record.ref is not RefRole.SHARED
                    or record.trust.value != "invocation"
                    or record.component != "review"
                    or not isinstance(redacted_value, Mapping)
                    or record.provenance != context_provenance(str(redacted_value.get("provider")))
                    or record.source_path != CONTEXT_SOURCE
                    or record.confidence.value != "exact"
                    or record.commit_sha != redacted_value.get("source_sha")
                ):
                    raise ValueError("merge-request context provenance is invalid")
            if record.kind in POLICY_KINDS:
                if structured_policy and not policy_value_within_budget(redacted_value):
                    raise EvidenceStoreError("redacted policy value exceeds its byte budget")
                if structured_policy and (
                    policy_role is None
                    or record.ref is not policy_role
                    or record.trust.value != "target_repository"
                ):
                    raise ValueError("structured policy evidence must come from the target ref")
                expected_provenance = {
                    "repository.accepted_decision": "policy:accepted-decisions",
                    "repository.guidance": "policy:project-guidance",
                }[record.kind]
                if structured_policy and (
                    record.component != "repository"
                    or record.provenance != expected_provenance
                    or record.confidence.value != "exact"
                ):
                    raise ValueError("structured policy evidence provenance is invalid")
                if (
                    structured_policy
                    and record.kind == "repository.guidance"
                    and (
                        not isinstance(redacted_value, Mapping)
                        or redacted_value.get("identity") != record.source_path
                    )
                ):
                    raise ValueError("structured guidance identity must match its source path")
                if (
                    structured_policy
                    and record.kind == "repository.accepted_decision"
                    and (record.source_path != ".opencodereview/accepted-decisions.md")
                ):
                    raise ValueError("structured decision must use the canonical target path")
                if structured_policy:
                    validate_policy_record(record.kind, redacted_value)
                elif not structured_policy and not is_legacy_policy_value(redacted_value):
                    raise ValueError("legacy policy evidence must contain text only")
        except EvidenceValueRedactionError:
            self._diagnose_once(f"omitted ambiguous {record.kind} evidence value")
            return False
        except EvidenceStoreError:
            self._diagnose_once(f"omitted oversized {record.kind} evidence value")
            return False
        except ValueError as exc:
            raise EvidenceStoreError(f"invalid {record.kind} evidence value") from exc
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
        if len(self._records) + len(self._coverage) >= self.limits.max_records:
            self._diagnose_once("global evidence record limit reached")
            return False
        if self._kind_counts[redacted.kind] >= self.limits.max_records_per_kind:
            self._diagnose_once(f"per-kind evidence record limit reached for {redacted.kind}")
            return False
        self._records[redacted.id] = redacted
        self._kind_counts[redacted.kind] += 1
        return True

    def record_limit_state(
        self, kind: str, *, optional: bool = False
    ) -> Literal["global", "kind"] | None:
        """Explain whether a failed admission exhausted a shared or kind budget."""

        if len(self._records) + len(self._coverage) >= self.limits.max_records or (
            optional and self._optional_count >= self.optional_records
        ):
            return "global"
        kind_limit = (
            min(self.limits.max_records_per_kind, OPTIONAL_RECORDS_PER_KIND)
            if optional
            else self.limits.max_records_per_kind
        )
        if self._kind_counts[kind] >= kind_limit:
            return "kind"
        return None

    def add_target_context(self, records: tuple[EvidenceRecord, ...]) -> bool:
        """Admit a bounded optional target batch without reserializing per record."""

        return add_target_records(self, records)

    def _validate_policy_snapshot_bindings(self, schema_version: int = SCHEMA_VERSION) -> None:
        """Bind structured policy to its schema-owned immutable snapshot."""

        policy_records = tuple(
            record for record in self._records.values() if record.kind in POLICY_KINDS
        )
        if not policy_records or schema_version < 3:
            return
        if self.base is None or self.head is None:
            raise EvidenceStoreError("structured policy evidence requires base and head snapshots")
        policy_snapshot = self.policy if schema_version >= 4 else self.base
        policy_role = RefRole.POLICY if schema_version >= 4 else RefRole.BASE
        if policy_snapshot is None:
            raise EvidenceStoreError("structured policy evidence requires its policy snapshot")
        changed_paths = tuple(
            sorted(
                {
                    record.source_path
                    for snapshot in (self.base, self.head)
                    for record in snapshot.records
                    if record.kind == "repository.file"
                }
            )
        )
        for record in policy_records:
            if is_legacy_policy_value(record.value):
                raise EvidenceStoreError(
                    "legacy text policy cannot be serialized as structured evidence"
                )
            if (
                record.ref is not policy_role
                or record.trust.value != "target_repository"
                or record.commit_sha != policy_snapshot.commit_sha
            ):
                raise EvidenceStoreError(
                    "structured policy evidence does not match the policy snapshot"
                )
            try:
                validate_policy_applicability(record.kind, record.value, changed_paths)
            except ValueError as exc:
                raise EvidenceStoreError(f"invalid {record.kind} snapshot applicability") from exc

    def _validate_target_snapshot_bindings(self, schema_version: int = SCHEMA_VERSION) -> None:
        """Keep target code context tied to its own immutable snapshot and role."""

        target_records = tuple(
            record for record in self._records.values() if record.ref is RefRole.TARGET
        )
        if schema_version < 5:
            if self.target is not None or target_records:
                raise EvidenceStoreError("historical evidence cannot contain target context")
            return
        if self.target is None:
            if target_records:
                raise EvidenceStoreError("target records require a target snapshot")
            return
        if self.target.ref is not RefRole.TARGET or self.target.coverage:
            raise EvidenceStoreError("target snapshot has invalid role or coverage")
        snapshot_ids = {record.id for record in self.target.records}
        if snapshot_ids != {record.id for record in target_records}:
            raise EvidenceStoreError("target records do not match the target snapshot")
        if any(
            record.kind not in TARGET_CONTEXT_KINDS
            or record.trust.value != "target_repository"
            or record.commit_sha != self.target.commit_sha
            for record in target_records
        ):
            raise EvidenceStoreError("target evidence has invalid provenance")

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

        self._diagnose_once(safe_diagnostic(message))

    @property
    def safe_deltas(self) -> tuple[EvidenceDelta, ...]:
        """Return redacted, bounded deltas in deterministic public ordering."""

        if len(self.deltas) > self.limits.max_records:
            raise EvidenceStoreError("evidence deltas exceed the configured record budget")
        if any(
            delta.kind not in KNOWN_KINDS | {"repository.evidence_coverage"}
            for delta in self.deltas
        ):
            raise EvidenceStoreError("evidence delta kind is unregistered")
        normalized = (
            EvidenceDelta(
                kind=delta.kind,
                component=safe_delta_metadata(delta.component, name="component", max_chars=256),
                identity=safe_delta_metadata(delta.identity, name="identity", max_chars=4096),
                change=delta.change,
                before=safe_value(delta.before, self.limits.max_value_chars),
                after=safe_value(delta.after, self.limits.max_value_chars),
            )
            for delta in self.deltas
        )
        unique = {delta.id: delta for delta in normalized}
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.kind,
                    item.component,
                    item.identity,
                    item.change,
                    item.id,
                ),
            )
        )

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

        self._validate_policy_snapshot_bindings(self.schema_version)
        self._validate_target_snapshot_bindings(self.schema_version)
        snapshots: dict[str, object] = {}
        snapshot_items = [("base", self.base), ("head", self.head)]
        if self.schema_version >= 4:
            snapshot_items.append(("policy", self.policy))
        if self.schema_version >= 5:
            snapshot_items.append(("target", self.target))
        for name, snapshot in snapshot_items:
            if snapshot is not None:
                record_ids = [record.id for record in snapshot.records]
                coverage_ids = [record.id for record in snapshot.coverage]
                if any(record_id not in self._records for record_id in record_ids):
                    raise EvidenceStoreError(
                        f"{name} snapshot references an unadmitted evidence record"
                    )
                if any(record_id not in self._coverage for record_id in coverage_ids):
                    raise EvidenceStoreError(
                        f"{name} snapshot references an unadmitted coverage record"
                    )
                snapshots[name] = {
                    "ref": snapshot.ref.value,
                    "commit_sha": snapshot.commit_sha,
                    "record_ids": record_ids,
                    "coverage_ids": coverage_ids,
                    "diagnostics": [safe_diagnostic(message) for message in snapshot.diagnostics],
                }
        return {
            "schema_version": self.schema_version,
            "records": [record.to_dict() for record in self.records],
            "coverage": [record.to_dict() for record in self.coverage],
            "snapshots": snapshots,
            "deltas": [
                {
                    "kind": delta.kind,
                    "component": delta.component,
                    "identity": delta.identity,
                    "change": delta.change,
                    "before": delta.to_mcp_dict()["before"],
                    "after": delta.to_mcp_dict()["after"],
                }
                for delta in self.safe_deltas
            ],
            "diagnostics": sorted(safe_diagnostic(item) for item in self.diagnostics),
            "limits": {
                "max_records": self.limits.max_records,
                "max_records_per_kind": self.limits.max_records_per_kind,
                "max_bytes": self.limits.max_bytes,
                "max_value_chars": self.limits.max_value_chars,
            },
        }

    def to_json(self) -> str:
        """Serialize the store canonically while enforcing its byte budget."""

        return bounded_json(
            self.to_dict(), max_bytes=self.limits.max_bytes, reserved_bytes=self.reserved_bytes
        )

    def write(self, path: Path) -> None:
        """Atomically write a private store without exposing a partial file."""

        atomic_write(path, self.to_json)

    @classmethod
    def read(cls, path: Path) -> EvidenceStore:
        """Read and strictly validate an untrusted serialized store."""

        return read_store(path, lambda limits: cls(limits=limits))
