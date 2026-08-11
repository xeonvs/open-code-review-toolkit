"""Contracts for release-requiring change closure guidance."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
AGENT_GUIDANCE = PROJECT_ROOT / "AGENTS.md"
PRINCIPLES = PROJECT_ROOT / "docs" / "engineering" / "project_principles.md"
PITFALLS = PROJECT_ROOT / "docs" / "codex" / "AGENT_EXECUTION_PITFALLS.md"
RELEASE_GUIDE = PROJECT_ROOT / "docs" / "release.md"
DEVELOPMENT_GUIDE = PROJECT_ROOT / "docs" / "development.md"


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
    release_required = release.split("## Release-required changes", 1)[1].split(
        "## Development builds", 1
    )[0]
    delivery_steps = re.findall(r"^\d+\. (.+)$", release_required, re.MULTILINE)

    def step_with(*terms: str) -> int:
        return next(
            index
            for index, step in enumerate(delivery_steps)
            if all(term.casefold() in step.casefold() for term in terms)
        )

    ordered_boundaries = (
        step_with("feature", "pull request"),
        step_with(".devN", "TestPyPI"),
        step_with("release/vX.Y.Z"),
        step_with("stable", "PyPI"),
        step_with("release-receipt.json", "without another repository"),
    )
    assert ordered_boundaries == tuple(sorted(ordered_boundaries))
    assert "final repository mutation" in release_required
    assert "must not claim" in release_required
    assert "no-release closure" not in release_required


def test_boundary_guidance_has_one_authoritative_instruction_stack() -> None:
    """Keep concise actions, invariants, pitfalls, and tests connected."""

    guidance = AGENT_GUIDANCE.read_text(encoding="utf-8")
    principles = PRINCIPLES.read_text(encoding="utf-8")
    pitfalls = PITFALLS.read_text(encoding="utf-8")
    development = DEVELOPMENT_GUIDE.read_text(encoding="utf-8")

    assert "docs/engineering/project_principles.md` is authoritative" in guidance
    assert "docs/codex/AGENT_EXECUTION_PITFALLS.md" in guidance
    assert "docs/development.md" in guidance
    assert "## Boundary Invariants" in principles
    assert "## Treating post-hoc checks as bounded I/O" in pitfalls
    assert "## Trusting toolkit-created evidence on reload" in pitfalls
    assert "## Testing only the canonical parser spelling" in pitfalls
    assert "## Proving subprocess integration only with mocks" in pitfalls
    assert "## Letting outcome branches drift" in pitfalls
    assert "## Boundary-focused test checklist" in development
