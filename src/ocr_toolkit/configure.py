"""Configure OCR runtime settings from CI environment variables."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlsplit

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, update_ocr_config

HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
LLM_PROTOCOLS = {"anthropic", "openai", "openai-responses"}


class OCRRuntimeConfigError(Exception):
    """OCR runtime config from CI env is invalid."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool_env(name: str) -> bool:
    return _env(name).lower() == "true"


def _required_env(name: str) -> str:
    value = _env(name)
    if not value:
        raise OCRRuntimeConfigError(f"{name} is required")
    return value


def _parse_extra_headers(value: str) -> dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise OCRRuntimeConfigError("OCR_LLM_EXTRA_HEADERS must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise OCRRuntimeConfigError("OCR_LLM_EXTRA_HEADERS must be a JSON object")
    headers: dict[str, str] = {}
    for key, raw_value in parsed.items():
        if not isinstance(key, str) or not HEADER_NAME_RE.fullmatch(key):
            raise OCRRuntimeConfigError(
                "OCR_LLM_EXTRA_HEADERS contains an invalid HTTP header name"
            )
        if not isinstance(raw_value, str):
            raise OCRRuntimeConfigError("OCR_LLM_EXTRA_HEADERS contains a non-string header value")
        if "\n" in raw_value or "\r" in raw_value:
            raise OCRRuntimeConfigError(
                "OCR_LLM_EXTRA_HEADERS contains a header value with a line break"
            )
        headers[key] = raw_value
    return headers


def _parse_extra_body(value: str) -> Any:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise OCRRuntimeConfigError("OCR_LLM_EXTRA_BODY must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OCRRuntimeConfigError("OCR_LLM_EXTRA_BODY must be a JSON object")
    return parsed


def _llm_protocol() -> str:
    """Resolve and validate the OCR 1.7.10 LLM wire protocol."""

    protocol = _env("OCR_LLM_PROTOCOL")
    legacy_mode = _env("OCR_USE_ANTHROPIC").lower()
    if legacy_mode not in {"", "false", "true"}:
        raise OCRRuntimeConfigError("OCR_USE_ANTHROPIC must be true or false when set")
    if not protocol:
        protocol = "anthropic" if legacy_mode == "true" else "openai"
    if protocol not in LLM_PROTOCOLS:
        allowed = ", ".join(sorted(LLM_PROTOCOLS))
        raise OCRRuntimeConfigError(f"OCR_LLM_PROTOCOL must be one of: {allowed}")

    if legacy_mode == "true" and protocol != "anthropic":
        raise OCRRuntimeConfigError("OCR_LLM_PROTOCOL conflicts with OCR_USE_ANTHROPIC")
    if legacy_mode == "false" and protocol == "anthropic":
        raise OCRRuntimeConfigError("OCR_LLM_PROTOCOL conflicts with OCR_USE_ANTHROPIC")
    return protocol


def _llm_extra_body(protocol: str) -> dict[str, Any] | None:
    """Return explicit OCR LLM extra body with safe Anthropic defaults merged."""

    raw_env = os.environ.get("OCR_LLM_EXTRA_BODY")
    raw = raw_env.strip() if raw_env is not None else ""
    explicit_object = bool(raw)
    extra_body = _parse_extra_body(raw)
    if extra_body is None:
        extra_body = {}

    if protocol == "anthropic" and _bool_env("OCR_ANTHROPIC_DISABLE_THINKING"):
        existing = extra_body.get("thinking")
        disabled = {"type": "disabled"}
        if existing is not None and existing != disabled:
            raise OCRRuntimeConfigError(
                "OCR_ANTHROPIC_DISABLE_THINKING conflicts with OCR_LLM_EXTRA_BODY.thinking"
            )
        extra_body["thinking"] = disabled

    return extra_body if explicit_object or extra_body else None


def build_config_updates() -> dict[str, Any]:
    """Build OCR config updates from already-normalized CI environment."""

    cli_language = _required_env("OCR_CLI_LANGUAGE")
    llm_url = _required_env("OCR_LLM_URL")
    llm_token = _required_env("OCR_LLM_TOKEN")
    try:
        parsed_llm_url = urlsplit(llm_url)
        parsed_llm_port = parsed_llm_url.port
        parsed_llm_hostname = parsed_llm_url.hostname
        parsed_llm_username = parsed_llm_url.username
        parsed_llm_password = parsed_llm_url.password
    except ValueError as exc:
        raise OCRRuntimeConfigError(
            "OCR_LLM_URL must be an absolute HTTPS URL without embedded credentials"
        ) from exc
    if (
        parsed_llm_url.scheme.lower() != "https"
        or not parsed_llm_hostname
        or (parsed_llm_port is None and parsed_llm_url.netloc.endswith(":"))
        or parsed_llm_username is not None
        or parsed_llm_password is not None
    ):
        raise OCRRuntimeConfigError(
            "OCR_LLM_URL must be an absolute HTTPS URL without embedded credentials"
        )
    llm_model = _required_env("OCR_LLM_MODEL")
    llm_protocol = _llm_protocol()
    auth_header = _env("OCR_LLM_AUTH_HEADER", "Authorization") or "Authorization"
    if not HEADER_NAME_RE.fullmatch(auth_header):
        raise OCRRuntimeConfigError("OCR_LLM_AUTH_HEADER is not a valid HTTP header name")

    updates: dict[str, Any] = {
        "language": cli_language,
        "llm.url": llm_url,
        "llm.auth_token": llm_token,
        "llm.model": llm_model,
        "llm.protocol": llm_protocol,
        "llm.use_anthropic": llm_protocol == "anthropic",
        "llm.auth_header": auth_header,
        "telemetry.enabled": _bool_env("OCR_TELEMETRY_ENABLED"),
        "telemetry.content_logging": _bool_env("OCR_TELEMETRY_CONTENT_LOGGING"),
    }

    extra_headers = _parse_extra_headers(_env("OCR_LLM_EXTRA_HEADERS"))
    if any(header.casefold() == auth_header.casefold() for header in extra_headers):
        raise OCRRuntimeConfigError("OCR_LLM_EXTRA_HEADERS must not duplicate OCR_LLM_AUTH_HEADER")
    if extra_headers:
        updates["llm.extra_headers"] = extra_headers

    extra_body = _llm_extra_body(llm_protocol)
    if extra_body is not None:
        updates["llm.extra_body"] = extra_body

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
