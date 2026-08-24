"""Project verified toolkit-owned GitLab remediation threads."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from ocr_toolkit.context.contracts import RemediationThreadPolicy
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.posting.markers import (
    FINGERPRINT_LEN,
    WRITE_MARKER_RE,
    fingerprint_from_marker,
    reviewer_command_from_body,
)
from ocr_toolkit.providers.gitlab import GitLabProviderError
from ocr_toolkit.providers.gitlab_context import (
    RawGitLabSnapshot,
    anchor,
    author_class,
    pseudonym,
    timestamp,
)
from ocr_toolkit.providers.gitlab_identity import GitLabUserIdentity


@dataclass(frozen=True, slots=True)
class RemediationReply:
    """Represent one ordered DLP-admitted remediation reply."""

    order: int
    author_class: str
    author_pseudonym: str
    body: str
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class RemediationThreadRecord:
    """Represent one verified toolkit root and its admitted replies."""

    thread: int
    root_author_pseudonym: str
    root_body: str
    anchor_state: str
    replies: tuple[RemediationReply, ...]
    completeness: str
    resolved_count: int
    outdated_count: int
    version: str
    digest: str


@dataclass(frozen=True, slots=True)
class RemediationSnapshot:
    """Hold fixed remediation bundles or one closed degradation state."""

    state: str
    records: tuple[RemediationThreadRecord, ...]
    digest: str
    omitted: int
    dlp_rejected: int


def _toolkit_root(
    thread: object, identity: GitLabUserIdentity
) -> tuple[Mapping[str, object], str] | None:
    if not isinstance(thread, Mapping):
        return None
    notes = thread.get("notes")
    if not isinstance(notes, list) or not notes or not isinstance(notes[0], Mapping):
        return None
    root = notes[0]
    if root.get("system") is True or root.get("type") not in {None, "DiffNote", "DiscussionNote"}:
        return None
    author = root.get("author")
    classified = (
        author_class(root, author, toolkit_bot_id=identity.user_id)
        if isinstance(author, Mapping)
        else None
    )
    body = root.get("body")
    fingerprint = fingerprint_from_marker(body) if isinstance(body, str) else None
    if (
        classified is None
        or classified[0] != "toolkit_bot"
        or fingerprint is None
        or len(fingerprint) != FINGERPRINT_LEN
    ):
        return None
    return root, fingerprint


def _visible_root_text(body: str) -> str:
    lines = body.splitlines()
    visible = lines[1:]
    if visible and WRITE_MARKER_RE.fullmatch(visible[0]) is not None:
        visible = visible[1:]
    return "\n".join(visible).strip()


def project_remediation_threads(
    raw: RawGitLabSnapshot,
    *,
    source_sha: str,
    run_id: str,
    policy: RemediationThreadPolicy,
    now: int,
    forbidden: tuple[str, ...],
) -> tuple[RemediationSnapshot, frozenset[int]]:
    """Return fixed bundles and every verified root excluded from generic projection."""

    records: list[RemediationThreadRecord] = []
    verified_roots = frozenset(
        index
        for index, thread in enumerate(raw.threads)
        if _toolkit_root(thread, raw.identity) is not None
    )
    omitted = raw.pagination_omitted
    dlp_rejected = 0
    total_items = total_chars = total_bytes = total_lines = 0
    considered_threads = 0
    for thread_index, thread in enumerate(raw.threads):
        root_identity = _toolkit_root(thread, raw.identity)
        if root_identity is None:
            continue
        if considered_threads >= policy.max_threads:
            omitted += 1
            continue
        considered_threads += 1
        if not isinstance(thread, Mapping):
            raise GitLabProviderError("verified remediation thread is not an object")
        notes = thread.get("notes")
        if not isinstance(notes, list):
            raise GitLabProviderError("verified remediation thread has no note list")
        root, _fingerprint = root_identity
        created_at = timestamp(root.get("created_at"))
        updated_at = timestamp(root.get("updated_at"))
        root_anchor, outdated, anchor_invalid = anchor(root.get("position"), source_sha=source_sha)
        resolved = root.get("resolved") is True
        body = root.get("body")
        checked_root = check_text(body, budgets=policy.budgets, forbidden=forbidden)
        visible_root = (
            _visible_root_text(checked_root.text)
            if checked_root.admitted and isinstance(checked_root.text, str)
            else ""
        )
        visible_checked = check_text(
            visible_root,
            budgets=policy.budgets,
            forbidden=forbidden,
        )
        root_dlp_rejected = not checked_root.admitted or not visible_checked.admitted
        if (
            created_at is None
            or updated_at is None
            or created_at < 0
            or updated_at < created_at
            or updated_at > now + 300
            or (policy.max_age_seconds and now - updated_at > policy.max_age_seconds)
            or anchor_invalid
            or (resolved and not policy.include_resolved)
            or (outdated and not policy.include_outdated)
            or not visible_checked.admitted
            or not isinstance(visible_checked.text, str)
            or not visible_checked.text
        ):
            omitted += 1
            dlp_rejected += int(root_dlp_rejected)
            continue

        replies: list[RemediationReply] = []
        thread_partial = False
        resolved_count = int(resolved)
        outdated_count = int(outdated)
        reply_values = notes[1:]
        if len(reply_values) > policy.max_replies_per_thread:
            thread_partial = True
            reply_values = reply_values[: policy.max_replies_per_thread]
            omitted += len(notes) - 1 - len(reply_values)
        for reply_index, note in enumerate(reply_values):
            if total_items + 1 + len(replies) >= policy.max_items:
                thread_partial = True
                omitted += len(reply_values) - reply_index
                break
            if not isinstance(note, Mapping) or note.get("type") not in {
                None,
                "DiffNote",
                "DiscussionNote",
            }:
                thread_partial = True
                omitted += 1
                continue
            author = note.get("author")
            classified = (
                author_class(note, author, toolkit_bot_id=raw.identity.user_id)
                if isinstance(author, Mapping)
                else None
            )
            if classified is None or classified[0] not in policy.account_classes:
                thread_partial = True
                omitted += 1
                continue
            note_body = note.get("body")
            if (
                reviewer_command_from_body(note_body, bot_username=raw.identity.username)
                is not None
            ):
                continue
            reply_created = timestamp(note.get("created_at"))
            reply_updated = timestamp(note.get("updated_at"))
            _reply_anchor, reply_outdated, reply_anchor_invalid = anchor(
                note.get("position"), source_sha=source_sha
            )
            reply_resolved = note.get("resolved") is True
            checked = check_text(note_body, budgets=policy.budgets, forbidden=forbidden)
            if (
                reply_created is None
                or reply_updated is None
                or reply_created < 0
                or reply_updated < reply_created
                or reply_updated > now + 300
                or (policy.max_age_seconds and now - reply_updated > policy.max_age_seconds)
                or reply_anchor_invalid
                or (reply_resolved and not policy.include_resolved)
                or (reply_outdated and not policy.include_outdated)
                or not checked.admitted
                or not isinstance(checked.text, str)
            ):
                thread_partial = True
                omitted += 1
                dlp_rejected += int(not checked.admitted)
                continue
            account, author_id = classified
            replies.append(
                RemediationReply(
                    order=len(replies),
                    author_class=account,
                    author_pseudonym=pseudonym(run_id, account, author_id),
                    body=checked.text,
                    created_at=reply_created,
                    updated_at=reply_updated,
                )
            )
            resolved_count += int(reply_resolved)
            outdated_count += int(reply_outdated)
        if not replies:
            continue
        texts = [visible_checked.text, *(reply.body for reply in replies)]
        thread_chars = sum(len(text) for text in texts)
        thread_bytes = sum(len(text.encode()) for text in texts)
        thread_lines = sum(text.count("\n") + 1 for text in texts)
        if (
            total_items + 1 + len(replies) > policy.max_items
            or total_chars + thread_chars > policy.budgets.max_chars
            or total_bytes + thread_bytes > policy.budgets.max_bytes
            or total_lines + thread_lines > policy.budgets.max_lines
        ):
            omitted += 1 + len(replies)
            continue
        total_items += 1 + len(replies)
        total_chars += thread_chars
        total_bytes += thread_bytes
        total_lines += thread_lines
        anchor_state = "outdated" if outdated else ("current" if root_anchor else "unpositioned")
        root_actor = pseudonym(run_id, "toolkit_bot", raw.identity.user_id)
        completeness = "partial" if thread_partial else "complete"
        version = str(max(updated_at, *(reply.updated_at for reply in replies)))
        value = {
            "thread": thread_index,
            "root_author_pseudonym": root_actor,
            "root_body": visible_checked.text,
            "anchor_state": anchor_state,
            "replies": [
                {
                    "order": reply.order,
                    "author_class": reply.author_class,
                    "author_pseudonym": reply.author_pseudonym,
                    "body": reply.body,
                    "created_at": reply.created_at,
                    "updated_at": reply.updated_at,
                }
                for reply in replies
            ],
            "completeness": completeness,
            "resolved_count": resolved_count,
            "outdated_count": outdated_count,
            "version": version,
        }
        digest = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        records.append(
            RemediationThreadRecord(
                thread=thread_index,
                root_author_pseudonym=root_actor,
                root_body=visible_checked.text,
                anchor_state=anchor_state,
                replies=tuple(replies),
                completeness=completeness,
                resolved_count=resolved_count,
                outdated_count=outdated_count,
                version=version,
                digest=digest,
            )
        )
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
    return (
        RemediationSnapshot(
            state=state,
            records=tuple(records),
            digest=digest,
            omitted=omitted,
            dlp_rejected=dlp_rejected,
        ),
        verified_roots,
    )
