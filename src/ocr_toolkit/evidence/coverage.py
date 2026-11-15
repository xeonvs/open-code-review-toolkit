"""Compose scoped evidence completeness without turning absence into proof."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ocr_toolkit.evidence.model import (
    CoverageRecord,
    CoverageState,
    EvidenceDelta,
    EvidenceRecord,
    RefRole,
)


def coverage_domains(kind: str) -> frozenset[str]:
    """Map record kinds to their schema-owned completeness domains."""
    return {
        "framework.detected": frozenset(
            {"framework.declaration", "framework.resolution", "framework.configuration"}
        ),
        "template.file": frozenset({"template.inventory"}),
    }.get(kind, frozenset({kind}))


def record_in_coverage(record: EvidenceRecord, kind: str, scope: str | None) -> bool:
    """Join manifest paths or plugin semantic scopes to their owning record schema."""
    domains = coverage_domains(record.kind)
    if kind != record.kind and kind not in domains:
        return False
    if scope is None:
        return True
    if domains == frozenset({record.kind}):
        return record.source_path == scope
    fact = record.value.get("fact") if isinstance(record.value, Mapping) else None
    if not isinstance(fact, Mapping):
        return False
    plugin = fact.get("plugin")
    if not isinstance(plugin, str):
        return False
    selected = domains if kind == record.kind else frozenset({kind})
    scopes = {
        plugin
        if domain in {"framework.declaration", "template.inventory"}
        else f"{plugin}:{fact.get('framework')}"
        for domain in selected
    }
    return scope in scopes


@dataclass(frozen=True, slots=True)
class CoverageObservation:
    """Describe one bounded source's contribution to scoped completeness."""

    state: CoverageState
    reason: str
    positive: bool = False


def compose_coverage(
    *,
    component: str,
    domain: str,
    scope: str,
    observations: tuple[CoverageObservation, ...],
    ref: RefRole,
    commit_sha: str,
) -> CoverageRecord:
    """Combine source observations monotonically into one scoped record."""

    if not observations:
        state = CoverageState.UNAVAILABLE
        reasons = ("no-supported-source",)
    else:
        reasons = tuple(observation.reason for observation in observations)
        if any(
            observation.state is CoverageState.RUNTIME_DEPENDENT for observation in observations
        ):
            state = CoverageState.RUNTIME_DEPENDENT
        elif all(observation.state is CoverageState.COMPLETE for observation in observations):
            state = CoverageState.COMPLETE
        elif any(observation.positive for observation in observations):
            state = CoverageState.PARTIAL
        else:
            state = CoverageState.UNAVAILABLE
    return CoverageRecord(
        component=component,
        domain=domain,
        scope=scope,
        state=state,
        reasons=reasons,
        ref=ref,
        commit_sha=commit_sha,
    )


def coverage_deltas(records: tuple[CoverageRecord, ...]) -> tuple[EvidenceDelta, ...]:
    """Build deltas keyed by semantic applicability rather than mutable state."""

    base = {record.semantic_identity: record for record in records if record.ref is RefRole.BASE}
    head = {record.semantic_identity: record for record in records if record.ref is RefRole.HEAD}
    deltas = []
    for identity in sorted(set(base) | set(head)):
        before = base.get(identity)
        after = head.get(identity)
        before_value = (
            {"state": before.state.value, "reasons": list(before.reasons)} if before else None
        )
        after_value = (
            {"state": after.state.value, "reasons": list(after.reasons)} if after else None
        )
        if before_value == after_value:
            continue
        change = "removed" if after is None else "added" if before is None else "changed"
        selected = after or before
        if selected is None:  # pragma: no cover - identity came from the union above
            continue
        deltas.append(
            EvidenceDelta(
                kind="repository.evidence_coverage",
                component=selected.component,
                identity=identity,
                change=change,
                before=before_value,
                after=after_value,
            )
        )
    return tuple(deltas)
