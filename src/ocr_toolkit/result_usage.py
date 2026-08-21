"""Normalize provider token telemetry into one closed toolkit vocabulary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

TOKEN_USAGE_KEYS = (
    "usage",
    "token_usage",
    "tokenUsage",
    "token_usage_summary",
    "tokenUsageSummary",
)
TOKEN_USAGE_CONTAINER_KEYS = (
    *TOKEN_USAGE_KEYS,
    "summary",
    "project_summary",
    "metadata",
    "stats",
    "statistics",
)
TOKEN_TOTAL_KEYS = ("total_tokens", "totalTokens", "tokens", "total")
TOKEN_EXPLICIT_TOTAL_KEYS = ("total_tokens", "totalTokens", "tokens")
TOKEN_INPUT_KEYS = (
    "prompt_tokens",
    "input_tokens",
    "promptTokens",
    "inputTokens",
    "prompt",
    "input",
)
TOKEN_OUTPUT_KEYS = (
    "completion_tokens",
    "output_tokens",
    "completionTokens",
    "outputTokens",
    "completion",
    "output",
)
TOKEN_CACHED_KEYS = (
    "cached_tokens",
    "cache_read_input_tokens",
    "cachedInputTokens",
    "cacheReadInputTokens",
)
TOKEN_REASONING_KEYS = (
    "reasoning_tokens",
    "reasoningTokens",
)
TOKEN_INPUT_DETAILS_KEYS = ("input_tokens_details", "inputTokensDetails")
TOKEN_OUTPUT_DETAILS_KEYS = ("output_tokens_details", "outputTokensDetails")


def _strict_nonnegative_int(value: Any) -> int | None:
    """Return one JSON integer counter without coercing provider values."""

    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _one_counter(mapping: Mapping[str, Any], keys: Sequence[str]) -> tuple[int | None, bool]:
    """Return one unambiguous counter and whether a supported key was present."""

    present = [mapping[key] for key in keys if key in mapping]
    if not present:
        return None, False
    counters = [_strict_nonnegative_int(value) for value in present]
    if any(counter is None for counter in counters) or len(set(counters)) != 1:
        return None, True
    return counters[0], True


def _detail_counter(
    mapping: Mapping[str, Any], container_keys: Sequence[str], counter_keys: Sequence[str]
) -> tuple[int | None, bool]:
    """Read one supported nested detail counter without accepting mixed shapes."""

    values: list[Any] = []
    present = False
    for key in container_keys:
        if key not in mapping:
            continue
        present = True
        details = mapping[key]
        if not isinstance(details, Mapping):
            return None, True
        for counter_key in counter_keys:
            if counter_key in details:
                values.append(details[counter_key])
    if not present or not values:
        return None, False
    counters = [_strict_nonnegative_int(value) for value in values]
    if any(counter is None for counter in counters) or len(set(counters)) != 1:
        return None, True
    return counters[0], True


def _find_token_usage_mapping(
    value: Any, max_depth: int = 8, *, explicit_container: bool = False
) -> tuple[Mapping[str, Any], bool] | None:
    """Find the first mapping that contains a supported token counter."""

    if max_depth <= 0 or not isinstance(value, Mapping):
        return None
    direct_keys = (
        (TOKEN_TOTAL_KEYS if explicit_container else TOKEN_EXPLICIT_TOTAL_KEYS)
        + TOKEN_INPUT_KEYS
        + TOKEN_OUTPUT_KEYS
        + TOKEN_CACHED_KEYS
        + TOKEN_REASONING_KEYS
        + TOKEN_INPUT_DETAILS_KEYS
        + TOKEN_OUTPUT_DETAILS_KEYS
    )
    if any(key in value for key in direct_keys):
        return value, explicit_container
    for key in TOKEN_USAGE_CONTAINER_KEYS:
        nested = value.get(key)
        if isinstance(nested, Mapping):
            found = _find_token_usage_mapping(
                nested,
                max_depth=max_depth - 1,
                explicit_container=key in TOKEN_USAGE_KEYS,
            )
            if found is not None:
                return found
    return None


def token_usage_mapping(
    value: Any, max_depth: int = 8, *, explicit_container: bool = False
) -> Mapping[str, Any] | None:
    """Return the first supported token-usage mapping for compatibility callers."""

    found = _find_token_usage_mapping(
        value, max_depth=max_depth, explicit_container=explicit_container
    )
    return found[0] if found is not None else None


def normalize_token_usage(value: Any) -> dict[str, int] | None:
    """Return validated input/output/subset counters or no attributable telemetry.

    Unknown provider keys are ignored. Supported aliases must agree exactly;
    cached and reasoning counters are accepted only with their respective
    parent bucket, and an explicit total may not be smaller than known input
    plus output. ``other`` is emitted only when all arithmetic operands are
    known.
    """

    found = _find_token_usage_mapping(value)
    if found is None:
        return None
    mapping, explicit_container = found

    total, total_present = _one_counter(
        mapping, TOKEN_TOTAL_KEYS if explicit_container else TOKEN_EXPLICIT_TOTAL_KEYS
    )
    input_tokens, input_present = _one_counter(mapping, TOKEN_INPUT_KEYS)
    output_tokens, output_present = _one_counter(mapping, TOKEN_OUTPUT_KEYS)
    cached, cached_present = _one_counter(mapping, TOKEN_CACHED_KEYS)
    reasoning, reasoning_present = _one_counter(mapping, TOKEN_REASONING_KEYS)
    nested_cached, nested_cached_present = _detail_counter(
        mapping, TOKEN_INPUT_DETAILS_KEYS, TOKEN_CACHED_KEYS
    )
    nested_reasoning, nested_reasoning_present = _detail_counter(
        mapping, TOKEN_OUTPUT_DETAILS_KEYS, TOKEN_REASONING_KEYS
    )

    if any(
        present and counter is None
        for counter, present in (
            (total, total_present),
            (input_tokens, input_present),
            (output_tokens, output_present),
            (cached, cached_present),
            (reasoning, reasoning_present),
            (nested_cached, nested_cached_present),
            (nested_reasoning, nested_reasoning_present),
        )
    ):
        return None
    if cached is not None and nested_cached is not None and cached != nested_cached:
        return None
    if reasoning is not None and nested_reasoning is not None and reasoning != nested_reasoning:
        return None
    cached = cached if cached is not None else nested_cached
    reasoning = reasoning if reasoning is not None else nested_reasoning

    if cached is not None and (input_tokens is None or cached > input_tokens):
        return None
    if reasoning is not None and (output_tokens is None or reasoning > output_tokens):
        return None

    known_primary = (input_tokens or 0) + (output_tokens or 0)
    if total is not None and total < known_primary:
        return None
    if total is None and input_tokens is not None and output_tokens is not None:
        total = known_primary

    normalized: dict[str, int] = {}
    for name, counter in (
        ("input", input_tokens),
        ("output", output_tokens),
        ("cached", cached),
        ("reasoning", reasoning),
        ("total", total),
    ):
        if counter is not None:
            normalized[name] = counter
    if total is not None and input_tokens is not None and output_tokens is not None:
        other = total - input_tokens - output_tokens
        if other:
            normalized["other"] = other
    return normalized or None
