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
from typing import Any, Literal

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
TARGET_PROTECTION_MODE_VARIABLE = "OCR_GITLAB_TARGET_PROTECTION_MODE"
TargetProtectionMode = Literal["auto", "required", "unprotected"]
TargetProtectionState = Literal["protected", "unprotected"]
MergeRequestState = Literal["opened", "merged", "closed"]


class GitLabProviderError(ValueError):
    """Report unavailable or unsafe GitLab review identity."""


@dataclass(frozen=True, slots=True)
class GitLabMergeRequestLifecycle:
    """Bind one closed GitLab lifecycle state to exact review identities."""

    project_id: str
    merge_request_iid: str
    source_sha: str
    state: MergeRequestState


class GitLabMergeRequestTerminal(GitLabProviderError):
    """Report a valid reviewed MR that reached a terminal lifecycle state."""

    def __init__(self, lifecycle: GitLabMergeRequestLifecycle) -> None:
        super().__init__(f"GitLab merge request is already {lifecycle.state}")
        self.lifecycle = lifecycle


class GitLabMergeRequestStale(GitLabProviderError):
    """The current MR head differs from the revision this run was assigned."""

    def __init__(self, project_id: str, merge_request_iid: str) -> None:
        super().__init__("GitLab merge-request head does not match the reviewed head")
        self.project_id = project_id
        self.merge_request_iid = merge_request_iid


@dataclass(frozen=True, slots=True)
class GitLabReviewSnapshot:
    """Bind code, diff, and policy authority to one authenticated MR snapshot."""

    project_id: str
    merge_request_iid: str
    source_sha: str
    target_branch: str
    target_sha: str
    target_protection: TargetProtectionState
    policy_branch: str
    policy_sha: str
    policy_protection: TargetProtectionState
    protection_mode: TargetProtectionMode
    diff_base_sha: str
    diff_start_sha: str
    diff_head_sha: str
    diff_version_id: int
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
        or int(value) <= 0
        or str(int(value)) != value
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
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise GitLabProviderError("GitLab review metadata is not valid bounded JSON") from exc


def _sha(value: object, label: str) -> str:
    """Return one exact lowercase Git SHA-1 identity."""

    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise GitLabProviderError(f"GitLab returned invalid {label}")
    return value


def _positive_identifier(value: object, label: str) -> int:
    """Return one positive provider identity without accepting coercive values."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or len(str(value)) > MAX_CI_IDENTIFIER_CHARS
    ):
        raise GitLabProviderError(f"GitLab returned invalid {label}")
    return value


def parse_merge_request_lifecycle(
    value: object,
    *,
    expected_project_id: str,
    expected_merge_request_iid: str,
    expected_head: str,
) -> GitLabMergeRequestLifecycle:
    """Hostile-parse exact MR identity before accepting its closed lifecycle state."""

    expected_head = _sha(expected_head, "reviewed source head")
    if (
        not expected_project_id.isascii()
        or not expected_project_id.isdecimal()
        or not 1 <= len(expected_project_id) <= MAX_CI_IDENTIFIER_CHARS
        or int(expected_project_id) <= 0
        or str(int(expected_project_id)) != expected_project_id
    ):
        raise GitLabProviderError("expected GitLab project id is invalid")
    if (
        not expected_merge_request_iid.isascii()
        or not expected_merge_request_iid.isdecimal()
        or not 1 <= len(expected_merge_request_iid) <= MAX_CI_IDENTIFIER_CHARS
        or int(expected_merge_request_iid) <= 0
        or str(int(expected_merge_request_iid)) != expected_merge_request_iid
    ):
        raise GitLabProviderError("expected GitLab merge-request iid is invalid")
    if not isinstance(value, dict):
        raise GitLabProviderError("GitLab merge-request metadata must be an object")
    project_id = _positive_identifier(value.get("target_project_id"), "target project id")
    source_project_id = _positive_identifier(value.get("source_project_id"), "source project id")
    merge_request_iid = _positive_identifier(value.get("iid"), "merge-request iid")
    source_sha = _sha(value.get("sha"), "merge-request source head")
    state = value.get("state")
    if str(project_id) != expected_project_id:
        raise GitLabProviderError("GitLab merge request targets a different project")
    if str(source_project_id) != expected_project_id:
        raise GitLabProviderError("GitLab merge request source belongs to a different project")
    if str(merge_request_iid) != expected_merge_request_iid:
        raise GitLabProviderError("GitLab returned a different merge request")
    if source_sha != expected_head:
        raise GitLabMergeRequestStale(expected_project_id, expected_merge_request_iid)
    if state not in {"opened", "merged", "closed"}:
        raise GitLabProviderError("GitLab returned an invalid merge-request lifecycle state")
    return GitLabMergeRequestLifecycle(
        project_id=expected_project_id,
        merge_request_iid=expected_merge_request_iid,
        source_sha=source_sha,
        state=state,
    )


def parse_target_protection_mode(raw: str | None) -> TargetProtectionMode:
    """Parse the exact fail-closed target-protection policy setting."""

    if raw is None:
        return "auto"
    if raw == "auto":
        return "auto"
    if raw == "required":
        return "required"
    if raw == "unprotected":
        return "unprotected"
    raise GitLabProviderError(
        f"{TARGET_PROTECTION_MODE_VARIABLE} must be exactly 'auto', 'required', or 'unprotected'"
    )


def _branch(value: object, *, label: str = "target") -> str:
    """Return one bounded Git branch name for URL-encoded endpoint construction."""

    if not isinstance(value, str):
        raise GitLabProviderError(f"GitLab returned an invalid {label} branch")
    try:
        byte_length = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise GitLabProviderError(f"GitLab returned an invalid {label} branch") from exc
    if (
        not 1 <= len(value) <= 512
        or byte_length > 2_048
        or value == "@"
        or value.startswith("-")
        or value.endswith(("/", "."))
        or ".." in value
        or "@{" in value
        or any(
            character == "\x7f" or ord(character) < 32 or character in " ~^:?*[\\"
            for character in value
        )
        or any(
            not part or part.startswith(".") or part.endswith(".lock") for part in value.split("/")
        )
    ):
        raise GitLabProviderError(f"GitLab returned an invalid {label} branch")
    return value


def _current_diff_identity(
    mr: dict[str, object],
    *,
    api_root: str,
    project: str,
    merge_request_iid: str,
    token: str,
    deadline: float,
    source_sha: str,
) -> tuple[str, str, str, int]:
    """Bind current MR diff refs to its current authenticated version."""

    refs = mr.get("diff_refs")
    if refs is None:
        raise GitLabProviderError(
            "GitLab current merge-request diff refs are unavailable or pending"
        )
    if not isinstance(refs, dict):
        raise GitLabProviderError("GitLab current merge-request diff refs are malformed")
    try:
        base_sha = _sha(refs.get("base_sha"), "current diff base")
        start_sha = _sha(refs.get("start_sha"), "current diff start")
        head_sha = _sha(refs.get("head_sha"), "current diff head")
    except GitLabProviderError as exc:
        raise GitLabProviderError("GitLab current merge-request diff refs are malformed") from exc
    if head_sha != source_sha:
        raise GitLabProviderError(
            "GitLab current merge-request diff head contradicts its source head"
        )
    versions = _read_json(
        f"{api_root}/projects/{project}/merge_requests/{merge_request_iid}/versions?per_page=1",
        token,
        deadline=deadline,
    )
    if not isinstance(versions, list) or not versions:
        raise GitLabProviderError(
            "GitLab current merge-request diff version is unavailable or pending"
        )
    if len(versions) != 1 or not isinstance(versions[0], dict):
        raise GitLabProviderError("GitLab current merge-request diff version is malformed")
    version = versions[0]
    version_id = _positive_identifier(version.get("id"), "current diff version id")
    try:
        version_refs = (
            _sha(version.get("base_commit_sha"), "current diff version base"),
            _sha(version.get("start_commit_sha"), "current diff version start"),
            _sha(version.get("head_commit_sha"), "current diff version head"),
        )
    except GitLabProviderError as exc:
        raise GitLabProviderError("GitLab current merge-request diff version is malformed") from exc
    if version_refs != (base_sha, start_sha, head_sha):
        raise GitLabProviderError("GitLab current merge-request diff version contradicts its refs")
    return base_sha, start_sha, head_sha, version_id


def _branch_snapshot(
    *, api_root: str, project: str, branch_name: str, token: str, deadline: float
) -> tuple[bool, str]:
    """Read a named branch's protected state and immutable head over HTTPS."""

    encoded_branch = urllib.parse.quote(branch_name, safe="")
    branch = _read_json(
        f"{api_root}/projects/{project}/repository/branches/{encoded_branch}",
        token,
        deadline=deadline,
    )
    if not isinstance(branch, dict):
        raise GitLabProviderError("GitLab branch metadata must be an object")
    protected = branch.get("protected")
    if branch.get("name") != branch_name or not isinstance(protected, bool):
        raise GitLabProviderError("GitLab branch protection metadata is invalid")
    commit = branch.get("commit")
    if not isinstance(commit, dict):
        raise GitLabProviderError("GitLab branch has no commit identity")
    return protected, _sha(commit.get("id"), "branch head")


def acquire_review_snapshot(
    environment: Mapping[str, str], *, expected_head: str, include_metadata: bool = True
) -> GitLabReviewSnapshot:
    """Acquire the live MR code tuple and its selected policy authority."""

    expected_head = _sha(expected_head, "reviewed source head")
    protection_mode = parse_target_protection_mode(environment.get(TARGET_PROTECTION_MODE_VARIABLE))
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
    lifecycle = parse_merge_request_lifecycle(
        mr,
        expected_project_id=project_id,
        expected_merge_request_iid=merge_request_iid,
        expected_head=expected_head,
    )
    if lifecycle.state != "opened":
        raise GitLabMergeRequestTerminal(lifecycle)
    source_sha = lifecycle.source_sha
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
    diff_base_sha, diff_start_sha, diff_head_sha, diff_version_id = _current_diff_identity(
        mr,
        api_root=api_root,
        project=project,
        merge_request_iid=merge_request_iid,
        token=token,
        deadline=deadline,
        source_sha=source_sha,
    )
    protected, target_sha = _branch_snapshot(
        api_root=api_root,
        project=project,
        branch_name=target_branch,
        token=token,
        deadline=deadline,
    )
    if not protected and protection_mode != "unprotected":
        if protection_mode == "required":
            raise GitLabProviderError("GitLab target branch is not the captured protected branch")
        project_metadata = _read_json(
            f"{api_root}/projects/{project}",
            token,
            deadline=deadline,
        )
        if not isinstance(project_metadata, dict):
            raise GitLabProviderError("GitLab project metadata must be an object")
        if _positive_identifier(project_metadata.get("id"), "project id") != int(project_id):
            raise GitLabProviderError("GitLab project metadata belongs to a different project")
        policy_branch = _branch(project_metadata.get("default_branch"), label="default")
        policy_protected, policy_sha = _branch_snapshot(
            api_root=api_root,
            project=project,
            branch_name=policy_branch,
            token=token,
            deadline=deadline,
        )
        if not policy_protected:
            raise GitLabProviderError("GitLab default branch is not protected policy authority")
    else:
        policy_branch = target_branch
        policy_sha = target_sha
        policy_protected = protected
    return GitLabReviewSnapshot(
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        target_branch=target_branch,
        target_sha=target_sha,
        target_protection="protected" if protected else "unprotected",
        policy_branch=policy_branch,
        policy_sha=policy_sha,
        policy_protection="protected" if policy_protected else "unprotected",
        protection_mode=protection_mode,
        diff_base_sha=diff_base_sha,
        diff_start_sha=diff_start_sha,
        diff_head_sha=diff_head_sha,
        diff_version_id=diff_version_id,
        author_id=author_id,
        context=context,
    )
