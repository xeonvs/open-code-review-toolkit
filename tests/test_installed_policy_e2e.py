"""Installed wheel and sdist-to-wheel policy/MCP integration contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import venv
from pathlib import Path

import pytest

from tests.support import PROJECT_ROOT

HELPER = PROJECT_ROOT / "tests" / "installed_policy_e2e.py"
ARTIFACT_VERSION = "0.0.dev0"


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    """Run one bounded integration command and return its standard output."""

    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert completed.returncode == 0, (
        f"command failed ({completed.returncode}): {command!r}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return completed.stdout


@pytest.fixture(scope="module")
def installed_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build a direct wheel and a wheel rebuilt from the local source distribution."""

    root = tmp_path_factory.mktemp("installed-policy-artifacts")
    direct = root / "direct"
    source = root / "source"
    rebuilt = root / "rebuilt"
    direct.mkdir()
    source.mkdir()
    rebuilt.mkdir()
    environment = dict(os.environ)
    environment.update(
        {
            "SETUPTOOLS_SCM_PRETEND_VERSION": ARTIFACT_VERSION,
            "SOURCE_DATE_EPOCH": _run(
                ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=PROJECT_ROOT
            ).strip(),
        }
    )
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(direct),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
    )
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--sdist",
            "--outdir",
            str(source),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
    )
    sdist = next(source.glob("*.tar.gz"))
    extracted = root / "extracted"
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(extracted, filter="data")
    source_root = next(path for path in extracted.iterdir() if path.is_dir())
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(rebuilt),
        ],
        cwd=source_root,
        env=environment,
    )
    return next(direct.glob("*.whl")), next(rebuilt.glob("*.whl"))


def test_installed_wheel_and_sdist_expose_target_policy_through_real_mcp(
    installed_artifacts: tuple[Path, Path], tmp_path: Path
) -> None:
    """Prove both package paths under hostile imports, private state, and stdio MCP."""

    git_binary = shutil.which("git")
    assert git_binary is not None
    for label, artifact in zip(("wheel", "sdist"), installed_artifacts, strict=True):
        root = tmp_path / label
        root.mkdir(mode=0o700)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        binary_directory = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binary_directory / ("python.exe" if os.name == "nt" else "python")
        cli = binary_directory / ("ocr-ci.exe" if os.name == "nt" else "ocr-ci")
        _run(
            [str(python), "-m", "pip", "install", "--no-deps", str(artifact)],
            cwd=root,
        )
        _run([str(python), "-m", "pip", "check"], cwd=root)
        installed_version = _run(
            [str(python), "-I", "-c", "import ocr_toolkit; print(ocr_toolkit.__version__)"],
            cwd=root,
            env={"HOME": str(root), "PATH": ""},
        ).strip()
        assert installed_version == ARTIFACT_VERSION
        version_text = _run(
            [str(cli), "--version"],
            cwd=root,
            env={"HOME": str(root), "PATH": str(binary_directory)},
        )
        assert version_text.strip() == f"ocr-ci {ARTIFACT_VERSION}"
        help_text = _run(
            [str(cli), "--help"],
            cwd=root,
            env={"HOME": str(root), "PATH": str(binary_directory)},
        )
        assert "review" in help_text and "post" in help_text
        protocol_environment = {
            "HOME": str(root / "home"),
            "PATH": os.pathsep.join(
                dict.fromkeys((str(Path(git_binary).parent), "/usr/bin", "/bin"))
            ),
        }
        output = _run(
            [
                str(python),
                "-I",
                str(HELPER),
                str(root / "synthetic-repository"),
                installed_version,
            ],
            cwd=root,
            env=protocol_environment,
        )
        receipt = json.loads(output)
        assert receipt["installed_version"] == ARTIFACT_VERSION
        assert receipt["bootstrap_chars"] == 2_185
        assert receipt["bootstrap_truncated"] is False
        assert receipt["base"] != receipt["policy_sha"] != receipt["head"]
        assert receipt["merge_request_context"] == {
            "contract": "review.merge-request-context/v1",
            "records": 1,
            "trust": "invocation",
            "content_role": "untrusted_data",
            "authoritative_for_actions": False,
        }
        assert receipt["policy"] == {
            "accepted_decisions": 1,
            "guidance_documents": 3,
            "structured_target_records": 4,
            "legacy_text_records": 0,
            "target_only": True,
            "authoritative_for_actions": False,
        }
        assert receipt["prioritized_template"] == {
            "component": "late/templates",
            "detection": "jinja-extension",
            "engine": "jinja2",
            "provenance": "framework plugin:jinja2",
            "rendered_extension": ".conf",
        }
        assert receipt["private_modes"] is True
        assert receipt["read_only"] is True
        assert receipt["repository_clean"] is True
