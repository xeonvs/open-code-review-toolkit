"""Contracts for pure target-derived repository policy providers."""

from __future__ import annotations

from datetime import date

import pytest

from ocr_toolkit.evidence.policy import (
    POLICY_PROVIDERS,
    guidance_document,
    parse_accepted_decisions,
)
from ocr_toolkit.evidence.policy.scopes import PolicyScopeError, matches_scope, validate_scope


def test_static_registry_has_no_dynamic_provider_surface() -> None:
    """Keep policy extension explicit and incapable of repository-controlled loading."""

    assert [(provider.name, provider.kind) for provider in POLICY_PROVIDERS] == [
        ("accepted-decisions", "repository.accepted_decision"),
        ("project-guidance", "repository.guidance"),
    ]


def test_parser_preserves_legacy_decision_and_structures_optional_metadata() -> None:
    """Keep heading-and-rationale documents valid while adding scoped metadata."""

    result = parse_accepted_decisions(
        """
# Decisions

## Generated client timeout
The generated client keeps the provider timeout.
- Scope: services/api/**
- Scope: clients/*.py
- Category: compatibility
- Owner: client-platform
- Review after: 2026-12-01
- Future field: remains ordinary rationale

## Legacy choice
Keep the old shape.
""",
        changed_paths=("clients/demo.py", "docs/readme.md", "services/api/main.py"),
        today=date(2026, 8, 13),
    )

    assert result.diagnostics == ()
    first, legacy = result.decisions
    assert first.decision_id == "generated-client-timeout"
    assert first.scopes == ("services/api/**", "clients/*.py")
    assert first.matched_paths == ("clients/demo.py", "services/api/main.py")
    assert first.applicability == "applicable"
    assert first.category == "compatibility"
    assert first.owner == "client-platform"
    assert not first.stale
    assert "Future field" in first.rationale
    assert legacy.decision_id == "legacy-choice"
    assert legacy.scopes == ()
    assert legacy.applicability == "applicable"


def test_parser_isolates_bad_metadata_and_duplicate_ids() -> None:
    """Reject ambiguous authority without invalidating an unrelated decision."""

    result = parse_accepted_decisions(
        """
## Same choice
First.
- Scope: ../escape

## same--choice
Second.

## Safe
Still available.
- Review after: 2026-1-2
- Owner: first
- Owner: second
""",
        changed_paths=("src/app.py",),
        today=date(2026, 8, 13),
    )

    assert [item.decision_id for item in result.decisions] == ["safe"]
    assert result.decisions[0].owner == "first"
    assert result.decisions[0].review_after is None
    assert result.diagnostics == (
        "same-choice: unsafe scope ignored",
        "safe: invalid review after metadata",
        "safe: duplicate owner metadata ignored",
        "duplicate normalized decision id ignored: same-choice",
    )


def test_review_after_is_stale_from_that_utc_date_without_disappearing() -> None:
    result = parse_accepted_decisions(
        "## Existing\nRationale.\n- Review after: 2026-08-13\n",
        changed_paths=("src/app.py",),
        today=date(2026, 8, 13),
    )

    assert result.decisions[0].stale is True
    assert result.decisions[0].rationale == "Rationale."


@pytest.mark.parametrize(
    "scope",
    [
        "",
        "/root",
        "../escape",
        "safe/../escape",
        "safe//file",
        r"safe\\file",
        "!src/**",
        "src/[ab].py",
        "src/**.py",
        "src/@(a).py",
    ],
)
def test_scope_grammar_rejects_unsafe_or_ambiguous_syntax(scope: str) -> None:
    with pytest.raises(PolicyScopeError):
        validate_scope(scope)


@pytest.mark.parametrize(
    ("scope", "path", "expected"),
    [
        ("src/*.py", "src/app.py", True),
        ("src/*.py", "src/nested/app.py", False),
        ("services/**", "services/api/main.py", True),
        ("services/**/test?.py", "services/api/unit/test1.py", True),
        ("Services/**", "services/api.py", False),
    ],
)
def test_scope_matching_is_case_sensitive_and_segment_aware(
    scope: str, path: str, expected: bool
) -> None:
    assert matches_scope(scope, path) is expected


@pytest.mark.parametrize("path", [r"src\\app.py", "../app.py", "-option", "src/line\nfeed"])
def test_scope_matching_rejects_non_normalized_candidate_paths(path: str) -> None:
    """Fail closed when hostile persisted applicability supplies an unsafe path."""

    assert not matches_scope("**", path)


def test_guidance_applicability_and_precedence_are_toolkit_generated() -> None:
    root = guidance_document("AGENTS.md", "root text", ("services/api/main.py",))
    nested_agents = guidance_document(
        "services/api/AGENTS.md", "nested text", ("services/api/main.py", "web/app.ts")
    )
    nested_claude = guidance_document(
        "services/api/CLAUDE.md", "other text", ("services/api/main.py",)
    )

    assert root.scope == "**"
    assert root.matched_paths == ("services/api/main.py",)
    assert nested_agents.scope == "services/api/**"
    assert nested_agents.matched_paths == ("services/api/main.py",)
    assert (nested_agents.depth, nested_agents.document_order) == (2, 0)
    assert (nested_claude.depth, nested_claude.document_order) == (2, 1)


def test_scope_limit_fails_closed_without_widening_decision() -> None:
    """Never turn truncated scope metadata into broad applicability."""

    scopes = "\n".join(f"- Scope: services/service-{index}/**" for index in range(65))
    result = parse_accepted_decisions(
        f"## Bounded\nReason.\n{scopes}\n",
        changed_paths=("services/service-0/main.py",),
        today=date(2026, 8, 13),
    )

    assert result.decisions[0].applicability == "invalid"
    assert result.decisions[0].matched_paths == ()
    assert result.diagnostics == ("bounded: scope limit exceeded",)


@pytest.mark.parametrize(
    "path",
    ["../AGENTS.md", "/AGENTS.md", r"services\\AGENTS.md", "services/../AGENTS.md"],
)
def test_guidance_rejects_unsafe_repository_paths(path: str) -> None:
    """Do not derive scope or precedence from traversal or platform-specific paths."""

    with pytest.raises(ValueError):
        guidance_document(path, "text", ("services/app.py",))


def test_global_guidance_has_repository_wide_precedence() -> None:
    """Treat historical root-only sources as global regardless of their stored path."""

    document = guidance_document(
        ".github/copilot-instructions.md",
        "Synthetic global guidance.",
        ("services/app.py",),
    )

    assert document.scope == "**"
    assert document.depth == 0
    assert document.document_order == 2
