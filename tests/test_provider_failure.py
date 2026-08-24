"""Closed projection tests for private OCR provider retry diagnostics."""

from __future__ import annotations

from typing import Any

import pytest

from ocr_toolkit.provider_failure import (
    MAX_ATTEMPTS_PER_REQUEST,
    ProviderFailureReason,
    RetryReportError,
    parse_retry_report_failure,
    provider_failure_reason,
)


def _error_attempt(*, status: int, error_class: str, phase: str, number: int = 1) -> dict[str, Any]:
    """Return one v1 error attempt with hostile additive diagnostics."""

    return {
        "attempt": number,
        "outcome": "error",
        "error_class": error_class,
        "failure_phase": phase,
        "status_code": status,
        "request_id": "private-request-id",
        "provider_body": "Authorization: Bearer private-token",
    }


def _success_attempt(number: int) -> dict[str, Any]:
    """Return one v1 successful attempt."""

    return {"attempt": number, "outcome": "success", "status_code": 200}


def _request(outcome: str, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """Return one logical request with raw identity fields the parser must ignore."""

    return {
        "logical_request_id": "private-logical-id",
        "provider": "private-provider",
        "model": "private-model",
        "file_path": "/private/repository/file.py",
        "task_type": "main_task",
        "request_no": 1,
        "outcome": outcome,
        "attempts": attempts,
    }


def _result(requests: list[dict[str, Any]], *, total_requests: int | None = None) -> dict[str, Any]:
    """Return a counter-consistent retry-report result."""

    return {
        "comments": [{"content": "private finding must not be consumed"}],
        "retry_report": {
            "schema_version": "ocr.llm-retry-report/v1",
            "total_requests": len(requests) if total_requests is None else total_requests,
            "retried_requests": sum(len(request["attempts"]) > 1 for request in requests),
            "total_retries": sum(len(request["attempts"]) - 1 for request in requests),
            "recovered_requests": sum(request["outcome"] == "recovered" for request in requests),
            "failed_requests": sum(request["outcome"] == "failed" for request in requests),
            "cancelled_requests": sum(request["outcome"] == "cancelled" for request in requests),
            "requests": requests,
            "provider_private_extension": "private-response-body",
        },
    }


@pytest.mark.parametrize(
    ("status", "error_class", "expected"),
    [
        (400, "provider", ProviderFailureReason.REQUEST_REJECTED),
        (401, "authentication", ProviderFailureReason.AUTHENTICATION),
        (402, "provider", ProviderFailureReason.RATE_OR_SPENDING_LIMIT),
        (403, "authentication", ProviderFailureReason.AUTHORIZATION),
        (404, "provider", ProviderFailureReason.ENDPOINT_OR_MODEL_NOT_FOUND),
        (408, "timeout", ProviderFailureReason.TIMEOUT),
        (409, "provider", ProviderFailureReason.REQUEST_REJECTED),
        (413, "provider", ProviderFailureReason.REQUEST_REJECTED),
        (422, "provider", ProviderFailureReason.REQUEST_REJECTED),
        (429, "rate_limited", ProviderFailureReason.RATE_OR_SPENDING_LIMIT),
        (500, "provider", ProviderFailureReason.PROVIDER_UNAVAILABLE),
        (503, "provider", ProviderFailureReason.PROVIDER_UNAVAILABLE),
        (504, "timeout", ProviderFailureReason.TIMEOUT),
        (529, "overloaded", ProviderFailureReason.OVERLOADED),
    ],
)
def test_http_status_matrix_maps_only_validated_attempt_fields(
    status: int, error_class: str, expected: ProviderFailureReason
) -> None:
    """Map the complete required HTTP matrix without reading provider text."""

    result = _result(
        [_request("failed", [_error_attempt(status=status, error_class=error_class, phase="http")])]
    )

    assert parse_retry_report_failure(result) is expected


@pytest.mark.parametrize(
    ("attempt", "expected"),
    [
        (
            _error_attempt(status=0, error_class="timeout", phase="context"),
            ProviderFailureReason.TIMEOUT,
        ),
        (
            _error_attempt(status=0, error_class="network", phase="transport"),
            ProviderFailureReason.NETWORK,
        ),
        (
            _error_attempt(status=200, error_class="network", phase="response_decode"),
            ProviderFailureReason.INVALID_RESPONSE,
        ),
        (
            _error_attempt(status=200, error_class="provider", phase="response_status"),
            ProviderFailureReason.INVALID_RESPONSE,
        ),
        (
            _error_attempt(status=0, error_class="unknown", phase="transport"),
            ProviderFailureReason.UNKNOWN,
        ),
    ],
)
def test_non_http_failure_matrix_uses_class_and_phase(
    attempt: dict[str, Any], expected: ProviderFailureReason
) -> None:
    """Classify transport and response failures from closed fields only."""

    assert parse_retry_report_failure(_result([_request("failed", [attempt])])) is expected


def test_cancelled_and_mixed_terminal_outcomes_are_closed() -> None:
    """Prefer terminal cancellation and collapse heterogeneous failures to mixed."""

    cancelled = _request(
        "cancelled",
        [_error_attempt(status=0, error_class="cancelled", phase="context")],
    )
    unavailable = _request(
        "failed",
        [_error_attempt(status=503, error_class="provider", phase="http")],
    )

    assert parse_retry_report_failure(_result([cancelled])) is ProviderFailureReason.CANCELLED
    assert (
        parse_retry_report_failure(_result([cancelled, unavailable])) is ProviderFailureReason.MIXED
    )


def test_recovered_only_report_does_not_create_a_failure_reason() -> None:
    """Keep successful recovery private and outside failure-note semantics."""

    recovered = _request(
        "recovered",
        [
            _error_attempt(status=429, error_class="rate_limited", phase="http"),
            _success_attempt(2),
        ],
    )

    assert parse_retry_report_failure(_result([recovered], total_requests=2)) is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report: report.update(schema_version="future"),
        lambda report: report.update(requests=[], total_requests=1, failed_requests=0),
        lambda report: report.update(failed_requests=2),
        lambda report: report["requests"][0]["attempts"][0].update(status_code=True),
        lambda report: report["requests"][0]["attempts"][0].update(error_class="future"),
        lambda report: report["requests"][0]["attempts"][0].update(
            error_class="provider", status_code=401
        ),
    ],
)
def test_malformed_or_impossible_reports_degrade_to_generic(
    mutate: Any,
) -> None:
    """Reject unsupported and internally contradictory private diagnostics."""

    result = _result(
        [
            _request(
                "failed",
                [_error_attempt(status=429, error_class="rate_limited", phase="http")],
            )
        ]
    )
    mutate(result["retry_report"])

    with pytest.raises(RetryReportError):
        parse_retry_report_failure(result)
    assert provider_failure_reason(result) is None


def test_attempt_and_request_bounds_fail_before_projection() -> None:
    """Reject per-request and aggregate lists beyond their fixed parser bounds."""

    attempts = [
        _error_attempt(status=503, error_class="provider", phase="http", number=index)
        for index in range(1, MAX_ATTEMPTS_PER_REQUEST + 2)
    ]
    result = _result([_request("failed", attempts)])

    with pytest.raises(RetryReportError, match="attempts"):
        parse_retry_report_failure(result)


def test_raw_provider_identity_and_payload_fields_do_not_affect_reason() -> None:
    """Ignore additive identity and payload data even when it contains secrets."""

    result = _result(
        [
            _request(
                "failed",
                [_error_attempt(status=404, error_class="provider", phase="http")],
            )
        ]
    )

    reason = parse_retry_report_failure(result)

    assert reason is ProviderFailureReason.ENDPOINT_OR_MODEL_NOT_FOUND
    assert "private" not in reason.value
