"""Establish the aggregate-only machine report from one offline snapshot."""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from ocr_toolkit.telemetry.collection.merge_request import MR_STATES
from ocr_toolkit.telemetry.links import INSTANCE_PATH, project_path, web_location
from ocr_toolkit.telemetry.rates import publication_model

from .common import DAY, data, review_rows, rows, timestamp
from .delivery import delivery_summary, supported_review
from .process import adoption_comparison, process_summary
from .technical import technical_summary
from .trends import calendar_trends


def _limits(scope: dict[str, Any], captured_at: datetime | None) -> tuple[datetime, datetime]:
    start, end = timestamp(scope.get("start")), timestamp(scope.get("end"))
    if start is None or end is None or end < start:
        raise ValueError("invalid telemetry scope")
    if isinstance(scope.get("end"), str) and len(scope["end"]) == 10:
        end = end + DAY - datetime.resolution
    return start, min(captured_at, end) if captured_at else end


def _labels(values: set[str], anonymize: bool, prefix: str) -> dict[str, str]:
    return {
        value: f"{prefix} {index:02d}" if anonymize else value
        for index, value in enumerate(sorted(values), 1)
    }


def _link(value: object, scope: dict[str, Any], saved_path: object, iid: object) -> str | None:
    """Use the collector's HTTPS authority grammar and require the exact saved MR path."""

    host, prefix = scope.get("host"), scope.get("base_path", "")
    if (
        isinstance(host, str)
        and host
        and isinstance(prefix, str)
        and INSTANCE_PATH.fullmatch(prefix)
        and (path := project_path(saved_path)) is not None
        and type(iid) is int
        and 0 < iid < 10**19
        and isinstance(value, str)
        and web_location(value) == (host, f"{prefix}/{path}/-/merge_requests/{iid}")
    ):
        return value
    return None


def _project_label(project: dict[str, Any]) -> str:
    path = project.get("path") or project.get("name")
    if not isinstance(path, str) or not path:
        raise ValueError("missing project label")
    return path


def aggregate_report(
    snapshot: dict[str, Any],
    *,
    anonymize: bool,
    costs: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scope = data(snapshot.get("scope"))
    captured_at = timestamp(scope.get("updated_at", scope.get("observed_at")))
    start, horizon = _limits(scope, captured_at)
    projects = sorted(
        rows(snapshot.get("projects")), key=lambda row: (_project_label(row), row["id"])
    )
    records = rows(snapshot.get("records"))
    project_model_observed_at: dict[int, datetime] = {}
    project_models: dict[int, str] = {}
    if costs:
        for project in projects:
            model = project.get("cost_model")
            observed_at = timestamp(project.get("cost_model_observed_at"))
            if isinstance(model, str) and model.strip() and observed_at is not None:
                project_models[project["id"]] = model
                project_model_observed_at[project["id"]] = observed_at
    by_project: dict[int, list[dict[str, Any]]] = defaultdict(list)
    reviews: list[dict[str, Any]] = []
    project_model_hints: list[str | None] = []
    for record in records:
        project_id = record["project_id"]
        by_project[project_id].append(record)
        related_reviews = review_rows(record)
        reviews.extend(related_reviews)
        if costs:
            project_model_hints.extend([project_models.get(project_id)] * len(related_reviews))
    label_counts = Counter(_project_label(project) for project in projects)
    label_ordinals: Counter[str] = Counter()
    project_labels: dict[int, str] = {}
    for index, project in enumerate(projects, 1):
        name = _project_label(project)
        label_ordinals[name] += 1
        if anonymize:
            label = f"Project {index:02d}"
        elif label_counts[name] > 1:
            label = f"{name} ({label_ordinals[name]})"
        else:
            label = name
        project_labels[project["id"]] = label
    model_labels = _labels(
        {model for review in reviews if (model := publication_model(review)) is not None},
        anonymize,
        "Model",
    )
    prices = data(snapshot.get("prices")) if costs else {}
    project_rows = []
    details = []
    correlation: Counter[str] = Counter()
    completeness: dict[str, Counter[str]] = defaultdict(Counter)
    for project in projects:
        project_id = project["id"]
        label = project_labels[project_id]
        members = by_project[project_id]
        link_path = project.get("path") if label_counts[_project_label(project)] == 1 else None
        project_reviews = [review for row in members for review in review_rows(row)]
        technical = technical_summary(
            project_reviews,
            model_labels,
            prices=prices,
            costs=costs,
            project_model_hints=[project_models.get(project_id)] * len(project_reviews)
            if costs
            else None,
        )
        if costs:
            observed_at = project_model_observed_at.get(project_id)
            technical["cost"]["cost_model_observed_at"] = (
                observed_at.isoformat() if observed_at else None
            )
        project_rows.append(
            {
                "project": label,
                "archived": project.get("archived") is True,
                "access": project.get("access")
                if project.get("access") in ("complete", "partial", "unavailable")
                else "unavailable",
                "merge_requests": len(members),
                "delivery": delivery_summary(members),
                "process": process_summary(members, horizon, captured_at=captured_at),
                "technical": technical,
            }
        )
        for row in members:
            if not anonymize:
                details.append(
                    {
                        "project": label,
                        "project_id": project_id,
                        "mr": row.get("iid"),
                        "url": _link(row.get("web_url"), scope, link_path, row.get("iid")),
                        "state": row.get("state") if row.get("state") in MR_STATES else "unknown",
                        "opened": row.get("created_at"),
                        "draft": row.get("draft") is True,
                        "attempts": len(rows(row.get("runs"))),
                        "reviewed_revisions": len(rows(row.get("checkpoints"))),
                        "delivered": supported_review(row),
                    }
                )
            for field in (
                "messages",
                "matched_messages",
                "unmatched_messages",
                "ambiguous_messages",
                "matched_technical_attempts",
            ):
                value = data(row.get("correlation")).get(field)
                if type(value) is int and 0 <= value < 2**63:
                    correlation[field] += value
            for field in (
                "pipelines",
                "discussions",
                "reactions",
                "process",
                "revisions",
                "approvals",
                "versions",
                "graphql",
                "commits",
            ):
                value = data(row.get("completeness")).get(field)
                completeness[field][
                    value if value in ("complete", "partial", "unavailable") else "unavailable"
                ] += 1
    authored_scope: dict[str, Any] = {
        "start": start.date().isoformat(),
        "end": scope.get("end"),
        "observed_through": horizon.isoformat(),
        "captured_at": captured_at.isoformat() if captured_at else None,
        "discovery": scope.get("discovery")
        if scope.get("discovery")
        in {"explicit", "activity", "bot_activity", "bot_contributions", "unknown"}
        else "unknown",
        "anonymized": anonymize,
    }
    if costs:
        price_time = timestamp(snapshot.get("prices_at"))
        authored_scope["prices_at"] = price_time.isoformat() if prices and price_time else None
    delivered = [record for record in records if supported_review(record)]
    undelivered = [record for record in records if not supported_review(record)]
    return {
        "schema_version": "ocr.toolkit.telemetry-report/v1",
        "scope": authored_scope,
        "overview": {
            "projects": len(projects),
            "archived_projects": sum(project.get("archived") is True for project in projects),
            "merge_requests": len(records),
            "projects_with_merge_requests": sum(bool(items) for items in by_project.values()),
            "projects_with_attempts": sum(
                any(rows(row.get("runs")) for row in items) for items in by_project.values()
            ),
            "projects_with_delivered_review": sum(
                any(supported_review(row) for row in items) for items in by_project.values()
            ),
            "lifecycle": {
                state: sum(record.get("state") == state for record in records)
                for state in sorted(MR_STATES)
            },
        },
        "delivery": {**delivery_summary(records), "pre_model_correlation": dict(correlation)},
        "technical": technical_summary(
            reviews,
            model_labels,
            prices=prices,
            costs=costs,
            project_model_hints=project_model_hints if costs else None,
        ),
        "process": {
            **process_summary(records, horizon, captured_at=captured_at),
            "by_delivery": {
                "delivered": process_summary(delivered, horizon, captured_at=captured_at),
                "without_observed_delivery": process_summary(
                    undelivered, horizon, captured_at=captured_at
                ),
            },
        },
        "adoption": adoption_comparison(
            by_project, project_labels, horizon, captured_at=captured_at
        ),
        "source_coverage": {key: dict(value) for key, value in completeness.items()},
        "trends": calendar_trends(
            records,
            start,
            horizon,
            prices=prices,
            costs=costs,
            project_models=project_models,
        ),
        "projects": project_rows,
    }, details
