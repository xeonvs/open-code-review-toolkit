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
    assert 'OCR_AUTO_APPROVE: "true"' in example
    assert "OCR_POST_MODE=draft" in configuration
    assert "OCR_STRICT_POSTING=true" in configuration


def test_auto_approval_contract_is_default_on_exact_sha_and_own_user_only() -> None:
    """Keep the new GitLab write and its safety boundaries explicit."""

    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")

    for phrase in (
        "`OCR_AUTO_APPROVE=true` is the default",
        "at most three findings",
        "severity exactly `low`",
        "category exactly `style`, `documentation`, or\n`maintainability`",
        "`patch_id_sha`",
        "never retried against the new commit",
        "never\ncalls `reset_approvals`",
        "Partial, skipped, legacy,\nand disabled runs preserve",
    ):
        assert phrase in operations

    assert "`OCR_AUTO_APPROVE` defaults to `true`" in configuration
    assert "`false`,\n`0`, `no`, or `off`" in configuration
    assert (
        "There are intentionally no\nenvironment variables for policy thresholds" in configuration
    )
    assert 'OCR_AUTO_APPROVE: "true"' in example


def test_security_workflow_has_a_bounded_bandit_job() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")

    assert "sast-bandit:" in workflow
    assert "./scripts/quality.sh security" in workflow
    assert (
        "bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium" in development
    )
    assert "# nosec B108" in security


def test_ocr_compatibility_workflow_is_bounded_and_protected() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ocr-compatibility.yml").read_text(
        encoding="utf-8"
    )
    qualifier = (PROJECT_ROOT / "scripts" / "ocr_compat.py").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: read" in workflow
    assert "issues: write" in workflow
    assert "pull-requests: write" not in workflow
    assert "persist-credentials: false" in workflow
    assert "max-parallel: 2" in workflow
    assert "build-matrix" in workflow
    assert "assess-chain" in workflow
    assert "pattern: ocr-compatibility-v*" in workflow
    assert workflow.count("prepare-update") == 1
    assert "MAX_QUALIFICATION_CHAIN = 10" in qualifier
    assert "OCR_UPDATE_BOT_TOKEN" in workflow
    assert "gh auth setup-git" in workflow
    assert "git switch -C" in workflow
    assert "git push --force-with-lease" in workflow
    assert workflow.count("upsert-issue") == 1
    assert "gh issue create" not in workflow
    assert "--search" not in workflow
    assert "git push origin main" not in workflow
    assert "gh pr merge" not in workflow
    assert "automatic-safe" in workflow
    assert "human-review-required" in policy
    assert "never writes directly to `main`" in policy
    assert "Go MCP SDK v1.6.1" in policy
    assert "`2025-11-25`" in policy
    assert "initialized notification" in policy
    assert "absolute Python executable in isolated mode" in policy
    assert "eventually consistent search index" in policy
    assert "ocr.run-manifest/v1" in policy


def test_actions_storage_maintenance_preserves_run_metadata() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "actions-maintenance.yml").read_text(
        encoding="utf-8"
    )
    ci = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    codeql = (PROJECT_ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")

    assert "actions: write" in workflow
    assert "scripts/actions_cleanup.py" in workflow
    assert "--execute" in workflow
    assert "save-cache:" in ci
    assert "refs/heads/main" in ci
    assert "trap-caching: false" in codeql
    assert "CODEQL_OVERLAY_DATABASE_MODE: none" in codeql
    assert "separately controlled v4 overlay-database mode are disabled" in development
    assert "never workflow runs or check metadata" in development
