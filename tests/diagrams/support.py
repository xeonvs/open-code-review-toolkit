"""Synthetic diagram payloads shared by protocol and rendering regressions."""

from typing import Any

from ocr_toolkit.review_range import ReviewRange

REVIEW_RANGE = ReviewRange("a" * 40, "b" * 40)


def references(path: str = "app.py", start: int = 1, end: int = 1) -> list[dict[str, Any]]:
    return [{"path": path, "start_line": start, "end_line": end}]


def flow_submission() -> dict[str, Any]:
    return {
        "state": "generated",
        "base_sha": REVIEW_RANGE.base,
        "head_sha": REVIEW_RANGE.head,
        "diagram": {
            "kind": "flowchart",
            "nodes": [
                {
                    "id": "check",
                    "kind": "decision",
                    "label": "version >= 2026.10.19",
                    "references": references(),
                },
                {
                    "id": "handle",
                    "kind": "step",
                    "label": "Handle request",
                    "references": references(start=2, end=3),
                },
            ],
            "edges": [
                {
                    "source": "check",
                    "target": "handle",
                    "condition": "supported",
                    "references": references(),
                }
            ],
        },
    }


def message(label: str = "Call service", kind: str = "call") -> dict[str, Any]:
    return {
        "kind": "message",
        "source": "api",
        "target": "service",
        "message_type": kind,
        "label": label,
        "references": references(),
    }


def alternative(
    steps: list[dict[str, Any]], other: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "kind": "alt",
        "branches": [
            {"condition": "request accepted", "references": references(), "steps": steps},
            {"condition": "request rejected", "references": references(), "steps": other or []},
        ],
    }


def sequence_submission() -> dict[str, Any]:
    return {
        "state": "generated",
        "base_sha": REVIEW_RANGE.base,
        "head_sha": REVIEW_RANGE.head,
        "diagram": {
            "kind": "sequence",
            "participants": [
                {"id": "api", "label": "API", "references": references()},
                {"id": "service", "label": "Service", "references": references()},
            ],
            "steps": [
                message(),
                alternative(
                    [message("Read cache"), alternative([message("Cache result", "return")])],
                    [message("Reject request", "return")],
                ),
            ],
        },
    }
