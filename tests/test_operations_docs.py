"""Contracts for the public GitLab operations documentation."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
README = PROJECT_ROOT / "README.md"
OPERATIONS = PROJECT_ROOT / "docs" / "operations.md"
GITLAB_GUIDE = PROJECT_ROOT / "docs" / "gitlab.md"
CONFIGURATION = PROJECT_ROOT / "docs" / "configuration.md"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
GITLAB_EXAMPLES = PROJECT_ROOT / "examples" / "gitlab"
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


def test_documentation_indexes_route_to_canonical_owners() -> None:
    docs_index = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    codex_index = (PROJECT_ROOT / "docs" / "codex" / "README.md").read_text(encoding="utf-8")
    engineering_index = (PROJECT_ROOT / "docs" / "engineering" / "README.md").read_text(
        encoding="utf-8"
    )
    readme = README.read_text(encoding="utf-8")

    for index in (docs_index, codex_index, engineering_index):
        assert index.count("<!-- engineering-workflow:index:start -->") == 1
        assert index.count("<!-- engineering-workflow:index:end -->") == 1

    for relative_path in (
        "configuration.md",
        "gitlab.md",
        "operations.md",
        "review-context.md",
        "security.md",
        "development.md",
        "release.md",
        "engineering/README.md",
        "codex/README.md",
    ):
        assert relative_path in docs_index
    for phrase in ("PLANS.md", "TASKS_BACKLOG.md", "AGENT_EXECUTION_PITFALLS.md"):
        assert phrase in codex_index
    for phrase in (
        "toolkit_strategy.md",
        "project_principles.md",
        "m5_context_contracts.md",
        "evidence_migration_matrix.md",
        "test_evidence_matrix.md",
        "execution_history/README.md",
    ):
        assert phrase in engineering_index

    assert "not a second source" in codex_index
    assert "without duplicating their rules" in engineering_index
    assert "docs/README.md" in readme


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
    assert "`@<live-bot-username> suppress`" in operations
    assert "`@<live-bot-username> resolve`" in operations
    assert "`@mr.bot resolve`" in operations
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
    assert 'OCR_REVIEW_CONTEXT_MODE: "off"' in example
    assert 'OCR_MAX_TOKENS_BUDGET: "0"' in example
    assert '--max-tokens-budget "${OCR_MAX_TOKENS_BUDGET:-0}"' in example
    assert "OCR_MAX_TOKENS_BUDGET" in configuration
    assert "OCR_POST_MODE=draft" in configuration
    assert "OCR_STRICT_POSTING=true" in configuration
    assert 'OCR_POST_BADGES: "shields"' in example
    assert "OCR_POST_BADGES" in configuration
    assert "default `text` mode" in configuration


def test_aggregate_review_budget_is_explicit_and_never_looks_complete() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    for document in (operations, configuration, gitlab):
        assert "OCR_MAX_TOKENS_BUDGET" in document
        assert "partial" in document
        assert "automatic" in document
    assert "operator-owned cost ceiling" in configuration
    assert "not a quality profile" in configuration
    assert "approximate" in configuration


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
        "never retried against the new identity",
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


def test_context_receipt_and_mcp_profile_contracts_are_public() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")

    for document in (configuration, gitlab):
        assert "OCR_REVIEW_CONTEXT_MODE" in document
        assert "identity-only" in document
        assert "`metadata`" in document
        assert "`enriched`" in document
    assert 'OCR_REVIEW_CONTEXT_MODE: "off"' in example
    assert "receipt v5" in configuration
    assert "Receipt v1-v4" in configuration
    assert "Receipt v1-v4" in operations
    assert "complete `metadata` context" in operations.lower()
    assert "Every configured direct external MCP" in configuration
    assert "required context degradation" in operations
    assert "admitted remediation context" in operations
    assert "absolute HTTPS `url`" in configuration
    assert "sole stdio exception" in configuration


def test_production_bot_modes_and_current_contract_are_public() -> None:
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    bounded = (PROJECT_ROOT / "docs" / "review-context.md").read_text(encoding="utf-8")

    for phrase in (
        "## Production bot configuration",
        "## Choose one operating mode",
        "Identity only",
        "Metadata",
        "Enriched discussions",
        "Enriched adapters",
        "Direct MCP",
        "live `GET /user`",
        "@mr.bot resolve",
        "Retry UI/API",
        "Note Hook receiver",
    ):
        assert phrase in gitlab
    assert "Migration from" not in gitlab
    assert "service-side tenant/object/field/operation authorization" in gitlab
    assert "#choosing-a-discussion-policy" in gitlab
    for phrase in (
        "### Choosing a discussion policy",
        "Ordinary MR conversation only",
        "Earlier OCR finding plus human remediation replies only",
        "Both ordinary conversation and remediation history",
        "Discussions plus authorized issue/document records",
        "required: false",
        "zero selected threads is still complete",
    ):
        assert phrase in bounded

    mode_root = GITLAB_EXAMPLES / "modes"
    expected_modes = {
        "direct-mcp.gitlab-ci.yml",
        "enriched-adapters.gitlab-ci.yml",
        "enriched-discussions.gitlab-ci.yml",
        "identity-only.gitlab-ci.yml",
        "metadata.gitlab-ci.yml",
    }
    assert {path.name for path in mode_root.glob("*.yml")} == expected_modes
    for mode in expected_modes:
        recipe = (mode_root / mode).read_text(encoding="utf-8")
        assert recipe.startswith("variables:\n")
        assert "OCR_REVIEW_CONTEXT_MODE" in recipe
        assert "OCR_AUTO_APPROVE" in recipe


def test_examples_and_current_public_docs_use_product_oriented_language() -> None:
    current_documents = (
        README,
        CONFIGURATION,
        GITLAB_GUIDE,
        OPERATIONS,
        PROJECT_ROOT / "docs" / "review-context.md",
    )
    example_files = tuple(path for path in GITLAB_EXAMPLES.rglob("*") if path.is_file())
    for path in (*current_documents, *example_files):
        assert "synthetic" not in path.read_text(encoding="utf-8").casefold(), path


def test_accepted_decision_example_is_shown_in_a_later_review_flow() -> None:
    example = (GITLAB_EXAMPLES / "accepted-decisions.md").read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "## generated-client-timeout" in example
    assert "Scope: src/client/generated/**" in example
    for document in (configuration, gitlab):
        assert '"action":"list","kind":"repository.accepted_decision","ref":"policy"' in document
        assert '"action":"get","id":"<id' in document
        assert "later merge request" in document


def test_inline_create_reconciliation_contract_is_bounded_and_nonretrying() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")

    for phrase in (
        "`posted`, `invalid_position`, `definite_failure`, or `ambiguous_create`",
        "Only `invalid_position` may enter bounded fallback",
        "no retry and no fallback",
        "marker-only global rescan",
        "exactly once",
    ):
        assert phrase in operations
    assert "one author-bound readback without retry" in security
    assert "Rollback deletes only recorded IDs absent from the baseline" in security


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
