"""Contracts for the quiet quality-command wrapper."""

from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "quality.sh"


def test_quality_script_uses_an_isolated_ignored_environment() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "OCR_TOOLKIT_QUALITY_ENVIRONMENT:-$log_dir/venv" in script
    assert "export UV_PROJECT_ENVIRONMENT=$quality_environment" in script


def test_quality_script_runs_the_bounded_bandit_gate() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    command = "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium"
    assert "security)" in script
    assert script.count(command) == 2
    assert "tests" not in command
