"""Contracts for the durable strategy, roadmap, and regenerated backlog."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
PLANNING_DOCUMENTS = (
    "AGENTS.md",
    "README.md",
    "ROADMAP.md",
    "docs/engineering/toolkit_strategy.md",
    "docs/codex/TASKS_BACKLOG.md",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_canonical_strategy_and_roadmap_are_linked() -> None:
    agents = read("AGENTS.md")
    readme = read("README.md")
    assert "docs/engineering/toolkit_strategy.md" in agents
    assert "ROADMAP.md" in agents
    assert "[Toolkit strategy](docs/engineering/toolkit_strategy.md)" in readme
    assert "[Roadmap](ROADMAP.md)" in readme
    assert "[Backlog](docs/codex/TASKS_BACKLOG.md)" in readme


def test_local_markdown_links_resolve() -> None:
    link_pattern = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")

    for document in PLANNING_DOCUMENTS:
        path = ROOT / document
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#")):
                continue
            relative_path = target.split("#", 1)[0]
            assert (path.parent / relative_path).resolve().exists(), (document, target)


def test_durable_planning_does_not_pin_an_ocr_release() -> None:
    durable_planning = (
        read("docs/engineering/toolkit_strategy.md")
        + read("ROADMAP.md")
        + read("docs/codex/TASKS_BACKLOG.md")
    )
    assert re.search(r"\bOCR [`v]*\d+\.\d+\.\d+", durable_planning) is None


def test_backlog_contains_complete_numbered_items() -> None:
    backlog = read("docs/codex/TASKS_BACKLOG.md")
    item_ids = re.findall(r"^### (BL-\d{3}):", backlog, flags=re.MULTILINE)
    assert item_ids == [f"BL-{number:03d}" for number in range(1, 23)]
    fields = (
        "Status",
        "Priority",
        "Roadmap theme",
        "Dependencies",
        "Activation trigger",
        "Goal",
        "Scoped deliverables",
        "Acceptance criteria",
        "Exclusions",
        "Validation",
        "Release classification expectation",
    )
    for field in fields:
        assert backlog.count(f"**{field}:**") == 22


def test_every_previous_backlog_item_has_an_explicit_disposition() -> None:
    backlog = read("docs/codex/TASKS_BACKLOG.md")
    previous_items = (
        "Native fuzzing campaign",
        "OpenSSF Best Practices registration",
        "Additional provider adapters",
        "File-based user configuration",
    )
    for previous_item in previous_items:
        assert f"| {previous_item} |" in backlog


def test_roadmap_defines_every_backlog_theme() -> None:
    roadmap = read("ROADMAP.md")
    backlog = read("docs/codex/TASKS_BACKLOG.md")
    themes = set(re.findall(r"\*\*Roadmap theme:\*\* (M\d [^\n]+)", backlog))
    assert themes == {
        "M0 Foundation",
        "M1 Evidence architecture",
        "M2 Ecosystem and framework coverage",
        "M3 External MCP hardening",
        "M4 Policy and project guidance",
        "M5 Review profiles and quality measurement",
        "M6 Later and conditional work",
    }
    roadmap_theme_names = {
        "M0 Foundation",
        "M1 Evidence architecture",
        "M2 Ecosystem and framework coverage",
        "M3 External MCP hardening",
        "M4 Policy and project guidance",
        "M5 Profiles and quality measurement",
        "M6 Later and conditional work",
    }
    for theme in roadmap_theme_names:
        assert theme in roadmap
