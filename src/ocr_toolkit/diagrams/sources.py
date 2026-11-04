"""Optional diagram projection of shared immutable text facts."""

from __future__ import annotations

import re
from pathlib import Path

from ocr_toolkit.diagrams.contracts import ReferenceSourceInfo
from ocr_toolkit.evidence.source_reader import SourceReadSession
from ocr_toolkit.evidence.text_contracts import MAX_SOURCE_BYTES as MAX_SOURCE_BYTES
from ocr_toolkit.evidence.text_contracts import MAX_TOTAL_SOURCE_BYTES as MAX_TOTAL_SOURCE_BYTES
from ocr_toolkit.evidence.text_contracts import SOURCE_SECONDS as SOURCE_SECONDS


class DiagramSourceReader:
    """Share already acquired facts or lazily start a metadata-only session."""

    def __init__(self, root: Path, head: str, *, session: SourceReadSession | None = None) -> None:
        if re.fullmatch(r"[0-9a-f]{40}", head) is None:
            raise ValueError("diagram source head must be immutable")
        if session is not None and (session.head != head or session.root != root):
            raise ValueError("diagram source session identity differs")
        self.root, self.head, self.session = root, head, session

    def __call__(self, path: str) -> ReferenceSourceInfo:
        if self.session is None:
            self.session = SourceReadSession(
                self.root,
                self.head,
                max_source_bytes=MAX_SOURCE_BYTES,
                max_total_bytes=MAX_TOTAL_SOURCE_BYTES,
                seconds=SOURCE_SECONDS,
            )
        result = self.session.read(path)
        if result.metadata is not None:
            return ReferenceSourceInfo(result.metadata.line_count)
        return ReferenceSourceInfo(
            reason=(
                "reference"
                if result.reason in {"missing-source", "invalid-source"}
                else "budget"
                if result.reason in {"source-limit", "budget"}
                else "unavailable"
            )
        )
