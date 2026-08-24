"""Project private OCR retry diagnostics into closed provider failure reasons."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

RETRY_REPORT_SCHEMA = "ocr.llm-retry-report/v1"
MAX_RETRY_REQUESTS = 10_000
MAX_ATTEMPTS_PER_REQUEST = 100
ERROR_CLASSES = frozenset(
    {
        "authentication",
        "cancelled",
        "network",
        "overloaded",
        "provider",
        "rate_limited",
        "timeout",
        "unknown",
    }
)
FAILURE_PHASES = frozenset(
    {"context", "http", "response_decode", "response_status", "stream", "transport"}
)
REQUEST_OUTCOMES = frozenset({"cancelled", "failed", "recovered", "succeeded"})
ATTEMPT_OUTCOMES = frozenset({"error", "success"})


class ProviderFailureReason(StrEnum):
    """Closed provider-neutral failure reason safe for control-flow and rendering."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_OR_SPENDING_LIMIT = "rate-or-spending-limit"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    NETWORK = "network"
    ENDPOINT_OR_MODEL_NOT_FOUND = "endpoint-or-model-not-found"
    REQUEST_REJECTED = "request-rejected"
    PROVIDER_UNAVAILABLE = "provider-unavailable"
    INVALID_RESPONSE = "invalid-response"
    CANCELLED = "cancelled"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RetryReportError(Exception):
    """The private retry report is malformed or internally inconsistent."""


def _bounded_count(value: object, field: str, *, maximum: int = MAX_RETRY_REQUESTS) -> int:
    """Return one bounded non-negative JSON integer."""

    if type(value) is not int or not 0 <= value <= maximum:
        raise RetryReportError(f"retry report field {field!r} is invalid")
    return value


def _http_reason(status_code: int) -> ProviderFailureReason:
    """Map one observed non-success HTTP status to a closed reason."""

    if status_code == 401:
        return ProviderFailureReason.AUTHENTICATION
    if status_code == 403:
        return ProviderFailureReason.AUTHORIZATION
    if status_code in {402, 429}:
        return ProviderFailureReason.RATE_OR_SPENDING_LIMIT
    if status_code == 404:
        return ProviderFailureReason.ENDPOINT_OR_MODEL_NOT_FOUND
    if status_code in {408, 504}:
        return ProviderFailureReason.TIMEOUT
    if status_code == 529:
        return ProviderFailureReason.OVERLOADED
    if 500 <= status_code <= 599:
        return ProviderFailureReason.PROVIDER_UNAVAILABLE
    return ProviderFailureReason.REQUEST_REJECTED


def _validate_http_class(status_code: int, error_class: str, failure_phase: str) -> None:
    """Reject attempt fields that contradict OCR's status-derived v1 classifier."""

    if failure_phase != "http":
        raise RetryReportError("retry report HTTP status has a non-HTTP failure phase")
    expected = "provider"
    if status_code == 429:
        expected = "rate_limited"
    elif status_code == 529:
        expected = "overloaded"
    elif status_code in {401, 403}:
        expected = "authentication"
    elif status_code in {408, 504}:
        expected = "timeout"
    if error_class != expected:
        raise RetryReportError("retry report HTTP status contradicts its error class")


def _attempt_reason(attempt: Mapping[str, Any]) -> ProviderFailureReason | None:
    """Validate one attempt and return its closed error reason, if any."""

    outcome = attempt.get("outcome")
    if outcome not in ATTEMPT_OUTCOMES:
        raise RetryReportError("retry report attempt outcome is invalid")
    status_value = attempt.get("status_code", 0)
    if type(status_value) is not int or not (status_value == 0 or 100 <= status_value <= 599):
        raise RetryReportError("retry report attempt status_code is invalid")
    error_class = attempt.get("error_class", "")
    failure_phase = attempt.get("failure_phase", "")
    if outcome == "success":
        if error_class or failure_phase or not 200 <= status_value <= 299:
            raise RetryReportError("retry report success attempt is inconsistent")
        return None
    if error_class not in ERROR_CLASSES or failure_phase not in FAILURE_PHASES:
        raise RetryReportError("retry report error attempt classification is invalid")

    if status_value and not 200 <= status_value <= 299:
        _validate_http_class(status_value, error_class, failure_phase)
        return _http_reason(status_value)
    if status_value:
        if failure_phase not in {"response_decode", "response_status", "stream"}:
            raise RetryReportError("retry report successful HTTP status has invalid failure phase")
        if error_class not in {"network", "provider", "unknown"}:
            raise RetryReportError("retry report successful HTTP status has invalid error class")
        return ProviderFailureReason.INVALID_RESPONSE
    if failure_phase == "http" or error_class in {
        "authentication",
        "overloaded",
        "provider",
        "rate_limited",
    }:
        raise RetryReportError("retry report transport failure has HTTP-only classification")
    if error_class == "cancelled":
        return ProviderFailureReason.CANCELLED
    if error_class == "timeout":
        return ProviderFailureReason.TIMEOUT
    if error_class == "network":
        if failure_phase in {"response_decode", "response_status", "stream"}:
            return ProviderFailureReason.INVALID_RESPONSE
        return ProviderFailureReason.NETWORK
    return ProviderFailureReason.UNKNOWN


def _request_reason(request: Mapping[str, Any]) -> ProviderFailureReason | None:
    """Validate one logical request and classify only its terminal failure."""

    outcome = request.get("outcome")
    if outcome not in REQUEST_OUTCOMES:
        raise RetryReportError("retry report request outcome is invalid")
    attempts = request.get("attempts")
    if not isinstance(attempts, list) or not 0 < len(attempts) <= MAX_ATTEMPTS_PER_REQUEST:
        raise RetryReportError("retry report request attempts are invalid")
    reasons: list[ProviderFailureReason | None] = []
    for index, attempt in enumerate(attempts, start=1):
        if (
            not isinstance(attempt, dict)
            or type(attempt.get("attempt")) is not int
            or attempt.get("attempt") != index
        ):
            raise RetryReportError("retry report attempt order is invalid")
        reasons.append(_attempt_reason(attempt))
    if outcome == "succeeded":
        if len(attempts) < 2 or any(reason is not None for reason in reasons):
            raise RetryReportError("retry report succeeded request is inconsistent")
        return None
    if outcome == "recovered":
        if reasons[-1] is not None or not any(reason is not None for reason in reasons[:-1]):
            raise RetryReportError("retry report recovered request is inconsistent")
        return None
    if outcome == "cancelled":
        return ProviderFailureReason.CANCELLED
    if reasons[-1] is None:
        raise RetryReportError("retry report failed request ends in success")
    return reasons[-1]


def parse_retry_report_failure(result: object) -> ProviderFailureReason | None:
    """Validate retry-report v1 and return one closed terminal failure reason."""

    if not isinstance(result, dict):
        raise RetryReportError("OCR result must be an object")
    report = result.get("retry_report")
    if report is None:
        return None
    if not isinstance(report, dict) or report.get("schema_version") != RETRY_REPORT_SCHEMA:
        raise RetryReportError("OCR retry report schema is unsupported")
    requests = report.get("requests")
    if not isinstance(requests, list) or not 0 < len(requests) <= MAX_RETRY_REQUESTS:
        raise RetryReportError("OCR retry report requests are invalid")

    total_requests = _bounded_count(report.get("total_requests"), "total_requests")
    expected_counts = {
        "retried_requests": sum(
            1
            for request in requests
            if isinstance(request, dict)
            and isinstance(request.get("attempts"), list)
            and len(request["attempts"]) > 1
        ),
        "total_retries": sum(
            max(len(request.get("attempts", [])) - 1, 0)
            for request in requests
            if isinstance(request, dict) and isinstance(request.get("attempts"), list)
        ),
        "recovered_requests": sum(
            1
            for request in requests
            if isinstance(request, dict) and request.get("outcome") == "recovered"
        ),
        "failed_requests": sum(
            1
            for request in requests
            if isinstance(request, dict) and request.get("outcome") == "failed"
        ),
        "cancelled_requests": sum(
            1
            for request in requests
            if isinstance(request, dict) and request.get("outcome") == "cancelled"
        ),
    }
    if total_requests < len(requests):
        raise RetryReportError("OCR retry report total_requests is inconsistent")
    for field, expected in expected_counts.items():
        if _bounded_count(report.get(field), field, maximum=MAX_RETRY_REQUESTS * 100) != expected:
            raise RetryReportError(f"OCR retry report {field} is inconsistent")

    reasons: list[ProviderFailureReason] = []
    for request in requests:
        if not isinstance(request, dict):
            raise RetryReportError("OCR retry report request is invalid")
        reason = _request_reason(request)
        if reason is not None:
            reasons.append(reason)
    if not reasons:
        return None
    counts = Counter(reasons)
    return next(iter(counts)) if len(counts) == 1 else ProviderFailureReason.MIXED


def provider_failure_reason(result: object) -> ProviderFailureReason | None:
    """Return a closed reason, degrading malformed private diagnostics to unavailable."""

    try:
        return parse_retry_report_failure(result)
    except RetryReportError:
        return None
