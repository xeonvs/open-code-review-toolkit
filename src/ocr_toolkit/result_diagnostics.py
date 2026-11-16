"""Project hostile result documents into closed, count-only failure diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from ocr_toolkit.evidence.actions import MAX_ACTION_CALLS, validate_action_counts
from ocr_toolkit.result_contract import LEGACY_OUTCOMES, MANIFEST_OUTCOMES

RESULT_KEYS = frozenset(
    {
        "status",
        "llm",
        "trace_id",
        "message",
        "summary",
        "tool_calls",
        "comments",
        "groups",
        "warnings",
        "project_summary",
        "resume",
        "session_id",
        "manifest",
        "retry_report",
    }
)
RESULT_STATUSES = frozenset((*LEGACY_OUTCOMES, *MANIFEST_OUTCOMES))


def _count(value: object) -> int | None:
    """Accept only bounded counters, never booleans or numeric text."""

    return value if type(value) is int and 0 <= value <= MAX_ACTION_CALLS else None


@dataclass(frozen=True, slots=True)
class ResultDiagnostic:
    """Retain only closed facts from the exact document seen by finalization."""

    status: str
    keys: tuple[str, ...]
    unknown_keys: int
    manifest_present: bool
    tool_calls: str
    telemetry_detail: str
    total: int | None
    evidence_calls: int | None
    exit_code: int | None
    summary_attempted: int | None
    summary_completed: int | None

    def render(self) -> str:
        """Render bounded public facts without repository or provider text."""

        def shown(value: int | None) -> str:
            return "unavailable" if value is None else str(value)

        return (
            f"OCR result diagnostics: status={self.status} keys=[{','.join(self.keys)}] "
            f"unknown_keys={self.unknown_keys} manifest={'present' if self.manifest_present else 'absent'} "
            f"tool_calls={self.tool_calls} ocr_exit_code={shown(self.exit_code)} "
            f"telemetry_detail={self.telemetry_detail} "
            f"reported_total={shown(self.total)} reported_evidence_calls={shown(self.evidence_calls)} "
            f"summary_receipt={'unavailable' if self.summary_attempted is None else 'available'} "
            f"summary_attempted={shown(self.summary_attempted)} "
            f"summary_completed={shown(self.summary_completed)}"
        )


def result_diagnostic(
    payload: dict[str, object],
    *,
    exit_code: int | None,
    action_counts: object,
) -> ResultDiagnostic:
    """Observe result shape before admission without conferring admission authority."""

    status = payload.get("status")
    telemetry = payload.get("tool_calls")
    total = None
    evidence = None
    state = "missing" if "tool_calls" not in payload else "null" if telemetry is None else "invalid"
    detail = (
        "missing-field"
        if state == "missing"
        else "explicit-null"
        if state == "null"
        else "not-object"
    )
    if isinstance(telemetry, dict):
        total = _count(telemetry.get("total"))
        by_tool = telemetry.get("by_tool")
        detail = "total-invalid" if total is None else "by-tool-not-object"
        if total is not None and isinstance(by_tool, dict):
            primary = _count(by_tool.get("ocr_toolkit_evidence", 0))
            detail = "evidence-count-invalid" if primary is None else "evidence-exceeds-total"
            if primary is not None and primary <= total:
                state = "present"
                evidence = primary
                detail = (
                    "evidence-entry-absent"
                    if "ocr_toolkit_evidence" not in by_tool
                    else "evidence-zero"
                    if primary == 0
                    else "evidence-reported"
                )
    actions = validate_action_counts(action_counts)
    return ResultDiagnostic(
        status if isinstance(status, str) and status in RESULT_STATUSES else "unknown",
        tuple(sorted(RESULT_KEYS.intersection(payload))),
        sum(key not in RESULT_KEYS for key in payload),
        "manifest" in payload,
        state,
        detail,
        total,
        evidence,
        exit_code if type(exit_code) is int and -(2**31) <= exit_code < 2**32 else None,
        actions["attempted"]["summary"] if actions is not None else None,
        actions["completed"]["summary"] if actions is not None else None,
    )
