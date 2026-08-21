"""Persist and validate count-only built-in evidence action attribution."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, flock
from pathlib import Path
from typing import Any

from ocr_toolkit.evidence.store.atomic import atomic_write

ACTION_RECEIPT_SCHEMA = "ocr.evidence-action-receipt/v1"
EVIDENCE_ACTIONS = ("summary", "list", "get")
MAX_ACTION_CALLS = 1_000_000_000
MAX_ACTION_RECEIPT_BYTES = 4_096


def _locked_receipt_path(path: Path) -> Path:
    """Return one sibling lock path that never enters the public receipt."""

    return path.with_name(f".{path.name}.lock")


@contextmanager
def _serialized_receipt_update(path: Path) -> Iterator[None]:
    """Serialize sibling receipt updates through one private regular lock file."""

    lock_path = _locked_receipt_path(path)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise OSError("evidence action receipt lock is unsafe")
        os.fchmod(descriptor, 0o600)
        flock(descriptor, LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _validated_counts(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict) or set(value) != {"schema_version", "actions"}:
        return None
    actions = value.get("actions")
    if value.get("schema_version") != ACTION_RECEIPT_SCHEMA or not isinstance(actions, dict):
        return None
    if set(actions) != set(EVIDENCE_ACTIONS):
        return None
    if any(
        not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= MAX_ACTION_CALLS
        for count in actions.values()
    ):
        return None
    return {action: actions[action] for action in EVIDENCE_ACTIONS}


def read_action_receipt(path: Path) -> dict[str, int] | None:
    """Read one bounded receipt or return unavailable for any unsafe shape."""

    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_ACTION_RECEIPT_BYTES + 1)
    except OSError:
        return None
    if len(raw) > MAX_ACTION_RECEIPT_BYTES:
        return None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return None
    return _validated_counts(value)


def record_action(path: Path, action: object) -> None:
    """Atomically increment one completed action without retaining arguments."""

    if action not in EVIDENCE_ACTIONS:
        raise ValueError("evidence action is outside the closed receipt enum")
    with _serialized_receipt_update(path):
        counts = read_action_receipt(path)
        if path.exists() and counts is None:
            raise ValueError("evidence action receipt is malformed")
        if counts is None:
            counts = dict.fromkeys(EVIDENCE_ACTIONS, 0)
        if counts[action] >= MAX_ACTION_CALLS:
            raise ValueError("evidence action receipt exceeds the count bound")
        counts[action] += 1
        payload = {
            "schema_version": ACTION_RECEIPT_SCHEMA,
            "actions": {name: counts[name] for name in EVIDENCE_ACTIONS},
        }
        atomic_write(
            path,
            lambda: json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        )
