"""Read immutable repository refs and derive bounded evidence snapshots."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    RefRole,
    TrustClass,
)

OBJECT_LINE_RE = re.compile(
    r"^(?P<mode>[0-7]{6}) (?P<type>blob|tree|commit) (?P<sha>[0-9a-f]{40})\t(?P<path>.+)$"
)


class RepositoryEvidenceError(ValueError):
    """Report an invalid ref, path, object type, or bounded Git read."""


@dataclass(frozen=True, slots=True)
class RepositoryObject:
    """Describe one immutable Git tree entry without checking it out."""

    path: str
    mode: str
    object_type: str
    object_sha: str

    @property
    def is_symlink(self) -> bool:
        """Return whether this entry stores a symbolic-link target."""

        return self.mode == "120000"

    @property
    def is_submodule(self) -> bool:
        """Return whether this entry is a submodule commit pointer."""

        return self.mode == "160000" or self.object_type == "commit"


def normalize_repo_path(value: str) -> str:
    """Return one safe repository-relative path accepted by Git plumbing."""

    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise RepositoryEvidenceError("repository path must be normalized and relative")
    normalized = PurePosixPath(value).as_posix()
    if normalized.startswith("-") or "\x00" in normalized or "\n" in normalized:
        raise RepositoryEvidenceError("repository path contains unsupported control syntax")
    return normalized


class GitRepositoryReader:
    """Provide bounded read-only Git plumbing for one trusted repository root."""

    def __init__(self, root: Path, *, max_file_bytes: int = 256_000) -> None:
        """Resolve the repository root and constrain every subsequent Git command."""

        resolved = root.resolve(strict=True)
        probe = self._run_at(resolved, ["rev-parse", "--show-toplevel"])
        if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != resolved:
            raise RepositoryEvidenceError("root is not a Git repository top level")
        self.root = resolved
        if not 1 <= max_file_bytes <= 5_000_000:
            raise RepositoryEvidenceError("max_file_bytes must be between 1 and 5000000")
        self.max_file_bytes = max_file_bytes

    @staticmethod
    def _run_at(
        root: Path, args: list[str], *, timeout: int = 15, text: bool = True
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        """Run Git without a shell, hooks, prompts, or repository-controlled paging."""

        environment = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
            capture_output=True,
            check=False,
            env=environment,
            text=text,
            timeout=timeout,
        )

    def _run(
        self, args: list[str], *, timeout: int = 15, text: bool = True
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        """Run a bounded Git plumbing command at this reader's fixed root."""

        return self._run_at(self.root, args, timeout=timeout, text=text)

    def resolve_commit(self, ref: str) -> str:
        """Resolve an explicit ref to an existing commit without fetching objects."""

        if not ref or ref.startswith("-") or any(char in ref for char in ("\x00", "\n", " ")):
            raise RepositoryEvidenceError("Git ref contains unsupported syntax")
        result = self._run(["rev-parse", "--verify", f"{ref}^{{commit}}"])
        assert isinstance(result.stdout, str)
        sha = result.stdout.strip() if result.returncode == 0 else ""
        if len(sha) != 40 or not all(char in "0123456789abcdef" for char in sha):
            raise RepositoryEvidenceError(f"Git commit is unavailable locally: {ref}")
        return sha

    def list_objects(self, ref: str, *, max_entries: int = 20_000) -> tuple[RepositoryObject, ...]:
        """List bounded tree entries without following symlinks or submodules."""

        sha = self.resolve_commit(ref)
        result = self._run(["ls-tree", "-r", "--full-tree", sha], timeout=30)
        assert isinstance(result.stdout, str)
        if result.returncode != 0:
            raise RepositoryEvidenceError("failed to enumerate repository tree")
        lines = result.stdout.splitlines()
        if len(lines) > max_entries:
            raise RepositoryEvidenceError("repository tree exceeds the bounded entry limit")
        entries = []
        for line in lines:
            match = OBJECT_LINE_RE.fullmatch(line)
            if match is None:
                raise RepositoryEvidenceError("Git returned an unsupported tree entry")
            entries.append(
                RepositoryObject(
                    path=normalize_repo_path(match.group("path")),
                    mode=match.group("mode"),
                    object_type=match.group("type"),
                    object_sha=match.group("sha"),
                )
            )
        return tuple(entries)

    def object_at(self, ref: str, path: str) -> RepositoryObject | None:
        """Return one exact tree entry, preserving symlink and submodule types."""

        safe_path = normalize_repo_path(path)
        sha = self.resolve_commit(ref)
        result = self._run(["ls-tree", sha, "--", safe_path])
        assert isinstance(result.stdout, str)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        lines = result.stdout.splitlines()
        if len(lines) != 1:
            raise RepositoryEvidenceError("Git returned an ambiguous tree entry")
        match = OBJECT_LINE_RE.fullmatch(lines[0])
        if match is None or normalize_repo_path(match.group("path")) != safe_path:
            raise RepositoryEvidenceError("Git returned a mismatched tree entry")
        return RepositoryObject(
            path=safe_path,
            mode=match.group("mode"),
            object_type=match.group("type"),
            object_sha=match.group("sha"),
        )

    def read_blob(self, ref: str, path: str) -> bytes | None:
        """Read one bounded regular blob without dereferencing repository links."""

        entry = self.object_at(ref, path)
        if entry is None:
            return None
        if entry.is_symlink:
            raise RepositoryEvidenceError(f"refusing to follow repository symlink: {entry.path}")
        if entry.is_submodule or entry.object_type != "blob":
            raise RepositoryEvidenceError(
                f"refusing to read non-file repository object: {entry.path}"
            )
        size_result = self._run(["cat-file", "-s", entry.object_sha])
        assert isinstance(size_result.stdout, str)
        try:
            size = int(size_result.stdout.strip()) if size_result.returncode == 0 else -1
        except ValueError as exc:
            raise RepositoryEvidenceError("Git returned an invalid object size") from exc
        if size < 0 or size > self.max_file_bytes:
            raise RepositoryEvidenceError(
                f"repository blob exceeds {self.max_file_bytes} bytes: {entry.path}"
            )
        content = self._run(["cat-file", "blob", entry.object_sha], text=False)
        assert isinstance(content.stdout, bytes)
        if content.returncode != 0 or len(content.stdout) != size:
            raise RepositoryEvidenceError("failed to read the complete repository blob")
        return content.stdout

    def changed_paths(
        self, base_ref: str, head_ref: str, *, max_paths: int = 10_000
    ) -> tuple[str, ...]:
        """Return deterministic changed paths, including both sides of renames."""

        base = self.resolve_commit(base_ref)
        head = self.resolve_commit(head_ref)
        result = self._run(["diff", "--name-status", "--find-renames", "--no-ext-diff", base, head])
        assert isinstance(result.stdout, str)
        if result.returncode != 0:
            raise RepositoryEvidenceError("failed to compare immutable repository refs")
        paths: set[str] = set()
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                raise RepositoryEvidenceError("Git returned an invalid name-status row")
            for raw_path in parts[1:]:
                paths.add(normalize_repo_path(raw_path))
                if len(paths) > max_paths:
                    raise RepositoryEvidenceError("changed path count exceeds the bounded limit")
        return tuple(sorted(paths))


def build_file_snapshot(
    reader: GitRepositoryReader,
    ref: str,
    role: RefRole,
    *,
    paths: tuple[str, ...] | None = None,
) -> EvidenceSnapshot:
    """Build repository-file facts for a commit without reading file contents."""

    if role is RefRole.SHARED:
        raise RepositoryEvidenceError("file snapshot role must be base or head")
    sha = reader.resolve_commit(ref)
    selected = set(paths) if paths is not None else None
    records = []
    diagnostics = []
    trust = TrustClass.TARGET_REPOSITORY if role is RefRole.BASE else TrustClass.SOURCE_REPOSITORY
    for entry in reader.list_objects(sha):
        if selected is not None and entry.path not in selected:
            continue
        if entry.is_symlink:
            diagnostics.append(f"symlink not followed: {entry.path}")
        if entry.is_submodule:
            diagnostics.append(f"submodule not traversed: {entry.path}")
        records.append(
            EvidenceRecord(
                kind="repository.file",
                value={
                    "mode": entry.mode,
                    "object_type": entry.object_type,
                    "object_sha": entry.object_sha,
                },
                source_path=entry.path,
                ref=role,
                commit_sha=sha,
                provenance="git.ls_tree",
                confidence=Confidence.EXACT,
                trust=trust,
            )
        )
    return EvidenceSnapshot(role, sha, tuple(records), tuple(sorted(diagnostics)))


def file_deltas(base: EvidenceSnapshot, head: EvidenceSnapshot) -> tuple[EvidenceDelta, ...]:
    """Compute explicit file-level deltas from immutable evidence snapshots."""

    before = {
        record.source_path: record for record in base.records if record.kind == "repository.file"
    }
    after = {
        record.source_path: record for record in head.records if record.kind == "repository.file"
    }
    deltas = []
    for path in sorted(before.keys() | after.keys()):
        old = before.get(path)
        new = after.get(path)
        if old is None:
            change = "added"
        elif new is None:
            change = "removed"
        elif old.value != new.value:
            change = "changed"
        else:
            continue
        deltas.append(
            EvidenceDelta(
                kind="repository.file",
                component="repository",
                identity=path,
                change=change,
                before=None if old is None else old.value,
                after=None if new is None else new.value,
            )
        )
    return tuple(deltas)
