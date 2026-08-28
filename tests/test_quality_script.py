"""Contracts for the quiet quality-command and local secret-scan wrappers."""

import os
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "quality.sh"
PROJECT_ROOT = SCRIPT.parent.parent
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"


def test_quality_script_uses_an_isolated_ignored_environment() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv" in script
    assert 'export UV_PROJECT_ENVIRONMENT="$quality_environment"' in script
    assert "open_code_review_toolkit-*.dist-info" in script
    assert '[ ! -f "$metadata/RECORD" ]' in script
    assert 'uv venv --clear "$quality_environment"' in script
    assert "uv sync --locked --all-groups" in script
    assert "quality environment sync failed; last 80 lines follow" in script
    assert script.count("uv run --no-sync") == 6


def test_quality_script_enforces_combined_and_boundary_coverage() -> None:
    """Use one branch-aware test run and one hosted coverage owner."""

    script = SCRIPT.read_text(encoding="utf-8")
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    coverage_commands = (
        "coverage report --include=src/ocr_toolkit/ocr_result.py,src/ocr_toolkit/preflight.py --fail-under=80",
        "coverage report --include=src/ocr_toolkit/posting/workflow.py,src/ocr_toolkit/posting/gitlab.py,src/ocr_toolkit/posting/snapshot.py,src/ocr_toolkit/posting/gitlab_approval.py --fail-under=80",
        "coverage report --include=src/ocr_toolkit/review_runner.py,src/ocr_toolkit/context/broker.py,src/ocr_toolkit/context/store.py,src/ocr_toolkit/context/dlp.py,src/ocr_toolkit/posting/approval.py --fail-under=85",
        "coverage report --include=src/ocr_toolkit/mcp_config.py,src/ocr_toolkit/providers/gitlab.py,src/ocr_toolkit/providers/gitlab_context.py,src/ocr_toolkit/providers/gitlab_discussions.py,src/ocr_toolkit/providers/gitlab_remediation.py,src/ocr_toolkit/context/policy.py,src/ocr_toolkit/result_contract.py --fail-under=85",
    )

    assert script.count("pytest -q --cov=ocr_toolkit") == 1
    assert "--cov-fail-under=85" in script
    assert script.count("coverage report --include=") == 4
    assert (
        "uv run pytest --cov=ocr_toolkit --cov-report=term-missing --cov-fail-under=85" in workflow
    )
    assert workflow.count("coverage: true") == 1
    assert workflow.count("coverage: false") == 4
    assert "if: ${{ matrix.coverage }}" in workflow
    assert "if: ${{ !matrix.coverage }}" in workflow
    assert workflow.count("uv run pytest -q") == 1
    for command in coverage_commands:
        assert command in script
        assert workflow.count(f"uv run {command}") == 1


def test_ci_quality_job_does_not_duplicate_the_package_gate() -> None:
    """Leave distribution construction and clean-install smoke to Build artifacts."""

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    quality_job = workflow.split("  quality:", 1)[1]

    assert "python -m build" not in quality_job
    assert "twine check" not in quality_job
    assert "wheel-smoke" not in quality_job
    assert "sdist-smoke" not in quality_job


def test_quality_script_runs_the_bounded_bandit_gate() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    command = "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium"
    assert "security)" in script
    assert script.count(command) == 2
    assert "tests" not in command


def test_python_commit_gate_applies_and_then_checks_ruff_formatting() -> None:
    """Keep immediate formatting and the repository-wide commit gate explicit."""

    script = SCRIPT.read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")

    assert "set -- uv run --no-sync ruff format ." in script
    assert 'for command in "ruff format --check ."' in script
    assert "`scripts/quality.sh format` before self-review" in development
    assert "`uv run --frozen ruff format --check .`" in development


def test_quality_script_truncates_multi_command_log_per_invocation(tmp_path: Path) -> None:
    """Do not mix stale coverage output into a later multi-command result."""

    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    fake_uv = binary_dir / "uv"
    fake_uv.write_text(
        "#!/bin/sh\nprintf 'fresh invocation: %s\\n' \"$*\"\n",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log = log_dir / "coverage.log"
    log.write_text("stale invocation must disappear\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PATH"] = f"{binary_dir}:{environment['PATH']}"
    environment["OCR_TOOLKIT_LOG_DIR"] = str(log_dir)

    subprocess.run([str(SCRIPT), "coverage"], cwd=PROJECT_ROOT, env=environment, check=True)

    output = log.read_text(encoding="utf-8")
    assert "stale invocation" not in output
    assert output.count("fresh invocation: run --no-sync sh -c") == 5


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
