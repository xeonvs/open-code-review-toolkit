"""Isolated OCR execution and controlled temporary Git repositories."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import core


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()[-2000:]
        raise core.CompatibilityError(
            f"contract command failed: {' '.join(command)}: exit {exc.returncode}: {stderr}"
        ) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise core.CompatibilityError(
            f"contract command failed: {' '.join(command)}: {exc}"
        ) from exc
    return completed.stdout


def _isolated_probe_environment(home: Path) -> dict[str, str]:
    """Return a private OCR/Git environment independent of operator configuration."""

    home.mkdir(mode=0o700)
    temp = home / "tmp"
    temp.mkdir(mode=0o700)
    git = shutil.which("git")
    if git is None or not Path(git).is_absolute():
        core._fail("qualification requires an absolute Git executable")
    return {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "NO_PROXY": "127.0.0.1,localhost",
        "PATH": os.pathsep.join((str(Path(git).parent), os.defpath)),
        "TMPDIR": str(temp),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
    }


def _synthetic_repo(directory: Path, env: dict[str, str]) -> tuple[Path, str, str]:
    """Create an immutable two-commit fixture under isolated Git configuration."""

    repo = directory / "synthetic-review"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo, env=env)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=env)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=env)
    target = repo / "example.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo, env=env)
    _run(["git", "commit", "-m", "baseline"], cwd=repo, env=env)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    target.write_text("def value():\n    return 2\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo, env=env)
    _run(["git", "commit", "-m", "change value"], cwd=repo, env=env)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    return repo, base, head
