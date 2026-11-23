"""Own the atomic snapshot and completed report pairs outside Git worktrees."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ocr_toolkit.common.filesystem import fsync_directory, open_private_parent_directory
from ocr_toolkit.telemetry.snapshot import SCHEMA, read_document
from ocr_toolkit.telemetry.snapshot import TelemetryError as TelemetryError

SNAPSHOT = "snapshot.json"
MAX_BYTES = 128 * 1024 * 1024


def _outside_worktree(directory: int) -> None:
    try:
        os.stat(".git", dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise TelemetryError("Choose a physical state directory outside all Git worktrees.")


@contextmanager
def private_directory(path: Path, *, create: bool) -> Iterator[int]:
    path = path.expanduser().absolute()
    if ".." in path.parts:
        raise TelemetryError("Choose a physical state directory outside all Git worktrees.")
    parent, name = open_private_parent_directory(
        path, create=create, check_directory=_outside_worktree
    )
    try:
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        _outside_worktree(directory)
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise TelemetryError("State directory must be owned by this user with mode 0700.")
        try:
            fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TelemetryError("Telemetry state is busy.") from exc
        yield directory
    finally:
        os.close(directory)


def _file_info(info: os.stat_result) -> None:
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
    ):
        raise TelemetryError("Unsafe telemetry file.")


def read_snapshot(directory: int) -> dict[str, Any]:
    fd = os.open(SNAPSHOT, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(fd)
        _file_info(info)
        if info.st_size > MAX_BYTES:
            raise TelemetryError("Snapshot exceeds the size limit.")
        raw = stream.read(info.st_size + 1)
        if len(raw) != info.st_size or os.fstat(fd).st_ctime_ns != info.st_ctime_ns:
            raise TelemetryError("Snapshot changed while reading.")
    return read_document(raw)


def _write_new(directory: int, name: str, data: bytes) -> None:
    if len(data) > MAX_BYTES:
        raise TelemetryError("Telemetry output exceeds the size limit.")
    fd = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
    )
    with os.fdopen(fd, "wb") as stream:
        os.fchmod(fd, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(fd)


def _json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def save_snapshot(directory: int, snapshot: dict[str, Any]) -> None:
    try:
        existing = os.stat(SNAPSHOT, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        _file_info(existing)
    temp = ".snapshot-" + uuid.uuid4().hex
    try:
        raw = _json({**snapshot, "schema": SCHEMA})
        if len(raw) > MAX_BYTES:
            raise TelemetryError("Telemetry output exceeds the size limit.")
        read_document(raw)
        _write_new(directory, temp, raw)
        os.replace(temp, SNAPSHOT, src_dir_fd=directory, dst_dir_fd=directory)
        fsync_directory(directory)
    finally:
        try:
            os.unlink(temp, dir_fd=directory)
        except FileNotFoundError:
            pass


def save_report(directory: int, html: str, report: dict[str, Any], lang: str) -> str:
    """Publish both files together; a failed render cannot replace an earlier pair."""
    identity = uuid.uuid4().hex
    temp = ".render-" + identity
    name = f"report-{lang}-{identity}"
    os.mkdir(temp, mode=0o700, dir_fd=directory)
    try:
        child = os.open(temp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    except OSError:
        os.rmdir(temp, dir_fd=directory)
        raise
    try:
        _write_new(child, "report.html", html.encode())
        _write_new(child, "report.json", _json(report))
        fsync_directory(child)
        os.rename(temp, name, src_dir_fd=directory, dst_dir_fd=directory)
    except BaseException:
        for leaf in ("report.html", "report.json"):
            try:
                os.unlink(leaf, dir_fd=child)
            except FileNotFoundError:
                pass
        os.rmdir(temp, dir_fd=directory)
        raise
    finally:
        os.close(child)
    fsync_directory(directory)
    return name
