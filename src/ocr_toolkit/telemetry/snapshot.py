"""Validate the identity and scope of a portable, private GitLab observation."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

SCHEMA = "ocr.gitlab-telemetry/v1"


class TelemetryError(ValueError):
    """An operator-facing diagnostic with no upstream response or matched text."""


def unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise TelemetryError("Duplicate fields in telemetry snapshot.")
    return fields


def _invalid_number(_value: str) -> None:
    raise TelemetryError("Invalid number in telemetry snapshot.")


def _id(row: object, field: str) -> int:
    value = row.get(field) if isinstance(row, dict) else None
    if type(value) is not int or not 0 < value < 2**63:
        raise TelemetryError("Invalid telemetry snapshot identity.")
    return value


def _scope(scope: dict[str, Any], value: dict[str, Any]) -> None:
    from .collection.facts import instant
    from .collection.scope import BOT
    from .links import INSTANCE_PATH, web_location

    jobs = scope.get("job_names")
    bot, host, prefix = (scope.get(key) for key in ("bot", "host", "base_path"))
    if not (
        isinstance(bot, str)
        and BOT.fullmatch(bot)
        and isinstance(host, str)
        and isinstance(prefix, str)
        and INSTANCE_PATH.fullmatch(prefix)
        and web_location(f"https://{host}{prefix}/") == (host, f"{prefix}/")
        and scope.get("discovery") in ("explicit", "bot_contributions")
        and instant(scope.get("updated_at")) is not None
        and type(value.get("rolling_end")) is bool
        and type(value.get("costs_enabled")) is bool
        and isinstance(jobs, list)
        and 0 < len(jobs) <= 64
        and all(
            isinstance(job, str)
            and 0 < len(job) <= 128
            and all(ord(c) >= 32 and ord(c) != 127 for c in job)
            for job in jobs
        )
        and jobs == sorted(set(jobs))
    ):
        raise TelemetryError("Invalid saved telemetry scope.")
    _id(scope, "bot_id")


def read_document(raw: bytes) -> dict[str, Any]:
    from ocr_toolkit.review_model import model_slug

    from .collection.facts import instant

    value = json.loads(raw, object_pairs_hook=unique_fields, parse_constant=_invalid_number)
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise TelemetryError("Unsupported telemetry snapshot. Collect a fresh snapshot.")
    scope, projects, records = (value.get(field) for field in ("scope", "projects", "records"))
    if (
        not isinstance(scope, dict)
        or not isinstance(projects, list)
        or len(projects) > 100
        or not isinstance(records, list)
        or len(records) > 10_000
    ):
        raise TelemetryError("Incomplete or oversized telemetry snapshot.")
    _scope(scope, value)
    try:
        start, end = date.fromisoformat(scope["start"]), date.fromisoformat(scope["end"])
    except (TypeError, KeyError, ValueError):
        raise TelemetryError("Invalid snapshot period.") from None
    if not 0 <= (end - start).days < 10_000:
        raise TelemetryError("Invalid snapshot period.")
    project_ids = {_id(row, "id") for row in projects}
    for project in projects:
        model, observed = project.get("cost_model"), project.get("cost_model_observed_at")
        if model is None and observed is None:
            continue
        if not model_slug(model) or instant(observed) is None:
            raise TelemetryError("Invalid project cost model observation.")
    mr_ids = {(_id(row, "project_id"), _id(row, "iid")) for row in records}
    if (
        len(project_ids) != len(projects)
        or len(mr_ids) != len(records)
        or any(pid not in project_ids for pid, _iid in mr_ids)
    ):
        raise TelemetryError("Telemetry snapshot identities are inconsistent.")
    for row in records:
        for field in ("runs", "reviews", "checkpoints", "discussions", "revisions"):
            if not isinstance(row.get(field), list) or any(
                not isinstance(item, dict) for item in row[field]
            ):
                raise TelemetryError("Invalid telemetry observation list.")
        for field in ("process", "completeness", "correlation", "reactions"):
            if not isinstance(row.get(field), dict):
                raise TelemetryError("Invalid telemetry observation.")
    return value
