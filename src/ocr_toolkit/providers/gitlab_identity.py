"""Validated live GitLab identities shared by acquisition and posting owners."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

DISCUSSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,255}\Z")
USERNAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,253}[A-Za-z0-9])?\Z")


class GitLabIdentityError(ValueError):
    """The authenticated GitLab identity was unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class GitLabUserIdentity:
    """Hold only the live fields required for ownership and exact commands."""

    user_id: int
    username: str


def valid_discussion_id(value: Any) -> bool:
    """Return whether a value is an endpoint-safe GitLab discussion identity."""

    return isinstance(value, str) and DISCUSSION_ID_RE.fullmatch(value) is not None


def parse_current_user_identity(payload: object) -> GitLabUserIdentity:
    """Validate the minimal authenticated `GET /user` identity projection."""

    if not isinstance(payload, Mapping):
        raise GitLabIdentityError("GET /user returned no JSON object")
    user_id = payload.get("id")
    username = payload.get("username")
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise GitLabIdentityError("GET /user response has no valid id field")
    if not isinstance(username, str) or USERNAME_RE.fullmatch(username) is None:
        raise GitLabIdentityError("GET /user response has no valid username field")
    return GitLabUserIdentity(user_id=user_id, username=username)


def fetch_current_user_identity(
    api_root: str,
    read_json: Callable[[str], object],
) -> GitLabUserIdentity:
    """Read and validate the sole authenticated GitLab identity endpoint."""

    if not isinstance(api_root, str) or not api_root or api_root.endswith("/"):
        raise GitLabIdentityError("GitLab API root is invalid")
    return parse_current_user_identity(read_json(f"{api_root}/user"))
