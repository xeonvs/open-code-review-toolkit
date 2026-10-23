"""Immutable Git evidence for changed submodule pointers."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.gitlinks import changed_gitlinks, plan_gitlink_input
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.preflight import validate_ocr_binary

OLD_OID = "1" * 40
NEW_OID = "2" * 40


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip()


def _fixture(root: Path, kind: str) -> tuple[str, str]:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Synthetic Reviewer")
    _git(root, "config", "user.email", "reviewer@example.invalid")
    (root / "main.php").write_text("<?php\n$limit = 1;\n", encoding="utf-8")
    _git(root, "add", "main.php")
    if kind != "added":
        _git(root, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / "main.php").write_text("<?php\n$limit = 2;\n", encoding="utf-8")
    _git(root, "add", "main.php")
    if kind == "deleted":
        _git(root, "update-index", "--force-remove", "schema")
    else:
        _git(root, "update-index", "--add", "--cacheinfo", f"160000,{NEW_OID},schema")
    _git(root, "commit", "-qm", "head")
    return base, _git(root, "rev-parse", "HEAD")


@pytest.mark.parametrize("kind", ["added", "updated", "deleted"])
def test_changed_gitlinks_use_immutable_tree_modes_with_ordinary_file(
    tmp_path: Path, kind: str
) -> None:
    base, head = _fixture(tmp_path, kind)
    changes = changed_gitlinks(GitRepositoryReader(tmp_path), base, head)
    assert len(changes) == 1
    assert changes[0].path == "schema"
    assert changes[0].kind == kind
    assert changes[0].before_oid == (None if kind == "added" else OLD_OID)
    assert changes[0].after_oid == (None if kind == "deleted" else NEW_OID)
    assert _git(tmp_path, "cat-file", "-t", f"{head}:main.php") == "blob"
    for oid in (OLD_OID, NEW_OID):
        assert (
            subprocess.run(
                ["git", "-C", str(tmp_path), "cat-file", "-e", oid],
                check=False,
                capture_output=True,
                timeout=15,
            ).returncode
            != 0
        )


def test_unchanged_gitlink_is_not_reported(tmp_path: Path) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    assert changed_gitlinks(reader, head, head) == ()
    with pytest.raises(RepositoryEvidenceError, match="immutable commit IDs"):
        changed_gitlinks(reader, "HEAD~1", head)
    assert changed_gitlinks(reader, base, head)[0].kind == "updated"


@pytest.mark.parametrize("kind", ["added", "updated", "deleted"])
def test_private_input_plan_retains_original_ordinary_delta(tmp_path: Path, kind: str) -> None:
    base, head = _fixture(tmp_path, kind)
    plan = plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)
    assert plan is not None
    assert plan.base_sha == base and plan.head_sha == head
    assert plan.counts[kind] == 1
    assert plan.config_names == ()
    assert [change.path for change in plan.ordinary] == ["main.php"]
    assert plan.ordinary[0].before is not None
    assert plan.ordinary[0].after is not None


def test_unique_gitlink_move_keeps_changed_gitmodules_reviewable(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    (tmp_path / "main.php").write_text("<?php\n$limit = 1;\n", encoding="utf-8")
    (tmp_path / ".gitmodules").write_text(
        '[submodule "example"]\npath = schema-old\nurl = https://example.invalid/repo\nignore = none\n',
        encoding="utf-8",
    )
    _git(tmp_path, "add", "main.php", ".gitmodules")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema-old")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "main.php").write_text("<?php\n$limit = 2;\n", encoding="utf-8")
    (tmp_path / ".gitmodules").write_text(
        '[submodule "example"]\npath = schema-new\nurl = https://example.invalid/repo\nignore = none\n',
        encoding="utf-8",
    )
    _git(tmp_path, "add", "main.php", ".gitmodules")
    _git(tmp_path, "update-index", "--force-remove", "schema-old")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema-new")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")

    plan = plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)
    assert plan is not None
    assert plan.moves == (("schema-old", "schema-new"),)
    assert plan.counts == {"added": 0, "updated": 0, "deleted": 0, "moved": 1}
    assert plan.config_names == ("example",)
    assert [change.path for change in plan.ordinary] == [".gitmodules", "main.php"]


@pytest.mark.parametrize("to_gitlink", [True, False])
def test_same_path_type_transition_is_not_a_pure_pointer(tmp_path: Path, to_gitlink: bool) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    if to_gitlink:
        (tmp_path / "schema").write_text("ordinary\n", encoding="utf-8")
        _git(tmp_path, "add", "schema")
    else:
        _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    if to_gitlink:
        _git(tmp_path, "update-index", "--cacheinfo", f"160000,{NEW_OID},schema")
    else:
        (tmp_path / "schema").write_text("ordinary\n", encoding="utf-8")
        _git(tmp_path, "add", "schema")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")

    change = changed_gitlinks(GitRepositoryReader(tmp_path), base, head)[0]
    assert change.kind == "transition"
    assert change.before_entry is not None and change.after_entry is not None
    assert {change.before_entry.mode, change.after_entry.mode} == {"100644", "160000"}
    with pytest.raises(RepositoryEvidenceError, match="type transition"):
        plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)


def test_directory_to_gitlink_transition_is_rejected(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "part.py").write_text("value = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "schema/part.py")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "rm", "-q", "--cached", "schema/part.py")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{NEW_OID},schema")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RepositoryEvidenceError, match="directory transition"):
        plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)


def test_gitlink_to_directory_transition_is_rejected(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "update-index", "--force-remove", "schema")
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "part.py").write_text("value = 2\n", encoding="utf-8")
    _git(tmp_path, "add", "schema/part.py")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RepositoryEvidenceError, match="directory transition"):
        plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (
            '[submodule "one"]\npath = schema\n[submodule "two"]\npath = schema\n',
            "path is ambiguous",
        ),
        ("[include]\npath = ../ignored.conf\n", "includes are unsupported"),
        ('[submodule "one"]\npath = ../outside\n', "normalized and relative"),
    ],
)
def test_untrusted_gitmodules_cannot_authorize_projection(
    tmp_path: Path, content: str, error: str
) -> None:
    base, _head = _fixture(tmp_path, "updated")
    (tmp_path / ".gitmodules").write_text(content, encoding="utf-8")
    _git(tmp_path, "add", ".gitmodules")
    _git(tmp_path, "commit", "-qm", "untrusted mapping")
    head = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RepositoryEvidenceError, match=error):
        plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)


def test_ambiguous_gitlink_move_pairing_is_rejected(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    for path in ("old-a", "old-b"):
        _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},{path}")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    for path in ("old-a", "old-b"):
        _git(tmp_path, "update-index", "--force-remove", path)
    for path in ("new-a", "new-b"):
        _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},{path}")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")
    with pytest.raises(RepositoryEvidenceError, match="ambiguous"):
        plan_gitlink_input(GitRepositoryReader(tmp_path), base, head)


@pytest.mark.parametrize("kind", ["added", "updated", "deleted"])
def test_changed_gitlink_closes_preview_before_model(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _fixture(repo, kind)
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    calls: list[str] = []
    monkeypatch.setattr(
        review_runner,
        "_qualify_review_background",
        lambda *_args, **_kwargs: calls.append("preview"),
    )
    monkeypatch.setattr(
        review_runner,
        "run_review",
        lambda *_args, **_kwargs: calls.append("model"),
    )
    identity = review_runner.ReviewIdentity(head, base, None, "off", None, base, "local")
    code, _qualification = review_runner._run_background_qualified_review(
        tmp_path / "result.json",
        tmp_path / "stderr.log",
        [],
        ocr_binary="/private/ocr",
        session_home=home,
        artifacts=artifacts,
        refs=review_runner.ReviewRefs(base, head),
        identity=identity,
        gitlink_detected=bool(changed_gitlinks(GitRepositoryReader(repo), base, head)),
    )
    assert code == 2 and calls == []
    assert not artifacts.pre_execution_status.exists()


@pytest.mark.parametrize("kind", ["added", "updated", "deleted"])
def test_installed_ocr_gitlink_preview_qualification(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opt-in real-binary probe; CI may not have a verified installed OCR."""

    binary = os.environ.get("OCR_GITLINK_QUALIFY_BINARY")
    if binary is None:
        pytest.skip("set OCR_GITLINK_QUALIFY_BINARY to the verified OCR executable")
    validated = validate_ocr_binary(executable=binary, announce=False)
    assert validated
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _fixture(repo, kind)
    private_home = tmp_path / "ocr-home"
    private_home.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(private_home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    completed = subprocess.run(
        [
            binary,
            "review",
            "--from",
            base,
            "--to",
            head,
            "--format",
            "json",
            "--audience",
            "agent",
            "--preview",
        ],
        cwd=repo,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0
    assert len(completed.stdout) <= 2_000_000
    assert len(completed.stderr) <= 100_000
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    records = payload.get("files")
    assert isinstance(records, list)
    assert sum(isinstance(item, dict) and item.get("path") == "main.php" for item in records) == 1
    assert sum(isinstance(item, dict) and item.get("path") == "schema" for item in records) == 1
    ordinary = next(item for item in records if item["path"] == "main.php")
    gitlink = next(item for item in records if item["path"] == "schema")
    assert ordinary["will_review"] is True
    assert gitlink["will_review"] is (kind != "deleted")
    if kind == "deleted":
        assert gitlink["exclude_reason"] == "deleted"
        assert completed.stderr == b""
    else:
        assert completed.stderr.startswith(b"[ocr] WARNING: cannot read file schema at ref ")
        assert completed.stderr.endswith(b": exit status 128\n")
    assert changed_gitlinks(GitRepositoryReader(repo), base, head)[0].kind == kind
