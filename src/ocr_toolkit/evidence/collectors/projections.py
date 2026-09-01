"""Project collected facts into plugin records, coverage, and semantic deltas."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping

from ocr_toolkit.evidence.coverage import CoverageObservation, compose_coverage
from ocr_toolkit.evidence.frameworks import PluginCoverage, PluginFact
from ocr_toolkit.evidence.model import (
    Confidence,
    CoverageRecord,
    EvidenceDelta,
    EvidenceRecord,
    RefRole,
    TrustClass,
)


def plugin_records(
    facts: tuple[PluginFact, ...],
    *,
    ref: RefRole,
    commit_sha: str,
    trust: TrustClass,
) -> list[EvidenceRecord]:
    """Attach immutable ref provenance to validated static plugin facts."""

    return [
        EvidenceRecord(
            kind=fact.kind,
            value={"identity": fact.identity, "fact": fact.value},
            source_path=fact.source_path,
            ref=ref,
            commit_sha=commit_sha,
            component=fact.component,
            provenance=f"framework plugin:{fact.value['plugin']}",
            confidence=Confidence.EXACT,
            trust=trust,
        )
        for fact in facts
    ]


def plugin_coverage(
    observations: tuple[PluginCoverage, ...], *, ref: RefRole, commit_sha: str
) -> list[CoverageRecord]:
    """Compose plugin coverage by semantic component/domain/scope identity."""

    grouped: dict[tuple[str, str, str], list[CoverageObservation]] = {}
    for item in observations:
        grouped.setdefault((item.component, item.domain, item.scope), []).append(item.observation)
    return [
        compose_coverage(
            component=component,
            domain=domain,
            scope=scope,
            observations=tuple(values),
            ref=ref,
            commit_sha=commit_sha,
        )
        for (component, domain, scope), values in sorted(grouped.items())
    ]


def fact_deltas(
    records: Iterable[EvidenceRecord], *, incomplete_kinds: Collection[str] = ()
) -> tuple[EvidenceDelta, ...]:
    """Build deltas only where base/head admission leaves the identity comparable."""

    base: dict[tuple[str, str, str], list[EvidenceRecord]] = {}
    head: dict[tuple[str, str, str], list[EvidenceRecord]] = {}
    for record in records:
        if record.kind in {"repository.accepted_decision", "repository.guidance"}:
            continue
        if not isinstance(record.value, Mapping) or not isinstance(
            record.value.get("identity"), str
        ):
            continue
        key = (record.kind, record.component, record.value["identity"])
        if record.ref == RefRole.BASE:
            base.setdefault(key, []).append(record)
        elif record.ref == RefRole.HEAD:
            head.setdefault(key, []).append(record)

    def projected_values(
        values: list[EvidenceRecord] | None,
        peer: list[EvidenceRecord] | None,
    ) -> object:
        """Retain legacy scalar facts unless source ambiguity needs provenance."""

        if values is None:
            return None
        if len(values) == 1 and (
            not peer or (len(peer) == 1 and values[0].source_path == peer[0].source_path)
        ):
            value = values[0].value
            return value.get("fact") if isinstance(value, Mapping) else None
        ordered = sorted(values, key=lambda record: (record.source_path, record.id))
        projected = [
            {
                "source_path": record.source_path,
                "fact": (serialized.get("fact") if isinstance(serialized, Mapping) else None),
            }
            for record in ordered
            for serialized in (record.to_dict()["value"],)
        ]
        return projected

    deltas = []
    for key in sorted(set(base) | set(head)):
        before = base.get(key)
        after = head.get(key)
        if key[0] in incomplete_kinds:
            # Kind-level admission failure cannot identify which semantic key was
            # omitted. Even a remaining same-source pair may have lost a third
            # value for this identity, so no delta for that kind is authoritative.
            continue
        before_value = projected_values(before, after)
        after_value = projected_values(after, before)
        change = "removed" if after is None else "added" if before is None else "changed"
        if before_value == after_value:
            continue
        deltas.append(EvidenceDelta(key[0], key[1], key[2], change, before_value, after_value))
    return tuple(deltas)
