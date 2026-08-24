"""Shared closed types and projections for bounded GitLab context snapshots."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from ocr_toolkit.context.dlp import normalize_text
from ocr_toolkit.providers.gitlab_identity import GitLabUserIdentity

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True)
class RawGitLabSnapshot:
    """Hold one bounded provider snapshot only until stable projection."""

    identity: GitLabUserIdentity
    threads: tuple[object, ...]
    pagination_omitted: int
    digest: str


def timestamp(value: object) -> int | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return int(parsed.astimezone(timezone.utc).timestamp())


def author_class(
    note: Mapping[str, object], author: Mapping[str, object], *, toolkit_bot_id: int
) -> tuple[str, int] | None:
    author_id = author.get("id")
    if not isinstance(author_id, int) or isinstance(author_id, bool) or author_id <= 0:
        return None
    if note.get("system") is True:
        return "system", author_id
    if author_id == toolkit_bot_id:
        return "toolkit_bot", author_id
    if author.get("bot") is True:
        return "automation", author_id
    if author.get("state") in {None, "active", "blocked"} and author.get("bot") in {None, False}:
        return "user", author_id
    return None


def anchor(position: object, *, source_sha: str) -> tuple[Mapping[str, object], bool, bool]:
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


def pseudonym(run_id: str, account_class: str, author_id: int) -> str:
    """Return a run-local actor identity without retaining the provider id."""

    return (
        "actor-" + hashlib.sha256(f"{run_id}:{account_class}:{author_id}".encode()).hexdigest()[:16]
    )
