"""Acquire stable bounded GitLab discussion snapshots as untrusted context."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ocr_toolkit.context.contracts import DiscussionPolicy
from ocr_toolkit.context.dlp import check_text, normalize_text
from ocr_toolkit.providers.gitlab import GitLabProviderError, _api_root, _numeric_identifier

MAX_PAGE_BYTES = 512 * 1024
MAX_PAGES = 10
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


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


def _timestamp(value: object) -> int | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return int(parsed.astimezone(timezone.utc).timestamp())


def _author_class(
    note: Mapping[str, object], author: Mapping[str, object], *, toolkit_bot_id: int | None
) -> tuple[str, int] | None:
    author_id = author.get("id")
    if not isinstance(author_id, int) or isinstance(author_id, bool) or author_id <= 0:
        return None
    if note.get("system") is True:
        return "system", author_id
    if toolkit_bot_id is not None and author_id == toolkit_bot_id:
        return "toolkit_bot", author_id
    if author.get("bot") is True:
        return "automation", author_id
    if author.get("state") in {None, "active", "blocked"} and author.get("bot") in {None, False}:
        return "user", author_id
    return None


def _anchor(position: object, *, source_sha: str) -> tuple[Mapping[str, object], bool, bool]:
    if position is None:
        return {}, False, False
    if not isinstance(position, Mapping):
        return {}, False, True
    result: dict[str, object] = {}
    path = position.get("new_path") or position.get("old_path")
    normalized = normalize_text(path)
    if normalized and len(normalized) <= 512 and len(normalized.encode()) <= 2_048:
        result["path"] = normalized
    line = position.get("new_line") or position.get("old_line")
    if isinstance(line, int) and not isinstance(line, bool) and 0 < line <= 10_000_000:
        result["line"] = line
    head_sha = position.get("head_sha")
    if head_sha is not None and (
        not isinstance(head_sha, str) or SHA_RE.fullmatch(head_sha) is None
    ):
        return {}, False, True
    outdated = isinstance(head_sha, str) and head_sha != source_sha
    return result, outdated, bool(position.get("position_type") == "text" and not result)


def _snapshot_once(
    environment: Mapping[str, str],
    *,
    project_id: str,
    merge_request_iid: str,
    source_sha: str,
    run_id: str,
    policy: DiscussionPolicy,
    now: int,
    deadline: float,
    forbidden: tuple[str, ...],
) -> DiscussionSnapshot:
    token = environment.get("GITLAB_API_TOKEN", "").strip()
    api_root = _api_root(environment)
    project = urllib.parse.quote(project_id, safe="")
    pages: list[object] = []
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
        if int(next_page) <= int(page):
            raise GitLabProviderError("GitLab discussion pagination did not advance")
        page = next_page
    else:
        raise GitLabProviderError("GitLab discussions exceed the page limit")
    toolkit_raw = environment.get("OCR_GITLAB_BOT_USER_ID", "").strip()
    toolkit_bot_id = int(toolkit_raw) if toolkit_raw.isdecimal() and int(toolkit_raw) > 0 else None
    records: list[DiscussionRecord] = []
    omitted = 0
    total_chars = total_bytes = total_lines = 0
    for thread_index, thread in enumerate(pages):
        if thread_index >= policy.max_threads:
            omitted += len(pages) - thread_index
            break
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
                _author_class(note, author, toolkit_bot_id=toolkit_bot_id)
                if isinstance(author, Mapping)
                else None
            )
            if classified is None or classified[0] not in policy.account_classes:
                omitted += 1
                continue
            created_at, updated_at = (
                _timestamp(note.get("created_at")),
                _timestamp(note.get("updated_at")),
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
            anchor, outdated, anchor_invalid = _anchor(note.get("position"), source_sha=source_sha)
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
            pseudonym = (
                "actor-"
                + hashlib.sha256(f"{run_id}:{account_class}:{author_id}".encode()).hexdigest()[:16]
            )
            version = str(updated_at)
            value = {
                "thread": thread_index,
                "reply": reply_index,
                "author_class": account_class,
                "author_pseudonym": pseudonym,
                "body": checked.text,
                "created_at": created_at,
                "updated_at": updated_at,
                "resolved": resolved,
                "outdated": outdated,
                "anchor": dict(anchor),
                "version": version,
            }
            digest = hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            records.append(DiscussionRecord(digest=digest, **value))
    state = "partial" if omitted else "complete"
    snapshot_body = {
        "project_id": project_id,
        "merge_request_iid": merge_request_iid,
        "source_sha": source_sha,
        "state": state,
        "omitted": omitted,
        "records": [record.digest for record in records],
    }
    digest = hashlib.sha256(
        json.dumps(snapshot_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DiscussionSnapshot(state=state, records=tuple(records), digest=digest, omitted=omitted)


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
    """Accept only two identical bounded ordered snapshots of the validated MR."""

    if (
        project_id != _numeric_identifier(environment, "CI_PROJECT_ID")
        or merge_request_iid != _numeric_identifier(environment, "CI_MERGE_REQUEST_IID")
        or SHA_RE.fullmatch(source_sha) is None
    ):
        raise GitLabProviderError("GitLab discussion identity is invalid")
    acquisition_deadline = (
        time.monotonic() + min(30.0, max(0.1, policy.max_items / 10))
        if deadline is None
        else deadline
    )
    first = _snapshot_once(
        environment,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        run_id=run_id,
        policy=policy,
        now=now,
        deadline=acquisition_deadline,
        forbidden=forbidden,
    )
    second = _snapshot_once(
        environment,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        run_id=run_id,
        policy=policy,
        now=now,
        deadline=acquisition_deadline,
        forbidden=forbidden,
    )
    if first.digest != second.digest:
        return DiscussionSnapshot(state="mutated", records=(), digest=second.digest, omitted=0)
    return second
