"""Contracts for the quiet quality-command wrapper."""

import os
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


def test_complete_quality_gate_runs_local_gitleaks_first() -> None:
    """Keep the history-aware secret scan ahead of expensive Python checks."""

    script = SCRIPT.read_text(encoding="utf-8")
    gitleaks = (SCRIPT.parent / "gitleaks.sh").read_text(encoding="utf-8")

    assert script.index('if [ "$mode" = secrets ] || [ "$mode" = check ]') < script.index(
        "environment_sync_log="
    )
    assert "GITLEAKS_VERSION=8.24.3" in gitleaks
    assert "--no-merges --first-parent" in gitleaks
    assert "${first_commit}^..${head_commit}" in gitleaks


def test_gitleaks_wrapper_scans_the_complete_feature_history(tmp_path: Path) -> None:
    """Prove an intermediate feature commit is inside the scanner range."""

    repository = tmp_path / "repository"
    binary_dir = tmp_path / "bin"
    captured_args = tmp_path / "gitleaks-args"
    repository.mkdir()
    binary_dir.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "synthetic@example.invalid"], cwd=repository, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Synthetic Contributor"], cwd=repository, check=True
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repository, check=True)
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    subprocess.run(["git", "switch", "-q", "-c", "feature"], cwd=repository, check=True)
    for value in ("first\n", "second\n"):
        tracked.write_text(value, encoding="utf-8")
        subprocess.run(["git", "commit", "-q", "-am", value.strip()], cwd=repository, check=True)

    fake_gitleaks = binary_dir / "gitleaks"
    fake_gitleaks.write_text(
        "#!/bin/sh\n"
        'if [ "${1:-}" = version ]; then echo 8.24.3; exit 0; fi\n'
        f"printf '%s\\n' \"$@\" > {captured_args}\n",
        encoding="utf-8",
    )
    fake_gitleaks.chmod(0o755)
    environment = dict(os.environ)
    environment["PATH"] = f"{binary_dir}:{environment['PATH']}"

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
