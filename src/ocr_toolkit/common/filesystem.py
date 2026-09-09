"""Small cross-platform filesystem durability helpers."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path


def fsync_directory(descriptor: int) -> None:
    """Persist a directory-entry change when the platform supports it."""

    try:
        os.fsync(descriptor)
    except OSError as exc:
        # Some supported filesystems reject directory fsync even though the
        # atomic rename itself succeeded. Ignore only documented unsupported
        # descriptor/filesystem cases; propagate genuine durability failures.
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EBADF}:
            raise


def open_private_parent_directory(path: Path) -> tuple[int, str]:
    """Open a path's parent without following replaceable pathname components.

    The returned descriptor pins the parent directory.  Callers must use
    descriptor-relative operations and close it themselves; returning an
    absolute pathname would reintroduce the ancestor replacement race this
    helper avoids.
    """

    absolute = path.absolute()
    parts = [part for part in absolute.parts if part != os.path.sep]
    if not parts:
        raise ValueError("private output path must name a file or directory")
    descriptor = os.open(os.path.sep, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                try:
                    child = os.open(component, flags, dir_fd=descriptor)
                except OSError as exc:
                    raise ValueError("private output parent must not be a symlink") from exc
            except OSError as exc:
                raise ValueError("private output parent must not be a symlink") from exc
            os.close(descriptor)
            descriptor = child
        parent = os.fstat(descriptor)
        if not stat.S_ISDIR(parent.st_mode):
            raise OSError("private output parent is not a directory")
        return descriptor, parts[-1]
    except BaseException:
        os.close(descriptor)
        raise


def same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare two pinned filesystem identities without following pathnames."""

    return left.st_dev == right.st_dev and left.st_ino == right.st_ino
