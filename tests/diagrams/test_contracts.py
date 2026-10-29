"""Closed schemas and global diagram budgets, including nested alternatives."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ocr_toolkit.diagrams.contracts import (
    DiagramError,
    Flowchart,
    SequenceDiagram,
    bounded_json,
    diagram_requested,
    diagram_text_units,
    parse_diagram_mode,
    parse_submission,
    submission_payload,
)
from tests.diagrams.support import (
    REVIEW_RANGE,
    alternative,
    flow_submission,
    message,
    references,
    sequence_submission,
)


@pytest.mark.parametrize("raw", (None, "on", "off", "spoiler", "local", "", " ", "ON", "unknown"))
@pytest.mark.parametrize("local", (False, True))
def test_exact_configuration_matrix(raw: str | None, local: bool) -> None:
    if raw in ("", " ", "ON", "unknown") or (raw == "local" and not local):
        with pytest.raises(DiagramError, match="OCR_REVIEW_DIAGRAM_MODE"):
            parse_diagram_mode(raw, local=local)
    else:
        mode = parse_diagram_mode(raw, local=local)
        assert mode == (raw or "on")
        assert diagram_requested(mode, local=local) == (
            raw == "local" if local else raw in (None, "on", "spoiler")
        )


@pytest.mark.parametrize(
    "factory,variant", ((flow_submission, Flowchart), (sequence_submission, SequenceDiagram))
)
def test_both_variants_round_trip_without_untyped_fields(factory, variant) -> None:
    parsed = parse_submission(factory(), expected_range=REVIEW_RANGE)
    assert isinstance(parsed.diagram, variant)
    assert parse_submission(submission_payload(parsed), expected_range=REVIEW_RANGE) == parsed
    assert diagram_text_units(parsed.diagram)


def test_normalized_flow_order_is_idempotent_but_sequence_order_is_semantic() -> None:
    flow = flow_submission()
    expected = parse_submission(flow, expected_range=REVIEW_RANGE)
    flow["diagram"]["nodes"].reverse()
    flow["diagram"]["nodes"][0]["label"] = " Handle request "
    assert parse_submission(flow, expected_range=REVIEW_RANGE) == expected
    sequence = sequence_submission()
    expected_sequence = parse_submission(sequence, expected_range=REVIEW_RANGE)
    sequence["diagram"]["steps"].reverse()
    assert parse_submission(sequence, expected_range=REVIEW_RANGE) != expected_sequence


@pytest.mark.parametrize("value", (None, [], {}, {"state": "unsupported"}, {"state": []}))
def test_malformed_root_types_and_states_fail_closed(value: object) -> None:
    with pytest.raises(DiagramError):
        parse_submission(value, expected_range=REVIEW_RANGE)


@pytest.mark.parametrize("field", ("base_sha", "head_sha"))
@pytest.mark.parametrize("value", (None, "c" * 40, "HEAD"))
def test_stale_and_nonimmutable_range_cannot_reach_a_variant(field: str, value: object) -> None:
    payload = flow_submission()
    payload[field] = value
    with pytest.raises(DiagramError, match="range"):
        parse_submission(payload, expected_range=REVIEW_RANGE)


def test_not_applicable_has_no_model_reason_or_diagram_payload() -> None:
    payload = {
        "state": "not-applicable",
        "base_sha": REVIEW_RANGE.base,
        "head_sha": REVIEW_RANGE.head,
    }
    parsed = parse_submission(payload, expected_range=REVIEW_RANGE)
    assert parsed.diagram is None and submission_payload(parsed) == payload
    for key in ("reason", "diagram", "mermaid", "confidence"):
        with pytest.raises(DiagramError, match="closed shape"):
            parse_submission({**payload, key: "model claim"}, expected_range=REVIEW_RANGE)


@pytest.mark.parametrize(
    "label",
    (
        "x" * 81,
        "😀" * 81,
        "line\nbreak",
        "line\rbreak",
        "tab\there",
        "\ud800",
        "\u202e",
        "\u200b",
        "",
        "   ",
    ),
)
def test_label_boundaries_and_invisible_characters(label: str) -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["label"] = label
    with pytest.raises(DiagramError):
        parse_submission(payload, expected_range=REVIEW_RANGE)


def test_exact_character_and_utf8_boundary_is_admissible() -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["label"] = "😀" * 80
    assert parse_submission(payload, expected_range=REVIEW_RANGE).diagram is not None


@pytest.mark.parametrize(
    "path",
    (
        "",
        "/app.py",
        "../app.py",
        "a/../app.py",
        "a//app.py",
        "./app.py",
        "-app.py",
        "a\\app.py",
        "app.py ",
        "a" * 513,
        "a\x00b",
    ),
)
def test_source_path_grammar(path: str) -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["references"] = references(path)
    with pytest.raises(DiagramError):
        parse_submission(payload, expected_range=REVIEW_RANGE)


@pytest.mark.parametrize(
    "start,end", ((0, 1), (2, 1), (True, 2), (1, False), (1, 1_000_001), ("1", 2))
)
def test_source_span_units_and_types(start: object, end: object) -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["references"] = references(start=start, end=end)
    with pytest.raises(DiagramError, match="span"):
        parse_submission(payload, expected_range=REVIEW_RANGE)


@pytest.mark.parametrize("bad_refs", ([], references() * 2, references() * 3, [False]))
def test_required_reference_budget_and_duplicates(bad_refs: object) -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["references"] = bad_refs
    with pytest.raises(DiagramError):
        parse_submission(payload, expected_range=REVIEW_RANGE)


def test_flow_global_limits_duplicate_and_dangling_identities() -> None:
    original = flow_submission()
    for mutate in (
        lambda diagram: diagram["nodes"].append(deepcopy(diagram["nodes"][0])),
        lambda diagram: diagram["nodes"][0].update(id="bad;id"),
        lambda diagram: diagram["nodes"][0].update(kind="subgraph"),
        lambda diagram: diagram["edges"][0].update(target="missing"),
        lambda diagram: diagram["edges"].append(deepcopy(diagram["edges"][0])),
        lambda diagram: diagram.update(nodes=diagram["nodes"] * 7),
        lambda diagram: diagram.update(edges=diagram["edges"] * 17),
    ):
        payload = deepcopy(original)
        mutate(payload["diagram"])
        with pytest.raises(DiagramError):
            parse_submission(payload, expected_range=REVIEW_RANGE)


@pytest.mark.parametrize("count", (0, 1, 16, 17))
def test_sequence_message_budget_counts_both_branches(count: int) -> None:
    payload = sequence_submission()
    payload["diagram"]["steps"] = [
        alternative(
            [message() for _ in range(count // 2)], [message() for _ in range(count - count // 2)]
        )
    ]
    if 1 <= count <= 16:
        assert parse_submission(payload, expected_range=REVIEW_RANGE).diagram is not None
    else:
        with pytest.raises(DiagramError, match="message"):
            parse_submission(payload, expected_range=REVIEW_RANGE)


def test_sequence_global_alternative_and_depth_limits() -> None:
    payload = sequence_submission()
    payload["diagram"]["steps"] = [alternative([message()]) for _ in range(4)]
    assert parse_submission(payload, expected_range=REVIEW_RANGE).diagram is not None
    payload["diagram"]["steps"].append(alternative([message()]))
    with pytest.raises(DiagramError, match="alternative"):
        parse_submission(payload, expected_range=REVIEW_RANGE)
    payload["diagram"]["steps"] = [alternative([alternative([alternative([message()])])])]
    with pytest.raises(DiagramError, match="nesting"):
        parse_submission(payload, expected_range=REVIEW_RANGE)


def test_sequence_endpoint_types_and_closed_nested_grammar() -> None:
    original = sequence_submission()
    for mutate in (
        lambda diagram: diagram["participants"].append(deepcopy(diagram["participants"][0])),
        lambda diagram: diagram.update(participants=diagram["participants"] * 5),
        lambda diagram: diagram["steps"][0].update(source="missing"),
        lambda diagram: diagram["steps"][0].update(message_type="activate"),
        lambda diagram: diagram["steps"][0].update(kind="loop"),
        lambda diagram: diagram["steps"].append(None),
        lambda diagram: diagram["steps"][1]["branches"].pop(),
        lambda diagram: diagram["steps"][1]["branches"][0].update(style="red"),
        lambda diagram: diagram.update(steps=[message()] * 21),
    ):
        payload = deepcopy(original)
        mutate(payload["diagram"])
        with pytest.raises(DiagramError):
            parse_submission(payload, expected_range=REVIEW_RANGE)


def test_unknown_fields_never_become_raw_mermaid_or_output_authority() -> None:
    original = flow_submission()
    for target in (
        original,
        original["diagram"],
        original["diagram"]["nodes"][0],
        original["diagram"]["nodes"][0]["references"][0],
        original["diagram"]["edges"][0],
    ):
        target["output_path"] = "https://example.invalid/collector"
        with pytest.raises(DiagramError, match="closed shape"):
            parse_submission(original, expected_range=REVIEW_RANGE)
        del target["output_path"]


def test_byte_limit_unserializable_and_unknown_variants() -> None:
    assert bounded_json("x", limit=3) == b'"x"'
    for value in ("x" * 16384, {"x": object()}, float("nan")):
        with pytest.raises(DiagramError):
            bounded_json(value)
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(DiagramError):
        bounded_json(cyclic)
    for diagram in ([], {"kind": "raw-mermaid"}):
        payload = flow_submission()
        payload["diagram"] = diagram
        with pytest.raises(DiagramError):
            parse_submission(payload, expected_range=REVIEW_RANGE)
