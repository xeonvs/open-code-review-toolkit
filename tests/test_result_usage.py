"""Contract tests for closed provider-neutral token telemetry."""

from __future__ import annotations

import pytest

from ocr_toolkit.result_usage import normalize_token_usage, token_usage_mapping


def test_normalizes_closed_buckets_and_derives_other() -> None:
    assert normalize_token_usage(
        {
            "usage": {
                "input_tokens": 120,
                "output_tokens": 30,
                "cached_tokens": 20,
                "reasoning_tokens": 10,
                "total_tokens": 170,
                "provider_charge_units": 999,
            }
        }
    ) == {
        "input": 120,
        "output": 30,
        "cached": 20,
        "reasoning": 10,
        "total": 170,
        "other": 20,
    }


def test_accepts_nested_standard_detail_buckets() -> None:
    assert normalize_token_usage(
        {
            "usage": {
                "input_tokens": 12,
                "output_tokens": 5,
                "input_tokens_details": {"cached_tokens": 4, "provider": "ignored"},
                "output_tokens_details": {"reasoning_tokens": 2},
            }
        }
    ) == {"input": 12, "output": 5, "cached": 4, "reasoning": 2, "total": 17}


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": 10, "prompt_tokens": 11, "output_tokens": 2},
        {"input_tokens": "10", "output_tokens": 2},
        {"input_tokens": 10, "cached_tokens": 11},
        {"output_tokens": 10, "reasoning_tokens": 11},
        {"input_tokens": 10, "output_tokens": 5, "total_tokens": 14},
        {"cached_tokens": 1},
        {"reasoning_tokens": 1},
    ],
)
def test_rejects_malformed_or_contradictory_supported_telemetry(
    usage: dict[str, object],
) -> None:
    assert normalize_token_usage({"usage": usage}) is None


def test_root_total_is_not_misread_as_usage_and_depth_is_bounded() -> None:
    assert normalize_token_usage({"total": 17}) is None
    value: dict[str, object] = {"total_tokens": 123}
    for _ in range(12):
        value = {"metadata": value}
    assert token_usage_mapping(value) is None
    assert token_usage_mapping(value, max_depth=25) == {"total_tokens": 123}


def test_preserves_a_single_primary_bucket_without_inventing_total() -> None:
    assert normalize_token_usage({"usage": {"input_tokens": 12}}) == {"input": 12}
