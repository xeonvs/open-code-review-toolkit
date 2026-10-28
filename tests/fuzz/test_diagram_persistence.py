"""Vary conditions and hostile nested fields across the exact persistence boundary."""

import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.contracts import DiagramError, parse_submission
from ocr_toolkit.diagrams.persistence import diagram_payload, parse_diagram_payload
from ocr_toolkit.ocr_result import load_ocr_result
from tests.diagrams.support import flow_submission
from tests.diagrams.test_persistence import persisted_result
from tests.fuzz.strategies import json_values
from tests.fuzz.test_dlp import technical_text
from tests.test_review_receipt_v13 import CURRENT_RANGE, generated_diagram


@given(technical_text(), st.booleans(), st.sampled_from((None, 0, 2)))
def test_conditions_round_trip_without_redaction_or_semantic_mutation(
    condition: str, ensure_ascii: bool, indent: int | None
) -> None:
    payload = flow_submission()
    payload.update(base_sha=CURRENT_RANGE.base, head_sha=CURRENT_RANGE.head)
    payload["diagram"]["edges"][0]["condition"] = condition
    diagram = replace(
        generated_diagram(), submission=parse_submission(payload, expected_range=CURRENT_RANGE)
    )
    native = persisted_result(diagram)
    with TemporaryDirectory(prefix="ocr-diagram-persistence-") as directory:
        path = Path(directory) / "result.json"
        path.write_text(
            json.dumps(native, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8"
        )
        loaded = load_ocr_result(path)
        assert loaded["_ocr_toolkit"] == native["_ocr_toolkit"]


@given(
    st.sampled_from(("schema", "mode", "state", "reason", "calls", "failed_calls", "submission")),
    json_values(),
)
def test_persisted_field_variations_have_a_closed_failure_boundary(
    field: str, value: object
) -> None:
    payload = diagram_payload(generated_diagram())
    payload[field] = value
    try:
        parsed = parse_diagram_payload(payload, review_range=CURRENT_RANGE)
    except DiagramError:
        return
    assert diagram_payload(parsed) == payload


@given(json_values())
def test_nonobject_persisted_envelopes_never_raise_incidental_type_errors(value: object) -> None:
    if not isinstance(value, dict):
        with pytest.raises(DiagramError):
            parse_diagram_payload(value, review_range=CURRENT_RANGE)
