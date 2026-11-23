"""Entry points for authenticated collection and independent offline rendering."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from ocr_toolkit.common.language import resolve_review_language
from ocr_toolkit.telemetry.prices import capture_prices
from ocr_toolkit.telemetry.state import (
    SNAPSHOT,
    TelemetryError,
    private_directory,
    read_snapshot,
    save_report,
    save_snapshot,
)


def configure_parser(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="telemetry_action", required=True)
    collect = actions.add_parser("collect", help="Read GitLab through the active glab context.")
    report = actions.add_parser("report", help="Render private HTML and aggregate JSON offline.")
    for action in (collect, report):
        action.add_argument(
            "--state-dir", type=Path, help="Private physical directory outside Git worktrees."
        )
        action.add_argument(
            "--no-costs", action="store_true", help="Omit pricing and cost information."
        )
    collect.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="First date inclusive (default: 2026-11-01).",
    )
    collect.add_argument(
        "--to",
        dest="end",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Last date inclusive (default: today in UTC).",
    )
    collect.add_argument("--bot", help="Exact GitLab username (default: mr.bot).")
    collect.add_argument(
        "--job-name",
        action="append",
        help="Review job name, repeatable (default: open_code_review).",
    )
    collect.add_argument(
        "--project", action="append", help="Exact GitLab project ID or namespace/path, repeatable."
    )
    collect.add_argument(
        "--update", action="store_true", help="Refresh the existing snapshot in its original scope."
    )
    report.add_argument(
        "--lang",
        metavar="LANGUAGE",
        help="English or Russian name or language tag. Overrides OCR_REVIEW_LANGUAGE.",
    )
    report.add_argument(
        "--anonymize", action="store_true", help="Use report-local labels and omit MR links."
    )


def _language(explicit: str | None) -> str:
    label = resolve_review_language(explicit).lower().split("-")[0]
    if label in {"ru", "russian"}:
        return "ru"
    if label not in {"en", "english", "english (uk)", "english (us)"}:
        print("Telemetry report language unavailable; using English.", file=sys.stderr)
    return "en"


def _collect(directory: int, args: argparse.Namespace) -> None:
    from ocr_toolkit.telemetry.collection import collect

    if not args.update and SNAPSHOT in os.listdir(directory):
        raise TelemetryError("A snapshot already exists. Use --update or a fresh --state-dir.")
    previous = read_snapshot(directory) if args.update else None
    scope = previous["scope"] if previous else {}
    start = args.start or date.fromisoformat(scope.get("start", "2026-11-01"))
    rolling = args.end is None and (previous is None or previous.get("rolling_end", False))
    end = args.end or (datetime.now(UTC).date() if rolling else date.fromisoformat(scope["end"]))
    if start > end:
        raise TelemetryError("The start date must be on or before the end date.")
    if (end - start).days >= 10_000:
        raise TelemetryError("Select a period of at most 10,000 days.")
    if previous and any((args.start, args.bot, args.project, args.job_name)):
        raise TelemetryError(
            "An update reuses the original bot, start date, projects and job names."
        )
    if previous and end < date.fromisoformat(scope["end"]):
        raise TelemetryError("An update cannot shorten the snapshot period.")
    snapshot = collect(
        previous=previous,
        projects=args.project or [],
        bot=args.bot or scope.get("bot", "mr.bot"),
        job_names=args.job_name or scope.get("job_names", ["open_code_review"]),
        collect_model=not args.no_costs,
        start=start.isoformat(),
        end=end.isoformat(),
    )
    snapshot["rolling_end"] = rolling
    snapshot["costs_enabled"] = not args.no_costs
    models = {
        model
        for record in snapshot["records"]
        for review in record["reviews"]
        if isinstance(model := review.get("model"), str) and model
    }
    models.update(
        model
        for project in snapshot["projects"]
        if isinstance(model := project.get("cost_model"), str) and model
    )
    lookup = not args.no_costs and bool(models)
    prices, captured = capture_prices() if lookup else (None, None)
    if prices is None and lookup:
        if previous and previous.get("prices"):
            prices, captured = previous["prices"], previous["prices_at"]
            print("Price catalog unavailable; keeping the dated snapshot.", file=sys.stderr)
        else:
            print("Price catalog unavailable; token usage remains available.", file=sys.stderr)
    selected_prices = {model: prices[model] for model in models if prices and model in prices}
    snapshot.update(prices=selected_prices or None, prices_at=captured if selected_prices else None)
    save_snapshot(directory, snapshot)
    print(
        f"Snapshot saved. Projects: {len(snapshot['projects'])}. Merge requests: {len(snapshot['records'])}."
    )


def run(args: argparse.Namespace) -> int:
    directory = (
        args.state_dir
        or Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
        / "ocr-toolkit/telemetry"
    )
    collecting = args.telemetry_action == "collect"
    try:
        try:
            directory = directory.expanduser().absolute()
        except RuntimeError:
            raise TelemetryError("Cannot resolve the telemetry state directory.") from None
        if (not collecting or args.update) and not directory.exists():
            raise TelemetryError("Telemetry snapshot is unavailable. Run telemetry collect first.")
        with private_directory(directory, create=collecting and not args.update) as fd:
            if collecting:
                _collect(fd, args)
            else:
                from ocr_toolkit.telemetry.presentation import build_report

                snapshot: dict[str, Any] = read_snapshot(fd)
                lang = _language(args.lang)
                html, report = build_report(
                    snapshot,
                    lang=lang,
                    anonymize=args.anonymize,
                    costs=not args.no_costs and snapshot["costs_enabled"],
                )
                name = save_report(fd, html, report, lang)
                print(directory / name)
    except FileNotFoundError:
        print("Telemetry snapshot is unavailable. Run telemetry collect first.", file=sys.stderr)
        return 2
    except TelemetryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError, OverflowError):
        print(
            "Cannot process telemetry. Check the private directory, snapshot and collection configuration.",
            file=sys.stderr,
        )
        return 2
    return 0
