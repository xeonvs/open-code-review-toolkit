"""Closed source diagnoses, historical readback and real audit worker handoffs."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.dlp_audit import scanner
from ocr_toolkit.dlp_audit.proof import PROOF_SCHEMA, SnapshotProofSource, snapshot_units
from ocr_toolkit.dlp_audit.state import AuditError
from tests.fuzz.strategies import json_values
from tests.test_dlp_audit import captured, request, run_in_process
from tests.test_dlp_audit import state as state


@given(st.text(alphabet="ab \t\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029", max_size=300))
def test_source_addresses_do_not_renumber_historical_diagnostic_units(source):
    units = snapshot_units(source)
    assert [(number, value) for number, value, _, _ in units] == [
        (0, source),
        *((number, value) for number, value in enumerate(source.splitlines(), 1) if value.strip()),
    ]
    offset = 0
    for _, value, start, end in units[1:]:
        offset = source.index(value, offset)
        assert start == end == source.count("\n", 0, offset) + 1
        offset += len(value)
    assert units[0][3] == source.count("\n") + int(bool(source) and not source.endswith("\n"))


@pytest.mark.parametrize(
    "separator", ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
)
def test_actual_worker_preserves_unit_identity_but_uses_lf_source_addresses(state, separator):
    identity = captured(state, f"intro{separator}continued\nList<Entry> value;\n")
    result = scanner.supervised(request(state, identity), 15)
    # Historical splitlines units remain stable; this is unit 3 but Git line 2.
    hits = [hit for hit in result["hits"] if hit["unit"] == 3]
    assert hits and all(hit["role"] == "text" for hit in hits)
    assert all(hit["proof"] and hit["source_proof"] == "verified" for hit in hits)


def test_actual_worker_qualifies_large_snapshot_excerpts_without_parsing_fragments(state):
    identity = captured(state, ("// " + "plain " * 200 + "\n") * 240 + "List<Entry> value;\n")
    result = scanner.supervised(request(state, identity), 15)
    assert result["proof_schema"] == PROOF_SCHEMA
    line_hits = [hit for hit in result["hits"] if hit["unit"] == 241]
    assert line_hits and all(hit["role"] == "text" for hit in line_hits)
    assert all(hit["proof"] and hit["source_proof"] == "verified" for hit in line_hits)
    assert all(hit["syntax_proof"] == "source-limit" for hit in line_hits)


def test_in_memory_snapshot_proof_closes_invalid_sources_and_wrong_paths():
    source = SnapshotProofSource("safe\nlate\0", "source")
    assert source.read("source", 1, 1).reason == "invalid-source"
    assert source.read("other", 1, 1).reason == "missing-source"


def test_historical_diagnoses_remain_unavailable_without_reinterpreting_identity(
    state, monkeypatch
):
    corpus = captured(state, 'api_key="synthetic-value"\n')
    _, run = run_in_process(state, corpus, monkeypatch)
    legacy = deepcopy(run)
    legacy.pop("proof_schema")
    for hit in legacy["hits"]:
        hit.pop("source_proof")
        hit.pop("syntax_proof")
    identity = "a" * 32
    state.save("run", identity, legacy)
    loaded = scanner.load_run(state, identity)
    assert loaded == legacy
    assert [hit["id"] for hit in loaded["hits"]] == [hit["id"] for hit in run["hits"]]


@pytest.mark.parametrize(
    "case",
    [
        "schema",
        "missing-schema",
        "missing-source",
        "unknown-source",
        "contradiction",
        "syntax-without-proof",
    ],
)
def test_persisted_diagnostic_corruption_rejects_the_complete_run(state, monkeypatch, case):
    corpus = captured(state, 'api_key="synthetic-value"\n')
    _, run = run_in_process(state, corpus, monkeypatch)
    broken = deepcopy(run)
    hit = broken["hits"][0]
    if case == "schema":
        broken["proof_schema"] = "unknown"
    elif case == "missing-schema":
        broken.pop("proof_schema")
    elif case == "missing-source":
        hit.pop("source_proof")
    elif case == "unknown-source":
        hit["source_proof"] = "unexpected"
    elif case == "contradiction":
        hit["proof"] = not hit["proof"]
    else:
        hit.update(proof=False, source_proof="unavailable", syntax_proof="qualified")
    identity = "b" * 32
    state.save("run", identity, broken)
    with pytest.raises(AuditError):
        scanner.load_run(state, identity)


@given(
    st.sampled_from(("slot", "role", "reason", "source_proof", "syntax_proof", "proof", "unit")),
    json_values(),
)
def test_nested_or_malformed_diagnoses_use_only_the_closed_contract_error(field, value):
    hit = {
        "id": "a" * 64,
        "slot": "b" * 32,
        "unit": 1,
        "role": "text",
        "reason": "secret",
        "detector": "normalized",
        "proof": True,
        "source_proof": "verified",
        "syntax_proof": "not-qualified",
    }
    hit[field] = value
    try:
        result = scanner.validate_hits(
            [hit], files=[{"slot": "b" * 32, "lines": 1}], units=2, diagnostics=True
        )
    except AuditError:
        return
    assert result == [hit] and type(hit["proof"]) is bool
