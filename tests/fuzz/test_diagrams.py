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
