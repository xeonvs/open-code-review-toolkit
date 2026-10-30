"""Descriptor-pinned private state and authenticated, bounded audit documents."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

from ocr_toolkit.common.filesystem import fsync_directory, open_private_parent_directory

MAX_DOCUMENT = 32_000_000
ID = re.compile(r"[a-f0-9]{32}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")


class AuditError(ValueError):
    """Carry a fixed, source-free diagnostic rather than an input exception."""


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys at every level."""

    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise AuditError("duplicate document key")
        result[key] = value
    return result


def decode(raw: bytes) -> Any:
    """Load bounded JSON without accepting NaN or exposing rejected content."""

    if len(raw) > MAX_DOCUMENT:
        raise AuditError("document limit exceeded")
    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(AuditError("invalid number")),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AuditError("invalid audit document") from exc


def encode(value: Any) -> bytes:
    """Produce a single canonical byte representation for HMAC and storage."""

    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def fields(value: Any, names: set[str]) -> dict[str, Any]:
    """Require a closed object before consuming authenticated state."""

    if not isinstance(value, dict) or set(value) != names:
        raise AuditError("invalid document fields")
    return value


def identifier(value: str) -> str:
    """Accept only generated slot names, never a path supplied by a document."""

    if not isinstance(value, str) or ID.fullmatch(value) is None:
        raise AuditError("invalid audit identity")
    return value


def read_regular(descriptor: int, name: str, limit: int) -> bytes:
    """Read a pinned owned regular file, rejecting links and concurrent changes."""

    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_size > limit
        ):
            raise AuditError("unsafe private file")
        raw = bytearray()
        while len(raw) <= limit:
            part = os.read(fd, min(65536, limit + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
        after = os.fstat(fd)
        if len(raw) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise AuditError("private file changed or exceeded limit")
        return bytes(raw)
    finally:
        os.close(fd)


class State:
    """Own a private directory lock and only generated, authenticated children."""

    def __init__(self, path: Path, *, create: bool = False) -> None:
        """Pin every ancestor and reject state inside a Git worktree."""

        self.path = path.absolute()
        if ".." in self.path.parts:
            raise AuditError("state path must be normalized")
        for parent in (self.path, *self.path.parents):
            if os.path.lexists(parent / ".git"):
                raise AuditError("audit state must be outside Git worktrees")
        parent_fd, name = open_private_parent_directory(self.path, create=create)
        try:
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=parent_fd)
                except FileExistsError:
                    pass
            self.fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
        self.lock_fd = -1
        try:
            info = os.fstat(self.fd)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise AuditError("state directory must be private and owned")
            self.lock_fd = os.open(
                "lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self.fd,
            )
            info = os.fstat(self.lock_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise AuditError("unsafe state lock")
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AuditError("audit state is busy") from exc
            if create and not os.listdir(self.fd) == ["lock"] and "key" not in os.listdir(self.fd):
                raise AuditError("state directory is not empty")
            if create and "key" not in os.listdir(self.fd):
                self._write("key", os.urandom(32), replace=False)
            self.key = read_regular(self.fd, "key", 32)
            if len(self.key) != 32:
                raise AuditError("invalid state key")
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> State:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        """Release only this operation's pinned descriptors."""

        if self.lock_fd >= 0:
            os.close(self.lock_fd)
            self.lock_fd = -1
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def mac(self, *parts: object) -> str:
        """Bind exact private identities without storing a raw secret or value."""

        return hmac.new(self.key, encode(parts), hashlib.sha256).hexdigest()

    def _write(self, name: str, raw: bytes, *, replace: bool = True) -> None:
        """Publish bytes atomically through the pinned directory."""

        temporary = "tmp-" + uuid.uuid4().hex
        fd = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if replace:
                os.replace(temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
            else:
                # Link publication is exclusive; unlink its temporary second name immediately.
                os.link(
                    temporary, name, src_dir_fd=self.fd, dst_dir_fd=self.fd, follow_symlinks=False
                )
                os.unlink(temporary, dir_fd=self.fd)
            fsync_directory(self.fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.fd)
            except FileNotFoundError:
                pass

    def save(self, kind: str, identity: str, payload: dict[str, Any]) -> None:
        """Authenticate one closed owner document; names never come from its body."""

        if kind not in {"corpus", "run", "expectations"}:
            raise AuditError("invalid document kind")
        identifier(identity)
        body = {"schema": "ocr.dlp-audit/1", "kind": kind, "id": identity, "payload": payload}
        raw = encode({**body, "mac": self.mac(body)})
        if len(raw) > MAX_DOCUMENT:
            raise AuditError("document limit exceeded")
        self._write(f"{kind}-{identity}.json", raw)

    def load(self, kind: str, identity: str) -> dict[str, Any]:
        """Revalidate envelope, identity and integrity before a consumer schema."""

        if kind not in {"corpus", "run", "expectations"}:
            raise AuditError("invalid document kind")
        identifier(identity)
        body = fields(
            decode(read_regular(self.fd, f"{kind}-{identity}.json", MAX_DOCUMENT)),
            {"schema", "kind", "id", "payload", "mac"},
        )
        signature = body.pop("mac")
        if (
            body["schema"] != "ocr.dlp-audit/1"
            or body["kind"] != kind
            or body["id"] != identity
            or not isinstance(signature, str)
            or not hmac.compare_digest(signature, self.mac(body))
            or not isinstance(body["payload"], dict)
        ):
            raise AuditError("invalid authenticated state")
        return body["payload"]

    def raw_directory(self, identity: str, *, create: bool = False) -> int:
        """Open one owned raw slot; creation is recoverable before any source write."""

        identifier(identity)
        name = "raw-" + identity
        if create:
            os.mkdir(name, mode=0o700, dir_fd=self.fd)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            os.close(fd)
            raise AuditError("unsafe raw directory")
        return fd

    def markdown(self, identity: str, text: str) -> None:
        """Store a private source-free human report beside its signed JSON owner."""

        self._write(f"run-{identifier(identity)}.md", text.encode())
