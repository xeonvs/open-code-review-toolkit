"""Stable integration contracts independent of the retired context renderer."""

from __future__ import annotations

import ast
import json
import re
from datetime import date

import pytest

from ocr_toolkit.context.adapters import parse_adapter_config
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.evidence.policy import parse_accepted_decisions
from ocr_toolkit.mcp_config import parse_mcp_servers
from tests.support import HELPER_DIR, PROJECT_ROOT


def test_project_rules_extend_instead_of_replacing_ocr_system_rules() -> None:
    """Keep project additions narrow so OCR owns generic language guidance."""

    payload = json.loads((HELPER_DIR / "rules.json").read_text(encoding="utf-8"))
    rules = payload["rules"]
    paths = [rule["path"] for rule in rules]

    assert not {
        "**/*.{py,pyi}",
        "**/*",
        "**/*.go",
        "**/*.php",
        "**/*.{js,jsx,ts,tsx,mjs,cjs}",
        "**/*.{tf,tfvars,hcl}",
    }.intersection(paths)
    assert paths.count("**/*.sql") == 1
    assert "Determine the SQL dialect" in rules[paths.index("**/*.sql")]["rule"]
    assert (
        "{requirements.yml,requirements.yaml,**/requirements.yml,**/requirements.yaml}"
    ) in paths
    assert "{pyproject.toml,uv.lock,**/pyproject.toml,**/uv.lock}" in paths
    assert payload["include"] == [
        "{*.j2,*.jinja,*.jinja2,*.twig}",
        "**/*.{j2,jinja,jinja2,twig}",
        "roles/*/templates/**",
        "**/roles/*/templates/**",
    ]
    assert paths[:3] == [
        "{roles/*/templates/**,**/roles/*/templates/**}",
        "{*.j2,*.jinja,*.jinja2,**/*.j2,**/*.jinja,**/*.jinja2}",
        "{*.twig,**/*.twig}",
    ]
    assert all(rule["merge_system_rule"] is True for rule in rules[:3])


def test_gitlab_ci_rule_preserves_unresolved_inheritance_uncertainty() -> None:
    payload = json.loads((HELPER_DIR / "rules.json").read_text(encoding="utf-8"))
    gitlab_rule = next(
        rule["rule"] for rule in payload["rules"] if ".gitlab-ci.yml" in rule["path"]
    )
    fixture_root = PROJECT_ROOT / "tests" / "fixtures" / "gitlab_ci_inheritance"
    qualification = json.loads((fixture_root / "expected.json").read_text(encoding="utf-8"))

    for field in (
        "allow_failure",
        "rules",
        "needs",
        "image",
        "before_script",
        "variables",
        "environment",
    ):
        assert field in gitlab_rule
    for contract in (
        "effective value as unknown",
        "explicit local override",
        "admitted bounded effective/compiled fact",
        "Do not infer a GitLab default",
        "defect, severity, or replacement suggestion",
    ):
        assert contract in gitlab_rule

    assert qualification == {
        "schema_version": "ocr.gitlab-ci-inheritance-qualification/v1",
        "project_policy": "review_job must remain advisory",
        "scenarios": [
            {
                "id": "unresolved_parent",
                "file": "unresolved-parent.yml",
                "compiled_fact": None,
                "expected": "unknown_no_finding",
            },
            {
                "id": "compiled_true",
                "file": "compiled-true.yml",
                "compiled_fact": "effective allow_failure is true",
                "expected": "proven_no_finding",
            },
            {
                "id": "compiled_false_advisory",
                "file": "compiled-false-advisory.yml",
                "compiled_fact": "effective allow_failure is false",
                "expected": "finding_allowed",
            },
            {
                "id": "local_false",
                "file": "local-false.yml",
                "compiled_fact": None,
                "expected": "finding_allowed",
            },
        ],
    }
    scenario_files = {
        item["id"]: (fixture_root / item["file"]).read_text(encoding="utf-8")
        for item in qualification["scenarios"]
    }
    assert "extends: .shared_review_job" in scenario_files["unresolved_parent"]
    assert "allow_failure" not in scenario_files["unresolved_parent"]
    assert "allow_failure" not in scenario_files["compiled_true"]
    assert "allow_failure" not in scenario_files["compiled_false_advisory"]
    assert "allow_failure: false" in scenario_files["local_false"]


def test_gitlab_example_preserves_review_gating_and_manual_self_test() -> None:
    """Freeze the intentional lint prerequisite and manual diagnostic boundary."""

    workflow = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
    review_job, self_test = workflow.split("open_code_review_self_test:", 1)

    assert workflow.index("  - lint") < workflow.index("  - ai_review")
    assert 'OCR_LLM_VALIDATE_MODEL: "false"' in workflow
    assert 'OCR_MAX_TOKENS_BUDGET: "0"' in workflow
    assert 'OCR_REVIEW_EFFORT: "medium"' in workflow
    assert 'OCR_MAX_TOOLS: "0"' in workflow
    assert "timeout: 45m" in review_job
    assert '--max-tools "${OCR_MAX_TOOLS:-0}"' in review_job
    assert '--max-tokens-budget "${OCR_MAX_TOKENS_BUDGET:-0}"' in review_job
    assert "lint:\n  stage: lint" in workflow
    assert "open_code_review:" in review_job
    assert "when: manual" not in review_job.split("open_code_review:", 1)[1]
    assert "when: manual" in self_test
    assert "env -u OCR_LLM_TOKEN ocr-ci preflight" in self_test


def test_gitlab_docs_match_the_current_review_surface() -> None:
    """Keep documented commands and ownership boundaries aligned with CI."""

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    docs = (PROJECT_ROOT / "docs" / "gitlab.md").read_text(encoding="utf-8")
    configuration = (PROJECT_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    workflow = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")
    manifest = json.loads(
        (PROJECT_ROOT / "compatibility" / "ocr-support.json").read_text(encoding="utf-8")
    )
    recommended = manifest["recommended_version"]
    recommended_entry = next(
        item for item in manifest["releases"] if item["version"] == recommended
    )
    linux_digest = next(
        asset["sha256"]
        for asset in recommended_entry["assets"]
        if asset["name"] == "opencodereview-linux-amd64"
    )

    for command in ("ocr-ci review", "ocr-ci post"):
        assert command in docs
        assert command in workflow
    for obsolete in ("git diff --name-only", "ocr review --commit", "ocr config set"):
        assert obsolete not in docs
        assert obsolete not in workflow
    assert "OCR_LLM_VALIDATE_MODEL" in configuration
    assert "OCR_LLM_VALIDATE_MODEL" in workflow
    assert "OCR_MAX_TOKENS_BUDGET" in configuration
    assert "OCR_MAX_TOKENS_BUDGET" in workflow
    assert "OCR_MAX_TOOLS" in configuration
    assert "OCR_MAX_TOOLS" in workflow
    assert "OCR_REVIEW_EFFORT" in configuration
    assert "OCR_REVIEW_EFFORT" in workflow
    assert "--preserve-private-artifacts" in configuration
    assert "without a posting receipt" in configuration
    assert "rejects this flag before OCR execution" in configuration
    assert "--preserve-private-artifacts" not in workflow
    assert "OCR_REVIEW_CONTEXT_MODE" in configuration
    assert 'OCR_REVIEW_CONTEXT_MODE: "off"' in workflow
    assert "OCR_TOOLKIT_VERSION" in workflow
    assert "OCR_TOOLKIT_CHECKSUMS_URL" in workflow
    assert (
        'OCR_TOOLKIT_CHECKSUMS_URL: "https://github.com/xeonvs/'
        'open-code-review-toolkit/releases/download/v${OCR_TOOLKIT_VERSION}/SHA256SUMS"' in workflow
    )
    assert 'pip install --no-deps "/tmp/${OCR_TOOLKIT_WHEEL}"' in workflow
    assert not re.search(r"releases/download/v\d+\.\d+\.\d+/SHA256SUMS", workflow)
    assert not re.search(r"pip install --no-deps /tmp/open_code_review_toolkit-\d", workflow)
    assert ".opencodereview/accepted-decisions.md" in configuration
    assert "ocr-accept: generated-client-timeout" in configuration
    assert "not a source-code parser" in configuration
    assert "come only from immutable target blobs" in security
    assert "source/head content never becomes policy evidence" in security
    assert f'OCR_VERSION: "v{recommended}"' in workflow
    assert "compatibility/ocr-support.json" in readme
    assert "../compatibility/ocr-support.json" in docs
    assert "../compatibility/ocr-support.json" in security
    assert f"v{recommended}" not in docs
    assert f"v{recommended}" not in security
    assert f'OCR_SHA256: "{linux_digest}"' in workflow
    assert "`Russian` is one example" in docs
    assert "ocr-ci preflight" in workflow
    assert "ocr-ci configure" in workflow
    assert "uv run pytest tests" not in workflow
    assert "--background-file" not in workflow
    assert 'set -- "$@" --background ' not in workflow
    assert "review-background.md" not in workflow
    assert '--from "${CI_MERGE_REQUEST_DIFF_BASE_SHA}"' in workflow
    assert '--to "${CI_MERGE_REQUEST_SOURCE_BRANCH_SHA}"' in workflow
    assert "Pin the exact recommended Open Code Review release" in security
    assert "when: manual" in workflow
    assert "env -u OCR_LLM_TOKEN" in workflow


def test_public_bounded_context_recipes_match_runtime_schemas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    example_root = PROJECT_ROOT / "examples" / "gitlab" / "context"
    adapter_policy = parse_policy((example_root / "policy-adapters.json").read_bytes())
    discussion_policy = parse_policy((example_root / "policy-discussions.json").read_bytes())
    ci_policy = parse_policy((example_root / "policy-ci-outcomes.json").read_bytes())
    stdio = parse_adapter_config((example_root / "adapters-stdio.json").read_text(encoding="utf-8"))
    remote = parse_adapter_config(
        (example_root / "adapters-remote.json").read_text(encoding="utf-8")
    )

    assert adapter_policy.schema_version == "ocr.review-context-policy/v2"
    assert adapter_policy.remediation_threads is not None
    assert adapter_policy.remediation_threads.account_classes == ("automation", "system", "user")
    assert adapter_policy.references[0].adapter == "tracker"
    assert discussion_policy.schema_version == "ocr.review-context-policy/v2"
    assert discussion_policy.remediation_threads is not None
    assert discussion_policy.references == ()
    assert ci_policy.schema_version == "ocr.review-context-policy/v3"
    assert ci_policy.ci_outcomes is not None
    assert ci_policy.ci_outcomes.required is False
    assert ci_policy.ci_outcomes.max_age_seconds == 86_400
    assert [check.name for check in ci_policy.ci_outcomes.checks] == [
        "functional-tests",
        "package",
    ]
    assert stdio[0].name == "tracker" and stdio[0].type == "stdio"
    assert remote[0].name == "tracker" and remote[0].type == "remote"
    assert remote[0].url == ("https://context-proxy.example.invalid/v1/authorize-and-resolve")
    assert adapter_policy.references[0].adapter == stdio[0].name == remote[0].name

    mode_root = PROJECT_ROOT / "examples" / "gitlab" / "modes"
    adapter_recipe = (mode_root / "enriched-adapters.gitlab-ci.yml").read_text(encoding="utf-8")
    adapter_json = adapter_recipe.split("OCR_REVIEW_CONTEXT_ADAPTERS_JSON: >-\n", 1)[
        1
    ].splitlines()[0]
    adapter_config = parse_adapter_config(adapter_json.strip())
    assert adapter_config[0].name == "tracker" and adapter_config[0].type == "remote"

    direct_recipe = (mode_root / "direct-mcp.gitlab-ci.yml").read_text(encoding="utf-8")
    direct_json = direct_recipe.split("OCR_MCP_SERVERS_JSON: >-\n", 1)[1].splitlines()[0]
    monkeypatch.setenv("REVIEW_EVIDENCE_MCP_AUTHORIZATION", "example-test-secret")
    direct_config = parse_mcp_servers(direct_json.strip(), profile="gitlab_mr")
    assert direct_config[0].name == "review_evidence"
    assert direct_config[0].transport == "remote"
    assert direct_config[0].tools == ["read_review_evidence"]


def test_public_accepted_decisions_recipe_matches_runtime_parser() -> None:
    recipe = (PROJECT_ROOT / "examples" / "gitlab" / "accepted-decisions.md").read_text(
        encoding="utf-8"
    )
    parsed = parse_accepted_decisions(
        recipe,
        changed_paths=("services/api/routes.py", "src/client/generated/client.py"),
        today=date(2026, 8, 22),
    )

    assert parsed.diagnostics == ()
    assert [decision.decision_id for decision in parsed.decisions] == [
        "generated-client-timeout",
        "staged-api-removal",
    ]
    assert all(decision.applicability == "applicable" for decision in parsed.decisions)


def test_public_docs_describe_the_established_m5_boundary() -> None:
    bounded = (PROJECT_ROOT / "docs" / "review-context.md").read_text(encoding="utf-8")
    configuration = (PROJECT_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    gitlab = (PROJECT_ROOT / "docs" / "gitlab.md").read_text(encoding="utf-8")
    operations = (PROJECT_ROOT / "docs" / "operations.md").read_text(encoding="utf-8")
    security = (PROJECT_ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    strategy = (PROJECT_ROOT / "docs" / "engineering" / "toolkit_strategy.md").read_text(
        encoding="utf-8"
    )
    roadmap = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    for contract in (
        "ocr.review-context-policy/v1",
        "ocr.review-context-policy/v2",
        "ocr.review-context-policy/v3",
        "ocr.context-store/v2",
        "ocr.context-adapter-request/v1",
        "ocr.context-adapter-response/v1",
        "context_list",
        "context_get",
        "receipt v7",
        "schema_version",
        "no store or receipt migration path",
        "semantic paraphrase",
    ):
        assert contract in bounded
    for document in (configuration, gitlab, operations, security):
        assert "receipt v7" in document
        assert "review-context.md" in document
    assert "M5's foundation is established in v0.7.0" in strategy
    assert "Toolkit 0.9.0 advances the current result boundary to receipt v7" in strategy
    assert "It is not protected-policy equivalence" in strategy
    assert "M5 Bounded review-context enrichment<br/>established" in roadmap
    assert "Toolkit 0.9.0 adds receipt-v7 source/target/protection binding" in roadmap
    assert "DLP-clean metadata, generic discussions, and adapter records" in strategy
    assert "v0.8.0 release tree completes its remediation/provider-neutral extension" in roadmap
    assert "explicit owner waiver for the separate enriched OCR+LLM receipt" in roadmap
    assert "still-present/evidence-resolved scenarios" in roadmap
    assert "protected release workflow" in roadmap
    assert "independent registry/GitHub readback" in roadmap
    assert "complete BL-023 broker remains planned" not in roadmap


def test_gitlab_example_does_not_inline_python_helpers() -> None:
    """Keep CI logic in the tested package rather than ad-hoc heredocs."""

    workflow = (HELPER_DIR / "ocr-review.gitlab-ci.yml").read_text(encoding="utf-8")

    assert "<<'PY'" not in workflow
    assert "OCR review scope:" not in workflow


def test_security_workflow_pins_the_local_gitleaks_version() -> None:
    """Keep CI and the repository-owned history scanner on one engine."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
    wrapper = (PROJECT_ROOT / "scripts" / "gitleaks.sh").read_text(encoding="utf-8")
    assert "Load pinned Gitleaks version" in workflow
    assert "./scripts/gitleaks.sh --version" in workflow
    assert "GITLEAKS_VERSION:" not in workflow
    assert wrapper.count("GITLEAKS_VERSION=") == 1


def test_release_workflows_do_not_duplicate_the_security_gitleaks_job() -> None:
    """Keep secret scanning local-before-push and in one hosted security job."""

    for workflow_name in ("testpypi.yml", "release.yml"):
        workflow = (PROJECT_ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )
        assert "gitleaks-action" not in workflow
        assert "install_gitleaks" not in workflow


def test_test_modules_have_no_duplicate_test_methods() -> None:
    """Reject silent test replacement caused by duplicate class method names."""

    duplicates: list[str] = []
    for test_path in sorted((PROJECT_ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            seen: dict[str, int] = {}
            for child in node.body:
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                previous = seen.get(child.name)
                if previous is not None:
                    duplicates.append(
                        f"{test_path.name}:{node.name}.{child.name}: {previous} and {child.lineno}"
                    )
                else:
                    seen[child.name] = child.lineno

    assert duplicates == []
