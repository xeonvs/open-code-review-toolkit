"""Closed GitLab posting identity grammars shared by transaction owners."""

from __future__ import annotations

import re
from typing import Any

DISCUSSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,255}")


def valid_discussion_id(value: Any) -> bool:
    """Return whether a value is an endpoint-safe GitLab discussion identity."""

    return isinstance(value, str) and DISCUSSION_ID_RE.fullmatch(value) is not None
