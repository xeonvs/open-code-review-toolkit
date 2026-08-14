"""Small cross-platform filesystem durability helpers."""

from __future__ import annotations

import errno
import os


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
