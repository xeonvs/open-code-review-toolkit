"""Snapshot proof inputs and closed, source-free private audit diagnoses."""

from __future__ import annotations

import hashlib
from typing import Any

from ocr_toolkit.evidence.text_contracts import (
    MAX_SYNTAX_CHARS,
    RepositoryTextMetadata,
    SourceReadResult,
    excerpt_from_lines,
    source_lines,
)

from .state import AuditError, fields

PROOF_SCHEMA = "ocr.dlp-source-proof/v1"
SOURCE_REASONS = frozenset(
    {
        "not-requested",
        "verified",
        "invalid-request",
        "excerpt-limit",
        "line-mismatch",
        "excerpt-unavailable",
        "missing-source",
        "source-limit",
        "budget",
        "invalid-source",
        "unavailable",
    }
)
SYNTAX_REASONS = frozenset(
    {"not-requested", "qualified", "not-qualified", "source-limit", "not-retained"}
)


def snapshot_units(source: str) -> list[tuple[int, str, int, int]]:
    """Preserve historical splitlines identities with independent Git LF spans."""

    line_count = source.count("\n") + int(bool(source) and not source.endswith("\n"))
    units = [(0, source, 1, line_count)]
    source_line = 1
    for number, segment in enumerate(source.splitlines(keepends=True), 1):
        # One historical unit can be only part of an LF line. It must not gain
        # whole-line source proof; later units still need their actual LF address.
        value = segment.splitlines()[0]
        if value.strip():
            units.append((number, value, source_line, source_line))
        source_line += segment.count("\n")
    return units


class SnapshotProofSource:
    """Reuse one authenticated file; never parse a selected fragment as full syntax."""

    def __init__(self, source: str, path: str) -> None:
        self._source, self._path = source, path
        self._metadata: RepositoryTextMetadata | None = None
        self._lines: tuple[str, ...] = ()
        self._invalid = "\0" in source

    def read(self, path: str, start: int, end: int) -> SourceReadResult:
        if path != self._path:
            return SourceReadResult(reason="missing-source")
        if self._invalid:
            return SourceReadResult(reason="invalid-source")
        if self._metadata is None:
            encoded = self._source.encode()
            self._lines = source_lines(self._source)
            self._metadata = RepositoryTextMetadata(
                hashlib.sha256(encoded).hexdigest(), len(encoded), len(self._lines)
            )
        limited = len(self._source) > MAX_SYNTAX_CHARS
        return SourceReadResult(
            RepositoryTextMetadata(
                self._metadata.object_sha,
                self._metadata.byte_count,
                self._metadata.line_count,
                (excerpt_from_lines(self._lines, start, end),),
            ),
            "none",
            None if limited else self._source,
            limited,
        )


def validate_diagnoses(hit: dict[str, Any], *, required: bool) -> None:
    """Historical records remain frozen; new diagnostics are atomic and closed."""

    base = {"id", "slot", "unit", "role", "reason", "detector", "proof"}
    if not required:
        fields(hit, base)
        return
    fields(hit, base | {"source_proof", "syntax_proof"})
    source, syntax = hit["source_proof"], hit["syntax_proof"]
    if (
        not isinstance(source, str)
        or source not in SOURCE_REASONS
        or not isinstance(syntax, str)
        or syntax not in SYNTAX_REASONS
        or (source == "verified") != hit["proof"]
        or (not hit["proof"] and syntax != "not-requested")
    ):
        raise AuditError("invalid source proof diagnosis")
