"""Independent owner-only atomic context store and opaque handles."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ocr_toolkit.context.contracts import (
    PROJECTION_FIELDS,
    RESOURCE_CLASSES,
    RETENTION_FIELDS,
    STORE_SCHEMA,
)

MAX_STORE_BYTES = 4_000_000
MAX_STORE_RECORDS = 128
HANDLE_RE = re.compile(r"ctx1_[A-Za-z0-9_-]{43}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID_RE = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")


class ContextStoreError(ValueError):
    """The private context store failed closed validation."""


@dataclass(frozen=True, slots=True)
class PendingContextRecord:
    """Hold one fully normalized record before atomic admission."""

    source: str
    adapter: str
    tenant: str
    canonical_object: str
    resource_class: str
    descriptor: str
    projections: Mapping[str, Mapping[str, object]]
    version: str
    digest: str
    mutable: bool
    expiry: int


@dataclass(frozen=True, slots=True)
class ContextRecord:
    """Bind one admitted record to a private opaque handle."""

    handle: str
    source: str
    adapter: str
    tenant: str
    canonical_object: str
    resource_class: str
    descriptor: str
    projections: Mapping[str, Mapping[str, object]]
    version: str
    digest: str
    mutable: bool
    expiry: int


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextStoreError("context store contains a duplicate key")
        result[key] = value
    return result


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _mint(token_bytes: Callable[[int], bytes]) -> str:
    raw = token_bytes(32)
    if not isinstance(raw, bytes) or len(raw) != 32:
        raise ContextStoreError("context handle entropy source is invalid")
    return "ctx1_" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".context-store-", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContextStoreError(f"{label} must be an object")
    return value


def _read_safe(path: Path, metadata: os.stat_result) -> bytes:
    """Read the exact regular inode already checked by lstat, without following links."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or opened.st_size != metadata.st_size
        ):
            raise ContextStoreError("context store changed during read")
        chunks: list[bytes] = []
        remaining = metadata.st_size
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                raise ContextStoreError("context store was only partially readable")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise ContextStoreError("context store changed during read")
        return b"".join(chunks)
    except OSError as exc:
        raise ContextStoreError("context store read failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _record(value: object) -> ContextRecord:
    item = _mapping(value, "context record")
    exact = {
        "handle",
        "source",
        "adapter",
        "tenant",
        "canonical_object",
        "resource_class",
        "descriptor",
        "projections",
        "version",
        "digest",
        "mutable",
        "expiry",
    }
    if set(item) != exact:
        raise ContextStoreError("context record fields are invalid")
    handle = item.get("handle")
    strings = {
        name: item.get(name)
        for name in (
            "source",
            "adapter",
            "tenant",
            "canonical_object",
            "resource_class",
            "descriptor",
            "version",
            "digest",
        )
    }
    if not isinstance(handle, str) or HANDLE_RE.fullmatch(handle) is None:
        raise ContextStoreError("context handle is invalid")
    if any(
        not isinstance(value, str) or not value or len(value) > 512 for value in strings.values()
    ):
        raise ContextStoreError("context record identity is invalid")
    if strings["resource_class"] not in RESOURCE_CLASSES:
        raise ContextStoreError("context record resource class is invalid")
    if SHA256_RE.fullmatch(str(strings["digest"])) is None:
        raise ContextStoreError("context record digest is invalid")
    mutable, expiry = item.get("mutable"), item.get("expiry")
    if (
        not isinstance(mutable, bool)
        or not isinstance(expiry, int)
        or isinstance(expiry, bool)
        or expiry < 0
    ):
        raise ContextStoreError("context record state is invalid")
    projections = _mapping(item.get("projections"), "context projections")
    if set(projections) != {"model", "publish", "retain"}:
        raise ContextStoreError("context projection names are invalid")
    normalized_projections: dict[str, Mapping[str, object]] = {}
    for name, projection in projections.items():
        mapped = _mapping(projection, f"context {name} projection")
        allowed = RETENTION_FIELDS if name == "retain" else PROJECTION_FIELDS
        if len(mapped) > len(allowed) or not set(mapped).issubset(allowed):
            raise ContextStoreError("context projection fields are invalid")
        normalized_projections[name] = dict(mapped)
    return ContextRecord(
        handle=handle,
        projections=normalized_projections,
        mutable=mutable,
        expiry=expiry,
        **strings,  # type: ignore[arg-type]
    )


@dataclass(frozen=True, slots=True)
class ContextStore:
    """Expose validated local records without any provider transport."""

    run_id: str
    policy_digest: str
    created_at: int
    expiry: int
    completeness: Mapping[str, str]
    records: tuple[ContextRecord, ...]

    @classmethod
    def commit(
        cls,
        path: Path,
        *,
        run_id: str,
        policy_digest: str,
        completeness: Mapping[str, str],
        records: Sequence[PendingContextRecord],
        created_at: int,
        expiry: int,
        token_bytes: Callable[[int], bytes] = secrets.token_bytes,
    ) -> ContextStore:
        """Mint only in-memory candidates, atomically commit all, then hostile-read them."""

        if RUN_ID_RE.fullmatch(run_id) is None or SHA256_RE.fullmatch(policy_digest) is None:
            raise ContextStoreError("context store identity is invalid")
        if (
            not isinstance(created_at, int)
            or not isinstance(expiry, int)
            or isinstance(created_at, bool)
            or isinstance(expiry, bool)
            or created_at < 0
            or expiry <= created_at
            or len(records) > MAX_STORE_RECORDS
        ):
            raise ContextStoreError("context store lifetime or count is invalid")
        handles: set[str] = set()
        object_identities: set[tuple[str, str, str, str]] = set()
        serialized: list[dict[str, object]] = []
        for pending in records:
            if pending.expiry < created_at or pending.expiry > expiry:
                raise ContextStoreError("context record lifetime is invalid")
            identity = (
                pending.adapter,
                pending.tenant,
                pending.resource_class,
                pending.canonical_object,
            )
            if identity in object_identities:
                raise ContextStoreError("context records collide")
            object_identities.add(identity)
            handle = ""
            for _attempt in range(8):
                candidate = _mint(token_bytes)
                if candidate not in handles:
                    handle = candidate
                    handles.add(candidate)
                    break
            if not handle:
                raise ContextStoreError("context handle entropy collided repeatedly")
            value = {
                "handle": handle,
                "source": pending.source,
                "adapter": pending.adapter,
                "tenant": pending.tenant,
                "canonical_object": pending.canonical_object,
                "resource_class": pending.resource_class,
                "descriptor": pending.descriptor,
                "projections": {name: dict(value) for name, value in pending.projections.items()},
                "version": pending.version,
                "digest": pending.digest,
                "mutable": pending.mutable,
                "expiry": pending.expiry,
            }
            _record(value)
            serialized.append(value)
        body = {
            "schema_version": STORE_SCHEMA,
            "run_id": run_id,
            "policy_digest": policy_digest,
            "created_at": created_at,
            "expiry": expiry,
            "completeness": dict(sorted(completeness.items())),
            "records": serialized,
        }
        envelope = dict(body)
        envelope["digest"] = hashlib.sha256(_canonical(body)).hexdigest()
        payload = _canonical(envelope)
        if len(payload) > MAX_STORE_BYTES:
            raise ContextStoreError("context store exceeds its byte bound")
        try:
            _atomic_write(path, payload)
        except OSError as exc:
            raise ContextStoreError("context store atomic commit failed") from exc
        return cls.read(
            path,
            expected_run_id=run_id,
            expected_policy_digest=policy_digest,
            now=created_at,
        )

    @classmethod
    def read(
        cls,
        path: Path,
        *,
        expected_run_id: str,
        expected_policy_digest: str,
        now: int,
    ) -> ContextStore:
        """Treat the persisted owner-only artifact as hostile input."""

        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ContextStoreError("context store is unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or metadata.st_size <= 0
            or metadata.st_size > MAX_STORE_BYTES
        ):
            raise ContextStoreError("context store file metadata is unsafe")
        try:
            raw = _read_safe(path, metadata)
            payload = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContextStoreError("context store is malformed") from exc
        root = _mapping(payload, "context store")
        if set(root) != {
            "schema_version",
            "run_id",
            "policy_digest",
            "created_at",
            "expiry",
            "completeness",
            "records",
            "digest",
        }:
            raise ContextStoreError("context store fields are invalid")
        if root.get("schema_version") != STORE_SCHEMA:
            raise ContextStoreError("context store schema is unsupported")
        run_id, policy_digest = root.get("run_id"), root.get("policy_digest")
        if run_id != expected_run_id or policy_digest != expected_policy_digest:
            raise ContextStoreError("context store identity does not match this run")
        created_at, expiry = root.get("created_at"), root.get("expiry")
        if (
            not isinstance(created_at, int)
            or isinstance(created_at, bool)
            or not isinstance(expiry, int)
            or isinstance(expiry, bool)
            or created_at < 0
            or expiry <= created_at
            or now > expiry
        ):
            raise ContextStoreError("context store is expired or has an invalid lifetime")
        digest = root.get("digest")
        body = dict(root)
        body.pop("digest", None)
        if not isinstance(digest, str) or not secrets.compare_digest(
            digest, hashlib.sha256(_canonical(body)).hexdigest()
        ):
            raise ContextStoreError("context store digest does not match")
        completeness = _mapping(root.get("completeness"), "context completeness")
        if any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or value not in {"complete", "partial", "mutated", "unavailable"}
            for key, value in completeness.items()
        ):
            raise ContextStoreError("context completeness is invalid")
        values = root.get("records")
        if not isinstance(values, list) or len(values) > MAX_STORE_RECORDS:
            raise ContextStoreError("context store records are invalid")
        records = tuple(_record(value) for value in values)
        handles = [record.handle for record in records]
        if len(handles) != len(set(handles)):
            raise ContextStoreError("context store handles collide")
        return cls(
            run_id=expected_run_id,
            policy_digest=expected_policy_digest,
            created_at=created_at,
            expiry=expiry,
            completeness=dict(completeness),
            records=records,
        )

    def get(self, handle: str, *, run_id: str, policy_digest: str, now: int) -> ContextRecord:
        """Resolve one exact minted handle only within its bound run and lifetime."""

        if (
            HANDLE_RE.fullmatch(handle) is None
            or run_id != self.run_id
            or policy_digest != self.policy_digest
            or now > self.expiry
        ):
            raise ContextStoreError("context handle is unavailable")
        record = next((record for record in self.records if record.handle == handle), None)
        if record is None or now > record.expiry:
            raise ContextStoreError("context handle is unavailable")
        return record
