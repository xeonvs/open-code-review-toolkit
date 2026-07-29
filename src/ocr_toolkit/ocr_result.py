"""Own bounded OCR result loading and toolkit-authored result metadata."""

from __future__ import annotations

import errno
import json
import os
import secrets
import stat
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ocr_toolkit.common.redaction import sanitize_ocr_value

DEFAULT_MAX_RESULT_BYTES = 2_000_000
MAX_RESULT_BYTES_HARD_LIMIT = 20_000_000
TOOLKIT_RESULT_KEY = "_ocr_toolkit"
TOOLKIT_RESULT_SCHEMA_VERSION = 1


class OcrResultMissing(Exception):
    """The OCR result artifact is missing or unreadable on disk."""


class OcrResultMalformed(Exception):
    """The OCR result artifact exists but is not valid JSON."""


class OcrResultTooLarge(Exception):
    """The OCR result artifact exceeds the configured safety limit."""


def max_result_bytes() -> int:
    """Return the maximum OCR JSON artifact size to read into memory."""

    raw = os.getenv("OCR_MAX_RESULT_BYTES", str(DEFAULT_MAX_RESULT_BYTES)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        print(
            f"OCR_MAX_RESULT_BYTES is not an integer; using default {DEFAULT_MAX_RESULT_BYTES}.",
            file=sys.stderr,
        )
        return DEFAULT_MAX_RESULT_BYTES

    if parsed <= 0:
        print(
            f"OCR_MAX_RESULT_BYTES must be positive; using default {DEFAULT_MAX_RESULT_BYTES}.",
            file=sys.stderr,
        )
        return DEFAULT_MAX_RESULT_BYTES

    if parsed > MAX_RESULT_BYTES_HARD_LIMIT:
        print(
            f"OCR_MAX_RESULT_BYTES exceeds hard limit {MAX_RESULT_BYTES_HARD_LIMIT}; "
            f"using {MAX_RESULT_BYTES_HARD_LIMIT}.",
            file=sys.stderr,
        )
        return MAX_RESULT_BYTES_HARD_LIMIT

    return parsed


def _open_result(path: Path) -> int:
    """Open one result artifact without following a final symlink."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise OcrResultMissing(str(exc)) from exc
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink > 1:
        os.close(descriptor)
        raise OcrResultMissing(f"OCR result is not a private regular file: {path}")
    return descriptor


def _open_result_parent(path: Path) -> int:
    """Open the result parent directory for descriptor-relative replacement."""

    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path.parent, flags)
    except OSError as exc:
        raise OcrResultMissing(str(exc)) from exc
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise OcrResultMissing(f"OCR result parent is not a directory: {path.parent}")
    return descriptor


def _open_result_at(parent_descriptor: int, path: Path) -> int:
    """Open the result relative to its pinned parent without following a symlink."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise OcrResultMissing(str(exc)) from exc
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink > 1:
        os.close(descriptor)
        raise OcrResultMissing(f"OCR result is not a private regular file: {path}")
    return descriptor


def _create_private_temporary(parent_descriptor: int, path: Path) -> tuple[int, str]:
    """Create an owner-only sibling used for one atomic result replacement."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    for _attempt in range(128):
        name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise OcrResultMissing(
                f"could not create private OCR result replacement: {exc}"
            ) from exc
        try:
            os.fchmod(descriptor, 0o600)
        except OSError:
            os.close(descriptor)
            try:
                os.unlink(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise
        return descriptor, name
    raise OcrResultMissing("could not allocate a private OCR result replacement")


def _write_all(descriptor: int, payload: bytes) -> None:
    """Write a complete encoded result or fail without replacing the original."""

    written = 0
    while written < len(payload):
        try:
            count = os.write(descriptor, payload[written:])
        except InterruptedError:
            continue
        if count <= 0:
            raise OSError("short write while preparing OCR result replacement")
        written += count


def _fsync_directory(descriptor: int) -> None:
    """Persist a replacement entry when the platform supports directory fsync."""

    try:
        os.fsync(descriptor)
    except OSError as exc:
        # Some supported filesystems reject directory fsync even though the
        # atomic rename itself succeeded; do not turn durable metadata into a
        # false review failure in that platform-specific case.
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EBADF}:
            raise


def _same_result_entry(parent_descriptor: int, path: Path, opened: os.stat_result) -> bool:
    """Return whether the directory entry still names the inspected result inode."""

    try:
        current = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(current.st_mode)
        and current.st_nlink == 1
        and current.st_dev == opened.st_dev
        and current.st_ino == opened.st_ino
    )


def _read_descriptor(descriptor: int, *, limit: int) -> bytes:
    """Read a bounded result payload from an already validated descriptor."""

    metadata = os.fstat(descriptor)
    if metadata.st_size > limit:
        raise OcrResultTooLarge(
            f"OCR result JSON is {metadata.st_size} bytes, above OCR_MAX_RESULT_BYTES={limit}"
        )
    os.lseek(descriptor, 0, os.SEEK_SET)
    data = os.read(descriptor, limit + 1)
    if len(data) > limit:
        raise OcrResultTooLarge(f"OCR result JSON grew above OCR_MAX_RESULT_BYTES={limit}")
    return data


def _decode_result(data: bytes) -> Any:
    """Decode one bounded UTF-8 JSON result payload."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OcrResultMalformed(str(exc)) from exc
    try:
        return json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise OcrResultMalformed(str(exc)) from exc


def load_ocr_result(path: Path) -> Any:
    """Load and sanitize one bounded OCR JSON result from disk."""

    descriptor = _open_result(path)
    try:
        try:
            return sanitize_ocr_value(
                _decode_result(_read_descriptor(descriptor, limit=max_result_bytes()))
            )
        except RecursionError as exc:
            raise OcrResultMalformed(str(exc)) from exc
    finally:
        os.close(descriptor)


def attach_toolkit_metadata(
    path: Path, metadata_factory: Callable[[dict[str, Any]], Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inspect one OCR result and attach toolkit metadata through the same descriptor.

    Existing toolkit metadata is rejected so provider-controlled output cannot
    impersonate the review-time receipt. The private result artifact is opened
    without following symlinks and restricted to its owner after the rewrite.
    """

    limit = max_result_bytes()
    parent_descriptor = _open_result_parent(path)
    descriptor = -1
    temporary_descriptor = -1
    temporary_name = ""
    try:
        descriptor = _open_result_at(parent_descriptor, path)
        opened = os.fstat(descriptor)
        result = _decode_result(_read_descriptor(descriptor, limit=limit))
        if not isinstance(result, dict):
            raise OcrResultMalformed("OCR result JSON must be an object")
        if TOOLKIT_RESULT_KEY in result:
            raise OcrResultMalformed(f"OCR result contains reserved field {TOOLKIT_RESULT_KEY!r}")
        metadata = dict(metadata_factory(result))
        # Schema ownership remains with the toolkit even if a future internal
        # producer accidentally returns a conflicting key.
        metadata["schema_version"] = TOOLKIT_RESULT_SCHEMA_VERSION
        result[TOOLKIT_RESULT_KEY] = metadata
        encoded = json.dumps(
            result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > limit:
            raise OcrResultTooLarge(
                f"OCR result JSON with toolkit metadata exceeds OCR_MAX_RESULT_BYTES={limit}"
            )
        temporary_descriptor, temporary_name = _create_private_temporary(parent_descriptor, path)
        try:
            _write_all(temporary_descriptor, encoded)
            os.fsync(temporary_descriptor)
        except OSError as exc:
            raise OcrResultMissing(
                f"could not write private OCR result replacement: {exc}"
            ) from exc
        finally:
            os.close(temporary_descriptor)
            temporary_descriptor = -1
        # Refuse to publish metadata onto a different result if another process
        # replaced the path while the original payload was being inspected.
        if not _same_result_entry(parent_descriptor, path, opened):
            raise OcrResultMissing("OCR result changed while toolkit metadata was prepared")
        try:
            os.replace(
                temporary_name,
                path.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
        except OSError as exc:
            raise OcrResultMissing(f"could not replace private OCR result: {exc}") from exc
        temporary_name = ""
        _fsync_directory(parent_descriptor)
        return result, metadata
    finally:
        if temporary_descriptor >= 0:
            os.close(temporary_descriptor)
        if temporary_name:
            try:
                os.unlink(temporary_name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)
