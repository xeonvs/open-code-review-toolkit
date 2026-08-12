"""Immutable repository evidence value objects and canonical identities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TypeAlias, cast

EvidenceValue: TypeAlias = (
    "bool | int | float | str | list[EvidenceValue] | tuple[EvidenceValue, ...] "
    "| Mapping[str, EvidenceValue] | None"
)


def _freeze_value(value: EvidenceValue) -> EvidenceValue:
    """Return a recursively immutable JSON-compatible value."""

    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    return value


def _thaw_value(value: EvidenceValue) -> EvidenceValue:
    """Return a fresh ordinary JSON value for serialization callers."""

    if isinstance(value, (list, tuple)):
        return [_thaw_value(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    return value


class RefRole(str, Enum):
    """Identify which immutable repository state supplied an evidence fact."""

    BASE = "base"
    HEAD = "head"
    SHARED = "shared"


class Confidence(str, Enum):
    """Describe how directly a collector established an evidence fact."""

    EXACT = "exact"
    DERIVED = "derived"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class TrustClass(str, Enum):
    """Record the authority boundary of repository-derived evidence."""

    TOOLKIT = "toolkit"
    TARGET_REPOSITORY = "target_repository"
    SOURCE_REPOSITORY = "source_repository"
    INVOCATION = "invocation"
    DERIVED = "derived"


class Sensitivity(str, Enum):
    """State whether a stored fact is public or explicitly redacted."""

    PUBLIC = "public"
    REDACTED = "redacted"


class CoverageState(str, Enum):
    """Describe whether missing evidence can support a negative conclusion."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    RUNTIME_DEPENDENT = "runtime-dependent"
    UNAVAILABLE = "unavailable"


def _canonical_json(value: object) -> str:
    """Serialize a validated evidence value for stable hashing and ordering."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_value(value: EvidenceValue, *, depth: int = 0) -> None:
    """Reject non-JSON, excessively nested, or non-finite evidence values."""

    if depth > 16:
        raise ValueError("evidence value exceeds the maximum nesting depth")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("evidence value contains a non-finite number")
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_value(item, depth=depth + 1)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("evidence object keys must be strings")
            _validate_value(item, depth=depth + 1)
        return
    raise ValueError(f"unsupported evidence value type: {type(value).__name__}")


def _normalize_source_path(value: str) -> str:
    """Return a repository-relative POSIX path without traversal components."""

    path = PurePosixPath(value)
    raw_parts = value.split("/")
    if path.is_absolute() or not value or any(part in {"", ".", ".."} for part in raw_parts):
        raise ValueError("source_path must be a normalized repository-relative path")
    if any(character == "\x7f" or ord(character) < 32 for character in value):
        raise ValueError("source_path must not contain control characters")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Represent one bounded fact with origin, trust, and stable identity."""

    kind: str
    value: EvidenceValue
    source_path: str
    ref: RefRole
    commit_sha: str
    component: str = "repository"
    provenance: str = "unknown"
    confidence: Confidence = Confidence.EXACT
    trust: TrustClass = TrustClass.DERIVED
    sensitivity: Sensitivity = Sensitivity.PUBLIC
    staleness: str | None = None
    id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate the public record contract and derive its stable identifier."""

        if not self.kind or not all(
            part.replace("_", "").isalnum() for part in self.kind.split(".")
        ):
            raise ValueError("kind must contain dot-separated alphanumeric identifiers")
        _validate_value(self.value)
        object.__setattr__(self, "value", _freeze_value(self.value))
        object.__setattr__(self, "source_path", _normalize_source_path(self.source_path))
        if self.commit_sha and (
            len(self.commit_sha) != 40 or not all(c in "0123456789abcdef" for c in self.commit_sha)
        ):
            raise ValueError("commit_sha must be an empty value or a lowercase 40-character SHA-1")
        if not self.component or len(self.component) > 256:
            raise ValueError("component must contain between 1 and 256 characters")
        if not self.provenance or len(self.provenance) > 256:
            raise ValueError("provenance must contain between 1 and 256 characters")
        identity = {
            "kind": self.kind,
            "value": _thaw_value(self.value),
            "source_path": self.source_path,
            "ref": self.ref.value,
            "commit_sha": self.commit_sha,
            "component": self.component,
            "provenance": self.provenance,
            "confidence": self.confidence.value,
            "trust": self.trust.value,
            "sensitivity": self.sensitivity.value,
            "staleness": self.staleness,
        }
        digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
        object.__setattr__(self, "id", f"ev1_{digest}")

    def to_dict(self) -> dict[str, EvidenceValue]:
        """Return the schema-versioned JSON representation of this record."""

        return {
            "id": self.id,
            "kind": self.kind,
            "value": _thaw_value(self.value),
            "source_path": self.source_path,
            "ref": self.ref.value,
            "commit_sha": self.commit_sha,
            "component": self.component,
            "provenance": self.provenance,
            "confidence": self.confidence.value,
            "trust": self.trust.value,
            "sensitivity": self.sensitivity.value,
            "staleness": self.staleness,
        }

    @classmethod
    def from_dict(cls, raw: object) -> EvidenceRecord:
        """Validate and construct a record from an untrusted JSON object."""

        if not isinstance(raw, dict):
            raise ValueError("evidence record must be an object")
        required = {"kind", "value", "source_path", "ref", "commit_sha"}
        allowed = required | {
            "id",
            "component",
            "provenance",
            "confidence",
            "trust",
            "sensitivity",
            "staleness",
        }
        if not required <= raw.keys():
            raise ValueError("evidence record is missing required fields")
        if not raw.keys() <= allowed:
            raise ValueError("evidence record contains unknown fields")
        defaults = {
            "component": "repository",
            "provenance": "unknown",
            "confidence": Confidence.EXACT.value,
            "trust": TrustClass.DERIVED.value,
            "sensitivity": Sensitivity.PUBLIC.value,
        }
        metadata: dict[str, str] = {}
        for name in ("kind", "source_path", "ref", "commit_sha", *defaults):
            candidate = raw.get(name, defaults.get(name))
            if not isinstance(candidate, str):
                raise ValueError(f"evidence record field {name!r} must be a string")
            metadata[name] = candidate
        staleness = raw.get("staleness")
        if staleness is not None and not isinstance(staleness, str):
            raise ValueError("evidence record field 'staleness' must be a string or null")
        value = cast(EvidenceValue, raw["value"])
        record = cls(
            kind=metadata["kind"],
            value=value,
            source_path=metadata["source_path"],
            ref=RefRole(metadata["ref"]),
            commit_sha=metadata["commit_sha"],
            component=metadata["component"],
            provenance=metadata["provenance"],
            confidence=Confidence(metadata["confidence"]),
            trust=TrustClass(metadata["trust"]),
            sensitivity=Sensitivity(metadata["sensitivity"]),
            staleness=staleness,
        )
        raw_id = raw.get("id")
        if raw_id is not None and not isinstance(raw_id, str):
            raise ValueError("evidence record id must be a string")
        if raw_id not in {None, record.id}:
            raise ValueError("evidence record id does not match its canonical content")
        return record


@dataclass(frozen=True, slots=True)
class CoverageRecord:
    """Describe completeness for one evidence domain and semantic scope."""

    component: str
    domain: str
    scope: str
    state: CoverageState
    reasons: tuple[str, ...]
    ref: RefRole
    commit_sha: str
    schema_version: str = "repository.evidence-coverage/v1"
    kind: str = field(init=False, default="repository.evidence_coverage")
    id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate the closed contract and derive a stable content identifier."""

        if self.schema_version != "repository.evidence-coverage/v1":
            raise ValueError("coverage schema version is unsupported")
        if not isinstance(self.state, CoverageState) or not isinstance(self.ref, RefRole):
            raise ValueError("coverage state and ref must use their closed enums")
        for name, value in (
            ("component", self.component),
            ("domain", self.domain),
            ("scope", self.scope),
        ):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 256
                or any(ord(character) < 32 for character in value)
            ):
                raise ValueError(f"coverage {name} must contain between 1 and 256 safe characters")
        if self.ref is RefRole.SHARED:
            raise ValueError("coverage ref must be base or head")
        if len(self.commit_sha) != 40 or not all(
            character in "0123456789abcdef" for character in self.commit_sha
        ):
            raise ValueError("coverage commit_sha must be a lowercase 40-character SHA-1")
        if not isinstance(self.reasons, tuple) or not all(
            isinstance(reason, str) for reason in self.reasons
        ):
            raise ValueError("coverage reasons must be a tuple of strings")
        normalized_reasons = tuple(sorted(set(self.reasons)))
        if not normalized_reasons or any(
            not reason
            or len(reason) > 64
            or not all(
                character.isascii() and (character.isalnum() or character in ".-")
                for character in reason
            )
            or reason != reason.casefold()
            for reason in normalized_reasons
        ):
            raise ValueError("coverage reasons must contain bounded machine labels")
        object.__setattr__(self, "reasons", normalized_reasons)
        identity = {
            "schema_version": self.schema_version,
            "component": self.component,
            "domain": self.domain,
            "scope": self.scope,
            "state": self.state.value,
            "reasons": list(self.reasons),
            "ref": self.ref.value,
            "commit_sha": self.commit_sha,
        }
        digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
        object.__setattr__(self, "id", f"cov1_{digest}")

    @property
    def semantic_identity(self) -> str:
        """Return the applicability identity used for base-to-head deltas."""

        return _canonical_json([self.component, self.domain, self.scope])

    def to_dict(self) -> dict[str, EvidenceValue]:
        """Return the versioned public JSON representation."""

        return {
            "id": self.id,
            "kind": self.kind,
            "schema_version": self.schema_version,
            "component": self.component,
            "domain": self.domain,
            "scope": self.scope,
            "state": self.state.value,
            "reasons": list(self.reasons),
            "ref": self.ref.value,
            "commit_sha": self.commit_sha,
        }

    @classmethod
    def from_dict(cls, raw: object) -> CoverageRecord:
        """Validate and construct coverage from an untrusted JSON object."""

        if not isinstance(raw, dict):
            raise ValueError("coverage record must be an object")
        required = {
            "kind",
            "schema_version",
            "component",
            "domain",
            "scope",
            "state",
            "reasons",
            "ref",
            "commit_sha",
        }
        allowed = required | {"id"}
        if not required <= raw.keys() or not raw.keys() <= allowed:
            raise ValueError("coverage record fields are invalid")
        if raw.get("kind", "repository.evidence_coverage") != "repository.evidence_coverage":
            raise ValueError("coverage kind is unsupported")
        if raw.get("schema_version", "repository.evidence-coverage/v1") != (
            "repository.evidence-coverage/v1"
        ):
            raise ValueError("coverage schema version is unsupported")
        strings: dict[str, str] = {}
        for name in ("component", "domain", "scope", "state", "ref", "commit_sha"):
            value = raw.get(name)
            if not isinstance(value, str):
                raise ValueError(f"coverage field {name!r} must be a string")
            strings[name] = value
        reasons = raw.get("reasons")
        if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
            raise ValueError("coverage reasons must be strings")
        record = cls(
            component=strings["component"],
            domain=strings["domain"],
            scope=strings["scope"],
            state=CoverageState(strings["state"]),
            reasons=tuple(cast(list[str], reasons)),
            ref=RefRole(strings["ref"]),
            commit_sha=strings["commit_sha"],
        )
        raw_id = raw.get("id")
        if raw_id is not None and not isinstance(raw_id, str):
            raise ValueError("coverage id must be a string")
        if raw_id not in {None, record.id}:
            raise ValueError("coverage id does not match its canonical content")
        return record


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    """Collect deterministic evidence for one immutable repository ref."""

    ref: RefRole
    commit_sha: str
    records: tuple[EvidenceRecord, ...]
    diagnostics: tuple[str, ...] = ()
    coverage: tuple[CoverageRecord, ...] = ()

    def __post_init__(self) -> None:
        """Ensure snapshot records match the declared ref and are ordered."""

        if self.ref is RefRole.SHARED:
            raise ValueError("snapshot ref must be base or head")
        if len(self.commit_sha) != 40 or not all(c in "0123456789abcdef" for c in self.commit_sha):
            raise ValueError("snapshot commit_sha must be a lowercase 40-character SHA-1")
        for record in self.records:
            if record.ref is not self.ref or record.commit_sha != self.commit_sha:
                raise ValueError("snapshot record ref and commit must match the snapshot")
        for coverage in self.coverage:
            if coverage.ref is not self.ref or coverage.commit_sha != self.commit_sha:
                raise ValueError("snapshot coverage ref and commit must match the snapshot")
        if not all(isinstance(item, str) for item in self.diagnostics):
            raise ValueError("snapshot diagnostics must be strings")
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        # Record values may contain dicts or lists and therefore are intentionally
        # not hashable. Content-addressed IDs provide safe deduplication.
        unique = {record.id: record for record in self.records}
        ordered = tuple(
            sorted(unique.values(), key=lambda item: (item.kind, item.source_path, item.id))
        )
        object.__setattr__(self, "records", ordered)
        unique_coverage = {record.id: record for record in self.coverage}
        object.__setattr__(
            self,
            "coverage",
            tuple(
                sorted(
                    unique_coverage.values(),
                    key=lambda item: (item.component, item.domain, item.scope, item.id),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class EvidenceDelta:
    """Describe a typed base-to-head change without conflating unknown states."""

    kind: str
    component: str
    identity: str
    change: str
    before: EvidenceValue
    after: EvidenceValue
    id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate the closed delta-state contract and derive its stable identifier."""

        if (
            not isinstance(self.kind, str)
            or not self.kind
            or len(self.kind) > 256
            or not all(part.replace("_", "").isalnum() for part in self.kind.split("."))
        ):
            raise ValueError("delta kind must be a bounded dotted identifier")
        for name, value, limit in (
            ("component", self.component, 256),
            ("identity", self.identity, 4096),
        ):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > limit
                or any(character == "\x7f" or ord(character) < 32 for character in value)
            ):
                raise ValueError(f"delta {name} must contain bounded safe text")
        if not isinstance(self.change, str) or self.change not in {
            "added",
            "removed",
            "changed",
            "unknown",
        }:
            raise ValueError("unsupported evidence delta state")
        _validate_value(self.before)
        _validate_value(self.after)
        object.__setattr__(self, "before", _freeze_value(self.before))
        object.__setattr__(self, "after", _freeze_value(self.after))
        identity = {
            "kind": self.kind,
            "component": self.component,
            "identity": self.identity,
            "change": self.change,
            "before": _thaw_value(self.before),
            "after": _thaw_value(self.after),
        }
        digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
        object.__setattr__(self, "id", f"del1_{digest}")

    def to_mcp_dict(self) -> dict[str, EvidenceValue]:
        """Return the closed first-class delta projection exposed by the evidence MCP."""

        return {
            "id": self.id,
            "kind": "repository.evidence_delta",
            "schema_version": "repository.evidence-delta/v1",
            "delta_kind": self.kind,
            "component": self.component,
            "identity": self.identity,
            "change": self.change,
            "before": _thaw_value(self.before),
            "after": _thaw_value(self.after),
        }
