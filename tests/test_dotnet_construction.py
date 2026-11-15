"""Parser output must remain bounded before any evidence-store admission."""

import json

import pytest

from ocr_toolkit.evidence.ecosystems.dotnet import (
    parse_global_json,
    parse_msbuild,
    parse_packages_lock,
)
from ocr_toolkit.evidence.ecosystems.dotnet.limits import ConstructionBudget


@pytest.mark.parametrize("namespace", ["u" * 4000, "\u754c" * 1000])
@pytest.mark.parametrize("attributes", [True, False])
def test_expanded_namespace_storage_is_bounded_during_tree_construction(namespace, attributes):
    """Refuse namespace-key and element-name fanout before retaining the expanded tree."""
    if attributes:
        items = "".join(
            "<ItemGroup " + " ".join(f'p:a{row:04x}{column:02x}="x"' for column in range(16)) + "/>"
            for row in range(1000)
        )
    else:
        items = "<p:ItemGroup/>" * 1000
    body = '<Project xmlns:p="' + namespace + '">' + items + "</Project>"
    assert len(body.encode()) <= 256_000
    with pytest.raises(ValueError, match="expanded tree limit"):
        parse_msbuild(body)


@pytest.mark.parametrize("attribute", ["Include", "Condition"])
@pytest.mark.parametrize("scalar", ["x", "\u754c"])
def test_nested_xml_cannot_amplify_retained_fact_payload(attribute, scalar):
    """Bound both ancestor identities and repeated inherited conditions before retention."""
    opening = f'<ItemGroup {attribute}="' + scalar * 4096 + '">'
    body = (
        "<Project>"
        + opening * 30
        + "<Nullable>enable</Nullable>" * 500
        + "</ItemGroup>" * 30
        + "</Project>"
    )
    parsed = parse_msbuild(body)
    assert all(len(fact.identity) < 256 for fact in parsed.facts)
    encoded = json.dumps(
        [{"identity": fact.identity, "value": fact.value} for fact in parsed.facts],
        ensure_ascii=False,
    ).encode()
    assert len(encoded) < 2 * ConstructionBudget.for_text(body).limit
    assert parsed.runtime_dependent
    if attribute == "Condition":
        assert any("payload was truncated" in notice for notice in parsed.notices)


@pytest.mark.parametrize("scalar", ["x", "\u754c"])
def test_lock_framework_fanout_is_bounded_by_constructed_bytes(scalar):
    """Apply the same output boundary to repeated JSON framework identities and values."""
    body = json.dumps(
        {
            "version": 1,
            "dependencies": {
                scalar * 4096: {f"P{n}": {"type": "Direct", "resolved": "1"} for n in range(500)}
            },
        },
        ensure_ascii=False,
    )
    parsed = parse_packages_lock(body)
    assert len(parsed.facts) < 500
    assert parsed.runtime_dependent and any(
        "payload was truncated" in notice for notice in parsed.notices
    )
    encoded = json.dumps(
        [{"identity": fact.identity, "value": fact.value} for fact in parsed.facts],
        ensure_ascii=False,
    ).encode()
    assert len(encoded) < 2 * ConstructionBudget.for_text(body).limit


def test_fact_budget_uses_utf8_and_stops_accounting_after_exhaustion():
    """Distinguish character and byte bounds and refuse further retained output."""
    budget = ConstructionBudget(13)
    assert budget.admit("k", "i", "")
    assert not budget.admit("k", "i", "\u754c")
    used = budget.used
    assert budget.exhausted and not budget.admit("", "", "")
    assert budget.used == used <= budget.limit
    assert not ConstructionBudget(14).admit("k", "i", "\u754c")
    assert ConstructionBudget(14).admit("k", "i", "x")
    assert ConstructionBudget.for_text("x" * 200_000).limit == 1_000_000


def test_sdk_payload_omission_is_explicit(monkeypatch):
    """Preserve unknown state when the shared output budget cannot retain an SDK fact."""
    monkeypatch.setattr(ConstructionBudget, "for_text", classmethod(lambda cls, text: cls(1)))
    parsed = parse_global_json('{"sdk":{"version":"9.0.100"}}')
    assert not parsed.facts and parsed.runtime_dependent and parsed.notices


def test_character_data_cannot_overrun_the_remaining_tree_budget(monkeypatch):
    """Count character data independently when the opening element already fits."""
    monkeypatch.setattr(ConstructionBudget, "for_text", classmethod(lambda cls, text: cls(35)))
    with pytest.raises(ValueError, match="expanded tree limit"):
        parse_msbuild("<Project>data</Project>")
