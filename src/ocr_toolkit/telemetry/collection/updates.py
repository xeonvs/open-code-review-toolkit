"""Resolve bounded observation work across MR, pipeline, and discussion changes."""

from __future__ import annotations

import re
from typing import Any

from .attempts import ANCESTRY_UNAVAILABLE, TERMINAL_JOB_STATES
from .facts import timestamp
from .merge_request import mr_identity
from .transport import CollectionError, GitLabClient, RequestError

MAX_RECORDS = 10_000
MR_PIPELINE_REF = re.compile(r"refs/merge-requests/([1-9][0-9]{0,18})/(?:head|merge)")


def _list_mrs(
    client: GitLabClient, project_id: int, *, start: str, end: str, updated: str | None = None
) -> dict[int, dict[str, Any]]:
    """Read period or incremental MR membership through the scoped project endpoint."""

    rows = client.pages(
        f"projects/{project_id}/merge_requests",
        query={
            "state": "all",
            "scope": "all",
            "created_before": end,
            "created_after": start,
            **({"updated_after": updated} if updated else {}),
        },
    )
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        iid = mr_identity(row, project_id)
        created_at = timestamp(row["created_at"])
        assert created_at is not None
        if start <= created_at < end:
            current = result.get(iid)
            if current is None or (timestamp(current["updated_at"]) or "") <= (
                timestamp(row["updated_at"]) or ""
            ):
                result[iid] = row
    return result


def _pipeline_updates(
    client: GitLabClient, project_id: int, watermark: str, known: dict[int, dict[str, Any]]
) -> set[int]:
    """Detect job-only changes and conservatively refresh unbound project pipelines."""

    rows = client.pages(
        f"projects/{project_id}/pipelines",
        query={"source": "merge_request_event", "updated_after": watermark},
    )
    changed: set[int] = set()
    for row in rows:
        if row.get("source", "merge_request_event") != "merge_request_event":
            continue
        ref = row.get("ref")
        match = MR_PIPELINE_REF.fullmatch(ref) if isinstance(ref, str) else None
        if match is None:
            # Some GitLab releases use branch refs for MR pipelines. Those
            # events cannot select a foreign MR and still need a safe refresh.
            changed.update(known)
        elif int(match[1]) in known:
            changed.add(int(match[1]))
    changed.update(
        iid
        for iid, record in known.items()
        if record["completeness"].get("pipelines") != "complete"
        or record["completeness"].get("versions") != "complete"
        or any(
            interval.get("change_kind") == ANCESTRY_UNAVAILABLE for interval in record["revisions"]
        )
        or any(run["status"] not in TERMINAL_JOB_STATES for run in record["runs"])
    )
    return changed


def observation_work(
    client: GitLabClient,
    projects: list[dict[str, Any]],
    existing: dict[tuple[int, int], dict[str, Any]],
    *,
    first: str,
    last: str,
    previous_end: str,
    watermark: str | None,
    retry_projects: set[int],
) -> list[tuple[dict[str, Any], int, bool]]:
    """Combine MR, pipeline and discussion refresh work under one fixed bound."""

    work: list[tuple[dict[str, Any], int, bool]] = []
    for project in projects:
        if project["access"] == "unavailable":
            continue
        project_id = project["id"]
        try:
            updated = None if project_id in retry_projects else watermark
            observed = _list_mrs(client, project_id, start=first, end=last, updated=updated)
            if updated and previous_end < last:
                observed.update(_list_mrs(client, project_id, start=previous_end, end=last))
        except RequestError as exc:
            if exc.status not in {403, 404} or watermark is None:
                raise
            project["access"] = "unavailable"
            continue
        known = {iid: record for (pid, iid), record in existing.items() if pid == project_id}
        changed = set(observed)
        if project_id in retry_projects:
            changed.update(known)
        elif watermark:
            try:
                changed |= _pipeline_updates(client, project_id, watermark, known)
            except RequestError as exc:
                if exc.status not in {403, 404}:
                    raise
                changed.update(known)
                project["access"] = "partial"
        refresh = {
            iid
            for iid, record in known.items()
            if record["reviews"]
            or record["discussions"]
            or record["process"].get("assigned_review_threads")
            or any(
                record["completeness"].get(source) != "complete"
                for source in ("discussions", "graphql", "approvals", "reactions")
            )
        }
        work.extend((project, iid, iid in changed) for iid in sorted(changed | refresh))
        if len(work) > MAX_RECORDS:
            raise CollectionError("The selected GitLab period exceeded the merge-request limit.")
    return work


def unavailable_sources(record: dict[str, Any]) -> dict[str, Any]:
    """Keep saved observations while exposing the loss of fresh source access."""

    return {
        **record,
        "process": {**record["process"], "latest_meaningful_activity_at": None},
        "completeness": dict.fromkeys(record["completeness"], "unavailable"),
    }
