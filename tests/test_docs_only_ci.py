"""The documentation shortcut is narrow and keeps protected check identities."""

import importlib.util
import subprocess
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


def test_unavailable_git_range_uses_full_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(128, ["git", "diff"])

    monkeypatch.setattr(docs_only.subprocess, "run", unavailable)
    assert not docs_only.docs_only("a" * 40, "b" * 40)


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
    preview = (ROOT / ".github/workflows/testpypi.yml").read_text()
    assert "needs.classify.outputs.docs_only != 'true'" in preview
    assert "github.event.before" in preview
    assert 'BASE=$(git rev-parse "${HEAD}^")' not in preview
    assert yaml.safe_load(preview)["jobs"]["classify"]["timeout-minutes"] == 5
