"""Contracts for the intentionally small published distribution contents."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def test_sdist_includes_only_runtime_and_end_user_material() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    start = pyproject.index("[tool.hatch.build.targets.sdist]")
    end = pyproject.index("[tool.hatch.version.raw-options]")
    sdist = pyproject[start:end]

    required = {
        '"/src"',
        '"/README.md"',
        '"/LICENSE"',
        '"/pyproject.toml"',
    }
    assert {
        line.strip().rstrip(",") for line in sdist.splitlines() if line.strip().startswith('"/')
    } == required
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
