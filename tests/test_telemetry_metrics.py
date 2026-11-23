"""Exercise offline history, coverage, cost, and localized rendering with synthetic facts."""

import json
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser

import pytest

from ocr_toolkit.posting.formatting import format_token_usage_summary, summarize_result
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.posting.workflow import summary_with_run_marker
from ocr_toolkit.telemetry.metrics.common import ratio
from ocr_toolkit.telemetry.metrics.process import adoption_comparison
from ocr_toolkit.telemetry.metrics.technical import technical_summary
from ocr_toolkit.telemetry.presentation import build_report
from ocr_toolkit.telemetry.publications import parse_publication


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs)["href"])


def _snapshot():
    parsed = parse_publication(
        "## Open Code Review\n\n"
        "**Review incomplete — 1 finding published**\n\n"
        "<details>\n<summary>Technical details</summary>\n\n"
        "- Coverage: selected 2; completed 1; reused 0; failed 1; waived 0.\n"
        "</details>\n"
    )
    assert parsed is not None
    return {
        "projects": [
            {"id": 481747, "path": "synthetic/team", "archived": True, "access": "partial"},
            {"id": 732145, "path": "synthetic/zero<test>", "archived": False, "access": "complete"},
        ],
        "scope": {
            "start": "2026-01-01",
            "end": "2026-03-01",
            "discovery": "explicit",
            "bot": "synthetic.bot",
            "host": "gitlab.example.test",
            "updated_at": "2026-03-02T09:00:00Z",
        },
        "records": [
            {
                "project_id": 481747,
                "iid": 247915,
                "state": "merged",
                "created_at": "2026-01-19T09:00:00Z",
                "merged_at": "2026-01-24T09:00:00Z",
                "web_url": "https://gitlab.example.test/synthetic/team/-/merge_requests/247915",
                "revisions": [
                    {
                        "comparable": True,
                        "commits": 4,
                        "non_merge_commits": 2,
                        "followup_review": True,
                    },
                    {"comparable": True, "commits": 0, "non_merge_commits": 0, "final_tail": True},
                ],
                "runs": [
                    {
                        "status": "failed",
                        "started": True,
                        "started_at": "2026-01-19T10:00:00Z",
                        "allow_failure": True,
                        "pipeline_created_at": "2026-01-19T09:32:00Z",
                    },
                    {
                        "status": "success",
                        "success": True,
                        "started": True,
                        "started_at": "2026-01-20T10:00:00Z",
                        "pipeline_created_at": "2026-01-20T09:00:00Z",
                        "created_at": "2026-01-20T09:55:00Z",
                        "review_finished_at": "2026-01-20T10:05:00Z",
                        "attempt_kind": "repeat_new_pipeline",
                    },
                ],
                "checkpoints": [{"pipeline_created_at": "2026-01-20T09:00:00Z"}],
                "reviews": [
                    {
                        **parsed,
                        "created_at": "2026-01-19T10:03:00Z",
                        "model": "synthetic/private-model",
                        "tokens": {"input": 10, "output": 3, "cached": 4, "total": 13},
                        "publication_filter": {
                            "version": "v4",
                            "state": "publication-filtered",
                            "public_output": {
                                "comments": 1,
                                "warnings": 0,
                                "fields": 0,
                                "reason_counts": {"secret": 1},
                            },
                            "private_sanitization": {"fields": 2, "reason_counts": {"pii": 2}},
                        },
                    },
                    {
                        "created_at": "2026-01-20T10:06:00Z",
                        "outcome": "complete",
                        "recognized": True,
                        "findings": 0,
                        "tokens": {"total": 5},
                    },
                    {
                        "created_at": "2026-01-21T10:06:00Z",
                        "outcome": "setup_pending",
                        "recognized": True,
                        "result_kind": "pre_model",
                    },
                ],
                "process": {
                    "assigned_reviewer_count": 2,
                    "assigned_involved_reviewer_count": 1,
                    "first_assigned_reviewer_action_at": "2026-01-20T09:00:00Z",
                    "changed_lines": 501,
                },
                "completeness": {
                    "reactions": "complete",
                    "discussions": "complete",
                    "pipelines": "complete",
                    "revisions": "complete",
                },
                "discussions": [{"bot_note_count": 3, "has_author_reply": True}],
                "reactions": {
                    "reacted_bot_notes": 1,
                    "author_reactions": 2,
                    "reactions_from_others": 3,
                },
                "correlation": {"messages": 1, "matched_messages": 1},
            },
            {
                "project_id": 481747,
                "iid": 247916,
                "state": "opened",
                "draft": True,
                "created_at": "2026-02-25T09:00:00Z",
                "web_url": "https://different.example.test/invalid",
                "reviews": [{"recognized": False, "outcome": "complete"}],
                "process": {},
                "completeness": {"reactions": "partial", "revisions": "unavailable"},
                "reactions": {"author_reactions": 1000},
            },
        ],
        "prices": {
            "synthetic/private-model": {
                "prompt": "0.01",
                "completion": "0.02",
                "input_cache_read": "0.003",
            }
        },
        "prices_at": "2026-03-02T05:00:00Z",
    }


def test_report_separates_delivery_coverage_and_excludes_incomplete_reaction_samples():
    _, report = build_report(_snapshot(), anonymize=False, costs=True, lang="en")
    assert report["overview"]["archived_projects"] == 1
    assert report["overview"]["projects_with_merge_requests"] == 1
    assert report["projects"][0]["access"] == "partial"
    delivery = report["delivery"]
    assert (
        delivery["attempts"],
        delivery["successful_attempts"],
        delivery["reviewed_revisions"],
    ) == (2, 1, 1)
    assert delivery["mrs_with_delivered_review"] == 1
    assert delivery["mrs_with_partial_model_delivery"] == 1
    assert delivery["reaction_snapshot"] == {
        "author_reactions": 2,
        "reacted_bot_notes": 1,
        "reactions_from_others": 3,
    }
    assert delivery["reaction_snapshot_coverage"] == ratio(1, 2)
    assert report["source_coverage"]["reactions"] == {"complete": 1, "partial": 1}
    assert report["source_coverage"]["pipelines"] == {"complete": 1, "unavailable": 1}
    technical = report["technical"]
    assert technical["observed_publications"] == 4
    assert technical["recognized_publications"] == 3
    assert technical["counts"]["tokens"] == {"input": 10, "output": 3, "cached": 4, "total": 18}
    assert technical["cost"]["estimated_usd"] == 0.132
    assert technical["cost"]["pricing_coverage"] == ratio(1, 2)
    assert technical["cost"]["usage_coverage"] == ratio(1, 2)
    assert technical["partial_model_results"] == 1
    assert technical["successful_model_results"] == 1
    assert technical["publication_dlp"]["omitted"]["comments"] == 1
    assert technical["publication_dlp"]["reasons"]["secret"] == 1
    assert technical["publication_dlp"]["private_sanitization"]["pii"] == 2
    process = report["process"]
    assert process["merged_within_14_days"] == ratio(1, 1)
    assert process["revision_flow"]["non_merge_commits"] == 2
    assert process["revision_flow"]["merge_commits"] == 2
    assert process["revision_flow"]["mrs_with_unknown_change"] == 1
    assert process["calendar_durations"]["opening_to_assigned_action"]["p50_seconds"] == 86400
    assert report["trends"]["four_week_comparison"]["earlier_four_weeks"]["attempts"] == 2


def test_render_localizes_html_with_stable_json_and_omits_identifiers_and_costs():
    source = _snapshot()
    english, report = build_report(source, anonymize=True, costs=False, lang="en")
    russian, translated = build_report(source, anonymize=True, costs=False, lang="ru")
    named, _ = build_report(source, anonymize=False, costs=False, lang="en")
    assert report == translated
    assert "<title>Review telemetry</title>" in english
    assert "<title>Телеметрия ревью</title>" in russian
    assert "Проект 01" in russian
    assert "<meter " in english
    assert "100.0% (1/1)" in english
    assert "zero&lt;test&gt;" in named
    links = _Links()
    links.feed(named)
    assert "https://gitlab.example.test/synthetic/team/-/merge_requests/247915" in links.links
    assert all("different.example.test" not in link for link in links.links)
    anonymized = english + russian + json.dumps(report)
    for value in (
        "synthetic",
        "247915",
        "481747",
        "gitlab.example.test",
        "estimated_usd",
        "prices_at",
    ):
        assert value not in anonymized


def _adoption_periods(adopted):
    periods = []
    for offset in range(-16, 10):
        opened = adopted + timedelta(days=3 * offset)
        merged = opened + timedelta(days=2) if offset >= 0 else None
        periods.append(
            {
                "created_at": opened.isoformat(),
                "merged_at": merged.isoformat() if merged else None,
                "closed_at": None if merged else (opened + timedelta(days=1)).isoformat(),
                "state": "merged" if merged else "closed",
                "process": {"changed_lines": 42},
                "runs": [{"created_at": adopted.isoformat()}] if offset == 0 else [],
            }
        )
    periods.append({"created_at": (adopted - timedelta(days=1)).isoformat(), "state": "opened"})
    return periods


def test_adoption_uses_balanced_observed_window_and_excludes_transitional_mrs():
    adopted = datetime(2026, 2, 1, tzinfo=UTC)
    periods = _adoption_periods(adopted)
    captured = adopted + timedelta(days=60)
    comparison = adoption_comparison(
        {1: periods, 2: periods},
        {1: "Project 01", 2: "Project 02"},
        captured,
        captured_at=captured,
    )
    assert comparison["eligible_projects"] == 2
    assert comparison["exclusions"]["transitional"] == 2
    assert comparison["projects"][0]["sample_per_period"] == 10
    assert comparison["effect"]["before"] == ratio(0, 20)
    assert comparison["effect"]["after"] == ratio(20, 20)
    assert comparison["effect"]["pooled_delta"] == 1.0
    assert comparison["effect"]["confidence_interval_95"] == {"low": 1.0, "high": 1.0}
    assert comparison["by_change_size"]["small"]["after"] == ratio(20, 20)


def test_future_scope_has_no_observed_calendar_days():
    snapshot = _snapshot()
    snapshot["scope"].update(start="2026-03-10", end="2026-04-10")
    snapshot["records"] = []
    _, report = build_report(snapshot, anonymize=True, costs=False, lang="en")
    assert report["scope"]["observed_through"] == report["scope"]["captured_at"]
    assert report["trends"]["daily"] == []
    assert report["process"]["merged_within_14_days"] == ratio(0, 0)


def test_optional_signals_require_observations_and_hidden_findings_are_not_clean():
    base = {"outcome": "complete", "recognized": True, "result_kind": "model"}
    technical = technical_summary(
        [
            {**base, "findings": 0, "findings_reported": True, "tool_calls": 0},
            {**base, "findings": 0, "findings_reported": False, "warning_count": 0},
            {**base, "findings": 0, "reviewer_suppressed_findings": 2},
            {**base, "findings": 0, "posting": {"omitted": 1}},
            {**base, "model_started": False, "outcome": "skipped"},
            {**base, "recognized": False, "tokens": {"total": 10}},
            {
                **base,
                "mcp": {
                    "kind": "verified_calls",
                    "servers": 2,
                    "calls": 3,
                    "calls_by_name": {"ocr_toolkit_evidence": 1, "ocr_toolkit_federation": 2},
                },
            },
        ],
        {},
        prices={},
        costs=False,
    )
    assert technical["recognized_publications"] == 6
    assert technical["model_results"] == 5
    assert technical["clean_model_results"] == 1
    assert technical["unrecognized_token_counts"] == {"total": 10}
    assert technical["tool_call_distribution"] == {"count": 1, "mean": 0, "p50": 0, "p90": 0}
    assert technical["field_coverage"]["warning_count"] == ratio(1, 5)
    assert technical["counts"]["mcp.verified_calls"] == {
        "ocr_toolkit_evidence": 1,
        "ocr_toolkit_federation": 2,
    }


def test_locked_state_counts_and_renders():
    source = _snapshot()
    source["records"][1]["state"] = "locked"
    rendered, report = build_report(source, anonymize=False, costs=False, lang="ru")
    assert report["overview"]["lifecycle"] == {"closed": 0, "locked": 1, "merged": 1, "opened": 0}
    assert "<td>Заблокировано</td>" in rendered


def test_rolling_merge_rate_waits_for_all_openings_on_the_last_day():
    source = _snapshot()
    source["scope"].update(start="2026-05-19", end="2026-06-15", updated_at="2026-06-15T12:00:00Z")
    source["records"] = [
        {
            "project_id": 481747,
            "iid": 1,
            "state": "merged",
            "created_at": "2026-06-01T18:00:00Z",
            "merged_at": "2026-06-02T09:00:00Z",
        },
        {
            "project_id": 481747,
            "iid": 2,
            "state": "opened",
            "created_at": "2026-06-01T19:00:00Z",
            "lifecycle_observed_at": "2026-06-15T19:00:00Z",
        },
        {
            "project_id": 481747,
            "iid": 3,
            "state": "opened",
            "created_at": "2026-06-01T19:00:00Z",
            "lifecycle_observed_at": "2026-06-04T19:00:00Z",
        },
    ]

    def june_first_rate():
        _, result = build_report(source, anonymize=True, costs=False, lang="en")
        windows = result["trends"]["rolling_14_days"]
        return next(row for row in windows if row["date"] == "2026-06-01").get(
            "merge_completion_rate"
        )

    assert june_first_rate() is None
    source["scope"]["updated_at"] = "2026-06-15T23:59:59.999999Z"
    assert june_first_rate() == ratio(1, 2)


def test_calendar_uses_retry_job_day_and_enforces_exact_capture_time():
    source = _snapshot()
    source["scope"].update(start="2026-05-31", end="2026-06-01", updated_at="2026-06-01T12:00:00Z")
    record = source["records"][0]
    record.update(created_at="2026-05-31T23:00:00Z", merged_at="2026-06-01T12:00:00.1Z")
    source["records"][1].update(created_at="2026-06-01T12:00:00.1Z")
    first_pipeline = "2026-05-31T23:30:00Z"
    record["runs"] = [
        {"pipeline_created_at": first_pipeline, "status": "failed"},
        {
            "pipeline_created_at": first_pipeline,
            "created_at": "2026-06-01T12:00:00Z",
            "status": "failed",
        },
        {
            "pipeline_created_at": first_pipeline,
            "created_at": "2026-06-01T12:00:00.1Z",
            "status": "failed",
        },
    ]
    observed, later, _ = record["reviews"]
    record["reviews"] = [
        {**observed, "created_at": "2026-06-01T12:00:00Z"},
        {**later, "created_at": "2026-06-01T12:00:00.1Z"},
    ]
    _, report = build_report(source, anonymize=True, costs=True, lang="en")
    sunday, monday = report["trends"]["daily"]
    assert (sunday["attempts"], monday["attempts"]) == (1, 1)
    assert (sunday["opened"], monday["opened"], monday["merged"]) == (1, 0, 0)
    assert (monday["publications"], monday["tokens"], monday["estimated_usd"]) == (1, 13, 0.132)
    assert report["overview"]["lifecycle"]["merged"] == 1
    assert report["delivery"]["attempts"] == 3


def test_inactivity_uses_snapshot_time_and_reactions_require_current_coverage():
    source = _snapshot()
    source["scope"].update(updated_at="2026-04-15T12:00:00Z")
    first, second = source["records"]
    first.update(state="opened")
    for row in (first, second):
        row["completeness"].update(discussions="complete", versions="complete")
    first["process"].update(
        latest_meaningful_activity_at="2026-04-04T12:00:00Z",
        human_reactions_comparable=True,
        author_reactions_to_assigned_review=0,
    )
    second["process"].update(
        latest_meaningful_activity_at="2026-02-27T12:00:00Z",
        human_reactions_comparable=True,
        author_reactions_to_assigned_review=1000,
    )
    second["completeness"]["reactions"] = "unavailable"
    _, report = build_report(source, anonymize=True, costs=False, lang="en")
    process = report["process"]
    assert report["scope"]["observed_through"].startswith("2026-03-01")
    assert process["open_inactivity"] == {"days_7_13": 1, "days_30_plus": 1}
    assert process["author_reaction_coverage"] == ratio(1, 2)
    assert process["author_reactions_to_assigned_review"] == ratio(0, 1)
    assert process["process_counts"]["author_reactions_to_assigned_review"] == 0
    assert process["process_field_coverage"]["author_reactions_to_assigned_review"] == ratio(1, 2)
    second["completeness"]["versions"] = "partial"
    _, partial = build_report(source, anonymize=True, costs=False, lang="en")
    assert partial["process"]["open_inactivity"] == {"days_7_13": 1, "unknown": 1}


def test_preparing_and_canceling_jobs_are_nonterminal():
    source = _snapshot()
    for run, state in zip(source["records"][0]["runs"], ("preparing", "canceling"), strict=True):
        run["status"] = state
    _, report = build_report(source, anonymize=True, costs=False, lang="en")
    assert report["delivery"]["statuses"] == {"preparing": 1, "canceling": 1}
    assert report["delivery"]["failed_created_attempts"] == ratio(0, 2)
    assert sum(day["failed_attempts"] for day in report["trends"]["daily"]) == 0


def test_project_path_reuse_keeps_adoption_and_drilldowns_distinct():
    source = _snapshot()
    source["scope"].update(start="2025-12-01", end="2026-03-15", updated_at="2026-03-16T00:00:00Z")
    adopted = datetime(2026, 2, 1, tzinfo=UTC)
    source["projects"][1].update(path="synthetic/team", access="unavailable")
    source["records"] = [
        {
            **row,
            "project_id": project["id"],
            "iid": 91224 + index,
            "web_url": f"https://gitlab.example.test/synthetic/team/-/merge_requests/{91224 + index}",
        }
        for project in source["projects"]
        for index, row in enumerate(_adoption_periods(adopted))
    ]
    named, named_report = build_report(source, anonymize=False, costs=False, lang="en")
    anonymous, anon_report = build_report(source, anonymize=True, costs=False, lang="en")
    for report in (named_report, anon_report):
        assert report["overview"]["projects_with_merge_requests"] == 2
        assert report["overview"]["projects_with_attempts"] == 2
        assert report["adoption"]["eligible_projects"] == 2
        assert report["adoption"]["effect"]["after"] == ratio(20, 20)
    assert [row["project"] for row in named_report["projects"]] == [
        "synthetic/team (1)",
        "synthetic/team (2)",
    ]
    assert [row["project"] for row in anon_report["projects"]] == ["Project 01", "Project 02"]
    details = named.split('<section id="details">', 1)[1]
    assert "<summary>synthetic/team (1)</summary>" in details
    assert "<summary>synthetic/team (2)</summary>" in details
    assert details.count("!91224") == 2
    assert "https://gitlab.example.test/" not in details
    assert "synthetic/team" not in anonymous and "!91224" not in anonymous


@pytest.mark.parametrize(
    ("host", "url", "linked"),
    [
        (
            "gitlab.example.test:8443",
            "https://gitlab.example.test:8443/forge/synthetic/team/-/merge_requests/247915",
            True,
        ),
        ("", "https:///other.example.test/synthetic/team/-/merge_requests/247915", False),
        (
            "gitlab.example.test",
            "https://gitlab.example.test/forge/other/team/-/merge_requests/247915",
            False,
        ),
        (
            "gitlab.example.test",
            "https://gitlab.example.test/forge/synthetic/team/-/merge_requests/247916",
            False,
        ),
        (
            "gitlab.example.test",
            "https://gitlab.example.test/forge/synthetic/team/-/merge_requests/247915?redirect=1",
            False,
        ),
        (
            "gitlab.example.test",
            "https://gitlab.example.test/other/../forge/synthetic/team/-/merge_requests/247915",
            False,
        ),
    ],
)
def test_offline_links_require_nonempty_https_authority_and_exact_project_mr_path(
    host, url, linked
):
    source = _snapshot()
    source["scope"].update(host=host, base_path="/forge")
    source["records"][0]["web_url"] = url
    rendered, _ = build_report(source, anonymize=False, costs=False, lang="en")
    links = _Links()
    links.feed(rendered)
    assert (url in links.links) is linked
    assert "!247915" in rendered


def test_legacy_dlp_reason_counts_remain_distinct_from_current_public_filters():
    reviews = [
        {
            "recognized": True,
            "outcome": "complete_publication_filtered",
            "publication_filter": {
                "state": "publication-filtered",
                "historical_reason_counts": {"pii": 3},
            },
        },
        {
            "recognized": True,
            "outcome": "complete_publication_filtered",
            "publication_filter": {
                "state": "publication-filtered",
                "public_output": {"reason_counts": {"pii": 1}},
            },
        },
        {
            "recognized": True,
            "outcome": "complete",
            "publication_filter": {
                "state": "private-sanitized",
                "private_sanitization": {"fields": 2, "reason_counts": {"pii": 2}},
            },
        },
    ]
    values = technical_summary(reviews, {}, prices={}, costs=False)["publication_dlp"]
    assert values["historical_reasons"] == {"pii": 3}
    assert values["reasons"] == {"pii": 1}
    assert values["private_sanitization"] == {"pii": 2}


def test_named_model_ids_remain_literal_and_active_job_states_are_localized():
    source = _snapshot()
    record = source["records"][0]
    record["reviews"][0]["model"] = "medium"
    record["runs"] = [
        {"status": status, "created_at": "2026-01-19T10:00:00Z"}
        for status in ("created", "pending", "running", "scheduled", "waiting_for_resource")
    ]
    named, report = build_report(source, anonymize=False, costs=False, lang="ru")
    assert any(row["model"] == "medium" for row in report["technical"]["models"])
    assert "<td>medium</td>" in named and "<td>Средние</td>" not in named
    for status in ("Создано", "В очереди", "Выполняется", "Запланировано", "Ожидает ресурса"):  # noqa: RUF001
        assert f'<th scope="row">{status}</th>' in named
    anon, _ = build_report(source, anonymize=True, costs=False, lang="ru")
    assert "<td>Модель 01</td>" in anon


def test_empty_recent_chart_shows_its_range_while_earlier_usage_stays_in_table():
    source = _snapshot()
    source["scope"].update(end="2026-06-01", updated_at="2026-06-02T00:00:00Z")
    html, report = build_report(source, anonymize=True, costs=True, lang="en")
    weekly = report["trends"]["weekly"]
    assert any(row["tokens"] == 18 for row in weekly[:-12])
    assert all(row["tokens"] is None for row in weekly[-12:])
    figure = html.split("<figcaption>Reported tokens per week</figcaption>", 1)[1].split(
        "</figure>", 1
    )[0]
    assert weekly[-12]["week_start"] in figure and weekly[-1]["week_start"] in figure
    assert "No observations in the shown period" in figure


def test_adoption_excludes_early_terminal_and_still_open_mrs_of_equal_age():
    adopted = datetime(2026, 2, 1, tzinfo=UTC)
    horizon = adopted + timedelta(days=40)
    observed_at = horizon.isoformat()
    opened = (horizon - timedelta(days=2)).isoformat()
    mature = [
        row
        for row in _adoption_periods(adopted)
        if row["created_at"] < (adopted + timedelta(days=27)).isoformat()
    ]
    early = [
        {"created_at": opened, "state": "opened", "lifecycle_observed_at": observed_at},
        {
            "created_at": opened,
            "state": "merged",
            "merged_at": observed_at,
            "lifecycle_observed_at": observed_at,
        },
    ]
    baseline = adoption_comparison({1: mature}, {1: "Project 01"}, horizon, captured_at=horizon)
    report = adoption_comparison(
        {1: mature + early}, {1: "Project 01"}, horizon, captured_at=horizon
    )
    assert report["eligible_projects"] == 0
    assert (
        report["exclusions"]["unobserved_completion_window"]
        == baseline["exclusions"]["unobserved_completion_window"] + 2
    )


def test_adoption_uses_job_time_and_only_skips_self_service_with_complete_evidence():
    adopted = datetime(2026, 2, 1, tzinfo=UTC)
    horizon = adopted + timedelta(days=60)
    rows = _adoption_periods(adopted)
    first_job = next(row["runs"][0] for row in rows if row["runs"])
    first_job["pipeline_created_at"] = (adopted - timedelta(days=2)).isoformat()
    last_terminal = rows[-2]
    last_terminal["process"].update(terminal_actor_is_author=True, involved_reviewer_count=0)
    last_terminal["completeness"] = {"discussions": "complete", "approvals": "unavailable"}
    report = adoption_comparison({1: rows}, {1: "Project 01"}, horizon, captured_at=horizon)
    assert report["eligible_projects"] == 1
    assert report["projects"][0]["adoption_at"] == adopted.isoformat()
    assert report["effect"]["after"] == ratio(10, 10)
    last_terminal["completeness"]["approvals"] = "complete"
    verified = adoption_comparison({1: rows}, {1: "Project 01"}, horizon, captured_at=horizon)
    assert verified["exclusions"]["self_service"] == 1
    assert verified["eligible_projects"] == 0


def test_edited_terminal_note_is_latest_by_normalized_content_timestamp():
    source = _snapshot()
    source["records"] = [source["records"][0]]
    source["records"][0]["reviews"] = [
        {
            "created_at": "2026-01-19T10:00:00Z",
            "updated_at": "2026-01-24T11:00:00+01:00",
            "result_kind": "terminal_lifecycle",
            "outcome": "terminal_merged",
        },
        {"created_at": "2026-01-24T09:30:00Z", "result_kind": "status", "outcome": "failed"},
    ]
    _, report = build_report(source, anonymize=True, costs=False, lang="en")
    assert report["delivery"]["latest_observed_outcomes"] == {"terminal_merged": 1}
    assert report["delivery"]["mrs_with_successful_job_and_latest_failed_result"] == 0


def test_retained_intervals_preserve_history_without_claiming_a_fresh_tail():
    source = _snapshot()
    fresh = source["records"][0]
    fresh["revisions"] = [fresh["revisions"][1]]
    stale = source["records"][1]
    stale["revisions"] = list(fresh["revisions"])
    _, report = build_report(source, anonymize=True, costs=False, lang="en")
    flow = report["process"]["revision_flow"]
    assert flow["comparable_intervals"] == 2
    assert flow["mrs_with_fresh_final_revision"] == 1
    assert flow["mrs_with_no_observed_change"] == 1
    assert flow["mrs_with_unknown_change"] == 1


def test_current_project_model_prices_only_unattributed_reviews_and_keeps_sources_separate():
    source = _snapshot()
    current_model = "synthetic/private-project-configuration"
    source["projects"][0].update(
        cost_model=current_model, cost_model_observed_at="2026-03-02T09:01:00Z"
    )
    source["prices"][current_model] = {
        "prompt": "0.02",
        "completion": "0.03",
        "input_cache_read": "0.005",
    }
    record, other = source["records"]
    baseline = {"recognized": True, "outcome": "complete", "result_kind": "model"}
    record["reviews"].extend(
        [
            {
                **baseline,
                "created_at": "2026-01-20T14:00:00Z",
                "tokens": {"input": 20, "output": 5, "cached": 2, "total": 25},
            },
            {
                **baseline,
                "created_at": "2026-01-20T15:00:00Z",
                "model": "synthetic/unpriced-review-alias",
                "tokens": {"input": 1, "output": 1},
            },
        ]
    )
    other.update(
        project_id=732145,
        reviews=[
            {**baseline, "created_at": "2026-02-25T10:00:00Z", "tokens": {"input": 1, "output": 1}}
        ],
    )
    doc, report = build_report(source, anonymize=True, costs=True, lang="ru")
    cost = report["technical"]["cost"]
    assert cost["estimated_usd"] == 0.652
    assert cost["pricing_coverage"] == ratio(2, 5)
    assert cost["usage_coverage"] == ratio(4, 5)
    assert cost["by_source"] == {
        "publication_model": {
            "model_results": 2,
            "estimated_usd": 0.132,
            "pricing_coverage": ratio(1, 2),
            "usage_coverage": ratio(2, 2),
        },
        "current_project_configuration": {
            "model_results": 2,
            "estimated_usd": 0.52,
            "pricing_coverage": ratio(1, 2),
            "usage_coverage": ratio(1, 2),
        },
        "unavailable": {
            "model_results": 1,
            "estimated_usd": None,
            "pricing_coverage": ratio(0, 1),
            "usage_coverage": ratio(1, 1),
        },
    }
    observed_breakdown = {row["model"]: row for row in report["technical"]["models"]}
    assert set(observed_breakdown) == {"Model 01", "Model 02", "unknown"}
    assert observed_breakdown["Model 01"]["estimated_usd"] == 0.132
    assert observed_breakdown["unknown"]["results"] == 3
    assert observed_breakdown["unknown"]["estimated_usd"] is None
    project = report["projects"][0]["technical"]["cost"]
    assert project["cost_model_observed_at"] == "2026-03-02T09:01:00+00:00"
    days = {row["date"]: row for row in report["trends"]["daily"]}
    assert days["2026-01-19"]["priced_publication_model_results"] == 1
    assert days["2026-01-19"]["estimated_usd"] == 0.132
    assert days["2026-01-20"]["priced_current_project_configuration_results"] == 1
    assert days["2026-01-20"]["estimated_usd"] == 0.52
    assert "Оценка по текущей настройке проекта" in doc
    assert "Модель из публикации" in doc
    exported = doc + json.dumps(report)
    assert "synthetic/" not in exported

    named, machine = build_report(source, anonymize=False, costs=True, lang="en")
    assert "Estimate based on current project configuration" in named
    assert current_model not in named + json.dumps(machine)

    disabled, machine = build_report(source, anonymize=True, costs=False, lang="en")
    exported = disabled + json.dumps(machine)
    for field in (
        "estimated_usd",
        "prices_at",
        "cost_model_observed_at",
        "current_project_configuration",
        "current project configuration",
    ):
        assert field not in exported


def test_rejected_model_line_never_prices_using_the_current_project_setting():
    source = _snapshot()
    priced_model = "synthetic-model-v1"
    source["prices"][priced_model] = source["prices"]["synthetic/private-model"]
    source["projects"][0].update(
        cost_model=priced_model, cost_model_observed_at="2026-03-02T09:01:00Z"
    )
    token_line = format_token_usage_summary({"usage": {"input": 80, "output": 15, "total": 95}})
    with_model = summarize_result(
        0, 0, 0, 0, review_model=priced_model, token_usage_summary=token_line
    )
    rejected = parse_publication(
        build_marked_note_body(
            summary_with_run_marker(
                with_model.replace(
                    f"- Review model v1: `{priced_model}`", "- Review model v1: malformed-alias"
                ),
                "a" * 32,
            )
        )
    )
    historical = parse_publication(
        build_marked_note_body(
            summary_with_run_marker(
                summarize_result(0, 0, 0, 0, token_usage_summary=token_line),
                "b" * 32,
            )
        )
    )
    assert rejected is not None and rejected["model_rejected"] is True and "model" not in rejected
    assert historical is not None and "model_rejected" not in historical
    source["records"] = [source["records"][0]]
    source["records"][0]["reviews"] = [
        {**rejected, "created_at": "2026-01-19T10:00:00Z"},
        {**historical, "created_at": "2026-01-20T10:00:00Z"},
        {**rejected, "created_at": "2026-01-21T10:00:00Z", "model": priced_model},
    ]
    rendered, report = build_report(source, anonymize=False, costs=True, lang="en")
    technical = report["technical"]
    assert technical["cost"]["estimated_usd"] == 1.1
    assert technical["cost"]["pricing_coverage"] == ratio(1, 3)
    assert technical["cost"]["usage_coverage"] == ratio(3, 3)
    assert technical["cost"]["by_source"]["unavailable"]["model_results"] == 2
    assert technical["cost"]["by_source"]["current_project_configuration"][
        "pricing_coverage"
    ] == ratio(1, 1)
    assert technical["models"][0]["model"] == "unknown"
    days = {row["date"]: row for row in report["trends"]["daily"]}
    assert [days[f"2026-01-{day}"]["estimated_usd"] for day in (19, 20, 21)] == [None, 1.1, None]
    assert "malformed-alias" not in rendered + json.dumps(report)
    assert priced_model not in rendered + json.dumps(report)


@pytest.mark.parametrize(
    ("total", "omit_residual", "estimate"),
    [(95, False, 0.96), (100, False, None), (100, True, None)],
)
def test_cost_requires_all_reported_tokens_to_be_priced(total, omit_residual, estimate):
    source = _snapshot()
    model = "synthetic-model-v1"
    source["prices"][model] = source["prices"]["synthetic/private-model"]
    token_line = format_token_usage_summary(
        {
            "usage": {
                "input": 80,
                "output": 15,
                "total": total,
                "cached_tokens": 20,
                "reasoning_tokens": 5,
            }
        }
    )
    publication = parse_publication(
        build_marked_note_body(
            summary_with_run_marker(
                summarize_result(0, 0, 0, 0, review_model=model, token_usage_summary=token_line),
                "a" * 32,
            )
        )
    )
    assert publication is not None and publication["model"] == model
    assert publication["tokens"]["cached"] == 20 and publication["tokens"]["reasoning"] == 5
    assert publication["tokens"].get("other", 0) == total - 95
    if omit_residual:
        del publication["tokens"]["other"]
    source["records"] = [source["records"][0]]
    source["records"][0]["reviews"] = [{**publication, "created_at": "2026-01-19T10:00:00Z"}]
    _, report = build_report(source, anonymize=True, costs=True, lang="en")
    technical = report["technical"]
    assert technical["counts"]["tokens"]["total"] == total
    assert technical["cost"]["estimated_usd"] == estimate
    assert technical["cost"]["usage_coverage"] == ratio(1, 1)
    assert technical["cost"]["by_source"]["publication_model"]["pricing_coverage"] == ratio(
        int(estimate is not None), 1
    )
    day = next(row for row in report["trends"]["daily"] if row["date"] == "2026-01-19")
    assert (day["tokens"], day["estimated_usd"]) == (total, estimate)
