"""Contracts for the public GitLab operations documentation."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
README = PROJECT_ROOT / "README.md"
OPERATIONS = PROJECT_ROOT / "docs" / "operations.md"
GITLAB_GUIDE = PROJECT_ROOT / "docs" / "gitlab.md"
CONFIGURATION = PROJECT_ROOT / "docs" / "configuration.md"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"


def test_readme_and_gitlab_guide_link_to_operations() -> None:
    readme = README.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "docs/operations.md" in readme
    assert "operations.md" in gitlab
    assert "## How reviews evolve" in readme


def test_operations_guide_documents_lifecycle_contract() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")

    assert "```mermaid" in operations
    assert "flowchart LR" in operations
    assert "stateDiagram-v2" not in operations
    assert "OCR command" in operations
    assert "Publish succeeds" in operations
    assert "`/ocr suppress`" in operations
    assert "`/ocr resolve`" in operations
    assert "OCR_POST_MODE=draft" in operations
    assert "OCR_STRICT_POSTING=true" in operations
    assert "Developer role" in operations
    assert "`api` scope" in operations
    assert "fingerprint" in operations
    assert "previous review" in operations


def test_legacy_commands_are_only_documented_as_removed() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert operations.count("`/ocr keep`") == 1
    assert operations.count("`/ocr skip`") == 1
    assert "`/ocr keep`" not in readme + gitlab
    assert "`/ocr skip`" not in readme + gitlab


def test_blocking_gitlab_example_uses_safe_posting_defaults() -> None:
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")

    assert 'OCR_POST_MODE: "draft"' in example
    assert 'OCR_STRICT_POSTING: "true"' in example
    assert "OCR_POST_MODE=draft" in configuration
    assert "OCR_STRICT_POSTING=true" in configuration


def test_security_workflow_has_a_bounded_bandit_job() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")

    assert "sast-bandit:" in workflow
    assert "./scripts/quality.sh security" in workflow
    assert "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium" in development
    assert "# nosec B108" in security
