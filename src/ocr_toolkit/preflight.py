"""Fail-fast checks for OCR CI before LLM review spend."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.provider_config import (
    HEADER_NAME_RE,
    ProviderConfigError,
    provider_config_from_environment,
)

HTTP_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BODY_BYTES = 2_000_000
RESPONSE_READ_CHUNK_BYTES = 64 * 1024
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "open-code-review-ci-preflight/1.0",
}
EXPECTED_OCR_VERSION = "1.9.10"


class PreflightError(Exception):
    """A required OCR CI preflight check failed."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent urllib from forwarding secret headers across redirects."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


URL_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _set_response_timeout(response: Any, timeout: float) -> None:
    """Best-effort update of the underlying socket timeout before each read."""

    try:
        sock = response.fp.raw._sock
    except AttributeError:
        return
    sock.settimeout(timeout)


def _safe_url(url: str) -> str:
    """Return a URL safe for CI diagnostics."""

    return redact_sensitive(url)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _gitlab_api_root() -> str:
    api_root = _env("CI_API_V4_URL")
    if api_root:
        return api_root.rstrip("/")

    server_url = _env("CI_SERVER_URL")
    if not server_url:
        raise PreflightError("CI_SERVER_URL or CI_API_V4_URL is required")
    return f"{server_url.rstrip('/')}/api/v4"


def _request_json(url: str, headers: dict[str, str]) -> Any:
    parsed_url = urllib.parse.urlsplit(url)
    if headers and (parsed_url.scheme != "https" or not parsed_url.netloc):
        raise PreflightError(f"Refusing to send credentials to non-HTTPS URL: {_safe_url(url)}")

    request_headers: dict[str, str] = dict(DEFAULT_REQUEST_HEADERS)
    for key, value in headers.items():
        if not HEADER_NAME_RE.fullmatch(key) or "\r" in value or "\n" in value:
            raise PreflightError(f"GET {_safe_url(url)} contains an invalid HTTP header")
        request_headers[key] = value

    raw_body = b""
    last_error: Exception | None = None
    deadline = time.monotonic() + HTTP_TIMEOUT_SECONDS
    retryable_statuses = {408, 429, 500, 502, 503, 504}
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PreflightError(f"GET {_safe_url(url)} timed out after {HTTP_TIMEOUT_SECONDS}s")
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with URL_OPENER.open(request, timeout=remaining) as response:
                chunks: list[bytes] = []
                total_bytes = 0
                while total_bytes < MAX_RESPONSE_BODY_BYTES:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    _set_response_timeout(response, remaining)
                    chunk = response.read(
                        min(RESPONSE_READ_CHUNK_BYTES, MAX_RESPONSE_BODY_BYTES - total_bytes)
                    )
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total_bytes += len(chunk)
                if total_bytes >= MAX_RESPONSE_BODY_BYTES:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    _set_response_timeout(response, remaining)
                    if response.read(1):
                        raise PreflightError(
                            f"GET {_safe_url(url)} response exceeds {MAX_RESPONSE_BODY_BYTES} bytes"
                        )
                raw_body = b"".join(chunks)
            break
        except urllib.error.HTTPError as exc:
            raw_error = exc.read(16_384).decode("utf-8", errors="replace").strip()
            if exc.code not in retryable_statuses or attempt == 2:
                detail = f": {redact_sensitive(raw_error)}" if raw_error else ""
                raise PreflightError(
                    f"GET {_safe_url(url)} failed with HTTP {exc.code}{detail}"
                ) from exc
            last_error = exc
        except TimeoutError as exc:
            last_error = exc
            if attempt == 2:
                raise PreflightError(
                    f"GET {_safe_url(url)} timed out after {HTTP_TIMEOUT_SECONDS}s"
                ) from exc
        except OSError as exc:
            last_error = exc
            if attempt == 2:
                raise PreflightError(
                    f"GET {_safe_url(url)} failed: {redact_sensitive(str(exc))}"
                ) from exc
        sleep_seconds = min(1.0, max(0.0, deadline - time.monotonic()))
        if sleep_seconds:
            time.sleep(sleep_seconds)
    else:
        raise PreflightError(f"GET {_safe_url(url)} failed: {redact_sensitive(str(last_error))}")

    if not raw_body:
        return None

    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"GET {_safe_url(url)} returned non-JSON metadata") from exc


def validate_gitlab_access() -> None:
    """Verify the configured bot token can read this project and MR."""

    token = _env("GITLAB_API_TOKEN")
    project_id = _env("CI_PROJECT_ID")
    mr_iid = _env("CI_MERGE_REQUEST_IID")
    if not token:
        raise PreflightError("GITLAB_API_TOKEN is required")
    if not project_id or not mr_iid:
        raise PreflightError("CI_PROJECT_ID and CI_MERGE_REQUEST_IID are required")

    api_root = _gitlab_api_root()
    project_id_encoded = urllib.parse.quote_plus(project_id)
    headers = {"PRIVATE-TOKEN": token}

    print("Validating GitLab token access to project and merge request")
    _request_json(f"{api_root}/user", headers)
    _request_json(f"{api_root}/projects/{project_id_encoded}", headers)
    _request_json(f"{api_root}/projects/{project_id_encoded}/merge_requests/{mr_iid}", headers)


def validate_ocr_binary() -> None:
    """Verify that the external OCR binary has the supported release."""

    executable = shutil.which("ocr")
    if executable is None:
        raise PreflightError(
            "Open Code Review binary 'ocr' was not found on PATH; install it separately"
        )
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"Cannot run ocr --version: {redact_sensitive(str(exc))}") from exc
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode != 0:
        raise PreflightError(
            f"ocr --version exited {completed.returncode}: {redact_sensitive(output)}"
        )
    if not re.search(rf"(?<![0-9.])v?{re.escape(EXPECTED_OCR_VERSION)}(?![0-9.])", output):
        raise PreflightError(
            f"Unsupported Open Code Review version; expected {EXPECTED_OCR_VERSION}, "
            f"got {redact_sensitive(output)!r}"
        )
    print(f"Open Code Review binary validated: {EXPECTED_OCR_VERSION}")


def _models_url() -> str:
    try:
        return provider_config_from_environment().require_models_url()
    except ProviderConfigError as exc:
        raise PreflightError(str(exc)) from exc


def _context_length(model: dict[str, Any]) -> int:
    for key in (
        "context_length",
        "contextLength",
        "max_context_length",
        "maxContextLength",
    ):
        value = model.get(key)
        if value is None:
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return 0


def _allowed_models() -> list[str]:
    """Return exact model ids allowed without querying gateway metadata."""

    value = _env("OCR_LLM_ALLOWED_MODELS")
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_allowed_model(model_id: str) -> bool:
    """Return whether model id is in the optional offline allowlist."""

    allowed = _allowed_models()
    if not allowed:
        return False
    return model_id in allowed


def _validate_allowed_model(model_id: str) -> bool:
    """Validate model id against the optional offline allowlist."""

    allowed = _allowed_models()
    if not allowed:
        return False
    if not _is_allowed_model(model_id):
        raise PreflightError(f"OCR_LLM_MODEL {model_id!r} is not listed in OCR_LLM_ALLOWED_MODELS")
    print(f"OCR model allowed by OCR_LLM_ALLOWED_MODELS: {model_id}")
    return True


def validate_llm_model() -> None:
    """Verify the selected model exists in OpenAI-compatible metadata."""

    try:
        provider = provider_config_from_environment()
        model_id = provider.require_model()
    except ProviderConfigError as exc:
        raise PreflightError(str(exc)) from exc
    allowlist_matched = _validate_allowed_model(model_id)

    validate_mode = _env("OCR_LLM_VALIDATE_MODEL", "false").lower()
    if validate_mode in {"false", "0", "no", "off"}:
        print("OCR LLM /models validation disabled by OCR_LLM_VALIDATE_MODEL=false")
        return
    if validate_mode not in {"true", "1", "yes", "on", "auto"}:
        raise PreflightError("OCR_LLM_VALIDATE_MODEL must be true, false, or auto")

    try:
        headers = provider.request_headers()
    except ProviderConfigError as exc:
        raise PreflightError(str(exc)) from exc

    print("Validating OCR model against LLM gateway metadata")
    try:
        models_url = provider.require_models_url()
    except ProviderConfigError as exc:
        if validate_mode == "auto" and allowlist_matched:
            print(
                "OCR LLM /models URL unavailable; continuing because "
                f"OCR_LLM_MODEL is allowlisted: {redact_sensitive(str(exc))}",
                file=sys.stderr,
            )
            return
        raise PreflightError(str(exc)) from exc
    try:
        payload = _request_json(models_url, headers)
    except PreflightError as exc:
        if validate_mode == "auto" and allowlist_matched:
            print(
                "OCR LLM /models validation unavailable; continuing because "
                f"OCR_LLM_MODEL is allowlisted: {redact_sensitive(str(exc))}",
                file=sys.stderr,
            )
            return
        raise
    items = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise PreflightError("LLM /models response is not a model list")

    matched_model = next(
        (item for item in items if isinstance(item, dict) and item.get("id") == model_id),
        None,
    )
    if matched_model is None:
        raise PreflightError(f"Gateway model {model_id!r} was not found in /models")

    context_length = _context_length(matched_model)
    if context_length <= 0:
        print(f"LLM model validated: {model_id} context_length=unknown")
        return
    print(f"LLM model validated: {model_id} context_length={context_length}")


def main() -> int:
    """Run all fail-fast checks."""

    try:
        validate_ocr_binary()
        validate_gitlab_access()
        validate_llm_model()
    except PreflightError as exc:
        print(f"OCR preflight failed: {redact_sensitive(str(exc))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
