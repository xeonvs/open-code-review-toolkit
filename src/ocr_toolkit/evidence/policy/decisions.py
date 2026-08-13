"""Parse tolerant accepted-decision Markdown without granting source authority."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone

from ocr_toolkit.evidence.policy.contracts import AcceptedDecision
from ocr_toolkit.evidence.policy.scopes import PolicyScopeError, matches_scope, validate_scope

MAX_DECISIONS = 256
MAX_MATCHED_PATHS = 64
MAX_SCOPES = 64
MAX_TITLE_CHARS = 256
MAX_METADATA_CHARS = 512
_HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")
_METADATA = re.compile(r"^[ \t]*[-*][ \t]+([^:]+):[ \t]*(.*?)\s*$")


@dataclass(frozen=True, slots=True)
class DecisionParseResult:
    """Return independently accepted decisions and bounded deterministic diagnostics."""

    decisions: tuple[AcceptedDecision, ...]
    diagnostics: tuple[str, ...]


def normalize_decision_id(title: str) -> str:
    """Derive a bounded stable ID from a Unicode heading."""

    folded = unicodedata.normalize("NFKC", title).casefold()
    normalized = re.sub(r"[^\w]+", "-", folded, flags=re.UNICODE).strip("-")
    normalized = normalized.replace("_", "-")
    normalized = re.sub(r"-+", "-", normalized)[:128].strip("-")
    if not normalized:
        raise ValueError("decision heading has no usable identifier")
    return normalized


def _parse_date(value: str) -> date:
    """Parse only canonical ISO calendar dates."""

    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date is not canonical ISO format")
    return parsed


def parse_accepted_decisions(
    text: str, *, changed_paths: tuple[str, ...], today: date | None = None
) -> DecisionParseResult:
    """Parse H2 decisions while isolating malformed entries and metadata."""

    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            current = (match.group(1).strip(), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)
    diagnostics: list[str] = []
    if len(sections) > MAX_DECISIONS:
        diagnostics.append(f"accepted decisions truncated at {MAX_DECISIONS} entries")
        sections = sections[:MAX_DECISIONS]
    parsed: list[AcceptedDecision] = []
    current_date = today or datetime.now(timezone.utc).date()
    for index, (title, lines) in enumerate(sections, 1):
        label = f"decision {index}"
        if not title or len(title) > MAX_TITLE_CHARS:
            diagnostics.append(f"{label}: heading is empty or oversized")
            continue
        try:
            decision_id = normalize_decision_id(title)
        except ValueError:
            diagnostics.append(f"{label}: heading has no usable identifier")
            continue
        scopes: list[str] = []
        category: str | None = None
        owner: str | None = None
        review_after: date | None = None
        invalid_scope = False
        rationale_lines: list[str] = []
        seen_singletons: set[str] = set()
        for line in lines:
            metadata = _METADATA.match(line)
            if metadata is None:
                rationale_lines.append(line)
                continue
            raw_name, value = metadata.groups()
            name = " ".join(raw_name.casefold().split())
            if name not in {"scope", "category", "owner", "review after"}:
                rationale_lines.append(line)
                continue
            if not value or len(value) > MAX_METADATA_CHARS:
                diagnostics.append(f"{decision_id}: invalid {name} metadata")
                if name == "scope":
                    invalid_scope = True
                continue
            if name == "scope":
                if len(scopes) >= MAX_SCOPES:
                    invalid_scope = True
                    diagnostics.append(f"{decision_id}: scope limit exceeded")
                    continue
                try:
                    scopes.append(validate_scope(value))
                except PolicyScopeError:
                    invalid_scope = True
                    diagnostics.append(f"{decision_id}: unsafe scope ignored")
                continue
            if name in seen_singletons:
                diagnostics.append(f"{decision_id}: duplicate {name} metadata ignored")
                continue
            seen_singletons.add(name)
            if name == "category":
                category = value
            elif name == "owner":
                owner = value
            else:
                try:
                    review_after = _parse_date(value)
                except ValueError:
                    diagnostics.append(f"{decision_id}: invalid review after metadata")
        matched = tuple(
            path
            for path in changed_paths
            if not invalid_scope
            and (not scopes or any(matches_scope(scope, path) for scope in scopes))
        )[:MAX_MATCHED_PATHS]
        applicability = (
            "invalid" if invalid_scope else "applicable" if matched else "not_applicable"
        )
        # A project-wide decision is applicable even for an empty diff-oriented caller.
        if not invalid_scope and not scopes and not changed_paths:
            applicability = "applicable"
        parsed.append(
            AcceptedDecision(
                decision_id=decision_id,
                title=title,
                rationale="\n".join(rationale_lines).strip(),
                scopes=tuple(scopes),
                category=category,
                owner=owner,
                review_after=review_after,
                stale=review_after is not None and current_date >= review_after,
                applicability=applicability,  # type: ignore[arg-type]
                matched_paths=matched,
            )
        )
    counts: dict[str, int] = {}
    for item in parsed:
        counts[item.decision_id] = counts.get(item.decision_id, 0) + 1
    collisions = {key for key, count in counts.items() if count > 1}
    for collision in sorted(collisions):
        diagnostics.append(f"duplicate normalized decision id ignored: {collision}")
    return DecisionParseResult(
        tuple(item for item in parsed if item.decision_id not in collisions), tuple(diagnostics)
    )
