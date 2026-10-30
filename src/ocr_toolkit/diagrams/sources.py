"""Bounded immutable text metadata for optional diagram reference checks."""

from __future__ import annotations

import re
import time
from pathlib import Path
from subprocess import TimeoutExpired

from ocr_toolkit.diagrams.contracts import ReferenceSourceInfo
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryReadBudget,
    RepositoryTextInvalid,
)

MAX_SOURCE_BYTES = 5_000_000
MAX_TOTAL_SOURCE_BYTES = 32_000_000
SOURCE_SECONDS = 30


class DiagramSourceReader:
    """One lazy session bound to an immutable head, retaining metadata only."""

    def __init__(self, root: Path, head: str) -> None:
        if re.fullmatch(r"[0-9a-f]{40}", head) is None:
            raise ValueError("diagram source head must be immutable")
        self.root = root
        self.head = head
        self._reader: GitRepositoryReader | None = None
        self._deadline: float | None = None
        self._used = 0
        self._paths: dict[str, ReferenceSourceInfo] = {}
        self._objects: dict[str, ReferenceSourceInfo] = {}

    def __call__(self, path: str) -> ReferenceSourceInfo:
        if path in self._paths:
            return self._paths[path]
        result = self._read(path)
        self._paths[path] = result
        return result

    def _read(self, path: str) -> ReferenceSourceInfo:
        try:
            if self._deadline is None:
                self._deadline = time.monotonic() + SOURCE_SECONDS
            if time.monotonic() >= self._deadline:
                return ReferenceSourceInfo(reason="budget")
            if self._reader is None:
                self._reader = GitRepositoryReader(
                    self.root,
                    max_file_bytes=MAX_SOURCE_BYTES,
                    deadline=self._deadline,
                    command_timeout=SOURCE_SECONDS,
                )
            entry = self._reader.object_at(self.head, path)
            if (
                entry is None
                or entry.mode not in {"100644", "100755"}
                or entry.object_type != "blob"
            ):
                return ReferenceSourceInfo(reason="reference")
            if entry.object_sha in self._objects:
                return self._objects[entry.object_sha]
            size = self._reader.bounded_regular_blob_size(entry)
            if size > MAX_TOTAL_SOURCE_BYTES - self._used:
                return ReferenceSourceInfo(reason="budget")
            # Charge the preflight size even if decoding fails near EOF. Failed
            # aliases cannot be used to acquire the same malformed blob again.
            self._used += size
            try:
                metadata = self._reader.read_text_metadata(entry, max_bytes=size)
                result = ReferenceSourceInfo(metadata.line_count)
            except (UnicodeError, RepositoryTextInvalid):
                result = ReferenceSourceInfo(reason="reference")
            except RepositoryReadBudget:
                result = ReferenceSourceInfo(reason="budget")
            except TimeoutExpired:
                result = ReferenceSourceInfo(reason="budget")
            except (OSError, RepositoryEvidenceError):
                result = ReferenceSourceInfo(
                    reason="budget" if time.monotonic() >= self._deadline else "unavailable"
                )
            self._objects[entry.object_sha] = result
            return result
        except (RepositoryReadBudget, TimeoutExpired):
            return ReferenceSourceInfo(reason="budget")
        except (OSError, ValueError):
            return ReferenceSourceInfo(
                reason="budget"
                if self._deadline is not None and time.monotonic() >= self._deadline
                else "unavailable"
            )
