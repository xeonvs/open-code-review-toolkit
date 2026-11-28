"""Normalize provider primitives shared by the collection boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ocr_toolkit.review_identity import full_sha as revision_sha


def identity(value: object) -> int | None:
    """Return one positive provider identifier within the bounded wire domain."""

    return value if type(value) is int and 0 < value < 2**63 else None


def actor(value: Any) -> int | None:
    """Compare provider account identity without retaining its profile."""

    return identity(value.get("id")) if isinstance(value, dict) else None


def instant(value: object) -> datetime | None:
    """Normalize an aware provider timestamp and reject hostile types and values."""

    if not isinstance(value, str) or not 20 <= len(value) <= 40 or value[10] != "T":
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(UTC) if parsed.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def timestamp(value: object) -> str | None:
    """Return a fixed-width UTC time suitable for exact stable comparisons."""

    parsed = instant(value)
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z") if parsed else None


__all__ = ["actor", "identity", "instant", "revision_sha", "timestamp"]
