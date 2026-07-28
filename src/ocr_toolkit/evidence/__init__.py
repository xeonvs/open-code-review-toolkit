"""Schema-versioned repository evidence contracts and projections."""

from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    RefRole,
    Sensitivity,
    TrustClass,
)
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    build_file_snapshot,
    file_deltas,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError, EvidenceStoreLimits

__all__ = [
    "Confidence",
    "EvidenceDelta",
    "EvidenceRecord",
    "EvidenceSnapshot",
    "EvidenceStore",
    "EvidenceStoreError",
    "EvidenceStoreLimits",
    "GitRepositoryReader",
    "RefRole",
    "RepositoryEvidenceError",
    "Sensitivity",
    "TrustClass",
    "build_file_snapshot",
    "file_deltas",
]
