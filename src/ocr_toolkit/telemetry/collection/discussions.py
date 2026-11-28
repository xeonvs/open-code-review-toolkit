"""Reduce GitLab review conversations to participant counts and normalized publications."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ocr_toolkit.posting.markers import fingerprint_from_marker, note_starts_with_marker

from ..publications import parse_publication
from .facts import actor, identity, timestamp
from .transport import CollectionError, GitLabClient, RequestError

MAX_NOTE_BYTES = 256 * 1024
MAX_NOTES = 2_000
MAX_AWARD_READS = 600


def _notes(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Validate unique note identities before reducing discussion observations."""

    seen: set[int] = set()
    identities: dict[tuple[int, ...], list[dict[str, Any]]] = {}
    threads: list[list[dict[str, Any]]] = []
    for row in rows:
        notes = row.get("notes")
        if not isinstance(notes, list):
            raise CollectionError("GitLab returned an invalid merge-request discussion.")
        keys: list[int] = []
        for note in notes:
            note_id = identity(note.get("id")) if isinstance(note, dict) else None
            if note_id is None:
                raise CollectionError("GitLab returned an invalid or repeated discussion note.")
            keys.append(note_id)
        key = tuple(keys)
        if key in identities and notes == identities[key]:
            continue
        if len(notes) + len(seen) > MAX_NOTES:
            raise CollectionError("A GitLab merge request exceeded the discussion note limit.")
        if len(set(keys)) != len(keys) or seen.intersection(keys):
            raise CollectionError("GitLab returned an invalid or repeated discussion note.")
        seen.update(keys)
        identities[key] = notes
        if notes:
            threads.append(notes)
    return threads


def _reaction_counts(
    client: GitLabClient,
    endpoint: str,
    note_ids: list[tuple[int, str]],
    bot_id: int,
    author_id: int | None,
) -> tuple[dict[str, int | None], str]:
    """Count reactions from authenticated account identities and explicit availability."""

    counts: dict[str, int | None] = {
        "reacted_bot_notes": 0,
        "reactions_from_others": 0,
        "author_reactions": 0 if author_id is not None else None,
        "author_reactions_to_assigned_review": 0 if author_id is not None else None,
    }
    state = "complete"
    for index, (note_id, role) in enumerate(note_ids):
        if index == MAX_AWARD_READS:
            state = "partial"
            break
        try:
            awards = client.pages(f"{endpoint}/notes/{note_id}/award_emoji")
        except RequestError as exc:
            if exc.status not in {403, 404}:
                raise
            state = "partial"
            continue
        seen_awards: dict[int, int | None] = {}
        actors = []
        for award in awards:
            award_id, account = identity(award.get("id")), actor(award.get("user"))
            if award_id is not None and award_id in seen_awards:
                if account != seen_awards[award_id]:
                    state = "partial"
                continue
            if award_id is not None:
                seen_awards[award_id] = account
            actors.append(account)
        if any(account is None for account in actors):
            state = "partial"
        if role == "bot":
            reactions = sum(account is not None and account != bot_id for account in actors)
            counts["reacted_bot_notes"] = (counts["reacted_bot_notes"] or 0) + int(reactions > 0)
            counts["reactions_from_others"] = (counts["reactions_from_others"] or 0) + reactions
        key = "author_reactions" if role == "bot" else "author_reactions_to_assigned_review"
        if author_id is not None:
            counts[key] = (counts[key] or 0) + sum(account == author_id for account in actors)
    return counts, state


def merge_review_history(
    previous: list[dict[str, Any]], current: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Refresh one observation per source note while retaining disappeared publications."""

    history = {review["source_note_id"]: review for review in previous}
    for review in current:
        note_id = review["source_note_id"]
        prior = history.get(note_id)
        if (
            prior
            and prior["created_at"]
            and review["created_at"]
            and prior["created_at"] != review["created_at"]
        ):
            raise CollectionError("GitLab changed the creation identity of a saved review note.")
        if prior is None or (review["updated_at"] or "") >= (prior["updated_at"] or ""):
            history[note_id] = review
        if len(history) > MAX_NOTES:
            raise CollectionError("A GitLab merge request exceeded the publication history limit.")
    return sorted(
        history.values(),
        key=lambda review: (
            review["created_at"] or "",
            review["source_note_id"],
            review["updated_at"] or "",
        ),
    )


def _bot_publication(
    note: dict[str, Any], bot_id: int
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Identify toolkit output without classifying unrelated discussion text."""

    body = note.get("body")
    if (
        note.get("system") is not False
        or actor(note.get("author")) != bot_id
        or not isinstance(body, str)
        or len(body) > MAX_NOTE_BYTES
        or len(body.encode("utf-8", errors="replace")) > MAX_NOTE_BYTES
    ):
        return False, None, None
    publication = parse_publication(body)
    return (
        publication is not None or note_starts_with_marker(body),
        publication,
        fingerprint_from_marker(body),
    )


def read_discussions(
    client: GitLabClient,
    endpoint: str,
    mr: dict[str, Any],
    bot_id: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, int | None],
    str,
    dict[str, list[str]],
]:
    """Collect selected bot activity, human process facts and reaction observations."""

    threads = _notes(client.pages(f"{endpoint}/discussions"))
    author = actor(mr.get("author"))
    reviewers = mr.get("reviewers")
    assigned = (
        {
            account
            for item in reviewers
            if (account := actor(item)) is not None and account not in {author, bot_id}
        }
        if isinstance(reviewers, list)
        else set()
    )
    observed: set[int] = set()
    involved: set[int] = set()
    activity: list[str] = []
    reviewer_actions: list[str] = []
    assigned_actions: list[str] = []
    author_actions: list[str] = []
    assignment_events: list[str] = []
    approval_events: list[str] = []
    ready_events: list[str] = []
    award_notes: list[tuple[int, str]] = []
    discussions: list[dict[str, Any]] = []
    publications: list[dict[str, Any]] = []
    fingerprints: Counter[str] = Counter()
    process_counts: Counter[str] = Counter()
    for notes in threads:
        first = notes[0]
        owner = actor(first.get("author"))
        first_publication = _bot_publication(first, bot_id)
        bot_thread = first_publication[0]
        code_thread = bool(first.get("resolvable") is True and owner not in {None, author, bot_id})
        assigned_thread = bool(code_thread and owner in assigned)
        process_counts["code_discussions"] += int(code_thread)
        process_counts["assigned_review_threads"] += int(assigned_thread)
        author_reply = author_resolved = False
        resolver = actor(first.get("resolved_by"))
        resolved_at = timestamp(first.get("resolved_at"))
        if first.get("resolved") is True and resolver not in {None, bot_id}:
            process_counts["resolutions"] += 1
            if resolved_at:
                activity.append(resolved_at)
            if resolver != author:
                involved.add(resolver)
                if resolved_at:
                    reviewer_actions.append(resolved_at)
            if resolver in assigned:
                process_counts["assigned_reviewer_resolutions"] += 1
                if resolved_at:
                    assigned_actions.append(resolved_at)
            if assigned_thread and resolver == author:
                process_counts["author_resolutions_of_assigned_review"] += 1
                if resolved_at:
                    author_actions.append(resolved_at)
        if bot_thread and first.get("resolved") is True:
            author_resolved = author is not None and resolver == author
        bot_notes = resolvable = resolved = inline = 0
        other_reply = False
        for index, note in enumerate(notes):
            account = actor(note.get("author"))
            created = timestamp(note.get("created_at"))
            system = note.get("system") is True
            body = note.get("body")
            if system and created and isinstance(body, str) and len(body) <= 1024:
                message = body.strip().casefold()
                approved = message == "approved this merge request"
                if "requested review from" in message:
                    assignment_events.append(created)
                if "marked this merge request as ready" in message or "marked as ready" in message:
                    ready_events.append(created)
                if account not in {None, author, bot_id} and (
                    approved or "resolved all threads" in message
                ):
                    if approved:
                        approval_events.append(created)
                    involved.add(account)
                    reviewer_actions.append(created)
                    activity.append(created)
                    if account in assigned:
                        assigned_actions.append(created)
            if system or account is None:
                continue
            if account == bot_id:
                toolkit_note, publication, fingerprint = (
                    first_publication if index == 0 else _bot_publication(note, bot_id)
                )
                if bot_thread and toolkit_note:
                    award_notes.append((note["id"], "bot"))
                    bot_notes += 1
                    is_resolvable = note.get("resolvable") is True
                    resolvable += int(is_resolvable)
                    resolved += int(is_resolvable and note.get("resolved") is True)
                    inline += int(is_resolvable and isinstance(note.get("position"), dict))
                if publication is not None:
                    publications.append(
                        {
                            **publication,
                            "created_at": created,
                            "updated_at": timestamp(note.get("updated_at")),
                            "source_note_id": note["id"],
                        }
                    )
                elif fingerprint:
                    fingerprints[fingerprint] += 1
                continue
            observed.add(account)
            process_counts["human_comments"] += 1
            process_counts["human_replies"] += int(index > 0)
            if created:
                activity.append(created)
            if account != author:
                involved.add(account)
                if created:
                    reviewer_actions.append(created)
            if account in assigned:
                process_counts["assigned_reviewer_comments"] += 1
                if created:
                    assigned_actions.append(created)
                if assigned_thread:
                    award_notes.append((note["id"], "reviewer"))
            if index > 0:
                other_reply = True
                if account == author:
                    author_reply = True
                    if assigned_thread and created:
                        author_actions.append(created)
        if assigned_thread and author_reply:
            process_counts["author_replies_to_assigned_review"] += 1
        if bot_thread:
            discussions.append(
                {
                    "bot_note_count": bot_notes,
                    "resolvable_count": resolvable,
                    "resolved_count": resolved,
                    "inline_count": inline,
                    "general_count": resolvable - inline,
                    "has_non_bot_reply": other_reply,
                    "has_author_reply": author_reply,
                    "resolved_by_author": author_resolved,
                }
            )

    approval_payload: Any = None
    try:
        approval_payload = client.get(f"{endpoint}/approvals")
    except RequestError as exc:
        if exc.status not in {403, 404}:
            raise
    approvals = approval_payload.get("approved_by") if isinstance(approval_payload, dict) else None
    approvers: set[int] = set()
    for approval in approvals if isinstance(approvals, list) else []:
        if not isinstance(approval, dict) or (account := actor(approval.get("user"))) in {
            None,
            author,
            bot_id,
        }:
            continue
        approvers.add(account)
        involved.add(account)
        observed.add(account)
        approved_at = timestamp(approval.get("approved_at"))
        if approved_at:
            approval_events.append(approved_at)
            activity.append(approved_at)
            reviewer_actions.append(approved_at)
            if account in assigned:
                assigned_actions.append(approved_at)

    reactions, reaction_state = _reaction_counts(client, endpoint, award_notes, bot_id, author)
    terminal = (
        actor(mr.get("merge_user")) or actor(mr.get("merged_by")) or actor(mr.get("closed_by"))
    )
    process = {
        **dict.fromkeys(
            (
                "human_comments",
                "human_replies",
                "resolutions",
                "code_discussions",
                "assigned_review_threads",
                "assigned_reviewer_comments",
                "assigned_reviewer_resolutions",
                "author_replies_to_assigned_review",
                "author_resolutions_of_assigned_review",
            ),
            0,
        ),
        **process_counts,
        "assigned_reviewer_count": len(assigned) if isinstance(reviewers, list) else None,
        "involved_reviewer_count": len(involved),
        "assigned_involved_reviewer_count": len(assigned & involved)
        if isinstance(reviewers, list)
        else None,
        "observed_human_participant_count": len(observed),
        "other_human_action": bool(involved),
        "terminal_actor_is_author": terminal == author if terminal and author else None,
        "approval_count": len(approvers) if isinstance(approvals, list) else None,
        "required_approvals": (
            approval_payload["approvals_required"]
            if isinstance(approval_payload, dict)
            and type(approval_payload.get("approvals_required")) is int
            and 0 <= approval_payload["approvals_required"] <= 10_000
            else None
        ),
        "approvals_from_assigned_reviewers": len(approvers & assigned)
        if isinstance(approvals, list) and isinstance(reviewers, list)
        else None,
        "first_approval_at": min(approval_events, default=None),
        "first_human_action_at": min(reviewer_actions, default=None),
        "first_assigned_reviewer_action_at": min(assigned_actions, default=None),
        "first_reviewer_assignment_at": min(assignment_events, default=None),
        "latest_human_action_at": max(activity, default=None),
        "ready_at": min(ready_events, default=None),
        "assigned_reviewer_returned_after_author_action": (
            bool(
                assigned_actions and author_actions and max(assigned_actions) > min(author_actions)
            )
        ),
        "author_reactions_to_assigned_review": reactions["author_reactions_to_assigned_review"],
        "human_reactions_comparable": reaction_state == "complete"
        and author is not None
        and isinstance(reviewers, list),
        "ocr_repeated_publications": sum(count - 1 for count in fingerprints.values()),
    }
    return (
        discussions,
        publications,
        process,
        reactions,
        reaction_state,
        {"assigned_review": assigned_actions, "author_action": author_actions},
    )
