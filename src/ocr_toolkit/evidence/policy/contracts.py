"""Closed value contracts for target-derived repository policy evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Literal

Applicability = Literal["applicable", "not_applicable", "invalid"]

MAX_DECISION_TITLE_CHARS = 256
MAX_RATIONALE_CHARS = 64_000
MAX_POLICY_VALUE_BYTES = 56_000


def policy_value_within_budget(value: object) -> bool:
    """Keep one policy fact small enough for persistence and MCP retrieval."""

    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return len(serialized.encode("utf-8")) <= MAX_POLICY_VALUE_BYTES


@dataclass(frozen=True, slots=True)
class AcceptedDecision:
    """Represent one parsed target-branch accepted decision."""

    decision_id: str
    title: str
    rationale: str
    scopes: tuple[str, ...]
    category: str | None
    owner: str | None
    review_after: date | None
    stale: bool
    applicability: Applicability
    matched_paths: tuple[str, ...]

    def evidence_value(self) -> dict[str, object]:
        """Return the closed persisted value for this decision."""

        return {
            "identity": self.decision_id,
            "fact": {
                "schema_version": "repository.accepted-decision/v2",
                "decision_id": self.decision_id,
                "title": self.title,
                "rationale": self.rationale,
                "scopes": list(self.scopes),
                "category": self.category,
                "owner": self.owner,
                "review_after": self.review_after.isoformat() if self.review_after else None,
                "stale": self.stale,
                "applicability": self.applicability,
                "matched_paths": list(self.matched_paths),
            },
        }


@dataclass(frozen=True, slots=True)
class GuidanceDocument:
    """Represent one target-derived guidance document and its applicability."""

    path: str
    document_type: str
    scope: str
    text: str
    applicability: Applicability
    matched_paths: tuple[str, ...]
    depth: int
    document_order: int

    def evidence_value(self) -> dict[str, object]:
        """Return the closed persisted value for this guidance document."""

        return {
            "identity": self.path,
            "fact": {
                "schema_version": "repository.guidance/v2",
                "path": self.path,
                "document_type": self.document_type,
                "scope": self.scope,
                "text": self.text,
                "applicability": self.applicability,
                "matched_paths": list(self.matched_paths),
                "precedence": {
                    "depth": self.depth,
                    "path": self.path,
                    "document_order": self.document_order,
                },
            },
        }
