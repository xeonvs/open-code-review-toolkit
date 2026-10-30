"""Freeze explicit, bounded input selections without following or executing them."""

from __future__ import annotations

import codecs
import hashlib
import os
import selectors
import stat
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from ocr_toolkit.common.filesystem import fsync_directory, open_private_parent_directory
from ocr_toolkit.evidence.repository import GitRepositoryReader

from .state import DIGEST, MAX_DOCUMENT, AuditError, State, encode, fields, identifier, read_regular

MAX_FILE = 1_048_576
MAX_TOTAL = 16_777_216
MAX_FILES = 20_000
MAX_UNITS = 200_000


class InputSkipped(AuditError):
    """Account for a refused source without reading it or aborting other inputs."""

    def __init__(
        self,
        reason: Literal[
            "oversize_input",
            "unsupported_input_type",
            "corpus_budget",
            "binary input",
            "non-UTF8 input",
        ],
    ) -> None:
        self.reason = reason
        super().__init__(
            "file size limit"
            if reason == "oversize_input"
            else "corpus size limit"
            if reason == "corpus_budget"
            else reason
            if reason in {"binary input", "non-UTF8 input"}
            else "unsupported input type"
        )


def read_input(descriptor: int, *, deadline: float) -> bytes:
    """Bound stdin acquisition even when a producer keeps its pipe open."""

    blocking = os.get_blocking(descriptor)
    try:
        os.set_blocking(descriptor, False)
        with selectors.PollSelector() as selector:
            selector.register(descriptor, selectors.EVENT_READ)
            value = bytearray()
            while len(value) <= MAX_FILE:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise AuditError("input deadline exceeded")
                try:
                    part = os.read(descriptor, min(65536, MAX_FILE + 1 - len(value)))
                except BlockingIOError:
                    continue
                if not part:
                    return bytes(value)
                value.extend(part)
            raise AuditError("file size limit")
    finally:
        os.set_blocking(descriptor, blocking)


def relative_path(value: str) -> str:
    """Accept an exact relative locator, including printable Unicode/newlines."""

    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 4096
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise AuditError("invalid input locator")
    return value


def private_location(state: State, root: Path) -> None:
    """Keep recoverable raw state outside the entire selected source root."""

    if state.path.is_relative_to(root.absolute()) or root.absolute().is_relative_to(state.path):
        raise AuditError("audit state must be outside input roots")


def _directory(root: Path) -> int:
    """Pin a physical source root without accepting a symlink ancestor."""

    parent, name = open_private_parent_directory(root, create=False)
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)


def selected_file(
    root_fd: int, path: str, *, max_bytes: int | None = None, textual: bool = True
) -> bytes:
    """Read a regular single-link source file and prove it stayed unchanged."""

    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 0):
        raise AuditError("invalid source byte budget")
    parts = relative_path(path).split("/")
    parent = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise InputSkipped("unsupported_input_type")
            if before.st_size > MAX_FILE:
                raise InputSkipped("oversize_input")
            if max_bytes is not None and before.st_size > max_bytes:
                raise InputSkipped("corpus_budget")
            value = bytearray()
            decoder = codecs.getincrementaldecoder("utf-8")() if textual else None
            limit = min(MAX_FILE, max_bytes) if max_bytes is not None else MAX_FILE
            while len(value) <= limit:
                chunk = os.read(fd, min(65536, limit + 1 - len(value)))
                if not chunk:
                    if decoder is not None:
                        try:
                            decoder.decode(b"", final=True)
                        except UnicodeError as exc:
                            raise InputSkipped("non-UTF8 input") from exc
                    break
                if textual and b"\x00" in chunk:
                    raise InputSkipped("binary input")
                if decoder is not None:
                    try:
                        decoder.decode(chunk, final=False)
                    except UnicodeError as exc:
                        raise InputSkipped("non-UTF8 input") from exc
                value.extend(chunk)
            after = os.fstat(fd)
            current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)

            def signature(item: os.stat_result) -> tuple[int, int, int, int, int]:
                return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)

            if signature(before) != signature(after) or signature(after) != signature(current):
                raise AuditError("input changed during capture")
            if len(value) > MAX_FILE:
                raise InputSkipped("oversize_input")
            if len(value) > limit:
                raise InputSkipped("corpus_budget")
            return bytes(value)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def input_units(raw: bytes) -> int:
    """Count the exact population evaluated by both scanner roles."""

    if b"\x00" in raw:
        raise AuditError("binary input")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise AuditError("non-UTF8 input") from exc
    return 1 + sum(bool(line.strip()) for line in text.splitlines())


def capture(
    state: State,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
    git_ref: str | None = None,
    snippet: bytes | None = None,
    metadata_only: bool = False,
    deadline: float,
    git_seconds: int = 120,
) -> str:
    """Capture accepted input bytes with a recovery owner established first."""

    identity = uuid.uuid4().hex
    if metadata_only and (
        root is None or paths is None or git_ref is not None or snippet is not None
    ):
        raise AuditError("metadata-only mode requires an explicit file selection")
    candidates: list[tuple[str, bytes | None, str | None]] = []
    origin: dict[str, Any]
    if snippet is not None:
        if root is not None or paths is not None or git_ref is not None:
            raise AuditError("conflicting input modes")
        candidates = [("snippet.txt", snippet, None)]
        origin = {"kind": "snippet", "root": None, "revision": None}
    else:
        if root is None:
            raise AuditError("input root is required")
        root = root.absolute()
        if ".." in root.parts:
            raise AuditError("input root must be normalized")
        private_location(state, root)
        root_fd = _directory(root)
        try:
            if git_ref is not None:
                if paths is not None:
                    raise AuditError("conflicting input modes")
                reader = GitRepositoryReader(
                    root, max_file_bytes=MAX_FILE, deadline=deadline, command_timeout=git_seconds
                )
                revision = reader.resolve_commit(git_ref)
                entries = reader.list_objects(revision, max_entries=MAX_FILES)
                regular = tuple(entry for entry in entries if entry.mode in {"100644", "100755"})
                blobs: dict[str, bytes] = {}
                remaining_bytes = MAX_TOTAL
                for offset in range(0, len(regular), 1000):
                    batch = reader.read_candidate_blobs(
                        regular[offset : offset + 1000], max_total_bytes=remaining_bytes
                    ).blobs
                    remaining_bytes -= sum(len(raw) for raw in batch.values())
                    blobs.update(batch)
                for entry in entries:
                    raw = blobs.get(entry.path)
                    candidates.append(
                        (
                            relative_path(entry.path),
                            raw,
                            "unsupported_git_object"
                            if entry.mode not in {"100644", "100755"}
                            else "unreadable_blob"
                            if raw is None
                            else None,
                        )
                    )
                origin = {"kind": "git", "root": str(root), "revision": revision}
            else:
                if not paths or len(paths) > MAX_FILES or len(set(paths)) != len(paths):
                    raise AuditError("file selection must be nonempty, unique and bounded")
                total = 0
                for path in sorted(paths):
                    if time.monotonic() >= deadline:
                        raise AuditError("capture deadline exceeded")
                    path = relative_path(path)
                    try:
                        raw = selected_file(root_fd, path, max_bytes=MAX_TOTAL - total)
                        total += len(raw)
                        if total > MAX_TOTAL:
                            raise AuditError("corpus size limit")
                        candidates.append((path, raw, None))
                    except InputSkipped as exc:
                        candidates.append((path, None, exc.reason))
                    except OSError:
                        candidates.append((path, None, "unreadable_input"))
                # The selection must stay stable across capture, not only during
                # each individual read. Never silently call a moving tree frozen.
                for path, raw, error in candidates:
                    if time.monotonic() >= deadline:
                        raise AuditError("capture deadline exceeded")
                    if error is None and selected_file(root_fd, path) != raw:
                        raise AuditError("input selection changed during capture")
                origin = {"kind": "files", "root": str(root), "revision": None}
        finally:
            os.close(root_fd)
    if len(candidates) > MAX_FILES:
        raise AuditError("file count limit")
    files: list[dict[str, Any]] = []
    accepted: list[tuple[str, bytes]] = []
    total_bytes = 0
    total_units = 0
    manifest_bytes = 0
    for path, raw, error in candidates:
        slot = uuid.uuid4().hex
        units = 0
        if raw is not None and error is None:
            total_bytes += len(raw)
            if len(raw) > MAX_FILE or total_bytes > MAX_TOTAL:
                raise AuditError("corpus size limit")
            try:
                units = input_units(raw)
            except AuditError as exc:
                error = str(exc)  # Only our own closed diagnoses reach state.
            if error is None:
                total_units += units
                accepted.append((slot, raw))
        digest = state.mac("source", hashlib.sha256(raw).hexdigest()) if raw is not None else None
        member = {
            "slot": slot,
            "path": path,
            "digest": digest,
            "units": units,
            "lines": len(raw.decode().splitlines()) if error is None and raw is not None else 0,
            "error": error,
        }
        manifest_bytes += len(encode(member)) + 1
        if manifest_bytes > MAX_DOCUMENT - 65536:
            raise AuditError("corpus manifest size limit")
        files.append(member)
    if total_units > MAX_UNITS or time.monotonic() >= deadline:
        raise AuditError("capture unit or time limit")
    manifest = {
        "origin": origin,
        "files": files,
        "units": total_units,
        "bytes": total_bytes,
        "storage": "original" if metadata_only else "snapshot",
        "raw_removed": metadata_only,
    }
    # An authenticated inventory exists before the first raw byte is persisted.
    state.save("corpus", identity, manifest)
    if metadata_only:
        return identity
    raw_fd = state.raw_directory(identity, create=True)
    try:
        for slot, raw in accepted:
            if time.monotonic() >= deadline:
                raise AuditError("capture deadline exceeded")
            fd = os.open(slot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=raw_fd)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        fsync_directory(raw_fd)
    finally:
        os.close(raw_fd)
    return identity


def manifest(state: State, identity: str) -> dict[str, Any]:
    """Validate all persisted corpus fields atomically before reading raw slots."""

    value = fields(
        state.load("corpus", identity),
        {"origin", "files", "units", "bytes", "storage", "raw_removed"},
    )
    origin = fields(value["origin"], {"kind", "root", "revision"})
    if (
        origin["kind"] not in {"git", "files", "snippet"}
        or not isinstance(value["files"], list)
        or len(value["files"]) > MAX_FILES
        or type(value["raw_removed"]) is not bool
        or value["storage"] not in {"original", "snapshot"}
        or type(value["units"]) is not int
        or not 0 <= value["units"] <= MAX_UNITS
        or type(value["bytes"]) is not int
        or not 0 <= value["bytes"] <= MAX_TOTAL
    ):
        raise AuditError("invalid corpus manifest")
    if value["storage"] == "original" and (origin["kind"] != "files" or not value["raw_removed"]):
        raise AuditError("invalid source-only storage")
    if origin["kind"] == "snippet":
        if origin["root"] is not None or origin["revision"] is not None:
            raise AuditError("invalid snippet origin")
    elif not isinstance(origin["root"], str) or not Path(origin["root"]).is_absolute():
        raise AuditError("invalid input origin")
    if origin["kind"] == "git":
        revision = origin["revision"]
        if (
            not isinstance(revision, str)
            or len(revision) != 40
            or any(char not in "abcdef0123456789" for char in revision)
        ):
            raise AuditError("invalid Git origin")
    elif origin["revision"] is not None:
        raise AuditError("invalid input revision")
    slots: set[str] = set()
    paths: set[str] = set()
    for item in value["files"]:
        fields(item, {"slot", "path", "digest", "units", "lines", "error"})
        slot = identifier(item["slot"])
        path = relative_path(item["path"])
        if slot in slots or path in paths:
            raise AuditError("duplicate corpus member")
        slots.add(slot)
        paths.add(path)
        if (
            type(item["units"]) is not int
            or not 0 <= item["units"] <= MAX_UNITS
            or type(item["lines"]) is not int
            or not 0 <= item["lines"] <= MAX_FILE + 1
            or item["units"] > item["lines"] + 1
            or item["error"]
            not in {
                None,
                "unsupported_git_object",
                "unreadable_blob",
                "unreadable_input",
                "oversize_input",
                "unsupported_input_type",
                "corpus_budget",
                "binary input",
                "non-UTF8 input",
            }
            or (
                item["digest"] is not None
                and (
                    not isinstance(item["digest"], str) or DIGEST.fullmatch(item["digest"]) is None
                )
            )
            or (item["error"] is None and (item["digest"] is None or item["units"] < 1))
            or (item["error"] is not None and item["units"] != 0)
        ):
            raise AuditError("invalid corpus member")
    if sum(item["units"] for item in value["files"]) != value["units"]:
        raise AuditError("invalid unit population")
    return value


def read_source(state: State, raw_fd: int, item: dict[str, Any]) -> bytes:
    """Bind a raw snapshot to its authenticated content and unit population."""

    raw = read_regular(raw_fd, identifier(item["slot"]), MAX_FILE)
    verify_source(state, raw, item)
    return raw


def verify_source(state: State, raw: bytes, item: dict[str, Any]) -> None:
    """Reject original/snapshot drift before treating absent hits as passes."""

    if (
        state.mac("source", hashlib.sha256(raw).hexdigest()) != item["digest"]
        or input_units(raw) != item["units"]
        or len(raw.decode().splitlines()) != item["lines"]
    ):
        raise AuditError("source snapshot does not match manifest")


def original_source(state: State, value: dict[str, Any], item: dict[str, Any]) -> bytes:
    """Read one exact original, without retaining an entire corpus in memory."""

    root = Path(value["origin"]["root"])
    private_location(state, root)
    descriptor = _directory(root)
    try:
        raw = selected_file(descriptor, item["path"])
        verify_source(state, raw, item)
        return raw
    finally:
        os.close(descriptor)


def verify_originals(state: State, value: dict[str, Any], *, deadline: float) -> None:
    """Check all fingerprints in a bounded pass before and after evaluation."""

    for item in value["files"]:
        if time.monotonic() >= deadline:
            raise AuditError("source verification deadline exceeded")
        if item["error"] is None:
            original_source(state, value, item)


def cleanup(state: State, identity: str) -> None:
    """Remove only inventoried raw slots, preserving source-free evidence and originals."""

    value = manifest(state, identity)
    name = "raw-" + identifier(identity)
    try:
        raw_fd = state.raw_directory(identity)
    except FileNotFoundError:
        raw_fd = -1
    if raw_fd >= 0:
        try:
            known = {item["slot"] for item in value["files"] if item["error"] is None}
            present = set(os.listdir(raw_fd))
            if not present <= known:
                raise AuditError("raw directory has unowned entries")
            # Validate every entry before removing any; never follow a substituted link.
            for slot in present:
                info = os.stat(slot, dir_fd=raw_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600
                ):
                    raise AuditError("unsafe raw cleanup member")
            for slot in present:
                os.unlink(slot, dir_fd=raw_fd)
            fsync_directory(raw_fd)
            if os.listdir(raw_fd):
                raise AuditError("raw cleanup is incomplete")
        finally:
            os.close(raw_fd)
        os.rmdir(name, dir_fd=state.fd)
    if os.path.lexists(state.path / name):
        raise AuditError("raw cleanup is incomplete")
    value["raw_removed"] = True
    state.save("corpus", identity, value)
    fsync_directory(state.fd)
