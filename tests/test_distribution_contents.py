"""Contracts for the intentionally small published distribution contents."""

import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def test_sdist_includes_only_runtime_and_end_user_material() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    start = pyproject.index("[tool.hatch.build.targets.sdist]")
    end = pyproject.index("[tool.hatch.version.raw-options]")
    sdist = pyproject[start:end]

    assert 'only-include = ["src", "README.md", "LICENSE", "pyproject.toml"]' in sdist
    # Hatch force-includes the active VCS exclusion file in standard sdists; a custom
    # build hook would add more packaging code than this single metadata file.
    assert "ignore-vcs" not in sdist
    for excluded in (
        '"/tests"',
        '"/examples"',
        '"/docs"',
        '"/scripts"',
        '"/compatibility"',
        '"/.github"',
        '"/changelog.d"',
        '"/docs/development.md"',
        '"/docs/release.md"',
        '"/docs/codex"',
        '"/docs/engineering"',
        '"/PLANS.md"',
        '"/ROADMAP.md"',
        '"/SECURITY.md"',
        '"/CHANGELOG.md"',
    ):
        assert excluded not in sdist


def test_wheel_is_built_only_from_runtime_package() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert '[tool.hatch.build.targets.wheel]\npackages = ["src/ocr_toolkit"]' in pyproject


def test_review_runner_is_inside_the_wheel_runtime_package() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    assert (PROJECT_ROOT / "src/ocr_toolkit/review_runner.py").is_file()
    assert '[tool.hatch.build.targets.wheel]\npackages = ["src/ocr_toolkit"]' in pyproject


def test_built_wheel_contains_ecosystem_packages_without_flat_parser_shims(
    tmp_path: Path,
) -> None:
    """Lock the installed source-adapter layout rather than source imports alone."""

    import subprocess
    import sys

    output = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(output)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(output.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    expected = {
        "ocr_toolkit/evidence/ecosystems/__init__.py",
        "ocr_toolkit/evidence/ecosystems/ansible/__init__.py",
        "ocr_toolkit/evidence/ecosystems/ansible/requirements.py",
        "ocr_toolkit/evidence/ecosystems/ansible/topology.py",
        "ocr_toolkit/evidence/ecosystems/contracts.py",
        "ocr_toolkit/evidence/ecosystems/go.py",
        "ocr_toolkit/evidence/ecosystems/javascript.py",
        "ocr_toolkit/evidence/ecosystems/php.py",
        "ocr_toolkit/evidence/ecosystems/python.py",
    }
    removed = {
        "ocr_toolkit/evidence/ansible.py",
        "ocr_toolkit/evidence/ansible_requirements.py",
        "ocr_toolkit/evidence/composer_manifests.py",
        "ocr_toolkit/evidence/go_manifests.py",
        "ocr_toolkit/evidence/javascript_manifests.py",
        "ocr_toolkit/evidence/manifest_model.py",
        "ocr_toolkit/evidence/python_manifests.py",
    }
    assert expected <= names
    assert not removed & names
