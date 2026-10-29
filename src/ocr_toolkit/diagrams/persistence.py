"""Pure exact diagram receipt grammar; acquisition/admission stay outside it."""

from __future__ import annotations

from typing import cast

from ocr_toolkit.diagrams.contracts import (
    MAX_SUBMISSIONS,
    DiagramError,
    DiagramReason,
    DiagramResult,
    DiagramState,
    diagram_requested,
    parse_diagram_mode,
    parse_submission,
    submission_payload,
)
from ocr_toolkit.ocr_result import MAX_TOOLKIT_MCP_USAGE_COUNT
from ocr_toolkit.review_range import ReviewRange

DIAGRAM_RECEIPT_SCHEMA = "ocr.review-diagram/v1"


def diagram_payload(result: DiagramResult) -> dict[str, object]:
    """Persist only closed state, reconciled count and a normalized candidate."""

    return {
        "schema": DIAGRAM_RECEIPT_SCHEMA,
        "mode": result.mode,
        "state": result.state,
        "reason": result.reason,
        "calls": result.calls,
        "failed_calls": result.failed_calls,
        "submission": submission_payload(result.submission)
        if result.submission is not None
        else None,
    }


def parse_diagram_payload(
    value: object, *, review_range: ReviewRange | None, local: bool = False
) -> DiagramResult:
    """Reject impossible state/candidate/count combinations atomically on read."""

    if (
        not isinstance(value, dict)
        or set(value)
        != {"schema", "mode", "state", "reason", "calls", "failed_calls", "submission"}
        or value["schema"] != DIAGRAM_RECEIPT_SCHEMA
    ):
        raise DiagramError("persisted diagram shape is invalid")
    if not isinstance(value["mode"], str):
        raise DiagramError("persisted diagram mode is invalid")
    mode = parse_diagram_mode(value["mode"], local=local)
    state, reason, calls = value["state"], value["reason"], value["calls"]
    failed_calls = value["failed_calls"]
    if (
        state
        not in (
            "disabled",
            "not-applicable",
            "unsupported",
            "generated",
            "not-generated",
            "omitted-invalid",
        )
        or reason
        not in ("none", "invalid", "conflict", "budget", "unavailable", "range", "reference", "dlp")
        or type(calls) is not int
        or not 0 <= calls <= MAX_TOOLKIT_MCP_USAGE_COUNT
        or type(failed_calls) is not int
        or not 0 <= failed_calls <= calls
        or (failed_calls > 0 and state != "omitted-invalid")
        or (not diagram_requested(mode, local=local)) != (state == "disabled")
        or (state == "omitted-invalid") != (reason != "none")
        or (state in ("disabled", "unsupported", "not-generated") and calls != 0)
        or (state in ("generated", "not-applicable") and not 1 <= calls <= MAX_SUBMISSIONS)
        or (state in ("generated", "not-applicable") and review_range is None)
        or (state != "generated" and value["submission"] is not None)
    ):
        raise DiagramError("persisted diagram state is inconsistent")
    submission = None
    if state == "generated":
        assert review_range is not None
        submission = parse_submission(value["submission"], expected_range=review_range)
        if submission.diagram is None:
            raise DiagramError("generated diagram is absent")
        if submission_payload(submission) != value["submission"]:
            raise DiagramError("persisted diagram is not canonical")
    return DiagramResult(
        mode,
        cast(DiagramState, state),
        cast(DiagramReason, reason),
        submission,
        calls,
        failed_calls,
    )
