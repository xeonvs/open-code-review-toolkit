"""Collect bounded review-invocation facts outside repository trust boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceRecord,
    RefRole,
    TrustClass,
)

MAX_CI_IDENTIFIER_CHARS = 32
INVOCATION_SOURCE = ".ocr-toolkit/review-invocation"
IDENTIFIER_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True, slots=True)
class InvocationIdentifier:
    """Describe one provider-normalized bounded invocation identifier."""

    provider: str
    field: str
    value: str
    provenance: str


def collect_invocation_evidence(
    identifiers: tuple[InvocationIdentifier, ...], *, head_sha: str
) -> tuple[EvidenceRecord, ...]:
    """Return normalized invocation identifiers and immutable coverage-policy facts."""

    records = []
    for identifier in identifiers:
        value = identifier.value.strip()
        if (
            not value
            or not IDENTIFIER_NAME_RE.fullmatch(identifier.provider)
            or not IDENTIFIER_NAME_RE.fullmatch(identifier.field)
            or not identifier.provenance
            or len(identifier.provenance) > 256
        ):
            continue
        if len(value) > MAX_CI_IDENTIFIER_CHARS or not value.isascii() or not value.isdecimal():
            continue
        records.append(
            EvidenceRecord(
                kind="review.ci_context",
                value={
                    "provider": identifier.provider,
                    "field": identifier.field,
                    "value": value,
                },
                source_path=INVOCATION_SOURCE,
                ref=RefRole.SHARED,
                commit_sha=head_sha,
                component="review",
                provenance=identifier.provenance,
                confidence=Confidence.EXACT,
                trust=TrustClass.INVOCATION,
            )
        )
    records.append(
        EvidenceRecord(
            kind="diagnostic.coverage",
            value={
                "surface": "installed_tool_versions",
                "status": "intentionally_excluded",
                "reason": (
                    "runner-installed versions are mutable invocation state; "
                    "declared repository versions remain available as immutable evidence"
                ),
            },
            source_path=INVOCATION_SOURCE,
            ref=RefRole.SHARED,
            commit_sha=head_sha,
            component="review",
            provenance="evidence.coverage_policy",
            confidence=Confidence.EXACT,
            trust=TrustClass.TOOLKIT,
        )
    )
    return tuple(records)
