"""Bounded typed diagrams and global alternative budgets under generated input."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.contracts import DiagramError, parse_submission, submission_payload
from tests.diagrams.support import (
    REVIEW_RANGE,
    alternative,
    flow_submission,
    message,
    references,
    sequence_submission,
)
from tests.fuzz.strategies import json_values

LABEL = st.text(alphabet="abcxyz01239 .<>=[]{}|&;:#'\"😀é", min_size=1, max_size=80).filter(
    lambda text: bool(text.strip())
)


@given(st.integers(1, 12), st.integers(0, 16), LABEL)
def test_flow_round_trip_preserves_all_labels_and_endpoints(
    node_count: int, edge_count: int, label: str
) -> None:
    payload = flow_submission()
    graph = payload["diagram"]
    graph["nodes"] = [
        {"id": f"n{index}", "kind": "step", "label": label, "references": references()}
        for index in range(node_count)
    ]
    graph["edges"] = [
        {
            "source": "n0",
            "target": f"n{index % node_count}",
            "condition": str(index),
            "references": references(),
        }
        for index in range(edge_count)
    ]
    parsed = parse_submission(payload, expected_range=REVIEW_RANGE)
    assert parse_submission(submission_payload(parsed), expected_range=REVIEW_RANGE) == parsed
    for field in ("source", "target"):
        hostile = deepcopy(payload)
        if not hostile["diagram"]["edges"]:
            continue
        hostile["diagram"]["edges"][0][field] = "missing"
        with pytest.raises(DiagramError, match="endpoint"):
            parse_submission(hostile, expected_range=REVIEW_RANGE)


@given(st.integers(0, 20), st.integers(0, 20), LABEL)
def test_sequence_budget_is_global_across_mutually_exclusive_branches(
    first: int, second: int, label: str
) -> None:
    payload = sequence_submission()
    payload["diagram"]["steps"] = [
        alternative(
            [message(label) for _ in range(first)],
            [message(label, "return") for _ in range(second)],
        )
    ]
    if 1 <= first + second <= 16:
        parsed = parse_submission(payload, expected_range=REVIEW_RANGE)
        assert parse_submission(submission_payload(parsed), expected_range=REVIEW_RANGE) == parsed
    else:
        with pytest.raises(DiagramError):
            parse_submission(payload, expected_range=REVIEW_RANGE)


@given(json_values())
def test_arbitrary_nested_json_uses_only_the_closed_submission_error(value: object) -> None:
    try:
        parsed = parse_submission(value, expected_range=REVIEW_RANGE)
    except DiagramError:
        return
    assert parse_submission(submission_payload(parsed), expected_range=REVIEW_RANGE) == parsed


FLOW_FIELDS = (
    ("state",),
    ("diagram", "kind"),
    ("diagram", "nodes"),
    *(("diagram", "nodes", 0, field) for field in ("id", "kind", "label", "references")),
    *(
        ("diagram", "nodes", 0, "references", 0, field)
        for field in ("path", "start_line", "end_line")
    ),
    *(("diagram", "edges", 0, field) for field in ("source", "target", "condition", "references")),
)
SEQUENCE_FIELDS = (
    ("diagram", "participants"),
    ("diagram", "steps"),
    *(("diagram", "participants", 0, field) for field in ("id", "label", "references")),
    *(
        ("diagram", "steps", 0, field)
        for field in ("kind", "message_type", "source", "target", "label", "references")
    ),
    ("diagram", "steps", 1, "branches"),
    ("diagram", "steps", 1, "branches", 0, "condition"),
    ("diagram", "steps", 1, "branches", 0, "steps"),
)


@given(st.booleans(), st.data(), json_values())
def test_nested_field_mutations_reach_both_variant_parsers(
    sequence: bool, data: st.DataObject, value: object
) -> None:
    payload = sequence_submission() if sequence else flow_submission()
    path = data.draw(st.sampled_from(SEQUENCE_FIELDS if sequence else FLOW_FIELDS))
    parent = payload
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    try:
        parsed = parse_submission(payload, expected_range=REVIEW_RANGE)
    except DiagramError:
        return
    assert parse_submission(submission_payload(parsed), expected_range=REVIEW_RANGE) == parsed


@st.composite
def sequence_trees(draw: st.DrawFn) -> dict:
    payload = sequence_submission()
    participants = draw(st.integers(1, 8))
    payload["diagram"]["participants"] = [
        {"id": f"p{index}", "label": f"Component {index}", "references": references()}
        for index in range(participants)
    ]

    def messages() -> list[dict]:
        return [
            {
                **message(
                    draw(st.sampled_from(("Load", "Return", "Café", "end: [] | # ;"))),
                    draw(st.sampled_from(("call", "return"))),
                ),
                "source": f"p{draw(st.integers(0, participants - 1))}",
                "target": f"p{draw(st.integers(0, participants - 1))}",
            }
            for _ in range(draw(st.integers(0, 5)))
        ]

    shape = draw(st.sampled_from(("flat", "single", "nested", "both", "deep", "many")))
    left, right = messages(), messages()
    if shape == "flat":
        steps = left + right
    elif shape == "single":
        steps = [alternative(left, right)]
    elif shape == "nested":
        steps = [alternative([alternative(left, right)], messages())]
    elif shape == "both":
        steps = [alternative([alternative(left, right)], [alternative(messages(), messages())])]
    elif shape == "deep":
        steps = [alternative([alternative([alternative(left, right)])])]
    else:
        steps = [alternative(messages(), messages()) for _ in range(draw(st.integers(4, 6)))]
    payload["diagram"]["steps"] = steps
    return payload


@given(sequence_trees())
def test_interacting_tree_limits_preserve_order_or_reject_the_whole_candidate(
    payload: dict,
) -> None:
    # Count the wire tree independently, including both sides of each alternative.
    messages, alternatives, depth = 0, 0, 0
    pending = [(payload["diagram"]["steps"], 0)]
    while pending:
        items, nesting = pending.pop()
        for item in items:
            if item["kind"] == "message":
                messages += 1
            else:
                alternatives += 1
                depth = max(depth, nesting + 1)
                pending.extend((branch["steps"], nesting + 1) for branch in item["branches"])
    if 1 <= messages <= 16 and alternatives <= 4 and depth <= 2:
        parsed = parse_submission(payload, expected_range=REVIEW_RANGE)
        assert submission_payload(parsed)["diagram"]["steps"] == payload["diagram"]["steps"]
    else:
        with pytest.raises(DiagramError):
            parse_submission(payload, expected_range=REVIEW_RANGE)
