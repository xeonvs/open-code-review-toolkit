"""Render overview, process, and technical sections from aggregate fields."""

import html
from typing import Any

from .markup import ReportMarkup


def _projects(self: ReportMarkup, rows: list[dict[str, Any]]) -> str:
    return "".join(
        self.folded(
            self.scalar(row["project"], field="project")
            + (
                f' <span class="archive">{self.label("archive_label")}</span>'
                if row["archived"]
                else ""
            ),
            self.mapping(
                {key: value for key, value in row.items() if key not in {"project", "archived"}}
            ),
        )
        for row in rows
    ) or self.note("no_data")


def _details(self: ReportMarkup, rows: list[dict[str, Any]]) -> str:
    groups: dict[int, tuple[str, list[list[str]]]] = {}
    for row in rows:
        mr = html.escape(str(row["mr"]))
        url = row["url"]
        identity = (
            f'<a href="{html.escape(url, quote=True)}" rel="noreferrer">!{mr}</a>'
            if url
            else f"!{mr}"
        )
        _, entries = groups.setdefault(row["project_id"], (row["project"], []))
        entries.append(
            [
                identity,
                *[
                    self.scalar(row[key], field=key)
                    for key in (
                        "state",
                        "opened",
                        "draft",
                        "attempts",
                        "reviewed_revisions",
                        "delivered",
                    )
                ],
            ]
        )
    headers = [
        "MR",
        *[
            self.label(key)
            for key in (
                "state",
                "opened",
                "draft",
                "attempts",
                "reviewed_revisions",
                "delivered",
            )
        ],
    ]
    return "".join(
        self.folded(html.escape(project), self.table(headers, values))
        for project, values in groups.values()
    )


def _overview(ui: ReportMarkup, report: dict[str, Any], *, costs: bool) -> dict[str, str]:
    summary = report["overview"]
    trend = report["trends"]
    charts = [
        ("opening_chart", "opened"),
        ("attempt_chart", "attempts"),
        ("completion_chart", "merged"),
        ("close_chart", "closed"),
        ("delivery_chart", "model_results"),
        ("token_chart", "tokens"),
    ]
    if costs:
        charts.append(("cost_chart", "estimated_usd"))
    chart_html = "".join(ui.chart(title, field, trend["weekly"]) for title, field in charts)
    delivery = report["delivery"]
    return {
        "overview": ui.cards(
            {
                "project_count": summary["projects"],
                **{
                    key: summary[key]
                    for key in (
                        "merge_requests",
                        "projects_with_delivered_review",
                        "archived_projects",
                    )
                },
            }
        )
        + ui.note("cohort_note")
        + ui.folded(ui.label("scope"), ui.mapping(report["scope"]))
        + ui.mapping({"lifecycle": summary["lifecycle"]}),
        "trends": ui.note("calendar_note")
        + '<div class="charts">'
        + chart_html
        + "</div>"
        + ui.mapping(trend),
        "delivery": ui.cards(
            {
                key: delivery[key]
                for key in (
                    "attempts",
                    "reviewed_revisions",
                    "mrs_with_delivered_review",
                    "mrs_with_partial_model_delivery",
                )
            }
        )
        + ui.note("delivery_note")
        + ui.folded(ui.label("show_table"), ui.mapping(delivery)),
    }


def _workflow(ui: ReportMarkup, report: dict[str, Any]) -> dict[str, str]:
    process = report["process"]
    adoption = report["adoption"]
    matured = [
        {"date": row["date"], "merge_completion_rate": row["merge_completion_rate"]["value"]}
        for row in report["trends"]["rolling_14_days"]
        if "merge_completion_rate" in row
    ]
    time_to_merge = [
        {
            "week_start": row["week_start"],
            "opening_to_completion_median": row["opening_to_completion"]["p50_seconds"],
        }
        for row in report["trends"]["weekly"]
    ]
    charts = (
        '<div class="charts">'
        + ui.chart("completion_rate_chart", "merge_completion_rate", matured, proportion=True)
        + ui.chart("duration_chart", "opening_to_completion_median", time_to_merge)
        + "</div>"
    )
    return {
        "process": ui.cards(
            {
                "merged_within_14_days": process["merged_within_14_days"],
                "opening_to_merge_median": process["calendar_durations"]["opening_to_merge"][
                    "p50_seconds"
                ],
                "assigned_involved_reviewer_count": process["process_counts"].get(
                    "assigned_involved_reviewer_count"
                ),
                "mrs_with_followup_review": process["revision_flow"].get(
                    "mrs_with_followup_review"
                ),
            }
        )
        + ui.note("process_note")
        + charts
        + ui.folded(ui.label("show_table"), ui.mapping(process)),
        "adoption": ui.cards(
            {
                "eligible_projects": adoption["eligible_projects"],
                "before": adoption["effect"]["before"],
                "after": adoption["effect"]["after"],
            }
        )
        + ui.note("adoption_note")
        + ui.mapping({key: value for key, value in adoption.items() if key != "projects"})
        + "".join(
            ui.folded(
                ui.scalar(row["project"], field="project"),
                ui.mapping({key: value for key, value in row.items() if key != "project"}),
            )
            for row in adoption["projects"]
        ),
    }


def _technical(ui: ReportMarkup, report: dict[str, Any], *, costs: bool) -> dict[str, str]:
    technical = report["technical"]
    counts = technical["counts"]
    usage = counts.get("tokens", {})
    cost_sources = ""
    if costs:
        cost_sources = ui.note("cost_note") + ui.cards(
            {
                source: technical["cost"]["by_source"][source]["estimated_usd"]
                for source in ("publication_model", "current_project_configuration")
            }
        )
    return {
        "technical": ui.cards(
            {
                **{
                    key: technical[key]
                    for key in (
                        "recognized_publications",
                        "model_results",
                        "successful_model_results",
                    )
                },
                "tokens": usage.get("total"),
                **({"estimated_usd": technical["cost"]["estimated_usd"]} if costs else {}),
            }
        )
        + cost_sources
        + ui.folded(ui.label("show_table"), ui.mapping(technical)),
        "source_coverage": ui.mapping(report["source_coverage"]),
        "projects": _projects(ui, report["projects"]),
    }


def report_sections(
    ui: ReportMarkup,
    report: dict[str, Any],
    details: list[dict[str, Any]],
    *,
    costs: bool,
) -> dict[str, str]:
    return {
        **_overview(ui, report, costs=costs),
        **_workflow(ui, report),
        **_technical(ui, report, costs=costs),
        **({"details": _details(ui, details)} if details else {}),
    }
