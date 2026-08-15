"""Contracts for the public GitLab operations documentation."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
README = PROJECT_ROOT / "README.md"
OPERATIONS = PROJECT_ROOT / "docs" / "operations.md"
GITLAB_GUIDE = PROJECT_ROOT / "docs" / "gitlab.md"
CONFIGURATION = PROJECT_ROOT / "docs" / "configuration.md"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
CODE_OF_CONDUCT = PROJECT_ROOT / "CODE_OF_CONDUCT.md"


def test_readme_security_badges_link_to_repository_specific_results() -> None:
    readme = README.read_text(encoding="utf-8")

    assert (
        "[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/"
        "github.com/xeonvs/open-code-review-toolkit/badge)]"
        "(https://securityscorecards.dev/viewer/?uri="
        "github.com/xeonvs/open-code-review-toolkit)"
    ) in readme
    assert (
        "[![CodeQL](https://github.com/xeonvs/open-code-review-toolkit/actions/"
        "workflows/codeql.yml/badge.svg?branch=main)]"
        "(https://github.com/xeonvs/open-code-review-toolkit/actions/"
        "workflows/codeql.yml)"
    ) in readme


def test_readme_and_gitlab_guide_link_to_operations() -> None:
    readme = README.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "docs/operations.md" in readme
    assert "operations.md" in gitlab
    assert "## How reviews evolve" in readme


def test_community_conduct_policy_has_a_private_enforcement_route() -> None:
    """Keep conduct reports private and separate from public issue intake."""

    conduct = CODE_OF_CONDUCT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    contributing = (PROJECT_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    issue_config = (PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(
        encoding="utf-8"
    )

    assert "Contributor Covenant" in conduct
    assert "version 2.1" in conduct
    assert "[INSERT CONTACT METHOD]" not in conduct
    assert "security/advisories/new" in conduct
    assert "[Code of Conduct]" in conduct
    assert "Do not report conduct incidents in public issues" in conduct
    assert "CODE_OF_CONDUCT.md" in readme
    assert contributing.count("(CODE_OF_CONDUCT.md)") == 2
    assert "Code of Conduct report" in issue_config
    assert "Security vulnerability" in issue_config


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
    assert 'OCR_POST_BADGES: "shields"' in example
    assert "OCR_POST_BADGES" in configuration
    assert "default `text` mode" in configuration


def test_finding_badge_contract_is_opt_in_and_privacy_explicit() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")

    assert "Category and severity belong to each individual finding" in operations
    assert "OCR_POST_BADGES=shields" in operations
    assert "external image service" in operations
    assert "Unknown metadata never becomes a URL" in operations
    assert "makes no\nexternal image request" in configuration
    assert "does not change summary outcomes" in configuration


def test_auto_approval_contract_is_default_on_exact_sha_and_own_user_only() -> None:
    """Keep the new GitLab write and its safety boundaries explicit."""

    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")
    normalized_operations = " ".join(operations.split())
    normalized_configuration = " ".join(configuration.split())

    for phrase in (
        "`OCR_AUTO_APPROVE=true` is the default",
        "at most three findings",
        "severity exactly `low`",
        "category exactly `style`, `documentation`, or `maintainability`",
        "`patch_id_sha`",
        "never retried against the new commit",
        "never removes an existing approval",
        "Ineligible, partial, skipped, legacy, and disabled runs do not make an approval write",
    ):
        assert phrase in normalized_operations

    assert "`OCR_AUTO_APPROVE` defaults to `true`" in configuration
    assert "`false`,\n`0`, `no`, or `off`" in configuration
    assert (
        "There are intentionally no\nenvironment variables for policy thresholds" in configuration
    )
    assert "never removes an existing approval" in normalized_configuration
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


def test_threat_model_covers_remote_finding_image_boundary() -> None:
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "Optional remote finding images add a" in security
    assert "External finding images are disabled by default" in security
    assert "does not send finding prose" in security
    assert "arbitrary remote-image requests" in policy


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
    assert "README.md docs/gitlab.md docs/security.md" not in workflow
    assert 'README = ROOT / "README.md"' not in qualifier
    assert 'GITLAB_DOC = ROOT / "docs" / "gitlab.md"' not in qualifier
    assert 'SECURITY_DOC = ROOT / "docs" / "security.md"' not in qualifier
    assert "public version references" not in policy
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
