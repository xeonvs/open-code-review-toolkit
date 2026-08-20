"""Closed private transport for one identity-bound pre-execution outcome."""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

STATUS_SCHEMA = "ocr.pre-execution-status/v1"
PROTECTED_TARGET_RULE_PATH_PENDING = "protected_target_rule_path_pending"
MAX_STATUS_BYTES = 2_048
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class PreExecutionStatusError(ValueError):
    """The closed pre-execution status could not be trusted."""


@dataclass(frozen=True, slots=True)
class PreExecutionStatus:
    """Carry no display data, only one closed reason and immutable identities."""

    schema_version: str
    reason: str
    diff_base_sha: str
    source_sha: str
    policy_sha: str


def _sha(value: str) -> bool:
    return SHA_RE.fullmatch(value) is not None and not value.startswith("0" * 40)


def _validate(status: PreExecutionStatus) -> None:
    if (
        status.schema_version != STATUS_SCHEMA
        or status.reason != PROTECTED_TARGET_RULE_PATH_PENDING
        or any(
            not _sha(value)
            for value in (status.diff_base_sha, status.source_sha, status.policy_sha)
        )
    ):
        raise PreExecutionStatusError("pre-execution status fields are invalid")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreExecutionStatusError("pre-execution status contains a duplicate key")
        result[key] = value
    return result


def _safe_directory(path: Path) -> tuple[int, os.stat_result]:
    descriptor = -1
    try:
        metadata = path.lstat()
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise PreExecutionStatusError("pre-execution status directory is unsafe") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_dev != opened.st_dev
        or metadata.st_ino != opened.st_ino
        or stat.S_IMODE(opened.st_mode) & 0o077
    ):
        os.close(descriptor)
        raise PreExecutionStatusError("pre-execution status directory is unsafe")
    return descriptor, opened


def write_pre_execution_status(path: Path, status: PreExecutionStatus) -> None:
    """Atomically create an owner-only exact envelope without following links."""

    _validate(status)
    payload = (
        json.dumps(asdict(status), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("ascii")
    if len(payload) > MAX_STATUS_BYTES:
        raise PreExecutionStatusError("pre-execution status exceeds its byte limit")
    directory, _metadata = _safe_directory(path.parent)
    temporary = f".{path.name}.{secrets.token_hex(16)}"
    file_descriptor = -1
    try:
        try:
            existing = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and (
            not stat.S_ISREG(existing.st_mode)
            or existing.st_nlink != 1
            or stat.S_IMODE(existing.st_mode) & 0o077
        ):
            raise PreExecutionStatusError("existing pre-execution status is unsafe")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        file_descriptor = os.open(temporary, flags, 0o600, dir_fd=directory)
        os.fchmod(file_descriptor, 0o600)
        offset = 0
        while offset < len(payload):
            written = os.write(file_descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short pre-execution status write")
            offset += written
        os.fsync(file_descriptor)
        os.close(file_descriptor)
        file_descriptor = -1
        os.replace(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    except OSError as exc:
        raise PreExecutionStatusError("pre-execution status write failed") from exc
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)


def read_pre_execution_status(
    path: Path, *, expected_diff_base_sha: str, expected_source_sha: str
) -> PreExecutionStatus:
    """Hostile-read one status and bind it to current source/diff-base identities."""

    if not _sha(expected_diff_base_sha) or not _sha(expected_source_sha):
        raise PreExecutionStatusError("current pre-execution identity is invalid")
    directory, _metadata = _safe_directory(path.parent)
    descriptor = -1
    try:
        try:
            metadata = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        except OSError as exc:
            raise PreExecutionStatusError("pre-execution status is unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or not 0 < metadata.st_size <= MAX_STATUS_BYTES
        ):
            raise PreExecutionStatusError("pre-execution status metadata is unsafe")
        descriptor = os.open(
            path.name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory,
        )
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
        ):
            raise PreExecutionStatusError("pre-execution status changed during read")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise PreExecutionStatusError("pre-execution status is partial")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise PreExecutionStatusError("pre-execution status changed during read")
        raw = b"".join(chunks)
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise PreExecutionStatusError("pre-execution status is malformed") from exc
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "reason",
            "diff_base_sha",
            "source_sha",
            "policy_sha",
        }:
            raise PreExecutionStatusError("pre-execution status fields are invalid")
        if any(not isinstance(item, str) for item in value.values()):
            raise PreExecutionStatusError("pre-execution status fields are invalid")
        status = PreExecutionStatus(**value)
        _validate(status)
        if (
            status.diff_base_sha != expected_diff_base_sha
            or status.source_sha != expected_source_sha
        ):
            raise PreExecutionStatusError("pre-execution status identity does not match")
        return status
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(directory)
