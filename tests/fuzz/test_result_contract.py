"""Untrusted native enum types produce closed contract errors, never parser crashes."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome
from tests.fuzz.strategies import json_values
from tests.test_result_contract import manifest_result

JSON_VALUE = json_values()


@given(
    st.one_of(
        st.sampled_from(
            (
                "provider",
                "timeout",
                "cancelled",
                "configuration",
                "input",
                "budget",
                "panic",
                "unknown",
            )
        ),
        JSON_VALUE,
    )
)
def test_failed_item_classification_is_a_closed_string_enum(value: object) -> None:
    result = manifest_result("failed", selected=["a"], failed=[("a", "unknown")])
    result["manifest"]["coverage"]["failed"][0]["classification"] = value
    if isinstance(value, str) and value in {
        "provider",
        "timeout",
        "cancelled",
        "configuration",
        "input",
        "budget",
        "panic",
        "unknown",
    }:
        assert parse_result_outcome(result).kind == "failed"
    else:
        with pytest.raises(OcrResultContractError):
            parse_result_outcome(result)


@given(
    st.one_of(
        st.sampled_from(
            ("input", "configuration", "timeout", "cancelled", "budget", "internal", "unknown")
        ),
        JSON_VALUE,
    )
)
def test_run_failure_classification_is_a_closed_string_enum(value: object) -> None:
    result = manifest_result("failed", selected=[], run_failure="unknown")
    result["manifest"]["run_failure"]["classification"] = value
    if isinstance(value, str) and value in {
        "input",
        "configuration",
        "timeout",
        "cancelled",
        "budget",
        "internal",
        "unknown",
    }:
        assert parse_result_outcome(result).kind == "failed"
    else:
        with pytest.raises(OcrResultContractError):
            parse_result_outcome(result)


@given(st.one_of(st.sampled_from(("complete", "partial", "failed", "skipped")), JSON_VALUE))
def test_manifest_terminal_state_types_cannot_escape_the_contract_error(value: object) -> None:
    result = manifest_result("complete", selected=["a"], completed=["a"])
    result["manifest"]["terminal_state"] = value
    if value == "complete":
        assert parse_result_outcome(result).kind == "clean"
    else:
        with pytest.raises(OcrResultContractError):
            parse_result_outcome(result)


@pytest.mark.parametrize("value", ([], {}))
@pytest.mark.parametrize("field", ("terminal", "item-failure", "run-failure"))
def test_minimized_unhashable_enum_regressions(value: object, field: str) -> None:
    result = manifest_result(
        "failed", selected=["a"], failed=[("a", "unknown")], run_failure="unknown"
    )
    if field == "terminal":
        result["manifest"]["terminal_state"] = value
    elif field == "item-failure":
        result["manifest"]["coverage"]["failed"][0]["classification"] = value
    else:
        result["manifest"]["run_failure"]["classification"] = value
    with pytest.raises(OcrResultContractError, match="unsupported"):
        parse_result_outcome(result)
