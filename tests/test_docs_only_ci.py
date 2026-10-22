"""The documentation shortcut is narrow and keeps protected check identities."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/docs_only.py"
SPEC = importlib.util.spec_from_file_location("docs_only", SCRIPT)
assert SPEC and SPEC.loader
docs_only = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs_only)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({"docs/guide.md": "guide"}, True),
        ({"README.md": "readme", "PLANS.md": "plan"}, True),
        ({"docs/image.png": "binary"}, False),
        ({".release-reconciled-version": "0.12.1"}, False),
        ({".github/workflows/ci.yml": "changed"}, False),
        ({"scripts/quality.sh": "changed"}, False),
        ({"src/ocr_toolkit/app.py": "changed"}, False),
        ({"docs/guide.md": "guide", "src/ocr_toolkit/app.py": "changed"}, False),
    ],
)
def test_exact_git_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: dict[str, str], expected: bool
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "initial").write_text("initial")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    base = _git(tmp_path, "rev-parse", "HEAD")
    for name, content in changed.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "change")
    monkeypatch.chdir(tmp_path)
    assert docs_only.docs_only(base, _git(tmp_path, "rev-parse", "HEAD")) is expected


def test_empty_or_invalid_range_is_not_exempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("readme")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    monkeypatch.chdir(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    assert not docs_only.docs_only(head, head)
    assert not docs_only.docs_only("HEAD", head)
    assert not docs_only.docs_only("0" * 40, head)
    assert not docs_only.development_only(head, head)
    assert not docs_only.development_only("HEAD", head)
    assert not docs_only.development_only("0" * 40, head)


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({".github/workflows/ci.yml": "changed"}, True),
        ({".github/workflows/release.yml": "changed"}, True),
        ({".github/workflows/site-release-notify.yml": "changed"}, True),
        ({".github/workflows/testpypi.yml": "changed"}, True),
        ({"scripts/docs_only.py": "changed", "tests/test_ci.py": "test"}, True),
        ({"docs/development.md": "guide", "tests/test_ci.py": "test"}, True),
        ({".release-reconciled-version": "0.12.1"}, False),
        ({".github/workflows/security.yml": "changed"}, False),
        ({"scripts/quality.sh": "changed"}, False),
        ({"pyproject.toml": "changed"}, False),
        ({"src/ocr_toolkit/app.py": "changed"}, False),
        ({"tests/data.json": "changed"}, False),
        ({"tests/test_ci.py": "test", "src/ocr_toolkit/app.py": "changed"}, False),
    ],
)
def test_internal_main_push_range_skips_development_artifacts_only_for_closed_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: dict[str, str], expected: bool
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "initial").write_text("initial")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    base = _git(tmp_path, "rev-parse", "HEAD")
    for name, content in changed.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "change")
    monkeypatch.chdir(tmp_path)
    assert docs_only.development_only(base, _git(tmp_path, "rev-parse", "HEAD")) is expected


def test_development_classifier_emits_exact_workflow_output(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "initial").write_text("initial")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    base = _git(tmp_path, "rev-parse", "HEAD")
    target = tmp_path / ".github/workflows/ci.yml"
    target.parent.mkdir(parents=True)
    target.write_text("internal check")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "internal")
    output = tmp_path / "github-output"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--base",
            base,
            "--head",
            _git(tmp_path, "rev-parse", "HEAD"),
            "--development",
        ],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert completed.stdout == "development_only=true\n"
    assert output.read_text() == completed.stdout


def test_multi_commit_push_includes_earlier_code_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("initial")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    before = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "app.py").write_text("value = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "code")
    penultimate = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("updated")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "docs")
    head = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    assert docs_only.docs_only(penultimate, head)
    assert not docs_only.docs_only(before, head)
    assert not docs_only.development_only(before, head)


def test_unavailable_git_range_uses_full_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(128, ["git", "diff"])

    monkeypatch.setattr(docs_only.subprocess, "run", unavailable)
    assert not docs_only.docs_only("a" * 40, "b" * 40)
    assert not docs_only.development_only("a" * 40, "b" * 40)


def test_documentation_rename_is_not_exempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("same content")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "mv", "README.md", "CONTRIBUTING.md")
    _git(tmp_path, "commit", "-qm", "rename")
    monkeypatch.chdir(tmp_path)
    assert not docs_only.docs_only(base, _git(tmp_path, "rev-parse", "HEAD"))
    assert not docs_only.development_only(base, _git(tmp_path, "rev-parse", "HEAD"))


def test_required_job_names_and_full_fallback() -> None:
    expected = {
        "ci.yml": {"test-ubuntu-latest-py3.12", "quality"},
        "build.yml": {"build-distributions"},
        "security.yml": {"sast-bandit", "dependency-audit", "secrets"},
    }
    for name, required in expected.items():
        source = (ROOT / ".github/workflows" / name).read_text()
        jobs = yaml.safe_load(source)["jobs"]
        assert required <= {job["name"] for job in jobs.values()}
        assert "github.event_name == 'pull_request'" in source
        assert "needs.classify.outputs.docs_only != 'true'" in source
        assert jobs["classify"]["timeout-minutes"] == 5
        classifier = jobs["classify"]["steps"][-1]["run"]
        assert 'git show "${BASE}:scripts/docs_only.py"' in classifier
        assert 'env -u GITHUB_OUTPUT python "$trusted_script"' in classifier
        assert "result=docs_only=false" in classifier
        assert 'echo "$result" >> "$GITHUB_OUTPUT"' in classifier
    preview = (ROOT / ".github/workflows/testpypi.yml").read_text()
    assert "needs.classify.outputs.development_only != 'true'" in preview
    assert 'python scripts/docs_only.py --base "$BASE" --head "$HEAD" --development' in preview
    assert "github.event.before" in preview
    assert 'BASE=$(git rev-parse "${HEAD}^")' not in preview
    assert yaml.safe_load(preview)["jobs"]["classify"]["timeout-minutes"] == 5


def test_pr_cannot_replace_trusted_classifier(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    script = tmp_path / "scripts" / "docs_only.py"
    script.parent.mkdir()
    script.write_text(SCRIPT.read_text())
    (tmp_path / "README.md").write_text("original\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "trusted base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    script.write_text('print("docs_only=true")\n')
    (tmp_path / "app.py").write_text("changed code\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "malicious PR")
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    classifier = workflow["jobs"]["classify"]["steps"][-1]["run"]
    output = tmp_path / "github-output"
    environment = {
        **os.environ,
        "BASE": base,
        "HEAD": _git(tmp_path, "rev-parse", "HEAD"),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(output),
    }
    subprocess.run(["bash", "-e", "-c", classifier], cwd=tmp_path, env=environment, check=True)
    assert output.read_text() == "docs_only=false\n"
