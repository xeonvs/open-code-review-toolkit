"""Shared normalized contracts for typed dependency manifest parsers."""

from __future__ import annotations

from dataclasses import dataclass

from ocr_toolkit.evidence.model import EvidenceValue

MAX_MANIFEST_ITEMS = 512


@dataclass(frozen=True, slots=True)
class ManifestFact:
    """Describe one normalized typed fact before ref provenance is attached."""

    kind: str
    component: str
    identity: str
    value: EvidenceValue


@dataclass(frozen=True, slots=True)
class ManifestParseResult:
    """Return bounded manifest facts together with safe coverage notices."""

    facts: tuple[ManifestFact, ...]
    notices: tuple[str, ...] = ()
    include_paths: tuple[str, ...] = ()
