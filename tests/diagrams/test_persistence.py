"""Persisted diagrams preserve conditions exactly or fail as an atomic envelope."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit.diagrams.contracts import parse_submission
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.ocr_result import OcrResultMalformed, load_ocr_result
from tests.diagrams.support import flow_submission
from tests.test_review_range import native_result
from tests.test_review_receipt_v13 import CURRENT_RANGE, _receipt_v13, generated_diagram


def persisted_result(diagram):
    result = native_result(CURRENT_RANGE)
    result["tool_calls"] = {
        "total": 2,
        "by_tool": {"ocr_toolkit_evidence": 1, DIAGRAM_TOOL_NAME: 1},
    }
    result["_ocr_toolkit"] = _receipt_v13(diagram=diagram)
    return result


@pytest.mark.parametrize(
    "condition",
    (
        '"login_password": ""',
        "'login_password': '{{ service_password }}'",
        "date < 2020-01-01",
        "version >= 2026.10.19",
    ),
)
def test_current_loader_never_redacts_a_valid_condition_into_another_route(
    tmp_path: Path, condition: str
) -> None:
    payload = flow_submission()
    payload.update(base_sha=CURRENT_RANGE.base, head_sha=CURRENT_RANGE.head)
    payload["diagram"]["edges"][0]["condition"] = condition
    diagram = replace(
        generated_diagram(), submission=parse_submission(payload, expected_range=CURRENT_RANGE)
    )
    result = persisted_result(diagram)
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    loaded = load_ocr_result(path)
    assert loaded["_ocr_toolkit"] == result["_ocr_toolkit"]
    assert (
        loaded["_ocr_toolkit"]["diagram"]["submission"]["diagram"]["edges"][0]["condition"]
        == condition
    )


def test_unknown_persisted_graph_field_rejects_the_entire_artifact(tmp_path: Path) -> None:
    result = persisted_result(generated_diagram())
    result["comments"] = [{"path": "app.py", "line": 1, "content": "A separate finding."}]
    result["_ocr_toolkit"]["diagram"]["submission"]["diagram"]["mermaid"] = "untrusted raw syntax"
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    with pytest.raises(OcrResultMalformed, match="receipt is invalid"):
        load_ocr_result(path)


def test_duplicate_json_fields_cannot_change_a_candidate_during_load(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text('{"status":"success","status":"skipped"}')
    with pytest.raises(OcrResultMalformed, match="repeats a JSON field"):
        load_ocr_result(path)
