"""Native debug projections retain text while closing unexpected record shapes."""

from copy import deepcopy
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.review_trace import NativeTraceError, project_record
from tests.fuzz.strategies import json_values
from tests.test_review_trace import records


@given(st.integers(0, 6), st.data(), json_values())
def test_native_record_mutation_uses_only_closed_projection_outcomes(
    index: int, data: st.DataObject, value: object
) -> None:
    record = records(Path("/synthetic/repository"))[index]
    field = data.draw(st.sampled_from(tuple(record)))
    record[field] = value
    try:
        result = project_record(record)
    except NativeTraceError:
        return
    assert result is None or isinstance(result, dict)
    if result is not None:
        assert not {"config", "native_payload", "reasoning_content"} & result.keys()


@given(st.text(max_size=1024), st.booleans())
def test_diagnostic_text_is_not_silently_sanitized_or_reinterpreted(
    text: str, flattened: bool
) -> None:
    record = deepcopy(records(Path("/synthetic/repository"))[2 if flattened else 1])
    if flattened:
        record["content"] = text
        record["tool_calls"][0]["arguments"] = text
    else:
        record["messages"][0]["content"] = text
        record["messages"][1]["tool_calls"][0]["function"]["arguments"] = text
    result = project_record(record)
    assert result is not None
    if flattened:
        assert result["content"] == text
        assert result["tool_calls"][0]["function"]["arguments"] == text
    else:
        assert result["messages"][0]["content"] == text
        assert result["messages"][1]["tool_calls"][0]["function"]["arguments"] == text
    assert "native_payload" not in result and "reasoning_content" not in result
