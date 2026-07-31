"""Pin the structured OCR v1.8.0 result contract used by posting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ocr-1.8.0"
SEVERITIES = {"critical", "high", "medium", "low"}
CATEGORIES = {
    "bug",
    "security",
    "performance",
    "maintainability",
    "test",
    "style",
    "documentation",
    "other",
}


def load_fixture(name: str) -> dict[str, Any]:
    """Load one synthetic payload copied from the OCR v1.8.0 JSON shape."""

    value = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_no_supported_files_is_a_structured_skip() -> None:
    """Keep an upstream skip distinct from a completed clean review."""

    result = load_fixture("no-supported-files.json")
    assert result["status"] == "skipped"
    assert result["message"] == "No supported files changed."
    assert result["comments"] == []
    assert result["tool_calls"] == {"total": 0, "by_tool": {}}


def test_no_findings_is_a_successful_review() -> None:
    """Pin OCR's positive result rather than inferring it from free text."""

    result = load_fixture("no-findings.json")
    assert result["status"] == "success"
    assert result["message"] == "No comments generated. Looks good to me."
    assert result["comments"] == []


def test_subtask_errors_are_not_clean_results() -> None:
    """Prevent a zero-comment partial failure from receiving a positive status."""

    result = load_fixture("completed-with-errors.json")
    assert result["status"] == "completed_with_errors"
    assert result["comments"] == []
    assert {item["type"] for item in result["warnings"]} == {"subtask_error"}


def test_finding_metadata_uses_the_upstream_closed_sets() -> None:
    """Keep severity and category presentation aligned with OCR v1.8.0."""

    comments = load_fixture("findings.json")["comments"]
    assert {item["severity"] for item in comments} <= SEVERITIES
    assert {item["category"] for item in comments} <= CATEGORIES
