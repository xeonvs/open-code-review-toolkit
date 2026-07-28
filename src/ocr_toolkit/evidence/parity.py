"""Compare temporary legacy Markdown facts with typed evidence coverage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ocr_toolkit.evidence.model import EvidenceRecord
from ocr_toolkit.evidence.store import EvidenceStore

LEGACY_DEPENDENCY_RE = re.compile(
    r"(?P<name>[A-Za-z0-9_.@/+:-]+)\s*(?::|===|==|~=|>=|<=)\s*(?P<version>[^\s,;`]+)"
)
LEGACY_IMAGE_RE = re.compile(r"(?i)(?:image|container(?: image)?)\s*:\s*`?([^`\s]+)")


@dataclass(frozen=True, slots=True)
class ParityReport:
    """Describe comparable legacy facts and missing typed coverage."""

    comparable: int
    matched: int
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Return whether every comparable legacy fact has typed coverage."""

        return not self.missing

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic machine-readable parity report."""

        return {
            "complete": self.complete,
            "comparable": self.comparable,
            "matched": self.matched,
            "missing": list(self.missing),
        }


def _legacy_context(store: EvidenceStore) -> str:
    """Return the one temporary legacy projection or an empty string."""

    values = [
        record.value
        for record in store.records
        if record.kind == "repository.context" and isinstance(record.value, str)
    ]
    return values[0] if values else ""


def _typed_tokens(record: EvidenceRecord) -> set[str]:
    """Normalize typed dependency/image values into comparable tokens."""

    if not isinstance(record.value, dict):
        return set()
    fact = record.value.get("fact")
    if not isinstance(fact, dict):
        return set()
    if record.kind in {"dependency.declared", "dependency.locked"}:
        name = fact.get("name")
        version = fact.get("version") or fact.get("constraint")
        if isinstance(name, str) and isinstance(version, str):
            return {f"dependency:{name.casefold()}:{version.casefold()}"}
    if record.kind in {"container.image", "ci.image"}:
        image = fact.get("image")
        if isinstance(image, str):
            return {f"image:{image.casefold()}"}
    return set()


def compare_legacy_projection(store: EvidenceStore) -> ParityReport:
    """Compare safe structured legacy facts with independently typed records."""

    legacy = _legacy_context(store)
    expected: set[str] = set()
    section = ""
    for line in legacy.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().casefold()
            continue
        if section not in {
            "python context",
            "go context",
            "php/composer context",
            "javascript context",
            "ansible requirements",
        }:
            continue
        stripped = line.lstrip("- ")
        image = LEGACY_IMAGE_RE.search(stripped)
        if image:
            expected.add(f"image:{image.group(1).casefold()}")
            continue
        for match in LEGACY_DEPENDENCY_RE.finditer(stripped):
            name = match.group("name")
            version = match.group("version").strip("`")
            nested = re.fullmatch(
                r"(?P<name>[A-Za-z0-9_.@/+:-]+(?:\[[A-Za-z0-9_,.-]+\])?)"
                r"(?:===|==|~=|>=|<=)(?P<version>.+)",
                version,
            )
            if nested:
                name = nested.group("name")
                version = nested.group("version")
            expected.add(f"dependency:{name.casefold()}:{version.casefold()}")
    actual = set().union(
        *(
            _typed_tokens(record)
            for record in store.records
            if not record.provenance.startswith("legacy.")
        )
    )
    missing = tuple(sorted(expected - actual))
    if not expected:
        return ParityReport(0, 0, ("coverage:no-comparable-legacy-facts",))
    return ParityReport(len(expected), len(expected) - len(missing), missing)


def render_parity_json(store: EvidenceStore) -> str:
    """Render the semantic parity report as deterministic JSON."""

    return (
        json.dumps(
            compare_legacy_projection(store).to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    )
