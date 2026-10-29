"""Structured policy rejection boundaries and exact applicability correlation."""

from __future__ import annotations

from datetime import date

import pytest

from ocr_toolkit.evidence.policy import guidance_document
from ocr_toolkit.evidence.policy.contracts import AcceptedDecision
from ocr_toolkit.evidence.policy.schema import (
    is_legacy_policy_value,
    validate_policy_applicability,
    validate_policy_record,
)

PATHS = ("src/app.py", "src/package/helper.py")


def policy_value(kind: str):
    if kind == "repository.guidance":
        return guidance_document(
            "src/AGENTS.md", "Inspect actual boundaries.", PATHS
        ).evidence_value()
    return AcceptedDecision(
        "safe-choice",
        "A scoped choice",
        "Keep current behavior.",
        ("src/**",),
        "compatibility",
        "maintainer",
        date(2030, 1, 1),
        False,
        "applicable",
        PATHS,
    ).evidence_value()


@pytest.mark.parametrize("kind", ("repository.guidance", "repository.accepted_decision"))
@pytest.mark.parametrize("state", ([], {}))
def test_minimized_unhashable_policy_state_regressions(kind: str, state: object) -> None:
    value = policy_value(kind)
    value["fact"]["applicability"] = state
    with pytest.raises(ValueError):
        validate_policy_record(kind, value)


@pytest.mark.parametrize("kind", ("repository.guidance", "repository.accepted_decision"))
def test_closed_policy_root_and_value_budgets(kind: str) -> None:
    for value in (
        None,
        [],
        {},
        {"identity": "", "fact": {}},
        {"identity": False, "fact": {}},
        {**policy_value(kind), "extra": True},
    ):
        with pytest.raises(ValueError):
            validate_policy_record(kind, value)
    value = policy_value(kind)
    value["fact"]["text"] = "x" * 56000
    with pytest.raises(ValueError, match="budget"):
        validate_policy_record(kind, value)


@pytest.mark.parametrize(
    "field,value",
    (
        ("schema_version", "future"),
        ("decision_id", "other"),
        ("title", ""),
        ("title", "x" * 257),
        ("rationale", None),
        ("scopes", None),
        ("scopes", ["src/**"] * 65),
        ("scopes", ["../unsafe"]),
        ("matched_paths", ["../unsafe"]),
        ("matched_paths", ["docs/other.py"]),
        ("matched_paths", []),
        ("applicability", "not_applicable"),
        ("applicability", "invalid"),
        ("applicability", "future"),
        ("owner", ""),
        ("owner", False),
        ("category", "x" * 513),
        ("review_after", False),
        ("review_after", "2030-1-1"),
        ("review_after", "2030-W01-1"),
        ("stale", 0),
    ),
)
def test_decision_schema_rejects_malformed_or_inconsistent_fact(field: str, value: object) -> None:
    record = policy_value("repository.accepted_decision")
    record["fact"][field] = value
    with pytest.raises(ValueError):
        validate_policy_record("repository.accepted_decision", record)


@pytest.mark.parametrize(
    "field,value",
    (
        ("schema_version", "future"),
        ("text", False),
        ("text", "x" * 64001),
        ("scope", "docs/**"),
        ("document_type", "unknown"),
        ("applicability", "future"),
        ("applicability", "not_applicable"),
        ("matched_paths", None),
        ("matched_paths", [False]),
        ("matched_paths", ["../unsafe"]),
        ("matched_paths", ["docs/other.py"]),
        ("matched_paths", []),
        ("precedence", {}),
    ),
)
def test_guidance_schema_rejects_malformed_or_inconsistent_fact(field: str, value: object) -> None:
    record = policy_value("repository.guidance")
    record["fact"][field] = value
    with pytest.raises(ValueError):
        validate_policy_record("repository.guidance", record)


def test_guidance_identity_and_precedence_are_derived_from_the_exact_path() -> None:
    for field, value in (
        ("depth", True),
        ("depth", 3),
        ("document_order", True),
        ("document_order", 5),
        ("path", "other/AGENTS.md"),
    ):
        record = policy_value("repository.guidance")
        record["fact"]["precedence"][field] = value
        with pytest.raises(ValueError, match="precedence"):
            validate_policy_record("repository.guidance", record)
    record = policy_value("repository.guidance")
    record["identity"] = record["fact"]["path"] = "src/README.md"
    with pytest.raises(ValueError, match="guidance path"):
        validate_policy_record("repository.guidance", record)


def test_legacy_text_shape_remains_frozen_and_new_kind_requires_an_owner() -> None:
    assert is_legacy_policy_value({"text": "legacy context"})
    assert not is_legacy_policy_value({"text": False})
    assert not is_legacy_policy_value({"text": "legacy context", "authority": True})
    record = policy_value("repository.guidance")
    with pytest.raises(ValueError, match="unsupported"):
        validate_policy_record("future.policy", record)
    with pytest.raises(ValueError, match="unsupported"):
        validate_policy_applicability("future.policy", record, PATHS)


def test_applicability_validates_the_snapshot_not_just_the_stored_state() -> None:
    for kind in ("repository.guidance", "repository.accepted_decision"):
        value = policy_value(kind)
        validate_policy_applicability(kind, value, PATHS)
        with pytest.raises(ValueError, match="snapshots"):
            validate_policy_applicability(kind, value, ("other.py",))
    value = policy_value("repository.accepted_decision")
    value["fact"].update(applicability="invalid", matched_paths=[])
    validate_policy_applicability("repository.accepted_decision", value, PATHS)
    value["fact"]["matched_paths"] = [PATHS[0]]
    with pytest.raises(ValueError, match="invalid accepted decision"):
        validate_policy_applicability("repository.accepted_decision", value, PATHS)
