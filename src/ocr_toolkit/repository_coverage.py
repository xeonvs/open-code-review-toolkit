"""Closed, path-free repository coverage for qualified partial gitlink reviews."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from ocr_toolkit.evidence.gitlink_projection import GitlinkProjection, RawDiffEntry

REPOSITORY_COVERAGE_SCHEMA = "ocr.repository-coverage/v1"
GITLINK_PARTIAL_REASON = "changed_gitlink_not_reviewed"
MAX_COVERAGE_COUNT = 20_000
CoverageState = Literal["partial", "not_started"]


class RepositoryCoverageError(ValueError):
    """Reject an unsupported or inconsistent effective-coverage statement."""


@dataclass(frozen=True, slots=True)
class RepositoryCoverage:
    """Public counts without paths, object IDs, URLs or provider content."""

    schema_version: str
    state: CoverageState
    reason: str
    ordinary_changed: int
    ordinary_selected: int
    ordinary_completed: int
    ordinary_excluded: int
    gitlink_changes: int
    gitlink_added: int
    gitlink_updated: int
    gitlink_deleted: int
    gitlink_moved: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


def parse_repository_coverage(
    value: Any, *, required_state: CoverageState | None = None
) -> RepositoryCoverage:
    """Parse one exact versioned effective coverage without coercion."""

    if not isinstance(value, dict) or set(value) != set(RepositoryCoverage.__dataclass_fields__):
        raise RepositoryCoverageError("repository coverage has an unsupported shape")
    if (
        value.get("schema_version") != REPOSITORY_COVERAGE_SCHEMA
        or not isinstance(value.get("state"), str)
        or value["state"] not in {"partial", "not_started"}
        or value.get("reason") != GITLINK_PARTIAL_REASON
        or (required_state is not None and value.get("state") != required_state)
    ):
        raise RepositoryCoverageError("repository coverage has unsupported values")
    count_fields = (
        "ordinary_changed",
        "ordinary_selected",
        "ordinary_completed",
        "ordinary_excluded",
        "gitlink_changes",
        "gitlink_added",
        "gitlink_updated",
        "gitlink_deleted",
        "gitlink_moved",
    )
    if any(
        type(value[field]) is not int or not 0 <= value[field] <= MAX_COVERAGE_COUNT
        for field in count_fields
    ):
        raise RepositoryCoverageError("repository coverage has invalid counts")
    if (
        value["ordinary_selected"] > value["ordinary_changed"]
        or value["ordinary_completed"] > value["ordinary_selected"]
        or value["ordinary_excluded"] != value["ordinary_changed"] - value["ordinary_selected"]
        or value["gitlink_changes"] == 0
        or value["gitlink_changes"]
        != value["gitlink_added"]
        + value["gitlink_updated"]
        + value["gitlink_deleted"]
        + 2 * value["gitlink_moved"]
        or (
            value["state"] == "partial"
            and (
                value["ordinary_selected"] == 0
                or value["ordinary_completed"] != value["ordinary_selected"]
            )
        )
        or (
            value["state"] == "not_started"
            and (value["ordinary_selected"] != 0 or value["ordinary_completed"] != 0)
        )
    ):
        raise RepositoryCoverageError("repository coverage counts are inconsistent")
    return RepositoryCoverage(**value)


def coverage_from_projection(
    projection: GitlinkProjection,
    selected: tuple[RawDiffEntry, ...],
    *,
    state: CoverageState,
) -> RepositoryCoverage:
    """Construct verified public counters from the frozen private input plan."""

    counts = projection.plan.counts
    selected_count = len(selected)
    value = {
        "schema_version": REPOSITORY_COVERAGE_SCHEMA,
        "state": state,
        "reason": GITLINK_PARTIAL_REASON,
        "ordinary_changed": len(projection.ordinary_diff),
        "ordinary_selected": selected_count,
        "ordinary_completed": selected_count if state == "partial" else 0,
        "ordinary_excluded": len(projection.ordinary_diff) - selected_count,
        "gitlink_changes": len(projection.plan.changes),
        "gitlink_added": counts["added"],
        "gitlink_updated": counts["updated"],
        "gitlink_deleted": counts["deleted"],
        "gitlink_moved": counts["moved"],
    }
    return parse_repository_coverage(value, required_state=state)


def repository_coverage_summary(coverage: RepositoryCoverage) -> str:
    """Render one path-free, non-approval coverage statement."""

    if coverage.state == "not_started":
        return (
            "Review not started: no ordinary files were selected; "
            f"{coverage.gitlink_changes} changed gitlink pointer(s) remain unreviewed."
        )
    return (
        "Repository coverage: partial; "
        f"{coverage.ordinary_completed} of {coverage.ordinary_changed} ordinary diff record(s) "
        "completed; "
        f"{coverage.gitlink_changes} changed gitlink pointer(s) were not reviewed."
    )
