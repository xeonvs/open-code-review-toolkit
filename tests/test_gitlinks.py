"""Immutable Git evidence for changed submodule pointers."""

from __future__ import annotations

import json
import os
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.gitlink_projection import (
    make_gitlink_projection,
    qualify_gitlink_manifest,
    qualify_gitlink_preview,
    verify_gitlink_projection,
)
from ocr_toolkit.evidence.gitlinks import changed_gitlinks, plan_gitlink_input
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.pre_execution import (
    GITLINK_PROJECTION_UNQUALIFIED,
    GITLINK_STATUS_SCHEMA,
    read_pre_execution_status,
)
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


def _mixed_fixture(root: Path) -> tuple[str, str]:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Synthetic Reviewer")
    _git(root, "config", "user.email", "reviewer@example.invalid")
    (root / "main.py").write_text("value = 1\n", encoding="utf-8")
    (root / "old.py").write_text("old = True\n", encoding="utf-8")
    (root / "gone.py").write_text("gone = True\n", encoding="utf-8")
    _git(root, "add", "main.py", "old.py", "gone.py")
    _git(root, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / "main.py").write_text("value = 2\n", encoding="utf-8")
    (root / "new.py").write_text("new = True\n", encoding="utf-8")
    _git(root, "mv", "old.py", "renamed.py")
    _git(root, "rm", "gone.py")
    _git(root, "add", "main.py", "new.py")
    _git(root, "update-index", "--add", "--cacheinfo", f"160000,{NEW_OID},schema")
    _git(root, "commit", "-qm", "head")
    return base, _git(root, "rev-parse", "HEAD")


def _gitlink_only_fixture(root: Path) -> tuple[str, str]:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Synthetic Reviewer")
    _git(root, "config", "user.email", "reviewer@example.invalid")
    _git(root, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD")
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


@pytest.mark.parametrize("kind", ["added", "updated", "deleted"])
def test_projection_preserves_original_ordinary_diff(tmp_path: Path, kind: str) -> None:
    base, head = _fixture(tmp_path, kind)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    assert len(projection.original_diff) == 2
    assert [entry.path for entry in projection.ordinary_diff] == ["main.php"]
    assert [entry.path for entry in projection.gitlink_diff] == ["schema"]
    assert projection.child_environment()["GIT_CONFIG_KEY_0"] == "diff.ignoreSubmodules"
    verify_gitlink_projection(reader, projection)


def _preview(path: str = "main.php", *, selected: bool = True) -> bytes:
    item: dict[str, object] = {
        "path": path,
        "status": "modified",
        "insertions": 1,
        "deletions": 1,
        "will_review": selected,
    }
    if not selected:
        item["exclude_reason"] = "user_exclude"
    return json.dumps(
        {
            "files": [item],
            "total_insertions": 1,
            "total_deletions": 1,
            "total_files": 1,
            "reviewable_count": int(selected),
            "excluded_count": int(not selected),
        }
    ).encode()


def test_projection_qualifies_exact_preview_and_zero_selection(tmp_path: Path) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    assert qualify_gitlink_preview(projection, _preview()) == projection.ordinary_diff
    assert qualify_gitlink_preview(projection, _preview(selected=False)) == ()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["files"].append(dict(payload["files"][0])),
        lambda payload: payload["files"][0].update(path="schema"),
        lambda payload: payload["files"][0].update(status="added"),
        lambda payload: payload.update(reviewable_count=0),
        lambda payload: payload["files"][0].update(
            exclude_reason="future_reason", will_review=False
        ),
    ],
)
def test_projection_rejects_wrong_preview(tmp_path: Path, mutate: object) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    payload = json.loads(_preview())
    mutate(payload)  # type: ignore[operator]
    with pytest.raises(RepositoryEvidenceError, match="preview"):
        qualify_gitlink_preview(projection, json.dumps(payload).encode())


def test_projection_detects_local_git_input_drift(tmp_path: Path) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    (tmp_path / ".gitignore").write_text("main.php\n", encoding="utf-8")
    with pytest.raises(RepositoryEvidenceError, match="drifted"):
        verify_gitlink_projection(reader, projection)


def test_projection_scrubs_inherited_git_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, head = _fixture(tmp_path, "updated")
    _git(tmp_path, "config", "diff.ignoreSubmodules", "none")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.ignoreSubmodules")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "none")
    monkeypatch.setenv("GIT_WORK_TREE", "/outside")
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "/outside/diff")
    projection = make_gitlink_projection(reader, plan)
    env = projection.child_environment()
    assert env["GIT_CONFIG_COUNT"] == "1"
    assert env["GIT_CONFIG_KEY_0"] == "diff.ignoreSubmodules"
    assert env["GIT_CONFIG_VALUE_0"] == "all"
    assert "GIT_WORK_TREE" not in env and "GIT_EXTERNAL_DIFF" not in env
    assert [entry.path for entry in projection.ordinary_diff] == ["main.php"]


def test_projection_uses_exact_slash_qualified_gitmodules_name(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / ".gitmodules").write_text(
        '[submodule "vendor/schema"]\npath = schema\nurl = https://example.invalid/repo\n',
        encoding="utf-8",
    )
    _git(tmp_path, "add", "main.py", ".gitmodules")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "main.py").write_text("value = 2\n", encoding="utf-8")
    _git(tmp_path, "add", "main.py")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{NEW_OID},schema")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None and plan.config_names == ("vendor/schema",)
    projection = make_gitlink_projection(reader, plan)
    assert projection.child_environment()["GIT_CONFIG_KEY_1"] == "submodule.vendor/schema.ignore"


def test_gitlink_only_projection_has_no_selected_work(tmp_path: Path) -> None:
    base, head = _gitlink_only_fixture(tmp_path)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    assert projection.ordinary_diff == ()
    assert len(projection.gitlink_diff) == 1
    empty_preview = {
        "files": [],
        "total_insertions": 0,
        "total_deletions": 0,
        "total_files": 0,
        "reviewable_count": 0,
        "excluded_count": 0,
    }
    assert qualify_gitlink_preview(projection, json.dumps(empty_preview).encode()) == ()


def test_runner_uses_one_projected_environment_and_skips_empty_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _gitlink_only_fixture(repo)
    reader = GitRepositoryReader(repo)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    preview = {
        "files": [],
        "total_insertions": 0,
        "total_deletions": 0,
        "total_files": 0,
        "reviewable_count": 0,
        "excluded_count": 0,
    }
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        assert kwargs["env"] == projection.child_environment()
        kwargs["stdout"].write(json.dumps(preview).encode())  # type: ignore[union-attr]
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(review_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(
        review_runner,
        "run_review",
        lambda *_args, **_kwargs: pytest.fail("model must not run for gitlink-only input"),
    )
    identity = review_runner.ReviewIdentity(
        source_sha=head,
        policy_sha="a" * 40,
        mr_author_id=None,
        context_mode="off",
        context=None,
        target_sha=base,
        target_protection="local",
    )
    args = ["--from", base, "--to", head, "--format", "json"]
    code, qualification = review_runner._run_background_qualified_review(
        tmp_path / "result.json",
        tmp_path / "stderr.log",
        args,
        ocr_binary="/synthetic/ocr",
        session_home=home,
        artifacts=artifacts,
        refs=review_runner.ReviewRefs(base, head),
        identity=identity,
        projection=projection,
    )
    assert code == 2 and qualification.selected_diff == ()
    assert calls == [["/synthetic/ocr", "review", *args, "--preview"]]
    assert list(home.iterdir()) == []


@pytest.mark.parametrize("drift", [False, True])
def test_runner_rechecks_projection_before_using_frozen_child_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _fixture(repo, "updated")
    reader = GitRepositoryReader(repo)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    calls: list[tuple[str, object]] = []

    def qualify(*_args: object, **_kwargs: object) -> review_runner.BackgroundQualification:
        calls.append(("preview", _kwargs.get("projection")))
        return review_runner.BackgroundQualification(selected_diff=projection.ordinary_diff)

    def verify(*_args: object) -> None:
        calls.append(("recheck", projection))
        if drift:
            raise RepositoryEvidenceError("synthetic drift")

    def production(*_args: object, **kwargs: object) -> int:
        calls.append(("production", kwargs.get("child_environment")))
        return 0

    monkeypatch.setattr(review_runner, "_qualify_review_background", qualify)
    monkeypatch.setattr(review_runner, "verify_gitlink_projection", verify)
    monkeypatch.setattr(review_runner, "run_review", production)
    identity = review_runner.ReviewIdentity(
        source_sha=head,
        policy_sha="a" * 40,
        mr_author_id=None,
        context_mode="off",
        context=None,
        target_sha=base,
        target_protection="local",
    )
    monkeypatch.chdir(repo)
    args = ["--from", base, "--to", head, "--format", "json"]
    if drift:
        with pytest.raises(review_runner.ReviewRunnerError, match="drifted before"):
            review_runner._run_background_qualified_review(
                tmp_path / "result.json",
                tmp_path / "stderr.log",
                args,
                ocr_binary="/synthetic/ocr",
                session_home=home,
                artifacts=artifacts,
                refs=review_runner.ReviewRefs(base, head),
                identity=identity,
                projection=projection,
            )
        assert [call[0] for call in calls] == ["preview", "recheck"]
    else:
        code, qualification = review_runner._run_background_qualified_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            args,
            ocr_binary="/synthetic/ocr",
            session_home=home,
            artifacts=artifacts,
            refs=review_runner.ReviewRefs(base, head),
            identity=identity,
            projection=projection,
        )
        assert code == 0 and qualification.selected_diff == projection.ordinary_diff
        assert calls == [
            ("preview", projection),
            ("recheck", projection),
            ("production", projection.child_environment()),
        ]


def test_projection_rejects_local_git_config_include(tmp_path: Path) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    _git(tmp_path, "config", "include.path", "/tmp/unused-config")
    with pytest.raises(RepositoryEvidenceError, match="includes"):
        make_gitlink_projection(reader, plan)


def test_projection_rejects_changed_symlink_with_gitlink(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Synthetic Reviewer")
    _git(tmp_path, "config", "user.email", "reviewer@example.invalid")
    (tmp_path / "alias.py").symlink_to("first.py")
    _git(tmp_path, "add", "alias.py")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{OLD_OID},schema")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "alias.py").unlink()
    (tmp_path / "alias.py").symlink_to("second.py")
    _git(tmp_path, "add", "alias.py")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{NEW_OID},schema")
    _git(tmp_path, "commit", "-qm", "head")
    head = _git(tmp_path, "rev-parse", "HEAD")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    with pytest.raises(RepositoryEvidenceError, match="non-regular"):
        make_gitlink_projection(reader, plan)


def test_projection_rejects_wrong_manifest_identity_or_reuse(tmp_path: Path) -> None:
    base, head = _fixture(tmp_path, "updated")
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    item_id, fingerprint = projection.fingerprints[0]
    item = {"item_id": item_id, "path": "main.php", "fingerprint": fingerprint}
    import hashlib

    source = hashlib.sha256()
    for field in (item_id, fingerprint):
        raw = field.encode()
        source.update(len(raw).to_bytes(8, "big"))
        source.update(raw)
    payload: dict[str, object] = {
        "status": "complete",
        "comments": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "terminal_state": "complete",
            "input": {
                "mode": "range",
                "requested_from": base,
                "requested_head": head,
                "resolved_base": base,
                "resolved_head": head,
                "exact_range": f"{base}..{head}",
                "source_artifact_sha256": source.hexdigest(),
            },
            "execution": {"ocr_version": "v1.13.3"},
            "coverage": {
                "selected": [item],
                "completed": [item],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }
    qualify_gitlink_manifest(projection, projection.ordinary_diff, payload)
    manifest = payload["manifest"]
    assert isinstance(manifest, dict)
    native_input = manifest["input"]
    assert isinstance(native_input, dict)
    native_input["resolved_head"] = base
    with pytest.raises(RepositoryEvidenceError, match="identity"):
        qualify_gitlink_manifest(projection, projection.ordinary_diff, payload)
    native_input["resolved_head"] = head
    native_input["source_artifact_sha256"] = "0" * 64
    with pytest.raises(RepositoryEvidenceError, match="source artifact"):
        qualify_gitlink_manifest(projection, projection.ordinary_diff, payload)
    native_input["source_artifact_sha256"] = source.hexdigest()
    coverage = manifest["coverage"]
    assert isinstance(coverage, dict)
    bad_item = dict(item, fingerprint="0" * 64)
    coverage["completed"] = [bad_item]
    with pytest.raises(RepositoryEvidenceError, match="disagrees with Git"):
        qualify_gitlink_manifest(projection, projection.ordinary_diff, payload)
    coverage["completed"] = [item]
    coverage["reused"] = [item]
    with pytest.raises(RepositoryEvidenceError, match="unreviewed"):
        qualify_gitlink_manifest(projection, projection.ordinary_diff, payload)


def _move_fixture(tmp_path: Path) -> tuple[str, str]:
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
    return base, head


def test_unique_gitlink_move_keeps_changed_gitmodules_reviewable(tmp_path: Path) -> None:
    base, head = _move_fixture(tmp_path)

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


def test_unqualified_gitlink_writes_versioned_no_model_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _fixture(repo, "updated")
    artifacts = repository_artifacts(repo)
    prepare_artifact_directory(artifacts)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    identity = review_runner.ReviewIdentity(
        source_sha=head,
        policy_sha=base,
        mr_author_id=41,
        context_mode="off",
        context=None,
        target_sha=base,
        target_protection="protected",
        project_id="1",
        merge_request_iid="2",
        diff_base_sha=base,
        diff_start_sha=base,
        diff_head_sha=head,
        diff_version_id=7,
        target_branch="main",
        policy_project_id="1",
        policy_branch="main",
        policy_protection="protected",
        protection_mode="auto",
    )
    code, _qualification = review_runner._run_background_qualified_review(
        tmp_path / "result.json",
        tmp_path / "stderr.log",
        [],
        ocr_binary="/private/ocr",
        session_home=home,
        artifacts=artifacts,
        refs=review_runner.ReviewRefs(base, head),
        identity=identity,
        gitlink_detected=True,
    )
    assert code == 2
    status = read_pre_execution_status(
        artifacts.pre_execution_status,
        expected_diff_base_sha=base,
        expected_source_sha=head,
    )
    assert status.schema_version == GITLINK_STATUS_SCHEMA
    assert status.reason == GITLINK_PROJECTION_UNQUALIFIED
    assert status.repository_coverage is None


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


@pytest.mark.parametrize("kind", ["added", "updated", "deleted", "mixed", "move"])
def test_installed_ocr_projected_review_matches_native_manifest(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opt-in production proof against the official binary and local fake provider."""

    binary = os.environ.get("OCR_GITLINK_QUALIFY_BINARY")
    if binary is None:
        pytest.skip("set OCR_GITLINK_QUALIFY_BINARY to the checksum-verified OCR 1.13.3")
    assert validate_ocr_binary(executable=binary, announce=False) == "1.13.3"
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from ocr_compat import _stub_gateway

    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = (
        _mixed_fixture(repo)
        if kind == "mixed"
        else _move_fixture(repo)
        if kind == "move"
        else _fixture(repo, kind)
    )
    reader = GitRepositoryReader(repo)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    home = tmp_path / "ocr-home"
    home.mkdir(mode=0o700)
    env = projection.child_environment()
    env["HOME"] = str(home)
    args = [
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
        "--concurrency",
        "1",
    ]
    preview = subprocess.run(
        [*args, "--preview"],
        cwd=repo,
        env=env,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert preview.returncode == 0 and preview.stderr == b""
    selected = qualify_gitlink_preview(projection, preview.stdout)
    assert selected
    assert all(entry.status != "D" for entry in selected)
    if kind in {"added", "updated", "deleted"}:
        assert selected == projection.ordinary_diff
    with _stub_gateway() as gateway:
        env.update(
            {
                "OCR_LLM_URL": gateway,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        production = subprocess.run(
            args,
            cwd=repo,
            env=env,
            capture_output=True,
            check=False,
            timeout=90,
        )
    assert production.returncode == 0 and production.stderr == b""
    qualify_gitlink_manifest(projection, selected, json.loads(production.stdout))
    verify_gitlink_projection(reader, projection)


@pytest.mark.parametrize("kind", ["updated", "only"])
def test_installed_ocr_toolkit_local_gitlink_route(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the toolkit and real OCR together without a paid model or forge."""

    binary = os.environ.get("OCR_GITLINK_QUALIFY_BINARY")
    if binary is None:
        pytest.skip("set OCR_GITLINK_QUALIFY_BINARY to the checksum-verified OCR 1.13.3")
    assert validate_ocr_binary(executable=binary, announce=False) == "1.13.3"
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import http.server
    import threading

    from ocr_compat import _StubHandler

    from ocr_toolkit import cli, provider_config

    class EvidenceStub(_StubHandler):
        request_count = 0
        request_stages: list[str] = []
        issued_evidence = False

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            request = json.loads(raw)
            tools = request.get("tools", [])
            names = {
                function["name"]
                for tool in tools
                if isinstance(tool, dict)
                if isinstance((function := tool.get("function")), dict)
                if isinstance(function.get("name"), str)
            }
            if "ocr_toolkit_evidence" not in names or "approve_all_comments" in names:
                self.rfile = BytesIO(raw)
                super().do_POST()
                return
            cls = type(self)
            cls.request_count += 1
            if not cls.issued_evidence:
                cls.issued_evidence = True
                cls.request_stages.append("evidence")
                function = {"name": "ocr_toolkit_evidence", "arguments": '{"action":"summary"}'}
                call_id = "call-evidence"
            else:
                cls.request_stages.append("done")
                function = {"name": "task_done", "arguments": "{}"}
                call_id = "call-done"
            payload = json.dumps(
                {
                    "id": "toolkit-gitlink-proof",
                    "object": "chat.completion",
                    "model": "synthetic-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": call_id,
                                        "type": "function",
                                        "function": function,
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            self.close_connection = True

    repo = tmp_path / "repo"
    repo.mkdir()
    base, head = _gitlink_only_fixture(repo) if kind == "only" else _fixture(repo, kind)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ocr").symlink_to(binary)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-token")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("OCR_LLM_PROTOCOL", "openai")
    monkeypatch.setenv("OCR_TELEMETRY_ENABLED", "false")
    monkeypatch.setenv("OCR_REVIEW_CONTEXT_MODE", "off")
    monkeypatch.setenv("OCR_REVIEW_PROGRESS", "false")
    # The product continues to require HTTPS. This disposable in-process fixture
    # admits only its own loopback server so OCR can use an HTTP fake provider.
    original_url_parser = provider_config._parse_https_url

    def local_url_parser(value: str, name: str):  # type: ignore[no-untyped-def]
        if value == local_url:
            return urlsplit(value)
        return original_url_parser(value, name)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), EvidenceStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    local_url = f"http://127.0.0.1:{server.server_port}/v1"
    monkeypatch.setenv("OCR_LLM_URL", local_url)
    monkeypatch.setattr(provider_config, "_parse_https_url", local_url_parser)
    monkeypatch.chdir(repo)
    result = tmp_path / "review.json"
    stderr = tmp_path / "review.stderr"
    report = tmp_path / "review.md"
    try:
        code = cli.main(
            [
                "review",
                "--local",
                "--result",
                str(result),
                "--stderr",
                str(stderr),
                "--report",
                str(report),
                "--",
                "--from",
                base,
                "--to",
                head,
                "--concurrency",
                "1",
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    if kind == "only":
        assert code == 2
        assert EvidenceStub.request_count == 0
        assert "no ordinary files" in report.read_text(encoding="utf-8").lower()
    else:
        assert code == 0, stderr.read_text(encoding="utf-8")[:2000]
        assert EvidenceStub.issued_evidence
        assert "evidence" in EvidenceStub.request_stages
        assert "partial" in report.read_text(encoding="utf-8").lower()
        payload = json.loads(result.read_text(encoding="utf-8"))
        assert payload["status"] == "complete"
