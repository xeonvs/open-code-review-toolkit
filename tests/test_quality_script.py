"""Contracts for the quiet quality-command and local secret-scan wrappers."""

import os
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "quality.sh"
PROJECT_ROOT = SCRIPT.parent.parent


def test_quality_script_uses_an_isolated_ignored_environment() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv" in script
    assert "export UV_PROJECT_ENVIRONMENT=$quality_environment" in script
    assert "open_code_review_toolkit-*.dist-info" in script
    assert '[ ! -f "$metadata/RECORD" ]' in script
    assert 'uv venv --clear "$quality_environment"' in script
    assert "uv sync --locked --all-groups" in script
    assert "quality environment sync failed; last 80 lines follow" in script
    assert script.count("uv run --no-sync") == 7


def test_quality_script_runs_the_bounded_bandit_gate() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    command = "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium"
    assert "security)" in script
    assert script.count(command) == 2
    assert "tests" not in command


def test_gitleaks_wrapper_scans_the_complete_feature_history(tmp_path: Path) -> None:
    """Match CI's first-parent, no-merge history before a branch is pushed."""

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Synthetic User"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "synthetic@example.invalid"], cwd=repository, check=True
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repository, check=True)
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    for index in range(2):
        tracked.write_text(f"feature {index}\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", f"feature {index}"], cwd=repository, check=True)

    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    captured_args = tmp_path / "gitleaks-arguments.txt"
    pinned_version = subprocess.check_output(
        [str(SCRIPT.parent / "gitleaks.sh"), "--version"], text=True
    ).strip()
    fake_gitleaks = binary_dir / "gitleaks"
    fake_gitleaks.write_text(
        "#!/bin/sh\n"
        f'if [ "${{1:-}}" = version ]; then echo {pinned_version}; exit 0; fi\n'
        f"printf '%s\\n' \"$@\" > {captured_args}\n",
        encoding="utf-8",
    )
    fake_gitleaks.chmod(0o755)
    for command in ("git", "sed"):
        resolved = shutil.which(command)
        assert resolved is not None
        (binary_dir / command).symlink_to(resolved)

    environment = os.environ.copy()
    environment["PATH"] = str(binary_dir)
    subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "gitleaks.sh"), base_commit, "HEAD"],
        cwd=repository,
        env=environment,
        check=True,
    )

    arguments = captured_args.read_text(encoding="utf-8")
    first_feature_commit = subprocess.check_output(
        ["git", "rev-list", "--first-parent", "--no-merges", "--reverse", f"{base_commit}..HEAD"],
        cwd=repository,
        text=True,
    ).splitlines()[0]
    assert "detect" in arguments
    assert f"--no-merges --first-parent {first_feature_commit}^.." in arguments
