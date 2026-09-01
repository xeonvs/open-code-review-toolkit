"""Provider-neutral broker projections and dependency boundaries."""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from ocr_toolkit.context.broker import (
    ContextOrigin,
    prepare_discussion_records,
    prepare_remediation_records,
)
from ocr_toolkit.context.ci_outcomes import (
    CIOutcome,
    CIOutcomeSnapshot,
    prepare_ci_outcome_records,
)
from ocr_toolkit.context.policy import parse_policy
from tests.test_context_policy import (
    ci_policy_value,
    encoded_policy,
    policy_value,
    remediation_policy_value,
)


@dataclass(frozen=True)
class Discussion:
    thread: int = 0
    reply: int = 0
    author_class: str = "user"
    author_pseudonym: str = "actor-0123456789abcdef"
    body: str = "The current implementation still accepts an unchecked argument."
    created_at: int = 100
    updated_at: int = 110
    resolved: bool = False
    outdated: bool = False
    anchor: Mapping[str, object] = field(
        default_factory=lambda: {"path": "src/review.py", "line": 8}
    )
    version: str = "110"
    digest: str = "a" * 64


@dataclass(frozen=True)
class RemediationReply:
    order: int = 0
    author_class: str = "user"
    author_pseudonym: str = "actor-fedcba9876543210"
    body: str = "The branch now validates the argument before execution."
    created_at: int = 120
    updated_at: int = 130


@dataclass(frozen=True)
class RemediationThread:
    root_author_pseudonym: str = "actor-0123456789abcdef"
    root_body: str = "Finding: validate the command argument before execution."
    anchor_state: str = "current"
    replies: tuple[RemediationReply, ...] = (RemediationReply(),)
    completeness: str = "complete"
    resolved_count: int = 0
    outdated_count: int = 0
    version: str = "130"
    digest: str = "b" * 64


def ci_outcome(**changes: object) -> CIOutcome:
    """Build one digest-bound provider-neutral CI outcome."""

    value: dict[str, object] = {
        "check": "functional-tests",
        "status": "passed",
        "requirement": "required",
        "path_prefixes": ("src/", "tests/"),
        "origin": "same_revision_pipeline",
        "completed_at": 120,
    }
    value.update(changes)
    digest_value = {**value, "path_prefixes": list(value["path_prefixes"])}
    digest = hashlib.sha256(
        json.dumps(digest_value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CIOutcome(version=str(value["completed_at"]), digest=digest, **value)  # type: ignore[arg-type]


def test_context_core_does_not_import_a_forge_provider() -> None:
    context_root = Path(__file__).parents[1] / "src" / "ocr_toolkit" / "context"
    provider_imports: list[tuple[str, str]] = []
    for source_path in sorted(context_root.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            provider_imports.extend(
                (source_path.name, name)
                for name in names
                if name.startswith("ocr_toolkit.providers")
            )

    assert provider_imports == []


def test_common_discussion_projection_uses_explicit_provider_origin_and_rechecks_dlp() -> None:
    policy = parse_policy(encoded_policy()).forge_discussions
    assert policy is not None
    origin = ContextOrigin(source="forge:codehost_discussions", adapter="codehost", tenant="repo")

    records = prepare_discussion_records(
        (Discussion(), Discussion(body="private adapter value", digest="c" * 64)),
        policy=policy,
        origin=origin,
        expiry=200,
        forbidden=("private adapter value",),
    )

    assert len(records) == 1
    assert (records[0].source, records[0].adapter, records[0].tenant) == (
        "forge:codehost_discussions",
        "codehost",
        "repo",
    )
    assert "private adapter value" not in repr(records)


def test_common_discussion_publish_text_gets_publication_specific_dlp() -> None:
    value = policy_value()
    projection = value["forge_discussions"]["projections"]  # type: ignore[index]
    projection["publish"] = ["descriptor", "state", "text"]
    policy = parse_policy(encoded_policy(value)).forge_discussions
    assert policy is not None
    origin = ContextOrigin(source="forge:codehost_discussions", adapter="codehost", tenant="repo")

    records = prepare_discussion_records(
        (
            Discussion(body="Safe publication text."),
            Discussion(
                body="See [private destination](https://example.invalid/private).",
                digest="c" * 64,
            ),
        ),
        policy=policy,
        origin=origin,
        expiry=200,
    )

    assert len(records) == 1
    assert records[0].projections["publish"]["text"] == "Safe publication text."


def test_common_remediation_projection_is_fixed_model_only_and_rechecks_every_text() -> None:
    policy = parse_policy(encoded_policy(remediation_policy_value())).remediation_threads
    assert policy is not None
    origin = ContextOrigin(
        source="forge:codehost_remediation_threads",
        adapter="codehost",
        tenant="repo",
    )
    rejected = RemediationThread(
        replies=(RemediationReply(body="contact reviewer@example.invalid"),),
        digest="c" * 64,
    )

    records = prepare_remediation_records(
        (RemediationThread(), rejected),
        policy=policy,
        origin=origin,
        expiry=200,
    )

    assert len(records) == 1
    record = records[0]
    assert (record.source, record.adapter, record.tenant) == (
        "forge:codehost_remediation_threads",
        "codehost",
        "repo",
    )
    assert set(record.projections["model"]) == {"descriptor", "remediation_thread"}
    assert record.projections["publish"] == {"descriptor": "remediation_thread"}
    assert "reviewer@example.invalid" not in repr(records)


def test_common_ci_projection_is_provider_neutral_scoped_and_dlp_checked() -> None:
    """Admit a fake-provider outcome without forge IDs or unsafe protected text."""

    policy_value = ci_policy_value()
    policy_value["ci_outcomes"]["checks"].append(  # type: ignore[index,union-attr]
        {"name": "private-check", "path_prefixes": ["private/"]}
    )
    policy = parse_policy(encoded_policy(policy_value)).ci_outcomes
    assert policy is not None
    safe = ci_outcome()
    secret = ci_outcome(check="private-check", path_prefixes=("private/",), completed_at=121)

    records = prepare_ci_outcome_records(
        CIOutcomeSnapshot("complete", (safe, secret), 0, 0),
        policy=policy,
        now=150,
        forbidden=("private-check",),
    )

    assert len(records) == 1
    record = records[0]
    assert record.resource_class == "ci_outcome"
    assert record.mutable is False
    assert record.projections["model"]["ci_outcome"] == {
        "check": "functional-tests",
        "revision": "reviewed_head",
        "status": "passed",
        "requirement": "required",
        "scope": {"mode": "declared", "path_prefixes": ["src/", "tests/"]},
        "origin": "same_revision_pipeline",
        "completed_at": 120,
    }
    assert "gitlab" not in repr(record.projections)


@pytest.mark.parametrize(
    "record",
    [
        replace(Discussion(), body="contact reviewer@example.invalid"),
        replace(Discussion(), author_class="owner"),
        replace(Discussion(), author_pseudonym="raw-user-7"),
        replace(Discussion(), anchor={"path": "src/review.py", "column": 4}),
        replace(Discussion(), anchor={"path": "contact@example.invalid", "line": 8}),
        replace(Discussion(), anchor={"path": "src/review.py", "line": True}),
        replace(Discussion(), resolved="yes"),
        replace(Discussion(), created_at=True),
        replace(Discussion(), digest="not-a-digest"),
        replace(Discussion(), version="two\nlines"),
    ],
)
def test_common_discussion_projection_rejects_hostile_projected_shapes(
    record: Discussion,
) -> None:
    """Reject provider records that violate the neutral discussion projection."""

    value = policy_value()
    projected = sorted(
        {
            "anchor",
            "author_class",
            "author_pseudonym",
            "created_at",
            "descriptor",
            "digest",
            "expiry",
            "outdated",
            "resolved",
            "state",
            "text",
            "updated_at",
            "version",
        }
    )
    value["forge_discussions"]["projections"] = {  # type: ignore[index]
        "retrieve": projected,
        "model": projected,
        "publish": ["descriptor", "state"],
        "retain": ["digest", "expiry", "state", "version"],
    }
    policy = parse_policy(encoded_policy(value)).forge_discussions
    assert policy is not None

    records = prepare_discussion_records(
        (record,),
        policy=policy,
        origin=ContextOrigin(
            source="forge:codehost_discussions",
            adapter="codehost",
            tenant="repo",
        ),
        expiry=200,
    )

    assert records == ()


@pytest.mark.parametrize(
    "record",
    [
        replace(RemediationThread(), root_author_pseudonym="raw-user-7"),
        replace(RemediationThread(), root_author_pseudonym=None),
        replace(RemediationThread(), anchor_state="unknown"),
        replace(RemediationThread(), completeness="unknown"),
        replace(RemediationThread(), resolved_count=True),
        replace(RemediationThread(), outdated_count=-1),
        replace(RemediationThread(), digest="not-a-digest"),
        replace(RemediationThread(), version=""),
        replace(RemediationThread(), replies=()),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), order=1),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), author_class="toolkit_bot"),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), author_pseudonym="raw-user-7"),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), author_pseudonym=None),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), created_at=True),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), updated_at=119),),
        ),
        replace(
            RemediationThread(),
            replies=(replace(RemediationReply(), updated_at=201),),
        ),
        replace(RemediationThread(), resolved_count=3),
        replace(RemediationThread(), anchor_state="outdated", outdated_count=0),
    ],
)
def test_common_remediation_projection_rejects_impossible_provider_shapes(
    record: RemediationThread,
) -> None:
    """Reject impossible remediation records before common store admission."""

    policy = parse_policy(encoded_policy(remediation_policy_value())).remediation_threads
    assert policy is not None

    records = prepare_remediation_records(
        (record,),
        policy=policy,
        origin=ContextOrigin(
            source="forge:codehost_remediation_threads",
            adapter="codehost",
            tenant="repo",
        ),
        expiry=200,
    )

    assert records == ()
