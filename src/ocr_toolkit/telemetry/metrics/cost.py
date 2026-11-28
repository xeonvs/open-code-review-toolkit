"""Estimate USD cost from usage, catalog rates, and an explicit model source."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from ocr_toolkit.telemetry.rates import cost_token_counts, publication_model, rates

CostSource = Literal["publication_model", "current_project_configuration", "unavailable"]
COST_SOURCES = ("publication_model", "current_project_configuration", "unavailable")


@dataclass(frozen=True, slots=True)
class CostObservation:
    source: CostSource
    usage_available: bool
    estimate: Decimal | None = None


def observe_cost(
    row: dict[str, Any], prices: dict[str, Any], *, project_model: str | None = None
) -> CostObservation:
    """Prefer the model from the publication, including when its catalog price is missing."""

    observed_model = publication_model(row)
    source: CostSource
    if observed_model is not None:
        model, source = observed_model, "publication_model"
    elif project_model and row.get("model_rejected") is not True:
        model, source = project_model, "current_project_configuration"
    else:
        model, source = None, "unavailable"

    usage = cost_token_counts(row.get("tokens"))
    if usage is None:
        return CostObservation(source, usage_available=False)
    input_tokens, output_tokens, cached, complete = usage
    if not complete:
        return CostObservation(source, usage_available=True)
    pricing = rates(prices.get(model)) if model is not None else None
    if pricing is None or (cached and "input_cache_read" not in pricing):
        return CostObservation(source, usage_available=True)
    estimate = (
        (input_tokens - cached) * pricing["prompt"]
        + output_tokens * pricing["completion"]
        + (cached * pricing["input_cache_read"] if cached else 0)
    )
    return CostObservation(source, usage_available=True, estimate=estimate)


def estimated_cost(row: dict[str, Any], prices: dict[str, Any]) -> Decimal | None:
    """Return the explicit-publication estimate without a project fallback."""

    return observe_cost(row, prices).estimate
