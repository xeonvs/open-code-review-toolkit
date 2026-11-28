"""Aggregate observed GitLab process events and balanced adoption cohorts."""

import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from .common import (
    DAY,
    WINDOW,
    attempt_created_at,
    completion,
    count,
    data,
    distribution,
    duration,
    quantile,
    ratio,
    revision_rows,
    rows,
    terminal,
    timestamp,
)

_PROCESS_COUNTS = (
    "assigned_reviewer_count",
    "involved_reviewer_count",
    "assigned_involved_reviewer_count",
    "approval_count",
    "required_approvals",
    "approvals_from_assigned_reviewers",
    "human_comments",
    "human_replies",
    "code_discussions",
    "resolutions",
    "diff_versions",
    "assigned_review_threads",
    "assigned_reviewer_comments",
    "assigned_reviewer_resolutions",
    "author_replies_to_assigned_review",
    "author_resolutions_of_assigned_review",
    "author_reactions_to_assigned_review",
    "feedback_cycles",
    "observed_human_participant_count",
    "changed_lines",
    "changed_files",
    "commit_count",
    "ocr_repeated_publications",
)
_PROCESS_FLAGS = (
    "assigned_reviewer_returned_after_author_action",
    "author_responded_before_post_review_commit",
    "assigned_reviewer_returned_after_change",
)
_STAGES = {
    "opening_to_ready": ("created_at", "ready_at"),
    "opening_to_assignment": ("created_at", "first_reviewer_assignment_at"),
    "opening_to_first_human_action": ("created_at", "first_human_action_at"),
    "assignment_to_first_action": (
        "first_reviewer_assignment_at",
        "first_assigned_reviewer_action_at",
    ),
    "opening_to_assigned_action": ("created_at", "first_assigned_reviewer_action_at"),
    "opening_to_first_approval": ("created_at", "first_approval_at"),
    "assigned_action_to_merge": ("first_assigned_reviewer_action_at", "merged_at"),
    "opening_to_merge": ("created_at", "merged_at"),
    "opening_to_close": ("created_at", "closed_at"),
}
_ROLES = ("author", "mr_author", "assigned_reviewer", "other", "other_participant", "unknown")


def revision_flow(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for record in records:
        revisions = revision_rows(record)
        comparable = [row for row in revisions if row.get("comparable") is True]
        changed = [row for row in comparable if (count(row.get("non_merge_commits")) or 0) > 0]
        tails = (
            [row for row in comparable if row.get("final_tail") is True]
            if data(record.get("completeness")).get("revisions") in ("complete", "partial")
            else []
        )
        counts["intervals"] += len(revisions)
        counts["comparable_intervals"] += len(comparable)
        counts["non_merge_commits"] += sum(
            count(row.get("non_merge_commits")) or 0 for row in comparable
        )
        for row in comparable:
            commits, ordinary = count(row.get("commits")), count(row.get("non_merge_commits"))
            counts["merge_commits"] += (
                commits - ordinary
                if commits is not None and ordinary is not None and commits >= ordinary
                else count(row.get("merge_commits")) or 0
            )
        counts["mrs_with_post_review_changes"] += bool(changed)
        counts["mrs_with_followup_review"] += any(
            row.get("followup_review") is True for row in changed
        )
        counts["mrs_with_fresh_final_revision"] += any(
            count(row.get("commits")) == 0 for row in tails
        )
        complete = bool(tails) and all(
            row.get("comparable") is True and count(row.get("non_merge_commits")) == 0
            for row in revisions
        )
        counts["mrs_with_no_observed_change"] += complete
        counts["mrs_with_unknown_change"] += not (complete or changed)
    return dict(counts)


def _band(value: int, limits: tuple[int, ...], labels: tuple[str, ...]) -> str:
    return labels[sum(value >= limit for limit in limits)]


def process_summary(
    records: list[dict[str, Any]], horizon: datetime, *, captured_at: datetime | None
) -> dict[str, Any]:
    observed = [{**record, **data(record.get("process"))} for record in records]
    attempts = [value for record in records if (value := completion(record, horizon)) is not None]
    counts, fields = Counter(), Counter()
    flag_counts, flag_fields = Counter(), Counter()
    roles: dict[str, Counter[str]] = defaultdict(Counter)
    size: dict[str, Counter[str]] = defaultdict(Counter)
    intensity: dict[str, Counter[str]] = defaultdict(Counter)
    time_to_merge: Counter[str] = Counter()
    inactivity: Counter[str] = Counter()
    reactions = []
    for record, row in zip(records, observed, strict=True):
        sources = data(record.get("completeness"))
        reactions_comparable = (
            row.get("human_reactions_comparable") is True
            and sources.get("reactions") == "complete"
            and count(row.get("author_reactions_to_assigned_review")) is not None
        )
        if reactions_comparable:
            reactions.append(row)
        for field in _PROCESS_COUNTS:
            if field == "author_reactions_to_assigned_review" and not reactions_comparable:
                continue
            value = count(row.get(field))
            if value is not None:
                counts[field] += value
                fields[field] += 1
        review_author_action = any(
            (count(row.get(field)) or 0) > 0
            for field in (
                "author_replies_to_assigned_review",
                "author_resolutions_of_assigned_review",
            )
        )
        commits_after_review = any(
            (count(data(row.get("non_merge_commits_after_review_by_role")).get(role)) or 0) > 0
            for role in _ROLES
        )
        opportunities = (review_author_action, commits_after_review, commits_after_review)
        for field, opportunity in zip(_PROCESS_FLAGS, opportunities, strict=True):
            if type(value := row.get(field)) is bool and (value or opportunity):
                flag_counts[field] += value
                flag_fields[field] += 1
        if row.get("commit_authorship_comparable") is True:
            for field in ("non_merge_commits_by_role", "non_merge_commits_after_review_by_role"):
                roles[field].update(
                    {key: count(data(row.get(field)).get(key)) or 0 for key in _ROLES}
                )
        lines, files = count(row.get("changed_lines")), count(row.get("changed_files"))
        for field, value, limits in (("lines", lines, (101, 501)), ("files", files, (4, 11))):
            if value is not None:
                size[field][_band(value, limits, ("small", "medium", "large"))] += 1
        involved = count(row.get("assigned_involved_reviewer_count"))
        if involved is not None:
            intensity["assigned_reviewer_participation"][
                _band(involved, (1, 2), ("none", "one", "multiple"))
            ] += 1
        elapsed = (
            duration(row.get("created_at"), row.get("merged_at"))
            if row.get("state") == "merged"
            else None
        )
        if elapsed is not None:
            time_to_merge[
                _band(
                    int(elapsed // DAY.total_seconds()),
                    (1, 4, 8, 15),
                    ("same_day", "days_1_3", "days_4_7", "days_8_14", "days_15_plus"),
                )
            ] += 1
        if row.get("state") in {"opened", "open"}:
            activity = timestamp(row.get("latest_meaningful_activity_at"))
            if (
                activity is None
                or captured_at is None
                or activity > captured_at
                or sources.get("discussions") != "complete"
                or sources.get("versions") != "complete"
            ):
                inactivity["unknown"] += 1
            else:
                inactivity[
                    _band(
                        (captured_at - activity).days,
                        (7, 14, 30),
                        ("under_7_days", "days_7_13", "days_14_29", "days_30_plus"),
                    )
                ] += 1
    return {
        "merge_requests": len(records),
        "merged_within_14_days": ratio(sum(attempts), len(attempts)),
        "calendar_durations": {
            name: distribution(duration(row.get(first), row.get(last)) for row in observed)
            for name, (first, last) in _STAGES.items()
        },
        "process_counts": dict(counts),
        "process_field_coverage": {
            field: ratio(fields[field], len(records)) for field in _PROCESS_COUNTS
        },
        "feedback_evidence": {
            field: ratio(flag_counts[field], flag_fields[field]) for field in _PROCESS_FLAGS
        },
        "time_to_merge_bands": dict(time_to_merge),
        "open_inactivity": dict(inactivity),
        "change_size": {field: dict(values) for field, values in size.items()},
        "reviewer_intensity": {field: dict(values) for field, values in intensity.items()},
        "commit_authorship_coverage": ratio(
            sum(row.get("commit_authorship_comparable") is True for row in observed), len(records)
        ),
        "non_merge_commit_roles": {field: dict(values) for field, values in roles.items()},
        "author_reaction_coverage": ratio(len(reactions), len(records)),
        "author_reactions_to_assigned_review": ratio(
            sum(
                (count(row.get("author_reactions_to_assigned_review")) or 0) > 0
                for row in reactions
            ),
            len(reactions),
        ),
        "revision_flow": revision_flow(records),
    }


def _effect(
    phases: dict[int, tuple[list[bool], list[bool]]], labels: dict[int, str]
) -> dict[str, Any]:
    summary = {
        project_id: (sum(before), len(before), sum(after), len(after))
        for project_id, (before, after) in phases.items()
        if before and after
    }
    before_hits, before_n, after_hits, after_n = (
        map(sum, zip(*summary.values(), strict=True)) if summary else (0, 0, 0, 0)
    )
    effect: dict[str, Any] = {
        "before": ratio(before_hits, before_n),
        "after": ratio(after_hits, after_n),
        "pooled_delta": None,
        "project_equal_delta": None,
        "confidence_interval_95": {"low": None, "high": None},
        "leave_one_project_out": [],
    }
    if not summary:
        return effect
    rates = [(b / bn, a / an, bn, an) for b, bn, a, an in summary.values()]
    effect["pooled_delta"] = after_hits / after_n - before_hits / before_n
    effect["project_equal_delta"] = sum(a - b for b, a, _, _ in rates) / len(rates)
    # A stratified binary bootstrap reduces each stratum to one binomial draw.
    rng = random.Random(20260901)
    draws = sorted(
        sum(rng.binomialvariate(an, a) for _, a, _, an in rates) / after_n
        - sum(rng.binomialvariate(bn, b) for b, _, bn, _ in rates) / before_n
        for _ in range(4000)
    )
    effect["confidence_interval_95"] = {
        "low": quantile(draws, 0.025),
        "high": quantile(draws, 0.975),
    }
    effect["leave_one_project_out"] = [
        {
            "project": labels[project_id],
            "pooled_delta": (after_hits - a) / (after_n - an) - (before_hits - b) / (before_n - bn),
        }
        for project_id, (b, bn, a, an) in summary.items()
        if before_n > bn and after_n > an
    ]
    return effect


def adoption_comparison(
    projects: dict[int, list[dict[str, Any]]],
    labels: dict[int, str],
    horizon: datetime,
    *,
    captured_at: datetime | None,
) -> dict[str, Any]:
    cohorts = []
    metrics: dict[int, tuple[list[bool], list[bool]]] = {}
    size_metrics: dict[str, dict[int, tuple[list[bool], list[bool]]]] = defaultdict(dict)
    excluded: Counter[str] = Counter()
    for project_id, project in labels.items():
        records = projects.get(project_id, [])
        adopted = min(
            (
                observed
                for record in records
                for run in rows(record.get("runs"))
                if (observed := attempt_created_at(run)) is not None
            ),
            default=None,
        )
        if adopted is None or adopted > horizon:
            continue
        before, after = [], []
        ordered = sorted(
            records,
            key=lambda row: (
                timestamp(row.get("created_at")) or datetime.min.replace(tzinfo=horizon.tzinfo)
            ),
        )
        for record in ordered:
            opened, finished = timestamp(record.get("created_at")), timestamp(terminal(record))
            process = data(record.get("process"))
            if opened is None or opened > horizon:
                continue
            cutoff = adopted if opened < adopted else horizon
            sources = data(record.get("completeness"))
            if opened < adopted and (finished is None or finished >= adopted):
                excluded["transitional"] += 1
            elif (
                process.get("terminal_actor_is_author") is True
                and count(process.get("involved_reviewer_count")) == 0
                and sources.get("discussions") == sources.get("approvals") == "complete"
            ):
                excluded["self_service"] += 1
            elif cutoff - opened < WINDOW or completion(record, cutoff) is None:
                excluded["unobserved_completion_window"] += 1
            else:
                (before if opened < adopted else after).append(record)
        size = min(len(before), len(after))
        if size < 10:
            excluded["insufficient_projects"] += 1
            continue
        before, after = before[-size:], after[:size]
        phases = (before, after)
        horizons = (adopted, horizon)
        values = [
            [value for record in items if (value := completion(record, end)) is not None]
            for items, end in zip(phases, horizons, strict=True)
        ]
        metrics[project_id] = (values[0], values[1])
        for band, limits in (
            ("small", (0, 101)),
            ("medium", (101, 501)),
            ("large", (501, math.inf)),
        ):
            matched = [
                [
                    record
                    for record in items
                    if isinstance(
                        lines := count(data(record.get("process")).get("changed_lines")), int
                    )
                    and limits[0] <= lines < limits[1]
                ]
                for items in phases
            ]
            matched_size = min(map(len, matched))
            if matched_size:
                a, b = matched[0][-matched_size:], matched[1][:matched_size]
                matches = [
                    [value for record in items if (value := completion(record, end)) is not None]
                    for items, end in zip((a, b), horizons, strict=True)
                ]
                size_metrics[band][project_id] = (matches[0], matches[1])
        cohorts.append(
            {
                "project": project,
                "adoption_at": adopted.isoformat(),
                "sample_per_period": size,
                "before": process_summary(before, adopted, captured_at=captured_at),
                "after": process_summary(after, horizon, captured_at=captured_at),
            }
        )
    return {
        "eligible_projects": len(cohorts),
        "exclusions": dict(excluded),
        "projects": cohorts,
        "effect": _effect(metrics, labels),
        "by_change_size": {
            band: _effect(eligible, labels)
            for band, values in size_metrics.items()
            if len(
                eligible := {project: phases for project, phases in values.items() if all(phases)}
            )
            >= 2
            and min(sum(len(values[phase]) for values in eligible.values()) for phase in (0, 1))
            >= 20
        },
    }
