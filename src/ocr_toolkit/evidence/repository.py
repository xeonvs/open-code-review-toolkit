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
BATCH_HEADER_RE = re.compile(
    rb"^(?P<sha>[0-9a-f]{40}) (?P<type>blob|tree|commit) (?P<size>[0-9]+)\n$"
)
MAX_BATCH_BLOB_BYTES = 32_000_000
MAX_GIT_TEXT_BYTES = 8_000_000


def _git_environment() -> dict[str, str]:
    """Return a Git environment without caller-injected configuration entries."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
            "GIT_CONFIG_COUNT",
            "GIT_CONFIG_PARAMETERS",
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_REPLACE_REF_BASE",
            "GIT_WORK_TREE",
        }
        and not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
    )
    return environment


def _git_prefix(root: Path) -> list[str]:
    """Return the fixed safe prefix for read-only repository Git commands."""

    return ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root)]


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


@dataclass(frozen=True, slots=True)
class BoundedBlobRead:
    """Return successfully read blobs and explicit per-candidate omissions."""

    blobs: dict[str, bytes]
    diagnostics: tuple[str, ...]


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

        completed = subprocess.run(
            [*_git_prefix(root), *args],
            capture_output=True,
            check=False,
            env=_git_environment(),
            text=text,
            timeout=timeout,
        )
        stdout_size = (
            len(completed.stdout.encode("utf-8"))
            if isinstance(completed.stdout, str)
            else len(completed.stdout)
        )
        stderr_size = (
            len(completed.stderr.encode("utf-8"))
            if isinstance(completed.stderr, str)
            else len(completed.stderr)
        )
        if stdout_size > MAX_GIT_TEXT_BYTES or stderr_size > MAX_GIT_TEXT_BYTES:
            raise RepositoryEvidenceError("Git plumbing output exceeds the bounded byte limit")
        return completed

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

    @staticmethod
    def _batch_request(entries: tuple[RepositoryObject, ...]) -> bytes:
        """Validate immutable blob entries and encode an object-ID-only request."""

        if len(entries) > 10_000:
            raise RepositoryEvidenceError("batch blob request exceeds 10000 entries")
        seen_paths: set[str] = set()
        request = bytearray()
        for entry in entries:
            if normalize_repo_path(entry.path) != entry.path or not re.fullmatch(
                r"[0-9a-f]{40}", entry.object_sha
            ):
                raise RepositoryEvidenceError("batch blob entry is not normalized")
            if entry.path in seen_paths:
                raise RepositoryEvidenceError(f"duplicate batch blob path: {entry.path}")
            seen_paths.add(entry.path)
            if entry.is_symlink:
                raise RepositoryEvidenceError(
                    f"refusing to follow repository symlink: {entry.path}"
                )
            if entry.is_submodule or entry.object_type != "blob":
                raise RepositoryEvidenceError(
                    f"refusing to read non-file repository object: {entry.path}"
                )
            request.extend(entry.object_sha.encode("ascii"))
            request.extend(b"\n")
        return bytes(request)

    def _batch_sizes(self, entries: tuple[RepositoryObject, ...]) -> tuple[int, ...]:
        """Return authenticated object sizes from one bounded batch-check process."""

        request = self._batch_request(entries)

        environment = _git_environment()
        command_prefix = [*_git_prefix(self.root), "cat-file"]
        try:
            size_result = subprocess.run(
                [*command_prefix, "--batch-check"],
                cwd=self.root,
                env=environment,
                input=request,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepositoryEvidenceError("bounded Git batch size check failed") from exc
        if size_result.returncode != 0:
            raise RepositoryEvidenceError("Git batch size check failed")
        headers = size_result.stdout.splitlines(keepends=True)
        if len(headers) != len(entries):
            raise RepositoryEvidenceError("Git returned an invalid batch size response")
        sizes = []
        for entry, header in zip(entries, headers, strict=True):
            match = BATCH_HEADER_RE.fullmatch(header)
            if match is None or match.group("sha").decode("ascii") != entry.object_sha:
                raise RepositoryEvidenceError("Git returned an invalid batch size header")
            if match.group("type") != b"blob":
                raise RepositoryEvidenceError("Git batch object is not a blob")
            sizes.append(int(match.group("size")))
        return tuple(sizes)

    def _batch_contents(
        self, entries: tuple[RepositoryObject, ...], sizes: tuple[int, ...]
    ) -> dict[str, bytes]:
        """Read preflighted immutable blobs and validate every response frame."""

        if len(entries) != len(sizes):
            raise RepositoryEvidenceError("batch blob size count does not match request")
        request = self._batch_request(entries)
        environment = _git_environment()
        command_prefix = [*_git_prefix(self.root), "cat-file"]
        try:
            result = subprocess.run(
                [*command_prefix, "--batch"],
                cwd=self.root,
                env=environment,
                input=request,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepositoryEvidenceError("bounded Git batch read failed") from exc
        if result.returncode != 0:
            raise RepositoryEvidenceError("Git batch read failed")

        output = result.stdout
        offset = 0
        decoded: dict[str, bytes] = {}
        for entry, expected_size in zip(entries, sizes, strict=True):
            newline = output.find(b"\n", offset)
            if newline < 0:
                raise RepositoryEvidenceError("Git returned a truncated batch header")
            match = BATCH_HEADER_RE.fullmatch(output[offset : newline + 1])
            if match is None:
                raise RepositoryEvidenceError("Git returned an invalid batch header")
            if match.group("sha").decode("ascii") != entry.object_sha:
                raise RepositoryEvidenceError("Git returned an unexpected batch object")
            if match.group("type") != b"blob":
                raise RepositoryEvidenceError("Git batch object is not a blob")
            size = int(match.group("size"))
            if size != expected_size:
                raise RepositoryEvidenceError("Git batch object size changed after preflight")
            start = newline + 1
            end = start + size
            if end >= len(output) or output[end] != 0x0A:
                raise RepositoryEvidenceError("Git returned a truncated batch blob")
            decoded[entry.path] = output[start:end]
            offset = end + 1
        if offset != len(output):
            raise RepositoryEvidenceError("Git returned unexpected trailing batch data")
        return decoded

    def read_blobs(self, entries: tuple[RepositoryObject, ...]) -> dict[str, bytes]:
        """Read regular blobs strictly through two immutable Git batch processes."""

        if not entries:
            return {}
        sizes = self._batch_sizes(entries)
        total_size = 0
        for entry, size in zip(entries, sizes, strict=True):
            if size > self.max_file_bytes:
                raise RepositoryEvidenceError(
                    f"repository blob exceeds {self.max_file_bytes} bytes: {entry.path}"
                )
            total_size += size
            if total_size > MAX_BATCH_BLOB_BYTES:
                raise RepositoryEvidenceError(
                    f"batch blob content exceeds {MAX_BATCH_BLOB_BYTES} bytes"
                )
        return self._batch_contents(entries, sizes)

    def read_candidate_blobs(self, entries: tuple[RepositoryObject, ...]) -> BoundedBlobRead:
        """Read candidates within bounds while reporting deterministic omissions."""

        if not entries:
            return BoundedBlobRead({}, ())
        sizes = self._batch_sizes(entries)
        accepted_entries = []
        accepted_sizes = []
        diagnostics = []
        total_size = 0
        for entry, size in zip(entries, sizes, strict=True):
            if size > self.max_file_bytes:
                diagnostics.append(
                    f"omitted {entry.path}: blob exceeds {self.max_file_bytes} bytes"
                )
                continue
            if total_size + size > MAX_BATCH_BLOB_BYTES:
                diagnostics.append(
                    f"omitted {entry.path}: batch content exceeds {MAX_BATCH_BLOB_BYTES} bytes"
                )
                continue
            accepted_entries.append(entry)
            accepted_sizes.append(size)
            total_size += size
        blobs = (
            self._batch_contents(tuple(accepted_entries), tuple(accepted_sizes))
            if accepted_entries
            else {}
        )
        return BoundedBlobRead(blobs, tuple(diagnostics))

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
