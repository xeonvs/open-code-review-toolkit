"""Public facade for bounded, atomic repository evidence persistence."""

from ocr_toolkit.evidence.store.contracts import (
    EvidenceStoreError,
    EvidenceStoreLimits,
)
from ocr_toolkit.evidence.store.core import EvidenceStore

__all__ = ["EvidenceStore", "EvidenceStoreError", "EvidenceStoreLimits"]
