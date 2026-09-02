"""Contracts for the public GitLab operations documentation."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
README = PROJECT_ROOT / "README.md"
OPERATIONS = PROJECT_ROOT / "docs" / "operations.md"
GITLAB_GUIDE = PROJECT_ROOT / "docs" / "gitlab.md"
CONFIGURATION = PROJECT_ROOT / "docs" / "configuration.md"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
GITLAB_EXAMPLES = PROJECT_ROOT / "examples" / "gitlab"
CODE_OF_CONDUCT = PROJECT_ROOT / "CODE_OF_CONDUCT.md"
SIGNAL_OWNERSHIP = PROJECT_ROOT / "docs" / "engineering" / "review_signal_ownership.md"


def test_readme_product_and_security_badges_link_to_authoritative_results() -> None:
    readme = README.read_text(encoding="utf-8")

    product_badges = (
        "[![Version](https://img.shields.io/pypi/v/open-code-review-toolkit?"
        "label=version&color=0A66C2)](https://pypi.org/project/open-code-review-toolkit/)",
        "[![Python](https://img.shields.io/pypi/pyversions/open-code-review-toolkit?"
        "logo=python&logoColor=white&label=python)]"
        "(https://pypi.org/project/open-code-review-toolkit/)",
        "[![License](https://img.shields.io/pypi/l/open-code-review-toolkit?color=0A66C2)]"
        "(https://github.com/xeonvs/open-code-review-toolkit/blob/main/LICENSE)",
    )
    for badge in product_badges:
        assert badge in readme
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
    positions = [readme.index(badge) for badge in product_badges]
    assert positions == sorted(positions)
    assert positions[-1] < readme.index("[![OpenSSF Best Practices]")
    assert "img.shields.io/pypi/v/open-code-review-toolkit" in readme
    assert "test.pypi.org" not in readme.split("## Install", 1)[0]


def test_readme_and_gitlab_guide_link_to_operations() -> None:
    readme = README.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "docs/operations.md" in readme
    assert "operations.md" in gitlab
    assert "## How reviews evolve" in readme


def test_readme_install_is_isolated_checksum_pinned_and_no_llm() -> None:
    """Keep the root installation path exact without using preflight as a smoke test."""

    readme = README.read_text(encoding="utf-8")
    install = readme.split("## Install", 1)[1].split("## How reviews evolve", 1)[0]
    manifest = json.loads(
        (PROJECT_ROOT / "compatibility" / "ocr-support.json").read_text(encoding="utf-8")
    )
    recommended = manifest["recommended_version"]
    release = next(item for item in manifest["releases"] if item["version"] == recommended)
    digests = {asset["name"]: asset["sha256"] for asset in release["assets"]}

    assert "Python 3.12 through 3.14" in install
    assert "uv tool install open-code-review-toolkit" in install
    assert install.index(". .venv/bin/activate") < install.index(
        "python -m pip install open-code-review-toolkit"
    )
    assert f"Open Code Review {recommended}" in install
    assert f"open-code-review v{recommended}" in install
    assert digests["opencodereview-linux-amd64"] in install
    assert digests["opencodereview-darwin-arm64"] in install
    assert "ocr --version" in install
    assert "ocr-ci --help" in install
    assert "not the installation\nsmoke test" in install


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
        "review_signal_ownership.md",
        "m5_context_contracts.md",
        "evidence_migration_matrix.md",
        "test_evidence_matrix.md",
        "execution_history/README.md",
    ):
        assert phrase in engineering_index

    assert "not a second source" in codex_index
    assert "without duplicating their rules" in engineering_index
    assert "docs/README.md" in readme


def test_review_signal_audit_keeps_group_data_outside_toolkit_authority() -> None:
    """Keep the completed BL-017 ownership and privacy conclusion explicit."""

    audit = SIGNAL_OWNERSHIP.read_text(encoding="utf-8")
    backlog = (PROJECT_ROOT / "docs" / "codex" / "TASKS_BACKLOG.md").read_text(encoding="utf-8")
    roadmap = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    for phrase in (
        "Source-to-signal matrix",
        "Group labels are model-produced",
        "sorted changed paths",
        "no exporter of its own",
        "concludes `no-new-layer`",
        "BL-016 remains parked",
        "BL-018 remains conditional",
        "BL-019 and",
        "BL-020 retain",
    ):
        assert phrase in audit
    assert "Review measurement gaps (BL-017) | Completed and removed" in backlog
    assert "M6 Profiles and quality measurement | Established / conditional" in roadmap


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


def test_completion_cap_and_provider_failure_boundaries_are_public() -> None:
    """Keep token ownership, safe failure projection, and migration behavior explicit."""

    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    compatibility = (PROJECT_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")

    for document in (configuration, operations, gitlab):
        assert "OCR_LLM_MAX_COMPLETION_TOKENS" in document
        assert "OCR_MAX_TOKENS_BUDGET" in document
        assert "/models" in document
        assert "provider-specific" in document
    for document in (configuration, operations, gitlab):
        assert "OCR_LLM_MAX_COMPLETION_TOKENS=4096" not in document
    current_compatibility = compatibility.split("### OCR 1.11.2 — toolkit 0.9.0 target", 1)[1]
    assert "explicit positive completion-cap transport" in current_compatibility
    assert "default remains unset" in current_compatibility
    assert "provider-specific cap" in current_compatibility
    assert "historical OCR 1.10.0 through 1.10.2" in compatibility
    for field in ("max_completion_tokens", "max_output_tokens", "max_tokens"):
        assert field in configuration
    for phrase in (
        "defaults to **unset**",
        "positive decimal integer from `1` through `1000000`",
        "exactly equal JSON integer is deduplicated",
        "fails configuration with a migration error",
        "The toolkit does not add an environment alias",
    ):
        assert phrase in configuration

    for phrase in (
        "endpoint-or-model-not-found",
        "cost reservation from the requested output cap",
        "OCR provider diagnostics:",
        "http-payment-required",
        "http-rate-limited",
        "not toolkit telemetry",
        "Neither setting is presented as the proven cause",
        "`OCR_POST_ERROR_DETAILS=1` cannot add them",
        "the previous successful review is preserved",
        "automatic approval is not attempted",
    ):
        assert phrase in operations
    assert "one separate local line may contain closed protocol detail" in security
    assert "receipt, DLP, telemetry, severity, finding, or approval signal" in security


def test_summary_and_code_tab_boundaries_are_public() -> None:
    """Keep coverage, filtering, advisory, and field-specific HTAB semantics distinct."""

    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")

    for phrase in (
        "Review complete with publication filtering",
        "it is not called incomplete OCR coverage",
        "at least two findings",
        "Tool and token lines remain independent",
    ):
        assert phrase in gitlab
    for document in (operations, configuration, security):
        assert "existing_code" in document
        assert "suggestion_code" in document
        assert "horizontal tab" in document.casefold()
    assert "filtered warnings into legacy failed-item inference" in configuration
    assert "public projection is incomplete" in operations
    assert "all other control/format characters remain blocking" in operations


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
    assert "receipt v7" in configuration
    assert "Receipt v1-v6" in configuration
    assert "Receipt v1-v6" in operations
    assert "complete `metadata` context" in operations.lower()
    assert "Every configured direct external MCP" in configuration
    assert "required context degradation" in operations
    assert "admitted remediation context" in operations
    assert "absolute HTTPS `url`" in configuration
    assert "sole stdio exception" in configuration


def test_builtin_search_coverage_and_receipt_v7_boundaries_are_public() -> None:
    """Document efficient routing without exposing search or coverage arguments."""

    configuration = CONFIGURATION.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    for name in (
        "ocr_toolkit_evidence",
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
    ):
        assert name in configuration
        assert name in gitlab
    for phrase in (
        "1\u2013128 characters",
        "at most eight literal tokens",
        "absence_authoritative=true",
        "Stop once the required evidence is sufficient",
        "action receipt v2",
        "Receipt v7",
    ):
        assert phrase in configuration
    assert "DLP-admitted store" in security
    assert "Zero action counters, queries, scopes, IDs" in operations
    assert "arguments, queries, scopes, IDs, and results stay private" in gitlab


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
        "unprotected-target.gitlab-ci.yml",
    }
    assert {path.name for path in mode_root.glob("*.yml")} == expected_modes
    for mode in expected_modes:
        recipe = (mode_root / mode).read_text(encoding="utf-8")
        assert recipe.startswith("variables:\n")
        assert "OCR_REVIEW_CONTEXT_MODE" in recipe
        assert "OCR_AUTO_APPROVE" in recipe


def test_unprotected_target_contract_is_complete_and_fail_closed() -> None:
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    bounded = (PROJECT_ROOT / "docs" / "review-context.md").read_text(encoding="utf-8")
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")
    recipe = (GITLAB_EXAMPLES / "modes" / "unprotected-target.gitlab-ci.yml").read_text(
        encoding="utf-8"
    )

    assert 'OCR_GITLAB_TARGET_PROTECTION_MODE: "required"' in example
    assert 'OCR_GITLAB_TARGET_PROTECTION_MODE: "unprotected"' in recipe
    assert 'OCR_REVIEW_CONTEXT_MODE: "metadata"' in recipe
    assert 'OCR_AUTO_APPROVE: "false"' in recipe

    for document in (configuration, gitlab, security, bounded):
        assert "OCR_GITLAB_TARGET_PROTECTION_MODE" in document
        assert "required" in document
        assert "unprotected" in document
        assert "receipt v7" in document
    for phrase in (
        "Explicit empty strings",
        "Context `off` and bounded untrusted `metadata`",
        "any configured `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` value",
        "direct external MCP",
        "Structured target guidance and accepted decisions are omitted",
        "approval executor and GitLab approval endpoint are not reached",
    ):
        assert phrase in configuration
    limitation = (
        "The target branch was not protected in GitLab. "
        "This review ran in limited, comment-only mode."
    )
    assert limitation in configuration
    assert limitation in gitlab
    assert limitation in operations
    assert "without turning complete coverage into partial coverage" in gitlab
    assert "cannot reach the approval executor" in security
    assert "does not change result completeness or status" in bounded

    for phrase in (
        "Use two merge requests for the recommended setup",
        "Retrying that same merge request",
        "generic fail-closed failure note",
        "Code Owners and code-owner approval rules",
        "green advisory pipeline",
    ):
        assert phrase in gitlab
    assert "valid non-zero MR SHA takes precedence" in operations
    assert "absent or all-zero MR SHA" in operations
    assert "require a valid result, complete manifest coverage" in operations


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


def test_protected_pr_and_scheduled_checks_do_not_repeat_on_main_push() -> None:
    """Assign source validation to the reviewed tree and publication to main."""

    workflows = PROJECT_ROOT / ".github" / "workflows"
    for name in ("ci.yml", "build.yml", "security.yml", "codeql.yml"):
        workflow = (workflows / name).read_text(encoding="utf-8")
        assert "  push:" not in workflow
        assert "pull_request:" in workflow

    security = (workflows / "security.yml").read_text(encoding="utf-8")
    codeql = (workflows / "codeql.yml").read_text(encoding="utf-8")
    testpypi = (workflows / "testpypi.yml").read_text(encoding="utf-8")
    release = (workflows / "release.yml").read_text(encoding="utf-8")

    assert "schedule:" in security
    assert "schedule:" in codeql
    assert "  push:\n    branches: [main]" in testpypi
    assert "./scripts/quality.sh check" in release
    assert "uv run pip-audit --skip-editable" in release


def test_threat_model_covers_remote_finding_image_boundary() -> None:
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "Optional remote finding images add a" in security
    assert "External finding images are disabled by default" in security
    assert "does not send finding prose" in security
    assert "arbitrary remote-image requests" in policy


def test_ocr_compatibility_workflow_is_bounded_and_protected() -> None:
    """Qualification retains bounded failure evidence without hiding a red job."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ocr-compatibility.yml").read_text(
        encoding="utf-8"
    )
    qualifier = (PROJECT_ROOT / "scripts" / "ocr_compat.py").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert '- cron: "15 7 * * *"' in workflow
    assert '- cron: "41 5 * * *"' not in workflow
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
    assert "continue-on-error: true" in workflow
    assert "--status-output /tmp/ocr-compat/status.json" in workflow
    assert "QUALIFICATION_OUTCOME: ${{ steps.qualify.outcome }}" in workflow
    assert 'case "${QUALIFICATION_OUTCOME}" in' in workflow
    assert "success) input=(--evidence /tmp/ocr-compat/evidence.json)" in workflow
    assert "failure) input=(--status /tmp/ocr-compat/status.json)" in workflow
    assert "if: ${{ !cancelled() }}" in workflow
    assert "if: ${{ always() && !cancelled() }}" in workflow
    assert "if: steps.qualify.outcome == 'failure'" in workflow
    assert "run: exit 1" in workflow
    assert "gh issue create" not in workflow
    assert 'f"{fragment_number}.maintenance.md"' in qualifier
    assert 'f"{fragment_number}.feature.md"' not in qualifier
    for contract in (
        "OCR 1.9.9 — inherited predecessor",
        "OCR 1.9.10 — toolkit 0.8.0 target and 0.8.2 predecessor",
        "OCR 1.10.0 — toolkit 0.8.2 and 0.8.3 target",
        "OCR 1.10.1 — toolkit 0.8.4 target",
        "OCR 1.10.2 — toolkit 0.8.5 target",
        "OCR 1.11.0 — toolkit 0.8.6 target",
        "OCR 1.11.1 — toolkit 0.8.7 target",
        "OCR 1.11.2 — toolkit 0.9.0 target",
        "ocr.toolkit-advisory/v1",
        "ocr.llm-retry-report/v1",
        "not toolkit telemetry",
        "Deploy toolkit 0.8.2 or 0.8.3 directly with OCR 1.10.0",
        "Deploy toolkit 0.8.4 directly with OCR 1.10.1",
        "Deploy toolkit 0.8.5 directly with OCR 1.10.2",
        "Deploy toolkit 0.8.6 directly with OCR 1.11.0",
        "Deploy toolkit 0.8.7 directly with OCR 1.11.1",
        "Deploy toolkit 0.9.0 directly with OCR 1.11.2",
        "max-tools runtime behavior is unchanged",
        "max_completion_tokens=16384",
        "do not install OCR 1.9.10 as an intermediate step",
    ):
        assert contract in policy
    assert "daily trigger is scheduled for `07:15 UTC`" in policy
    assert "feature-bearing patch notes" in policy
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


def test_numeric_ocr_controls_use_behavioral_qualification_and_template_delegation() -> None:
    """Keep help text, normalization, effective values, and authority distinct."""

    configuration = CONFIGURATION.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    compatibility = (PROJECT_ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")

    assert "default at `0` so OCR uses its embedded template limit of `100`" in configuration
    assert "explicit `50` remain below the template default" in configuration
    assert "raw stderr is not added to\nfindings, result warnings" in configuration
    assert "receipts, DLP inputs, telemetry" in configuration
    assert "`OCR_MAX_TOOLS=0`" in operations
    assert "corrects stale help text for the already-qualified behavior" in operations
    assert "effective `100` for omitted, sentinel `0`, `49`, and `50`" in compatibility
    assert "help text\n  alone is not compatibility evidence" in development


def test_actions_storage_maintenance_bounds_completed_run_metadata() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "actions-maintenance.yml").read_text(
        encoding="utf-8"
    )
    ci = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    codeql = (PROJECT_ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    development = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")

    assert "actions: write" in workflow
    assert "scripts/actions_cleanup.py" in workflow
    assert "--execute" in workflow
    assert "save-cache: false" in ci
    assert "trap-caching: false" in codeql
    assert "CODEQL_OVERLAY_DATABASE_MODE: none" in codeql
    assert "separately controlled v4 overlay-database mode are disabled" in development
    assert "TestPyPI preview runs after 14 days" in development
    assert "TestPyPI development and ordinary completed runs after 30 days" in development
    assert "stable Release runs after 60 days" in development
    assert "Active and newer runs remain untouched" in development
    assert "fail-closed ten-page limit per day" in development


def test_gitlab_operations_separate_model_metadata_from_review_connectivity() -> None:
    """Do not present an advisory green job or `/models` read as a usable review."""

    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "run `ocr llm test`" in gitlab
    assert "metadata read is not a full review request" in gitlab
    assert "green pipeline with an allowed-to-fail OCR job" in gitlab
    assert "not evidence that OCR produced a usable review" in gitlab
