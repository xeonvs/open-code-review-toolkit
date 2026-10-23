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

GitlinkChangeKind = Literal["added", "updated", "deleted", "transition"]
_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True)
class GitlinkChange:
    """Private tree evidence; paths and object IDs must not enter public receipts."""

    path: str
    kind: GitlinkChangeKind
    before_oid: str | None
    after_oid: str | None
    before_entry: RepositoryObject | None = None
    after_entry: RepositoryObject | None = None


@dataclass(frozen=True, slots=True)
class OrdinaryTreeChange:
    """One original non-gitlink tree delta, including changes OCR may exclude."""

    path: str
    before: RepositoryObject | None
    after: RepositoryObject | None


@dataclass(frozen=True, slots=True)
class GitlinkInputPlan:
    """Private immutable scope for one original commit range."""

    base_sha: str
    head_sha: str
    changes: tuple[GitlinkChange, ...]
    moves: tuple[tuple[str, str], ...]
    ordinary: tuple[OrdinaryTreeChange, ...]
    config_names: tuple[str, ...]
    before_gitmodules: tuple[tuple[str, str], ...]
    after_gitmodules: tuple[tuple[str, str], ...]

    @property
    def counts(self) -> dict[str, int]:
        moved_paths = {path for pair in self.moves for path in pair}
        return {
            "added": sum(
                change.kind == "added" and change.path not in moved_paths for change in self.changes
            ),
            "updated": sum(change.kind == "updated" for change in self.changes),
            "deleted": sum(
                change.kind == "deleted" and change.path not in moved_paths
                for change in self.changes
            ),
            "moved": len(self.moves),
        }


def _entries_by_path(entries: tuple[RepositoryObject, ...]) -> dict[str, RepositoryObject]:
    by_path: dict[str, RepositoryObject] = {}
    for entry in entries:
        if entry.path in by_path:
            raise RepositoryEvidenceError("Git tree contains a duplicate path")
        expected_type = {
            "100644": "blob",
            "100755": "blob",
            "120000": "blob",
            "160000": "commit",
        }.get(entry.mode)
        if expected_type != entry.object_type:
            raise RepositoryEvidenceError("Git tree contains an unsupported entry mode or type")
        by_path[entry.path] = entry
    return by_path


def _changes_from_maps(
    before: dict[str, RepositoryObject], after: dict[str, RepositoryObject]
) -> tuple[GitlinkChange, ...]:
    changes: list[GitlinkChange] = []
    for path in sorted(before.keys() | after.keys()):
        prior = before.get(path)
        current = after.get(path)
        prior_oid = prior.object_sha if prior is not None and prior.is_submodule else None
        current_oid = current.object_sha if current is not None and current.is_submodule else None
        if prior_oid == current_oid:
            continue
        kind: GitlinkChangeKind
        if prior is not None and current is not None and prior.is_submodule != current.is_submodule:
            kind = "transition"
        else:
            kind = "added" if prior_oid is None else "deleted" if current_oid is None else "updated"
        changes.append(GitlinkChange(path, kind, prior_oid, current_oid, prior, current))
    return tuple(changes)


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
    return _changes_from_maps(before, after)


def plan_gitlink_input(
    reader: GitRepositoryReader, base_sha: str, head_sha: str
) -> GitlinkInputPlan | None:
    """Qualify changed pure pointers and retain every ordinary original delta.

    No submodule target object is opened. Unsafe transitions and ambiguous move
    pairing fail before any OCR preview or model call can use the plan.
    """

    if _SHA_RE.fullmatch(base_sha) is None or _SHA_RE.fullmatch(head_sha) is None:
        raise RepositoryEvidenceError("gitlink planning requires immutable commit IDs")
    before = _entries_by_path(reader.list_objects(base_sha))
    after = _entries_by_path(reader.list_objects(head_sha))
    changes = _changes_from_maps(before, after)
    if not changes:
        return None
    for change in changes:
        if change.kind == "transition":
            raise RepositoryEvidenceError("gitlink type transition is unsupported")
        other_tree = before if change.kind == "added" else after if change.kind == "deleted" else {}
        if any(path.startswith(change.path + "/") for path in other_tree):
            raise RepositoryEvidenceError("gitlink directory transition is unsupported")

    additions: dict[str, list[str]] = {}
    deletions: dict[str, list[str]] = {}
    for change in changes:
        if change.kind == "added":
            assert change.after_oid is not None
            additions.setdefault(change.after_oid, []).append(change.path)
        elif change.kind == "deleted":
            assert change.before_oid is not None
            deletions.setdefault(change.before_oid, []).append(change.path)
    moves: list[tuple[str, str]] = []
    for oid in additions.keys() & deletions.keys():
        if len(additions[oid]) != 1 or len(deletions[oid]) != 1:
            raise RepositoryEvidenceError("gitlink move pairing is ambiguous")
        moves.append((deletions[oid][0], additions[oid][0]))

    before_modules = reader.gitmodules_paths(base_sha)
    after_modules = reader.gitmodules_paths(head_sha)
    changed_paths = {change.path for change in changes}
    names = {
        name
        for mapping in (before_modules, after_modules)
        for name, path in mapping.items()
        if path in changed_paths
    }
    ordinary = tuple(
        OrdinaryTreeChange(path, prior, current)
        for path in sorted(before.keys() | after.keys())
        if (prior := before.get(path)) != (current := after.get(path))
        and not (
            (prior is not None and prior.is_submodule)
            or (current is not None and current.is_submodule)
        )
    )
    return GitlinkInputPlan(
        base_sha,
        head_sha,
        changes,
        tuple(sorted(moves)),
        ordinary,
        tuple(sorted(names)),
        tuple(sorted(before_modules.items())),
        tuple(sorted(after_modules.items())),
    )
