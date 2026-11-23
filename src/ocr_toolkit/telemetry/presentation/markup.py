"""Escaped HTML, tables and inline charts for the standalone report."""

import html
from typing import Any

from .labels import ENGLISH, RUSSIAN

REPORT_CSS = """
:root{color-scheme:light;--ink:#202a38;--muted:#506070;--line:#d9e3ed;--fill:#edf4fa;--accent:#185d90}
*{box-sizing:border-box}body{margin:0;background:#f2f6fa;color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1260px;margin:auto;padding:clamp(1rem,3vw,2.7rem)}h1{margin:0;font-size:clamp(2.3rem,5vw,3.6rem)}
h2{margin-top:0;font-size:1.55rem}h3{font-size:1.12rem}a{color:var(--accent)}p{max-width:75ch}
header{padding:1.8rem 0}nav{display:flex;gap:.6rem 1.2rem;flex-wrap:wrap;margin:1.4rem 0}
section{padding:clamp(1rem,3vw,2rem);margin:1.1rem 0;background:#fff;border:1px solid var(--line);border-radius:12px}
.num-grid,.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:1rem}
.num-grid div{background:var(--fill);padding:1rem;border-radius:8px}.num-grid dt{color:var(--muted);font-size:.93rem}
.num-grid dd{margin:0;font-size:1.9rem;font-weight:700;font-variant-numeric:tabular-nums}
figure{margin:0;padding:1rem;border:1px solid var(--line);border-radius:8px;min-width:0}figcaption{font-weight:600;margin-bottom:.8rem}
.bar{display:grid;grid-template-columns:7.2rem minmax(1rem,1fr) minmax(3rem,auto);align-items:center;gap:.45rem;margin:.24rem 0;font-size:.86rem}
meter{display:block;width:100%;height:1.1rem;accent-color:var(--accent)}.bar span:last-child{text-align:right;font-variant-numeric:tabular-nums}
details{margin:.65rem 0;border:1px solid var(--line);border-radius:7px;padding:.4rem .7rem}summary{font-weight:600;cursor:pointer}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.92rem}th,td{text-align:left;padding:.45rem .65rem;border-bottom:1px solid var(--line);vertical-align:top}
thead th{background:var(--fill)}td,th{overflow-wrap:anywhere}td{font-variant-numeric:tabular-nums}tbody th{width:44%}thead th{width:auto}
.muted,footer{color:var(--muted)}footer{margin-top:1.6rem}.archive{font-size:.84rem;color:var(--muted);font-weight:400}
"""


class ReportMarkup:
    def __init__(self, lang: str, *, anonymize: bool) -> None:
        self.lang = lang
        self.labels = ENGLISH | RUSSIAN if lang == "ru" else ENGLISH
        self.anonymous = anonymize

    def label(self, key: str) -> str:
        if "." in key:
            return " · ".join(self.label(part) for part in key.split("."))
        text = self.labels.get(key)
        return html.escape(text if text else key.replace("_", " ").capitalize())

    def scalar(self, value: Any, *, field: str | None = None) -> str:
        if value is None:
            return "—"
        if type(value) is bool:
            if self.lang == "ru":
                return "Да" if value else "Нет"
            return "Yes" if value else "No"
        if type(value) is int:
            return f"{value:,}".replace(",", "\u202f")
        if type(value) is float:
            return f"{value:.6g}"
        if self.lang == "ru" and self.anonymous and isinstance(value, str):
            if field == "project" and value.startswith("Project "):
                return "Проект " + html.escape(value.removeprefix("Project "))
            if field == "model" and value.startswith("Model "):
                return "Модель " + html.escape(value.removeprefix("Model "))
        if (
            field in {"state", "access", "discovery"}
            and isinstance(value, str)
            and value in self.labels
        ):
            return self.label(value)
        return html.escape(str(value))

    def folded(self, title: str, body: str) -> str:
        return f"<details><summary>{title}</summary>{body}</details>"

    def table(self, headers: list[str], contents: list[list[str]]) -> str:
        heading = "".join(f'<th scope="col">{value}</th>' for value in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>" for row in contents
        )
        return f'<div class="table-wrap"><table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>'

    def value(self, value: Any, *, field: str | None = None) -> str:
        if isinstance(value, dict):
            if set(value) == {"numerator", "denominator", "value"}:
                if value["value"] is None:
                    return "—"
                return f"{value['value']:.1%} ({self.scalar(value['numerator'])}/{self.scalar(value['denominator'])})"
            return self.mapping(value)
        if isinstance(value, list):
            if not value:
                return f'<p class="muted">{self.label("no_data")}</p>'
            if all(isinstance(item, dict) for item in value):
                keys = list(dict.fromkeys(key for item in value for key in item))
                if keys:
                    return self.table(
                        [self.label(key) for key in keys],
                        [[self.value(item.get(key), field=key) for key in keys] for item in value],
                    )
            return "<ul>" + "".join(f"<li>{self.scalar(item)}</li>" for item in value) + "</ul>"
        return self.scalar(value, field=field)

    def mapping(self, values: dict[str, Any]) -> str:
        if not values:
            return f'<p class="muted">{self.label("no_data")}</p>'
        literals, sections = [], []
        for key, value in values.items():
            label = self.label(key)
            nested = isinstance(value, (dict, list))
            ratio = isinstance(value, dict) and set(value) == {"numerator", "denominator", "value"}
            if nested and not ratio:
                sections.append(self.folded(label, self.value(value)))
            else:
                literals.append(
                    f'<tr><th scope="row">{label}</th><td>{self.value(value, field=key)}</td></tr>'
                )
        table = (
            f'<div class="table-wrap"><table><tbody>{"".join(literals)}</tbody></table></div>'
            if literals
            else ""
        )
        return table + "".join(sections)

    def panel(self, key: str, content: str) -> str:
        return f'<section id="{key}"><h2>{self.label(key)}</h2>{content}</section>'

    def note(self, key: str) -> str:
        return f'<p class="muted">{self.label(key)}</p>'

    def cards(self, values: dict[str, Any]) -> str:
        cards = "".join(
            f"<div><dt>{self.label(key)}</dt><dd>{self.value(value)}</dd></div>"
            for key, value in values.items()
        )
        return f'<dl class="num-grid">{cards}</dl>'

    def chart(
        self, title: str, field: str, periods: list[dict[str, Any]], *, proportion: bool = False
    ) -> str:
        recent = [
            (period.get("week_start") or period["date"], period.get(field))
            for period in periods[-12:]
        ]
        known = [value for _, value in recent if isinstance(value, (int, float))]
        if not known:
            profile = self.note("no_data_in_chart" if recent else "no_data")
        else:
            ceiling = 1 if proportion else max(max(known), 1e-12)
            profile = "".join(
                f'<div class="bar"><time>{html.escape(day)}</time>'
                + (
                    f'<meter min="0" max="{ceiling}" value="{value}" aria-label="{self.label(field)}"></meter>'
                    if value is not None
                    else '<span aria-hidden="true"></span>'
                )
                + f"<span>{f'{value:.1%}' if proportion and value is not None else self.scalar(value)}</span></div>"
                for day, value in recent
            )
        date_range = (
            f'<p class="muted">{self.label("chart_period")} {self.scalar(recent[0][0])} \u2013 {self.scalar(recent[-1][0])}</p>'
            if recent
            else ""
        )
        return f"<figure><figcaption>{self.label(title)}</figcaption>{date_range}{profile}</figure>"
