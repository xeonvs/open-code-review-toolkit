"""Tests for exact GitHub Release note extraction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "release_notes.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_notes_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script()


def test_extracts_only_the_exact_release_section() -> None:
    changelog = "# Changelog\n\n## 0.2.0 - later\n\nnew\n\n## 0.1.0 - now\n\nfirst\n"

    assert release.release_notes(changelog, "0.1.0") == "## 0.1.0 - now\n\nfirst\n"


def test_version_is_treated_as_text_not_a_regular_expression() -> None:
    with pytest.raises(ValueError):
        release.release_notes("## 0x1x0 - wrong\n", "0.1.0")


def test_missing_release_fails_closed() -> None:
    with pytest.raises(ValueError, match=r"no 0\.1\.0 release section"):
        release.release_notes("# Changelog\n", "0.1.0")
