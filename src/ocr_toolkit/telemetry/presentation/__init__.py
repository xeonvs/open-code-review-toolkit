"""Render a self-contained, localized telemetry report and its aggregate JSON."""

from typing import Any

from ocr_toolkit.telemetry.metrics import aggregate_report

from .markup import REPORT_CSS, ReportMarkup
from .sections import report_sections


def build_report(
    snapshot: dict[str, Any],
    *,
    anonymize: bool,
    costs: bool,
    lang: str,
) -> tuple[str, dict[str, Any]]:
    """Render solely from the normalized snapshot with no subprocess or network I/O."""

    if lang not in {"en", "ru"}:
        raise ValueError("invalid telemetry report language")
    report, details = aggregate_report(snapshot, anonymize=anonymize, costs=costs)
    ui = ReportMarkup(lang, anonymize=anonymize)
    panels = report_sections(ui, report, details, costs=costs)
    navigation = "".join(f'<a href="#{key}">{ui.label(key)}</a>' for key in panels)
    scope = report["scope"]
    span = ui.scalar(scope["start"]) + " \u2013 " + ui.scalar(scope["end"])
    privacy = ui.note("privacy_note") if anonymize else ""
    document = (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{ui.label('title')}</title><style>{REPORT_CSS}</style></head><body><main>"
        f'<header><h1>{ui.label("title")}</h1><p class="muted">{span}</p>{privacy}<nav>{navigation}</nav></header>'
        + "".join(ui.panel(key, body) for key, body in panels.items())
        + f"<footer>{ui.note('method_note')}</footer></main></body></html>\n"
    )
    return document, report
