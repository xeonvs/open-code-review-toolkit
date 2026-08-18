"""Author-bound one-shot reconciliation for ambiguous GitLab inline creates."""

from __future__ import annotations

import sys
from typing import Any

from ocr_toolkit.posting import gitlab
from ocr_toolkit.posting.markers import author_id_from_note, write_id_from_body

MAX_RECONCILIATION_PAGES = 50


def _draft_match(note: Any, write_id: str, expected_author_id: int) -> int | None:
    if not isinstance(note, dict):
        return None
    body = note.get("note")
    if not isinstance(body, str):
        return None
    parsed = write_id_from_body(body)
    if parsed != write_id:
        return None
    if author_id_from_note(note) != expected_author_id:
        raise ValueError("draft write marker matched a foreign or malformed author")
    note_id = gitlab.draft_note_id(note)
    if note_id is None:
        raise ValueError("draft write marker matched an unusable draft identity")
    return note_id


def _discussion_match(
    discussion: Any, write_id: str, expected_author_id: int
) -> tuple[str, int] | None:
    if not isinstance(discussion, dict):
        return None
    notes = discussion.get("notes")
    if not isinstance(notes, list):
        return None
    matched: list[tuple[str, int]] = []
    for note in notes:
        if not isinstance(note, dict):
            continue
        body = note.get("body")
        if not isinstance(body, str):
            continue
        parsed = write_id_from_body(body)
        if parsed != write_id:
            continue
        if author_id_from_note(note) != expected_author_id:
            raise ValueError("discussion write marker matched a foreign or malformed author")
        parsed_discussion = gitlab.created_discussion_note(
            {"id": discussion.get("id"), "notes": [note]}
        )
        if parsed_discussion is None:
            raise ValueError("discussion write marker matched an unusable identity")
        matched.append((parsed_discussion.discussion_id, parsed_discussion.note_id))
    if len(matched) > 1:
        raise ValueError("discussion contains multiple matching write markers")
    return matched[0] if matched else None


def reconcile_ambiguous_inline_create(
    config: gitlab.GitLabConfig, result: gitlab.GitLabWriteResult
) -> gitlab.GitLabWriteResult:
    """Recover exactly one complete author-bound match without another create."""

    if not result.ambiguous_create or result.write_id is None:
        return result
    expected_author_id = config.current_user_id
    if expected_author_id is None:
        return result

    create_kind = result.create_kind
    if create_kind not in {"draft", "discussion"}:
        return result
    endpoint = "/draft_notes" if create_kind == "draft" else "/discussions"
    items = gitlab.api_get_paginated(config, endpoint, max_pages=MAX_RECONCILIATION_PAGES)
    if items is None:
        return result

    try:
        if create_kind == "draft":
            matches = [
                match
                for item in items
                if (match := _draft_match(item, result.write_id, expected_author_id)) is not None
            ]
            if len(matches) == 1:
                return gitlab.GitLabWriteResult(
                    "posted",
                    write_id=result.write_id,
                    create_kind="draft",
                    draft_note_id=matches[0],
                )
        else:
            discussion_matches = [
                match
                for item in items
                if (match := _discussion_match(item, result.write_id, expected_author_id))
                is not None
            ]
            if len(discussion_matches) == 1:
                discussion_id, note_id = discussion_matches[0]
                return gitlab.GitLabWriteResult(
                    "posted",
                    write_id=result.write_id,
                    create_kind="discussion",
                    discussion_id=discussion_id,
                    discussion_note_id=note_id,
                )
    except ValueError as exc:
        print(f"GitLab inline create reconciliation failed: {exc}.", file=sys.stderr)
        return result

    print(
        "GitLab inline create reconciliation did not find exactly one valid match; "
        "no retry or fallback was attempted.",
        file=sys.stderr,
    )
    return result
