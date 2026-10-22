"""Identify changed Git submodule pointers from immutable tree objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryObject,
)

GitlinkChangeKind = Literal["added", "updated", "deleted"]
_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True)
class GitlinkChange:
    """Private tree evidence; paths and object IDs must not enter public receipts."""

    path: str
    kind: GitlinkChangeKind
    before_oid: str | None
    after_oid: str | None


def _entries_by_path(entries: tuple[RepositoryObject, ...]) -> dict[str, RepositoryObject]:
    by_path: dict[str, RepositoryObject] = {}
    for entry in entries:
        if entry.path in by_path:
            raise RepositoryEvidenceError("Git tree contains a duplicate path")
        if (entry.mode == "160000") != (entry.object_type == "commit"):
            raise RepositoryEvidenceError("Git tree contains an invalid gitlink entry")
        by_path[entry.path] = entry
    return by_path


def changed_gitlinks(
    reader: GitRepositoryReader, base_sha: str, head_sha: str
) -> tuple[GitlinkChange, ...]:
    """Return changed mode-160000 entries without reading or following their targets.

    Both inputs must be full immutable commit IDs. The reader's bounded, isolated
    ``ls-tree -z`` path is the only source of evidence. A gitlink target object
    need not exist in the parent repository, so it is never looked up here.
    """

    if _SHA_RE.fullmatch(base_sha) is None or _SHA_RE.fullmatch(head_sha) is None:
        raise RepositoryEvidenceError("gitlink inspection requires immutable commit IDs")
    before = _entries_by_path(reader.list_objects(base_sha))
    after = _entries_by_path(reader.list_objects(head_sha))
    changes: list[GitlinkChange] = []
    for path in sorted(before.keys() | after.keys()):
        prior = before.get(path)
        current = after.get(path)
        prior_oid = prior.object_sha if prior is not None and prior.is_submodule else None
        current_oid = current.object_sha if current is not None and current.is_submodule else None
        if prior_oid == current_oid:
            continue
        kind: GitlinkChangeKind = (
            "added" if prior_oid is None else "deleted" if current_oid is None else "updated"
        )
        changes.append(GitlinkChange(path, kind, prior_oid, current_oid))
    return tuple(changes)
