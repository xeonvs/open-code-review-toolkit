"""Validate and normalize versioned Open Code Review result outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

OutcomeKind = Literal["clean", "warning", "partial", "failed", "skipped"]

MANIFEST_SCHEMA = "ocr.run-manifest/v1"
MAX_COVERAGE_RECORDS = 10_000
MAX_ITEM_ID_CHARS = 256
FAILURE_CLASSES = {
    "provider",
    "timeout",
    "cancelled",
    "configuration",
    "input",
    "budget",
    "panic",
    "unknown",
}
RUN_FAILURE_CLASSES = {
    "input",
    "configuration",
    "timeout",
    "cancelled",
    "budget",
    "internal",
    "unknown",
}
LEGACY_OUTCOMES: dict[str, OutcomeKind] = {
    "success": "clean",
    "completed_with_warnings": "warning",
    "completed_with_errors": "partial",
    "budget_exceeded": "partial",
    "skipped": "skipped",
}
MANIFEST_OUTCOMES: dict[str, OutcomeKind] = {
    "complete": "clean",
    "partial": "partial",
    "failed": "failed",
    "skipped": "skipped",
}


class OcrResultContractError(ValueError):
    """An OCR result contradicts the supported legacy or manifest contract."""


@dataclass(frozen=True, slots=True)
class ReviewOutcome:
    """Expose one validated OCR outcome without provider-specific branching."""

    status: str
    kind: OutcomeKind
    budget_exceeded: bool
    manifest_present: bool = False
    selected_count: int = 0
    completed_count: int = 0
    reused_count: int = 0
    failed_count: int = 0
    waived_count: int = 0

    @property
    def requires_evidence_mcp(self) -> bool:
        """Return whether the result represents review work that must use evidence."""

        return self.kind in {"clean", "warning", "partial"}

    @property
    def coverage_summary(self) -> str:
        """Return a path-free summary of versioned manifest coverage."""

        if not self.manifest_present:
            return ""
        return (
            f"Coverage: selected {self.selected_count}; completed {self.completed_count}; "
            f"reused {self.reused_count}; failed {self.failed_count}; "
            f"waived {self.waived_count}."
        )


def _budget_exceeded(result: Mapping[str, Any]) -> bool:
    """Read the optional summary budget flag without accepting truthy substitutes."""

    summary = result.get("summary")
    if summary is None:
        return False
    if not isinstance(summary, Mapping):
        raise OcrResultContractError("field 'summary' must be an object")
    value = summary.get("budget_exceeded", False)
    if not isinstance(value, bool):
        raise OcrResultContractError("field 'summary.budget_exceeded' must be a boolean")
    return value


def _coverage_ids(value: Any, field: str) -> tuple[set[str], list[Mapping[str, Any]]]:
    """Return bounded unique item identities from one coverage array."""

    if not isinstance(value, list):
        raise OcrResultContractError(f"field 'manifest.coverage.{field}' must be a list")
    if len(value) > MAX_COVERAGE_RECORDS:
        raise OcrResultContractError(
            f"field 'manifest.coverage.{field}' exceeds {MAX_COVERAGE_RECORDS} records"
        )
    identities: set[str] = set()
    records: list[Mapping[str, Any]] = []
    for index, record in enumerate(value):
        if not isinstance(record, Mapping):
            raise OcrResultContractError(
                f"field 'manifest.coverage.{field}[{index}]' must be an object"
            )
        item_id = record.get("item_id")
        if (
            not isinstance(item_id, str)
            or not item_id
            or len(item_id) > MAX_ITEM_ID_CHARS
            or any(character.isspace() for character in item_id)
        ):
            raise OcrResultContractError(
                f"field 'manifest.coverage.{field}[{index}].item_id' is invalid"
            )
        if item_id in identities:
            raise OcrResultContractError(
                f"field 'manifest.coverage.{field}' contains duplicate item_id values"
            )
        identities.add(item_id)
        records.append(record)
    return identities, records


def _validate_failure_records(records: list[Mapping[str, Any]]) -> bool:
    """Validate item failure classes and report whether budget caused one."""

    budget_failure = False
    for index, record in enumerate(records):
        classification = record.get("classification")
        if classification not in FAILURE_CLASSES:
            raise OcrResultContractError(
                f"field 'manifest.coverage.failed[{index}].classification' is unsupported"
            )
        budget_failure = budget_failure or classification == "budget"
    return budget_failure


def _validate_waived_records(records: list[Mapping[str, Any]]) -> None:
    """Require an explicit bounded reason for every waived item."""

    for index, record in enumerate(records):
        reason = record.get("reason")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2_000:
            raise OcrResultContractError(
                f"field 'manifest.coverage.waived[{index}].reason' is invalid"
            )


def _manifest_outcome(
    status: str, manifest: Mapping[str, Any], budget_exceeded: bool
) -> ReviewOutcome:
    """Validate the v1 coverage partition and derive its terminal outcome."""

    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise OcrResultContractError("field 'manifest.schema_version' is unsupported")
    if manifest.get("operation") != "review":
        raise OcrResultContractError("field 'manifest.operation' must be 'review'")
    terminal_state = manifest.get("terminal_state")
    if terminal_state not in MANIFEST_OUTCOMES:
        raise OcrResultContractError("field 'manifest.terminal_state' is unsupported")
    if status != terminal_state:
        raise OcrResultContractError("fields 'status' and 'manifest.terminal_state' disagree")

    coverage = manifest.get("coverage")
    if not isinstance(coverage, Mapping):
        raise OcrResultContractError("field 'manifest.coverage' must be an object")

    selected, _selected_records = _coverage_ids(coverage.get("selected"), "selected")
    completed, _completed_records = _coverage_ids(coverage.get("completed"), "completed")
    reused, _reused_records = _coverage_ids(coverage.get("reused"), "reused")
    failed, failed_records = _coverage_ids(coverage.get("failed"), "failed")
    waived, waived_records = _coverage_ids(coverage.get("waived"), "waived")

    terminal_sets = (completed, reused, failed, waived)
    terminal_union: set[str] = set()
    for terminal_set in terminal_sets:
        if terminal_union.intersection(terminal_set):
            raise OcrResultContractError("manifest coverage terminal sets are not disjoint")
        terminal_union.update(terminal_set)
    if terminal_union != selected:
        raise OcrResultContractError(
            "manifest coverage selected items do not equal the terminal partition"
        )

    budget_failure = _validate_failure_records(failed_records)
    _validate_waived_records(waived_records)

    run_failure = manifest.get("run_failure")
    if run_failure is not None:
        if not isinstance(run_failure, Mapping):
            raise OcrResultContractError("field 'manifest.run_failure' must be an object")
        if run_failure.get("classification") not in RUN_FAILURE_CLASSES:
            raise OcrResultContractError(
                "field 'manifest.run_failure.classification' is unsupported"
            )

    derived_state = (
        "failed"
        if run_failure is not None
        else "skipped"
        if not selected
        else "complete"
        if not failed
        else "failed"
        if failed == selected
        else "partial"
    )
    if terminal_state != derived_state:
        raise OcrResultContractError(
            "field 'manifest.terminal_state' disagrees with coverage and run_failure"
        )
    if budget_exceeded and not (
        budget_failure
        or (isinstance(run_failure, Mapping) and run_failure.get("classification") == "budget")
    ):
        raise OcrResultContractError(
            "field 'summary.budget_exceeded' has no matching manifest budget failure"
        )
    if terminal_state in {"complete", "skipped"} and budget_exceeded:
        raise OcrResultContractError(
            "complete or skipped manifest cannot report summary.budget_exceeded"
        )

    return ReviewOutcome(
        status=status,
        kind=MANIFEST_OUTCOMES[status],
        budget_exceeded=budget_exceeded,
        manifest_present=True,
        selected_count=len(selected),
        completed_count=len(completed),
        reused_count=len(reused),
        failed_count=len(failed),
        waived_count=len(waived),
    )


def parse_result_outcome(result: Mapping[str, Any]) -> ReviewOutcome:
    """Validate one OCR result and normalize legacy and manifest outcomes."""

    status_value = result.get("status", "success")
    if not isinstance(status_value, str) or not status_value:
        raise OcrResultContractError("field 'status' must be a non-empty string")
    budget_exceeded = _budget_exceeded(result)
    manifest = result.get("manifest")

    if manifest is not None:
        if not isinstance(manifest, Mapping):
            raise OcrResultContractError("field 'manifest' must be an object")
        return _manifest_outcome(status_value, manifest, budget_exceeded)

    if status_value not in LEGACY_OUTCOMES:
        if status_value in MANIFEST_OUTCOMES:
            raise OcrResultContractError(f"status {status_value!r} requires a supported manifest")
        raise OcrResultContractError("field 'status' is unsupported")
    if (status_value == "budget_exceeded") != budget_exceeded:
        raise OcrResultContractError("fields 'status' and 'summary.budget_exceeded' disagree")
    return ReviewOutcome(
        status=status_value,
        kind=LEGACY_OUTCOMES[status_value],
        budget_exceeded=budget_exceeded,
    )
