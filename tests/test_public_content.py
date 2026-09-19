"""Exercise public-content scanning through real Git index and filesystem state."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/public_content.py"


def run_scan(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--privacy-only", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def repository(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)


def stage(root: Path) -> None:
    subprocess.run(["git", "add", "--all"], cwd=root, check=True)


def test_index_cannot_be_hidden_by_clean_worktree(tmp_path: Path) -> None:
    repository(tmp_path)
    private = "/" + "Users" + "/synthetic-owner/private.txt"
    (tmp_path / "note.md").write_text(private)
    stage(tmp_path)
    (tmp_path / "note.md").write_text("safe content")
    result = run_scan(tmp_path, "--staged")
    assert result.returncode == 1
    assert private not in result.stdout
    assert json.loads(result.stdout)["findings"] == [
        {"category": "user_profile_path", "file": "note.md", "line": 1}
    ]
    assert run_scan(tmp_path).returncode == 0


def test_tree_includes_untracked_but_not_ignored_files(tmp_path: Path) -> None:
    repository(tmp_path)
    (tmp_path / ".gitignore").write_text("private-cache/\n")
    cache = tmp_path / "private-cache"
    cache.mkdir()
    private = "/" + "home" + "/synthetic-owner/private.txt"
    (cache / "ignored").write_text(private)
    assert run_scan(tmp_path).returncode == 0
    (tmp_path / "public.txt").write_text(private)
    assert run_scan(tmp_path).returncode == 1


def test_symlinks_are_not_followed_and_targets_are_scanned(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    repository(root)
    outside = tmp_path / "outside"
    outside.write_text("not copied into snapshot")
    (root / "link").symlink_to(outside)
    assert run_scan(root).returncode == 0
    (root / "link").unlink()
    (root / "link").symlink_to("/" + "Users" + "/synthetic-owner/missing")
    assert run_scan(root).returncode == 1


def test_path_forms_and_safe_placeholders(tmp_path: Path) -> None:
    repository(tmp_path)
    (tmp_path / "safe").write_text('f"file:' + '//{remote}" /tmp/work ${HOME}/work\n')
    assert run_scan(tmp_path).returncode == 0
    (tmp_path / "unsafe").write_text("C:" + os.sep.replace("/", "\\") + "Users\\sample\\work")
    assert run_scan(tmp_path).returncode == 1
    (tmp_path / "unsafe").write_text("file:" + "///tmp/work")
    assert run_scan(tmp_path).returncode == 1
