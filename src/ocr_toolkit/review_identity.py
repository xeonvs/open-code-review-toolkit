"""Resolve one fail-closed reviewed source identity across review lifecycle owners."""

from __future__ import annotations

import re
from collections.abc import Mapping

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ZERO_SHA = "0" * 40


def full_sha(value: object) -> str:
    """Return one exact non-zero lowercase SHA-1 identity or an empty value."""

    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None or value == ZERO_SHA:
        return ""
    return value


def effective_reviewed_sha(environment: Mapping[str, str]) -> str:
    """Resolve the MR source head with the documented detached-pipeline fallback."""

    merge_request_sha = environment.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "")
    if merge_request_sha and merge_request_sha != ZERO_SHA:
        return full_sha(merge_request_sha)
    return full_sha(environment.get("CI_COMMIT_SHA", ""))
