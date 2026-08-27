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


def test_080_release_notes_are_actionable_for_operators_and_automation() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.0")

    for label in ("**Added:**", "**Changed:**", "**Migration:**"):
        assert label in notes
    for contract in (
        "ocr.review-context-policy/v1",
        "ocr.review-context-policy/v2",
        "ocr.context-store/v2",
        "remediation_threads",
        "remediation_thread",
        "DLP-clean metadata, generic discussions, and adapter records",
    ):
        assert contract in notes

    assert "@<live-bot-username> suppress" in notes
    assert "@<live-bot-username> resolve" in notes
    assert "GitLab `GET /user`" in notes

    for removed_name in (
        "OCR_GITLAB_BOT_USER_ID",
        "OCR_USE_ANTHROPIC",
        "OCR_RUN_HELPER_TESTS",
        "OCR_LLM_SUPPORTS_FUNCTION_CALLING",
        "OCR_LLM_SUPPORTS_REASONING",
        "OCR_CONFIG_PATH",
    ):
        assert removed_name in notes
    assert notes.count("**Removed:**") == 4
    assert "OCR_LLM_PROTOCOL=anthropic" in notes
    assert "default `openai`" in notes

    assert "ten-page fail-closed limit per shard" in notes
    for retention in (
        "TestPyPI preview runs after 14 days",
        "TestPyPI development and ordinary runs after 30 days",
        "stable `Release` runs after 60 days",
    ):
        assert retention in notes
    assert "active and newer runs remain untouched" in notes

    assert "examples/context/" in notes
    assert "examples/gitlab/context/" in notes
    assert ".opencodereview/review-context-policy.json" in notes
    for path in ("docs/README.md", "docs/codex/README.md", "docs/engineering/README.md"):
        assert path in notes

    for heading in (
        "OCR 1.9.9 — inherited",
        "OCR 1.9.10 — changed",
        "Telemetry",
        "Deployment/Migration",
    ):
        assert heading in notes
    for contract in (
        "toolkit 0.8.0 does not require installing or requalifying this predecessor",
        "ocr.llm-retry-report/v1",
        "ocr.run-manifest/v1",
        "does not ingest it as telemetry",
        "Install OCR 1.9.10 directly",
        "Do not install OCR 1.9.9 as an intermediate step",
        "359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c",
    ):
        assert contract in notes


def test_081_release_notes_separate_added_fixed_removed_and_unchanged_contracts() -> None:
    """Give deployment agents an exact delta without requiring source inspection."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.1")

    for label in ("**Added:**", "**Fixed:**", "**Changed:**", "**Removed:**", "**Unchanged:**"):
        assert label in notes
    for contract in (
        "OCR_LLM_MAX_COMPLETION_TOKENS",
        "unset",
        "llm.extra_body.max_completion_tokens",
        "max_output_tokens",
        "max_tokens",
        "OCR_LLM_EXTRA_BODY",
        "/models.max_completion_tokens",
        "endpoint-or-model-not-found",
        "requested-output cost reservation",
        "raw provider/model identities",
        "automatic approval is not attempted",
        "all five supported OS/Python",
        "generic `main`-push reruns",
        "complete post-merge stable-release validation",
    ):
        assert contract in notes


def test_082_release_notes_are_actionable_for_people_and_deployment_agents() -> None:
    """Keep added, changed, inherited, fixed, and migration outcomes distinct."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.2")

    for phrase in (
        "OCR 1.9.10 — inherited predecessor",
        "max_completion_tokens=58888",
        "OCR 1.10.0 — changed target",
        "OCR_REVIEW_EFFORT",
        "exact default is `medium`",
        "max_completion_tokens=16384",
        "Deploy toolkit 0.8.2 directly with OCR 1.10.0",
        "do not install OCR 1.9.10 as an intermediate step",
        "Caller `--output`/`-o` remains unsupported",
        "compatibility-status/v1",
        "job returns red",
        "no-new-layer",
        "No exporter",
    ):
        assert phrase in notes


def test_083_release_notes_cover_hotfix_activity_and_release_gates() -> None:
    """Keep the hotfix delta actionable without overstating telemetry or macOS gates."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.3")

    for phrase in (
        "actual qualification outcome",
        "sentinel `0`",
        "template-owned tool-loop value",
        "all OCR tool calls",
        "does not report per-tool token consumption",
        "macOS endpoint CI jobs",
        "Linux, coverage, quality, security, dependency, package, and CodeQL",
    ):
        assert phrase in notes


def test_084_release_notes_separate_advisory_publication_and_dlp_contracts() -> None:
    """Keep the summary hotfix and OCR deployment boundary explicit."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.4")

    for phrase in (
        "ocr.toolkit-advisory/v1",
        "Technical details",
        "Review complete with publication filtering",
        "original outcome/count combinations",
        "horizontal tabs",
        "unchanged value",
        "secret, PII, forbidden-value, laundering, and budget checks",
        "two or more published findings",
        "Open Code Review 1.10.1",
        "MATLAB or Objective-C",
        "update directly from OCR 1.10.0 to 1.10.1",
    ):
        assert phrase in notes


def test_085_release_notes_keep_provider_diagnostics_bounded_and_actionable() -> None:
    """Keep the provider and OCR upgrade boundaries explicit for deployment."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = release.release_notes(changelog, "0.8.5")

    for phrase in (
        "ocr.llm-retry-report/v1",
        "http-payment-required",
        "http-rate-limited",
        "OCR_REVIEW_CONCURRENCY",
        "OCR_LLM_MAX_COMPLETION_TOKENS",
        "GitLab summary/reason",
        "Open Code Review 1.10.2",
        "07:15 UTC",
        "Solidity",
        "Vyper",
    ):
        assert phrase in notes


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
