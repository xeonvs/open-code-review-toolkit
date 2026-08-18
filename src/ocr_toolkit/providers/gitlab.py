"""Acquire bounded GitLab review identity and normalize invocation identifiers."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.evidence.invocation import MAX_CI_IDENTIFIER_CHARS, InvocationIdentifier
from ocr_toolkit.evidence.review_context import (
    MergeRequestContext,
    normalize_merge_request_context,
)

CI_IDENTIFIER_FIELDS = (
    ("CI_PROJECT_ID", "project_id"),
    ("CI_PIPELINE_ID", "pipeline_id"),
    ("CI_JOB_ID", "job_id"),
    ("CI_MERGE_REQUEST_IID", "merge_request_iid"),
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_PROVIDER_BODY_BYTES = 2_000_000
PROVIDER_READ_CHUNK_BYTES = 64 * 1024
PROVIDER_TIMEOUT_SECONDS = 30


class GitLabProviderError(ValueError):
    """Report unavailable or unsafe GitLab review identity."""


@dataclass(frozen=True, slots=True)
class GitLabReviewSnapshot:
    """Bind one reviewed source head to the current protected target commit."""

    project_id: str
    merge_request_iid: str
    source_sha: str
    target_branch: str
    target_sha: str
    author_id: int
    context: MergeRequestContext | None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward the provider credential through a redirect."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


URL_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _set_response_timeout(response: Any, timeout: float) -> None:
    """Best-effort bind each socket read to the shared acquisition deadline."""

    try:
        socket = response.fp.raw._sock
    except AttributeError:
        return
    socket.settimeout(timeout)


def invocation_identifiers(environment: Mapping[str, str]) -> tuple[InvocationIdentifier, ...]:
    """Return only explicitly allowlisted GitLab numeric identifiers."""

    identifiers = []
    for variable, field in CI_IDENTIFIER_FIELDS:
        value = environment.get(variable, "").strip()
        if (
            not value
            or len(value) > MAX_CI_IDENTIFIER_CHARS
            or not value.isascii()
            or not value.isdecimal()
        ):
            continue
        identifiers.append(
            InvocationIdentifier(
                provider="gitlab",
                field=field,
                value=value,
                provenance=f"gitlab.environment:{variable}",
            )
        )
    return tuple(identifiers)


def is_merge_request_environment(environment: Mapping[str, str]) -> bool:
    """Return whether the process declares a GitLab merge-request invocation."""

    return bool(environment.get("CI_MERGE_REQUEST_IID", "").strip())


def _numeric_identifier(environment: Mapping[str, str], name: str) -> str:
    """Return one required bounded decimal CI identifier."""

    value = environment.get(name, "").strip()
    if (
        not value
        or len(value) > MAX_CI_IDENTIFIER_CHARS
        or not value.isascii()
        or not value.isdecimal()
    ):
        raise GitLabProviderError(f"{name} must be a bounded decimal identifier")
    return value


def _api_root(environment: Mapping[str, str]) -> str:
    """Return one closed HTTPS GitLab API root without credentials or fragments."""

    raw = environment.get("CI_API_V4_URL", "").strip()
    if not raw:
        server = environment.get("CI_SERVER_URL", "").strip().rstrip("/")
        if not server:
            raise GitLabProviderError("CI_API_V4_URL or CI_SERVER_URL is required")
        raw = f"{server}/api/v4"
    raw = raw.rstrip("/")
    try:
        parsed = urllib.parse.urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise GitLabProviderError("GitLab API root must be an absolute HTTPS URL") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or (port is None and parsed.netloc.endswith(":"))
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith("/api/v4")
    ):
        raise GitLabProviderError("GitLab API root must be an absolute /api/v4 HTTPS URL")
    return raw


def _read_json(url: str, token: str, *, deadline: float) -> object:
    """Read one complete bounded provider response without redirects or retries."""

    if not token or "\r" in token or "\n" in token or len(token) > 16_384:
        raise GitLabProviderError("GITLAB_API_TOKEN is missing or malformed")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise GitLabProviderError("GitLab review snapshot acquisition timed out")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "PRIVATE-TOKEN": token,
            "User-Agent": "open-code-review-toolkit-provider/1",
        },
        method="GET",
    )
    try:
        with URL_OPENER.open(request, timeout=remaining) as response:
            chunks: list[bytes] = []
            size = 0
            while size < MAX_PROVIDER_BODY_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                _set_response_timeout(response, remaining)
                chunk = response.read(
                    min(PROVIDER_READ_CHUNK_BYTES, MAX_PROVIDER_BODY_BYTES - size)
                )
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size >= MAX_PROVIDER_BODY_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                _set_response_timeout(response, remaining)
                if response.read(1):
                    raise GitLabProviderError("GitLab review metadata exceeds the byte limit")
    except urllib.error.HTTPError as exc:
        raise GitLabProviderError(
            f"GitLab review metadata request failed with HTTP {exc.code}"
        ) from exc
    except (TimeoutError, OSError, urllib.error.URLError) as exc:
        raise GitLabProviderError("GitLab review metadata request failed") from exc
    try:
        return json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GitLabProviderError("GitLab review metadata is not valid bounded JSON") from exc


def _sha(value: object, label: str) -> str:
    """Return one exact lowercase Git SHA-1 identity."""

    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise GitLabProviderError(f"GitLab returned invalid {label}")
    return value


def _positive_identifier(value: object, label: str) -> int:
    """Return one positive provider identity without accepting coercive values."""

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitLabProviderError(f"GitLab returned invalid {label}")
    return value


def _branch(value: object) -> str:
    """Return one bounded safe target branch name for endpoint construction."""

    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 512
        or len(value.encode("utf-8")) > 2_048
        or any(character == "\x7f" or ord(character) < 32 for character in value)
    ):
        raise GitLabProviderError("GitLab returned an invalid target branch")
    return value


def acquire_review_snapshot(
    environment: Mapping[str, str], *, expected_head: str, include_metadata: bool = True
) -> GitLabReviewSnapshot:
    """Acquire and cross-check one MR plus protected-target branch snapshot."""

    expected_head = _sha(expected_head, "reviewed source head")
    project_id = _numeric_identifier(environment, "CI_PROJECT_ID")
    merge_request_iid = _numeric_identifier(environment, "CI_MERGE_REQUEST_IID")
    token = environment.get("GITLAB_API_TOKEN", "").strip()
    api_root = _api_root(environment)
    project = urllib.parse.quote(project_id, safe="")
    deadline = time.monotonic() + PROVIDER_TIMEOUT_SECONDS
    mr = _read_json(
        f"{api_root}/projects/{project}/merge_requests/{merge_request_iid}",
        token,
        deadline=deadline,
    )
    if not isinstance(mr, dict):
        raise GitLabProviderError("GitLab merge-request metadata must be an object")
    if mr.get("state") != "opened":
        raise GitLabProviderError("GitLab merge request is not open")
    source_sha = _sha(mr.get("sha"), "merge-request source head")
    if source_sha != expected_head:
        raise GitLabProviderError("GitLab merge-request head does not match the reviewed head")
    target_project = mr.get("target_project_id")
    if isinstance(target_project, bool) or str(target_project) != project_id:
        raise GitLabProviderError("GitLab merge request targets a different project")
    target_branch = _branch(mr.get("target_branch"))
    author = mr.get("author")
    if not isinstance(author, dict):
        raise GitLabProviderError("GitLab returned invalid merge-request author")
    author_id = _positive_identifier(author.get("id"), "merge-request author id")
    context = None
    if include_metadata:
        context = normalize_merge_request_context(
            provider="gitlab",
            project_id=project_id,
            merge_request_iid=merge_request_iid,
            source_sha=source_sha,
            title=mr.get("title"),
            description=mr.get("description"),
            labels=mr.get("labels"),
            source_branch=mr.get("source_branch"),
        )
    encoded_branch = urllib.parse.quote(target_branch, safe="")
    branch = _read_json(
        f"{api_root}/projects/{project}/repository/branches/{encoded_branch}",
        token,
        deadline=deadline,
    )
    if not isinstance(branch, dict):
        raise GitLabProviderError("GitLab target-branch metadata must be an object")
    if branch.get("name") != target_branch or branch.get("protected") is not True:
        raise GitLabProviderError("GitLab target branch is not the captured protected branch")
    commit = branch.get("commit")
    if not isinstance(commit, dict):
        raise GitLabProviderError("GitLab target branch has no commit identity")
    target_sha = _sha(commit.get("id"), "protected target head")
    return GitLabReviewSnapshot(
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        target_branch=target_branch,
        target_sha=target_sha,
        author_id=author_id,
        context=context,
    )
