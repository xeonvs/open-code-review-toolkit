"""Decode only closed numeric DLP and federation signals."""

import json
import re
from collections import Counter
from typing import Any

from .grammar import (
    OCR_FEDERATION_COUNTERS,
    OCR_FEDERATION_GATES,
    OCR_FEDERATION_MAX_COUNT,
    OCR_FEDERATION_MAX_OCR_ATTEMPTS,
    OCR_FEDERATION_REASONS,
    OCR_PUBLICATION_DLP_MAX_COUNT,
    OCR_PUBLICATION_DLP_REASON_KEYS,
    OCR_PUBLICATION_DLP_SIGNAL_MARKER,
    OCR_PUBLICATION_DLP_SIGNAL_RE,
    OCR_PUBLICATION_DLP_SOURCE_KEYS,
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate publication signal field")
    return value


def parse_ocr_publication_dlp_signal(body: str) -> tuple[dict[str, Any] | None, bool]:
    """Read one exact low-cardinality publication DLP signal, preserving old shapes."""

    if OCR_PUBLICATION_DLP_SIGNAL_MARKER not in body:
        return None, False
    markers = OCR_PUBLICATION_DLP_SIGNAL_RE.findall(body)
    if len(markers) != 1 or len(body.splitlines()) != 1:
        return None, True
    try:
        signal = json.loads(markers[0], object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return None, True
    if not isinstance(signal, dict):
        return None, True

    def counts(value: Any, keys: set[str]) -> bool:
        return (
            isinstance(value, dict)
            and set(value) == keys
            and all(
                isinstance(count, int)
                and not isinstance(count, bool)
                and 0 <= count <= OCR_PUBLICATION_DLP_MAX_COUNT
                for count in value.values()
            )
        )

    schema = signal.get("schema_version")
    state = signal.get("state")
    if not isinstance(schema, str) or not isinstance(state, str):
        return None, True
    if schema == "ocr.publication-dlp-signal/v4":
        return normalize_dlp_v4(signal, counts)
    reason_counts = signal.get("reason_counts")
    if schema == "ocr.publication-dlp-signal/v3" and state == "disabled":
        return (
            ({"state": state}, False)
            if set(signal) == {"schema_version", "state"}
            else (None, True)
        )
    if not counts(reason_counts, OCR_PUBLICATION_DLP_REASON_KEYS):
        return None, True
    source_attribution = signal.get("source_attribution")
    has_source_attribution = source_attribution is not None
    if has_source_attribution and not (
        schema == "ocr.publication-dlp-signal/v3"
        and isinstance(source_attribution, dict)
        and set(source_attribution) == {"schema", "counts"}
        and source_attribution.get("schema") == "ocr.forbidden-sources/v1"
        and counts(source_attribution.get("counts"), OCR_PUBLICATION_DLP_SOURCE_KEYS)
        and all(
            value <= reason_counts["forbidden"] for value in source_attribution["counts"].values()
        )
    ):
        return None, True
    if (
        schema in {"ocr.publication-dlp-signal/v2", "ocr.publication-dlp-signal/v3"}
        and state == "private-sanitized"
    ):
        sanitized = signal.get("sanitized_fields")
        expected = {"schema_version", "state", "reason_counts", "sanitized_fields"}
        if has_source_attribution:
            expected.add("source_attribution")
        if (
            set(signal) != expected
            or not isinstance(sanitized, int)
            or isinstance(sanitized, bool)
            or not 0 <= sanitized <= OCR_PUBLICATION_DLP_MAX_COUNT
        ):
            return None, True
        normalized: dict[str, Any] = {
            "state": state,
            "private_sanitization": {"fields": sanitized, "reason_counts": reason_counts},
        }
        if has_source_attribution:
            normalized["source_attribution"] = dict(source_attribution["counts"])
        return normalized, False

    expected_schema_state = {
        ("ocr.publication-dlp-signal/v1", "filtered"),
        ("ocr.publication-dlp-signal/v2", "publication-filtered"),
        ("ocr.publication-dlp-signal/v3", "publication-filtered"),
    }
    retained = signal.get("retained")
    omitted = signal.get("omitted")
    original = signal.get("original")
    carried = signal.get("carried_forward_comments")
    if (
        (schema, state) not in expected_schema_state
        or set(signal)
        != {
            "schema_version",
            "state",
            "reason_counts",
            "retained",
            "omitted",
            "original",
            "carried_forward_comments",
            *({"source_attribution"} if has_source_attribution else set()),
        }
        or not any(reason_counts.values())
        or not counts(retained, {"comments", "warnings"})
        or not counts(omitted, {"comments", "warnings", "fields"})
        or not isinstance(original, dict)
        or set(original) != {"outcome", "selected", "completed", "reused", "failed", "waived"}
        or not isinstance(original.get("outcome"), str)
        or original["outcome"] not in {"clean", "warning", "partial", "failed", "skipped"}
        or not counts(
            {
                key: original.get(key)
                for key in ("selected", "completed", "reused", "failed", "waived")
            },
            {"selected", "completed", "reused", "failed", "waived"},
        )
        or not isinstance(carried, int)
        or isinstance(carried, bool)
        or not 0 <= carried <= OCR_PUBLICATION_DLP_MAX_COUNT
    ):
        return None, True
    normalized = {
        "state": "publication-filtered",
        "historical_reason_counts": reason_counts,
        "retained_comments": retained["comments"],
        "retained_warnings": retained["warnings"],
        "omitted_comments": omitted["comments"],
        "omitted_warnings": omitted["warnings"],
        "omitted_fields": omitted["fields"],
        "carried_forward_comments": carried,
    }
    if has_source_attribution:
        normalized["source_attribution"] = dict(source_attribution["counts"])
    return normalized, False


def normalize_dlp_v4(signal: dict[str, Any], counts: Any) -> tuple[dict[str, Any] | None, bool]:
    """Keep public omissions and private cleanup in distinct numeric domains."""

    state = signal.get("state")
    base = {"schema_version", "state"}
    if state == "disabled":
        return ({"version": "v4", "state": state}, False) if set(signal) == base else (None, True)
    private = signal.get("private_sanitization")
    if (
        not isinstance(private, dict)
        or set(private) != {"fields", "reason_counts"}
        or not counts({"fields": private.get("fields")}, {"fields"})
        or not counts(private.get("reason_counts"), OCR_PUBLICATION_DLP_REASON_KEYS)
        or (private["fields"] == 0) != (not any(private["reason_counts"].values()))
    ):
        return None, True
    expected = base | {"private_sanitization"}
    normalized = {"version": "v4", "state": state, "private_sanitization": private}
    forbidden = private["reason_counts"]["forbidden"]
    if state == "private-sanitized":
        if private["fields"] == 0:
            return None, True
    elif state == "publication-filtered":
        expected |= {"reason_counts", "retained", "omitted", "original", "carried_forward_comments"}
        original = signal.get("original")
        reasons = signal.get("reason_counts")
        coverage_keys = {"selected", "completed", "reused", "failed", "waived"}
        if (
            not counts(reasons, OCR_PUBLICATION_DLP_REASON_KEYS)
            or not any(reasons.values())
            or not counts(signal.get("retained"), {"comments", "warnings"})
            or not counts(signal.get("omitted"), {"comments", "warnings", "fields"})
            or not counts({"count": signal.get("carried_forward_comments")}, {"count"})
            or not isinstance(original, dict)
            or set(original) - {"operational_partial"} != coverage_keys | {"outcome"}
            or not isinstance(original["outcome"], str)
            or not counts({key: original[key] for key in coverage_keys}, coverage_keys)
        ):
            return None, True
        selected, failed = original["selected"], original["failed"]
        allowed = {"failed"} | (
            {"skipped"}
            if selected == 0
            else {"clean", "warning"}
            if failed == 0
            else {"failed"}
            if failed == selected
            else {"partial"}
        )
        if (
            selected != sum(original[key] for key in ("completed", "reused", "failed", "waived"))
            or original["outcome"] not in allowed
        ):
            return None, True
        # Older producers could expose this private handoff flag in a v4 note.
        if "operational_partial" in original and not (
            original["operational_partial"] is True
            and original["outcome"] == "partial"
            and failed > 0
        ):
            return None, True
        forbidden += reasons["forbidden"]
        normalized.update(
            {
                "public_output": {**signal["omitted"], "reason_counts": reasons},
                **{f"retained_{key}": value for key, value in signal["retained"].items()},
                **{f"omitted_{key}": signal["omitted"][key] for key in ("comments", "warnings")},
                "carried_forward_comments": signal["carried_forward_comments"],
            }
        )
    else:
        return None, True
    if "source_attribution" in signal:
        expected.add("source_attribution")
        sources = signal["source_attribution"]
        if (
            not isinstance(sources, dict)
            or set(sources) != {"schema", "counts"}
            or sources["schema"] != "ocr.forbidden-sources/v1"
            or not counts(sources["counts"], OCR_PUBLICATION_DLP_SOURCE_KEYS)
            or any(value > forbidden for value in sources["counts"].values())
        ):
            return None, True
        normalized["source_attribution"] = sources["counts"]
    return (normalized, False) if set(signal) == expected else (None, True)


def parse_ocr_federation(body: str) -> tuple[dict[str, Any] | None, bool]:
    """Read bounded public federation v1/v2 accounting; discard tool aliases."""

    prefixes = re.findall(r"(?m)^- Federation v[^\r\n]*$", body)
    if not prefixes:
        return None, False
    if len(prefixes) != 1:
        return None, True
    match = re.fullmatch(r"- Federation (v1|v2): (complete|degraded); (.+)", prefixes[0])
    if not match:
        return None, True
    version, state, details = match.groups()
    legacy_suffix = "; External MCP DLP rejection; exact boundary/reason unavailable"
    has_legacy_suffix = details.endswith(legacy_suffix)
    if has_legacy_suffix:
        details = details[: -len(legacy_suffix)]
    result_suffix = re.search(
        r"; External context: ([1-9]\d?) call attempt\(s\) denied at response admission "
        r"by DLP; that context was unavailable to this review$",
        details,
    )
    result_denials = int(result_suffix.group(1)) if result_suffix else None
    if result_suffix:
        details = details[: result_suffix.start()]
    if (has_legacy_suffix and version != "v1") or (result_suffix and version != "v2"):
        return None, True
    gates = {gate: Counter() for gate in OCR_FEDERATION_GATES}
    if details == "unused":
        if state != "complete" or has_legacy_suffix or result_suffix:
            return None, True
        return {
            "state": state,
            "used": False,
            "tools": 0,
            "ocr_attempts": 0,
            **{key: 0 for key in OCR_FEDERATION_COUNTERS},
            **(
                {
                    "version": version,
                    "dlp_gates": {gate: dict(value) for gate, value in gates.items()},
                }
                if version == "v2"
                else {}
            ),
        }, False
    tools = []
    rendered_tools = details.split("; ")
    if len(rendered_tools) > 128:
        return None, True
    for rendered in rendered_tools:
        item = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_-]{0,63}__[A-Za-z][A-Za-z0-9_-]{0,63})"
            r"\[(advisory|review_read);ocr_attempts=(0|[1-9]\d{0,6});([^\]]+)\]",
            rendered,
        )
        if not item:
            return None, True
        alias, assurance, ocr_attempts, counters_text = item.groups()
        counters_text, separator, gate_text = counters_text.partition(";dlp_gates=")
        if separator and version != "v2":
            return None, True
        pairs = re.findall(r"([a-z_]+)=(0|[1-9]\d?)", counters_text)
        if ",".join(f"{key}={value}" for key, value in pairs) != counters_text:
            return None, True
        if [key for key, _value in pairs] != sorted(OCR_FEDERATION_COUNTERS) or len(alias) > 64:
            return None, True
        counters = {key: int(value) for key, value in pairs}
        if (
            int(ocr_attempts) > OCR_FEDERATION_MAX_OCR_ATTEMPTS
            or tuple(counters) != tuple(sorted(OCR_FEDERATION_COUNTERS))
            or any(value > OCR_FEDERATION_MAX_COUNT for value in counters.values())
        ):
            return None, True
        attempts = counters["attempted"]
        if (
            sum(counters[key] for key in ("completed", "denied", "failed", "timed_out")) != attempts
            or counters["dlp_rejected"] + counters["oversized"] > counters["denied"]
            or counters["cache_hits"] + counters["single_flight"] > attempts
        ):
            return None, True
        tool_gates = {}
        if separator:
            gate_pairs = re.findall(r"(arguments|result)\.([a-z_]+)=([1-9]\d?)", gate_text)
            if (
                ",".join(f"{gate}.{reason}={value}" for gate, reason, value in gate_pairs)
                != gate_text
                or not gate_pairs
            ):
                return None, True
            keys = [f"{gate}.{reason}" for gate, reason, _value in gate_pairs]
            if keys != sorted(set(keys)):
                return None, True
            for gate, reason, value in gate_pairs:
                if (
                    reason not in OCR_FEDERATION_REASONS
                    or not 0 < int(value) <= OCR_FEDERATION_MAX_COUNT
                ):
                    return None, True
                tool_gates[(gate, reason)] = int(value)
        if version == "v2" and (
            sum(value for (_gate, reason), value in tool_gates.items() if reason != "limit")
            != counters["dlp_rejected"]
            or sum(value for (_gate, reason), value in tool_gates.items() if reason == "limit")
            > counters["oversized"]
        ):
            return None, True
        for (gate, reason), value in tool_gates.items():
            gates[gate][reason] += value
        tools.append((alias, assurance, int(ocr_attempts), counters))
    aliases = [alias for alias, *_rest in tools]
    if aliases != sorted(set(aliases)):
        return None, True
    aggregate = Counter()
    assurances = Counter()
    ocr_total = 0
    for _alias, assurance, ocr_attempts, counters in tools:
        assurances[assurance] += 1
        ocr_total += ocr_attempts
        aggregate.update(counters)
    if aggregate["attempted"] > OCR_FEDERATION_MAX_COUNT:
        return None, True
    if has_legacy_suffix and aggregate["dlp_rejected"] == 0:
        return None, True
    response_total = sum(gates["result"].values())
    if version == "v2" and (
        (result_denials != response_total or result_denials == 0)
        if result_suffix
        else bool(response_total)
    ):
        return None, True
    derived_degraded = any(
        ocr_attempts != counters["attempted"]
        or counters["attempted"] != counters["completed"]
        or (ocr_attempts > 0 and assurance == "advisory")
        for _alias, assurance, ocr_attempts, counters in tools
    )
    if (state == "degraded") != derived_degraded:
        return None, True
    return {
        "state": state,
        "used": True,
        "tools": len(tools),
        "assurance": dict(assurances),
        "ocr_attempts": ocr_total,
        **{key: aggregate[key] for key in OCR_FEDERATION_COUNTERS},
        **(
            {"version": version, "dlp_gates": {gate: dict(value) for gate, value in gates.items()}}
            if version == "v2"
            else {}
        ),
    }, False
