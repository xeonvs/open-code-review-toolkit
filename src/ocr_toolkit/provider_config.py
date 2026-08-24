"""Own provider-neutral LLM request controls derived from the environment."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
POSITIVE_DECIMAL_RE = re.compile(r"^[1-9][0-9]*$")
LLM_PROTOCOLS = frozenset({"anthropic", "openai", "openai-responses"})
MAX_COMPLETION_TOKENS_LIMIT = 1_000_000
COMPLETION_TOKEN_FIELDS = {
    "anthropic": "max_tokens",
    "openai": "max_completion_tokens",
    "openai-responses": "max_output_tokens",
}
TERMINAL_ENDPOINTS = {
    "anthropic": "/v1/messages",
    "openai": "/chat/completions",
    "openai-responses": "/responses",
}


class ProviderConfigError(Exception):
    """Provider settings from the operator environment are invalid."""


@dataclass(frozen=True)
class ProviderRequestControls:
    """Validated protocol, headers, and request-body overlay for OCR."""

    protocol: str
    auth_header: str
    extra_headers: dict[str, str] = field(repr=False)
    extra_body: dict[str, Any] | None = field(repr=False)


@dataclass(frozen=True)
class ProviderConfig:
    """Canonical provider configuration shared by configure and preflight."""

    inference_url: str | None
    api_root_url: str | None
    models_url: str | None
    model: str | None
    token: str | None = field(repr=False)
    request_controls: ProviderRequestControls = field(repr=False)

    def require_inference_url(self) -> str:
        """Return the normalized OCR API root or reject missing review configuration."""

        if self.inference_url is None:
            raise ProviderConfigError("OCR_LLM_URL is required")
        return self.inference_url

    def require_model(self) -> str:
        """Return the configured model identifier."""

        if self.model is None:
            raise ProviderConfigError("OCR_LLM_MODEL is required")
        return self.model

    def require_token(self) -> str:
        """Return the configured provider credential without rendering it."""

        if self.token is None:
            raise ProviderConfigError("OCR_LLM_TOKEN is required")
        return self.token

    def require_models_url(self) -> str:
        """Return the safe auxiliary URL or explain how to make it explicit."""

        if self.models_url is None:
            raise ProviderConfigError(
                "Cannot derive LLM /models URL; set OCR_LLM_MODELS_URL or "
                "set OCR_LLM_VALIDATE_MODEL=false"
            )
        return self.models_url

    def request_headers(self) -> dict[str, str]:
        """Return metadata-request headers with the provider credential."""

        headers = dict(self.request_controls.extra_headers)
        headers[self.request_controls.auth_header] = f"Bearer {self.require_token()}"
        return headers


def _env(environment: Mapping[str, str], name: str, default: str = "") -> str:
    return environment.get(name, default).strip()


def _parse_protocol(environment: Mapping[str, str]) -> str:
    """Return the explicit closed OCR wire protocol."""

    if "OCR_USE_ANTHROPIC" in environment:
        raise ProviderConfigError(
            "OCR_USE_ANTHROPIC was removed; set OCR_LLM_PROTOCOL=anthropic explicitly"
        )
    protocol = _env(environment, "OCR_LLM_PROTOCOL", "openai") or "openai"
    if protocol not in LLM_PROTOCOLS:
        allowed = ", ".join(sorted(LLM_PROTOCOLS))
        raise ProviderConfigError(f"OCR_LLM_PROTOCOL must be one of: {allowed}")
    return protocol


def _parse_extra_headers(value: str) -> dict[str, str]:
    """Parse the optional JSON header map without admitting line breaks."""

    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ProviderConfigError("OCR_LLM_EXTRA_HEADERS must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ProviderConfigError("OCR_LLM_EXTRA_HEADERS must be a JSON object")
    headers: dict[str, str] = {}
    for key, raw_value in parsed.items():
        if not isinstance(key, str) or not HEADER_NAME_RE.fullmatch(key):
            raise ProviderConfigError("OCR_LLM_EXTRA_HEADERS contains an invalid HTTP header name")
        if not isinstance(raw_value, str):
            raise ProviderConfigError("OCR_LLM_EXTRA_HEADERS contains a non-string header value")
        if "\n" in raw_value or "\r" in raw_value:
            raise ProviderConfigError(
                "OCR_LLM_EXTRA_HEADERS contains a header value with a line break"
            )
        headers[key] = raw_value
    return headers


def _parse_extra_body(value: str) -> tuple[dict[str, Any], bool]:
    """Parse the optional JSON request overlay and retain explicit emptiness."""

    if not value:
        return {}, False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ProviderConfigError("OCR_LLM_EXTRA_BODY must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ProviderConfigError("OCR_LLM_EXTRA_BODY must be a JSON object")
    return parsed, True


def _parse_completion_cap(value: str) -> int | None:
    """Parse the optional bounded positive completion-token cap."""

    if not value:
        return None
    if len(value) > len(str(MAX_COMPLETION_TOKENS_LIMIT)):
        raise ProviderConfigError(
            f"OCR_LLM_MAX_COMPLETION_TOKENS must be at most {MAX_COMPLETION_TOKENS_LIMIT}"
        )
    if POSITIVE_DECIMAL_RE.fullmatch(value) is None:
        raise ProviderConfigError(
            "OCR_LLM_MAX_COMPLETION_TOKENS must be a positive decimal integer"
        )
    parsed = int(value)
    if parsed > MAX_COMPLETION_TOKENS_LIMIT:
        raise ProviderConfigError(
            f"OCR_LLM_MAX_COMPLETION_TOKENS must be at most {MAX_COMPLETION_TOKENS_LIMIT}"
        )
    return parsed


def _parse_https_url(value: str, name: str) -> SplitResult:
    """Parse one absolute credential-free HTTPS URL with no fragment."""

    if any(character.isspace() for character in value):
        raise ProviderConfigError(
            f"{name} must be an absolute HTTPS URL without embedded credentials or a fragment"
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ProviderConfigError(
            f"{name} must be an absolute HTTPS URL without embedded credentials or a fragment"
        ) from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or (port is None and parsed.netloc.endswith(":"))
        or parsed.username is not None
        or parsed.password is not None
        or "#" in value
    ):
        raise ProviderConfigError(
            f"{name} must be an absolute HTTPS URL without embedded credentials or a fragment"
        )
    return SplitResult("https", parsed.netloc, parsed.path.rstrip("/"), parsed.query, "")


def _canonical_provider_urls(
    llm_url: str, models_url: str, protocol: str
) -> tuple[str | None, str | None, str | None]:
    """Return normalized inference, API-root, and auxiliary provider URLs."""

    inference: str | None = None
    api_root: str | None = None
    derived_models: str | None = None
    if llm_url:
        parsed = _parse_https_url(llm_url, "OCR_LLM_URL")
        path = parsed.path
        matched_protocol: str | None = None
        for candidate, suffix in TERMINAL_ENDPOINTS.items():
            if path.endswith(suffix):
                matched_protocol = candidate
                path = path[: -len(suffix)].rstrip("/")
                break
        if matched_protocol is not None and matched_protocol != protocol:
            raise ProviderConfigError(
                "OCR_LLM_URL terminal endpoint conflicts with OCR_LLM_PROTOCOL; "
                f"use {protocol!r} endpoint semantics or provide the API root"
            )
        root_parts = SplitResult(parsed.scheme, parsed.netloc, path, "", "")
        api_root = urlunsplit(root_parts)
        inference = urlunsplit(root_parts._replace(query=parsed.query))
        if not parsed.query:
            derived_models = f"{api_root.rstrip('/')}/models"

    explicit_models: str | None = None
    if models_url:
        explicit_models = urlunsplit(_parse_https_url(models_url, "OCR_LLM_MODELS_URL"))
    return inference, api_root, explicit_models or derived_models


def request_controls_from_environment(
    environment: Mapping[str, str] | None = None,
) -> ProviderRequestControls:
    """Build validated OCR request controls from one environment snapshot."""

    values = os.environ if environment is None else environment
    protocol = _parse_protocol(values)
    auth_header = _env(values, "OCR_LLM_AUTH_HEADER", "Authorization") or "Authorization"
    if HEADER_NAME_RE.fullmatch(auth_header) is None:
        raise ProviderConfigError("OCR_LLM_AUTH_HEADER is not a valid HTTP header name")

    extra_headers = _parse_extra_headers(_env(values, "OCR_LLM_EXTRA_HEADERS"))
    if any(header.casefold() == auth_header.casefold() for header in extra_headers):
        raise ProviderConfigError("OCR_LLM_EXTRA_HEADERS must not duplicate OCR_LLM_AUTH_HEADER")

    extra_body, explicit_body = _parse_extra_body(_env(values, "OCR_LLM_EXTRA_BODY"))
    completion_cap = _parse_completion_cap(_env(values, "OCR_LLM_MAX_COMPLETION_TOKENS"))
    if completion_cap is not None:
        field = COMPLETION_TOKEN_FIELDS[protocol]
        existing = extra_body.get(field)
        if field in extra_body and (type(existing) is not int or existing != completion_cap):
            raise ProviderConfigError(
                f"OCR_LLM_MAX_COMPLETION_TOKENS conflicts with OCR_LLM_EXTRA_BODY.{field}; "
                "remove one setting or make the integer values equal"
            )
        extra_body[field] = completion_cap

    if protocol == "anthropic" and _env(values, "OCR_ANTHROPIC_DISABLE_THINKING").lower() == "true":
        existing = extra_body.get("thinking")
        disabled = {"type": "disabled"}
        if existing is not None and existing != disabled:
            raise ProviderConfigError(
                "OCR_ANTHROPIC_DISABLE_THINKING conflicts with OCR_LLM_EXTRA_BODY.thinking"
            )
        extra_body["thinking"] = disabled

    return ProviderRequestControls(
        protocol=protocol,
        auth_header=auth_header,
        extra_headers=extra_headers,
        extra_body=extra_body if explicit_body or extra_body else None,
    )


def provider_config_from_environment(
    environment: Mapping[str, str] | None = None,
) -> ProviderConfig:
    """Build one canonical provider configuration from an environment snapshot."""

    values: Mapping[str, str] = dict(os.environ) if environment is None else dict(environment)
    request_controls = request_controls_from_environment(values)
    inference_url, api_root_url, models_url = _canonical_provider_urls(
        _env(values, "OCR_LLM_URL"),
        _env(values, "OCR_LLM_MODELS_URL"),
        request_controls.protocol,
    )
    return ProviderConfig(
        inference_url=inference_url,
        api_root_url=api_root_url,
        models_url=models_url,
        model=_env(values, "OCR_LLM_MODEL") or None,
        token=_env(values, "OCR_LLM_TOKEN") or None,
        request_controls=request_controls,
    )
