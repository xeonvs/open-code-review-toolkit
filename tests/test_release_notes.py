"""Tests for exact GitHub Release note extraction."""

from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = Path(__file__).parents[1] / "scripts" / "release_notes.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_notes_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script()


def test_towncrier_categories_preserve_conditional_release_contract() -> None:
    """Keep user-facing headings stable without depending on pending fragments."""

    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    categories = {
        item["directory"]: item["name"] for item in configuration["tool"]["towncrier"]["type"]
    }

    assert categories == {
        "feature": "🚀 Features",
        "bugfix": "🐛 Bug Fixes",
        "maintenance": "🛠 Maintenance",
        "refactor": "🔧 Refactoring",
        "doc": "📖 Documentation",
        "rules": "🧩 Rules",
        "security": "Security",
        "deprecation": "Deprecations",
        "removal": "Removals",
    }


def test_080_fragments_are_actionable_for_operators_and_automation() -> None:
    feature = (ROOT / "changelog.d" / "120.feature.md").read_text(encoding="utf-8")
    mention = (ROOT / "changelog.d" / "125.feature.md").read_text(encoding="utf-8")
    maintenance = (ROOT / "changelog.d" / "124.maintenance.md").read_text(encoding="utf-8")
    examples = (ROOT / "changelog.d" / "124.doc.md").read_text(encoding="utf-8")
    navigation = (ROOT / "changelog.d" / "123.doc.md").read_text(encoding="utf-8")

    for label in ("**Added:**", "**Changed:**", "**Migration:**"):
        assert label in feature
    for contract in (
        "ocr.review-context-policy/v1",
        "ocr.review-context-policy/v2",
        "ocr.context-store/v2",
        "remediation_threads",
        "remediation_thread",
        "DLP-clean metadata, generic discussions, and adapter records",
    ):
        assert contract in feature

    assert "@<live-bot-username> suppress" in mention
    assert "@<live-bot-username> resolve" in mention
    assert "GitLab `GET /user`" in mention

    for removed_name in (
        "OCR_GITLAB_BOT_USER_ID",
        "OCR_USE_ANTHROPIC",
        "OCR_RUN_HELPER_TESTS",
        "OCR_LLM_SUPPORTS_FUNCTION_CALLING",
        "OCR_LLM_SUPPORTS_REASONING",
        "OCR_CONFIG_PATH",
    ):
        assert removed_name in maintenance
    assert maintenance.count("**Removed:**") == 4
    assert "OCR_LLM_PROTOCOL=anthropic" in maintenance
    assert "default `openai`" in maintenance

    assert "examples/context/" in examples
    assert "examples/gitlab/context/" in examples
    assert ".opencodereview/review-context-policy.json" in examples
    for path in ("docs/README.md", "docs/codex/README.md", "docs/engineering/README.md"):
        assert path in navigation


def test_extracts_only_the_exact_release_section() -> None:
    changelog = "# Changelog\n\n## 0.2.0 - later\n\nnew\n\n## 0.1.0 - now\n\nfirst\n"

    assert release.release_notes(changelog, "0.2.0") == (
        "## 0.2.0 - later\n\nnew\n\n"
        "**Full Changelog**: "
        "https://github.com/xeonvs/open-code-review-toolkit/compare/v0.1.0...v0.2.0\n"
    )


def test_repository_changelog_has_one_section_for_each_version() -> None:
    changelog = (SCRIPT.parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(r"^## (\d+\.\d+\.\d+)(?: - .+)?$", changelog, re.MULTILINE)

    assert len(versions) == len(set(versions))


def test_version_is_treated_as_text_not_a_regular_expression() -> None:
    with pytest.raises(ValueError, match=r"no 0\.1\.0 release section"):
        release.release_notes("## 0x1x0 - wrong\n", "0.1.0")


def test_non_stable_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid stable version"):
        release.release_notes("## 0.1.0.dev1\n", "0.1.0.dev1")


def test_missing_release_fails_closed() -> None:
    with pytest.raises(ValueError, match=r"no 0\.1\.0 release section"):
        release.release_notes("# Changelog\n", "0.1.0")


def test_oldest_release_without_adjacent_previous_release_fails_closed() -> None:
    with pytest.raises(ValueError, match="no previous stable release"):
        release.release_notes("## 0.1.0 - first\n\nnotes\n", "0.1.0")


@pytest.mark.parametrize(
    "repository_url",
    [
        "http://github.com/xeonvs/open-code-review-toolkit",
        "https://example.invalid/xeonvs/open-code-review-toolkit",
        "https://github.com/xeonvs/other",
        "https://github.com/xeonvs/open-code-review-toolkit?redirect=1",
    ],
)
def test_repository_url_must_be_the_canonical_https_origin(repository_url: str) -> None:
    changelog = "## 0.2.0\n\nnew\n\n## 0.1.0\n\nold\n"

    with pytest.raises(ValueError, match="repository URL"):
        release.release_notes(changelog, "0.2.0", repository_url)
