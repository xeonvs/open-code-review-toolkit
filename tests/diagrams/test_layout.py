"""Orientation follows topology and displayed labels without changing content."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.contracts import Flowchart, FlowEdge, FlowNode, parse_submission
from ocr_toolkit.reporting.diagram import diagram_mermaid
from ocr_toolkit.reporting.diagram_layout import flowchart_direction
from tests.diagrams.support import REVIEW_RANGE, sequence_submission


def graph(count, label="Read source", *, cycle=False, branches=False):
    nodes = tuple(FlowNode(f"node{i}", "step", label, ()) for i in range(count))
    edges = tuple(
        FlowEdge("node0" if branches else f"node{i - 1}", f"node{i}", "", ())
        for i in range(1, count)
    )
    if cycle and count > 1:
        edges += (FlowEdge(f"node{count - 1}", "node0", "retry", ()),)
    return Flowchart(nodes, edges)


@pytest.mark.parametrize(
    "diagram,expected",
    (
        (graph(0), "LR"),
        (graph(1), "LR"),
        (graph(3), "LR"),
        (graph(8), "TB"),
        (graph(8, cycle=True), "TB"),
        (graph(10, branches=True), "LR"),
        (graph(2, "Long source description " * 3), "TB"),
        (Flowchart(graph(8).nodes, ()), "LR"),
        (graph(4, "界" * 15), "TB"),
    ),
)
def test_bounded_orientation_examples(diagram, expected):
    assert flowchart_direction(diagram) == expected
    assert diagram_mermaid(diagram).splitlines()[0] == f"flowchart {expected}"


def test_edge_conditions_and_decision_boxes_contribute_to_width():
    diagram = graph(2, "x" * 8)
    assert flowchart_direction(diagram) == "LR"
    diagram = replace(diagram, edges=(replace(diagram.edges[0], condition="x" * 80),))
    assert flowchart_direction(diagram) == "TB"
    decision = replace(
        graph(3, "x" * 20),
        nodes=tuple(replace(node, kind="decision") for node in graph(3, "x" * 20).nodes),
    )
    assert flowchart_direction(decision) == "TB"


@given(st.integers(1, 12), st.integers(1, 60), st.booleans(), st.booleans())
def test_layout_is_independent_of_serialization_order_and_preserves_all_elements(
    n, width, cycle, branches
):
    diagram = graph(n, "x" * width, cycle=cycle, branches=branches)
    reordered = replace(diagram, nodes=diagram.nodes[::-1], edges=diagram.edges[::-1])
    assert flowchart_direction(diagram) == flowchart_direction(reordered)
    before, after = diagram_mermaid(diagram), diagram_mermaid(reordered)
    assert before.count(" -->") == after.count(" -->") == len(diagram.edges)
    assert before.count('["') == after.count('["') == len(diagram.nodes)


def test_sequence_keeps_its_standard_orientation_and_encoding():
    diagram = parse_submission(sequence_submission(), expected_range=REVIEW_RANGE).diagram
    assert diagram_mermaid(diagram).startswith("sequenceDiagram\n")
    assert "flowchart" not in diagram_mermaid(diagram)


def test_combining_marks_do_not_inflate_the_layout_estimate():
    assert flowchart_direction(graph(3, "e\u0301" * 20)) == flowchart_direction(graph(3, "e" * 20))
