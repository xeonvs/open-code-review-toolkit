"""Pure time, counting, and snapshot field helpers for report metrics."""

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

DAY = timedelta(days=1)
WINDOW = 14 * DAY


def timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def data(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def rows(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def count(value: object) -> int | None:
    return value if type(value) is int and 0 <= value < 2**63 else None


def closed(value: object, choices: Iterable[str]) -> str:
    return value if isinstance(value, str) and value in choices else "unknown"


def sum_fields(target: Counter[str], values: object, fields: Iterable[str]) -> None:
    mapping = data(values)
    for key in fields:
        if (value := count(mapping.get(key))) is not None:
            target[key] += value


def duration(start: object, end: object) -> float | None:
    first, last = timestamp(start), timestamp(end)
    return (last - first).total_seconds() if first and last and first <= last else None


def quantile(sorted_values: list[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (position - lower) * (sorted_values[upper] - sorted_values[lower])


def distribution(values: Iterable[float | None]) -> dict[str, int | float | None]:
    known = sorted(value for value in values if value is not None)
    return {
        "count": len(known),
        "mean_seconds": sum(known) / len(known) if known else None,
        "p50_seconds": quantile(known, 0.5),
        "p90_seconds": quantile(known, 0.9),
    }


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def review_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return rows(record.get("reviews"))


def revision_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return rows(record.get("revisions"))


def attempt_created_at(run: dict[str, Any]) -> datetime | None:
    """Use the job's start of existence, with a fallback for older observations."""

    return timestamp(run.get("created_at")) or timestamp(run.get("pipeline_created_at"))


def terminal(record: dict[str, Any]) -> object:
    if record.get("state") == "merged":
        return record.get("merged_at")
    return record.get("closed_at") if record.get("state") == "closed" else None


def completion(record: dict[str, Any], horizon: datetime) -> bool | None:
    """Use a terminal event or lifecycle evidence at the end of the opening window."""

    opened, finished = timestamp(record.get("created_at")), timestamp(terminal(record))
    if opened is None or opened > horizon:
        return None
    if finished and opened <= finished <= horizon:
        return record.get("state") == "merged" and finished - opened <= WINDOW
    cutoff = opened + WINDOW
    observed = timestamp(record.get("lifecycle_observed_at"))
    if cutoff <= horizon and (
        (finished is not None and cutoff <= finished)
        or (observed is not None and cutoff <= observed)
    ):
        return False
    return None
