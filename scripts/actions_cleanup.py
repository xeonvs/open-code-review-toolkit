"""Plan or execute bounded GitHub Actions cache, artifact, and log cleanup."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

API_VERSION = "2022-11-28"
USER_AGENT = "open-code-review-toolkit-actions-cleanup/1"
HTTP_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 10
PER_PAGE = 100
MAX_RUN_SHARD_DAYS = 90
MAX_NAME_CHARS = 512
ARTIFACT_RETENTION_DAYS = 7
ORDINARY_LOG_RETENTION_DAYS = 14
RELEASE_LOG_RETENTION_DAYS = 30
LOG_RETRY_WINDOW_DAYS = 14
TESTPYPI_RUN_RETENTION_DAYS = 14
ORDINARY_RUN_RETENTION_DAYS = 30
RELEASE_RUN_RETENTION_DAYS = 60
RUN_LIST_GRACE_DAYS = 14
MAIN_REF = "refs/heads/main"
RELEASE_WORKFLOWS = {"Release", "TestPyPI development build"}
TESTPYPI_WORKFLOWS = {"TestPyPI development build", "TestPyPI preview"}
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class CleanupError(Exception):
    """GitHub Actions cleanup could not be planned or completed safely."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent repository credentials from following an unexpected redirect."""

    def redirect_request(
        self,
        _request: urllib.request.Request,
        _file_pointer: Any,
        _code: int,
        _message: str,
        _headers: Any,
        _new_url: str,
    ) -> None:
        raise CleanupError("GitHub Actions API redirects are not allowed")


API_OPENER = urllib.request.build_opener(_NoRedirectHandler)


@dataclass(frozen=True, slots=True)
class CleanupCandidate:
    """Describe one deletable Actions storage object without holding its payload."""

    kind: str
    object_id: int
    name: str
    size_bytes: int
    reason: str


def _fail(message: str) -> NoReturn:
    raise CleanupError(message)


def _timestamp(value: Any, field: str) -> datetime:
    """Parse one GitHub UTC timestamp or fail closed."""

    if not isinstance(value, str):
        _fail(f"field {field!r} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CleanupError(f"field {field!r} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        _fail(f"field {field!r} must include a timezone")
    return parsed.astimezone(UTC)


def _positive_id(value: Any, field: str) -> int:
    """Return one positive integer API identity."""

    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(f"field {field!r} must be a positive integer")
    return value


def _nonnegative_size(value: Any, field: str) -> int:
    """Return one non-negative byte count."""

    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail(f"field {field!r} must be a non-negative integer")
    return value


def _bounded_name(value: Any, field: str) -> str:
    """Return a bounded control-free API name safe for logs and policy matching."""

    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_NAME_CHARS
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        _fail(f"field {field!r} must be a bounded control-free string")
    return value


def _cache_platform(key: str) -> str:
    """Group setup-uv keys by runner platform so each supported OS keeps one cache."""

    lowered = key.casefold()
    if "linux" in lowered:
        return "linux"
    if "darwin" in lowered or "macos" in lowered:
        return "macos"
    if "windows" in lowered:
        return "windows"
    return "unknown"


def plan_cache_cleanup(caches: list[dict[str, Any]]) -> list[CleanupCandidate]:
    """Remove CodeQL caches, PR uv caches, and superseded main cache generations."""

    candidates: list[CleanupCandidate] = []
    uv_by_platform: dict[str, list[dict[str, Any]]] = {}
    gitleaks: list[dict[str, Any]] = []
    for cache in caches:
        key = _bounded_name(cache.get("key"), "cache.key")
        if key.startswith("codeql-"):
            candidates.append(_cache_candidate(cache, "CodeQL trap caching is disabled"))
        elif key.startswith("setup-uv-"):
            if cache.get("ref") != MAIN_REF:
                candidates.append(_cache_candidate(cache, "setup-uv cache is not on main"))
            else:
                uv_by_platform.setdefault(_cache_platform(key), []).append(cache)
        elif key.startswith("gitleaks-cache-"):
            gitleaks.append(cache)

    # setup-uv keys change with the lockfile. Keep only the newest main cache for
    # each runner platform so Linux and macOS PRs can still restore a warm cache.
    for platform_caches in uv_by_platform.values():
        ordered = sorted(
            platform_caches,
            key=lambda item: _timestamp(item.get("last_accessed_at"), "last_accessed_at"),
            reverse=True,
        )
        for cache in ordered[1:]:
            candidates.append(_cache_candidate(cache, "superseded setup-uv main cache"))

    ordered_gitleaks = sorted(
        gitleaks,
        key=lambda item: _timestamp(item.get("last_accessed_at"), "last_accessed_at"),
        reverse=True,
    )
    for cache in ordered_gitleaks[1:]:
        candidates.append(_cache_candidate(cache, "superseded Gitleaks cache"))
    return sorted(candidates, key=lambda item: (item.kind, item.object_id))


def _cache_candidate(cache: dict[str, Any], reason: str) -> CleanupCandidate:
    """Build a validated cache deletion candidate."""

    key = _bounded_name(cache.get("key"), "cache.key")
    return CleanupCandidate(
        kind="cache",
        object_id=_positive_id(cache.get("id"), "cache.id"),
        name=key,
        size_bytes=_nonnegative_size(cache.get("size_in_bytes"), "cache.size_in_bytes"),
        reason=reason,
    )


def plan_artifact_cleanup(artifacts: list[dict[str, Any]], now: datetime) -> list[CleanupCandidate]:
    """Remove workflow artifacts after the repository's seven-day handoff window."""

    cutoff = now.astimezone(UTC) - timedelta(days=ARTIFACT_RETENTION_DAYS)
    candidates: list[CleanupCandidate] = []
    for artifact in artifacts:
        created_at = _timestamp(artifact.get("created_at"), "artifact.created_at")
        expired = artifact.get("expired")
        if not isinstance(expired, bool):
            _fail("field 'artifact.expired' must be a boolean")
        if not expired and created_at >= cutoff:
            continue
        name = _bounded_name(artifact.get("name"), "artifact.name")
        candidates.append(
            CleanupCandidate(
                kind="artifact",
                object_id=_positive_id(artifact.get("id"), "artifact.id"),
                name=name,
                size_bytes=_nonnegative_size(
                    artifact.get("size_in_bytes"), "artifact.size_in_bytes"
                ),
                reason=("artifact is expired" if expired else "artifact is older than 7 days"),
            )
        )
    return sorted(candidates, key=lambda item: item.object_id)


def plan_log_cleanup(
    runs: list[dict[str, Any]], now: datetime, *, include_all_old: bool = False
) -> list[CleanupCandidate]:
    """Remove due log archives while leaving workflow run and check metadata intact."""

    now_utc = now.astimezone(UTC)
    candidates: list[CleanupCandidate] = []
    for run in runs:
        if run.get("status") != "completed":
            continue
        name = _bounded_name(run.get("name"), "run.name")
        retention_days = (
            RELEASE_LOG_RETENTION_DAYS if name in RELEASE_WORKFLOWS else ORDINARY_LOG_RETENTION_DAYS
        )
        created_at = _timestamp(run.get("created_at"), "run.created_at")
        age = now_utc - created_at
        if age < timedelta(days=retention_days):
            continue
        # Scheduled runs get two weekly opportunities, then stop re-requesting
        # deletion for immutable run metadata whose log archive is already gone.
        if not include_all_old and age >= timedelta(days=retention_days + LOG_RETRY_WINDOW_DAYS):
            continue
        candidates.append(
            CleanupCandidate(
                kind="log",
                object_id=_positive_id(run.get("id"), "run.id"),
                name=name,
                size_bytes=0,
                reason=f"run logs are older than {retention_days} days",
            )
        )
    return sorted(candidates, key=lambda item: item.object_id)


def plan_run_cleanup(runs: list[dict[str, Any]], now: datetime) -> list[CleanupCandidate]:
    """Remove completed run metadata only after its class-specific retention window."""

    now_utc = now.astimezone(UTC)
    candidates: list[CleanupCandidate] = []
    for run in runs:
        if run.get("status") != "completed":
            continue
        name = _bounded_name(run.get("name"), "run.name")
        if name == "Release":
            retention_days = RELEASE_RUN_RETENTION_DAYS
        elif name in TESTPYPI_WORKFLOWS:
            retention_days = TESTPYPI_RUN_RETENTION_DAYS
        else:
            retention_days = ORDINARY_RUN_RETENTION_DAYS
        created_at = _timestamp(run.get("created_at"), "run.created_at")
        if now_utc - created_at < timedelta(days=retention_days):
            continue
        candidates.append(
            CleanupCandidate(
                kind="run",
                object_id=_positive_id(run.get("id"), "run.id"),
                name=name,
                size_bytes=0,
                reason=f"completed run is older than {retention_days} days",
            )
        )
    return sorted(candidates, key=lambda item: item.object_id)


def _api_json(url: str, token: str) -> dict[str, Any]:
    """Read one bounded GitHub Actions JSON response."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        _fail("GitHub Actions API URL escaped api.github.com")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        with API_OPENER.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_RESPONSE_BYTES:
                _fail("GitHub Actions API response exceeds the byte limit")
            data = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise CleanupError(f"GitHub Actions API request failed: {exc}") from exc
    if len(data) > MAX_RESPONSE_BYTES:
        _fail("GitHub Actions API response exceeds the byte limit")
    try:
        value = json.loads(data)
    except json.JSONDecodeError as exc:
        raise CleanupError("GitHub Actions API response is not JSON") from exc
    if not isinstance(value, dict):
        _fail("GitHub Actions API response must be an object")
    return value


def _list_paginated(repository: str, endpoint: str, field: str, token: str) -> list[dict[str, Any]]:
    """Read at most ten pages from one repository Actions collection shard."""

    values: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        separator = "&" if "?" in endpoint else "?"
        url = (
            f"https://api.github.com/repos/{repository}/{endpoint}"
            f"{separator}per_page={PER_PAGE}&page={page}"
        )
        payload = _api_json(url, token)
        page_values = payload.get(field)
        if not isinstance(page_values, list) or len(page_values) > PER_PAGE:
            _fail(f"GitHub Actions field {field!r} has unsupported shape or size")
        if any(not isinstance(item, dict) for item in page_values):
            _fail(f"GitHub Actions field {field!r} must contain objects")
        values.extend(page_values)
        if len(page_values) < PER_PAGE:
            break
    else:
        _fail(f"GitHub Actions listing for {field!r} exceeded {MAX_PAGES} pages")
    return values


def _list_recent_completed_runs(
    repository: str,
    token: str,
    *,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """List a closed UTC-day range while retaining the per-shard page bound."""

    start_date = start.astimezone(UTC).date()
    end_date = end.astimezone(UTC).date()
    days = (end_date - start_date).days + 1
    if not 1 <= days <= MAX_RUN_SHARD_DAYS:
        _fail("GitHub Actions run listing window is invalid or oversized")
    values: list[dict[str, Any]] = []
    seen: set[int] = set()
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        page_values = _list_paginated(
            repository,
            f"actions/runs?status=completed&created={day.isoformat()}",
            "workflow_runs",
            token,
        )
        for item in page_values:
            run_id = _positive_id(item.get("id"), "run.id")
            if run_id in seen:
                _fail("GitHub Actions daily run shards overlap")
            seen.add(run_id)
            values.append(item)
    return values


def _delete(url: str, token: str) -> bool:
    """Delete one exact Actions object, accepting an already-absent archive idempotently."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        _fail("GitHub Actions delete URL escaped api.github.com")
    request = urllib.request.Request(
        url,
        method="DELETE",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        with API_OPENER.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.status != 204:
                _fail(f"GitHub Actions delete returned HTTP {response.status}")
            if response.read(1):
                _fail("GitHub Actions delete returned an unexpected response body")
            return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise CleanupError(f"GitHub Actions delete failed: HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise CleanupError(f"GitHub Actions delete failed: {exc}") from exc


def cleanup_url(repository: str, candidate: CleanupCandidate) -> str:
    """Return the exact REST deletion URL for one planned object."""

    if candidate.kind == "cache":
        suffix = f"actions/caches/{candidate.object_id}"
    elif candidate.kind == "artifact":
        suffix = f"actions/artifacts/{candidate.object_id}"
    elif candidate.kind == "log":
        suffix = f"actions/runs/{candidate.object_id}/logs"
    elif candidate.kind == "run":
        suffix = f"actions/runs/{candidate.object_id}"
    else:
        _fail(f"unsupported cleanup kind: {candidate.kind}")
    return f"https://api.github.com/repos/{repository}/{suffix}"


def collect_plan(
    repository: str,
    token: str,
    now: datetime,
    *,
    include_all_old_logs: bool = False,
) -> list[CleanupCandidate]:
    """Collect one deterministic cleanup plan from current repository state."""

    caches = _list_paginated(repository, "actions/caches", "actions_caches", token)
    artifacts = _list_paginated(repository, "actions/artifacts", "artifacts", token)
    if include_all_old_logs:
        runs = _list_paginated(repository, "actions/runs?status=completed", "workflow_runs", token)
    else:
        lookback_days = max(
            RELEASE_LOG_RETENTION_DAYS + LOG_RETRY_WINDOW_DAYS,
            RELEASE_RUN_RETENTION_DAYS + RUN_LIST_GRACE_DAYS,
        )
        runs = _list_recent_completed_runs(
            repository,
            token,
            start=now.astimezone(UTC) - timedelta(days=lookback_days),
            end=now,
        )
    run_candidates = plan_run_cleanup(runs, now)
    run_candidate_ids = {candidate.object_id for candidate in run_candidates}
    log_candidates = [
        candidate
        for candidate in plan_log_cleanup(runs, now, include_all_old=include_all_old_logs)
        if candidate.object_id not in run_candidate_ids
    ]
    return [
        *plan_cache_cleanup(caches),
        *plan_artifact_cleanup(artifacts, now),
        *log_candidates,
        *run_candidates,
    ]


def main(argv: list[str] | None = None) -> int:
    """Run the Actions cleanup CLI with dry-run as the safe default."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--include-all-old-logs",
        action="store_true",
        help="include historical logs outside the scheduled retry window",
    )
    args = parser.parse_args(argv)
    try:
        if REPOSITORY_RE.fullmatch(args.repository) is None:
            _fail("repository must use the owner/name form")
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not token:
            _fail("GITHUB_TOKEN is required")
        plan = collect_plan(
            args.repository,
            token,
            datetime.now(UTC),
            include_all_old_logs=args.include_all_old_logs,
        )
        known_bytes = sum(candidate.size_bytes for candidate in plan)
        print(
            f"Actions cleanup plan: {len(plan)} object(s), "
            f"{known_bytes} known byte(s); execute={args.execute}"
        )
        for candidate in plan:
            print(
                f"- {candidate.kind} {candidate.object_id}: {candidate.name} "
                f"({candidate.reason}, {candidate.size_bytes} byte(s))"
            )
        if args.execute:
            deleted = 0
            already_absent = 0
            for candidate in plan:
                if _delete(cleanup_url(args.repository, candidate), token):
                    deleted += 1
                else:
                    already_absent += 1
            print(
                f"Deleted {deleted} Actions storage object(s); {already_absent} were already "
                "absent; only policy-selected completed runs removed their metadata."
            )
        return 0
    except CleanupError as exc:
        print(f"Actions cleanup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
