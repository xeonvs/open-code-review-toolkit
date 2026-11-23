"""Acquire technical attempts and classify causally comparable review revisions."""

from __future__ import annotations

import re
from typing import Any

from .facts import identity, revision_sha, timestamp
from .transport import CollectionError, GitLabClient, RequestError

TERMINAL_JOB_STATES = frozenset({"success", "failed", "canceled", "skipped"})
JOB_STATES = TERMINAL_JOB_STATES | {
    "created",
    "pending",
    "running",
    "manual",
    "scheduled",
    "preparing",
    "waiting_for_resource",
    "canceling",
}
FAILURE_REASONS = frozenset(
    {
        "script_failure",
        "runner_system_failure",
        "stuck_or_timeout_failure",
        "job_execution_timeout",
        "scheduler_failure",
        "archived_failure",
        "unmet_prerequisites",
        "data_integrity_failure",
        "api_failure",
        "runner_unsupported",
        "unknown_failure",
        "missing_dependency_failure",
        "forward_deployment_failure",
        "user_blocked",
        "protected_environment_failure",
    }
)
MAX_PIPELINES = 500
MAX_FIRST_PARENT_PAGES = 5
ANCESTRY_UNAVAILABLE = "ancestry_unavailable"
MR_REF = re.compile(r"refs/merge-requests/([1-9][0-9]{0,18})/(?:head|merge)")


def _job_status(value: object) -> str:
    """Keep closed provider job states only."""

    return value if isinstance(value, str) and value in JOB_STATES else "unknown"


def read_attempts(
    client: GitLabClient,
    project_id: int,
    iid: int,
    job_names: frozenset[str],
    *,
    known_revisions: set[str],
    source_branch: object,
) -> list[tuple[dict[str, Any], str]]:
    """Bind selected attempts to authorized MR pipelines and transient revisions."""

    base = f"projects/{project_id}"
    pipelines = client.pages(f"{base}/merge_requests/{iid}/pipelines")
    if len(pipelines) > MAX_PIPELINES:
        raise CollectionError("A GitLab merge request exceeded the pipeline limit.")
    seen_pipelines: dict[int, dict[str, Any]] = {}
    seen_jobs: dict[int, dict[str, Any]] = {}
    attempts: list[tuple[dict[str, Any], str]] = []
    for pipeline in pipelines:
        if "source" in pipeline and pipeline["source"] != "merge_request_event":
            continue
        if pipeline.get("project_id", project_id) != project_id:
            continue
        pipeline_id = identity(pipeline.get("id"))
        sha = revision_sha(pipeline.get("sha"))
        pipeline_time = timestamp(pipeline.get("created_at"))
        if pipeline_id is None or not sha:
            raise CollectionError("GitLab returned an invalid merge-request pipeline.")
        if pipeline_id in seen_pipelines:
            if seen_pipelines[pipeline_id] == pipeline:
                continue
            raise CollectionError("GitLab returned duplicate merge-request pipelines.")
        seen_pipelines[pipeline_id] = pipeline
        ref = pipeline.get("ref")
        if not isinstance(ref, str) or not ref:
            raise CollectionError("GitLab returned an invalid merge-request pipeline ref.")
        scoped_ref = MR_REF.fullmatch(ref)
        if scoped_ref and int(scoped_ref[1]) != iid:
            raise CollectionError("GitLab returned a pipeline for a different merge request.")
        if "source" not in pipeline or pipeline_time is None:
            detail = client.get(f"{base}/pipelines/{pipeline_id}")
            if (
                not isinstance(detail, dict)
                or identity(detail.get("id")) != pipeline_id
                or identity(detail.get("project_id")) != project_id
                or detail.get("sha") != sha
                or detail.get("ref") != ref
                or not isinstance(detail.get("source"), str)
                or ("source" in pipeline and detail["source"] != pipeline["source"])
                or (detail_time := timestamp(detail.get("created_at"))) is None
                or (pipeline_time is not None and pipeline_time != detail_time)
            ):
                raise CollectionError("GitLab pipeline details do not match the merge request.")
            if detail["source"] != "merge_request_event":
                continue
            pipeline_time = detail_time
        detached = ref == f"refs/merge-requests/{iid}/head" or (
            isinstance(source_branch, str) and ref == source_branch and sha in known_revisions
        )
        jobs = client.pages(
            f"{base}/pipelines/{pipeline_id}/jobs", query={"include_retried": "true"}
        )
        for job in jobs:
            if not isinstance(job.get("name"), str) or job["name"] not in job_names:
                continue
            job_id = identity(job.get("id"))
            nested = job.get("pipeline")
            if job_id is None or (
                isinstance(nested, dict)
                and (nested.get("id") != pipeline_id or nested.get("sha", sha) != sha)
            ):
                raise CollectionError("GitLab returned an invalid review job identity.")
            if job_id in seen_jobs:
                if seen_jobs[job_id] == job:
                    continue
                raise CollectionError("GitLab returned conflicting duplicate review jobs.")
            seen_jobs[job_id] = job
            started_at, finished_at = (
                timestamp(job.get("started_at")),
                timestamp(job.get("finished_at")),
            )
            status = _job_status(job.get("status"))
            reason = job.get("failure_reason")
            attempts.append(
                (
                    {
                        "_pipeline_id": pipeline_id,
                        "pipeline_created_at": pipeline_time,
                        "created_at": timestamp(job.get("created_at")),
                        "started_at": started_at,
                        "finished_at": finished_at,
                        "review_finished_at": finished_at,
                        "started": (
                            True
                            if started_at
                            else False
                            if "started_at" in job and job["started_at"] is None
                            else None
                        ),
                        "status": status,
                        "allow_failure": (
                            job["allow_failure"] if type(job.get("allow_failure")) is bool else None
                        ),
                        "failure_reason": (
                            reason
                            if isinstance(reason, str) and reason in FAILURE_REASONS
                            else None
                        ),
                        "detached": detached,
                    },
                    sha,
                )
            )
    return sorted(
        attempts,
        key=lambda entry: (
            entry[0]["pipeline_created_at"] or "",
            entry[0]["created_at"] or "",
            entry[0]["started_at"] or "",
            entry[0]["review_finished_at"] or "",
        ),
    )


def _execution(run: dict[str, Any]) -> tuple[str, str] | None:
    """Check the complete chronology before matching a delivery to a job."""

    times = [
        run.get(key)
        for key in ("pipeline_created_at", "created_at", "started_at", "review_finished_at")
    ]
    start, end = times[-2:]
    present = [value for value in times if value]
    return (start, end) if start and end and present == sorted(present) else None


def correlate(
    attempts: list[tuple[dict[str, Any], str]],
    reviews: list[dict[str, Any]],
    lifecycle: str,
    terminal_at: str | None,
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]], dict[str, int]]:
    """Retain technical attempts and exclude uniquely correlated pre-model stops."""

    runs: list[dict[str, Any]] = []
    checkpoints: dict[str, tuple[dict[str, Any], str]] = {}
    seen_revisions: set[str] = set()
    seen_pipelines: set[tuple[str, int]] = set()
    counts = dict(messages=0, matched_messages=0, unmatched_messages=0, ambiguous_messages=0)
    starts: dict[int, str] = {}
    for index, (run, _sha) in enumerate(attempts):
        if run.get("started_at"):
            starts[index] = run["started_at"]
    pre_model: set[int] = set()
    pre_terminal: set[int] = set()
    for review in reviews:
        kind = review.get("result_kind")
        if kind not in {"pre_model", "terminal_lifecycle"} or review.get("recognized") is False:
            continue
        created, updated = review.get("created_at"), review.get("updated_at")
        candidates = []
        terminal_time = None
        if created and updated and created <= updated:
            terminal_time = updated
            observed = (updated,) if kind == "terminal_lifecycle" else (created, updated)
            for index in starts:
                times = _execution(attempts[index][0])
                if times and any(times[0] <= value <= times[1] for value in observed):
                    candidates.append(index)
        if kind == "pre_model":
            counts["messages"] += 1
            if len(candidates) == 1:
                counts["matched_messages"] += 1
                pre_model.add(candidates[0])
            else:
                counts["ambiguous_messages" if candidates else "unmatched_messages"] += 1
        else:
            terminal = review.get("terminal_lifecycle")
            if terminal in {"closed", "merged"}:
                if len(candidates) == 1:
                    pre_terminal.add(candidates[0])
                if (
                    terminal == lifecycle
                    and terminal_at
                    and terminal_time
                    and terminal_time >= terminal_at
                ):
                    pre_terminal.update(
                        index for index, start in starts.items() if start > terminal_at
                    )
    counts["matched_technical_attempts"] = len(pre_model)
    for index, (run, sha) in enumerate(attempts):
        origin = (sha, run["_pipeline_id"])
        repeat = (
            "repeat_same_pipeline"
            if origin in seen_pipelines
            else "repeat_new_pipeline"
            if sha in seen_revisions
            else "first_for_revision"
        )
        seen_revisions.add(sha)
        seen_pipelines.add(origin)
        excluded = index in pre_model or index in pre_terminal
        success = (
            run["status"] == "success"
            and run["detached"]
            and run["pipeline_created_at"] is not None
            and not excluded
            and bool(_execution(run))
        )
        runs.append(
            {
                **{key: value for key, value in run.items() if key != "_pipeline_id"},
                "attempt_kind": repeat,
                "pre_model_stop": index in pre_model,
                "terminal_pre_model": index in pre_terminal,
                "success": success,
            }
        )
        if success:
            checkpoint = {key: run[key] for key in ("pipeline_created_at", "started_at")}
            checkpoint["finished_at"] = run["review_finished_at"]
            old = checkpoints.get(sha)
            if old is None or checkpoint["finished_at"] < old[0]["finished_at"]:
                checkpoints[sha] = (checkpoint, sha)
    return (
        runs,
        sorted(
            checkpoints.values(),
            key=lambda entry: (entry[0]["pipeline_created_at"] or "", entry[0]["finished_at"]),
        ),
        counts,
    )


def _first_parent_interval(
    client: GitLabClient, project_id: int, source: str, target: str
) -> dict[str, Any]:
    """Walk exact commit identities on the target's first-parent chain."""

    compare = {
        "comparable": False,
        "commits": None,
        "merge_commits": None,
        "non_merge_commits": None,
        "change_kind": "rewritten_or_incomparable",
    }
    if not source or not target:
        return compare
    current, commits, merges = target, 0, 0
    visited: set[str] = set()
    for page in range(1, MAX_FIRST_PARENT_PAGES + 1):
        if current == source:
            break
        try:
            rows = client.get(
                f"projects/{project_id}/repository/commits",
                query={
                    "ref_name": target,
                    "first_parent": "true",
                    "per_page": "100",
                    "page": str(page),
                },
            )
        except RequestError as exc:
            if exc.status not in {403, 404}:
                raise
            return {**compare, "change_kind": ANCESTRY_UNAVAILABLE}
        if not isinstance(rows, list) or not rows or len(rows) > 100:
            return compare
        for row in rows:
            if current == source:
                break
            if not isinstance(row, dict) or row.get("id") != current or current in visited:
                return compare
            visited.add(current)
            parents = row.get("parent_ids")
            if not isinstance(parents, list) or not parents or not all(map(revision_sha, parents)):
                return compare
            commits += 1
            merges += int(len(parents) > 1)
            current = parents[0]
    if current != source:
        return compare
    return {
        "comparable": True,
        "commits": commits,
        "merge_commits": merges,
        "non_merge_commits": commits - merges,
        "change_kind": (
            "none"
            if not commits
            else "non_merge_only"
            if not merges
            else "merge_only"
            if merges == commits
            else "mixed"
        ),
    }


def read_intervals(
    client: GitLabClient,
    project_id: int,
    checkpoints: list[tuple[dict[str, Any], str]],
    head: str,
) -> list[dict[str, Any]]:
    """Classify each transition once per distinct revision plus the final tail."""

    ordered: dict[str, dict[str, Any]] = {}
    for checkpoint, sha in checkpoints:
        ordered.setdefault(sha, checkpoint)
    entries = list(ordered.items())
    return [
        {
            "pipeline_created_at": checkpoint["pipeline_created_at"],
            "followup_review": index < len(entries) - 1,
            "final_tail": index == len(entries) - 1,
            **_first_parent_interval(
                client, project_id, sha, entries[index + 1][0] if index < len(entries) - 1 else head
            ),
        }
        for index, (sha, checkpoint) in enumerate(entries)
    ]
