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
DLP_CALL_GATES = frozenset({"arguments", "result"})
DLP_GATE_REASONS = frozenset({"forbidden", "invalid_text", "limit", "pii", "secret"})
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def valid_receipt(value: Any) -> bool:
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "run_id", "state", "cleanup", "tools"}
        or value["schema"] not in {"ocr.federation/v1", "ocr.federation/v2"}
        or value["state"] != "finalized"
        or value["cleanup"] != "clean"
        or not isinstance(value["run_id"], str)
        or re.fullmatch(r"[a-f0-9]{32}", value["run_id"]) is None
        or not isinstance(value["tools"], dict)
        or len(value["tools"]) > 128
    ):
        return False
    total = 0
    version = value["schema"]
    for alias, entry in value["tools"].items():
        if (
            not isinstance(alias, str)
            or not NAME.fullmatch(alias)
            or not isinstance(entry, dict)
            or set(entry)
            != {
                "server",
                "assurance",
                *COUNTERS,
                *({"dlp_gates"} if version.endswith("v2") else set()),
            }
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
        if version.endswith("v2"):
            gates = entry["dlp_gates"]
            if (
                not isinstance(gates, dict)
                or set(gates) != DLP_CALL_GATES
                or any(
                    not isinstance(counts, dict)
                    or set(counts) != DLP_GATE_REASONS
                    or any(
                        type(count) is not int or not 0 <= count <= 64 for count in counts.values()
                    )
                    for counts in gates.values()
                )
            ):
                return False
            if (
                sum(
                    count
                    for gate in gates.values()
                    for reason, count in gate.items()
                    if reason != "limit"
                )
                != entry["dlp_rejected"]
                or sum(gate["limit"] for gate in gates.values()) > entry["oversized"]
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
    version = value["receipt"]["schema"].rsplit("/", 1)[-1]
    for alias, entry in sorted(value["receipt"]["tools"].items()):
        if entry["attempted"] or value["ocr_attempts"][alias]:
            counts = ",".join(f"{k}={entry[k]}" for k in sorted(COUNTERS))
            gates = ""
            if version == "v2":
                decisions = (
                    f"{gate}.{reason}={count}"
                    for gate in sorted(DLP_CALL_GATES)
                    for reason, count in sorted(entry["dlp_gates"][gate].items())
                    if count
                )
                gate_counts = ",".join(decisions)
                gates = f";dlp_gates={gate_counts}" if gate_counts else ""
            used.append(
                f"{alias}[{entry['assurance']};ocr_attempts={value['ocr_attempts'][alias]};"
                f"{counts}{gates}]"
            )
    line = "- Federation " + version + ": " + value["state"] + "; " + ("; ".join(used) or "unused")
    if version == "v1" and any(
        entry["dlp_rejected"] for entry in value["receipt"]["tools"].values()
    ):
        line += "; External MCP DLP rejection; exact boundary/reason unavailable"
    elif version == "v2":
        result_denials = sum(
            sum(entry["dlp_gates"]["result"].values())
            for entry in value["receipt"]["tools"].values()
        )
        if result_denials:
            line += (
                f"; External context: {result_denials} call attempt(s) denied at response admission "
                "by DLP; that context was unavailable to this review"
            )
    return line
