"""Contracts for the quiet quality-command wrapper."""

import os
import shutil
import subprocess
import tarfile
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


def test_gitleaks_installer_pins_the_ci_archive_checksum() -> None:
    """Keep hosted release gates reproducible without trusting PATH state."""

    installer = (SCRIPT.parent / "install_gitleaks.sh").read_text(encoding="utf-8")

    assert "GITLEAKS_VERSION=8.24.3" in installer
    assert "9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c" in installer
    assert "--proto '=https' --proto-redir '=https'" in installer
    assert 'if [ "$actual_sha256" != "$expected_sha256" ]' in installer


def test_gitleaks_installer_verifies_before_installing(tmp_path: Path) -> None:
    """Exercise the hosted Linux installer with a synthetic local archive."""

    binary_dir = tmp_path / "bin"
    destination = tmp_path / "destination"
    source = tmp_path / "source-gitleaks"
    archive = tmp_path / "archive.tar.gz"
    binary_dir.mkdir()
    source.write_text("#!/bin/sh\necho synthetic\n", encoding="utf-8")
    source.chmod(0o755)
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname="gitleaks")

    for name, body in {
        "uname": '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo x86_64\n',
        "curl": f'#!/bin/sh\nwhile [ "$1" != --output ]; do shift; done\nshift\ncp {archive} "$1"\n',
        "sha256sum": "#!/bin/sh\nprintf '9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c  %s\\n' \"$1\"\n",
    }.items():
        helper = binary_dir / name
        helper.write_text(body, encoding="utf-8")
        helper.chmod(0o755)
    for name in ("cp", "cut", "gzip", "install", "mkdir", "mktemp", "rm", "tar"):
        target = shutil.which(name)
        assert target is not None
        (binary_dir / name).symlink_to(target)

    environment = dict(os.environ)
    environment["PATH"] = str(binary_dir)
    environment["TMPDIR"] = str(tmp_path)
    subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "install_gitleaks.sh"), str(destination)],
        env=environment,
        check=True,
    )

    installed = destination / "gitleaks"
    assert installed.read_bytes() == source.read_bytes()
    assert installed.stat().st_mode & 0o777 == 0o755
