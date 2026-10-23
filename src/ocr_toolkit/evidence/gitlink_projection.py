"""Private, independently checked Git input for OCR 1.13.3 gitlink reviews."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ocr_toolkit.common.git import read_only_git_prefix
from ocr_toolkit.evidence.gitlinks import GitlinkInputPlan
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.ocr_result import TOOLKIT_GITLINK_SELECTION_KEY

_SAFE_CONFIG_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,127}\Z")
_RAW_HEADER = re.compile(
    rb":(?P<old_mode>[0-7]{6}) (?P<new_mode>[0-7]{6}) "
    rb"(?P<old_oid>[0-9a-f]{40}) (?P<new_oid>[0-9a-f]{40}) "
    rb"(?P<status>[AMDRT])(?P<score>[0-9]{0,3})\Z"
)
_ZERO_OID = "0" * 40
_GIT_INPUT_LIMIT = 512_000
_DIFF_OUTPUT_LIMIT = 8_000_000
_GIT_TIMEOUT_SECONDS = 30
_DIFF_ENTRY_LIMIT = 20_000
_GITLINK_SELECTION_SCHEMA = "ocr.gitlink-selection/v1"
_LOCAL_INPUTS = (".gitignore", ".gitmodules", ".gitattributes")
_GIT_METADATA_INPUTS = ("config", "config.worktree", "info/attributes", "info/exclude")
_PREVIEW_REASONS = frozenset(
    {
        "user_exclude",
        "unsupported_ext",
        "default_path",
        "secret_exclude",
        "provider_directory",
        "deleted",
        "binary",
        "too_large",
    }
)


@dataclass(frozen=True, slots=True)
class RawDiffEntry:
    """One complete raw diff record, preserving both tree endpoints."""

    old_path: str | None
    new_path: str | None
    old_mode: str
    new_mode: str
    old_oid: str
    new_oid: str
    status: str

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or ""

    @property
    def preview_status(self) -> str:
        return {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
        }[self.status]

    @property
    def is_gitlink(self) -> bool:
        return "160000" in (self.old_mode, self.new_mode)


@dataclass(frozen=True, slots=True)
class GitlinkProjection:
    """Frozen original identity, projected ordinary diff and consulted inputs."""

    plan: GitlinkInputPlan
    original_diff: tuple[RawDiffEntry, ...]
    ordinary_diff: tuple[RawDiffEntry, ...]
    gitlink_diff: tuple[RawDiffEntry, ...]
    fingerprints: tuple[tuple[str, str], ...]
    line_counts: tuple[tuple[str, int, int], ...]
    environment: tuple[tuple[str, str], ...]
    input_digest: str

    def child_environment(self) -> dict[str, str]:
        return dict(self.environment)


def _read_input(path: Path) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _GIT_INPUT_LIMIT:
        raise RepositoryEvidenceError("OCR local Git input is unsafe or too large")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_ino != metadata.st_ino
            or opened.st_dev != metadata.st_dev
            or opened.st_size > _GIT_INPUT_LIMIT
        ):
            raise RepositoryEvidenceError("OCR local Git input changed or is unsafe")
        payload = os.read(descriptor, _GIT_INPUT_LIMIT + 1)
        if len(payload) > _GIT_INPUT_LIMIT or len(payload) != opened.st_size:
            raise RepositoryEvidenceError("OCR local Git input changed or is too large")
        return payload
    finally:
        os.close(descriptor)


def _input_digest(root: Path, plan: GitlinkInputPlan) -> str:
    paths = {root / path for path in _LOCAL_INPUTS}
    git_dir = root / ".git"
    try:
        git_dir_mode = git_dir.lstat().st_mode
    except OSError as exc:
        raise RepositoryEvidenceError("OCR Git directory is unavailable") from exc
    if not stat.S_ISDIR(git_dir_mode):
        # Linked worktrees have an indirect common configuration; leave this
        # shape closed until both metadata locations can be pinned.
        raise RepositoryEvidenceError("OCR gitlink projection requires a direct Git directory")
    paths.update(git_dir / path for path in _GIT_METADATA_INPUTS)
    for change in plan.ordinary:
        parts = change.path.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            paths.add(root.joinpath(*parts[:depth], ".gitattributes"))
    digest = hashlib.sha256()
    for path in sorted(paths):
        payload = _read_input(path)
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(b"M" if payload is None else b"P")
        if payload is not None:
            if path in {git_dir / "config", git_dir / "config.worktree"} and re.search(
                rb"(?im)^\s*\[\s*include(?:if)?(?:\s|\])",
                payload.removeprefix(b"\xef\xbb\xbf"),
            ):
                raise RepositoryEvidenceError("OCR local Git config includes are unsupported")
            digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def _projection_environment(plan: GitlinkInputPlan) -> dict[str, str]:
    # The same inherited environment is frozen once for preview and production.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "OCR_RAW_LOGGING"
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ATTR_NOSYSTEM": "1",
            "LC_ALL": "C",
        }
    )
    overrides = [
        ("diff.ignoreSubmodules", "all"),
        # OCR uses a temporary HOME, while posting uses the operator's HOME.
        # Keep user/XDG attributes out of both Git projections.
        ("core.attributesFile", os.devnull),
    ]
    for name in plan.config_names:
        if _SAFE_CONFIG_NAME.fullmatch(name) is None or ".." in name or name.endswith("/"):
            raise RepositoryEvidenceError(".gitmodules name is unsafe for OCR Git config")
        overrides.append((f"submodule.{name}.ignore", "all"))
    environment["GIT_CONFIG_COUNT"] = str(len(overrides))
    for index, (key, value) in enumerate(overrides):
        environment[f"GIT_CONFIG_KEY_{index}"] = key
        environment[f"GIT_CONFIG_VALUE_{index}"] = value
    return environment


def _git_output(root: Path, args: list[str], environment: dict[str, str]) -> bytes:
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            [*read_only_git_prefix(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        assert process.stdout is not None and process.stderr is not None
        output = bytearray()
        deadline = time.monotonic() + _GIT_TIMEOUT_SECONDS
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, _GIT_TIMEOUT_SECONDS)
                ready = selector.select(remaining)
                if not ready:
                    raise subprocess.TimeoutExpired(process.args, _GIT_TIMEOUT_SECONDS)
                for key, _ in ready:
                    limit = _DIFF_OUTPUT_LIMIT + 1 - len(output)
                    chunk = os.read(key.fileobj.fileno(), min(65_536, max(1, limit)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif key.data == "stderr":
                        raise RepositoryEvidenceError(
                            "OCR Git diff inventory failed or produced diagnostics"
                        )
                    else:
                        output.extend(chunk)
                        if len(output) > _DIFF_OUTPUT_LIMIT:
                            raise RepositoryEvidenceError(
                                "OCR Git diff inventory exceeded its output limit"
                            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, _GIT_TIMEOUT_SECONDS)
        if process.wait(timeout=remaining) != 0:
            raise RepositoryEvidenceError("OCR Git diff inventory failed or produced diagnostics")
        return bytes(output)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepositoryEvidenceError("OCR Git diff inventory could not complete") from exc
    finally:
        if process is not None:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                process.wait()
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


def _raw_diff(
    root: Path, plan: GitlinkInputPlan, environment: dict[str, str], *, reveal_gitlinks: bool
) -> tuple[RawDiffEntry, ...]:
    args = [
        "diff",
        "--raw",
        "-z",
        "--no-abbrev",
        "--no-ext-diff",
        "--no-textconv",
        "--find-renames",
    ]
    if reveal_gitlinks:
        args.append("--ignore-submodules=none")
    args.extend(["--end-of-options", plan.base_sha, plan.head_sha, "--"])
    raw = _git_output(root, args, environment)
    if not raw:
        return ()
    fields = raw.split(b"\0")
    if fields[-1] != b"":
        raise RepositoryEvidenceError("OCR Git raw diff is truncated")
    fields.pop()
    entries: list[RawDiffEntry] = []
    index = 0
    while index < len(fields):
        if len(entries) >= _DIFF_ENTRY_LIMIT:
            raise RepositoryEvidenceError("OCR Git raw diff exceeds its entry bound")
        match = _RAW_HEADER.fullmatch(fields[index])
        if match is None:
            raise RepositoryEvidenceError("OCR Git raw diff contains an unsupported record")
        status = match.group("status").decode("ascii")
        index += 1
        path_count = 2 if status == "R" else 1
        if index + path_count > len(fields):
            raise RepositoryEvidenceError("OCR Git raw diff is truncated")
        try:
            paths = [field.decode("utf-8") for field in fields[index : index + path_count]]
        except UnicodeDecodeError as exc:
            raise RepositoryEvidenceError("OCR Git raw diff has non-UTF-8 paths") from exc
        index += path_count
        from ocr_toolkit.evidence.repository import normalize_repo_path

        if any(normalize_repo_path(path) != path for path in paths):
            raise RepositoryEvidenceError("OCR Git raw diff path is unsafe")
        entries.append(
            RawDiffEntry(
                None if status == "A" else paths[0],
                None if status == "D" else paths[-1],
                match.group("old_mode").decode("ascii"),
                match.group("new_mode").decode("ascii"),
                match.group("old_oid").decode("ascii"),
                match.group("new_oid").decode("ascii"),
                status,
            )
        )
    return tuple(entries)


def _check_tree_identity(plan: GitlinkInputPlan, entries: tuple[RawDiffEntry, ...]) -> None:
    expected_before = {
        change.path: change.before for change in plan.ordinary if change.before is not None
    }
    expected_after = {
        change.path: change.after for change in plan.ordinary if change.after is not None
    }
    expected_before.update(
        {change.path: change.before_entry for change in plan.changes if change.before_entry}
    )
    expected_after.update(
        {change.path: change.after_entry for change in plan.changes if change.after_entry}
    )
    covered_before: set[str] = set()
    covered_after: set[str] = set()
    for entry in entries:
        for path, expected, mode, oid, covered in (
            (entry.old_path, expected_before, entry.old_mode, entry.old_oid, covered_before),
            (entry.new_path, expected_after, entry.new_mode, entry.new_oid, covered_after),
        ):
            if path is None:
                if mode != "000000" or oid != _ZERO_OID:
                    raise RepositoryEvidenceError("OCR Git raw diff has an invalid absent endpoint")
                continue
            object_entry = expected.get(path)
            if (
                object_entry is None
                or path in covered
                or object_entry.mode != mode
                or object_entry.object_sha != oid
            ):
                raise RepositoryEvidenceError("OCR Git raw diff disagrees with immutable trees")
            covered.add(path)
    if covered_before != set(expected_before) or covered_after != set(expected_after):
        raise RepositoryEvidenceError("OCR Git raw diff omitted an immutable tree change")


def _manifest_id(entry: RawDiffEntry) -> str:
    old_path = entry.old_path or entry.new_path or ""
    identity = "\0".join(("review", "range", old_path, entry.new_path or ""))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def gitlink_selection_proof(
    projection: GitlinkProjection, selected: tuple[RawDiffEntry, ...]
) -> dict[str, object]:
    """Carry only closed, path-free selected identities across DLP projection."""

    fingerprints = dict(projection.fingerprints)
    item_ids = sorted(_manifest_id(entry) for entry in selected)
    if len(item_ids) != len(set(item_ids)) or any(
        item_id not in fingerprints for item_id in item_ids
    ):
        raise RepositoryEvidenceError("OCR gitlink selected identities are ambiguous")
    source_hash = hashlib.sha256()
    for item_id in item_ids:
        for field in (item_id, fingerprints[item_id]):
            raw = field.encode("utf-8")
            source_hash.update(len(raw).to_bytes(8, "big"))
            source_hash.update(raw)
    return {
        "schema_version": _GITLINK_SELECTION_SCHEMA,
        "selected_item_ids": item_ids,
        "source_artifact_sha256": source_hash.hexdigest(),
    }


def selected_gitlink_proof_entries(
    projection: GitlinkProjection, result: dict[str, object]
) -> tuple[RawDiffEntry, ...]:
    """Rebuild DLP-filtered selection from the producer's path-free witness."""

    proof = result.get(TOOLKIT_GITLINK_SELECTION_KEY)
    metadata = result.get("_ocr_toolkit")
    publication = metadata.get("publication") if isinstance(metadata, dict) else None
    original = publication.get("original") if isinstance(publication, dict) else None
    if (
        result.get("status") != "completed_with_errors"
        or result.get("manifest") is not None
        or not isinstance(publication, dict)
        or publication.get("state") != "publication-filtered"
        or not isinstance(proof, dict)
        or set(proof) != {"schema_version", "selected_item_ids", "source_artifact_sha256"}
        or proof.get("schema_version") != _GITLINK_SELECTION_SCHEMA
        or not isinstance(proof.get("selected_item_ids"), list)
        or not isinstance(original, dict)
    ):
        raise RepositoryEvidenceError("OCR gitlink filtered selection proof is invalid")
    item_ids = proof["selected_item_ids"]
    if (
        not item_ids
        or len(item_ids) > _DIFF_ENTRY_LIMIT
        or any(not isinstance(item_id, str) for item_id in item_ids)
        or item_ids != sorted(set(item_ids))
    ):
        raise RepositoryEvidenceError("OCR gitlink filtered selection identities are invalid")
    expected = {_manifest_id(entry): entry for entry in projection.ordinary_diff}
    if len(expected) != len(projection.ordinary_diff) or any(
        item_id not in expected for item_id in item_ids
    ):
        raise RepositoryEvidenceError("OCR gitlink filtered selection differs from Git")
    selected = tuple(expected[item_id] for item_id in item_ids)
    if proof != gitlink_selection_proof(projection, selected):
        raise RepositoryEvidenceError("OCR gitlink filtered selection fingerprint differs from Git")
    if original.get("outcome") != "clean" or any(
        type(original.get(key)) is not int or original[key] != expected_count
        for key, expected_count in (
            ("selected", len(selected)),
            ("completed", len(selected)),
            ("reused", 0),
            ("failed", 0),
            ("waived", 0),
        )
    ):
        raise RepositoryEvidenceError("OCR gitlink filtered original coverage is invalid")
    comments = result.get("comments")
    selected_paths = {entry.path for entry in selected}
    if not isinstance(comments, list) or any(
        not isinstance(comment, dict)
        or not isinstance(comment.get("path"), str)
        or comment["path"] not in selected_paths
        for comment in comments
    ):
        raise RepositoryEvidenceError("OCR gitlink filtered finding is outside selected files")
    return selected


def _patch_fingerprints(
    root: Path,
    plan: GitlinkInputPlan,
    environment: dict[str, str],
    entries: tuple[RawDiffEntry, ...],
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, int, int], ...]]:
    """Reproduce the qualified OCR 1.13.3 raw patch fingerprint from Git."""

    patch = _git_output(
        root,
        [
            "-c",
            "core.quotepath=false",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            "--no-color",
            "-U3",
            "--end-of-options",
            plan.base_sha,
            plan.head_sha,
            "--",
        ],
        environment,
    )
    try:
        text = patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RepositoryEvidenceError("OCR projected patch is not UTF-8") from exc
    sections: list[list[str]] = []
    for raw_line in text.split("\n"):
        line = raw_line.removesuffix("\r")
        if line.startswith("diff --git "):
            sections.append([])
        if sections:
            sections[-1].append(line)
        elif line:
            raise RepositoryEvidenceError("OCR projected patch has unexpected prelude")
    if len(sections) != len(entries):
        raise RepositoryEvidenceError("OCR projected patch disagrees with raw diff")
    fingerprints: list[tuple[str, str]] = []
    line_counts: list[tuple[str, int, int]] = []
    for entry, lines in zip(entries, sections, strict=True):
        old_path = entry.old_path or entry.new_path or ""
        new_path = entry.new_path or entry.old_path or ""
        if lines[0] != f"diff --git a/{old_path} b/{new_path}":
            raise RepositoryEvidenceError("OCR projected patch path is ambiguous")
        in_hunk = False
        insertions = 0
        deletions = 0
        filtered: list[str] = []
        for line in lines:
            if line.startswith("@@"):
                in_hunk = True
            if not in_hunk and line.startswith("index "):
                continue
            if in_hunk and line.startswith("+"):
                insertions += 1
            elif in_hunk and line.startswith("-"):
                deletions += 1
            filtered.append(line)
        diff_text = "\n".join(filtered).rstrip("\r\n")
        fingerprint_source = "\0".join(("range", old_path, new_path, diff_text))
        fingerprints.append(
            (_manifest_id(entry), hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest())
        )
        line_counts.append((entry.path, insertions, deletions))
    if len({item_id for item_id, _ in fingerprints}) != len(fingerprints):
        raise RepositoryEvidenceError("OCR projected patch has duplicate identities")
    return tuple(fingerprints), tuple(line_counts)


def make_gitlink_projection(
    reader: GitRepositoryReader, plan: GitlinkInputPlan
) -> GitlinkProjection:
    """Qualify the original range and freeze exact OCR Git inputs."""

    environment = _projection_environment(plan)
    root = reader.root
    merge_base = (
        _git_output(root, ["merge-base", plan.base_sha, plan.head_sha], environment)
        .decode("ascii")
        .strip()
    )
    if merge_base != plan.base_sha:
        raise RepositoryEvidenceError("OCR range merge-base differs from the planned base")
    input_digest = _input_digest(root, plan)
    unfiltered = _raw_diff(root, plan, environment, reveal_gitlinks=True)
    _check_tree_identity(plan, unfiltered)
    projected = _raw_diff(root, plan, environment, reveal_gitlinks=False)
    ordinary = tuple(entry for entry in unfiltered if not entry.is_gitlink)
    if projected != ordinary:
        raise RepositoryEvidenceError("OCR Git config did not isolate the ordinary diff")
    if any(
        entry.status == "T"
        or entry.old_mode not in {"000000", "100644", "100755"}
        or entry.new_mode not in {"000000", "100644", "100755"}
        for entry in ordinary
    ):
        raise RepositoryEvidenceError("OCR non-regular ordinary change is unsupported")
    fingerprints, line_counts = _patch_fingerprints(root, plan, environment, projected)
    if input_digest != _input_digest(root, plan):
        raise RepositoryEvidenceError("OCR local Git inputs changed during qualification")
    return GitlinkProjection(
        plan,
        unfiltered,
        ordinary,
        tuple(entry for entry in unfiltered if entry.is_gitlink),
        fingerprints,
        line_counts,
        tuple(sorted(environment.items())),
        input_digest,
    )


def verify_gitlink_projection(reader: GitRepositoryReader, projection: GitlinkProjection) -> None:
    """Recheck every original endpoint, consulted input and projected record."""

    from ocr_toolkit.evidence.gitlinks import plan_gitlink_input

    current = plan_gitlink_input(reader, projection.plan.base_sha, projection.plan.head_sha)
    if (
        current != projection.plan
        or _input_digest(reader.root, projection.plan) != projection.input_digest
    ):
        raise RepositoryEvidenceError("OCR gitlink review inputs drifted")
    environment = projection.child_environment()
    if (
        _raw_diff(reader.root, projection.plan, environment, reveal_gitlinks=True)
        != projection.original_diff
    ):
        raise RepositoryEvidenceError("OCR original Git diff changed")
    if (
        _raw_diff(reader.root, projection.plan, environment, reveal_gitlinks=False)
        != projection.ordinary_diff
    ):
        raise RepositoryEvidenceError("OCR projected Git diff changed")
    if _patch_fingerprints(reader.root, projection.plan, environment, projection.ordinary_diff) != (
        projection.fingerprints,
        projection.line_counts,
    ):
        raise RepositoryEvidenceError("OCR projected Git patch changed")


def qualify_gitlink_preview(projection: GitlinkProjection, raw: bytes) -> tuple[RawDiffEntry, ...]:
    """Accept only the complete 1.13.3 preview for the independently proven diff."""

    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryEvidenceError("OCR gitlink preview is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "files",
        "total_insertions",
        "total_deletions",
        "total_files",
        "reviewable_count",
        "excluded_count",
    }:
        raise RepositoryEvidenceError("OCR gitlink preview has an unsupported schema")
    files = payload["files"]
    if not isinstance(files, list) or len(files) != len(projection.ordinary_diff):
        raise RepositoryEvidenceError("OCR gitlink preview omitted or added diff records")
    expected = {entry.path: entry for entry in projection.ordinary_diff}
    counts = {
        path: (insertions, deletions) for path, insertions, deletions in projection.line_counts
    }
    if len(expected) != len(projection.ordinary_diff):
        raise RepositoryEvidenceError("OCR gitlink projection has a duplicate path")
    selected: list[RawDiffEntry] = []
    seen: set[str] = set()
    insertions = 0
    deletions = 0
    for item in files:
        if (
            not isinstance(item, dict)
            or not {
                "path",
                "status",
                "insertions",
                "deletions",
                "will_review",
            }
            <= set(item)
            or set(item)
            - {
                "path",
                "status",
                "insertions",
                "deletions",
                "will_review",
                "exclude_reason",
            }
        ):
            raise RepositoryEvidenceError("OCR gitlink preview file has an unsupported schema")
        path = item["path"]
        if not isinstance(path, str) or path in seen or path not in expected:
            raise RepositoryEvidenceError("OCR gitlink preview has an unknown or duplicate path")
        seen.add(path)
        entry = expected[path]
        if item["status"] != entry.preview_status:
            raise RepositoryEvidenceError("OCR gitlink preview disagrees with Git status")
        for field in ("insertions", "deletions"):
            value = item[field]
            if type(value) is not int or not 0 <= value <= 1_000_000_000:
                raise RepositoryEvidenceError("OCR gitlink preview has invalid line counts")
        if (item["insertions"], item["deletions"]) != counts[path]:
            raise RepositoryEvidenceError("OCR gitlink preview line counts disagree with Git")
        insertions += item["insertions"]
        deletions += item["deletions"]
        will_review = item["will_review"]
        reason = item.get("exclude_reason", "")
        if type(will_review) is not bool or not isinstance(reason, str):
            raise RepositoryEvidenceError("OCR gitlink preview has invalid selection")
        if will_review:
            if reason:
                raise RepositoryEvidenceError(
                    "OCR gitlink preview selection conflicts with exclusion"
                )
            selected.append(entry)
        elif reason not in _PREVIEW_REASONS:
            raise RepositoryEvidenceError("OCR gitlink preview has an unknown exclusion")
    if seen != set(expected):
        raise RepositoryEvidenceError("OCR gitlink preview omitted an ordinary path")
    for field, value in (
        ("total_insertions", insertions),
        ("total_deletions", deletions),
        ("total_files", len(files)),
        ("reviewable_count", len(selected)),
        ("excluded_count", len(files) - len(selected)),
    ):
        if type(payload[field]) is not int or payload[field] != value:
            raise RepositoryEvidenceError("OCR gitlink preview totals are inconsistent")
    return tuple(selected)


def qualify_gitlink_manifest(
    projection: GitlinkProjection,
    selected: tuple[RawDiffEntry, ...],
    result: dict[str, object],
) -> None:
    """Bind native completed coverage to every preview-selected ordinary item."""

    manifest = result.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "ocr.run-manifest/v1":
        raise RepositoryEvidenceError("OCR gitlink result lacks the qualified manifest")
    if result.get("status") != "complete" or manifest.get("terminal_state") != "complete":
        raise RepositoryEvidenceError("OCR gitlink result is not native complete")
    native_input = manifest.get("input")
    if not isinstance(native_input, dict) or any(
        native_input.get(key) != value
        for key, value in (
            ("mode", "range"),
            ("requested_from", projection.plan.base_sha),
            ("requested_head", projection.plan.head_sha),
            ("resolved_base", projection.plan.base_sha),
            ("resolved_head", projection.plan.head_sha),
            ("exact_range", f"{projection.plan.base_sha}..{projection.plan.head_sha}"),
        )
    ):
        raise RepositoryEvidenceError("OCR gitlink manifest has a different review identity")
    execution = manifest.get("execution")
    if not isinstance(execution, dict) or execution.get("ocr_version") != "v1.13.3":
        raise RepositoryEvidenceError("OCR gitlink manifest has an unsupported binary version")
    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict):
        raise RepositoryEvidenceError("OCR gitlink manifest coverage is invalid")
    expected = {_manifest_id(entry): entry for entry in selected}
    fingerprints = dict(projection.fingerprints)
    if len(expected) != len(selected):
        raise RepositoryEvidenceError("OCR gitlink selected identities are ambiguous")
    proof = gitlink_selection_proof(projection, selected)
    if native_input.get("source_artifact_sha256") != proof["source_artifact_sha256"]:
        raise RepositoryEvidenceError("OCR gitlink source artifact differs from the Git patch")
    for key in ("selected", "completed"):
        records = coverage.get(key)
        if not isinstance(records, list) or len(records) != len(expected):
            raise RepositoryEvidenceError("OCR gitlink manifest omitted selected work")
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise RepositoryEvidenceError("OCR gitlink manifest item is invalid")
            item_id = record.get("item_id")
            if not isinstance(item_id, str) or item_id not in expected or item_id in seen:
                raise RepositoryEvidenceError("OCR gitlink manifest item is unexpected")
            seen.add(item_id)
            entry = expected[item_id]
            if (
                record.get("path") != entry.path
                or record.get("old_path", "") != (entry.old_path if entry.status == "R" else "")
                or record.get("fingerprint") != fingerprints.get(item_id)
            ):
                raise RepositoryEvidenceError("OCR gitlink manifest item disagrees with Git")
    for key in ("reused", "failed", "waived"):
        if coverage.get(key) != []:
            raise RepositoryEvidenceError("OCR gitlink manifest contains unreviewed work")
    if manifest.get("run_failure") is not None or manifest.get("parent_run_id"):
        raise RepositoryEvidenceError("OCR gitlink result is not a fresh complete review")
    comments = result.get("comments")
    if not isinstance(comments, list):
        raise RepositoryEvidenceError("OCR gitlink result comments are invalid")
    selected_paths = {entry.path for entry in selected}
    for comment in comments:
        if (
            not isinstance(comment, dict)
            or not isinstance(comment.get("path"), str)
            or comment["path"] not in selected_paths
        ):
            raise RepositoryEvidenceError("OCR gitlink result has a finding outside selected files")


def selected_gitlink_manifest_entries(
    projection: GitlinkProjection, result: dict[str, object]
) -> tuple[RawDiffEntry, ...]:
    """Recover the native selected subset for independent posting readback."""

    manifest = result.get("manifest")
    coverage = manifest.get("coverage") if isinstance(manifest, dict) else None
    records = coverage.get("selected") if isinstance(coverage, dict) else None
    if not isinstance(records, list):
        raise RepositoryEvidenceError("OCR gitlink manifest selected items are unavailable")
    expected = {_manifest_id(entry): entry for entry in projection.ordinary_diff}
    if len(expected) != len(projection.ordinary_diff):
        raise RepositoryEvidenceError("OCR gitlink ordinary identities are ambiguous")
    selected: list[RawDiffEntry] = []
    seen: set[str] = set()
    for record in records:
        item_id = record.get("item_id") if isinstance(record, dict) else None
        if not isinstance(item_id, str) or item_id not in expected or item_id in seen:
            raise RepositoryEvidenceError("OCR gitlink manifest selected item is invalid")
        seen.add(item_id)
        selected.append(expected[item_id])
    return tuple(selected)
