"""Project private OCR retry diagnostics into closed provider failure reasons."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
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


class ProviderFailureDetail(StrEnum):
    """Closed protocol detail safe for one toolkit-authored CI diagnostic."""

    HTTP_BAD_REQUEST = "http-bad-request"
    HTTP_UNAUTHORIZED = "http-unauthorized"
    HTTP_PAYMENT_REQUIRED = "http-payment-required"
    HTTP_FORBIDDEN = "http-forbidden"
    HTTP_NOT_FOUND = "http-not-found"
    HTTP_REQUEST_TIMEOUT = "http-request-timeout"
    HTTP_CONFLICT = "http-conflict"
    HTTP_CONTENT_TOO_LARGE = "http-content-too-large"
    HTTP_UNPROCESSABLE_CONTENT = "http-unprocessable-content"
    HTTP_RATE_LIMITED = "http-rate-limited"
    HTTP_GATEWAY_TIMEOUT = "http-gateway-timeout"
    HTTP_OVERLOADED = "http-overloaded"
    HTTP_SERVER_ERROR = "http-server-error"
    HTTP_NON_SUCCESS = "http-non-success"
    RESPONSE_DECODE = "response-decode"
    RESPONSE_STATUS = "response-status"
    STREAM = "stream"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderFailureProjection:
    """Validated provider-neutral failure state retained only for operator output."""

    reason: ProviderFailureReason
    details: tuple[tuple[ProviderFailureDetail, int], ...]
    status_code: int | None
    failed_requests: int
    cancelled_requests: int
    retried_requests: int
    total_retries: int
    recovered_requests: int


@dataclass(frozen=True)
class _AttemptFailure:
    """Internal terminal-attempt projection after retry-report validation."""

    reason: ProviderFailureReason
    detail: ProviderFailureDetail
    status_code: int | None


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


def _http_detail(status_code: int) -> ProviderFailureDetail:
    """Map one bounded HTTP status to provider-neutral protocol detail."""

    return {
        400: ProviderFailureDetail.HTTP_BAD_REQUEST,
        401: ProviderFailureDetail.HTTP_UNAUTHORIZED,
        402: ProviderFailureDetail.HTTP_PAYMENT_REQUIRED,
        403: ProviderFailureDetail.HTTP_FORBIDDEN,
        404: ProviderFailureDetail.HTTP_NOT_FOUND,
        408: ProviderFailureDetail.HTTP_REQUEST_TIMEOUT,
        409: ProviderFailureDetail.HTTP_CONFLICT,
        413: ProviderFailureDetail.HTTP_CONTENT_TOO_LARGE,
        422: ProviderFailureDetail.HTTP_UNPROCESSABLE_CONTENT,
        429: ProviderFailureDetail.HTTP_RATE_LIMITED,
        504: ProviderFailureDetail.HTTP_GATEWAY_TIMEOUT,
        529: ProviderFailureDetail.HTTP_OVERLOADED,
    }.get(
        status_code,
        (
            ProviderFailureDetail.HTTP_SERVER_ERROR
            if 500 <= status_code <= 599
            else ProviderFailureDetail.HTTP_NON_SUCCESS
        ),
    )


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


def _attempt_failure(attempt: Mapping[str, Any]) -> _AttemptFailure | None:
    """Validate one attempt and return its closed error projection, if any."""

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
        return _AttemptFailure(_http_reason(status_value), _http_detail(status_value), status_value)
    if status_value:
        if failure_phase not in {"response_decode", "response_status", "stream"}:
            raise RetryReportError("retry report successful HTTP status has invalid failure phase")
        if error_class not in {"network", "provider", "unknown"}:
            raise RetryReportError("retry report successful HTTP status has invalid error class")
        detail = {
            "response_decode": ProviderFailureDetail.RESPONSE_DECODE,
            "response_status": ProviderFailureDetail.RESPONSE_STATUS,
            "stream": ProviderFailureDetail.STREAM,
        }[failure_phase]
        return _AttemptFailure(ProviderFailureReason.INVALID_RESPONSE, detail, status_value)
    if failure_phase == "http" or error_class in {
        "authentication",
        "overloaded",
        "provider",
        "rate_limited",
    }:
        raise RetryReportError("retry report transport failure has HTTP-only classification")
    if error_class == "cancelled":
        return _AttemptFailure(
            ProviderFailureReason.CANCELLED, ProviderFailureDetail.CANCELLED, None
        )
    if error_class == "timeout":
        return _AttemptFailure(ProviderFailureReason.TIMEOUT, ProviderFailureDetail.TIMEOUT, None)
    if error_class == "network":
        if failure_phase in {"response_decode", "response_status", "stream"}:
            detail = {
                "response_decode": ProviderFailureDetail.RESPONSE_DECODE,
                "response_status": ProviderFailureDetail.RESPONSE_STATUS,
                "stream": ProviderFailureDetail.STREAM,
            }[failure_phase]
            return _AttemptFailure(ProviderFailureReason.INVALID_RESPONSE, detail, None)
        return _AttemptFailure(ProviderFailureReason.NETWORK, ProviderFailureDetail.NETWORK, None)
    return _AttemptFailure(ProviderFailureReason.UNKNOWN, ProviderFailureDetail.UNKNOWN, None)


def _request_failure(request: Mapping[str, Any]) -> _AttemptFailure | None:
    """Validate one logical request and project only its terminal failure."""

    outcome = request.get("outcome")
    if outcome not in REQUEST_OUTCOMES:
        raise RetryReportError("retry report request outcome is invalid")
    attempts = request.get("attempts")
    if not isinstance(attempts, list) or not 0 < len(attempts) <= MAX_ATTEMPTS_PER_REQUEST:
        raise RetryReportError("retry report request attempts are invalid")
    failures: list[_AttemptFailure | None] = []
    for index, attempt in enumerate(attempts, start=1):
        if (
            not isinstance(attempt, dict)
            or type(attempt.get("attempt")) is not int
            or attempt.get("attempt") != index
        ):
            raise RetryReportError("retry report attempt order is invalid")
        failures.append(_attempt_failure(attempt))
    if outcome == "succeeded":
        if len(attempts) < 2 or any(failure is not None for failure in failures):
            raise RetryReportError("retry report succeeded request is inconsistent")
        return None
    if outcome == "recovered":
        if failures[-1] is not None or not any(failure is not None for failure in failures[:-1]):
            raise RetryReportError("retry report recovered request is inconsistent")
        return None
    if outcome == "cancelled":
        return _AttemptFailure(
            ProviderFailureReason.CANCELLED, ProviderFailureDetail.CANCELLED, None
        )
    if failures[-1] is None:
        raise RetryReportError("retry report failed request ends in success")
    return failures[-1]


def parse_retry_report_projection(result: object) -> ProviderFailureProjection | None:
    """Validate retry-report v1 and return one closed numeric failure projection."""

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
        maximum = (
            MAX_RETRY_REQUESTS * (MAX_ATTEMPTS_PER_REQUEST - 1)
            if field == "total_retries"
            else MAX_RETRY_REQUESTS
        )
        if _bounded_count(report.get(field), field, maximum=maximum) != expected:
            raise RetryReportError(f"OCR retry report {field} is inconsistent")

    failures: list[_AttemptFailure] = []
    for request in requests:
        if not isinstance(request, dict):
            raise RetryReportError("OCR retry report request is invalid")
        failure = _request_failure(request)
        if failure is not None:
            failures.append(failure)
    if not failures:
        return None
    reason_counts = Counter(failure.reason for failure in failures)
    reason = next(iter(reason_counts)) if len(reason_counts) == 1 else ProviderFailureReason.MIXED
    detail_counts = Counter(failure.detail for failure in failures)
    statuses = {failure.status_code for failure in failures}
    shared_status = next(iter(statuses)) if len(statuses) == 1 else None
    return ProviderFailureProjection(
        reason=reason,
        details=tuple(sorted(detail_counts.items(), key=lambda item: item[0].value)),
        status_code=shared_status,
        failed_requests=expected_counts["failed_requests"],
        cancelled_requests=expected_counts["cancelled_requests"],
        retried_requests=expected_counts["retried_requests"],
        total_retries=expected_counts["total_retries"],
        recovered_requests=expected_counts["recovered_requests"],
    )


def parse_retry_report_failure(result: object) -> ProviderFailureReason | None:
    """Validate retry-report v1 and return one closed terminal failure reason."""

    projection = parse_retry_report_projection(result)
    return projection.reason if projection is not None else None


def render_provider_diagnostics(projection: ProviderFailureProjection) -> str:
    """Render one bounded deterministic CI line from a validated projection."""

    fields = [f"summary={projection.reason.value}"]
    if len(projection.details) == 1:
        fields.append(f"detail={projection.details[0][0].value}")
    else:
        details = ",".join(f"{detail.value}:{count}" for detail, count in projection.details)
        fields.append(f"details={details}")
    if projection.status_code is not None:
        fields.append(f"status={projection.status_code}")
    for name in (
        "failed_requests",
        "cancelled_requests",
        "retried_requests",
        "total_retries",
        "recovered_requests",
    ):
        value = getattr(projection, name)
        if value:
            fields.append(f"{name}={value}")
    return "OCR provider diagnostics: " + " ".join(fields)


def provider_failure_projection(result: object) -> ProviderFailureProjection | None:
    """Return closed diagnostics, degrading malformed private data to unavailable."""

    try:
        return parse_retry_report_projection(result)
    except RetryReportError:
        return None


def provider_failure_reason(result: object) -> ProviderFailureReason | None:
    """Return a closed reason, degrading malformed private diagnostics to unavailable."""

    projection = provider_failure_projection(result)
    return projection.reason if projection is not None else None
