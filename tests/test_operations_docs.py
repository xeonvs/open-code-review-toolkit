"""Contracts for the public GitLab operations documentation."""

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[1]
README = PROJECT_ROOT / "README.md"
OPERATIONS = PROJECT_ROOT / "docs" / "operations.md"
GITLAB_GUIDE = PROJECT_ROOT / "docs" / "gitlab.md"
CONFIGURATION = PROJECT_ROOT / "docs" / "configuration.md"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
GITLAB_EXAMPLES = PROJECT_ROOT / "examples" / "gitlab"
CODE_OF_CONDUCT = PROJECT_ROOT / "CODE_OF_CONDUCT.md"
SIGNAL_OWNERSHIP = PROJECT_ROOT / "docs" / "engineering" / "review_signal_ownership.md"
DECISION_FLOW = PROJECT_ROOT / "docs" / "review-decision-flow.md"


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
    assert "## How GitLab reviews evolve" in readme


def test_readme_install_is_isolated_checksum_pinned_and_no_llm() -> None:
    """Keep the root installation path exact without using preflight as a smoke test."""

    readme = README.read_text(encoding="utf-8")
    install = readme.split("## Install", 1)[1].split("## How reviews evolve", 1)[0]
    assert "Python 3.12 through 3.14" in install
    assert "uv tool install open-code-review-toolkit" in install
    assert install.index(". .venv/bin/activate") < install.index(
        "python -m pip install open-code-review-toolkit"
    )
    assert "compatibility/ocr-support.json" in install
    assert "`recommended_version`" in install
    assert "for this toolkit revision" in install
    assert "https://github.com/alibaba/open-code-review/releases)" in install
    assert "release entry's asset SHA-256" in install
    assert "Do not substitute the latest upstream" in install
    assert "manifest's exact `recommended_version`" in install
    assert not re.search(r"\b[a-f0-9]{64}\b", install)
    assert "ocr --version" in install
    assert "ocr-ci --help" in install
    assert "not the installation\nsmoke test" in install


def test_current_operator_guidance_uses_manifest_with_only_gitlink_ocr_literal() -> None:
    """Keep general pins in the manifest while naming the fixed gitlink boundary."""

    for document in (
        README,
        CONFIGURATION,
        OPERATIONS,
        GITLAB_GUIDE,
        GITLAB_EXAMPLES / "README.md",
    ):
        content = document.read_text(encoding="utf-8")
        assert "compatibility/ocr-support.json" in content
        assert all(
            match.group() == "OCR 1.13.3"
            for match in re.finditer(r"(?:OCR|Open Code Review) v?\d+\.\d+\.\d+", content)
        )
        assert not re.search(r"open-code-review/releases/tag/v\d+\.\d+\.\d+", content)
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    assert "Qualified OCR pin for the example's toolkit release" in configuration
    assert "not resolved dynamically" in configuration
    assert "Manifest SHA-256 for `opencodereview-linux-amd64`" in configuration
    assert not re.search(r"\b[a-f0-9]{64}\b", configuration)


def test_documentation_indexes_route_to_canonical_owners() -> None:
    docs_index = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    codex_index = (PROJECT_ROOT / "docs" / "codex" / "README.md").read_text(encoding="utf-8")
    engineering_index = (PROJECT_ROOT / "docs" / "engineering" / "README.md").read_text(
        encoding="utf-8"
    )
    context_contracts = (
        PROJECT_ROOT
        / "docs"
        / "engineering"
        / "execution_history"
        / "review_context_design_checkpoint.md"
    ).read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    for index in (docs_index, codex_index, engineering_index):
        assert index.count("<!-- engineering-workflow:index:start -->") == 1
        assert index.count("<!-- engineering-workflow:index:end -->") == 1

    for relative_path in (
        "configuration.md",
        "gitlab.md",
        "operations.md",
        "review-decision-flow.md",
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
        "execution_history/review_context_design_checkpoint.md",
        "execution_history/evidence_migration_matrix.md",
        "governed_federation_contracts.md",
        "test_evidence_matrix.md",
        "execution_history/README.md",
    ):
        assert phrase in engineering_index

    assert "not a second source" in codex_index
    assert "without duplicating their rules" in engineering_index
    assert "docs/README.md" in readme
    assert "current contracts live on `main`" in context_contracts
    assert "active release branch" not in context_contracts
    assert "active plan" not in context_contracts


def test_release_archive_reconciles_current_external_delivery_truth() -> None:
    """Keep legacy receipts and current repository closure distinct."""

    release_guide = (PROJECT_ROOT / "docs" / "release.md").read_text(encoding="utf-8")
    release_archive = (
        PROJECT_ROOT / "docs" / "engineering" / "execution_history" / "releases.md"
    ).read_text(encoding="utf-8")
    release_index = (
        PROJECT_ROOT / "docs" / "engineering" / "execution_history" / "README.md"
    ).read_text(encoding="utf-8")
    release_version = (PROJECT_ROOT / ".release-version").read_text(encoding="utf-8").strip()
    reconciled_version = (
        (PROJECT_ROOT / ".release-reconciled-version").read_text(encoding="utf-8").strip()
    )
    anchors = list(
        re.finditer(
            r'^<a id="plan-toolkit-(\d+)-(\d+)-(\d+)"></a>$',
            release_archive,
            flags=re.MULTILINE,
        )
    )
    assert anchors
    archive_version = ".".join(anchors[0].groups())
    current_release = release_archive[
        anchors[0].start() : anchors[1].start() if len(anchors) > 1 else None
    ]
    status_match = re.search(r"^Status: (.+)$", current_release, flags=re.MULTILINE)
    assert status_match
    current_status = status_match.group(1)
    release_version_key = tuple(int(part) for part in release_version.split("."))
    reconciled_version_key = tuple(int(part) for part in reconciled_version.split("."))

    assert "without another repository pull request" in release_guide
    assert "under `docs/engineering/execution_history/plans/`" in release_guide
    assert "does not advance for plans closed in the release PR" in release_guide
    assert "List tracked release issues in a release PR as bare references" in release_guide
    assert "The Release workflow is the sole closure owner" in release_guide
    assert reconciled_version == archive_version
    assert reconciled_version_key <= release_version_key
    assert "completed" in current_status
    assert "external reconciliation verified" in current_status
    assert "External reconciliation date:" in current_release

    current_index_row = next(
        line for line in release_index.splitlines() if line.startswith(f"| `v{release_version}`")
    )
    if release_version == archive_version:
        assert "external reconciliation" in current_index_row
        assert "stable-delivery handoff" not in current_index_row
    else:
        plan_directory = PROJECT_ROOT / "docs/engineering/execution_history/plans"
        stable_archives = []
        for path in plan_directory.glob("*.md"):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(rf"^## Active Plan: Toolkit {re.escape(release_version)}\b", text, re.M):
                stable_archives.append((path, text))
        assert len(stable_archives) == 1
        archive_path, archived_plan = stable_archives[0]
        assert "Status: done" in archived_plan
        assert "### Post-Close Delivery" in archived_plan
        assert "outside the closed repository plan" in archived_plan
        assert f"plans/{archive_path.name}" in current_index_row
        if "stable-delivery handoff" not in current_index_row:
            assert "immutable GitHub Release published" in current_index_row
            assert "archived plan remains a prepublication snapshot" in current_index_row
        assert "external reconciliation verified" not in current_index_row
        active_plan = (PROJECT_ROOT / "PLANS.md").read_text(encoding="utf-8")
        active_match = re.search(r"^## Active Plan: Toolkit (\d+\.\d+\.\d+)\b", active_plan, re.M)
        if active_match:
            active_version_key = tuple(int(part) for part in active_match.group(1).split("."))
            assert active_version_key > release_version_key


def test_review_signal_audit_keeps_group_data_outside_toolkit_authority() -> None:
    """Keep the completed BL-017 ownership and privacy conclusion explicit."""

    audit = SIGNAL_OWNERSHIP.read_text(encoding="utf-8")
    backlog = (PROJECT_ROOT / "docs" / "codex" / "TASKS_BACKLOG.md").read_text(encoding="utf-8")
    roadmap = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    for phrase in (
        "Source-to-signal matrix",
        "receipt v10",
        "action-receipt-v3 accounting",
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
    assert "Receipt v9 adds federation and stage-aware DLP accounting" in roadmap


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


def test_terminal_merge_request_race_contract_is_public_and_fail_closed() -> None:
    operations = OPERATIONS.read_text(encoding="utf-8")
    configuration = CONFIGURATION.read_text(encoding="utf-8")
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    flow = DECISION_FLOW.read_text(encoding="utf-8")

    for phrase in (
        "stops before evidence collection and OCR",
        "Duplicate jobs update the same note",
        "before each current-result write and cleanup step",
        "approval was not attempted",
        "stops publication",
        "Every non-strict success path re-reads that exact lifecycle",
        "`closed` MR remains reopenable",
        "marker-like finding text cannot select, overwrite, or delete",
    ):
        assert phrase in operations
    assert "ocr.pre-execution-status/v5" in configuration
    assert "findings, summaries, suppression, discussions, or approval state" in gitlab
    assert "close/reopen timing therefore fails" in gitlab
    assert "Unknown, malformed, unavailable, or mismatched provider data fails closed" in security
    assert "Merged or closed" in flow
    assert "no evidence, OCR, findings, or approval" in flow


def test_canonical_decision_flow_has_stable_palette_and_runtime_boundaries() -> None:
    """Keep one linked detailed flow aligned with signal-preserving publication."""

    flow = DECISION_FLOW.read_text(encoding="utf-8")
    strategy = (PROJECT_ROOT / "docs" / "engineering" / "toolkit_strategy.md").read_text(
        encoding="utf-8"
    )
    root_instructions = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert flow.count("```mermaid") == 4
    for color in ("#d1fae5", "#ffedd5", "#fee2e2", "#f3f4f6", "#dbeafe"):
        assert flow.count(color) == 4
    for phrase in (
        "core integrity boundary deliberately precedes additive diagnostics",
        "cannot replace an otherwise valid manifest, findings, summary, or posting transaction",
        "toolkit action receipt v3 remains authoritative",
        "not a local-mode exception",
        "not an automatic-approval feature",
        "publication owns review-signal delivery",
        "receipt v13",
        "OCR_REVIEW_PROGRESS",
        "Blocking pipe or unavailable",
        "Review continues unchanged",
    ):
        assert phrase in flow
    assert "review-decision-flow.md" in strategy
    assert "docs/review-decision-flow.md" in root_instructions
    assert 'id="review-flow"' in root_instructions
    assert 'owners="docs/review-decision-flow.md|docs/engineering/project_principles.md"' in (
        root_instructions
    )


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
    current_compatibility = compatibility.split("### OCR 1.11.3 — toolkit 0.9.0 target", 1)[1]
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
        "does not create a potentially stale MR failure note",
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
        "A moved or unverifiable identity before the write skips approval",
        "never removes an existing approval",
        "Ineligible, partial, skipped, older-receipt, and disabled runs do not make an approval write",
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
    assert "receipt v13" in configuration
    assert "v1-v8 results remain unsupported" in configuration
    assert "v1-v8 remains unsupported" in operations
    assert "complete `metadata` context" in operations.lower()
    assert "mandatory internal evidence MCP is unreplaceable" in configuration
    assert "required context degradation" in operations
    assert "admitted remediation context" in operations
    assert 'GitLab accepts only `{type:"https",url:...}`' in configuration
    assert 'Local review also accepts `{type:"stdio"' in configuration


def test_builtin_search_coverage_and_receipt_v11_boundaries_are_public() -> None:
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
        "action receipt v3",
        "Receipt v13",
    ):
        assert phrase in configuration
    assert "DLP-admitted store" in security
    assert (
        "Zero completed action counters, unattributed attempts, queries, scopes, IDs" in operations
    )
    assert "arguments, queries, scopes, IDs, and results stay private" in gitlab


def test_production_bot_modes_and_current_contract_are_public() -> None:
    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")
    bounded = (PROJECT_ROOT / "docs" / "review-context.md").read_text(encoding="utf-8")
    normalized_bounded = " ".join(bounded.split())

    for phrase in (
        "## Production bot configuration",
        "## Choose one operating mode",
        "Identity only",
        "Metadata",
        "Enriched discussions",
        "Governed MCP federation",
        "live `GET /user`",
        "@mr.bot resolve",
        "Retry UI/API",
        "Note Hook receiver",
    ):
        assert phrase in gitlab
    assert "Migration from" not in gitlab
    assert "service-side tenant/object/field/operation authorization" in gitlab
    assert "#protected-policy-v4" in gitlab
    for phrase in (
        "## Protected policy v4",
        "forge_discussions",
        "remediation_threads",
        "CI outcomes select exact job names",
        "external acquisition is now governed by operator registry v2",
        "required: false",
        "zero selected records is complete",
    ):
        assert phrase in normalized_bounded

    mode_root = GITLAB_EXAMPLES / "modes"
    expected_modes = {
        "direct-mcp.gitlab-ci.yml",
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


def test_gitlab_mode_recipe_requires_replacing_main_variables() -> None:
    """An included recipe cannot override overlapping variables in the main file."""

    main_variables = yaml.safe_load(GITLAB_EXAMPLE.read_text(encoding="utf-8"))["variables"]
    recipe = yaml.safe_load(
        (GITLAB_EXAMPLES / "modes" / "unprotected-target.gitlab-ci.yml").read_text(encoding="utf-8")
    )["variables"]
    readme = (GITLAB_EXAMPLES / "README.md").read_text(encoding="utf-8")

    included_result = {**recipe, **main_variables}
    copied_result = {**main_variables, **recipe}
    assert included_result["OCR_REVIEW_CONTEXT_MODE"] == "off"
    assert included_result["OCR_AUTO_APPROVE"] == "true"
    assert copied_result["OCR_GITLAB_TARGET_PROTECTION_MODE"] == "unprotected"
    assert copied_result["OCR_REVIEW_CONTEXT_MODE"] == "metadata"
    assert copied_result["OCR_AUTO_APPROVE"] == "false"
    assert "replacing any keys already there" in readme
    assert "Do not merely `include` a mode file" in readme


def test_public_review_and_post_share_job_specific_result_paths() -> None:
    """Two CI jobs sharing a host must not reuse the same result/stderr names."""

    script = yaml.safe_load(GITLAB_EXAMPLE.read_text(encoding="utf-8"))["open_code_review"][
        "script"
    ]
    review = next(command for command in script if command.startswith("ocr-ci review "))
    post = next(command for command in script if command.startswith("ocr-ci post "))
    for path in ("/tmp/ocr-result-${CI_JOB_ID}.json", "/tmp/ocr-stderr-${CI_JOB_ID}.log"):
        assert path in review
        assert path in post
    readme = README.read_text(encoding="utf-8")
    assert 'review_result="/tmp/ocr-result-${CI_JOB_ID}.json"' in readme
    assert 'review_stderr="/tmp/ocr-stderr-${CI_JOB_ID}.log"' in readme


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

    assert "OCR_GITLAB_TARGET_PROTECTION_MODE:" not in example
    assert 'OCR_GITLAB_TARGET_PROTECTION_MODE: "unprotected"' in recipe
    assert 'OCR_REVIEW_CONTEXT_MODE: "metadata"' in recipe
    assert 'OCR_AUTO_APPROVE: "false"' in recipe

    for document in (configuration, gitlab, security, bounded):
        assert "OCR_GITLAB_TARGET_PROTECTION_MODE" in document
        assert "required" in document
        assert "unprotected" in document
    for document in (configuration, gitlab, security, bounded):
        assert "receipt v13" in document
    for phrase in (
        "Explicit empty strings",
        "context `off` or bounded `metadata`",
        "no enriched context or governed federation",
        "Rules read as untrusted guidance from T",
        "no structured guidance or accepted decisions",
        "Policy selection grants no new tool or credential authority",
    ):
        assert phrase in configuration
    limitation = (
        "The target branch was not protected in GitLab. "
        "This review ran in limited, comment-only mode."
    )
    assert limitation in operations
    assert "limited, comment-only mode" in configuration
    assert "limited, comment-only mode" in gitlab
    assert "Neither status changes OCR completeness" in gitlab
    assert "cannot reach the approval executor" in " ".join(security.split())
    assert "Neither profile changes result completeness" in " ".join(bounded.split())

    for phrase in (
        "Use two merge requests for the recommended setup",
        "Retrying that same merge request",
        "without a merge-request note and leaves the earlier review intact",
        "Code Owners and code-owner approval rules",
        "green advisory pipeline",
    ):
        assert phrase in gitlab
    assert "`CI_COMMIT_SHA` must match the authenticated current MR source" in operations
    assert "any populated MR-specific source SHA must agree" in operations
    assert "Synthetic merge-result, merge-train, missing" in operations
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
        text = path.read_text(encoding="utf-8").casefold()
        # GitLab's merge-result description is a real CI term, not a test fixture.
        text = re.sub(r"\bsynthetic merge(?:-result)? commit\b", "", text)
        text = text.replace("synthetic merge-result, merge-train", "merge-train")
        assert re.search(r"\bsynthetic\b", text) is None, path


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
    assert "./scripts/quality.sh check" not in release
    assert "uv run --no-sync pip-audit --skip-editable" in release


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
    assert "20261001" in workflow
    assert 'matrix={"include":[]}' in workflow
    assert "steps.schedule_gate.outputs.skip != 'true'" in workflow
    assert "through_tag:" in workflow
    assert "tag and through_tag are mutually exclusive" in workflow
    assert "UV_SETUP_OUTCOME: ${{ steps.setup_uv.outcome }}" in workflow
    assert "|| ! uv sync --locked --no-default-groups --python 3.14" in workflow
    assert "record-setup-failure" in workflow
    assert '--through-tag "${THROUGH_TAG}"' in workflow
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
    qualify_job = workflow.split("  qualify:\n", 1)[1].split("  aggregate:\n", 1)[0]
    dependency_sync = "uv sync --locked --no-default-groups --python 3.14"
    assert re.search(r"uses: astral-sh/setup-uv@[0-9a-f]{40}(?:\s|$)", qualify_job)
    assert dependency_sync in qualify_job
    assert qualify_job.index("name: Qualify candidate") < qualify_job.index(dependency_sync)
    assert qualify_job.index(dependency_sync) < qualify_job.index(
        "PYTHONPATH=src .venv/bin/python scripts/ocr_compat.py qualify"
    )
    assert "PYTHONPATH=src .venv/bin/python scripts/ocr_compat.py qualify" in qualify_job
    assert "PYTHONPATH=src python scripts/ocr_compat.py upsert-issue" in qualify_job
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
        "OCR 1.11.2 — toolkit 0.9.0 qualification predecessor",
        "OCR 1.11.3 — toolkit 0.9.0 target",
        "ocr.toolkit-advisory/v1",
        "ocr.llm-retry-report/v1",
        "not toolkit telemetry",
        "Deploy toolkit 0.8.2 or 0.8.3 directly with OCR 1.10.0",
        "Deploy toolkit 0.8.4 directly with OCR 1.10.1",
        "Deploy toolkit 0.8.5 directly with OCR 1.10.2",
        "Deploy toolkit 0.8.6 directly with OCR 1.11.0",
        "Deploy toolkit 0.8.7 directly with OCR 1.11.1",
        "Deploy toolkit 0.9.0 directly with OCR 1.11.3",
        "max-tools runtime behavior is unchanged",
        "max_completion_tokens=16384",
        "do not install OCR 1.9.10 as an intermediate step",
    ):
        assert contract in policy
    assert "Exact-tag manual dispatch is the" in policy
    assert "feature-bearing patch notes" in policy
    assert "--search" not in workflow
    assert "git push origin main" not in workflow
    assert "gh pr merge" not in workflow
    assert "automatic-safe" in workflow
    assert "human-review-required" in policy
    assert "never writes directly to `main`" in policy
    assert "Go MCP SDK v1.7.0" in policy
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
    assert "normalized to `50`" in operations
    assert "explicit `50` remain effectively `100`" in operations
    assert "only values above `100` raise the cap" in operations
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
    assert "completed runs after two days" in development
    assert "Active and newer runs remain untouched" in development
    assert "fail-closed ten-page limit per day" in development


def test_gitlab_operations_separate_model_metadata_from_review_connectivity() -> None:
    """Do not present an advisory green job or `/models` read as a usable review."""

    gitlab = GITLAB_GUIDE.read_text(encoding="utf-8")

    assert "run `ocr llm test`" in gitlab
    assert "metadata read is not a full review request" in gitlab
    assert "green pipeline with an allowed-to-fail OCR job" in gitlab
    assert "not evidence that OCR produced a usable review" in gitlab
