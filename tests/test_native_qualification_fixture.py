"""Optional native suites cannot acquire an unrelated binary's configuration."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("target", ["OCR_GITLINK_QUALIFY_BINARY", "OCR_FEDERATION_QUALIFY_BINARY"])
@pytest.mark.parametrize("requested", [False, True])
def test_native_fixture_ignores_unrelated_missing_executable(tmp_path, target, requested):
    # A fresh pytest process exercises actual fixture initialization. A cached
    # session fixture in this parent process would hide the original eager read.
    probe = tmp_path / "test_selection.py"
    probe.write_text(
        f"def test_selection(qualified_native_ocr):\n    qualified_native_ocr({target!r})\n"
    )
    environment = os.environ.copy()
    for name in ("OCR_GITLINK_QUALIFY_BINARY", "OCR_FEDERATION_QUALIFY_BINARY", "PYTEST_ADDOPTS"):
        environment.pop(name, None)
    other = (
        "OCR_FEDERATION_QUALIFY_BINARY"
        if target == "OCR_GITLINK_QUALIFY_BINARY"
        else "OCR_GITLINK_QUALIFY_BINARY"
    )
    environment[other] = str(tmp_path / "unrelated-missing-binary")
    if requested:
        environment[target] = str(tmp_path / "requested-missing-binary")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "tests.conftest",
            "-q",
            "--confcutdir",
            str(tmp_path),
            "-o",
            "addopts=",
            str(probe),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr
    if requested:
        assert result.returncode == 1 and "requested-missing-binary" in output
        assert "1 failed" in output and "FileNotFoundError" in output
    else:
        assert result.returncode == 0 and "1 skipped" in output
    assert "unrelated-missing-binary" not in output
