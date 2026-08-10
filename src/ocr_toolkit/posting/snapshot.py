"""Previous OCR note snapshot, suppression, cleanup, and rollback."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from ocr_toolkit.posting.comments import comment_line, line_number
from ocr_toolkit.posting.gitlab import (
    GitLabConfig,
    api_get_paginated,
    delete_discussion_note,
    delete_draft_note,
    delete_plain_note,
    draft_note_id,
)
from ocr_toolkit.posting.markers import (
    OCR_REPLY_COMMAND_RE,
    ManagedApprovalReceipt,
    author_id_from_note,
    comment_fingerprint,
    comment_fingerprint_candidates,
    fingerprint_from_marker,
    is_diff_note,
    is_own_bot_note,
    managed_approval_receipt_from_body,
)
from ocr_toolkit.posting.settings import post_mode, strict_posting


@dataclass
class BotCommentRefs:
    """References to previous bot-created notes that can be deleted after success."""

    plain_note_ids: list[int] = field(default_factory=list)
    discussion_note_refs: list[tuple[str, int]] = field(default_factory=list)
    draft_note_ids: list[int] = field(default_factory=list)
    # Complete pre-run id baseline, including human-touched discussions that
    # success cleanup must preserve. Rollback subtracts against these fields so
    # it deletes only current-run notes after a failed publish attempt.
    all_plain_note_ids: list[int] = field(default_factory=list)
    all_discussion_note_refs: list[tuple[str, int]] = field(default_factory=list)
    all_draft_note_ids: list[int] = field(default_factory=list)
    # (path, new_line) pairs the reviewer marked as resolved or asked to
    # suppress via a reply command. New OCR comments hitting these locations
    # are dropped before posting.
    suppressed_inline_keys: set[tuple[str, int]] = field(default_factory=set)
    # Fingerprints from past resolved, human-touched, or explicitly suppressed
    # comments. Matching findings are dropped regardless of ordinary line shifts.
    suppressed_fingerprints: set[str] = field(default_factory=set)
    # Discussions that the bot should resolve after successful posting.
    discussions_to_resolve: list[str] = field(default_factory=list)
    # Accepted only from an owned plain summary note. Ambiguous receipts are
    # discarded so unapproval cannot be authorized by conflicting history.
    managed_approval_receipt: ManagedApprovalReceipt | None = None


def cleanup_drafts_created_by_this_run(config: GitLabConfig, draft_note_ids: list[int]) -> None:
    """Delete draft notes created by this script run after a creation failure."""

    for note_id in draft_note_ids:
        delete_draft_note(config, note_id)


def filter_suppressed_comments(
    comments: Sequence[dict[str, Any]],
    previous_refs: BotCommentRefs | None,
) -> tuple[list[dict[str, Any]], int]:
    """Drop OCR comments that should not be published again."""

    if previous_refs is None:
        return list(comments), 0

    suppressed_keys = previous_refs.suppressed_inline_keys
    suppressed_fingerprints = previous_refs.suppressed_fingerprints
    if not suppressed_keys and not suppressed_fingerprints:
        return list(comments), 0

    kept: list[dict[str, Any]] = []
    dropped = 0
    consumed_base_fingerprints: set[str] = set()
    for comment in comments:
        path = str(comment.get("path") or "").strip()
        line = comment_line(comment)
        if path and line > 0 and (path, line) in suppressed_keys:
            dropped += 1
            continue
        if suppressed_fingerprints:
            fingerprints = comment_fingerprint_candidates(comment)
            matched = fingerprints.intersection(suppressed_fingerprints)
            base_fingerprint = comment_fingerprint(comment)
            if base_fingerprint in matched:
                if base_fingerprint in consumed_base_fingerprints:
                    matched.remove(base_fingerprint)
                else:
                    consumed_base_fingerprints.add(base_fingerprint)
            if matched:
                dropped += 1
                continue
        kept.append(comment)

    return kept, dropped


def discussion_inline_key(discussion: dict[str, Any]) -> tuple[str, int] | None:
    """Return (path, new_line) for an inline discussion, if available.

    GitLab inline discussions store the diff position on the first note.
    For non-inline (general) discussions the position is missing — those
    are not tracked in the suppression set because they have no anchor line.
    """

    notes = discussion.get("notes")
    if not isinstance(notes, list) or not notes:
        return None

    first = notes[0]
    if not isinstance(first, dict):
        return None

    position = first.get("position")
    if not isinstance(position, dict):
        return None

    path = position.get("new_path") or position.get("old_path")
    line = line_number(position.get("new_line"))
    if not isinstance(path, str) or not path or line <= 0:
        return None
    return (path, line)


def reviewer_command_in_thread(config: GitLabConfig, notes: Sequence[Any]) -> str | None:
    """Return the last reviewer-issued lifecycle command, or None.

    Looks only at notes whose author is NOT the bot, so the bot's own
    follow-ups cannot change lifecycle state. The newest matching command wins.
    """

    bot_user_id = config.current_user_id
    found: str | None = None

    for note in notes:
        if not isinstance(note, dict):
            continue

        author_id = author_id_from_note(note)
        if bot_user_id is not None and author_id == bot_user_id:
            continue
        if note.get("system"):
            continue

        body = str(note.get("body") or "")
        for match in OCR_REPLY_COMMAND_RE.finditer(body):
            found = match.group(1).lower()

    return found


def process_discussion_for_refs(
    config: GitLabConfig,
    refs: BotCommentRefs,
    discussion_id: str,
    notes: Sequence[Any],
    *,
    preserve_human_touched: bool = True,
) -> None:
    """Classify a discussion into cleanup, suppression, and resolve buckets.

    Behavior:
    - resolved discussions: preserve them and suppress matching findings;
    - unresolved discussions with `/ocr suppress`: preserve them open and
      suppress matching findings;
    - unresolved discussions with `/ocr resolve`: suppress matching findings
      and schedule resolution after a successful posting transaction;
    - unresolved threads with any human reply: preserve the full discussion
      and suppress duplicates, because reviewer-visible context now belongs
      to that conversation even without an explicit `/ocr` command;
    - everything else (plain unresolved bot threads): mark for deletion
      as before, so a fresh review replaces the previous one.
    """

    bot_notes: list[dict[str, Any]] = []
    fingerprints: list[str] = []
    is_resolved = False
    human_reply = False
    bot_user_id = config.current_user_id

    for note in notes:
        if not isinstance(note, dict):
            continue

        if note.get("resolved"):
            is_resolved = True

        if not note.get("system"):
            author_id = author_id_from_note(note)
            if bot_user_id is None or author_id != bot_user_id:
                human_reply = True

        if not is_own_bot_note(config, note, body_field="body"):
            continue

        bot_notes.append(note)
        fingerprint = fingerprint_from_marker(str(note.get("body") or ""))
        if fingerprint:
            fingerprints.append(fingerprint)

    if not bot_notes:
        return

    reviewer_command = reviewer_command_in_thread(config, notes)
    inline_key = None
    first_note = bot_notes[0]
    if isinstance(first_note, dict):
        # discussion_inline_key needs the discussion-level shape, so
        # synthesize one with the bot note as the leading element.
        inline_key = discussion_inline_key({"notes": [first_note]})

    if preserve_human_touched and (
        is_resolved or reviewer_command in {"suppress", "resolve"} or human_reply
    ):
        if inline_key is not None:
            refs.suppressed_inline_keys.add(inline_key)
        refs.suppressed_fingerprints.update(fingerprints)
        if reviewer_command == "resolve" and not is_resolved:
            refs.discussions_to_resolve.append(discussion_id)
        return

    for note in bot_notes:
        note_id = note.get("id")
        if isinstance(note_id, int):
            refs.discussion_note_refs.append((discussion_id, note_id))


def collect_previous_bot_comment_refs(
    config: GitLabConfig, *, preserve_human_touched: bool = True
) -> BotCommentRefs | None:
    """Collect previous OCR bot notes without deleting them.

    Old bot notes are deleted only after the new OCR review is successfully
    created and published. This prevents a failed rerun from erasing the last
    valid review.
    """

    refs = BotCommentRefs()
    discussion_bot_note_ids: set[int] = set()

    plain_notes = api_get_paginated(config, "/notes?sort=desc&order_by=created_at", max_pages=50)
    if plain_notes is None:
        return None

    discussions = api_get_paginated(config, "/discussions", max_pages=50)
    if discussions is None:
        return None

    for discussion in discussions:
        if not isinstance(discussion, dict):
            continue

        discussion_id = str(discussion.get("id") or "")
        notes = discussion.get("notes")

        if not discussion_id or not isinstance(notes, list):
            continue

        for note in notes:
            if not isinstance(note, dict):
                continue
            if not is_own_bot_note(config, note, body_field="body"):
                continue
            note_id = note.get("id")
            if isinstance(note_id, int):
                discussion_bot_note_ids.add(note_id)
                refs.all_discussion_note_refs.append((discussion_id, note_id))

        process_discussion_for_refs(
            config,
            refs,
            discussion_id,
            notes,
            preserve_human_touched=preserve_human_touched,
        )

    managed_receipts: set[ManagedApprovalReceipt] = set()
    for note in plain_notes:
        if not isinstance(note, dict):
            continue

        if not is_own_bot_note(config, note, body_field="body"):
            continue

        note_id = note.get("id")
        if not isinstance(note_id, int):
            continue

        # Parse ownership before de-duplicating `/notes` against
        # `/discussions`: GitLab may expose the same general note through both
        # collections even though the approval receipt belongs to the plain
        # toolkit summary rather than an inline position.
        if not is_diff_note(note):
            receipt = managed_approval_receipt_from_body(str(note.get("body") or ""))
            if receipt is not None and receipt.user_id == config.current_user_id:
                managed_receipts.add(receipt)

        # GET /notes can include diff notes that also appear in
        # /discussions. GitLab does not always expose enough shape in
        # /notes to classify them with is_diff_note(), so skip every own
        # bot note id already seen in /discussions before using
        # DELETE /notes/{id}.
        if note_id in discussion_bot_note_ids or is_diff_note(note):
            continue

        refs.all_plain_note_ids.append(note_id)
        refs.plain_note_ids.append(note_id)

    if len(managed_receipts) == 1:
        refs.managed_approval_receipt = managed_receipts.pop()
    elif len(managed_receipts) > 1:
        print(
            "Multiple toolkit-managed approval receipts were found; "
            "automatic unapproval is disabled for this run.",
            file=sys.stderr,
        )

    draft_notes: list[Any] = []
    if post_mode() == "draft":
        fetched_draft_notes = api_get_paginated(config, "/draft_notes", max_pages=50)
        if fetched_draft_notes is None:
            return None
        draft_notes = fetched_draft_notes

    for note in draft_notes:
        if not isinstance(note, dict):
            continue

        if not is_own_bot_note(config, note, body_field="note"):
            continue

        note_id = draft_note_id(note)
        if note_id is not None:
            refs.all_draft_note_ids.append(note_id)
            refs.draft_note_ids.append(note_id)

    return refs


def delete_collected_bot_comments(config: GitLabConfig, refs: BotCommentRefs) -> None:
    """Delete collected OCR bot notes."""

    deleted = 0

    for note_id in refs.plain_note_ids:
        if delete_plain_note(config, note_id):
            deleted += 1

    for discussion_id, note_id in refs.discussion_note_refs:
        if delete_discussion_note(config, discussion_id, note_id):
            deleted += 1

    for note_id in refs.draft_note_ids:
        if delete_draft_note(config, note_id):
            deleted += 1

    if deleted:
        print(f"Deleted {deleted} OCR bot note(s).")


def delete_previous_bot_comments_if_collected(
    config: GitLabConfig,
    refs: BotCommentRefs | None,
) -> None:
    """Delete previous OCR bot notes only when the pre-posting snapshot is reliable."""

    if refs is None:
        print(
            "Skipping previous OCR bot note cleanup because previous comments were not collected safely.",
            file=sys.stderr,
        )
        return

    delete_collected_bot_comments(config, refs)


def subtract_bot_comment_ids(current: BotCommentRefs, baseline: BotCommentRefs) -> BotCommentRefs:
    """Return the delete-able id deltas between current and baseline refs.

    Only the three id-bearing fields (plain notes, inline discussion
    notes, draft notes) are subtracted. Suppression/resolve state from the
    baseline is intentionally NOT copied because the only caller
    (`rollback_current_run_comments`) consumes the result to delete
    ids only. If a future caller needs lifecycle state, fetch the
    baseline separately rather than using this delta.
    """

    baseline_plain_note_ids = set(baseline.all_plain_note_ids or baseline.plain_note_ids)
    baseline_discussion_note_refs = set(
        baseline.all_discussion_note_refs or baseline.discussion_note_refs
    )
    baseline_draft_note_ids = set(baseline.all_draft_note_ids or baseline.draft_note_ids)

    return BotCommentRefs(
        plain_note_ids=[
            note_id for note_id in current.plain_note_ids if note_id not in baseline_plain_note_ids
        ],
        discussion_note_refs=[
            ref for ref in current.discussion_note_refs if ref not in baseline_discussion_note_refs
        ],
        draft_note_ids=[
            note_id for note_id in current.draft_note_ids if note_id not in baseline_draft_note_ids
        ],
    )


def rollback_current_run_comments(
    config: GitLabConfig,
    previous_bot_comment_refs: BotCommentRefs | None,
    draft_note_ids: list[int],
) -> None:
    """Best-effort cleanup for comments created during a failed posting attempt."""

    cleanup_drafts_created_by_this_run(config, draft_note_ids)

    if previous_bot_comment_refs is None:
        print(
            "Skipping OCR published-note rollback because previous bot comments were not collected safely.",
            file=sys.stderr,
        )
        return

    current_bot_comment_refs = collect_previous_bot_comment_refs(
        config, preserve_human_touched=False
    )
    if current_bot_comment_refs is None:
        print(
            "Skipping OCR published-note rollback because current bot comments are unavailable.",
            file=sys.stderr,
        )
        return

    current_run_refs = subtract_bot_comment_ids(current_bot_comment_refs, previous_bot_comment_refs)
    delete_collected_bot_comments(config, current_run_refs)


def print_posting_failure_banner() -> None:
    """Print a visible banner so non-strict posting failures stay noticeable."""

    banner = (
        "==================================================================\n"
        "  OCR POSTING FAILED. Review comments may be missing from the MR.\n"
        "  Check the GitLab token, /user reachability, and rate limits.\n"
        "  Some unsafe states fail the posting script even when\n"
        "  OCR_STRICT_POSTING=false; otherwise set OCR_STRICT_POSTING=true\n"
        "  to fail CI on all posting errors.\n"
        "=================================================================="
    )
    print(banner, file=sys.stderr)


def posting_failure_exit(
    config: GitLabConfig,
    previous_bot_comment_refs: BotCommentRefs | None,
    draft_note_ids: list[int],
) -> int:
    """Rollback current-run GitLab comments and return the configured failure code."""

    rollback_current_run_comments(config, previous_bot_comment_refs, draft_note_ids)
    print_posting_failure_banner()
    return 1 if strict_posting() else 0


def publish_failure_exit(config: GitLabConfig, draft_note_ids: list[int]) -> int:
    """Handle ambiguous draft publish failures without deleting published notes.

    A draft publish timeout/5xx can mean GitLab already made part of this run
    visible. Treat that mixed state as CI-visible even in non-strict mode so an
    operator reruns the job instead of silently accepting two overlapping OCR
    reviews on the MR.
    """

    cleanup_drafts_created_by_this_run(config, draft_note_ids)
    print(
        "Skipping OCR published-note rollback after draft publish failure; "
        "some draft notes may already be visible on the MR.",
        file=sys.stderr,
    )
    print_posting_failure_banner()
    return 1
