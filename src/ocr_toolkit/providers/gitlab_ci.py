"""Acquire stable bounded same-revision GitLab CI outcomes without logs."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

from ocr_toolkit.context.ci_outcomes import CIOutcome, CIOutcomeSnapshot
from ocr_toolkit.context.contracts import CIOutcomePolicy
from ocr_toolkit.providers.gitlab import GitLabProviderError, _api_root, _numeric_identifier
from ocr_toolkit.providers.gitlab_context import SHA_RE, timestamp

MAX_PAGE_BYTES = 512 * 1024
MAX_PIPELINES = 20
MAX_JOBS_PER_PIPELINE = 100


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent provider credentials from crossing redirects."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GitLabProviderError("GitLab CI response contains a duplicate JSON key")
        result[key] = value
    return result


def _read_page(url: str, token: str, *, deadline: float) -> tuple[object, bool]:
    """Read one bounded JSON page and report whether another page exists."""

    if not token or "\r" in token or "\n" in token or len(token) > 16_384:
        raise GitLabProviderError("GITLAB_API_TOKEN is missing or malformed")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise GitLabProviderError("GitLab CI outcome acquisition timed out")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "PRIVATE-TOKEN": token,
            "User-Agent": "open-code-review-toolkit-ci-outcomes/1",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler)
    try:
        with opener.open(request, timeout=remaining) as response:
            if response.headers.get_content_type() != "application/json":
                raise GitLabProviderError("GitLab CI outcome content type is invalid")
            raw = response.read(MAX_PAGE_BYTES + 1)
            if len(raw) > MAX_PAGE_BYTES:
                raise GitLabProviderError("GitLab CI outcome page exceeds its byte limit")
            next_page = response.headers.get("X-Next-Page", "")
    except urllib.error.HTTPError as exc:
        raise GitLabProviderError("GitLab CI outcomes are unavailable") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise GitLabProviderError("GitLab CI outcome request failed") from exc
    if next_page and (not next_page.isascii() or not next_page.isdecimal() or len(next_page) > 4):
        raise GitLabProviderError("GitLab CI outcome pagination is invalid")
    try:
        return (
            json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs),
            bool(next_page),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GitLabProviderError("GitLab CI outcomes are not valid bounded JSON") from exc


def _positive_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitLabProviderError("GitLab CI outcome identity is invalid")
    return value


def _bounded_name(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or len(value.encode("utf-8")) > 512
        or any(character == "\x7f" or ord(character) < 32 for character in value)
    ):
        raise GitLabProviderError("GitLab CI check name is invalid")
    return value


def _raw_snapshot(
    environment: Mapping[str, str],
    *,
    project_id: str,
    source_sha: str,
    policy: CIOutcomePolicy,
    now: int,
    deadline: float,
) -> tuple[CIOutcomeSnapshot, str]:
    """Normalize one bounded provider read without retaining raw identities."""

    token = environment.get("GITLAB_API_TOKEN", "").strip()
    api_root = _api_root(environment)
    project = urllib.parse.quote(project_id, safe="")
    query = urllib.parse.urlencode(
        {
            "sha": source_sha,
            "order_by": "updated_at",
            "sort": "desc",
            "per_page": str(MAX_PIPELINES),
            "page": "1",
        }
    )
    pipelines, pipeline_more = _read_page(
        f"{api_root}/projects/{project}/pipelines?{query}", token, deadline=deadline
    )
    if not isinstance(pipelines, list) or len(pipelines) > MAX_PIPELINES:
        raise GitLabProviderError("GitLab CI pipeline list is invalid")
    requested = {check.name: check.path_prefixes for check in policy.checks}
    candidates: dict[str, list[tuple[int, int, int, str, bool]]] = {name: [] for name in requested}
    invalid_names: set[str] = set()
    structural: list[object] = []
    current_pipeline = int(_numeric_identifier(environment, "CI_PIPELINE_ID"))
    omitted = int(pipeline_more)
    invalid = 0
    for pipeline in pipelines:
        if not isinstance(pipeline, Mapping):
            raise GitLabProviderError("GitLab CI pipeline is invalid")
        pipeline_id = _positive_id(pipeline.get("id"))
        pipeline_sha = pipeline.get("sha")
        if not isinstance(pipeline_sha, str) or SHA_RE.fullmatch(pipeline_sha) is None:
            raise GitLabProviderError("GitLab CI pipeline revision is invalid")
        if pipeline_sha != source_sha:
            raise GitLabProviderError("GitLab CI pipeline revision does not match reviewed head")
        jobs, jobs_more = _read_page(
            f"{api_root}/projects/{project}/pipelines/{pipeline_id}/jobs"
            f"?include_retried=true&per_page={MAX_JOBS_PER_PIPELINE}&page=1",
            token,
            deadline=deadline,
        )
        if not isinstance(jobs, list) or len(jobs) > MAX_JOBS_PER_PIPELINE:
            raise GitLabProviderError("GitLab CI job list is invalid")
        omitted += int(jobs_more)
        for job in jobs:
            if not isinstance(job, Mapping):
                raise GitLabProviderError("GitLab CI job is invalid")
            raw_name = job.get("name")
            if not isinstance(raw_name, str) or raw_name not in requested:
                continue
            name = _bounded_name(raw_name)
            nested = job.get("pipeline")
            if (
                not isinstance(nested, Mapping)
                or _positive_id(nested.get("id")) != pipeline_id
                or nested.get("sha") != source_sha
            ):
                invalid_names.add(name)
                continue
            job_id = _positive_id(job.get("id"))
            status = job.get("status")
            allow_failure = job.get("allow_failure")
            completed_at = timestamp(job.get("finished_at"))
            if (
                not isinstance(status, str)
                or not status
                or len(status) > 64
                or not status.isascii()
                or not isinstance(allow_failure, bool)
                or completed_at is None
                or completed_at < 0
                or completed_at > now + 300
            ):
                invalid_names.add(name)
                continue
            candidates[name].append((completed_at, job_id, pipeline_id, status, allow_failure))
            structural.append([pipeline_id, job_id, name, status, allow_failure, completed_at])
    records: list[CIOutcome] = []
    for name, path_prefixes in requested.items():
        selected = sorted(candidates[name], reverse=True)
        if name in invalid_names or not selected:
            invalid += 1
            continue
        newest = selected[0]
        if len(selected) > 1 and selected[1][:2] == newest[:2]:
            invalid += 1
            continue
        completed_at, _job_id, pipeline_id, raw_status, allow_failure = newest
        if now - completed_at > policy.max_age_seconds:
            invalid += 1
            continue
        status = {
            "success": "passed",
            "failed": "failed",
            "canceled": "canceled",
            "skipped": "skipped",
        }.get(raw_status, "unknown")
        normalized = {
            "check": name,
            "status": status,
            "requirement": "advisory" if allow_failure else "required",
            "path_prefixes": list(path_prefixes),
            "origin": (
                "current_pipeline" if pipeline_id == current_pipeline else "same_revision_pipeline"
            ),
            "completed_at": completed_at,
        }
        digest = hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        records.append(
            CIOutcome(
                check=name,
                status=status,
                requirement="advisory" if allow_failure else "required",
                path_prefixes=tuple(path_prefixes),
                origin=(
                    "current_pipeline"
                    if pipeline_id == current_pipeline
                    else "same_revision_pipeline"
                ),
                completed_at=completed_at,
                version=str(completed_at),
                digest=digest,
            )
        )
    omitted += len(requested) - len(records) - invalid
    state = "complete" if not omitted and not invalid else "partial"
    snapshot_digest = hashlib.sha256(
        json.dumps(
            {
                "pipelines": sorted(structural),
                "records": sorted(record.digest for record in records),
                "state": state,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return (
        CIOutcomeSnapshot(
            state=state,
            records=tuple(sorted(records, key=lambda record: record.check)),
            omitted=omitted,
            invalid=invalid,
        ),
        snapshot_digest,
    )


def acquire_gitlab_ci_outcomes(
    environment: Mapping[str, str],
    *,
    project_id: str,
    source_sha: str,
    policy: CIOutcomePolicy,
    now: int,
    deadline: float | None = None,
) -> CIOutcomeSnapshot:
    """Return one twice-read exact-revision snapshot or a mutated state."""

    if (
        project_id != _numeric_identifier(environment, "CI_PROJECT_ID")
        or SHA_RE.fullmatch(source_sha) is None
    ):
        raise GitLabProviderError("GitLab CI outcome identity is invalid")
    acquisition_deadline = time.monotonic() + 30.0 if deadline is None else deadline
    _first, first_digest = _raw_snapshot(
        environment,
        project_id=project_id,
        source_sha=source_sha,
        policy=policy,
        now=now,
        deadline=acquisition_deadline,
    )
    second, second_digest = _raw_snapshot(
        environment,
        project_id=project_id,
        source_sha=source_sha,
        policy=policy,
        now=now,
        deadline=acquisition_deadline,
    )
    if first_digest != second_digest:
        return CIOutcomeSnapshot(state="mutated", records=(), omitted=0, invalid=1)
    return second
