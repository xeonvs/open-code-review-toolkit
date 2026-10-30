"""Pure source-free summaries of diagnostic observations, without inferred verdicts."""

from __future__ import annotations

from collections import Counter
from typing import Any


def render_report(identity: str, run: dict[str, Any]) -> str:
    """Group roles/proof and aggregate probes without treating hits as defects."""

    hits = run["hits"]
    groups = Counter((hit["reason"], hit["detector"], hit["role"], hit["proof"]) for hit in hits)
    units: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    children: set[tuple[str, str, str]] = set()
    for hit in hits:
        units.setdefault((hit["slot"], hit["unit"]), {})[hit["role"]] = hit
        if hit["unit"]:
            children.add((hit["slot"], hit["role"], hit["reason"]))
    whole = [hit for hit in hits if hit["unit"] == 0]
    repeated = sum((hit["slot"], hit["role"], hit["reason"]) in children for hit in whole)
    single_role = sum(len(roles) == 1 for roles in units.values())
    different = sum(
        len(roles) == 2
        and any(
            roles["text"][key] != roles["existing_code"][key]
            for key in ("reason", "detector", "proof")
        )
        for roles in units.values()
    )
    lines = [
        "# Private DLP audit",
        "",
        f"Run: `{identity}`",
        f"Complete: {run['complete']}",
        f"Evaluated units: {run['units']}/{run['expected_units']} (each in two roles)",
        f"Rejected role units: {len(hits)}",
        "",
        f"Distinct line locations: {sum(unit != 0 for _slot, unit in units)}",
        f"Whole-file role probes: {len(whole)}",
        f"Whole-file probes sharing a child primary reason: {repeated}",
        f"Whole-file probes without a child primary reason: {len(whole) - repeated}",
        f"Locations with one rejecting role: {single_role}",
        f"Locations with differing rejecting role facts: {different}",
        "",
        "## Top ten primary detector / role / source-proof groups",
        "",
    ]
    for (reason, detector, role, proof), count in sorted(
        groups.items(), key=lambda row: (-row[1], row[0])
    )[:10]:
        lines.append(f"- {reason} / {detector} / {role} / source-proof={proof}: {count}")
    if run["errors"]:
        lines.extend(("", "## Incomplete evaluation", ""))
        for reason, count in sorted(Counter(error["reason"] for error in run["errors"]).items()):
            lines.append(f"- {reason}: {count}")
    lines.extend(
        (
            "",
            "Locations and exact identities are in the authenticated JSON report and corpus manifest.",
            "Groups describe primary observations, not causal verdicts or a false-positive rate.",
            "A whole-file probe may repeat a line observation; proof absence does not prove a detector defect.",
            "Incomplete runs cannot establish admissions or protection loss. Raw source and matched values are absent.",
        )
    )
    return "\n".join(lines) + "\n"
