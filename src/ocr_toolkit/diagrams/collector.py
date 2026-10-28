"""Serialize bounded private submissions from all MCP processes in one run."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path
from typing import cast

from ocr_toolkit.common.filesystem import (
    fsync_directory,
    open_private_parent_directory,
    same_file_identity,
)
from ocr_toolkit.diagrams.contracts import (
    MAX_DIAGRAM_BYTES,
    MAX_SUBMISSION_BYTES,
    MAX_SUBMISSIONS,
    DiagramError,
    DiagramReason,
    DiagramSubmission,
    bounded_json,
    parse_submission,
    submission_payload,
)
from ocr_toolkit.review_range import ReviewRange

COLLECTOR_SCHEMA = "ocr.diagram-collector/v1"
MAX_COLLECTOR_BYTES = MAX_DIAGRAM_BYTES + 1024
_COLLECTOR_KEYS = {
    "schema",
    "run_id",
    "base_sha",
    "head_sha",
    "submissions",
    "input_bytes",
    "reason",
    "candidate",
}


@dataclass(frozen=True, slots=True)
class CollectorSnapshot:
    """A private validated snapshot, read before the runner removes artifacts."""

    submissions: int
    input_bytes: int
    reason: DiagramReason
    candidate: DiagramSubmission | None


@dataclass(frozen=True, slots=True)
class DiagramCollector:
    """Bind the output capability to caller-owned private path, run and range."""

    path: Path
    run_id: str
    review_range: ReviewRange

    def __post_init__(self) -> None:
        if not self.path.is_absolute() or re.fullmatch(r"[a-f0-9]{32}", self.run_id) is None:
            raise DiagramError("diagram collector binding is invalid")

    def _parent(self) -> tuple[int, str]:
        descriptor, name = open_private_parent_directory(self.path, create=False)
        try:
            metadata = os.fstat(descriptor)
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
                raise DiagramError("diagram collector parent is not private")
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor, name

    @contextmanager
    def _locked(self) -> Iterator[tuple[int, str]]:
        parent, name = self._parent()
        lock = -1
        try:
            lock_name = f".{name}.lock"
            lock = os.open(
                lock_name,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=parent,
            )
            opened = os.fstat(lock)
            _private_regular(opened)
            deadline = time.monotonic() + 1.0
            while True:
                try:
                    flock(lock, LOCK_EX | LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise DiagramError("diagram collector lock is unavailable") from None
                    time.sleep(0.01)
            if not same_file_identity(
                opened, os.stat(lock_name, dir_fd=parent, follow_symlinks=False)
            ):
                raise DiagramError("diagram collector lock changed")
            yield parent, name
        finally:
            if lock >= 0:
                os.close(lock)
            os.close(parent)

    def initialize(self) -> None:
        """Create a fresh run state before exposing its fixed output capability."""

        with self._locked() as (parent, name):
            try:
                os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise DiagramError("diagram collector already exists")
            self._write(parent, name, CollectorSnapshot(0, 0, "none", None))

    def _read(self, parent: int, name: str) -> CollectorSnapshot:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            metadata = os.fstat(descriptor)
            _private_regular(metadata)
            if metadata.st_size > MAX_COLLECTOR_BYTES:
                raise DiagramError("diagram collector exceeds its byte budget")
            raw = os.read(descriptor, MAX_COLLECTOR_BYTES + 1)
            if len(raw) != metadata.st_size or len(raw) > MAX_COLLECTOR_BYTES:
                raise DiagramError("diagram collector size changed")
            if not same_file_identity(
                metadata, os.stat(name, dir_fd=parent, follow_symlinks=False)
            ):
                raise DiagramError("diagram collector changed during read")
        finally:
            os.close(descriptor)
        try:
            value = json.loads(raw, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise DiagramError("diagram collector JSON is invalid") from exc
        if not isinstance(value, dict) or set(value) != _COLLECTOR_KEYS:
            raise DiagramError("diagram collector shape is invalid")
        if (value["schema"], value["run_id"], value["base_sha"], value["head_sha"]) != (
            COLLECTOR_SCHEMA,
            self.run_id,
            self.review_range.base,
            self.review_range.head,
        ):
            raise DiagramError("diagram collector belongs to a different run or range")
        count, size, reason = value["submissions"], value["input_bytes"], value["reason"]
        if (
            type(count) is not int
            or not 0 <= count <= MAX_SUBMISSIONS + 1
            or type(size) is not int
            or not 0 <= size <= MAX_SUBMISSION_BYTES + 1
            or reason not in ("none", "invalid", "conflict", "budget")
            or ((count == 0) != (size == 0))
            or (reason == "budget") != (count > MAX_SUBMISSIONS or size > MAX_SUBMISSION_BYTES)
            or (count == 0 and reason != "none")
        ):
            raise DiagramError("diagram collector counters or reason are invalid")
        candidate = value["candidate"]
        parsed = (
            parse_submission(candidate, expected_range=self.review_range)
            if candidate is not None
            else None
        )
        if (parsed is not None) != (count > 0 and reason == "none"):
            raise DiagramError("diagram collector candidate state is inconsistent")
        return CollectorSnapshot(count, size, cast(DiagramReason, reason), parsed)

    def read(self) -> CollectorSnapshot:
        """Take a serialized hostile-read snapshot before any cleanup occurs."""

        with self._locked() as (parent, name):
            return self._read(parent, name)

    def _write(self, parent: int, name: str, snapshot: CollectorSnapshot) -> None:
        payload = {
            "schema": COLLECTOR_SCHEMA,
            "run_id": self.run_id,
            "base_sha": self.review_range.base,
            "head_sha": self.review_range.head,
            "submissions": snapshot.submissions,
            "input_bytes": snapshot.input_bytes,
            "reason": snapshot.reason,
            "candidate": submission_payload(snapshot.candidate)
            if snapshot.candidate is not None
            else None,
        }
        encoded = bounded_json(payload, limit=MAX_COLLECTOR_BYTES)
        temporary = f".{name}.{secrets.token_hex(8)}"
        descriptor = -1
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent,
            )
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            fsync_directory(parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass

    def submit(self, value: object, *, input_bytes: int | None = None) -> CollectorSnapshot:
        """Count every attempt; retain only identical normalized valid candidates."""

        # MCP already bounds the wire request. This additional cap also applies
        # when an in-process caller supplies an unserializable or oversized value.
        try:
            size = len(bounded_json(value, limit=MAX_SUBMISSION_BYTES))
        except DiagramError:
            size = MAX_SUBMISSION_BYTES + 1
        if input_bytes is not None:
            if type(input_bytes) is not int or input_bytes < size:
                raise DiagramError("diagram wire byte count is invalid")
            # The transport supplies the original request length, including
            # whitespace/escaping. Compact normalization cannot shrink away the
            # run-wide input budget. This value is never a model argument.
            size = input_bytes
        with self._locked() as (parent, name):
            previous = self._read(parent, name)
            count = min(previous.submissions + 1, MAX_SUBMISSIONS + 1)
            total = min(previous.input_bytes + max(1, size), MAX_SUBMISSION_BYTES + 1)
            reason = previous.reason
            candidate = previous.candidate
            if count > MAX_SUBMISSIONS or total > MAX_SUBMISSION_BYTES:
                reason = "budget"
            elif reason == "none":
                try:
                    parsed = parse_submission(value, expected_range=self.review_range)
                except DiagramError:
                    reason = "invalid"
                else:
                    if candidate is not None and candidate != parsed:
                        reason = "conflict"
                    else:
                        candidate = parsed
            snapshot = CollectorSnapshot(
                count, total, reason, candidate if reason == "none" else None
            )
            self._write(parent, name, snapshot)
            return snapshot


def _private_regular(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise DiagramError("diagram collector file is unsafe")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DiagramError("diagram collector has duplicate JSON keys")
        result[key] = value
    return result
