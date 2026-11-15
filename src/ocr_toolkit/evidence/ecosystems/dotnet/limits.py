"""Bound static .NET input and constructed facts before collector retention."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ocr_toolkit.evidence.model import EvidenceValue

MAX_BYTES = 1_000_000
MAX_DEPTH = 32
MAX_ELEMENTS = 4_096
MAX_ATTRIBUTES = 32
MAX_SCALAR = 4_096


def bounded_text(text: str) -> None:
    """Reject oversized inputs before parser allocation; bytes are independent."""
    if len(text) > MAX_BYTES or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError(".NET manifest byte limit exceeded")


@dataclass(slots=True)
class ConstructionBudget:
    """Cap constructed tree or fact bytes relative to input, with small-input headroom."""

    limit: int
    used: int = 0
    exhausted: bool = False

    @classmethod
    def for_text(cls, text: str) -> ConstructionBudget:
        """Allow ordinary normalized-fact overhead without multiplying a source batch unboundedly."""
        # Short declarations expand into closed scope/provenance/version fields
        # and a digest identity. Bound that normal overhead as well as fanout.
        return cls(min(MAX_BYTES, max(1_024, len(text.encode("utf-8")) * 16)))

    def admit(self, kind: str, identity: str, value: EvidenceValue) -> bool:
        """Account the actual UTF-8 representation before retaining another structure."""
        if self.exhausted:
            return False
        size = len(
            json.dumps([kind, identity, value], ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        if size > self.limit - self.used:
            self.exhausted = True
            return False
        self.used += size
        return True
