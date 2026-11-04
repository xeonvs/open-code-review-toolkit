"""One immutable, bounded Git text session with preplanned excerpt ranges."""

from __future__ import annotations

import math
import re
import time
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path
from subprocess import TimeoutExpired

from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryObject,
    RepositoryReadBudget,
    RepositoryTextInvalid,
)
from ocr_toolkit.evidence.text_contracts import (
    MAX_SOURCE_BYTES,
    MAX_SYNTAX_CACHE_FILES,
    MAX_SYNTAX_CHARS,
    MAX_TOTAL_SOURCE_BYTES,
    SOURCE_SECONDS,
    RepositoryTextExcerpt,
    SourceReadResult,
    TextSpan,
)
from ocr_toolkit.evidence.text_excerpts import MAX_TEXT_SPANS, validate_spans


class SourceReadSession:
    """Coalesce aliases before streaming; never retry a charged immutable object."""

    def __init__(
        self,
        root: Path,
        head: str,
        requests: dict[str, tuple[TextSpan, ...]] | None = None,
        *,
        max_source_bytes: int = MAX_SOURCE_BYTES,
        max_total_bytes: int = MAX_TOTAL_SOURCE_BYTES,
        seconds: float = SOURCE_SECONDS,
        retain_syntax: bool = True,
    ) -> None:
        if not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{40}", head) is None:
            raise ValueError("source head must be immutable")
        if requests is not None and not isinstance(requests, dict):
            raise ValueError("invalid source request mapping")
        if (
            type(max_source_bytes) is not int
            or not 0 <= max_source_bytes <= MAX_SOURCE_BYTES
            or type(max_total_bytes) is not int
            or not 0 <= max_total_bytes <= MAX_TOTAL_SOURCE_BYTES
            or type(seconds) not in {int, float}
            or not math.isfinite(seconds)
            or not 0 <= seconds <= SOURCE_SECONDS
            or type(retain_syntax) is not bool
        ):
            raise ValueError("invalid source session budgets")
        self.root, self.head = root, head
        self._requests = dict(requests or {})
        if len(self._requests) > MAX_TEXT_SPANS:
            raise RepositoryReadBudget("source request population exceeds limit")
        for path, spans in self._requests.items():
            if not isinstance(path, str) or len(path) > 1024:
                raise ValueError("invalid source request path")
            if isinstance(spans, tuple) and len(spans) > MAX_TEXT_SPANS:
                raise RepositoryReadBudget("source request population exceeds limit")
            validate_spans(spans)
        if sum(map(len, self._requests.values())) > MAX_TEXT_SPANS:
            raise RepositoryReadBudget("source request population exceeds limit")
        self._max_source, self._max_total, self._seconds = (
            max_source_bytes,
            max_total_bytes,
            seconds,
        )
        self._retain_syntax = retain_syntax
        self._reader: GitRepositoryReader | None = None
        self._deadline: float | None = None
        self._paths: dict[str, RepositoryObject | SourceReadResult] = {}
        self._objects: dict[str, SourceReadResult] = {}
        self._spans: dict[str, set[TextSpan]] = {}
        self._excerpts: dict[str, dict[TextSpan, RepositoryTextExcerpt]] = {}
        self._syntax: OrderedDict[str, str] = OrderedDict()
        self._used = self._retained = 0
        self._initial_error: SourceReadResult | None = None

    def _lookup(self, path: str) -> RepositoryObject | SourceReadResult:
        if path in self._paths:
            return self._paths[path]
        try:
            assert self._reader is not None
            entry = self._reader.object_at(self.head, path)
            result: RepositoryObject | SourceReadResult = (
                entry
                if entry is not None
                and entry.mode in {"100644", "100755"}
                and entry.object_type == "blob"
                else SourceReadResult(reason="missing-source")
            )
        except (RepositoryReadBudget, TimeoutExpired):
            result = SourceReadResult(reason="budget")
        except Exception:
            result = SourceReadResult(reason="budget" if self._expired() else "unavailable")
        self._paths[path] = result
        return result

    def _expired(self) -> bool:
        return self._deadline is not None and time.monotonic() >= self._deadline

    @property
    def used_bytes(self) -> int:
        return self._used

    @property
    def retained_bytes(self) -> int:
        return self._retained

    def _prepare(self) -> None:
        if self._deadline is not None:
            return
        self._deadline = time.monotonic() + self._seconds
        self._reader = GitRepositoryReader(
            self.root,
            max_file_bytes=self._max_source,
            deadline=self._deadline,
            command_timeout=max(0.001, self._seconds),
        )
        for path, spans in self._requests.items():
            entry = self._lookup(path)
            if spans and isinstance(entry, RepositoryObject):
                self._spans.setdefault(entry.object_sha, set()).update(spans)

    def read(self, path: str) -> SourceReadResult:
        """Return complete facts only; errors carry a closed source-free reason."""

        if self._initial_error is not None:
            return self._initial_error
        if not isinstance(path, str) or len(path) > 1024:
            return SourceReadResult(reason="missing-source")
        try:
            self._prepare()
            entry = self._lookup(path)
            if isinstance(entry, SourceReadResult):
                return entry
            if entry.object_sha not in self._objects:
                self._objects[entry.object_sha] = self._read(entry)
            result = self._objects[entry.object_sha]
            source = self._syntax.get(entry.object_sha)
            if source is not None:
                self._syntax.move_to_end(entry.object_sha)
            return replace(result, syntax_source=source)
        except (RepositoryReadBudget, TimeoutExpired):
            result = SourceReadResult(reason="budget")
        except Exception:
            result = SourceReadResult(reason="budget" if self._expired() else "unavailable")
        if self._reader is None:
            self._initial_error = result
        return result

    def read_excerpt(self, path: str, start: int, end: int) -> SourceReadResult:
        """Project one preplanned span in constant time without another blob read."""

        result = self.read(path)
        if result.metadata is None:
            return result
        piece = self._excerpts.get(result.metadata.object_sha, {}).get((start, end))
        metadata = replace(result.metadata, excerpts=(piece,) if piece is not None else ())
        return replace(result, metadata=metadata)

    def _read(self, entry: RepositoryObject) -> SourceReadResult:
        assert self._reader is not None
        try:
            if self._expired():
                return SourceReadResult(reason="budget")
            try:
                size = self._reader.bounded_regular_blob_size(entry)
            except RepositoryReadBudget:
                return SourceReadResult(reason="budget" if self._expired() else "source-limit")
            if size > self._max_total - self._used:
                return SourceReadResult(reason="budget")
            self._used += size
            metadata = self._reader.read_text_metadata(
                entry,
                max_bytes=size,
                spans=tuple(sorted(self._spans.get(entry.object_sha, ()))),
                max_excerpt_bytes=self._max_total - self._retained,
                max_source_chars=(
                    MAX_SYNTAX_CHARS
                    if self._retain_syntax and entry.object_sha in self._spans
                    else 0
                ),
            )
            if metadata.object_sha != entry.object_sha or metadata.byte_count != size:
                raise RepositoryEvidenceError("source metadata has a different object identity")
            self._excerpts[entry.object_sha] = {
                (item.start_line, item.end_line): item for item in metadata.excerpts
            }
            self._retained += sum(
                len(item.text.encode()) for item in metadata.excerpts if item.text is not None
            )
            limited = (
                self._retain_syntax and metadata.source is None and entry.object_sha in self._spans
            )
            if metadata.source is not None:
                self._syntax[entry.object_sha] = metadata.source
                if len(self._syntax) > MAX_SYNTAX_CACHE_FILES:
                    self._syntax.popitem(last=False)
            return SourceReadResult(replace(metadata, source=None), "none", syntax_limited=limited)
        except (UnicodeError, RepositoryTextInvalid):
            return SourceReadResult(reason="invalid-source")
        except (RepositoryReadBudget, TimeoutExpired):
            return SourceReadResult(reason="budget")
        except Exception:
            return SourceReadResult(reason="budget" if self._expired() else "unavailable")
