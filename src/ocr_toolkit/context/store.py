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
    ACCOUNT_CLASSES,
    CI_OUTCOME_MODEL_FIELD,
    REMEDIATION_MODEL_FIELD,
    RETENTION_FIELDS,
    STORE_PROJECTION_FIELDS,
    STORE_RESOURCE_CLASSES,
    STORE_SCHEMA,
    TextBudgets,
)
from ocr_toolkit.context.dlp import check_text, normalize_text
from ocr_toolkit.context.policy import normalize_ci_path_prefix

MAX_STORE_BYTES = 4_000_000
MAX_STORE_RECORDS = 128
MAX_STORE_LIFETIME_SECONDS = 86_400
HANDLE_RE = re.compile(r"ctx1_[A-Za-z0-9_-]{43}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID_RE = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")
STATE_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
PSEUDONYM_RE = re.compile(r"actor-[0-9a-f]{16}\Z")
STORE_TEXT_BUDGETS = TextBudgets(
    max_chars=2_000_000,
    max_bytes=MAX_STORE_BYTES,
    max_lines=100_000,
)
REMEDIATION_ANCHOR_STATES = frozenset({"current", "outdated", "unpositioned"})
REMEDIATION_COMPLETENESS = frozenset({"complete", "partial"})
MAX_REMEDIATION_REPLIES = 100
CI_OUTCOME_STATUSES = frozenset({"passed", "failed", "skipped", "canceled", "unknown"})
CI_OUTCOME_REQUIREMENTS = frozenset({"required", "advisory"})
CI_OUTCOME_ORIGINS = frozenset({"current_pipeline", "same_revision_pipeline"})


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
            descriptor = -1
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
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContextStoreError(f"{label} must be an object")
    return value


def _bounded_projection_integer(value: object, *, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise ContextStoreError("remediation projection integer is invalid")
    return value


def _remediation_text(value: object) -> str:
    checked = check_text(value, budgets=STORE_TEXT_BUDGETS)
    if not checked.admitted or not isinstance(checked.text, str) or checked.text != value:
        raise ContextStoreError("remediation projection text is invalid")
    return checked.text


def _remediation_actor(value: object) -> str:
    normalized = normalize_text(value)
    if (
        not isinstance(normalized, str)
        or normalized != value
        or PSEUDONYM_RE.fullmatch(normalized) is None
    ):
        raise ContextStoreError("remediation projection actor is invalid")
    return normalized


def _remediation_projection(value: object) -> Mapping[str, object]:
    """Hostile-read the fixed model-only remediation-thread projection."""

    item = _mapping(value, "remediation projection")
    if set(item) != {"root", "anchor_state", "replies", "completeness", "counts"}:
        raise ContextStoreError("remediation projection fields are invalid")
    root = _mapping(item.get("root"), "remediation root")
    if set(root) != {"text", "author_pseudonym"}:
        raise ContextStoreError("remediation root fields are invalid")
    normalized_root = {
        "text": _remediation_text(root.get("text")),
        "author_pseudonym": _remediation_actor(root.get("author_pseudonym")),
    }
    anchor_state = normalize_text(item.get("anchor_state"))
    if anchor_state != item.get("anchor_state") or anchor_state not in REMEDIATION_ANCHOR_STATES:
        raise ContextStoreError("remediation anchor state is invalid")
    completeness = normalize_text(item.get("completeness"))
    if completeness != item.get("completeness") or completeness not in REMEDIATION_COMPLETENESS:
        raise ContextStoreError("remediation completeness is invalid")
    replies = item.get("replies")
    if not isinstance(replies, list) or not 1 <= len(replies) <= MAX_REMEDIATION_REPLIES:
        raise ContextStoreError("remediation replies are invalid")
    normalized_replies: list[dict[str, object]] = []
    previous_order = -1
    for reply_value in replies:
        reply = _mapping(reply_value, "remediation reply")
        if set(reply) != {
            "order",
            "author_class",
            "author_pseudonym",
            "text",
            "created_at",
            "updated_at",
        }:
            raise ContextStoreError("remediation reply fields are invalid")
        order = _bounded_projection_integer(reply.get("order"), maximum=MAX_REMEDIATION_REPLIES)
        author_class = normalize_text(reply.get("author_class"))
        created_at = _bounded_projection_integer(reply.get("created_at"), maximum=2**63 - 1)
        updated_at = _bounded_projection_integer(reply.get("updated_at"), maximum=2**63 - 1)
        if (
            order != previous_order + 1
            or author_class != reply.get("author_class")
            or author_class not in ACCOUNT_CLASSES.difference({"toolkit_bot"})
            or updated_at < created_at
        ):
            raise ContextStoreError("remediation reply identity or order is invalid")
        previous_order = order
        normalized_replies.append(
            {
                "order": order,
                "author_class": author_class,
                "author_pseudonym": _remediation_actor(reply.get("author_pseudonym")),
                "text": _remediation_text(reply.get("text")),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    counts = _mapping(item.get("counts"), "remediation counts")
    if set(counts) != {"replies", "resolved", "outdated"}:
        raise ContextStoreError("remediation count fields are invalid")
    normalized_counts = {
        "replies": _bounded_projection_integer(
            counts.get("replies"), maximum=MAX_REMEDIATION_REPLIES
        ),
        "resolved": _bounded_projection_integer(
            counts.get("resolved"), maximum=MAX_REMEDIATION_REPLIES + 1
        ),
        "outdated": _bounded_projection_integer(
            counts.get("outdated"), maximum=MAX_REMEDIATION_REPLIES + 1
        ),
    }
    maximum_note_count = len(normalized_replies) + 1
    if (
        normalized_counts["replies"] != len(normalized_replies)
        or normalized_counts["resolved"] > maximum_note_count
        or normalized_counts["outdated"] > maximum_note_count
    ):
        raise ContextStoreError("remediation reply count is inconsistent")
    if anchor_state == "outdated" and normalized_counts["outdated"] < 1:
        raise ContextStoreError("remediation outdated count is inconsistent")
    return {
        "root": normalized_root,
        "anchor_state": anchor_state,
        "replies": normalized_replies,
        "completeness": completeness,
        "counts": normalized_counts,
    }


def _ci_outcome_projection(value: object) -> Mapping[str, object]:
    """Hostile-read the fixed model-only same-revision CI projection."""

    item = _mapping(value, "CI outcome projection")
    if set(item) != {
        "check",
        "revision",
        "status",
        "requirement",
        "scope",
        "origin",
        "completed_at",
    }:
        raise ContextStoreError("CI outcome projection fields are invalid")
    check = normalize_text(item.get("check"))
    if (
        check != item.get("check")
        or not isinstance(check, str)
        or not 1 <= len(check) <= 128
        or not check_text(check, budgets=TextBudgets(128, 512, 1)).admitted
    ):
        raise ContextStoreError("CI outcome check is invalid")
    if item.get("revision") != "reviewed_head":
        raise ContextStoreError("CI outcome revision is invalid")
    status = item.get("status")
    requirement = item.get("requirement")
    origin = item.get("origin")
    if (
        status not in CI_OUTCOME_STATUSES
        or requirement not in CI_OUTCOME_REQUIREMENTS
        or origin not in CI_OUTCOME_ORIGINS
    ):
        raise ContextStoreError("CI outcome state is invalid")
    completed_at = item.get("completed_at")
    if not isinstance(completed_at, int) or isinstance(completed_at, bool) or completed_at < 0:
        raise ContextStoreError("CI outcome completion time is invalid")
    scope = _mapping(item.get("scope"), "CI outcome scope")
    if set(scope) != {"mode", "path_prefixes"} or scope.get("mode") != "declared":
        raise ContextStoreError("CI outcome scope is invalid")
    prefixes = scope.get("path_prefixes")
    if not isinstance(prefixes, list) or not prefixes or len(prefixes) > 32:
        raise ContextStoreError("CI outcome path prefixes are invalid")
    normalized: list[str] = []
    for prefix in prefixes:
        value = normalize_text(prefix)
        try:
            canonical = normalize_ci_path_prefix(value)
        except (ContextStoreError, ValueError):
            raise ContextStoreError("CI outcome path prefix is invalid") from None
        if (
            canonical != prefix
            or not check_text(canonical, budgets=TextBudgets(256, 1_024, 1)).admitted
        ):
            raise ContextStoreError("CI outcome path prefix is invalid")
        normalized.append(canonical)
    if normalized != sorted(set(normalized)):
        raise ContextStoreError("CI outcome path prefixes are not canonical")
    return {
        "check": check,
        "revision": "reviewed_head",
        "status": status,
        "requirement": requirement,
        "scope": {"mode": "declared", "path_prefixes": normalized},
        "origin": origin,
        "completed_at": completed_at,
    }


def _projection_value(field: str, value: object) -> object:
    """Hostile-read one generic projection value without policy reinterpretation."""

    if field == REMEDIATION_MODEL_FIELD:
        return _remediation_projection(value)
    if field == CI_OUTCOME_MODEL_FIELD:
        return _ci_outcome_projection(value)
    if field == "text":
        checked = check_text(value, budgets=STORE_TEXT_BUDGETS)
        if not checked.admitted or checked.text != value:
            raise ContextStoreError("context projection text is invalid")
        return value
    if field in {"descriptor", "state", "author_class", "author_pseudonym", "version"}:
        normalized = normalize_text(value)
        if normalized != value or not normalized or len(normalized) > 512:
            raise ContextStoreError("context projection string is invalid")
        if field == "descriptor" and normalized not in {"discussion", *STORE_RESOURCE_CLASSES}:
            raise ContextStoreError("context projection descriptor is invalid")
        if field == "state" and STATE_RE.fullmatch(normalized) is None:
            raise ContextStoreError("context projection state is invalid")
        if field == "author_class" and normalized not in ACCOUNT_CLASSES:
            raise ContextStoreError("context projection author class is invalid")
        if field == "author_pseudonym" and PSEUDONYM_RE.fullmatch(normalized) is None:
            raise ContextStoreError("context projection author pseudonym is invalid")
        return normalized
    if field in {"resolved", "outdated"}:
        if not isinstance(value, bool):
            raise ContextStoreError("context projection boolean is invalid")
        return value
    if field in {"created_at", "updated_at", "count", "expiry"}:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or (field == "count" and value > 1_000_000_000)
        ):
            raise ContextStoreError("context projection integer is invalid")
        return value
    if field == "digest":
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise ContextStoreError("context projection digest is invalid")
        return value
    if field == "anchor":
        anchor = _mapping(value, "context projection anchor")
        if set(anchor).difference({"path", "line"}):
            raise ContextStoreError("context projection anchor is invalid")
        normalized_anchor: dict[str, object] = {}
        if "path" in anchor:
            path = normalize_text(anchor["path"])
            if (
                path != anchor["path"]
                or not path
                or len(path) > 512
                or len(path.encode("utf-8")) > 2_048
            ):
                raise ContextStoreError("context projection anchor path is invalid")
            normalized_anchor["path"] = path
        if "line" in anchor:
            line = anchor["line"]
            if not isinstance(line, int) or isinstance(line, bool) or not 0 < line <= 10_000_000:
                raise ContextStoreError("context projection anchor line is invalid")
            normalized_anchor["line"] = line
        return normalized_anchor
    raise ContextStoreError("context projection field is invalid")


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
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or normalize_text(value) != value
        for value in strings.values()
    ):
        raise ContextStoreError("context record identity is invalid")
    if strings["resource_class"] not in STORE_RESOURCE_CLASSES:
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
        allowed = RETENTION_FIELDS if name == "retain" else STORE_PROJECTION_FIELDS
        if len(mapped) > len(allowed) or not set(mapped).issubset(allowed):
            raise ContextStoreError("context projection fields are invalid")
        normalized_projections[name] = {
            field: _projection_value(field, value) for field, value in mapped.items()
        }
    remediation_model = REMEDIATION_MODEL_FIELD in normalized_projections["model"]
    ci_outcome_model = CI_OUTCOME_MODEL_FIELD in normalized_projections["model"]
    if (
        REMEDIATION_MODEL_FIELD in normalized_projections["publish"]
        or REMEDIATION_MODEL_FIELD in normalized_projections["retain"]
        or (
            strings["resource_class"] == "remediation_thread"
            and (
                strings["descriptor"] != "remediation_thread"
                or not remediation_model
                or set(normalized_projections["model"]) != {"descriptor", REMEDIATION_MODEL_FIELD}
            )
        )
        or (strings["resource_class"] != "remediation_thread" and remediation_model)
        or CI_OUTCOME_MODEL_FIELD in normalized_projections["publish"]
        or CI_OUTCOME_MODEL_FIELD in normalized_projections["retain"]
        or (
            strings["resource_class"] == "ci_outcome"
            and (
                strings["descriptor"] != "ci_outcome"
                or not ci_outcome_model
                or set(normalized_projections["model"]) != {"descriptor", CI_OUTCOME_MODEL_FIELD}
                or mutable is not False
                or normalized_projections["model"][CI_OUTCOME_MODEL_FIELD]["completed_at"] > expiry
                or strings["version"]
                != str(normalized_projections["model"][CI_OUTCOME_MODEL_FIELD]["completed_at"])
            )
        )
        or (strings["resource_class"] != "ci_outcome" and ci_outcome_model)
    ):
        raise ContextStoreError("special context projection placement is invalid")
    for projection in normalized_projections.values():
        if (
            ("descriptor" in projection and projection["descriptor"] != strings["descriptor"])
            or ("version" in projection and projection["version"] != strings["version"])
            or ("digest" in projection and projection["digest"] != strings["digest"])
            or ("expiry" in projection and projection["expiry"] != expiry)
            or (
                "created_at" in projection
                and "updated_at" in projection
                and projection["created_at"] > projection["updated_at"]  # type: ignore[operator]
            )
            or (
                "created_at" in projection and projection["created_at"] > expiry  # type: ignore[operator]
            )
            or (
                "updated_at" in projection and projection["updated_at"] > expiry  # type: ignore[operator]
            )
        ):
            raise ContextStoreError("context projection identity is inconsistent")
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
            or expiry - created_at > MAX_STORE_LIFETIME_SECONDS
            or len(records) > MAX_STORE_RECORDS
        ):
            raise ContextStoreError("context store lifetime or count is invalid")
        handles: set[str] = set()
        object_identities: set[tuple[str, str, str, str]] = set()
        serialized: list[dict[str, object]] = []
        for pending in records:
            if pending.expiry <= created_at or pending.expiry > expiry:
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
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
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
            or expiry - created_at > MAX_STORE_LIFETIME_SECONDS
            or now >= expiry
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
        if any(record.expiry <= created_at or record.expiry > expiry for record in records):
            raise ContextStoreError("context record lifetime is invalid")
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
            or now >= self.expiry
        ):
            raise ContextStoreError("context handle is unavailable")
        record = next((record for record in self.records if record.handle == handle), None)
        if record is None or now >= record.expiry:
            raise ContextStoreError("context handle is unavailable")
        return record
