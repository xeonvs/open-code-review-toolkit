"""Repository, filesystem, command, and glob helpers for OCR context generation."""

from __future__ import annotations

import fnmatch
import heapq
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ocr_toolkit.context.settings import (
    DEFAULT_MAX_FILE_BYTES,
    MAX_BACKGROUND_SECTION_ITEMS,
    inline_code,
)

ROOT = Path.cwd()


@dataclass(frozen=True)
class CommandResult:
    """Small command execution result used for optional local tool detection."""

    stdout: str
    stderr: str
    returncode: int


DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        ".DS_Store",
        ".review-context",
        "node_modules",
        "vendor",
        ".venv",
        "venv",
        "__pycache__",
    }
)

LOCAL_GUIDANCE_STATUS_PATHS = frozenset(
    {
        "PR_REVIEW.md",
        "AGENTS.md",
        "AGENTS.MD",
        "CLAUDE.md",
        "CLAUDE.MD",
        ".cursorrules",
        ".github/copilot-instructions.md",
        ".opencodereview/accepted-decisions.md",
    }
)


def run_command(cmd: Sequence[str], timeout: int = 10) -> CommandResult:
    """Run a local command and return captured output without raising.

    Commands are used only for optional local version discovery, for example
    `ansible --version` when the binary is available in the CI image.
    """

    try:
        proc = subprocess.run(
            list(cmd),
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return CommandResult(proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired as exc:
        # Surface timeouts: a silent empty result here turns into a
        # missing background section downstream and is much harder to
        # diagnose than a one-line log entry.
        print(
            f"run_command timeout after {timeout}s: {' '.join(str(c) for c in cmd)}",
            file=sys.stderr,
        )
        return CommandResult("", str(exc), 124)
    except Exception as exc:
        print(
            f"run_command failed: {' '.join(str(c) for c in cmd)}: {exc}",
            file=sys.stderr,
        )
        return CommandResult("", str(exc), 127)


def resolve_repo_file(path: Path) -> Path | None:
    """Return a resolved regular file path only when it stays inside ROOT."""

    try:
        root = ROOT.resolve()
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None

    return resolved if resolved.is_file() else None


def safe_repo_match(path: Path, *, files_only: bool) -> Path | None:
    """Return a repository-local match only when it is safe to count."""

    if has_symlink_component(path):
        return None
    if files_only:
        return resolve_repo_file(path)
    try:
        root = ROOT.resolve()
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    return resolved


def has_symlink_component(path: Path) -> bool:
    """Return whether any path component under ROOT is a symlink."""

    try:
        rel_path = path.relative_to(ROOT)
    except ValueError:
        return True

    current = ROOT
    for part in rel_path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def trusted_guidance_file(rel_path: str) -> Path | None:
    """Return a trusted guidance file, or None when unsafe or missing."""

    path = ROOT / rel_path
    if has_symlink_component(path):
        print(
            f"Skipping symlinked guidance path {rel_path}; cannot trust its content for reviewer guidance.",
            file=sys.stderr,
        )
        return None
    return resolve_repo_file(path)


def resolve_output_path(value: str) -> Path | None:
    """Resolve an output path limited to the repo or system temp directory."""

    root_lexical = ROOT.absolute()
    root = ROOT.resolve()
    requested = Path(value)
    logical_output = requested if requested.is_absolute() else root_lexical / requested
    logical_output = logical_output.absolute()
    # tempfile supplies the platform temp root; containment and symlink checks follow.
    temp_lexical = Path(tempfile.gettempdir()).absolute()  # nosec B108
    allowed_roots = [(root_lexical, root), (root, root)]
    temp_resolved = temp_lexical.resolve()
    allowed_roots.extend([(temp_lexical, temp_resolved), (temp_resolved, temp_resolved)])
    # POSIX /tmp may be a distinct lexical alias (for example, /private/tmp).
    tmp_path = Path("/tmp")  # nosec B108
    if tmp_path.exists():
        tmp_lexical = tmp_path.absolute()
        tmp_resolved = tmp_path.resolve()
        allowed_roots.extend([(tmp_lexical, tmp_resolved), (tmp_resolved, tmp_resolved)])

    for lexical_root, resolved_root in allowed_roots:
        try:
            logical_relative = logical_output.relative_to(lexical_root)
        except ValueError:
            continue
        current = lexical_root
        for part in logical_relative.parts:
            current = current / part
            if current.is_symlink():
                return None
        try:
            output = logical_output.resolve()
            output.relative_to(resolved_root)
        except (OSError, ValueError):
            return None
        return output

    return None


def read_text(path: Path, max_bytes: int = DEFAULT_MAX_FILE_BYTES) -> str:
    """Read a UTF-8-ish repository text file defensively with a byte limit."""

    safe_path = resolve_repo_file(path)
    if safe_path is None:
        return ""

    try:
        with safe_path.open("rb") as handle:
            read_limit = max(0, max_bytes)
            data = handle.read(read_limit)
            truncated = read_limit > 0 and bool(handle.read(1))
    except OSError:
        return ""

    text = data.decode("utf-8", errors="replace")
    if truncated:
        text = text.rstrip() + f"\n# [truncated after {read_limit} bytes]\n"
    return text


def path_exists(path: str) -> bool:
    """Return whether a repository-relative regular file exists."""

    return resolve_repo_file(ROOT / path) is not None


def inline_ci_value(
    env_name: str,
    *,
    fallback_git_args: Sequence[str] | None = None,
    use_default_branch: bool = False,
) -> str:
    """Render CI metadata, marking local fallbacks explicitly."""

    value = os.environ.get(env_name, "").strip()
    if value:
        return inline_code(value)

    fallback_value = ""
    if use_default_branch:
        fallback_value = local_default_branch()
    elif fallback_git_args is not None:
        fallback_value = git_output(fallback_git_args)

    if fallback_value:
        return f"{inline_code(fallback_value)} _(local fallback; {env_name} unset)_"
    return f"_(not provided; {env_name} unset)_"


def git_output(args: Sequence[str], timeout: int = 10) -> str:
    """Return stripped git stdout or an empty string on failure."""

    result = run_command(["git", *args], timeout=timeout)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def local_default_branch() -> str:
    """Return the local default branch ref when GitLab CI metadata is absent."""

    ref = git_output(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if ref:
        return ref

    default_branch = os.environ.get("CI_DEFAULT_BRANCH", "").strip()
    if default_branch:
        return default_branch

    return ""


def bounded_rel_glob(
    patterns: Iterable[str],
    limit: int = MAX_BACKGROUND_SECTION_ITEMS,
    *,
    files_only: bool = False,
    exclude_dirs: Iterable[str] | None = None,
) -> list[str]:
    """Find bounded repository-relative glob matches without materializing all matches.

    Heavy vendored/build directories are excluded by default so a single
    `**/...` pattern does not walk through `node_modules`, `vendor`, etc.
    Pass an explicit ``exclude_dirs`` (including an empty iterable) to
    override the default set.
    """

    if limit <= 0:
        return []

    result: list[str] = []
    seen: set[str] = set()
    excluded_parts = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else frozenset(exclude_dirs)

    for pattern in patterns:
        remaining = limit - len(result)
        if remaining <= 0:
            return result
        paths = (
            iter_plain_glob(
                pattern,
                excluded_parts,
                limit=remaining,
                files_only=files_only,
                skip_rel_paths=seen,
            )
            if "**" not in pattern
            else iter_repo_glob(
                pattern,
                excluded_parts,
                limit=remaining,
                files_only=files_only,
                skip_rel_paths=seen,
            )
        )
        for path in paths:
            rel_path = path.relative_to(ROOT)
            rel = str(rel_path)
            if rel in seen:
                continue

            seen.add(rel)
            result.append(rel)
            if len(result) >= limit:
                return result

    return result


def iter_repo_glob(
    pattern: str,
    excluded_parts: frozenset[str],
    limit: int | None = None,
    *,
    files_only: bool = False,
    skip_rel_paths: set[str] | None = None,
) -> Iterable[Path]:
    """Yield repository paths for a glob pattern while pruning excluded dirs."""

    if "**" not in pattern:
        for path in iter_plain_glob(
            pattern,
            excluded_parts,
            limit=limit,
            files_only=files_only,
            skip_rel_paths=skip_rel_paths,
        ):
            yield path
        return

    pattern_parts = tuple(part for part in pattern.split("/") if part)

    @cache
    def matches(parts: tuple[str, ...], pattern_index: int = 0, path_index: int = 0) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(parts)
        segment = pattern_parts[pattern_index]
        if segment == "**":
            return matches(parts, pattern_index + 1, path_index) or (
                path_index < len(parts) and matches(parts, pattern_index, path_index + 1)
            )
        return (
            path_index < len(parts)
            and fnmatch.fnmatchcase(parts[path_index], segment)
            and matches(parts, pattern_index + 1, path_index + 1)
        )

    yielded = 0
    for dirpath, dirnames, filenames in os.walk(ROOT, topdown=True):
        if limit is not None and yielded >= limit:
            return
        rel_dir = Path(dirpath).relative_to(ROOT)
        if excluded_parts and any(part in excluded_parts for part in rel_dir.parts):
            dirnames[:] = []
            continue

        dirnames[:] = sorted(dirnames)
        filenames = sorted(filenames)

        if excluded_parts:
            dirnames[:] = [dirname for dirname in dirnames if dirname not in excluded_parts]

        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            if safe_repo_match(path, files_only=files_only) is None:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if skip_rel_paths and rel in skip_rel_paths:
                continue
            if matches(tuple(Path(rel).parts)):
                yielded += 1
                yield path
                if limit is not None and yielded >= limit:
                    return


def iter_plain_glob(
    pattern: str,
    excluded_parts: frozenset[str],
    limit: int | None = None,
    *,
    files_only: bool = False,
    skip_rel_paths: set[str] | None = None,
) -> Iterable[Path]:
    """Yield non-recursive glob matches in sorted order without ROOT.glob fanout."""

    parts = pattern.split("/")
    emitted = 0

    def emit(path: Path) -> Iterable[Path]:
        nonlocal emitted
        rel = path.relative_to(ROOT).as_posix()
        if excluded_parts and any(part in excluded_parts for part in Path(rel).parts):
            return
        if skip_rel_paths and rel in skip_rel_paths:
            return
        if safe_repo_match(path, files_only=files_only) is None:
            return
        if limit is not None and emitted >= limit:
            return
        emitted += 1
        yield path

    def walk(base: Path, index: int) -> Iterable[Path]:
        if index >= len(parts):
            if base.exists() and not base.is_symlink():
                yield from emit(base)
            return

        part = parts[index]
        if not part:
            return

        if any(char in part for char in "*?["):
            try:
                candidate_entries = []
                final_segment = index == len(parts) - 1
                for entry in base.iterdir():
                    if entry.is_dir() and entry.is_symlink():
                        continue
                    if excluded_parts and entry.name in excluded_parts:
                        continue
                    if not fnmatch.fnmatchcase(entry.name, part):
                        continue
                    if final_segment and safe_repo_match(entry, files_only=files_only) is None:
                        continue
                    candidate_entries.append(entry)

                key = lambda item: item.relative_to(ROOT).as_posix()
                if final_segment and limit is not None:
                    remaining = max(0, limit - emitted)
                    if skip_rel_paths:
                        candidate_entries = [
                            entry
                            for entry in candidate_entries
                            if entry.relative_to(ROOT).as_posix() not in skip_rel_paths
                        ]
                    entries = heapq.nsmallest(remaining, candidate_entries, key=key)
                else:
                    entries = sorted(candidate_entries, key=key)
            except OSError:
                return
            for entry in entries:
                if limit is not None and emitted >= limit:
                    return
                yield from walk(entry, index + 1)
            return

        if excluded_parts and part in excluded_parts:
            return
        if part == "..":
            return
        next_base = base / part
        if next_base.is_dir() and next_base.is_symlink():
            return
        yield from walk(next_base, index + 1)

    yield from walk(ROOT, 0)


def rel_glob(patterns: Iterable[str], limit: int = MAX_BACKGROUND_SECTION_ITEMS) -> list[str]:
    """Find repository-relative paths matching any of the provided glob patterns."""

    return bounded_rel_glob(patterns, limit=limit)


def parse_git_name_only_output(result: CommandResult) -> list[str] | None:
    """Parse `git diff --name-only -z` output or return None on failure."""

    if result.returncode != 0:
        return None

    return [path for path in result.stdout.split("\0") if path]


def parse_git_status_porcelain_output(result: CommandResult) -> list[str] | None:
    """Parse `git status --porcelain -z` paths or return None on failure."""

    if result.returncode != 0:
        return None

    paths: list[str] = []
    parts = [part for part in result.stdout.split("\0") if part]
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue

        status = entry[:2]
        path = entry[3:]
        if path:
            paths.append(path)

        if "R" in status or "C" in status:
            # With `-z`, rename/copy entries are followed by the original path.
            # The new path above is what matters for guidance self-review checks.
            index += 1

    return paths


def local_changed_files() -> list[str] | None:
    """Return local branch changed files when GitLab MR env is unavailable."""

    source_sha = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "").strip()
    if source_sha and not set(source_sha) <= {"0"}:
        head = source_sha
    else:
        head = os.environ.get("CI_COMMIT_SHA", "HEAD")
    base_refs = [
        ref
        for ref in (
            os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", ""),
            local_default_branch(),
            "origin/master",
        )
        if ref
    ]

    seen_bases: set[str] = set()
    for base_ref in base_refs:
        if base_ref in seen_bases:
            continue
        seen_bases.add(base_ref)

        merge_base = run_command(["git", "merge-base", base_ref, head], timeout=30)
        if merge_base.returncode != 0 or not merge_base.stdout.strip():
            continue

        # Local runs should reflect tracked working-tree edits as well as
        # committed branch changes. CI uses the MR-specific path above.
        result = run_command(
            ["git", "diff", "--name-only", "-z", merge_base.stdout.strip()],
            timeout=30,
        )
        files = parse_git_name_only_output(result)
        if files is not None:
            status = run_command(
                ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                timeout=30,
            )
            status_files = parse_git_status_porcelain_output(status)
            if status_files is not None:
                seen = set(files)
                for path in status_files:
                    if path not in LOCAL_GUIDANCE_STATUS_PATHS:
                        continue
                    if path in seen:
                        continue
                    seen.add(path)
                    files.append(path)
            print(
                f"Using local changed-files fallback against {base_ref}; GitLab MR env is unavailable.",
                file=sys.stderr,
            )
            return files

    return None


def changed_files() -> list[str] | None:
    """Return files changed in the current GitLab merge request.

    Prefer GitLab's MR diff base SHA because it matches the merge request diff
    more closely than a plain two-dot diff against the current target branch.

    Returns ``None`` when no diff strategy succeeded — distinct from an
    empty list (which means "successfully computed, no files changed").
    Callers downstream use the None state to fail closed on guidance/
    accepted-decisions inclusion so an MR cannot self-whitelist by making
    git introspection fail.
    """

    target = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")
    source_sha = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "").strip()
    if source_sha and not set(source_sha) <= {"0"}:
        head = source_sha
    else:
        if os.environ.get("CI_MERGE_REQUEST_EVENT_TYPE") in {
            "merged_result",
            "merge_train",
        }:
            print(
                "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA is unavailable in a merged-result/merge-train pipeline; "
                "refusing to diff the synthetic pipeline commit for review context.",
                file=sys.stderr,
            )
            return None
        head = os.environ.get("CI_COMMIT_SHA", "HEAD")
    diff_base = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")

    if not diff_base and not target:
        local_files = local_changed_files()
        if local_files is not None:
            return local_files

    diff_bases: list[str] = []

    if diff_base:
        diff_bases.append(diff_base)

    if target:
        merge_base = run_command(["git", "merge-base", f"origin/{target}", head], timeout=30)
        if merge_base.returncode == 0 and merge_base.stdout.strip():
            candidate = merge_base.stdout.strip()
            if candidate not in diff_bases:
                diff_bases.append(candidate)

    for base in diff_bases:
        result = run_command(["git", "diff", "--name-only", "-z", base, head], timeout=30)
        files = parse_git_name_only_output(result)
        if files is not None:
            return files

        print(
            f"Failed to compute changed files with diff base {base}; trying next strategy.",
            file=sys.stderr,
        )

    # No HEAD~1 fallback on purpose: on a multi-commit MR it silently
    # returns only the last commit's files, hiding the failure. Surface
    # the error instead.
    print(
        "Failed to compute changed files for MR; downstream code will "
        "treat guidance and accepted-decisions as unavailable to avoid "
        "self-whitelisting an unknown change set.",
        file=sys.stderr,
    )
    return None


def rel_glob_files(
    patterns: Iterable[str],
    limit: int = MAX_BACKGROUND_SECTION_ITEMS,
    exclude_dirs: Iterable[str] | None = None,
) -> list[str]:
    """Find repository-relative files matching any of the provided glob patterns."""

    return bounded_rel_glob(
        patterns,
        limit=limit,
        files_only=True,
        exclude_dirs=exclude_dirs,
    )


def tool_version(binary: str, args: Sequence[str]) -> list[str]:
    """Return the first few version lines for an available local binary."""

    if not shutil.which(binary):
        return []
    result = run_command([binary, *args], timeout=10)
    if not result.stdout:
        return []
    return result.stdout.splitlines()[:8]
