"""Collect a private telemetry observation from a bounded GitLab project scope."""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from ..publications.grammar import model_publication
from ..rates import cost_token_counts, publication_model
from .facts import instant, timestamp
from .merge_request import collect_mr, read_mr
from .scope import current_project_model, resolve_bot, selected_projects
from .transport import CollectionError, GitLabClient, RequestError
from .updates import MAX_RECORDS, observation_work, unavailable_sources


def collect(
    *,
    previous: dict[str, Any] | None,
    projects: list[str],
    bot: str,
    job_names: list[str],
    start: str,
    end: str,
    collect_model: bool = True,
) -> dict[str, Any]:
    """Collect a period or refresh a previously admitted observation on its exact host."""

    try:
        start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
        first = timestamp(f"{start_day}T00:00:00Z")
        last = timestamp(f"{end_day + timedelta(days=1)}T00:00:00Z")
    except (ValueError, OverflowError):
        raise CollectionError("Select a valid inclusive GitLab observation period.") from None
    if not first or not last or not 0 <= (end_day - start_day).days < 10_000:
        raise CollectionError("Select a valid inclusive GitLab observation period.")
    if (
        not job_names
        or len(job_names) > 64
        or any(
            not name or len(name) > 128 or any(ord(char) < 32 or ord(char) == 127 for char in name)
            for name in job_names
        )
    ):
        raise CollectionError("Specify one or more bounded review job names.")
    jobs = sorted(set(job_names))
    old_scope = previous["scope"] if previous else None
    watermark = None
    previous_end = last
    if old_scope:
        if (
            start != old_scope["start"]
            or end < old_scope["end"]
            or bot != old_scope["bot"]
            or jobs != old_scope["job_names"]
        ):
            raise CollectionError("The update does not match the saved GitLab observation scope.")
        stored_at = instant(old_scope["updated_at"])
        if stored_at is None:
            raise CollectionError("The saved GitLab observation watermark is unavailable.")
        watermark = timestamp((stored_at - timedelta(minutes=1)).isoformat())
        previous_end = (
            timestamp(f"{date.fromisoformat(old_scope['end']) + timedelta(days=1)}T00:00:00Z")
            or last
        )
    started = timestamp(datetime.now(UTC).isoformat())
    client = GitLabClient()
    if old_scope and (client.host, client.base_path) != (
        old_scope["host"],
        old_scope.get("base_path"),
    ):
        raise CollectionError("The active glab host does not match the saved GitLab observation.")
    bot_id = resolve_bot(client, bot)
    if old_scope and bot_id != old_scope.get("bot_id"):
        raise CollectionError("The selected GitLab bot no longer matches the saved observation.")
    selected, discovery = selected_projects(client, projects, bot_id, previous)
    print(
        f"GitLab telemetry period {start} to {end} inclusive across {len(selected)} project(s).",
        file=sys.stderr,
        flush=True,
    )
    existing = (
        {(row["project_id"], row["iid"]): row for row in previous["records"]} if previous else {}
    )
    retry_projects = (
        {item["id"] for item in previous["projects"] if item["access"] != "complete"}
        if previous
        else set()
    )
    work = observation_work(
        client,
        selected,
        existing,
        first=first,
        last=last,
        previous_end=previous_end,
        watermark=watermark,
        retry_projects=retry_projects,
    )
    inaccessible = {project["id"] for project in selected if project["access"] == "unavailable"}
    if len(inaccessible) == len(selected):
        raise CollectionError("GitLab access was lost for the entire saved project scope.")
    project_paths = {project["id"]: project["path"] for project in selected}
    for key, record in existing.items():
        if key[0] in inaccessible:
            existing[key] = unavailable_sources(record)
        else:
            relative = f"{project_paths[key[0]]}/-/merge_requests/{key[1]}"
            try:
                url = client.web_url(record.get("web_url"), relative)
            except CollectionError:
                url = client.web_url(None, relative)
            if record.get("web_url") != url:
                existing[key] = {**record, "web_url": url}
    total = len(work)
    print(f"Collecting {total} GitLab merge request(s).", file=sys.stderr, flush=True)
    for index, (project, iid, refresh_attempts) in enumerate(work, 1):
        key = (project["id"], iid)
        try:
            mr = read_mr(client, project["id"], iid)
        except RequestError as exc:
            if exc.status not in {403, 404} or previous is None:
                raise
            project["access"] = "partial"
            if key in existing:
                existing[key] = unavailable_sources(existing[key])
        else:
            lifecycle_observed_at = timestamp(datetime.now(UTC).isoformat())
            assert lifecycle_observed_at is not None
            created_at = timestamp(mr["created_at"])
            if key in existing or (created_at is not None and first <= created_at < last):
                existing[key] = collect_mr(
                    client,
                    project,
                    mr,
                    bot_id,
                    frozenset(jobs),
                    existing.get(key),
                    refresh_attempts=refresh_attempts,
                    lifecycle_observed_at=lifecycle_observed_at,
                )
        if index == total or index % 50 == 0:
            print(
                f"Collected {index}/{total} GitLab merge request(s).", file=sys.stderr, flush=True
            )
    if len(existing) > MAX_RECORDS:
        raise CollectionError("The selected GitLab period exceeded the merge-request limit.")
    eligible = {
        record["project_id"]
        for record in existing.values()
        if collect_model
        and any(
            model_publication(review)
            and review.get("model_rejected") is not True
            and publication_model(review) is None
            and (usage := cost_token_counts(review.get("tokens"))) is not None
            and usage.complete
            and (usage.input or usage.output)
            for review in record["reviews"]
        )
    }
    for project in selected:
        project["cost_model"], project["cost_model_observed_at"] = (
            current_project_model(client, project["id"])
            if project["access"] == "complete" and project["id"] in eligible
            else (None, None)
        )
    return {
        "scope": {
            "start": start,
            "end": end,
            "discovery": discovery,
            "bot": bot,
            "bot_id": bot_id,
            "job_names": jobs,
            "host": client.host,
            "base_path": client.base_path,
            "updated_at": started,
        },
        "projects": selected,
        "records": sorted(existing.values(), key=lambda row: (row["project_id"], row["iid"])),
    }


__all__ = ["CollectionError", "collect"]
