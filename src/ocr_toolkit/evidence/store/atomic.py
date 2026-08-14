"""Persist one private evidence envelope with atomic owner-only replacement."""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

from ocr_toolkit.common.filesystem import fsync_directory


def atomic_write(path: Path, render: Callable[[], str]) -> None:
    """Atomically write rendered evidence without exposing a partial file."""

    parent_created = not path.parent.exists()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Do not mutate a caller-owned shared ancestor such as /tmp or the
    # repository root. Newly created artifact directories remain private.
    if parent_created:
        os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(render())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory_descriptor = os.open(path.parent, directory_flags)
        try:
            fsync_directory(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
