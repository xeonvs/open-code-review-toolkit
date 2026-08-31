"""Project provider-neutral same-revision CI outcomes into private context."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ocr_toolkit.context.contracts import CIOutcomePolicy, TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.context.store import PendingContextRecord

CI_OUTCOME_STATUSES = frozenset({"passed", "failed", "skipped", "canceled", "unknown"})
CI_OUTCOME_REQUIREMENTS = frozenset({"required", "advisory"})
CI_OUTCOME_ORIGINS = frozenset({"current_pipeline", "same_revision_pipeline"})
CI_IDENTITY_BUDGETS = TextBudgets(max_chars=256, max_bytes=1_024, max_lines=1)


@dataclass(frozen=True, slots=True)
class CIOutcome:
    """Carry one normalized provider outcome without raw forge identities."""

    check: str
    status: str
    requirement: str
    path_prefixes: tuple[str, ...]
    origin: str
    completed_at: int
    version: str
    digest: str


@dataclass(frozen=True, slots=True)
class CIOutcomeSnapshot:
    """Carry a stable provider snapshot and its closed completeness state."""

    state: str
    records: tuple[CIOutcome, ...]
    omitted: int
    invalid: int


def prepare_ci_outcome_records(
    snapshot: CIOutcomeSnapshot,
    *,
    policy: CIOutcomePolicy,
    now: int,
    forbidden: tuple[str, ...] = (),
) -> tuple[PendingContextRecord, ...]:
    """DLP-check one closed snapshot and build exact immutable store records."""

    if (
        snapshot.state not in {"complete", "partial", "mutated"}
        or not isinstance(snapshot.omitted, int)
        or isinstance(snapshot.omitted, bool)
        or snapshot.omitted < 0
        or not isinstance(snapshot.invalid, int)
        or isinstance(snapshot.invalid, bool)
        or snapshot.invalid < 0
        or (snapshot.state == "complete" and (snapshot.omitted or snapshot.invalid))
        or (snapshot.state == "mutated" and snapshot.records)
    ):
        return ()
    if snapshot.state == "mutated":
        return ()
    authorized = {check.name: check.path_prefixes for check in policy.checks}
    pending: list[PendingContextRecord] = []
    for record in snapshot.records:
        normalized_identity = {
            "check": record.check,
            "status": record.status,
            "requirement": record.requirement,
            "path_prefixes": list(record.path_prefixes),
            "origin": record.origin,
            "completed_at": record.completed_at,
        }
        expected_digest = hashlib.sha256(
            json.dumps(normalized_identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            record.check not in authorized
            or record.path_prefixes != authorized[record.check]
            or record.status not in CI_OUTCOME_STATUSES
            or record.requirement not in CI_OUTCOME_REQUIREMENTS
            or record.origin not in CI_OUTCOME_ORIGINS
            or not isinstance(record.completed_at, int)
            or isinstance(record.completed_at, bool)
            or record.completed_at < 0
            or record.completed_at > now + 300
            or now - record.completed_at > policy.max_age_seconds
            or record.version != str(record.completed_at)
            or len(record.digest) != 64
            or any(character not in "0123456789abcdef" for character in record.digest)
            or record.digest != expected_digest
        ):
            continue
        values = (record.check, *record.path_prefixes)
        checked = [
            check_text(value, budgets=CI_IDENTITY_BUDGETS, forbidden=forbidden) for value in values
        ]
        if any(
            not value.admitted or value.text != original for value, original in zip(checked, values)
        ):
            continue
        model = {
            "check": record.check,
            "revision": "reviewed_head",
            "status": record.status,
            "requirement": record.requirement,
            "scope": {"mode": "declared", "path_prefixes": list(record.path_prefixes)},
            "origin": record.origin,
            "completed_at": record.completed_at,
        }
        canonical = json.dumps(model, sort_keys=True, separators=(",", ":"))
        pending.append(
            PendingContextRecord(
                source="forge:ci_outcomes",
                adapter="gitlab",
                tenant="project",
                canonical_object=hashlib.sha256(
                    f"ci-outcome:{record.check}:{record.digest}".encode()
                ).hexdigest(),
                resource_class="ci_outcome",
                descriptor="ci_outcome",
                projections={
                    "model": {"descriptor": "ci_outcome", "ci_outcome": model},
                    "publish": {"descriptor": "ci_outcome"},
                    "retain": {
                        "state": record.status,
                        "digest": hashlib.sha256(canonical.encode()).hexdigest(),
                        "version": record.version,
                        "expiry": now + 3_600,
                    },
                },
                version=record.version,
                digest=hashlib.sha256(canonical.encode()).hexdigest(),
                mutable=False,
                expiry=now + 3_600,
            )
        )
    return tuple(pending)
