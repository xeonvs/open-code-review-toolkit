"""Contracts for release-requiring change closure guidance."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
AGENT_GUIDANCE = PROJECT_ROOT / "AGENTS.md"
PRINCIPLES = PROJECT_ROOT / "docs" / "engineering" / "project_principles.md"
PITFALLS = PROJECT_ROOT / "docs" / "codex" / "AGENT_EXECUTION_PITFALLS.md"
RELEASE_GUIDE = PROJECT_ROOT / "docs" / "release.md"


def test_agent_guidance_keeps_release_required_work_open_through_publication() -> None:
    guidance = AGENT_GUIDANCE.read_text(encoding="utf-8")

    assert "release-required" in guidance
    assert "target stable version" in guidance
    assert "feature PR" in guidance
    assert "stable TestPyPI/PyPI publication" in guidance
    assert "explicitly defers" in guidance


def test_durable_guidance_distinguishes_readiness_from_delivery() -> None:
    principles = PRINCIPLES.read_text(encoding="utf-8")
    pitfalls = PITFALLS.read_text(encoding="utf-8")
    release = RELEASE_GUIDE.read_text(encoding="utf-8")

    assert "Feature validation proves readiness" in principles
    assert "production PyPI" in pitfalls
    assert "Do not mark the objective complete after step 1 or 2" in release
    assert "release/vX.Y.Z" in release
