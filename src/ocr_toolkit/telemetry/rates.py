"""Validate model identifiers and finite per-token USD catalog rates."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, NamedTuple

MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,254}\Z")
RATE_KEYS = ("prompt", "completion", "input_cache_read")


class CostTokenCounts(NamedTuple):
    """Validated usage and whether catalog rates cover every reported token."""

    input: int
    output: int
    cached: int
    complete: bool


def publication_model(row: dict[str, Any]) -> str | None:
    """Read a recorded model name with the same precedence as pricing."""

    model = row.get("model")
    return (
        model
        if row.get("model_rejected") is not True and isinstance(model, str) and model.strip()
        else None
    )


def cost_token_counts(value: object) -> CostTokenCounts | None:
    """Return valid primary counts and whether priceable buckets cover the entire usage."""

    if not isinstance(value, dict):
        return None
    counts = []
    for count in (value.get("input"), value.get("output"), value.get("cached", 0)):
        if type(count) is not int or not 0 <= count < 2**63:
            return None
        counts.append(count)
    input_tokens, output_tokens, cached = counts
    if cached > input_tokens:
        return None
    total = value.get("total", input_tokens + output_tokens)
    other = value.get("other", 0)
    complete = (
        type(total) is int
        and total == input_tokens + output_tokens
        and type(other) is int
        and other == 0
    )
    return CostTokenCounts(input_tokens, output_tokens, cached, complete)


def rates(value: object) -> dict[str, Decimal] | None:
    if not isinstance(value, dict):
        return None
    result = {}
    for key in RATE_KEYS:
        if key == "input_cache_read" and key not in value:
            continue
        raw = value.get(key)
        if not isinstance(raw, (str, int, float)) or len(str(raw)) > 80:
            return None
        try:
            rate = Decimal(str(raw))
        except InvalidOperation:
            return None
        if not rate.is_finite() or rate < 0 or abs(rate.adjusted()) > 30:
            return None
        result[key] = rate
    return result
