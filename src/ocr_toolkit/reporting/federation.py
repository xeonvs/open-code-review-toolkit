"""Pure hostile validation and reconciliation of content-free gateway receipts."""

from __future__ import annotations

import re
from typing import Any

COUNTERS = frozenset(
    {
        "attempted",
        "completed",
        "denied",
        "failed",
        "timed_out",
        "dlp_rejected",
        "oversized",
        "cache_hits",
        "single_flight",
    }
)
TERMINAL = frozenset({"completed", "denied", "failed", "timed_out"})
DENIAL_DIAGNOSTICS = frozenset({"dlp_rejected", "oversized"})
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def valid_receipt(value: Any) -> bool:
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "run_id", "state", "cleanup", "tools"}
        or value["schema"] != "ocr.federation/v1"
        or value["state"] != "finalized"
        or value["cleanup"] != "clean"
        or not isinstance(value["run_id"], str)
        or re.fullmatch(r"[a-f0-9]{32}", value["run_id"]) is None
        or not isinstance(value["tools"], dict)
        or len(value["tools"]) > 128
    ):
        return False
    total = 0
    for alias, entry in value["tools"].items():
        if (
            not isinstance(alias, str)
            or not NAME.fullmatch(alias)
            or not isinstance(entry, dict)
            or set(entry) != {"server", "assurance", *COUNTERS}
            or not isinstance(entry["server"], str)
            or not NAME.fullmatch(entry["server"])
            or "__" in entry["server"]
            or not alias.startswith(entry["server"] + "__")
            or not isinstance(entry["assurance"], str)
            or entry["assurance"] not in {"advisory", "review_read"}
            or any(type(entry[k]) is not int or not 0 <= entry[k] <= 64 for k in COUNTERS)
        ):
            return False
        if (
            sum(entry[k] for k in TERMINAL) != entry["attempted"]
            or sum(entry[k] for k in DENIAL_DIAGNOSTICS) > entry["denied"]
            or entry["cache_hits"] + entry["single_flight"] > entry["attempted"]
        ):
            return False
        total += entry["attempted"]
    return total <= 64


def reconcile(receipt: Any, attempts: Any, expected: set[str]) -> dict[str, Any]:
    if (
        not valid_receipt(receipt)
        or set(receipt["tools"]) != expected
        or not isinstance(attempts, dict)
    ):
        raise ValueError("federation receipt is unavailable or invalid")
    counts = {alias: attempts.get(alias, 0) for alias in sorted(expected)}
    if any(type(n) is not int or not 0 <= n <= 1_000_000 for n in counts.values()):
        raise ValueError("federation OCR accounting is invalid")
    degraded = any(
        counts[alias] != entry["attempted"]
        or entry["attempted"] != entry["completed"]
        or (counts[alias] > 0 and entry["assurance"] == "advisory")
        for alias, entry in receipt["tools"].items()
    )
    return {
        "receipt": receipt,
        "ocr_attempts": counts,
        "state": "degraded" if degraded else "complete",
    }


def valid_reconciliation(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"receipt", "ocr_attempts", "state"}:
        return False
    if not valid_receipt(value["receipt"]) or not isinstance(value["ocr_attempts"], dict):
        return False
    if set(value["ocr_attempts"]) != set(value["receipt"]["tools"]):
        return False
    try:
        return (
            reconcile(value["receipt"], value["ocr_attempts"], set(value["ocr_attempts"])) == value
        )
    except ValueError:
        return False


def format_federation(value: Any) -> str:
    if not valid_reconciliation(value):
        return ""
    used = []
    for alias, entry in sorted(value["receipt"]["tools"].items()):
        if entry["attempted"] or value["ocr_attempts"][alias]:
            counts = ",".join(f"{k}={entry[k]}" for k in sorted(COUNTERS))
            used.append(
                f"{alias}[{entry['assurance']};ocr_attempts={value['ocr_attempts'][alias]};{counts}]"
            )
    return "- Federation v1: " + value["state"] + "; " + ("; ".join(used) or "unused")
