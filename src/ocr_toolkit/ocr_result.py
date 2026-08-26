"""Own bounded OCR result loading and toolkit-authored result metadata."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ocr_toolkit.common.filesystem import fsync_directory
from ocr_toolkit.common.redaction import sanitize_ocr_value

DEFAULT_MAX_RESULT_BYTES = 2_000_000
MAX_RESULT_BYTES_HARD_LIMIT = 20_000_000
TOOLKIT_RESULT_KEY = "_ocr_toolkit"
TOOLKIT_RESULT_SCHEMA_VERSION = 5
SUPPORTED_TOOLKIT_RESULT_SCHEMA_VERSIONS = frozenset({TOOLKIT_RESULT_SCHEMA_VERSION})
TOOLKIT_ADVISORY_KEY = "_ocr_toolkit_advisory"
TOOLKIT_ADVISORY_SCHEMA_VERSION = "ocr.toolkit-advisory/v1"
TOOLKIT_ADVISORY_KIND = "background_recommended_limit"
TOOLKIT_ADVISORY_UNIT = "characters"
MAX_TOOLKIT_ADVISORY_VALUE = 999_999_999_999
# The receipt can name the 16 configured external servers plus the mandatory built-in.
MAX_TOOLKIT_MCP_USAGE_SERVERS = 17
MAX_TOOLKIT_MCP_TOOLS_PER_SERVER = 128
MAX_TOOLKIT_MCP_TOOL_NAME_CHARS = 4_096
MAX_TOOLKIT_MCP_USAGE_COUNT = 1_000_000_000
TOOLKIT_MCP_SERVER_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Closed names whose numeric call counts may appear in the public review summary.
# Dynamic external MCP tools remain represented by the receipt's verified
# per-server aggregate so provider-controlled names do not cross into GitLab.
PUBLIC_REVIEW_TOOL_CALL_NAMES = frozenset(
    {
        "code_comment",
        "code_search",
        "context_get",
        "context_list",
        "file_find",
        "file_read",
        "file_read_diff",
        "ocr_toolkit_evidence",
        "task_done",
    }
)


class OcrResultMissing(Exception):
    """The OCR result artifact is missing or unreadable on disk."""


class OcrResultMalformed(Exception):
    """The OCR result artifact exists but is not valid JSON."""


class OcrResultTooLarge(Exception):
    """The OCR result artifact exceeds the configured safety limit."""


@dataclass(frozen=True, slots=True)
class OcrToolkitAdvisory:
    """Carry one validated toolkit-authored numeric OCR advisory."""

    actual: int
    recommended: int


def parse_toolkit_advisory(value: Any) -> OcrToolkitAdvisory:
    """Parse the exact private toolkit advisory without accepting extensions."""

    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "kind",
        "actual",
        "recommended",
        "unit",
    }:
        raise OcrResultMalformed("OCR toolkit advisory has an unsupported schema")
    actual = value.get("actual")
    recommended = value.get("recommended")
    if (
        value.get("schema_version") != TOOLKIT_ADVISORY_SCHEMA_VERSION
        or value.get("kind") != TOOLKIT_ADVISORY_KIND
        or value.get("unit") != TOOLKIT_ADVISORY_UNIT
        or not isinstance(actual, int)
        or isinstance(actual, bool)
        or not isinstance(recommended, int)
        or isinstance(recommended, bool)
        or not 0 < recommended < actual <= MAX_TOOLKIT_ADVISORY_VALUE
    ):
        raise OcrResultMalformed("OCR toolkit advisory has invalid closed values")
    return OcrToolkitAdvisory(actual=actual, recommended=recommended)


def background_recommended_advisory(*, actual: int, recommended: int) -> OcrToolkitAdvisory:
    """Construct one validated background recommendation advisory."""

    return parse_toolkit_advisory(
        {
            "schema_version": TOOLKIT_ADVISORY_SCHEMA_VERSION,
            "kind": TOOLKIT_ADVISORY_KIND,
            "actual": actual,
            "recommended": recommended,
            "unit": TOOLKIT_ADVISORY_UNIT,
        }
    )


def toolkit_advisory_payload(advisory: OcrToolkitAdvisory) -> dict[str, object]:
    """Serialize a validated advisory into its exact private result shape."""

    payload: dict[str, object] = {
        "schema_version": TOOLKIT_ADVISORY_SCHEMA_VERSION,
        "kind": TOOLKIT_ADVISORY_KIND,
        "actual": advisory.actual,
        "recommended": advisory.recommended,
        "unit": TOOLKIT_ADVISORY_UNIT,
    }
    parse_toolkit_advisory(payload)
    return payload


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
    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
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

        def reject_duplicate_advisory(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key == TOOLKIT_ADVISORY_KEY and key in result:
                    raise OcrResultMalformed("OCR result repeats the reserved toolkit advisory")
                result[key] = value
            return result

        return json.loads(text, object_pairs_hook=reject_duplicate_advisory)
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


def inspect_ocr_result(path: Path) -> Any:
    """Load bounded raw OCR JSON for a pre-publication policy owner."""

    descriptor = _open_result(path)
    try:
        return _decode_result(_read_descriptor(descriptor, limit=max_result_bytes()))
    finally:
        os.close(descriptor)


def transform_ocr_result(
    path: Path, transformer: Callable[[dict[str, Any]], Mapping[str, Any]]
) -> dict[str, Any]:
    """Atomically replace one hostile OCR result with a validated transformation.

    The transformer observes the same inode that is replaced. This lets policy
    owners inspect, project, and attach metadata without a check/use gap in
    which another process could swap an unchecked result into the publication
    path.
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
        try:
            transformed = dict(transformer(result))
        except RecursionError as exc:
            raise OcrResultMalformed(str(exc)) from exc
        encoded = json.dumps(
            transformed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > limit:
            raise OcrResultTooLarge(
                f"transformed OCR result JSON exceeds OCR_MAX_RESULT_BYTES={limit}"
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
        if not _same_result_entry(parent_descriptor, path, opened):
            raise OcrResultMissing("OCR result changed while toolkit policy was applied")
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
        fsync_directory(parent_descriptor)
        return transformed
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


def attach_toolkit_metadata(
    path: Path, metadata_factory: Callable[[dict[str, Any]], Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inspect one OCR result and attach toolkit metadata through the same descriptor.

    Existing toolkit metadata is rejected so provider-controlled output cannot
    impersonate the review-time receipt. The private result artifact is opened
    without following symlinks and restricted to its owner after the rewrite.
    """

    metadata: dict[str, Any] = {}

    def attach(result: dict[str, Any]) -> dict[str, Any]:
        if TOOLKIT_RESULT_KEY in result:
            raise OcrResultMalformed(f"OCR result contains reserved field {TOOLKIT_RESULT_KEY!r}")
        metadata.update(metadata_factory(result))
        # Schema ownership remains with the toolkit even if a future internal
        # producer accidentally returns a conflicting key.
        metadata["schema_version"] = TOOLKIT_RESULT_SCHEMA_VERSION
        return {**result, TOOLKIT_RESULT_KEY: metadata}

    transformed = transform_ocr_result(path, attach)
    return transformed, metadata
