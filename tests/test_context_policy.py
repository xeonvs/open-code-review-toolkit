"""Exact protected policy, recognizer, and context-DLP contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit.context.contracts import ContextContractError, TextBudgets
from ocr_toolkit.context.dlp import ForbiddenMatcher, check_text
from ocr_toolkit.context.policy import POLICY_PATH, load_protected_policy, parse_policy
from ocr_toolkit.context.recognizers import recognize
from ocr_toolkit.evidence.repository import GitRepositoryReader


def policy_value() -> dict[str, object]:
    projection = {
        "retrieve": ["descriptor", "digest", "expiry", "state", "text", "version"],
        "model": ["descriptor", "state", "text"],
        "publish": ["descriptor", "state"],
        "retain": ["digest", "expiry", "state", "version"],
    }
    return {
        "schema_version": "ocr.review-context-policy/v1",
        "budgets": {
            "max_records": 32,
            "max_chars": 48000,
            "max_bytes": 96000,
            "max_lines": 1200,
            "timeout_ms": 15000,
        },
        "forge_discussions": {
            "required": False,
            "account_classes": ["automation", "user"],
            "include_resolved": False,
            "include_outdated": False,
            "max_age_seconds": 2592000,
            "max_threads": 20,
            "max_replies_per_thread": 10,
            "max_items": 100,
            "budgets": {"max_chars": 12000, "max_bytes": 24000, "max_lines": 300},
            "projections": projection,
        },
        "references": [
            {
                "adapter": "tracker",
                "tenant": "engineering",
                "resource_class": "issue",
                "recognizer": {"type": "issue_key", "prefix": "DEMO"},
                "required": True,
                "max_records": 8,
                "max_age_seconds": 31536000,
                "budgets": {"max_chars": 4000, "max_bytes": 8000, "max_lines": 100},
                "projections": projection,
            }
        ],
    }


def encoded_policy(value: dict[str, object] | None = None) -> bytes:
    return json.dumps(value or policy_value(), sort_keys=True).encode("utf-8")


def remediation_policy_value() -> dict[str, object]:
    value = policy_value()
    value["schema_version"] = "ocr.review-context-policy/v2"
    value["remediation_threads"] = {
        "required": False,
        "account_classes": ["automation", "user"],
        "include_resolved": True,
        "include_outdated": False,
        "max_age_seconds": 2592000,
        "max_threads": 10,
        "max_replies_per_thread": 8,
        "max_items": 80,
        "budgets": {"max_chars": 12000, "max_bytes": 24000, "max_lines": 300},
    }
    return value


def ci_policy_value() -> dict[str, object]:
    """Build one protected policy v3 with exact CI check scopes."""

    value = remediation_policy_value()
    value["schema_version"] = "ocr.review-context-policy/v3"
    value["ci_outcomes"] = {
        "checks": [
            {"name": "functional-tests", "path_prefixes": ["src/", "tests/"]},
            {"name": "package", "path_prefixes": ["pyproject.toml"]},
        ]
    }
    return value


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def test_policy_parser_accepts_exact_protected_contract() -> None:
    parsed = parse_policy(encoded_policy())

    assert parsed.schema_version == "ocr.review-context-policy/v1"
    assert len(parsed.digest) == 64
    assert parsed.forge_discussions is not None
    assert parsed.forge_discussions.account_classes == ("automation", "user")
    assert parsed.references[0].recognizer.prefix == "DEMO"
    assert parsed.references[0].projections.retain == (
        "digest",
        "expiry",
        "state",
        "version",
    )


def test_policy_v2_adds_fixed_remediation_threads_without_changing_v1() -> None:
    legacy = parse_policy(encoded_policy())
    current = parse_policy(encoded_policy(remediation_policy_value()))

    assert legacy.schema_version == "ocr.review-context-policy/v1"
    assert legacy.remediation_threads is None
    assert current.schema_version == "ocr.review-context-policy/v2"
    assert current.remediation_threads is not None
    assert current.remediation_threads.account_classes == ("automation", "user")
    assert current.remediation_threads.max_replies_per_thread == 8


def test_policy_v3_adds_exact_ci_scopes_with_conservative_defaults() -> None:
    """Keep CI authority protected, exact, bounded, and opt-in."""

    parsed = parse_policy(encoded_policy(ci_policy_value()))

    assert parsed.schema_version == "ocr.review-context-policy/v3"
    assert parsed.ci_outcomes is not None
    assert parsed.ci_outcomes.required is False
    assert parsed.ci_outcomes.max_age_seconds == 86_400
    assert parsed.ci_outcomes.checks[0].name == "functional-tests"
    assert parsed.ci_outcomes.checks[0].path_prefixes == ("src/", "tests/")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"schema_version": "ocr.review-context-policy/v2"}),
        lambda value: value["ci_outcomes"].update({"unknown": True}),
        lambda value: value["ci_outcomes"].update({"required": "yes"}),
        lambda value: value["ci_outcomes"].update({"max_age_seconds": 59}),
        lambda value: value["ci_outcomes"].update(
            {"checks": [{"name": "functional-tests", "path_prefixes": ["../tests/"]}]}
        ),
        lambda value: value["ci_outcomes"].update(
            {"checks": [{"name": "functional-tests", "path_prefixes": []}]}
        ),
        lambda value: value["ci_outcomes"].update(
            {
                "checks": [
                    {
                        "name": "functional-tests",
                        "path_prefixes": ["https://private.invalid/tests/"],
                    }
                ]
            }
        ),
        lambda value: value["ci_outcomes"].update(
            {
                "checks": [
                    {"name": "duplicate", "path_prefixes": ["src/"]},
                    {"name": "duplicate", "path_prefixes": ["tests/"]},
                ]
            }
        ),
        lambda value: value["ci_outcomes"].update(
            {"checks": [{"name": "unsafe\u202e", "path_prefixes": ["src/"]}]}
        ),
    ],
)
def test_policy_v3_rejects_ci_authority_expansion(mutation: object) -> None:
    """Reject legacy, ambiguous, unsafe, or unbounded CI policy forms."""

    value = ci_policy_value()
    assert callable(mutation)
    mutation(value)

    with pytest.raises(ContextContractError):
        parse_policy(encoded_policy(value))


@pytest.mark.parametrize(
    "value",
    [
        {**policy_value(), "schema_version": {}},
        {
            **policy_value(),
            "forge_discussions": {
                **policy_value()["forge_discussions"],  # type: ignore[dict-item]
                "account_classes": [{}],
            },
        },
        {
            **remediation_policy_value(),
            "remediation_threads": {
                **remediation_policy_value()["remediation_threads"],  # type: ignore[dict-item]
                "account_classes": [{}],
            },
        },
    ],
)
def test_policy_rejects_unhashable_closed_values(value: dict[str, object]) -> None:
    """Map hostile closed-list values to the policy contract error boundary."""

    with pytest.raises(ContextContractError):
        parse_policy(encoded_policy(value))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"schema_version": "ocr.review-context-policy/v1"}),
        lambda value: value["remediation_threads"].update({"projections": {}}),
        lambda value: value["remediation_threads"].update(
            {"account_classes": ["toolkit_bot", "user"]}
        ),
        lambda value: value["references"][0].update(
            {"resource_class": "remediation_thread", "recognizer": {"type": "explicit"}}
        ),
    ],
)
def test_policy_rejects_remediation_authority_expansion(mutation: object) -> None:
    value = remediation_policy_value()
    assert callable(mutation)
    mutation(value)

    with pytest.raises(ContextContractError):
        parse_policy(encoded_policy(value))


def test_protected_loader_uses_only_exact_policy_sha_and_path() -> None:
    calls: list[tuple[str, str]] = []

    def read_blob(sha: str, path: str) -> bytes:
        calls.append((sha, path))
        return encoded_policy()

    parsed = load_protected_policy(read_blob, policy_sha="a" * 40)

    assert parsed.references[0].adapter == "tracker"
    assert calls == [("a" * 40, POLICY_PATH)]


def test_protected_loader_crosses_real_immutable_git_and_rejects_unsafe_objects(
    tmp_path: Path,
) -> None:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "agent@example.invalid")
    git(tmp_path, "config", "user.name", "Synthetic Agent")
    policy_path = tmp_path / POLICY_PATH
    policy_path.parent.mkdir()
    policy_path.write_bytes(encoded_policy())
    git(tmp_path, "add", POLICY_PATH)
    git(tmp_path, "commit", "-qm", "protected policy")
    target_sha = git(tmp_path, "rev-parse", "HEAD")

    source_value = policy_value()
    source_value["references"][0]["recognizer"] = {"type": "issue_key", "prefix": "SOURCE"}
    policy_path.write_bytes(encoded_policy(source_value))
    git(tmp_path, "add", POLICY_PATH)
    git(tmp_path, "commit", "-qm", "source policy cannot expand access")
    source_sha = git(tmp_path, "rev-parse", "HEAD")
    reader = GitRepositoryReader(tmp_path)

    assert (
        load_protected_policy(reader.read_blob, policy_sha=target_sha)
        .references[0]
        .recognizer.prefix
        == "DEMO"
    )
    assert (
        load_protected_policy(reader.read_blob, policy_sha=source_sha)
        .references[0]
        .recognizer.prefix
        == "SOURCE"
    )

    policy_path.unlink()
    policy_path.symlink_to("../source-controlled.json")
    git(tmp_path, "add", POLICY_PATH)
    git(tmp_path, "commit", "-qm", "unsafe symlink")
    with pytest.raises(ContextContractError, match="unavailable"):
        load_protected_policy(reader.read_blob, policy_sha=git(tmp_path, "rev-parse", "HEAD"))

    policy_path.unlink()
    git(tmp_path, "rm", "--cached", "-q", POLICY_PATH)
    git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{target_sha},{POLICY_PATH}")
    git(tmp_path, "commit", "-qm", "unsafe submodule entry")
    with pytest.raises(ContextContractError, match="unavailable"):
        load_protected_policy(reader.read_blob, policy_sha=git(tmp_path, "rev-parse", "HEAD"))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"schema_version": "future"}),
        lambda value: value.update({"references": [], "forge_discussions": None}),
        lambda value: value["references"][0]["projections"].update({"model": ["author_class"]}),
        lambda value: value["references"][0]["projections"].update({"retain": ["text"]}),
        lambda value: value["references"][0].update(
            {"recognizer": {"type": "issue_key", "prefix": "unsafe.*"}}
        ),
    ],
)
def test_policy_parser_rejects_unknown_impossible_or_configurable_grammar(mutation: object) -> None:
    value = policy_value()
    assert callable(mutation)
    mutation(value)

    with pytest.raises(ContextContractError):
        parse_policy(encoded_policy(value))


def test_policy_parser_rejects_duplicates_utf8_and_size() -> None:
    with pytest.raises(ContextContractError, match="duplicate"):
        parse_policy(b'{"schema_version":"ocr.review-context-policy/v1","schema_version":"x"}')
    with pytest.raises(ContextContractError, match="UTF-8"):
        parse_policy(b"\xff")
    with pytest.raises(ContextContractError, match="oversized"):
        parse_policy(b"x" * (64 * 1024 + 1))


def test_fixed_recognizers_are_bounded_deduplicated_and_origin_exact() -> None:
    issue = parse_policy(encoded_policy()).references[0]
    candidates = recognize(
        "DEMO-7 demo-8 XDEMO-9 DEMO-7 DEMO-1234567890123",
        resource_class="issue",
        policy=issue.recognizer,
    )
    assert [item.value for item in candidates] == ["DEMO-7"]

    value = policy_value()
    value["references"] = [
        {
            **value["references"][0],
            "resource_class": "document",
            "recognizer": {
                "type": "https_url",
                "origin": "https://docs.example.invalid",
                "path_prefix": "/safe/",
            },
        }
    ]
    url_policy = parse_policy(encoded_policy(value)).references[0]
    urls = recognize(
        "https://docs.example.invalid/safe/page?view=1 "
        "https://docs.example.invalid/unsafe/page "
        "https://user@docs.example.invalid/safe/private",
        resource_class="document",
        policy=url_policy.recognizer,
    )
    assert [item.value for item in urls] == ["https://docs.example.invalid/safe/page?view=1"]

    hostile = recognize(
        "https://docs.example.invalid:bad/safe/ignored "
        "https://docs.example.invalid:99999/safe/ignored "
        "https://docs.example.invalid/safe/accepted",
        resource_class="document",
        policy=url_policy.recognizer,
    )
    assert [item.value for item in hostile] == ["https://docs.example.invalid/safe/accepted"]


@pytest.mark.parametrize(
    "origin",
    [
        "https://docs.example.invalid:bad",
        "https://docs.example.invalid:99999",
        "https://docs.example.invalid:",
        "https://[invalid",
        "https://:443",
    ],
)
def test_https_recognizer_rejects_ambiguous_authorities(origin: str) -> None:
    value = policy_value()
    value["references"][0]["resource_class"] = "document"  # type: ignore[index]
    value["references"][0]["recognizer"] = {  # type: ignore[index]
        "type": "https_url",
        "origin": origin,
        "path_prefix": "/safe/",
    }

    with pytest.raises(ContextContractError, match="unsafe"):
        parse_policy(encoded_policy(value))


def test_explicit_recognizer_never_searches_arbitrary_repository_text() -> None:
    value = policy_value()
    value["references"][0]["recognizer"] = {"type": "explicit"}
    policy = parse_policy(encoded_policy(value)).references[0]

    candidates = recognize(
        "DEMO-1 [[context:issue:DEMO-2]] [[context:document:page]]",
        resource_class="issue",
        policy=policy.recognizer,
    )

    assert [item.value for item in candidates] == ["DEMO-2"]


def test_context_dlp_applies_multibyte_units_pii_secrets_and_publication_laundering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budgets = TextBudgets(max_chars=4, max_bytes=8, max_lines=1)
    assert check_text("éééé", budgets=budgets).admitted is True
    assert check_text("ééééé", budgets=budgets).reason == "limit"
    assert check_text("a\nb", budgets=budgets).reason == "limit"
    email = check_text("dev@example.invalid", budgets=TextBudgets(100, 200, 2))
    phone = check_text("Call +420 123 456 789", budgets=TextBudgets(100, 200, 2))
    technical_id = check_text(
        "12345678-1234-5678-1234-123456789012",
        budgets=TextBudgets(100, 200, 2),
    )
    assert (email.reason, email.detector) == ("pii", "email:normalized")
    assert (phone.reason, phone.detector) == ("pii", "phone:normalized")
    assert (technical_id.reason, technical_id.detector) == ("pii", "phone:normalized")
    assert check_text("Build 123456789012345", budgets=TextBudgets(100, 200, 2)).admitted
    assert check_text("sha-a1234567890abcdef", budgets=TextBudgets(100, 200, 2)).admitted
    monkeypatch.setenv("SYNTHETIC_CONTEXT_SECRET", "not-a-real-token-value")
    assert check_text("not-a-real-token-value", budgets=TextBudgets(100, 200, 2)).reason == "secret"
    assert (
        check_text(
            "[safe label](https://example.invalid)",
            budgets=TextBudgets(100, 200, 2),
            publication=True,
        ).reason
        == "laundering"
    )
    for hidden in (
        "<!-- synthetic&#64;example.invalid -->safe",
        '<span title="synthetic&#64;example.invalid">safe</span>',
        "&lt;!-- synthetic&#x40;example.invalid --&gt;safe",
        "<code>safe</code>",
    ):
        assert (
            check_text(
                hidden,
                budgets=TextBudgets(200, 400, 2),
                publication=True,
            ).admitted
            is False
        )
    assert check_text(
        "x < y and y > z", budgets=TextBudgets(100, 200, 2), publication=True
    ).admitted
    assert (
        ForbiddenMatcher.compile(("<!-- hidden-only protected value -->",)).match_reason(
            "<!-- hidden-only protected value -->"
        )
        == "forbidden"
    )
