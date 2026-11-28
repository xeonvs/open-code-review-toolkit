"""Capture normalized per-token rates from the operator's configured model catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from http.client import HTTPException

from ocr_toolkit.preflight import PreflightError, _request_json
from ocr_toolkit.provider_config import ProviderConfigError, provider_config_from_environment
from ocr_toolkit.telemetry.rates import MODEL, rates


def normalized_prices(payload: object) -> dict[str, dict[str, str]]:
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return {}
    prices = {}
    for model in models:
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("id"), str)
            or not MODEL.fullmatch(model["id"])
        ):
            continue
        if pricing := rates(model.get("pricing")):
            prices[model["id"]] = {key: str(rate) for key, rate in pricing.items()}
    return prices


def capture_prices() -> tuple[dict[str, dict[str, str]] | None, str | None]:
    try:
        provider = provider_config_from_environment()
        payload = _request_json(provider.require_models_url(), provider.request_headers())
        prices = normalized_prices(payload)
    except (
        PreflightError,
        ProviderConfigError,
        ValueError,
        RecursionError,
        HTTPException,
        OSError,
    ):
        return None, None
    if not prices:
        return None, None
    return prices, datetime.now(UTC).isoformat()
