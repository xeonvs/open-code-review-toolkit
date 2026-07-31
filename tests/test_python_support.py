"""Contracts for the supported Python range and CI coverage."""

from __future__ import annotations

import tomllib

from tests.support import PROJECT_ROOT

SUPPORTED_PYTHON = ("3.12", "3.13", "3.14")


def test_project_metadata_declares_the_supported_python_range() -> None:
    """Keep the resolver bound and classifiers aligned with the public range."""

    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert metadata["requires-python"] == ">=3.12,<3.15"
    python_classifiers = {
        classifier.rsplit(" :: ", 1)[-1]
        for classifier in metadata["classifiers"]
        if classifier.startswith("Programming Language :: Python :: 3.")
    }
    assert python_classifiers == set(SUPPORTED_PYTHON)


def test_readme_does_not_duplicate_python_version_numbers() -> None:
    """Leave supported-version ownership with package metadata and CI."""

    notice = next(
        line
        for line in (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("> The project is under active development")
    )

    assert notice.startswith("> The project is under active development")
    assert all(version not in notice for version in SUPPORTED_PYTHON)
