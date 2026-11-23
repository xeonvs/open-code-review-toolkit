"""Opt-in native Analysis arguments and its bounded private result projection."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenValue, check_text

COMBINED_SCHEMA = "ocr.review-with-analysis/v2"
METADATA_SCHEMA = "ocr.review-analysis/v2"
PRIVATE_RESULT_KEY = "toolkit_analysis"
ENVIRONMENT_OPTIONS = ("OCR_ANALYSIS", "OCR_ANALYSIS_MAX_TOKENS_BUDGET")
_NATIVE_FIELDS = {"analysis", "analysis_raw", "analysis_meta", "review_status"}
_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
_MARKDOWN_BUDGETS = TextBudgets(max_chars=64_000, max_bytes=256_000, max_lines=4096)


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    """Keep model-only options out of preview and subprocess environment."""

    enabled: bool = False
    budget: int = 0

    def native_args(self) -> list[str]:
        if not self.enabled:
            return []
        return ["--analysis", "--analysis-max-tokens-budget", str(self.budget)]


def extract_options(
    args: list[str], environment: Mapping[str, str]
) -> tuple[list[str], AnalysisOptions]:
    """Normalize toolkit environment and explicit OCR argument forms once."""

    enabled = environment.get("OCR_ANALYSIS", "false").strip().lower()
    budget = environment.get("OCR_ANALYSIS_MAX_TOKENS_BUDGET", "0").strip()
    remaining = []
    seen: set[str] = set()
    iterator = iter(args)
    for argument in iterator:
        option, equals, value = argument.partition("=")
        if option not in {"--analysis", "--analysis-max-tokens-budget"}:
            remaining.append(argument)
            continue
        if option in seen:
            raise ValueError(f"{option} must be provided at most once")
        seen.add(option)
        if option == "--analysis":
            enabled = value.lower() if equals else "true"
        else:
            budget = value if equals else next(iterator, "")
    if enabled not in {"true", "false"}:
        raise ValueError("OCR_ANALYSIS requires true or false")
    if not re.fullmatch(r"[0-9]{1,19}", budget) or int(budget) > 2**63 - 1:
        raise ValueError("--analysis-max-tokens-budget requires a non-negative 64-bit integer")
    return remaining, AnalysisOptions(enabled == "true", int(budget))


def has_native_analysis_fields(payload: Mapping[str, object]) -> bool:
    """Recognize native Analysis material before ordinary review handoffs."""

    return payload.get("schema_version") == COMBINED_SCHEMA or bool(
        _NATIVE_FIELDS.intersection(payload)
    )


def admit_analysis(
    payload: dict[str, object],
    *,
    requested: bool,
    forbidden: tuple[str | ForbiddenValue, ...],
) -> dict[str, object] | None:
    """Consume native data before generic metadata, publication or reporting reads it."""

    if PRIVATE_RESULT_KEY in payload:
        raise ValueError("OCR result contains a reserved Analysis field")
    combined = payload.get("schema_version") == COMBINED_SCHEMA
    if not requested:
        if has_native_analysis_fields(payload):
            raise ValueError("unsolicited native Analysis result")
        return None
    if (
        not combined
        or payload.get("review_status") != payload.get("status")
        or not isinstance(payload.get("review_status"), str)
    ):
        raise ValueError("native Analysis result does not identify its primary review outcome")
    payload.pop("schema_version")
    payload.pop("review_status")
    markdown = payload.pop("analysis", None)
    payload.pop("analysis_raw", None)
    meta = payload.pop("analysis_meta", None)
    # The native session was removed during review teardown.
    payload.pop("session_id", None)
    if not isinstance(meta, dict) or meta.get("schema_version") != METADATA_SCHEMA:
        return {"status": "unavailable"}
    status = meta.get("execution_status")
    completion = meta.get("declared_completion")
    if not isinstance(status, str) or status not in {"completed", "partial", "skipped", "failed"}:
        return {"status": "unavailable"}
    accepted = meta.get("submission_accepted")
    if type(accepted) is not bool or (status == "completed" and not accepted):
        return {"status": "unavailable"}
    result: dict[str, object] = {"status": status}
    if isinstance(completion, str) and completion in {"complete", "partial", "unknown"}:
        result["declared_completion"] = completion
    usage = meta.get("usage")
    if isinstance(usage, dict):
        counts = {key: usage[key] for key in _USAGE_KEYS if key in usage}
        if counts and all(type(count) is int and 0 <= count < 2**63 for count in counts.values()):
            result["usage"] = counts
    if status in {"completed", "partial"}:
        if not isinstance(markdown, str) or not markdown:
            result["report_state"] = "unavailable"
            return result
        checked = check_text(
            markdown, publication=True, enabled=True, budgets=_MARKDOWN_BUDGETS, forbidden=forbidden
        )
        if checked.admitted and checked.text is not None and checked.text.strip():
            result["markdown"] = checked.text
        else:
            result["report_state"] = "filtered"
    return result
