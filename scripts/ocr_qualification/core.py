"""Qualification data types, strict versions and atomic JSON documents."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from . import settings


class CompatibilityError(Exception):
    """OCR compatibility metadata or qualification failed closed."""


class QualificationStageError(CompatibilityError):
    """Carry one closed public qualification stage alongside private detail."""

    def __init__(self, message: str, *, phase: str, reason: str) -> None:
        super().__init__(message)
        self.phase = phase
        self.reason = reason


@dataclass(frozen=True)
class GroupingInventoryEntry:
    """One strictly parsed, qualification-only grouping inventory entry."""

    index: int
    status: str
    path: str
    insertions: int
    deletions: int


@dataclass(frozen=True)
class Asset:
    """One bounded upstream release asset."""

    name: str
    size: int
    sha256: str
    url: str


def _fail(message: str) -> NoReturn:
    raise CompatibilityError(message)


def _version(value: str) -> tuple[int, int, int]:
    match = settings.VERSION_RE.fullmatch(value)
    if match is None:
        _fail(f"invalid stable semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())


def _release_transition(
    previous: tuple[int, int, int], candidate: tuple[int, int, int]
) -> str | None:
    """Classify one adjacent SemVer transition accepted for reviewed promotion."""

    if candidate[:2] == previous[:2] and candidate[2] == previous[2] + 1:
        return "patch"
    if candidate[0] == previous[0] and candidate[1] == previous[1] + 1 and candidate[2] == 0:
        return "minor"
    if candidate[0] == previous[0] + 1 and candidate[1:] == (0, 0):
        return "major"
    return None


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def write_atomic_bytes(path: Path, payload: bytes, *, label: str) -> None:
    """Commit one output through a private same-directory temporary file."""

    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as output:
            written = output.write(payload)
            if written != len(payload):
                raise OSError("short output write")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
        if os.name != "nt":
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except OSError as exc:
        raise CompatibilityError(f"cannot write {label}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"cannot load JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"{path} must contain a JSON object")
    return value


def _qualification_stage(phase: str, reason: str, function: Callable[[], settings.T]) -> settings.T:
    """Run one private qualification stage and expose only its closed identity."""

    try:
        return function()
    except QualificationStageError:
        raise
    except CompatibilityError as exc:
        raise QualificationStageError(str(exc), phase=phase, reason=reason) from exc
    except Exception as exc:
        raise QualificationStageError(
            f"unexpected {type(exc).__name__}", phase=phase, reason="unexpected-error"
        ) from exc
