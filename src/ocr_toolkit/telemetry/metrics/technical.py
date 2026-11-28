"""Aggregate publication claims without exposing private payload fields."""

from collections import Counter, defaultdict
from decimal import Decimal
from itertools import repeat
from typing import Any

from ocr_toolkit.ocr_result import PUBLIC_REVIEW_TOOL_CALL_NAMES
from ocr_toolkit.telemetry.publications.grammar import (
    OCR_FAILURE_STATUS_TYPES,
    OCR_FEDERATION_COUNTERS,
    OCR_MCP_KINDS,
    OCR_PROVIDER_FAILURE_REASON_SET,
    OCR_PUBLICATION_DLP_REASON_KEYS,
    OCR_PUBLICATION_DLP_SOURCE_KEYS,
    OCR_SETUP_AUTHORITIES,
    model_publication,
)
from ocr_toolkit.telemetry.rates import publication_model

from .common import closed, count, data, distribution, ratio, sum_fields
from .cost import COST_SOURCES, observe_cost
from .delivery import OUTCOMES, PARTIAL_OUTCOMES, SUCCESS_OUTCOMES

_GROUPS = {
    "severity": ("critical", "high", "medium", "low"),
    "categories": (
        "bug",
        "security",
        "performance",
        "maintainability",
        "test",
        "documentation",
        "style",
        "other",
    ),
    "posting": (
        "inline",
        "general",
        "fallback",
        "omitted",
        "suppressed",
        "retained",
        "limited",
        "failed",
        "carried_forward",
        "publication_limit",
    ),
    "coverage": ("selected", "completed", "reused", "failed", "waived"),
    "tool_calls_by_name": (*sorted(PUBLIC_REVIEW_TOOL_CALL_NAMES), "other"),
    "mcp": ("servers", "calls"),
    "completed_evidence_actions": ("summary", "list", "get", "search", "coverage"),
    "tokens": ("input", "output", "cached", "reasoning", "total", "other"),
    "repository_coverage": ("ordinary_completed", "ordinary_changed", "gitlink_changes"),
    "federation": ("tools", "ocr_attempts", *OCR_FEDERATION_COUNTERS),
    "ocr_core_advisory": ("actual", "recommended"),
    "fallback_reasons": (
        "missing_diff_refs",
        "missing_path",
        "missing_line",
        "unknown",
        "invalid_position",
        "other",
    ),
}
_MODEL_BUCKETS = {
    "posting_mode": ("draft", "direct"),
    "approval_state": ("approved", "not eligible", "disabled", "skipped", "failed"),
    "diagram_state": (
        "disabled",
        "unsupported",
        "not-generated",
        "not-applicable",
        "generated",
        "omitted-invalid",
    ),
}
_DLP_REASONS = tuple(sorted(OCR_PUBLICATION_DLP_REASON_KEYS))
_DLP_SOURCES = tuple(sorted(OCR_PUBLICATION_DLP_SOURCE_KEYS))


def technical_summary(
    reviews: list[dict[str, Any]],
    models: dict[str, str],
    *,
    prices: dict[str, Any],
    costs: bool,
    project_model_hints: list[str | None] | None = None,
) -> dict[str, Any]:
    recognized = [row for row in reviews if row.get("recognized", True) is True]
    hints = project_model_hints if project_model_hints is not None else repeat(None, len(reviews))
    model_entries = [
        (row, hint) for row, hint in zip(reviews, hints, strict=True) if model_publication(row)
    ]
    model_rows = [row for row, _ in model_entries]
    observed, fields = Counter(), Counter()
    groups: dict[str, Counter[str]] = defaultdict(Counter)
    dlp: dict[str, Counter[str]] = defaultdict(Counter)
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    model_costs: dict[str, Decimal] = defaultdict(Decimal)
    by_cost_source: dict[str, Counter[str]] = defaultdict(Counter)
    source_costs: dict[str, Decimal] = defaultdict(Decimal)
    for row in recognized:
        observed["outcomes." + closed(row.get("outcome"), OUTCOMES)] += 1
        observed[
            "kinds."
            + closed(
                row.get("result_kind", "model"),
                ("model", "pre_model", "terminal_lifecycle", "status", "provider_failure"),
            )
        ] += 1
        if row.get("result_kind") == "provider_failure":
            observed[
                "provider_failure_reason."
                + closed(row.get("provider_failure_reason"), OCR_PROVIDER_FAILURE_REASON_SET)
            ] += 1
        if row.get("result_kind") == "status":
            observed[
                "status_type." + closed(row.get("status_type"), OCR_FAILURE_STATUS_TYPES.values())
            ] += 1
        if rejection := data(row.get("review_rejection")):
            observed[
                "review_rejection."
                + closed(
                    rejection.get("reason"),
                    ("evidence-use-unconfirmed", "evidence-action-attribution-invalid"),
                )
            ] += 1
            sum_fields(groups["review_rejection"], rejection, ("reported_calls",))
        if row.get("outcome") == "setup_pending":
            observed[
                "setup_authority."
                + closed(row.get("setup_authority"), (*OCR_SETUP_AUTHORITIES, "unavailable"))
            ] += 1
        if row.get("terminal_lifecycle") in ("merged", "closed"):
            observed["terminal_lifecycle." + row["terminal_lifecycle"]] += 1
        if limits := data(row.get("pre_model_limit")):
            unit = closed(
                limits.get("unit"), ("characters", "bytes", "tokens", "files", "records", "entries")
            )
            sum_fields(groups["pre_model_limit." + unit], limits, ("actual", "limit"))
        if isinstance(coverage := row.get("repository_coverage"), dict):
            coverage_state = closed(coverage.get("state"), ("partial", "not_started"))
            sum_fields(
                groups["repository_coverage." + coverage_state],
                coverage,
                _GROUPS["repository_coverage"],
            )
        else:
            coverage_state = "unavailable"
        observed[
            "repository_signal."
            + ("invalid" if row.get("repository_coverage_invalid") else coverage_state)
        ] += 1
    for row, project_model in model_entries:
        for group, keys in _GROUPS.items():
            if group == "repository_coverage":
                continue
            value = data(row.get(group))
            fields[group] += any(count(value.get(key)) is not None for key in keys)
            sum_fields(groups[group], value, keys)
        for field in ("findings", "tool_calls", "reviewer_suppressed_findings", "warning_count"):
            if (value_count := count(row.get(field))) is not None:
                fields[field] += 1
                observed[field] += value_count
        observed[
            "review_modes."
            + (
                "invalid"
                if row.get("review_mode_invalid") is True
                else closed(
                    row.get("review_mode"),
                    ("protected_default_fallback", "limited_comment_only", "unavailable"),
                )
            )
        ] += 1
        for field, choices in _MODEL_BUCKETS.items():
            if (state := row.get(field)) in choices:
                fields[field] += 1
                observed[field + "." + state] += 1
        observed["legacy_context_policy"] += row.get("legacy_context_policy") is True
        if mcp := data(row.get("mcp")):
            kind = closed(mcp.get("kind"), OCR_MCP_KINDS.values())
            sum_fields(
                groups["mcp." + kind],
                mcp.get("calls_by_name"),
                ("ocr_toolkit", "ocr_toolkit_evidence", "ocr_toolkit_federation", "other"),
            )
        signal = data(row.get("publication_filter"))
        if signal:
            fields["publication_filter"] += 1
            dlp["states"][
                closed(
                    signal.get("state"),
                    ("passed", "disabled", "filtered", "publication-filtered", "private-sanitized"),
                )
            ] += 1
            public = data(signal.get("public_output"))
            sum_fields(
                dlp["reasons"],
                public.get("reason_counts", signal.get("reason_counts")),
                _DLP_REASONS,
            )
            sum_fields(dlp["retained"], signal.get("retained"), ("comments", "warnings", "fields"))
            sum_fields(
                dlp["omitted"], public or signal.get("omitted"), ("comments", "warnings", "fields")
            )
            sum_fields(
                dlp["retained"],
                {key: signal.get("retained_" + key) for key in ("comments", "warnings")},
                ("comments", "warnings"),
            )
            sum_fields(
                dlp["historical_field_counts"], signal, ("omitted_fields", "sanitized_fields")
            )
            sum_fields(
                dlp["historical_reasons"], signal.get("historical_reason_counts"), _DLP_REASONS
            )
            if not public and not signal.get("omitted"):
                sum_fields(
                    dlp["omitted"],
                    {key: signal.get("omitted_" + key) for key in ("comments", "warnings")},
                    ("comments", "warnings"),
                )
            sum_fields(dlp["retained"], signal, ("carried_forward_comments",))
            sum_fields(
                dlp["private_sanitization_fields"], signal.get("private_sanitization"), ("fields",)
            )
            sum_fields(
                dlp["private_sanitization"],
                data(signal.get("private_sanitization")).get("reason_counts"),
                _DLP_REASONS,
            )
            sum_fields(dlp["sources"], signal.get("source_attribution"), _DLP_SOURCES)
        for gate in ("arguments", "result"):
            sum_fields(
                groups["federation_" + gate],
                data(data(row.get("federation")).get("dlp_gates")).get(gate),
                _DLP_REASONS,
            )
        model = publication_model(row)
        label = models.get(model, "unknown") if model is not None else "unknown"
        by_model[label]["results"] += 1
        sum_fields(by_model[label], row.get("tokens"), _GROUPS["tokens"])
        if costs:
            observation = observe_cost(row, prices, project_model=project_model)
            source_counts = by_cost_source[observation.source]
            source_counts["model_results"] += 1
            source_counts["usage_available"] += observation.usage_available
            if observation.estimate is not None:
                source_counts["priced_results"] += 1
                source_costs[observation.source] += observation.estimate
                if observation.source == "publication_model":
                    by_model[label]["priced_results"] += 1
                    model_costs[label] += observation.estimate
    tool_calls = [count(row.get("tool_calls")) for row in model_rows]
    tool_distribution = distribution(float(value) for value in tool_calls if value is not None)
    unrecognized_tokens: Counter[str] = Counter()
    for row in reviews:
        if row.get("recognized", True) is not True:
            sum_fields(unrecognized_tokens, row.get("tokens"), _GROUPS["tokens"])
    result: dict[str, Any] = {
        "observed_publications": len(reviews),
        "recognized_publications": len(recognized),
        "recognized_publication_coverage": ratio(len(recognized), len(reviews)),
        "model_results": len(model_rows),
        "successful_model_results": sum(
            closed(row.get("outcome"), SUCCESS_OUTCOMES) in SUCCESS_OUTCOMES for row in model_rows
        ),
        "partial_model_results": sum(
            closed(row.get("outcome"), PARTIAL_OUTCOMES) in PARTIAL_OUTCOMES for row in model_rows
        ),
        "clean_model_results": sum(
            row.get("outcome") == "complete"
            and count(row.get("findings")) == 0
            and row.get("findings_reported", True) is True
            and not data(row.get("posting")).get("omitted")
            and not row.get("reviewer_suppressed_findings")
            and not row.get("repository_coverage")
            and not row.get("repository_coverage_invalid")
            for row in model_rows
        ),
        "summary": dict(observed),
        "unrecognized_token_counts": dict(unrecognized_tokens),
        "field_coverage": {
            field: ratio(fields[field], len(model_rows))
            for field in (
                *_GROUPS,
                "findings",
                "tool_calls",
                "publication_filter",
                "reviewer_suppressed_findings",
                "warning_count",
                *_MODEL_BUCKETS,
            )
            if field != "repository_coverage"
        },
        "counts": {field: dict(values) for field, values in groups.items() if values},
        "publication_dlp": {field: dict(values) for field, values in dlp.items() if values},
        "tool_call_distribution": {
            key.removesuffix("_seconds"): value for key, value in tool_distribution.items()
        },
        "models": [
            {
                "model": label,
                **dict(counters),
                **(
                    {"estimated_usd": float(model_costs[label]) if label in model_costs else None}
                    if costs
                    else {}
                ),
            }
            for label, counters in sorted(by_model.items())
        ],
    }
    if costs:
        priced = sum(values["priced_results"] for values in by_cost_source.values())
        with_usage = sum(values["usage_available"] for values in by_cost_source.values())
        result["cost"] = {
            "estimated_usd": float(sum(source_costs.values())) if priced else None,
            "pricing_coverage": ratio(priced, len(model_rows)),
            "usage_coverage": ratio(with_usage, len(model_rows)),
            "by_source": {
                source: {
                    "model_results": by_cost_source[source]["model_results"],
                    "estimated_usd": float(source_costs[source])
                    if source in source_costs
                    else None,
                    "pricing_coverage": ratio(
                        by_cost_source[source]["priced_results"],
                        by_cost_source[source]["model_results"],
                    ),
                    "usage_coverage": ratio(
                        by_cost_source[source]["usage_available"],
                        by_cost_source[source]["model_results"],
                    ),
                }
                for source in COST_SOURCES
            },
        }
    return result
