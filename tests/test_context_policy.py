"""Exact protected policy, recognizer, and context-DLP contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit.context.contracts import ContextContractError, TextBudgets
from ocr_toolkit.context.dlp import check_text
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
    assert check_text("dev@example.invalid", budgets=TextBudgets(100, 200, 2)).reason == "pii"
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
