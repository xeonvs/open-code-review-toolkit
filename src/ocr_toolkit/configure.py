"""Configure OCR runtime settings from CI environment variables."""

from __future__ import annotations

import os
import sys
from typing import Any

from ocr_toolkit.common.language import resolve_review_language
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, update_ocr_config
from ocr_toolkit.provider_config import (
    ProviderConfigError,
    provider_config_from_environment,
)


class OCRRuntimeConfigError(Exception):
    """OCR runtime config from CI env is invalid."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool_env(name: str) -> bool:
    return _env(name).lower() == "true"


def build_config_updates() -> dict[str, Any]:
    """Build OCR config updates from already-normalized CI environment."""

    review_language = resolve_review_language()
    try:
        provider = provider_config_from_environment()
        llm_url = provider.require_inference_url()
        llm_token = provider.require_token()
        llm_model = provider.require_model()
    except ProviderConfigError as exc:
        raise OCRRuntimeConfigError(str(exc)) from exc
    request_controls = provider.request_controls

    updates: dict[str, Any] = {
        "language": review_language,
        "llm.url": llm_url,
        "llm.auth_token": llm_token,
        "llm.model": llm_model,
        "llm.protocol": request_controls.protocol,
        "llm.use_anthropic": request_controls.protocol == "anthropic",
        "llm.auth_header": request_controls.auth_header,
        "telemetry.enabled": _bool_env("OCR_TELEMETRY_ENABLED"),
        "telemetry.content_logging": _bool_env("OCR_TELEMETRY_CONTENT_LOGGING"),
    }

    if request_controls.extra_headers:
        updates["llm.extra_headers"] = request_controls.extra_headers

    if request_controls.extra_body is not None:
        updates["llm.extra_body"] = request_controls.extra_body

    if _bool_env("OCR_TELEMETRY_ENABLED"):
        updates["telemetry.exporter"] = _env("OCR_TELEMETRY_EXPORTER")
        otlp_endpoint = _env("OCR_TELEMETRY_OTLP_ENDPOINT")
        if otlp_endpoint:
            updates["telemetry.otlp_endpoint"] = otlp_endpoint

    return updates


def main() -> int:
    """Write OCR config and return a process exit code."""

    try:
        update_ocr_config(build_config_updates())
    except (OCRRuntimeConfigError, OCRConfigError) as exc:
        print(f"Failed to configure OCR runtime: {redact_sensitive(str(exc))}", file=sys.stderr)
        return 1
    print("OCR runtime config written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
