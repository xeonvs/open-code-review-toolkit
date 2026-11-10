"""Closed validation feedback: structural locations, never rejected material."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager

MAX_DIAGNOSTIC_BYTES = 1024
MESSAGES = {
    "invalid": "diagram validation failed",
    "state": "diagram submission state is invalid",
    "shape": "diagram object has an invalid closed shape",
    "array": "diagram array exceeds its item budget",
    "text": "diagram text is not bounded single-line text",
    "text_bytes": "diagram text exceeds its UTF-8 byte budget",
    "text_form": "diagram text is empty or noncanonical",
    "identifier": "diagram identifier is invalid",
    "reference_path": "diagram source path is not normalized and relative",
    "reference_span": "diagram source span is invalid",
    "duplicate_reference": "diagram source references are duplicated",
    "duplicate_identifier": "diagram identifiers are duplicated",
    "node_kind": "diagram node kind is invalid",
    "edge_endpoint": "diagram edge has an unknown endpoint",
    "duplicate_edge": "diagram edges are duplicated",
    "sequence_object": "diagram sequence step must be an object",
    "message_endpoint": "diagram message has an unknown endpoint",
    "message_type": "diagram message type is invalid",
    "message_budget": "diagram exceeds its total message budget",
    "alternative_budget": "diagram exceeds its total alternative or nesting budget",
    "step_kind": "diagram sequence step kind is invalid",
    "empty_sequence": "diagram sequence has no messages",
    "json": "diagram is not bounded UTF-8 JSON",
    "diagram_budget": "diagram exceeds its byte budget",
    "range": "diagram immutable range is invalid",
    "range_mismatch": "diagram refers to a different immutable range",
    "variant_object": "diagram variant must be an object",
    "variant": "diagram variant is unsupported",
}
_CODES = {message: code for code, message in MESSAGES.items()}
_FIELDS = frozenset(
    [
        "state",
        "base_sha",
        "head_sha",
        "diagram",
        "kind",
        "nodes",
        "edges",
        "id",
        "label",
        "references",
        "source",
        "target",
        "condition",
        "participants",
        "steps",
        "branches",
        "message_type",
        "path",
        "start_line",
        "end_line",
    ]
)
_ENUMS = {
    "state": ("generated", "not-applicable"),
    "node_kind": ("step", "decision"),
    "message_type": ("call", "return"),
    "step_kind": ("message", "alt"),
    "variant": ("flowchart", "sequence"),
}
_POINTER = re.compile(r"(?:/(?:" + "|".join(sorted(_FIELDS)) + r"|0|[1-9][0-9]{0,5}))*\Z")


class DiagramError(ValueError):
    """Keep ordinary internal exceptions separate from closed model feedback."""

    def __init__(self, message: str, *, path: str = "", allowed: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code = _CODES.get(message, "invalid")
        self.path = path
        self.allowed = _ENUMS.get(self.code, allowed if self.code == "shape" else ())

    def diagnostic(self) -> dict[str, object]:
        """Produce an exact bounded payload; arbitrary exception text is excluded."""

        value = {
            "code": self.code,
            "path": self.path,
            "message": MESSAGES[self.code],
            "allowed": list(self.allowed),
        }
        return parse_diagnostic(value)


def parse_diagnostic(value: object) -> dict[str, object]:
    """Revalidate private diagnostic state without reflecting hostile values."""

    if not isinstance(value, dict) or set(value) != {"code", "path", "message", "allowed"}:
        raise DiagramError("diagram validation failed")
    code, path, allowed = value["code"], value["path"], value["allowed"]
    if (
        not isinstance(code, str)
        or code not in MESSAGES
        or value["message"] != MESSAGES[code]
        or not isinstance(path, str)
        or len(path) > 256
        or _POINTER.fullmatch(path) is None
        or not isinstance(allowed, list)
        or len(allowed) > len(_FIELDS)
        or any(not isinstance(item, str) for item in allowed)
        or len(set(allowed)) != len(allowed)
        or (code == "shape" and not set(allowed) <= _FIELDS)
        or (code != "shape" and allowed != list(_ENUMS.get(code, ())))
    ):
        raise DiagramError("diagram validation failed")
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_DIAGNOSTIC_BYTES:
        raise DiagramError("diagram validation failed")
    return {"code": code, "path": path, "message": MESSAGES[code], "allowed": list(allowed)}


@contextmanager
def at_pointer(pointer: str) -> Iterator[None]:
    """Add a parser-owned field/index location while retaining the closed cause."""

    try:
        yield
    except DiagramError as exc:
        raise DiagramError(str(exc), path=pointer + exc.path, allowed=exc.allowed) from None
