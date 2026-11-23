"""Aggregate technical attempts and distinguish them from delivered model results."""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from ocr_toolkit.telemetry.collection.attempts import FAILURE_REASONS, JOB_STATES
from ocr_toolkit.telemetry.publications.grammar import (
    OCR_PRE_MODEL_STATUSES,
    OCR_PREVIEW_STATUSES,
    model_publication,
)

from .common import (
    closed,
    data,
    distribution,
    duration,
    ratio,
    review_rows,
    rows,
    sum_fields,
    timestamp,
)

SUCCESS_OUTCOMES = frozenset(
    {"complete", "complete_with_warnings", "complete_publication_filtered"}
)
PARTIAL_OUTCOMES = frozenset(
    {"incomplete", "partial", "partial_publication_filtered", "budget_exceeded"}
)
OUTCOMES = SUCCESS_OUTCOMES | frozenset(
    {
        "partial",
        "incomplete",
        "partial_publication_filtered",
        "budget_exceeded",
        "failed",
        "failed_result",
        "skipped",
        "provider_failure",
        "review_rejected",
        "setup_pending",
        "setup_failed",
        "preview_rejected",
        "preview_unclassified",
        "gitlink_no_reviewable_files",
        "gitlink_projection_unqualified",
        "evidence_budget_exceeded",
        "terminal_merged",
        "terminal_closed",
        "merged",
        "closed",
        "no_supported_files",
        "setup_unavailable",
        "background_character_limit",
        "background_file_size_limit",
        "unclassified_preview_diagnostics",
        *OCR_PRE_MODEL_STATUSES.values(),
        *(outcome for outcome, _ in OCR_PREVIEW_STATUSES.values()),
    }
)
_FAILURES = frozenset({"failed", "canceled", "unknown"})
_NO_PUBLICATION_TIME = datetime.min.replace(tzinfo=UTC)


def adjusted_status(run: dict[str, Any]) -> str:
    status = job_status(run)
    return "unknown" if status == "success" and run.get("success") is False else status


def job_status(run: dict[str, Any]) -> str:
    return closed(run.get("status"), JOB_STATES)


def supported_review(
    record: dict[str, Any], outcomes: frozenset[str] = SUCCESS_OUTCOMES | PARTIAL_OUTCOMES
) -> bool:
    return any(
        model_publication(row) and closed(row.get("outcome"), outcomes) in outcomes
        for row in review_rows(record)
    )


def _reviewed_revisions(record: dict[str, Any]) -> int:
    if "checkpoints" in record:
        return len(rows(record.get("checkpoints")))
    successful = [run for run in rows(record.get("runs")) if adjusted_status(run) == "success"]
    return len(
        {
            revision
            for run in successful
            if isinstance(revision := run.get("revision", run.get("sha")), str) and revision
        }
    )


def delivery_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = [run for record in records for run in rows(record.get("runs"))]
    statuses = Counter(job_status(run) for run in attempts)
    starts = [
        run
        for run in attempts
        if run.get("started") is True or timestamp(run.get("started_at")) is not None
    ]
    successful = [run for run in attempts if adjusted_status(run) == "success"]
    failures = [run for run in attempts if job_status(run) in _FAILURES]
    distinct_counts = [_reviewed_revisions(record) for record in records]
    latest = [
        max(
            review_rows(row),
            key=lambda item: (
                timestamp(item.get("updated_at"))
                or timestamp(item.get("created_at"))
                or _NO_PUBLICATION_TIME
            ),
            default={},
        )
        for row in records
    ]
    d_count, r_count = Counter(), Counter()
    reaction_snapshots = 0
    for row in records:
        discussions = rows(row.get("discussions"))
        for discussion in discussions:
            sum_fields(
                d_count,
                discussion,
                (
                    "bot_note_count",
                    "resolvable_count",
                    "resolved_count",
                    "inline_count",
                    "general_count",
                ),
            )
            for field in ("has_non_bot_reply", "has_author_reply", "resolved_by_author"):
                d_count[field] += discussion.get(field) is True
        reactions = data(row.get("reactions"))
        if data(row.get("completeness")).get("reactions") == "complete":
            reaction_snapshots += 1
            sum_fields(
                r_count,
                reactions,
                (
                    "author_reactions",
                    "reacted_bot_notes",
                    "reactions_from_others",
                    "author_reactions_to_assigned_review",
                ),
            )
    return {
        "attempts": len(attempts),
        "started_attempts": len(starts),
        "statuses": dict(statuses),
        "successful_attempts": len(successful),
        "gitlab_successful_attempts": statuses["success"],
        "pre_model_attempts": sum(run.get("pre_model_stop") is True for run in attempts),
        "terminal_pre_model_attempts": sum(
            run.get("terminal_pre_model") is True for run in attempts
        ),
        "mrs_with_attempts": sum(bool(rows(row.get("runs"))) for row in records),
        "mrs_with_successful_attempt": sum(
            any(adjusted_status(run) == "success" for run in rows(row.get("runs")))
            for row in records
        ),
        "mrs_with_failed_attempt": sum(
            any(job_status(run) in _FAILURES for run in rows(row.get("runs"))) for row in records
        ),
        "mrs_with_reviewed_revision": sum(number > 0 for number in distinct_counts),
        "reviewed_revisions": sum(distinct_counts),
        "attempt_kinds": dict(
            Counter(
                closed(
                    run.get("attempt_kind"),
                    (
                        "first_for_revision",
                        "retry_same_pipeline",
                        "rerun_same_revision",
                        "retry_in_pipeline",
                        "same_revision_new_pipeline",
                        "repeat_same_pipeline",
                        "repeat_new_pipeline",
                    ),
                )
                for run in attempts
            )
        ),
        "failed_created_attempts": ratio(len(failures), len(attempts)),
        "failed_started_attempts": ratio(
            sum(job_status(run) in _FAILURES for run in starts), len(starts)
        ),
        "started_field_coverage": ratio(
            sum(
                type(run.get("started")) is bool or timestamp(run.get("started_at")) is not None
                for run in attempts
            ),
            len(attempts),
        ),
        "allow_failure_coverage": ratio(
            sum(type(run.get("allow_failure")) is bool for run in attempts), len(attempts)
        ),
        "advisory_attempts": sum(run.get("allow_failure") is True for run in attempts),
        "advisory_failed_attempts": sum(run.get("allow_failure") is True for run in failures),
        "failure_reasons": dict(
            Counter(closed(run.get("failure_reason"), FAILURE_REASONS) for run in failures)
        ),
        "mrs_with_delivered_review": sum(supported_review(row) for row in records),
        "mrs_with_successful_model_delivery": sum(
            supported_review(row, SUCCESS_OUTCOMES) for row in records
        ),
        "mrs_with_partial_model_delivery": sum(
            supported_review(row, PARTIAL_OUTCOMES) for row in records
        ),
        "latest_observed_outcomes": dict(
            Counter(closed(row.get("outcome"), OUTCOMES) for row in latest if row)
        ),
        "mrs_with_successful_job_and_latest_failed_result": sum(
            closed(review.get("outcome"), OUTCOMES)
            in {"provider_failure", "review_rejected", "failed", "failed_result"}
            and any(job_status(run) == "success" for run in rows(record.get("runs")))
            for record, review in zip(records, latest, strict=True)
        ),
        "discussion_snapshot": dict(d_count),
        "reaction_snapshot": dict(r_count),
        "reaction_snapshot_coverage": ratio(reaction_snapshots, len(records)),
        "latency": {
            name: distribution(
                duration(
                    run.get(start),
                    run.get(end)
                    or (run.get("review_finished_at") if end == "finished_at" else None),
                )
                for run in successful
            )
            for name, start, end in (
                ("queue", "created_at", "started_at"),
                ("execution", "started_at", "finished_at"),
                ("pipeline_to_result", "pipeline_created_at", "finished_at"),
            )
        },
    }
