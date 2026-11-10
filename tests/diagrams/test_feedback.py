"""Optional validation feedback is actionable without reflecting rejected text."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ocr_toolkit.diagrams.collector import MAX_COLLECTOR_BYTES, DiagramCollector
from ocr_toolkit.diagrams.contracts import DiagramError, bounded_json, parse_submission
from ocr_toolkit.diagrams.diagnostics import parse_diagnostic
from ocr_toolkit.diagrams.mcp import call_diagram_tool, diagram_status
from tests.diagrams.support import REVIEW_RANGE, flow_submission


@pytest.fixture
def collector(tmp_path: Path):
    tmp_path.chmod(0o700)
    value = DiagramCollector(tmp_path / "diagram.json", "c" * 32, REVIEW_RANGE)
    value.initialize()
    return value


def reply(collector, value):
    result = call_diagram_tool(collector, value)
    assert result.get("isError") is not True
    return json.loads(result["content"][0]["text"])


def test_bad_shape_has_closed_feedback_and_corrected_payload_is_received(collector):
    invalid = reply(collector, {"state": "SYNTHETIC_REJECTED_SECRET"})
    assert invalid == {
        "state": "invalid",
        "retryable": True,
        "submissions_left": 7,
        "error": {
            "code": "state",
            "path": "/state",
            "message": "diagram submission state is invalid",
            "allowed": ["generated", "not-applicable"],
        },
    }
    assert "SYNTHETIC_REJECTED_SECRET" not in json.dumps(invalid)
    assert diagram_status(collector) == {"state": "retryable-invalid"}
    assert reply(collector, flow_submission()) == {"state": "received"}
    assert diagram_status(collector) == {"state": "received"}


@pytest.mark.parametrize("field", ["kind", "label", "references", "id"])
def test_nested_error_locates_only_known_fields(field):
    value = flow_submission()
    value["diagram"]["nodes"][0][field] = (
        "SYNTHETIC_REJECTED_SECRET" if field != "label" else "\nSYNTHETIC_REJECTED_SECRET"
    )
    if field == "id":
        value["diagram"]["nodes"][0][field] = "!SYNTHETIC_REJECTED_SECRET"
    with pytest.raises(DiagramError) as caught:
        parse_submission(value, expected_range=REVIEW_RANGE)
    diagnostic = caught.value.diagnostic()
    assert diagnostic["path"].startswith("/diagram/nodes/0")
    assert "SYNTHETIC_REJECTED_SECRET" not in json.dumps(diagnostic)


def test_unknown_property_is_not_reflected(collector):
    value = flow_submission()
    value["diagram"]["nodes"][0]["SYNTHETIC_REJECTED_SECRET"] = "private"
    response = reply(collector, value)
    assert response["error"]["code"] == "shape"
    assert response["error"]["path"] == "/diagram/nodes/0"
    assert response["error"]["allowed"] == ["id", "kind", "label", "references"]
    assert "SYNTHETIC_REJECTED_SECRET" not in json.dumps(response)


def test_error_constructor_cannot_reflect_an_arbitrary_exception():
    assert DiagramError("SYNTHETIC_REJECTED_SECRET").diagnostic()["code"] == "invalid"
    assert "SYNTHETIC_REJECTED_SECRET" not in json.dumps(
        DiagramError("SYNTHETIC_REJECTED_SECRET").diagnostic()
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("code", "unknown"),
        ("path", "/SYNTHETIC_REJECTED_SECRET"),
        ("message", "SYNTHETIC_REJECTED_SECRET"),
        ("allowed", ["SYNTHETIC_REJECTED_SECRET"]),
        ("allowed", [[], []]),
        ("path", "/nodes/" + "1" * 260),
    ],
)
def test_persisted_diagnostics_are_hostile(field, value):
    diagnostic = DiagramError("diagram submission state is invalid", path="/state").diagnostic()
    diagnostic[field] = value
    with pytest.raises(DiagramError):
        parse_diagnostic(diagnostic)


@pytest.mark.parametrize("value", (None, [], {}, {"code": "invalid", "unexpected": "private"}))
def test_incomplete_or_extra_diagnostic_shape_cannot_reach_feedback(value):
    with pytest.raises(DiagramError):
        parse_diagnostic(value)


def test_near_maximum_candidate_survives_a_later_validation_error(collector):
    value = flow_submission()
    diagram = value["diagram"]
    template = deepcopy(diagram["nodes"][0])
    diagram["nodes"] = [dict(template, id=f"node{i}", label="x" * 80) for i in range(12)]
    diagram["edges"] = []
    # Approach the independent candidate byte limit with valid relative paths.
    for length in range(1, 500):
        for i, node in enumerate(diagram["nodes"]):
            node["references"] = [
                {"path": "src/" + "x" * length + f"/{i}{suffix}", "start_line": 1, "end_line": 1}
                for suffix in ("a", "b")
            ]
        try:
            bounded_json(value)
        except DiagramError:
            for node in diagram["nodes"]:
                for reference in node["references"]:
                    reference["path"] = reference["path"].replace("x" * length, "x" * (length - 1))
            break
    # Paths hit their own limit first; add distinct referenced edges to reach a
    # candidate close to the JSON cap without changing either production limit.
    for i in range(16):
        edge = {
            "source": f"node{i % 12}",
            "target": f"node{(i + 1 + i // 12) % 12}",
            "condition": "guard",
            "references": deepcopy(diagram["nodes"][0]["references"]),
        }
        diagram["edges"].append(edge)
        try:
            bounded_json(value)
        except DiagramError:
            diagram["edges"].pop()
            break
    assert len(bounded_json(value)) > 12_000
    first = collector.submit(value)
    assert first.candidate is not None
    after = collector.submit({"state": "proposed"})
    assert after.candidate == first.candidate and after.last_error is not None
    assert collector.path.stat().st_size <= MAX_COLLECTOR_BYTES <= 20_000
    assert collector.read() == after
