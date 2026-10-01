"""Committed dependency graphs and reviewed action pins are execution inputs."""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def test_workflows_consume_locked_environments_without_implicit_resolution() -> None:
    for name in (
        "ci.yml",
        "build.yml",
        "security.yml",
        "release.yml",
        "testpypi.yml",
        "ocr-compatibility.yml",
    ):
        text = (ROOT / ".github/workflows" / name).read_text()
        assert "uv sync --frozen" not in text, name
        assert not re.search(r"uv run (?!\-\-no-sync\b)", text), name
        for pin in re.findall(r"uses: astral-sh/setup-uv@(\S+)", text):
            assert re.fullmatch(r"[0-9a-f]{40}", pin), (name, pin)
    release = (ROOT / ".github/workflows/release.yml").read_text()
    assert release.index("uv sync --locked") < release.index("uv run --no-sync")
    updater = (ROOT / ".github/dependabot.yml").read_text()
    assert "package-ecosystem: uv" in updater
    assert "package-ecosystem: pip" not in updater


def test_stale_manifest_fails_before_commands_and_checked_run_preserves_lock(
    tmp_path: Path,
) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required to verify the committed-graph boundary")
    manifest = tmp_path / "pyproject.toml"
    dependency = tmp_path / "probe"
    dependency.mkdir()
    (dependency / "pyproject.toml").write_text(
        '[project]\nname = "locked-probe"\nversion = "0.1.0"\n[tool.uv]\npackage = false\n'
    )
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "pyproject.toml").write_text(
        '[project]\nname = "locked-extra"\nversion = "0.1.0"\n[tool.uv]\npackage = false\n'
    )
    manifest.write_text(
        '[project]\nname = "lock-boundary-fixture"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = ["locked-probe>=0.1.0"]\n[tool.uv.sources]\nlocked-probe = { path = "probe" }\nlocked-extra = { path = "extra" }\n'
    )
    environment = {
        **os.environ,
        "UV_PYTHON": sys.executable,
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PROJECT_ENVIRONMENT": str(tmp_path / ".venv"),
    }

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [uv, *args, "--offline"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    locked = run("lock")
    assert locked.returncode == 0, locked.stderr
    synced = run("sync", "--locked")
    assert synced.returncode == 0, synced.stderr
    lock = tmp_path / "uv.lock"
    before = hashlib.sha256(lock.read_bytes()).digest()
    executed = subprocess.run(
        [uv, "run", "--no-sync", "python", "-c", 'print("checked-environment")'],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.strip() == "checked-environment"
    assert hashlib.sha256(lock.read_bytes()).digest() == before
    manifest.write_text(
        manifest.read_text().replace(
            '["locked-probe>=0.1.0"]', '["locked-probe>=0.1.0", "locked-extra>=0.1.0"]'
        )
    )
    rejected = run("sync", "--locked")
    assert rejected.returncode != 0
    assert "lockfile" in rejected.stderr.lower() and "--locked" in rejected.stderr
    assert hashlib.sha256(lock.read_bytes()).digest() == before
