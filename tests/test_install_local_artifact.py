"""Tests for the hash-locked local artifact installer."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).parents[1] / "scripts" / "install_local_artifact.py"
REGISTRY_VERIFIER = Path(__file__).parents[1] / "scripts" / "verify_registry_artifacts.sh"
INSTALLED_SMOKE = Path(__file__).parents[1] / "scripts" / "installed_runtime_smoke.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("install_local_artifact_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_script()


def test_writes_exact_hash_locked_requirement(monkeypatch, tmp_path: Path) -> None:
    artifact = tmp_path / "synthetic.tar.gz"
    artifact.write_bytes(b"synthetic distribution")
    requirements = tmp_path / "requirements.txt"
    calls: list[tuple[list[str], bool]] = []

    monkeypatch.setattr(
        installer.subprocess, "run", lambda command, check: calls.append((command, check))
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--python",
            "/tmp/venv/bin/python",
            "--artifact",
            str(artifact),
            "--requirements",
            str(requirements),
        ],
    )

    assert installer.main() == 0
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert requirements.read_text(encoding="utf-8") == (
        f"{artifact.resolve().as_uri()} --hash=sha256:{digest}\n"
    )
    assert calls == [
        (
            [
                "/tmp/venv/bin/python",
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "--no-deps",
                "--requirement",
                str(requirements),
            ],
            True,
        )
    ]


def test_registry_verifier_uses_locked_binary_dependencies_and_runtime_smoke() -> None:
    verifier = REGISTRY_VERIFIER.read_text(encoding="utf-8")

    assert verifier.count("--require-hashes --only-binary=:all:") == 2
    assert verifier.count("--index-url https://pypi.org/simple") == 2
    assert verifier.count('bin/pip" check') == 2
    assert verifier.count("scripts/installed_runtime_smoke.py") == 2
    assert verifier.count("env -u PYTHONPATH") == 2
    assert verifier.count('bin/python" -I') == 2


def test_installed_runtime_smoke_is_self_contained() -> None:
    smoke = INSTALLED_SMOKE.read_text(encoding="utf-8")

    assert "tests." not in smoke
    assert "from ocr_toolkit.federation import admission" in smoke
    assert '"--peer"' in smoke
    assert "asyncio.timeout(30)" in smoke
    assert "client.list_tools()" in smoke
    assert 'client.call_tool("synthetic__schema_probe"' in smoke
