"""Collect one GitLab merge request and preserve normalized historical observations."""

from __future__ import annotations

import re
from typing import Any

from .attempts import correlate, read_attempts, read_intervals
from .discussions import merge_review_history, read_discussions
from .facts import identity, revision_sha, timestamp
from .process import read_process
from .transport import CollectionError, GitLabClient, RequestError

MR_STATES = {"opened", "closed", "merged", "locked"}


def mr_identity(payload: Any, project_id: int, iid: int | None = None) -> int:
    """Require a linked MR identity and valid chronology before reading its children."""

    identified = identity(payload.get("iid")) if isinstance(payload, dict) else None
    if (
        identified is None
        or (iid is not None and identified != iid)
        or identity(payload.get("project_id")) != project_id
        or (created_at := timestamp(payload.get("created_at"))) is None
        or (updated_at := timestamp(payload.get("updated_at"))) is None
        or updated_at < created_at
    ):
        raise CollectionError("Cannot verify a merge request in the selected GitLab project.")
    return identified


def read_mr(client: GitLabClient, project_id: int, iid: int) -> dict[str, Any]:
    """Read exact current process metadata within one selected project."""

    payload = client.get(f"projects/{project_id}/merge_requests/{iid}")
    mr_identity(payload, project_id, iid)
    return payload


def collect_mr(
    client: GitLabClient,
    project: dict[str, Any],
    mr: dict[str, Any],
    bot_id: int,
    job_names: frozenset[str],
    previous: dict[str, Any] | None,
    *,
    refresh_attempts: bool,
    lifecycle_observed_at: str,
) -> dict[str, Any]:
    """Acquire one verified MR and keep only report facts and stable history keys."""

    project_id = project["id"]
    iid = mr_identity(mr, project_id)
    endpoint = f"projects/{project_id}/merge_requests/{iid}"
    web_url = client.web_url(mr.get("web_url"), f"{project['path']}/-/merge_requests/{iid}")
    state = mr.get("state")
    if not isinstance(state, str) or state not in MR_STATES:
        raise CollectionError("GitLab returned an unsupported merge-request state.")
    created_at = timestamp(mr.get("created_at"))
    merged_at, closed_at = timestamp(mr.get("merged_at")), timestamp(mr.get("closed_at"))
    saved = previous or {}
    approved_sources = saved.get("completeness", {})
    discussion_state = "complete"
    try:
        discussions, current, process, reactions, reaction_state, timeline = read_discussions(
            client, endpoint, mr, bot_id
        )
        approval_state = "complete" if process["approval_count"] is not None else "unavailable"
    except RequestError as exc:
        if exc.status not in {403, 404}:
            raise
        discussion_state = approval_state = reaction_state = "unavailable"
        discussions, current = saved.get("discussions", []), []
        process, reactions = dict(saved.get("process", {})), saved.get("reactions", {})
        timeline = None
    history = merge_review_history(previous["reviews"] if previous else [], current)
    runs, revisions = saved.get("runs", []), saved.get("revisions", [])
    counts, checkpoints = saved.get("correlation", {}), saved.get("checkpoints", [])
    pipeline_state = approved_sources.get("pipelines", "unavailable")
    revision_state = approved_sources.get("revisions", "unavailable")
    version_state = approved_sources.get("versions", "unavailable")
    process["diff_versions"] = saved.get("process", {}).get("diff_versions")
    process["latest_revision_at"] = saved.get("process", {}).get("latest_revision_at")
    if previous is None or refresh_attempts or history != previous["reviews"]:
        head = revision_sha(mr.get("sha"))
        version_state = "complete"
        try:
            versions = client.pages(f"{endpoint}/versions")
        except RequestError as exc:
            if exc.status not in {403, 404}:
                raise
            versions = []
            version_state = "unavailable"
        if version_state == "complete":
            version_times = [
                observed
                for version in versions
                if (observed := timestamp(version.get("created_at")))
            ]
            process.update(
                diff_versions=len(versions), latest_revision_at=max(version_times, default=None)
            )
        known_revisions = {
            sha for version in versions if (sha := revision_sha(version.get("head_commit_sha")))
        }
        if version_state == "complete" and any(
            not revision_sha(version.get("head_commit_sha"))
            or not timestamp(version.get("created_at"))
            for version in versions
        ):
            version_state = "partial"
        try:
            raw_attempts = read_attempts(
                client,
                project_id,
                iid,
                job_names,
                known_revisions=known_revisions | {head},
                source_branch=mr.get("source_branch"),
            )
        except RequestError as exc:
            if exc.status not in {403, 404}:
                raise
            pipeline_state = revision_state = "unavailable"
        else:
            runs, correlated, counts = correlate(
                raw_attempts, history, state, merged_at if state == "merged" else closed_at
            )
            revisions = read_intervals(client, project_id, correlated, head)
            checkpoints = [checkpoint for checkpoint, _ in correlated]
            pipeline_state = "complete"
            revision_state = (
                "partial"
                if version_state != "complete"
                or any(not interval["comparable"] for interval in revisions)
                else "complete"
            )
    process["latest_meaningful_activity_at"] = (
        max(
            (
                value
                for value in (
                    created_at,
                    process.get("latest_human_action_at"),
                    process.get("latest_revision_at"),
                )
                if value
            ),
            default=None,
        )
        if discussion_state == version_state == "complete"
        else None
    )
    changes_count = mr.get("changes_count")
    process["changed_files"] = (
        int(changes_count)
        if isinstance(changes_count, str) and re.fullmatch(r"[0-9]{1,8}", changes_count)
        else None
    )
    graph_state, commits_state = read_process(client, project["path"], iid, mr, process, timeline)
    process_state = (
        "complete"
        if discussion_state == graph_state == "complete"
        else "unavailable"
        if discussion_state == graph_state == "unavailable"
        else "partial"
    )
    return {
        "project_id": project_id,
        "iid": iid,
        "state": state,
        "lifecycle_observed_at": lifecycle_observed_at,
        "draft": mr.get("draft") is True or mr.get("work_in_progress") is True,
        "created_at": created_at,
        "updated_at": timestamp(mr.get("updated_at")),
        "merged_at": merged_at,
        "closed_at": closed_at,
        "web_url": web_url,
        "runs": runs,
        "checkpoints": checkpoints,
        "revisions": revisions,
        "reviews": history,
        "discussions": discussions,
        "reactions": reactions,
        "process": process,
        "correlation": counts,
        "completeness": {
            "discussions": discussion_state,
            "approvals": approval_state,
            "reactions": reaction_state,
            "pipelines": pipeline_state,
            "revisions": revision_state,
            "versions": version_state,
            "graphql": graph_state,
            "commits": commits_state,
            "process": process_state,
        },
    }
