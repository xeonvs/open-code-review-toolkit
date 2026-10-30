"""Read immutable repository refs and derive bounded evidence snapshots."""

from __future__ import annotations

import math
import os
import re
import selectors
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ocr_toolkit.common.git import isolated_git_environment, read_only_git_prefix
from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceSnapshot,
    RefRole,
    TrustClass,
)

OBJECT_RECORD_RE = re.compile(
    rb"^(?P<mode>[0-7]{6}) (?P<type>blob|tree|commit) (?P<sha>[0-9a-f]{40})\t(?P<path>.*)$",
    re.DOTALL,
)
BATCH_HEADER_RE = re.compile(
    rb"^(?P<sha>[0-9a-f]{40}) (?P<type>blob|tree|commit) (?P<size>[0-9]+)\n$"
)
MAX_BATCH_BLOB_BYTES = 32_000_000
MAX_GIT_TEXT_BYTES = 8_000_000
MAX_ANCESTRY_FETCH_DEPTH = 128
MAX_GITMODULES_BYTES = 128_000
MAX_GITMODULES_ENTRIES = 256
MAX_SUBMODULE_NAME_BYTES = 256


def _git_environment() -> dict[str, str]:
    """Return a Git environment without caller-injected configuration entries."""

    return isolated_git_environment()


def _git_prefix(root: Path) -> list[str]:
    """Return the fixed safe prefix for read-only repository Git commands."""

    return read_only_git_prefix(root)


class RepositoryEvidenceError(ValueError):
    """Report an invalid ref, path, object type, or bounded Git read."""


class ShallowAncestryUnavailable(RepositoryEvidenceError):
    """Ancestry is undecidable until a bounded fetch supplies more parents."""


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
    if normalized.startswith("-") or any(
        character == "\x7f" or ord(character) < 32 for character in normalized
    ):
        raise RepositoryEvidenceError("repository path contains unsupported control syntax")
    return normalized


class GitRepositoryReader:
    """Provide bounded read-only Git plumbing for one trusted repository root."""

    def __init__(
        self,
        root: Path,
        *,
        max_file_bytes: int = 256_000,
        deadline: float | None = None,
        command_timeout: float | None = None,
    ) -> None:
        """Resolve the repository root and constrain every subsequent Git command."""

        if deadline is not None and not math.isfinite(deadline):
            raise RepositoryEvidenceError("repository deadline must be finite")
        if command_timeout is not None and (
            not math.isfinite(command_timeout) or command_timeout <= 0
        ):
            raise RepositoryEvidenceError("repository command timeout must be finite and positive")
        self.deadline = deadline
        self.command_timeout = command_timeout
        resolved = root.resolve(strict=True)
        probe = self._run_at(resolved, ["rev-parse", "--show-toplevel"], timeout=self._timeout(15))
        if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != resolved:
            raise RepositoryEvidenceError("root is not a Git repository top level")
        self.root = resolved
        if not 1 <= max_file_bytes <= 5_000_000:
            raise RepositoryEvidenceError("max_file_bytes must be between 1 and 5000000")
        self.max_file_bytes = max_file_bytes

    def _timeout(self, limit: int) -> float:
        """Cap each Git process by an optional caller-owned monotonic deadline."""

        budget = self.command_timeout if self.command_timeout is not None else limit
        if self.deadline is None:
            return budget
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RepositoryEvidenceError("repository acquisition deadline exceeded")
        return min(budget, remaining)

    @staticmethod
    def _run_at(
        root: Path, args: list[str], *, timeout: float = 15, text: bool = True
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

        if self.command_timeout is not None:
            return self._run_streamed(args, timeout=self._timeout(timeout), text=text)
        return self._run_at(self.root, args, timeout=self._timeout(timeout), text=text)

    def _run_streamed(
        self, args: list[str], *, timeout: float, text: bool
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        """Bound audit metadata while consuming it, including enormous Git trees."""

        command = [*_git_prefix(self.root), *args]
        output, errors = bytearray(), bytearray()
        deadline = time.monotonic() + timeout
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_git_environment()
        ) as process:
            assert process.stdout is not None and process.stderr is not None
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ, output)
                    selector.register(process.stderr, selectors.EVENT_READ, errors)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RepositoryEvidenceError(
                                "Git metadata acquisition deadline exceeded"
                            )
                        for key, _events in selector.select(remaining):
                            part = os.read(key.fd, 65536)
                            if not part:
                                selector.unregister(key.fileobj)
                            else:
                                if len(key.data) + len(part) > MAX_GIT_TEXT_BYTES:
                                    raise RepositoryEvidenceError(
                                        "Git plumbing output exceeds the bounded byte limit"
                                    )
                                key.data.extend(part)
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
        if text:
            return subprocess.CompletedProcess(
                command, process.returncode, output.decode(), errors.decode()
            )
        return subprocess.CompletedProcess(
            command, process.returncode, bytes(output), bytes(errors)
        )

    def has_commit(self, sha: str) -> bool:
        """Return whether one exact lowercase commit object is available locally."""

        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise RepositoryEvidenceError("Git commit identity must be a lowercase SHA-1")
        result = self._run(["cat-file", "-e", f"{sha}^{{commit}}"])
        return result.returncode == 0

    def fetch_commit(self, sha: str, *, remote: str = "origin") -> None:
        """Fetch one exact commit from the runner-owned origin without ref mutation."""

        self._validate_fetch_identity(sha, remote)
        if not self.has_commit(sha):
            self._fetch_commit(sha, depth=1)

    def fetch_commit_history(self, sha: str) -> None:
        """Fetch bounded parents for a shallow ancestry proof, even if the tip exists."""

        self._validate_fetch_identity(sha, "origin")
        self._fetch_commit(sha, depth=MAX_ANCESTRY_FETCH_DEPTH)

    @staticmethod
    def _validate_fetch_identity(sha: str, remote: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise RepositoryEvidenceError("Git commit identity must be a lowercase SHA-1")
        if remote != "origin":
            raise RepositoryEvidenceError("only the runner-owned origin remote is supported")

    def _fetch_commit(self, sha: str, *, depth: int) -> None:
        try:
            completed = subprocess.run(
                [
                    *_git_prefix(self.root),
                    "-c",
                    "protocol.version=2",
                    "fetch",
                    "--no-tags",
                    "--no-write-fetch-head",
                    "--no-recurse-submodules",
                    "--filter=blob:none",
                    f"--depth={depth}",
                    "origin",
                    sha,
                ],
                cwd=self.root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                env=_git_environment(),
                timeout=self._timeout(60),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepositoryEvidenceError("bounded protected-target fetch failed") from exc
        if completed.returncode != 0 or not self.has_commit(sha):
            raise RepositoryEvidenceError("captured protected-target commit is unavailable")
        if self.resolve_commit(sha) != sha:
            raise RepositoryEvidenceError("fetched protected-target identity does not match")

    def is_ancestor(self, older_sha: str, newer_sha: str) -> bool:
        """Prove ancestry of two available commits without accepting shallow uncertainty."""

        for sha in (older_sha, newer_sha):
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise RepositoryEvidenceError("Git ancestry requires lowercase SHA-1 identities")
            if self.resolve_commit(sha) != sha:
                raise RepositoryEvidenceError("Git ancestry commit identity does not match")
        graft_path_result = self._run(["rev-parse", "--git-path", "info/grafts"])
        assert isinstance(graft_path_result.stdout, str)
        graft_path_text = graft_path_result.stdout
        if (
            graft_path_result.returncode != 0
            or not graft_path_text.endswith("\n")
            or graft_path_text.count("\n") != 1
            or not graft_path_text[:-1]
        ):
            raise RepositoryEvidenceError("Git graft location is unverifiable")
        graft_path = Path(graft_path_text[:-1])
        if not graft_path.is_absolute():
            graft_path = self.root / graft_path
        if graft_path.exists() or graft_path.is_symlink():
            raise RepositoryEvidenceError("Git grafts make ancestry unverifiable")
        result = self._run(["merge-base", "--is-ancestor", older_sha, newer_sha])
        if result.returncode == 0:
            return True
        if result.returncode != 1:
            raise RepositoryEvidenceError("Git ancestry check failed")
        shallow = self._run(["rev-parse", "--is-shallow-repository"])
        if shallow.returncode != 0 or shallow.stdout.strip() not in {"true", "false"}:
            raise RepositoryEvidenceError("Git ancestry depth is unverifiable")
        if shallow.stdout.strip() == "true":
            raise ShallowAncestryUnavailable("Git ancestry is unverifiable in a shallow repository")
        return False

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
        result = self._run(["ls-tree", "-z", "-r", "--full-tree", sha], timeout=30, text=False)
        assert isinstance(result.stdout, bytes)
        if result.returncode != 0:
            raise RepositoryEvidenceError("failed to enumerate repository tree")
        records = result.stdout.split(b"\0")
        if records and records[-1] == b"":
            records.pop()
        if len(records) > max_entries:
            raise RepositoryEvidenceError("repository tree exceeds the bounded entry limit")
        entries = []
        for record in records:
            match = OBJECT_RECORD_RE.fullmatch(record)
            if match is None:
                raise RepositoryEvidenceError("Git returned an unsupported tree entry")
            try:
                raw_path = match.group("path").decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RepositoryEvidenceError("repository path is not valid UTF-8") from exc
            entries.append(
                RepositoryObject(
                    path=normalize_repo_path(raw_path),
                    mode=match.group("mode").decode("ascii"),
                    object_type=match.group("type").decode("ascii"),
                    object_sha=match.group("sha").decode("ascii"),
                )
            )
        return tuple(entries)

    def object_at(self, ref: str, path: str) -> RepositoryObject | None:
        """Return one exact tree entry, preserving symlink and submodule types."""

        safe_path = normalize_repo_path(path)
        sha = self.resolve_commit(ref)
        result = self._run(["ls-tree", "-z", sha, "--", safe_path], text=False)
        assert isinstance(result.stdout, bytes)
        if result.returncode != 0 or not result.stdout:
            return None
        records = result.stdout.split(b"\0")
        if records[-1] or len(records) != 2:
            raise RepositoryEvidenceError("Git returned an ambiguous tree entry")
        match = OBJECT_RECORD_RE.fullmatch(records[0])
        if match is None:
            raise RepositoryEvidenceError("Git returned an invalid tree entry")
        try:
            returned_path = normalize_repo_path(match.group("path").decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise RepositoryEvidenceError("repository paths must be valid UTF-8") from exc
        if returned_path != safe_path:
            raise RepositoryEvidenceError("Git returned a mismatched tree entry")
        return RepositoryObject(
            path=safe_path,
            mode=match.group("mode").decode("ascii"),
            object_type=match.group("type").decode("ascii"),
            object_sha=match.group("sha").decode("ascii"),
        )

    def read_blob(self, ref: str, path: str) -> bytes | None:
        """Read one bounded regular blob without dereferencing repository links."""

        entry = self.object_at(ref, path)
        if entry is None:
            return None
        size = self.bounded_regular_blob_size(entry)
        content = self._run(["cat-file", "blob", entry.object_sha], text=False)
        assert isinstance(content.stdout, bytes)
        if content.returncode != 0 or len(content.stdout) != size:
            raise RepositoryEvidenceError("failed to read the complete repository blob")
        return content.stdout

    def gitmodules_paths(self, ref: str) -> dict[str, str]:
        """Parse one committed .gitmodules blob without includes or URL access.

        The mapping is name to normalized path. Callers retain it privately and
        only use names as data in process-local Git configuration, never a shell.
        """

        entry = self.object_at(ref, ".gitmodules")
        if entry is None:
            return {}
        if entry.mode != "100644" or entry.object_type != "blob":
            raise RepositoryEvidenceError(".gitmodules is not a regular configuration blob")
        if self.bounded_regular_blob_size(entry) > MAX_GITMODULES_BYTES:
            raise RepositoryEvidenceError(".gitmodules exceeds the bounded byte limit")
        result = self._run(
            ["config", f"--blob={entry.object_sha}", "--no-includes", "-z", "--list"],
            text=False,
        )
        assert isinstance(result.stdout, bytes)
        if result.returncode != 0 or len(result.stdout) > MAX_GITMODULES_BYTES * 2:
            raise RepositoryEvidenceError(".gitmodules configuration is invalid or too large")
        records = result.stdout.split(b"\0")
        if records[-1] != b"":
            raise RepositoryEvidenceError(".gitmodules configuration is truncated")
        records.pop()
        if len(records) > MAX_GITMODULES_ENTRIES:
            raise RepositoryEvidenceError(".gitmodules has too many entries")
        paths: dict[str, str] = {}
        seen_paths: set[str] = set()
        for record in records:
            if record.count(b"\n") != 1:
                raise RepositoryEvidenceError(".gitmodules contains an invalid entry")
            raw_key, raw_value = record.split(b"\n", 1)
            try:
                key = raw_key.decode("utf-8")
                value = raw_value.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RepositoryEvidenceError(".gitmodules contains invalid UTF-8") from exc
            if key.startswith(("include.", "includeif.")):
                raise RepositoryEvidenceError(".gitmodules includes are unsupported")
            if not key.startswith("submodule.") or not key.endswith(".path"):
                continue
            name = key[len("submodule.") : -len(".path")]
            if (
                not name
                or len(name.encode("utf-8")) > MAX_SUBMODULE_NAME_BYTES
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or name in paths
            ):
                raise RepositoryEvidenceError(".gitmodules submodule name is ambiguous")
            path = normalize_repo_path(value)
            if path in seen_paths:
                raise RepositoryEvidenceError(".gitmodules path is ambiguous")
            paths[name] = path
            seen_paths.add(path)
        return paths

    def bounded_regular_blob_size(self, entry: RepositoryObject) -> int:
        """Validate one exact entry as a bounded regular blob without reading its content."""

        if normalize_repo_path(entry.path) != entry.path:
            raise RepositoryEvidenceError("repository blob path is not normalized")
        if entry.is_symlink:
            raise RepositoryEvidenceError(f"refusing to follow repository symlink: {entry.path}")
        if (
            entry.is_submodule
            or entry.object_type != "blob"
            or entry.mode not in {"100644", "100755"}
        ):
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
        return size

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
                timeout=self._timeout(30),
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
                timeout=self._timeout(30),
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

    def read_candidate_blobs(
        self, entries: tuple[RepositoryObject, ...], *, max_total_bytes: int | None = None
    ) -> BoundedBlobRead:
        """Read candidates within bounds while reporting deterministic omissions."""

        if max_total_bytes is None:
            max_total_bytes = MAX_BATCH_BLOB_BYTES
        if type(max_total_bytes) is not int or not 0 <= max_total_bytes <= MAX_BATCH_BLOB_BYTES:
            raise RepositoryEvidenceError("invalid candidate batch byte budget")
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
            if total_size + size > max_total_bytes:
                diagnostics.append(
                    f"omitted {entry.path}: batch content exceeds {max_total_bytes} bytes"
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
        result = self._run(
            ["diff", "--name-status", "-z", "--find-renames", "--no-ext-diff", base, head],
            text=False,
        )
        assert isinstance(result.stdout, bytes)
        if result.returncode != 0:
            raise RepositoryEvidenceError("failed to compare immutable repository refs")
        paths: set[str] = set()
        fields = result.stdout.split(b"\0")
        if fields and fields[-1] == b"":
            fields.pop()
        index = 0
        while index < len(fields):
            status = fields[index]
            index += 1
            path_count = 2 if status[:1] in {b"R", b"C"} else 1
            if not status or index + path_count > len(fields):
                raise RepositoryEvidenceError("Git returned an invalid name-status record")
            for raw_path in fields[index : index + path_count]:
                try:
                    decoded_path = raw_path.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise RepositoryEvidenceError("changed path is not valid UTF-8") from exc
                paths.add(normalize_repo_path(decoded_path))
                if len(paths) > max_paths:
                    raise RepositoryEvidenceError("changed path count exceeds the bounded limit")
            index += path_count
        return tuple(sorted(paths))


def build_file_snapshot(
    reader: GitRepositoryReader,
    ref: str,
    role: RefRole,
    *,
    paths: tuple[str, ...] | None = None,
) -> EvidenceSnapshot:
    """Build repository-file facts for a commit without reading file contents."""

    if role not in {RefRole.BASE, RefRole.HEAD, RefRole.TARGET}:
        raise RepositoryEvidenceError("file snapshot role must be base, head, or target")
    sha = reader.resolve_commit(ref)
    selected = set(paths) if paths is not None else None
    records = []
    diagnostics = []
    trust = (
        TrustClass.TARGET_REPOSITORY
        if role in {RefRole.BASE, RefRole.TARGET}
        else TrustClass.SOURCE_REPOSITORY
    )
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
