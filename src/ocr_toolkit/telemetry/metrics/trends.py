"""Calendar-aligned opening, delivery, usage, and completion trends."""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from ocr_toolkit.telemetry.publications.grammar import model_publication

from .common import (
    DAY,
    WINDOW,
    attempt_created_at,
    completion,
    count,
    data,
    distribution,
    duration,
    ratio,
    review_rows,
    rows,
    terminal,
    timestamp,
)
from .cost import observe_cost
from .delivery import adjusted_status, job_status, supported_review


def calendar_trends(
    records: list[dict[str, Any]],
    start: datetime,
    horizon: datetime,
    *,
    prices: dict[str, Any],
    costs: bool,
    project_models: dict[int, str],
) -> dict[str, Any]:
    first, last = start.date(), horizon.date()
    day_count = max(0, (last - first).days + 1)
    if day_count > 10_000:
        raise ValueError("invalid telemetry period length")
    daily: dict[date, Counter[str]] = {
        first + timedelta(days=offset): Counter() for offset in range(day_count)
    }
    week_durations: dict[date, list[float]] = defaultdict(list)
    week_mrs: dict[date, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    daily_price: dict[date, Decimal] = defaultdict(Decimal)

    def event_day(observed: datetime | None) -> date | None:
        return observed.date() if observed is not None and start <= observed <= horizon else None

    for index, record in enumerate(records):
        project_model = project_models.get(record["project_id"])
        opened = event_day(timestamp(record.get("created_at")))
        finished = event_day(timestamp(terminal(record)))
        if opened is not None:
            values = daily[opened]
            values["opened"] += 1
            if (completed := completion(record, horizon)) is not None:
                values["eligible_for_14_day_completion"] += 1
                values["merged_within_14_days"] += completed
        if finished is not None:
            daily[finished]["merged" if record.get("state") == "merged" else "closed"] += 1
            if (elapsed := duration(record.get("created_at"), terminal(record))) is not None:
                week_durations[finished - timedelta(days=finished.weekday())].append(elapsed)
        for run in rows(record.get("runs")):
            ran = event_day(attempt_created_at(run))
            if ran is None:
                continue
            daily[ran]["attempts"] += 1
            cohort = week_mrs[ran - timedelta(days=ran.weekday())]
            cohort["mrs_with_attempts"].add(index)
            status = job_status(run)
            if status == "success":
                daily[ran]["gitlab_successful_attempts"] += 1
            if adjusted_status(run) == "success":
                daily[ran]["successful_attempts"] += 1
                cohort["mrs_with_successful_attempt"].add(index)
            elif status in {"failed", "canceled", "unknown"}:
                daily[ran]["failed_attempts"] += 1
                cohort["mrs_with_failed_attempt"].add(index)
        for review in review_rows(record):
            published = event_day(timestamp(review.get("created_at")))
            if published is None or review.get("recognized", True) is False:
                continue
            values = daily[published]
            values["publications"] += 1
            values["delivered_reviews"] += supported_review({"reviews": [review]})
            if not model_publication(review):
                continue
            values["model_results"] += 1
            if (tokens := count(data(review.get("tokens")).get("total"))) is not None:
                values["tokens"] += tokens
                values["results_with_tokens"] += 1
            if costs:
                observation = observe_cost(review, prices, project_model=project_model)
                if observation.estimate is not None:
                    values["priced_results"] += 1
                    values[f"priced_{observation.source}_results"] += 1
                    daily_price[published] += observation.estimate
    fields = (
        "opened",
        "merged",
        "closed",
        "attempts",
        "successful_attempts",
        "gitlab_successful_attempts",
        "failed_attempts",
        "publications",
        "delivered_reviews",
        "model_results",
        "results_with_tokens",
        "eligible_for_14_day_completion",
        "merged_within_14_days",
        *(
            (
                "priced_results",
                "priced_publication_model_results",
                "priced_current_project_configuration_results",
            )
            if costs
            else ()
        ),
    )
    daily_rows, rolling_rows = [], []
    rolling: Counter[str] = Counter()
    weeks: dict[date, Counter[str]] = defaultdict(Counter)
    week_prices: dict[date, Decimal] = defaultdict(Decimal)
    rolling_price = Decimal(0)
    for day, values in daily.items():
        day_values = {name: values[name] for name in fields}
        cost_fields = (
            {"estimated_usd": float(daily_price[day]) if values["priced_results"] else None}
            if costs
            else {}
        )
        daily_rows.append(
            {
                "date": day.isoformat(),
                **day_values,
                "tokens": values["tokens"] if values["results_with_tokens"] else None,
                **cost_fields,
            }
        )
        monday = day - timedelta(days=day.weekday())
        weeks[monday].update(values)
        week_prices[monday] += daily_price[day]
        rolling.update(values)
        rolling.subtract(daily.get(day - 14 * DAY, Counter()))
        rolling_price += daily_price[day] - daily_price[day - 14 * DAY]
        if day - first >= 13 * DAY:
            trend_row: dict[str, Any] = {
                "date": day.isoformat(),
                **{name: rolling[name] for name in fields},
                "tokens": rolling["tokens"] if rolling["results_with_tokens"] else None,
            }
            if datetime.combine(day, time.max, tzinfo=UTC) + WINDOW <= horizon:
                trend_row["merge_completion_rate"] = ratio(
                    rolling["merged_within_14_days"], rolling["eligible_for_14_day_completion"]
                )
            if costs:
                trend_row["estimated_usd"] = (
                    float(rolling_price) if rolling["priced_results"] else None
                )
            rolling_rows.append(trend_row)
    weekly_rows: list[dict[str, Any]] = [
        {
            "week_start": day.isoformat(),
            "complete_week": day >= first
            and (day + 7 * DAY) <= (horizon + datetime.resolution).date(),
            **{name: values[name] for name in fields},
            "tokens": values["tokens"] if values["results_with_tokens"] else None,
            **{name: len(members) for name, members in week_mrs[day].items()},
            "opening_to_completion": distribution(week_durations[day]),
            **(
                {"estimated_usd": float(week_prices[day]) if values["priced_results"] else None}
                if costs
                else {}
            ),
        }
        for day, values in weeks.items()
    ]
    complete_weeks = [week for week in weekly_rows if week["complete_week"]]
    comparison = None
    if len(complete_weeks) >= 8:
        comparison = {}
        for phase, weeks_sample in (
            ("earlier_four_weeks", complete_weeks[-8:-4]),
            ("latest_four_weeks", complete_weeks[-4:]),
        ):
            comparison[phase] = {
                "start": weeks_sample[0]["week_start"],
                "end": weeks_sample[-1]["week_start"],
                **{name: sum(week[name] for week in weeks_sample) for name in fields},
                "tokens": sum(week["tokens"] for week in weeks_sample if week["tokens"] is not None)
                if any(week["tokens"] is not None for week in weeks_sample)
                else None,
                **(
                    {
                        "estimated_usd": sum(
                            week["estimated_usd"]
                            for week in weeks_sample
                            if week["estimated_usd"] is not None
                        )
                        if any(week["estimated_usd"] is not None for week in weeks_sample)
                        else None
                    }
                    if costs
                    else {}
                ),
            }
    return {
        "daily": daily_rows,
        "rolling_14_days": rolling_rows,
        "weekly": weekly_rows,
        "four_week_comparison": comparison,
    }
