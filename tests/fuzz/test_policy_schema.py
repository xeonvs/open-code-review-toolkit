"""Vary structured policy types and producer-consumer applicability handoffs."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.policy import guidance_document
from ocr_toolkit.evidence.policy.schema import validate_policy_applicability, validate_policy_record
from tests.fuzz.strategies import json_values
from tests.test_policy_schema import PATHS, policy_value

KINDS = st.sampled_from(("repository.accepted_decision", "repository.guidance"))
JSON_VALUE = json_values()


@given(KINDS, JSON_VALUE)
def test_applicability_uses_closed_errors_for_every_json_type(kind: str, state: object) -> None:
    value = policy_value(kind)
    value["fact"]["applicability"] = state
    try:
        validate_policy_record(kind, value)
        validate_policy_applicability(kind, value, PATHS)
    except ValueError:
        return
    assert state == "applicable"


@given(KINDS, st.integers(0, 20), JSON_VALUE)
def test_nested_policy_field_variations_never_escape_as_parser_crashes(
    kind: str, field_index: int, replacement: object
) -> None:
    value = policy_value(kind)
    keys = tuple(value["fact"])
    value["fact"][keys[field_index % len(keys)]] = replacement
    try:
        validate_policy_record(kind, value)
        validate_policy_applicability(kind, value, PATHS)
    except ValueError:
        return


@given(
    st.lists(st.sampled_from(("api", "pkg", "café", "модуль")), min_size=0, max_size=4),
    st.sampled_from(("AGENTS.md", "CLAUDE.md")),
    st.text(max_size=120),
)
def test_guidance_producer_and_snapshot_consumer_agree_across_scopes(
    parts: list[str], name: str, text: str
) -> None:
    prefix = "/".join(parts)
    path = f"{prefix}/{name}" if prefix else name
    changed = ((f"{prefix}/app.py" if prefix else "app.py"), "outside/other.py")
    value = guidance_document(path, text, changed).evidence_value()
    validate_policy_record("repository.guidance", value)
    validate_policy_applicability("repository.guidance", value, changed)
