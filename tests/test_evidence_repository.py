"""Integration tests for immutable ref-aware repository evidence reads."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit.evidence import RefRole
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.project import render_bootstrap, render_json
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    build_file_snapshot,
    file_deltas,
    normalize_repo_path,
)


def git(root: Path, *args: str) -> str:
    """Run one deterministic Git command in a synthetic repository."""

    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Synthetic Author",
        "GIT_AUTHOR_EMAIL": "author@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Committer",
        "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    }
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
    )
    return result.stdout.strip()


def synthetic_repository(tmp_path: Path) -> tuple[Path, str, str]:
    """Build two commits containing add, delete, rename, and symlink cases."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    (root / "removed.txt").write_text("removed\n", encoding="utf-8")
    (root / "renamed.txt").write_text("renamed\n", encoding="utf-8")
    (root / "changed.txt").write_text("before\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")

    (root / "removed.txt").unlink()
    (root / "changed.txt").write_text("after\n", encoding="utf-8")
    git(root, "mv", "renamed.txt", "moved.txt")
    (root / "added.txt").write_text("added\n", encoding="utf-8")
    (root / "outside-link").symlink_to("/etc/passwd")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    return root, base, head


@pytest.mark.parametrize(
    "path", ["", "/etc/passwd", "../escape", "safe/../escape", "./file", "-option", "a\\b"]
)
def test_normalize_repo_path_rejects_unsafe_values(path: str) -> None:
    """Keep model-controlled paths outside Git option and traversal syntax."""

    with pytest.raises(RepositoryEvidenceError):
        normalize_repo_path(path)


def test_reader_builds_immutable_snapshots_and_explicit_deltas(tmp_path: Path) -> None:
    """Read both commits without checking either commit out or mutating the worktree."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    changed = reader.changed_paths(base_sha, head_sha)

    assert changed == (
        "added.txt",
        "changed.txt",
        "moved.txt",
        "outside-link",
        "removed.txt",
        "renamed.txt",
    )
    base = build_file_snapshot(reader, base_sha, RefRole.BASE, paths=changed)
    head = build_file_snapshot(reader, head_sha, RefRole.HEAD, paths=changed)
    deltas = file_deltas(base, head)

    assert base.commit_sha == base_sha
    assert head.commit_sha == head_sha
    assert {(item.identity, item.change) for item in deltas} == {
        ("added.txt", "added"),
        ("changed.txt", "changed"),
        ("moved.txt", "added"),
        ("outside-link", "added"),
        ("removed.txt", "removed"),
        ("renamed.txt", "removed"),
    }
    assert head.diagnostics == ("symlink not followed: outside-link",)
    assert (root / "changed.txt").read_text(encoding="utf-8") == "after\n"


def test_reader_refuses_symlink_content_and_reads_old_regular_blob(tmp_path: Path) -> None:
    """Allow commit-addressed regular files while never following repository links."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)

    assert reader.read_blob(base_sha, "changed.txt") == b"before\n"
    assert reader.read_blob(head_sha, "changed.txt") == b"after\n"
    assert reader.read_blob(head_sha, "missing.txt") is None
    with pytest.raises(RepositoryEvidenceError, match="symlink"):
        reader.read_blob(head_sha, "outside-link")


def test_reader_reports_missing_objects_without_fetching(tmp_path: Path) -> None:
    """Treat unavailable shallow-clone objects as explicit local errors."""

    root, _base_sha, _head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)

    with pytest.raises(RepositoryEvidenceError, match="unavailable locally"):
        reader.resolve_commit("f" * 40)


def test_reader_enforces_blob_and_tree_bounds(tmp_path: Path) -> None:
    """Reject over-limit content before loading it into memory."""

    root, _base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root, max_file_bytes=4)

    with pytest.raises(RepositoryEvidenceError, match="exceeds 4 bytes"):
        reader.read_blob(head_sha, "changed.txt")
    with pytest.raises(RepositoryEvidenceError, match="entry limit"):
        reader.list_objects(head_sha, max_entries=1)


def test_collector_and_projections_preserve_legacy_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the legacy facts queryable while the compact bootstrap remains small."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", base_sha)
    monkeypatch.setenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", head_sha)
    monkeypatch.chdir(root)

    store = collect_repository_evidence(root)
    bootstrap = render_bootstrap(store)
    serialized = render_json(store)

    assert store.base and store.base.commit_sha == base_sha
    assert store.head and store.head.commit_sha == head_sha
    assert any(record.kind == "repository.context" for record in store.records)
    assert not any(
        record.provenance.startswith("legacy.") and record.kind != "repository.context"
        for record in store.records
    )
    assert "# Repository evidence bootstrap" in bootstrap
    assert "ocr_toolkit_evidence" in bootstrap
    assert "legacy-background.md" not in bootstrap
    assert len(bootstrap) <= 4_000
    assert serialized == store.to_json()


def test_bootstrap_truncation_is_explicit() -> None:
    """Never make compact-output clipping indistinguishable from complete coverage."""

    from ocr_toolkit.evidence import EvidenceStore

    store = EvidenceStore(diagnostics=["x" * 900])
    bootstrap = render_bootstrap(store, max_chars=400, max_bytes=1024)

    assert len(bootstrap) <= 400
    assert len(bootstrap.encode("utf-8")) <= 1024
    assert "bootstrap truncated" in bootstrap
