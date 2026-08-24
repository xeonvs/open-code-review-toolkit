"""Acquire stable bounded GitLab discussion snapshots as untrusted context."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.context.contracts import DiscussionPolicy, RemediationThreadPolicy
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.providers.gitlab import GitLabProviderError, _api_root, _numeric_identifier
from ocr_toolkit.providers.gitlab_context import (
    SHA_RE,
    RawGitLabSnapshot,
    anchor,
    author_class,
    pseudonym,
    timestamp,
)
from ocr_toolkit.providers.gitlab_identity import (
    GitLabIdentityError,
    fetch_current_user_identity,
)
from ocr_toolkit.providers.gitlab_remediation import (
    RemediationSnapshot,
    project_remediation_threads,
)

MAX_PAGE_BYTES = 512 * 1024
MAX_PAGES = 10


@dataclass(frozen=True, slots=True)
class DiscussionRecord:
    """Represent one provider-normalized reply without display identity."""

    thread: int
    reply: int
    author_class: str
    author_pseudonym: str
    body: str
    created_at: int
    updated_at: int
    resolved: bool
    outdated: bool
    anchor: Mapping[str, object]
    version: str
    digest: str


@dataclass(frozen=True, slots=True)
class DiscussionSnapshot:
    """Hold one repeated stable snapshot or a closed degraded state."""

    state: str
    records: tuple[DiscussionRecord, ...]
    digest: str
    omitted: int
    dlp_rejected: int


@dataclass(frozen=True, slots=True)
class GitLabContextSnapshot:
    """Return mutually exclusive projections from one stable provider snapshot."""

    discussions: DiscussionSnapshot | None
    remediation_threads: RemediationSnapshot | None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GitLabProviderError("GitLab discussions contain a duplicate JSON key")
        result[key] = value
    return result


def _read_page(url: str, token: str, *, deadline: float) -> tuple[object, str]:
    if not token or "\r" in token or "\n" in token or len(token) > 16_384:
        raise GitLabProviderError("GITLAB_API_TOKEN is missing or malformed")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise GitLabProviderError("GitLab discussion acquisition timed out")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "PRIVATE-TOKEN": token,
            "User-Agent": "open-code-review-toolkit-discussions/1",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler)
    try:
        with opener.open(request, timeout=remaining) as response:
            if response.headers.get_content_type() != "application/json":
                raise GitLabProviderError("GitLab discussions content type is invalid")
            raw = response.read(MAX_PAGE_BYTES + 1)
            if len(raw) > MAX_PAGE_BYTES:
                raise GitLabProviderError("GitLab discussions page exceeds its byte limit")
            next_page = response.headers.get("X-Next-Page", "")
    except urllib.error.HTTPError as exc:
        raise GitLabProviderError("GitLab discussions are unavailable") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise GitLabProviderError("GitLab discussion request failed") from exc
    if next_page and (not next_page.isascii() or not next_page.isdecimal() or len(next_page) > 4):
        raise GitLabProviderError("GitLab discussion pagination is invalid")
    try:
        return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs), next_page
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GitLabProviderError("GitLab discussions are not valid bounded JSON") from exc


def _read_raw_snapshot(
    environment: Mapping[str, str],
    *,
    project_id: str,
    merge_request_iid: str,
    max_threads: int,
    deadline: float,
) -> RawGitLabSnapshot:
    token = environment.get("GITLAB_API_TOKEN", "").strip()
    api_root = _api_root(environment)
    try:
        identity = fetch_current_user_identity(
            api_root,
            lambda url: _read_page(url, token, deadline=deadline)[0],
        )
    except GitLabIdentityError as exc:
        raise GitLabProviderError("authenticated GitLab identity is unavailable") from exc
    project = urllib.parse.quote(project_id, safe="")
    pages: list[object] = []
    unfetched = 0
    page = "1"
    for _ in range(MAX_PAGES):
        payload, next_page = _read_page(
            f"{api_root}/projects/{project}/merge_requests/{merge_request_iid}/discussions"
            f"?per_page=100&page={page}",
            token,
            deadline=deadline,
        )
        if not isinstance(payload, list) or len(payload) > 100:
            raise GitLabProviderError("GitLab discussion page shape is invalid")
        pages.extend(payload)
        if not next_page:
            break
        if len(pages) >= max_threads:
            # The provider proves at least one more page exists. The policy does
            # not authorize fetching it once the admitted thread bound is full.
            unfetched = 1
            break
        if int(next_page) <= int(page):
            raise GitLabProviderError("GitLab discussion pagination did not advance")
        page = next_page
    else:
        raise GitLabProviderError("GitLab discussions exceed the page limit")
    raw_body = {
        "identity": {"id": identity.user_id, "username": identity.username},
        "pagination_omitted": unfetched,
        "threads": pages,
    }
    digest = hashlib.sha256(
        json.dumps(raw_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RawGitLabSnapshot(
        identity=identity,
        threads=tuple(pages),
        pagination_omitted=unfetched,
        digest=digest,
    )


def _project_discussions(
    raw: RawGitLabSnapshot,
    *,
    source_sha: str,
    run_id: str,
    policy: DiscussionPolicy,
    now: int,
    forbidden: tuple[str, ...],
    excluded_threads: frozenset[int] = frozenset(),
) -> DiscussionSnapshot:
    pages = raw.threads
    toolkit_bot_id = raw.identity.user_id
    records: list[DiscussionRecord] = []
    omitted = raw.pagination_omitted
    dlp_rejected = 0
    total_chars = total_bytes = total_lines = 0
    considered_threads = 0
    for thread_index, thread in enumerate(pages):
        if thread_index in excluded_threads:
            continue
        if considered_threads >= policy.max_threads:
            omitted += sum(
                index not in excluded_threads for index in range(thread_index, len(pages))
            )
            break
        considered_threads += 1
        if not isinstance(thread, Mapping):
            omitted += 1
            continue
        notes = thread.get("notes")
        if not isinstance(notes, list):
            omitted += 1
            continue
        for reply_index, note in enumerate(notes):
            if reply_index >= policy.max_replies_per_thread or len(records) >= policy.max_items:
                omitted += max(1, len(notes) - reply_index)
                break
            if not isinstance(note, Mapping) or note.get("type") not in {
                None,
                "DiffNote",
                "DiscussionNote",
            }:
                omitted += 1
                continue
            author = note.get("author")
            classified = (
                author_class(note, author, toolkit_bot_id=toolkit_bot_id)
                if isinstance(author, Mapping)
                else None
            )
            if classified is None or classified[0] not in policy.account_classes:
                omitted += 1
                continue
            created_at, updated_at = (
                timestamp(note.get("created_at")),
                timestamp(note.get("updated_at")),
            )
            if (
                created_at is None
                or updated_at is None
                or created_at < 0
                or updated_at < created_at
                or updated_at > now + 300
            ):
                omitted += 1
                continue
            if policy.max_age_seconds and now - updated_at > policy.max_age_seconds:
                omitted += 1
                continue
            resolved = note.get("resolved") is True
            note_anchor, outdated, anchor_invalid = anchor(
                note.get("position"), source_sha=source_sha
            )
            if (
                anchor_invalid
                or (resolved and not policy.include_resolved)
                or (outdated and not policy.include_outdated)
            ):
                omitted += 1
                continue
            checked = check_text(note.get("body"), budgets=policy.budgets, forbidden=forbidden)
            if not checked.admitted or checked.text is None:
                omitted += 1
                dlp_rejected += int(checked.reason != "limit")
                continue
            body_chars = len(checked.text)
            body_bytes = len(checked.text.encode())
            body_lines = checked.text.count("\n") + 1
            if (
                total_chars + body_chars > policy.budgets.max_chars
                or total_bytes + body_bytes > policy.budgets.max_bytes
                or total_lines + body_lines > policy.budgets.max_lines
            ):
                omitted += 1
                continue
            total_chars += body_chars
            total_bytes += body_bytes
            total_lines += body_lines
            account_class, author_id = classified
            actor_pseudonym = pseudonym(run_id, account_class, author_id)
            version = str(updated_at)
            value = {
                "thread": thread_index,
                "reply": reply_index,
                "author_class": account_class,
                "author_pseudonym": actor_pseudonym,
                "body": checked.text,
                "created_at": created_at,
                "updated_at": updated_at,
                "resolved": resolved,
                "outdated": outdated,
                "anchor": dict(note_anchor),
                "version": version,
            }
            digest = hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            records.append(DiscussionRecord(digest=digest, **value))
    state = "partial" if omitted else "complete"
    snapshot_body = {
        "raw_digest": raw.digest,
        "source_sha": source_sha,
        "state": state,
        "omitted": omitted,
        "dlp_rejected": dlp_rejected,
        "records": [record.digest for record in records],
    }
    digest = hashlib.sha256(
        json.dumps(snapshot_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DiscussionSnapshot(
        state=state,
        records=tuple(records),
        digest=digest,
        omitted=omitted,
        dlp_rejected=dlp_rejected,
    )


def acquire_gitlab_context(
    environment: Mapping[str, str],
    *,
    project_id: str,
    merge_request_iid: str,
    source_sha: str,
    run_id: str,
    discussion_policy: DiscussionPolicy | None,
    remediation_policy: RemediationThreadPolicy | None,
    now: int,
    deadline: float | None = None,
    forbidden: tuple[str, ...] = (),
) -> GitLabContextSnapshot:
    """Project one twice-read stable bounded GitLab snapshot without duplication."""

    if (
        project_id != _numeric_identifier(environment, "CI_PROJECT_ID")
        or merge_request_iid != _numeric_identifier(environment, "CI_MERGE_REQUEST_IID")
        or SHA_RE.fullmatch(source_sha) is None
        or (discussion_policy is None and remediation_policy is None)
    ):
        raise GitLabProviderError("GitLab discussion identity is invalid")
    policies = tuple(
        policy for policy in (discussion_policy, remediation_policy) if policy is not None
    )
    max_threads = max(policy.max_threads for policy in policies)
    max_items = max(policy.max_items for policy in policies)
    acquisition_deadline = (
        time.monotonic() + min(30.0, max(0.1, max_items / 10)) if deadline is None else deadline
    )
    first = _read_raw_snapshot(
        environment,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        max_threads=max_threads,
        deadline=acquisition_deadline,
    )
    second = _read_raw_snapshot(
        environment,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        max_threads=max_threads,
        deadline=acquisition_deadline,
    )
    if first.digest != second.digest:
        return GitLabContextSnapshot(
            discussions=(
                DiscussionSnapshot(
                    state="mutated",
                    records=(),
                    digest=second.digest,
                    omitted=0,
                    dlp_rejected=0,
                )
                if discussion_policy is not None
                else None
            ),
            remediation_threads=(
                RemediationSnapshot(
                    state="mutated",
                    records=(),
                    digest=second.digest,
                    omitted=0,
                    dlp_rejected=0,
                )
                if remediation_policy is not None
                else None
            ),
        )
    remediation: RemediationSnapshot | None = None
    excluded_threads: frozenset[int] = frozenset()
    if remediation_policy is not None:
        remediation, excluded_threads = project_remediation_threads(
            second,
            source_sha=source_sha,
            run_id=run_id,
            policy=remediation_policy,
            now=now,
            forbidden=forbidden,
        )
    discussions = (
        _project_discussions(
            second,
            source_sha=source_sha,
            run_id=run_id,
            policy=discussion_policy,
            now=now,
            forbidden=forbidden,
            excluded_threads=excluded_threads,
        )
        if discussion_policy is not None
        else None
    )
    return GitLabContextSnapshot(
        discussions=discussions,
        remediation_threads=remediation,
    )


def acquire_discussions(
    environment: Mapping[str, str],
    *,
    project_id: str,
    merge_request_iid: str,
    source_sha: str,
    run_id: str,
    policy: DiscussionPolicy,
    now: int,
    deadline: float | None = None,
    forbidden: tuple[str, ...] = (),
) -> DiscussionSnapshot:
    """Compatibility entry point for the generic discussion-only source."""

    result = acquire_gitlab_context(
        environment,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        run_id=run_id,
        discussion_policy=policy,
        remediation_policy=None,
        now=now,
        deadline=deadline,
        forbidden=forbidden,
    )
    assert result.discussions is not None
    return result.discussions
