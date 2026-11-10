"""Closed, immutable diagram grammar without Git, environment or transport I/O."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from ocr_toolkit.diagrams.diagnostics import DiagramError as DiagramError
from ocr_toolkit.diagrams.diagnostics import at_pointer
from ocr_toolkit.result_contract import OcrResultContractError
from ocr_toolkit.review_range import ReviewRange

MAX_DIAGRAM_BYTES = 16 * 1024
DIAGRAM_TOOL_NAME = "ocr_toolkit_review_diagram"
MAX_SUBMISSIONS = 8
MAX_SUBMISSION_BYTES = 128 * 1024
MAX_LABEL_CHARS = 80
MAX_LABEL_BYTES = 320
DiagramMode = Literal["on", "off", "spoiler", "local"]
DiagramState = Literal[
    "disabled", "not-applicable", "unsupported", "generated", "not-generated", "omitted-invalid"
]
DiagramReason = Literal[
    "none", "invalid", "conflict", "budget", "unavailable", "range", "reference", "dlp"
]


def parse_diagram_mode(raw: str | None, *, local: bool) -> DiagramMode:
    """Resolve unset/default separately from explicit blank or unsupported values."""

    value = "on" if raw is None else raw
    if value not in {"on", "off", "spoiler", "local"}:
        raise DiagramError("OCR_REVIEW_DIAGRAM_MODE must be on, off, spoiler, or local")
    if value == "local" and not local:
        raise DiagramError("OCR_REVIEW_DIAGRAM_MODE=local requires standalone --local review")
    return cast(DiagramMode, value)


def diagram_requested(mode: DiagramMode, *, local: bool) -> bool:
    """Use the same admitted mode for generation and private/provider delivery."""

    return mode == "local" if local else mode in {"on", "spoiler"}


@dataclass(frozen=True, slots=True, order=True)
class SourceReference:
    """A bounded source span at the submission's immutable reviewed head."""

    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class ReferenceSourceInfo:
    """Mechanical source facts supplied by a caller-bound acquisition adapter."""

    line_count: int = 0
    reason: Literal["none", "budget", "unavailable", "reference"] = "none"


@dataclass(frozen=True, slots=True)
class FlowNode:
    identifier: str
    kind: Literal["step", "decision"]
    label: str
    references: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class FlowEdge:
    source: str
    target: str
    condition: str
    references: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class Flowchart:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]


@dataclass(frozen=True, slots=True)
class Participant:
    identifier: str
    label: str
    references: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class SequenceMessage:
    source: str
    target: str
    message_type: Literal["call", "return"]
    label: str
    references: tuple[SourceReference, ...]


@dataclass(frozen=True, slots=True)
class SequenceBranch:
    condition: str
    references: tuple[SourceReference, ...]
    steps: tuple[SequenceMessage | SequenceAlt, ...]


@dataclass(frozen=True, slots=True)
class SequenceAlt:
    branches: tuple[SequenceBranch, ...]


SequenceStep = SequenceMessage | SequenceAlt


@dataclass(frozen=True, slots=True)
class SequenceDiagram:
    participants: tuple[Participant, ...]
    steps: tuple[SequenceStep, ...]


Diagram = Flowchart | SequenceDiagram


@dataclass(frozen=True, slots=True)
class DiagramSubmission:
    review_range: ReviewRange
    diagram: Diagram | None


@dataclass(frozen=True, slots=True)
class DiagramResult:
    """Admission facts; a diagram never grants findings or approval authority."""

    mode: DiagramMode
    state: DiagramState
    reason: DiagramReason = "none"
    submission: DiagramSubmission | None = None
    calls: int = 0
    failed_calls: int = 0


def _object(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DiagramError(
            "diagram object has an invalid closed shape", allowed=tuple(sorted(keys))
        )
    return value


def _field[T](raw: dict[str, object], key: str, reader: Callable[[object], T]) -> T:
    """Locate a value failure under a known canonical property."""

    with at_pointer("/" + key):
        return reader(raw[key])


def _array(value: object, minimum: int, maximum: int) -> list[object]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise DiagramError("diagram array exceeds its item budget")
    return value


def _text(value: object, *, empty: bool = False, path: bool = False) -> str:
    max_chars, max_bytes = (512, 2048) if path else (MAX_LABEL_CHARS, MAX_LABEL_BYTES)
    if (
        not isinstance(value, str)
        or len(value) > max_chars
        or any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in value)
    ):
        raise DiagramError("diagram text is not bounded single-line text")
    if len(value.encode("utf-8")) > max_bytes:
        raise DiagramError("diagram text exceeds its UTF-8 byte budget")
    normalized = unicodedata.normalize("NFC", value).strip()
    if (not normalized and not empty) or (path and normalized != value):
        raise DiagramError("diagram text is empty or noncanonical")
    return normalized


def _identifier(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", value) is None:
        raise DiagramError("diagram identifier is invalid")
    return value


def _references(value: object, *, required: bool = True) -> tuple[SourceReference, ...]:
    references = []
    for item_index, item in enumerate(_array(value, 1 if required else 0, 2)):
        with at_pointer(f"/{item_index}"):
            raw = _object(item, {"path", "start_line", "end_line"})
            path = _field(raw, "path", lambda v: _text(v, path=True))
            if (
                path.startswith(("/", "-"))
                or "\\" in path
                or any(part in {"", ".", ".."} for part in path.split("/"))
            ):
                raise DiagramError("diagram source path is not normalized and relative")
            start, end = raw["start_line"], raw["end_line"]
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 1_000_000:
                raise DiagramError("diagram source span is invalid")
            references.append(SourceReference(path, start, end))
    if len(set(references)) != len(references):
        raise DiagramError("diagram source references are duplicated")
    return tuple(sorted(references))


def _unique_ids(values: tuple[FlowNode, ...] | tuple[Participant, ...]) -> set[str]:
    identifiers = {item.identifier for item in values}
    if len(identifiers) != len(values):
        raise DiagramError("diagram identifiers are duplicated")
    return identifiers


def _flowchart(value: dict[str, object]) -> Flowchart:
    raw = _object(value, {"kind", "nodes", "edges"})
    nodes = []
    for item_index, item in enumerate(_array(raw["nodes"], 1, 12)):
        with at_pointer(f"/nodes/{item_index}"):
            node = _object(item, {"id", "kind", "label", "references"})
            kind = node["kind"]
            if kind not in ("step", "decision"):
                raise DiagramError("diagram node kind is invalid", path="/kind")
            nodes.append(
                FlowNode(
                    _field(node, "id", _identifier),
                    kind,
                    _field(node, "label", _text),
                    _field(node, "references", _references),
                )
            )
    normalized_nodes = tuple(sorted(nodes, key=lambda node: node.identifier))
    identifiers = _unique_ids(normalized_nodes)
    edges = []
    for item_index, item in enumerate(_array(raw["edges"], 0, 16)):
        with at_pointer(f"/edges/{item_index}"):
            edge = _object(item, {"source", "target", "condition", "references"})
            source, target = (
                _field(edge, "source", _identifier),
                _field(edge, "target", _identifier),
            )
            if source not in identifiers or target not in identifiers:
                raise DiagramError("diagram edge has an unknown endpoint")
            condition = _field(edge, "condition", lambda v: _text(v, empty=True))
            edges.append(
                FlowEdge(
                    source,
                    target,
                    condition,
                    _field(edge, "references", lambda v: _references(v, required=bool(condition))),
                )
            )
    if len(set(edges)) != len(edges):
        raise DiagramError("diagram edges are duplicated")
    return Flowchart(
        normalized_nodes,
        tuple(
            sorted(
                edges, key=lambda edge: (edge.source, edge.target, edge.condition, edge.references)
            )
        ),
    )


def _sequence(value: dict[str, object]) -> SequenceDiagram:
    raw = _object(value, {"kind", "participants", "steps"})
    participants = []
    for item_index, item in enumerate(_array(raw["participants"], 1, 8)):
        with at_pointer(f"/participants/{item_index}"):
            participant = _object(item, {"id", "label", "references"})
            participants.append(
                Participant(
                    _field(participant, "id", _identifier),
                    _field(participant, "label", _text),
                    _field(participant, "references", _references),
                )
            )
    normalized_participants = tuple(
        sorted(participants, key=lambda participant: participant.identifier)
    )
    identifiers = _unique_ids(normalized_participants)
    messages, alternatives = 0, 0

    def parse_steps(value: object, depth: int) -> tuple[SequenceStep, ...]:
        nonlocal messages, alternatives
        steps: list[SequenceStep] = []
        for item_index, item in enumerate(_array(value, 0, 20)):
            with at_pointer(f"/{item_index}"):
                if not isinstance(item, dict):
                    raise DiagramError("diagram sequence step must be an object")
                if item.get("kind") == "message":
                    message = _object(
                        item, {"kind", "source", "target", "message_type", "label", "references"}
                    )
                    source, target = (
                        _field(message, "source", _identifier),
                        _field(message, "target", _identifier),
                    )
                    message_type = message["message_type"]
                    if source not in identifiers or target not in identifiers:
                        raise DiagramError("diagram message has an unknown endpoint")
                    if message_type not in ("call", "return"):
                        raise DiagramError("diagram message type is invalid", path="/message_type")
                    messages += 1
                    if messages > 16:
                        raise DiagramError("diagram exceeds its total message budget")
                    steps.append(
                        SequenceMessage(
                            source,
                            target,
                            message_type,
                            _field(message, "label", _text),
                            _field(message, "references", _references),
                        )
                    )
                elif item.get("kind") == "alt":
                    alternative = _object(item, {"kind", "branches"})
                    alternatives += 1
                    if alternatives > 4 or depth >= 2:
                        raise DiagramError(
                            "diagram exceeds its total alternative or nesting budget"
                        )
                    branches = []
                    for item_index, branch_item in enumerate(_array(alternative["branches"], 2, 2)):
                        with at_pointer(f"/branches/{item_index}"):
                            branch = _object(branch_item, {"condition", "references", "steps"})
                            branches.append(
                                SequenceBranch(
                                    _field(branch, "condition", _text),
                                    _field(branch, "references", _references),
                                    _field(branch, "steps", lambda v: parse_steps(v, depth + 1)),
                                )
                            )
                    steps.append(SequenceAlt(tuple(branches)))
                else:
                    raise DiagramError("diagram sequence step kind is invalid", path="/kind")
        return tuple(steps)

    steps = _field(raw, "steps", lambda v: parse_steps(v, 0))
    if not messages:
        raise DiagramError("diagram sequence has no messages")
    return SequenceDiagram(normalized_participants, steps)


def bounded_json(value: object, *, limit: int = MAX_DIAGRAM_BYTES) -> bytes:
    """Bound in-memory protocol/persistence values before recursive parsing."""

    try:
        encoded = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise DiagramError("diagram is not bounded UTF-8 JSON") from exc
    if len(encoded) > limit:
        raise DiagramError("diagram exceeds its byte budget")
    return encoded


def parse_submission(value: object, *, expected_range: ReviewRange) -> DiagramSubmission:
    """Validate one exact wire candidate before any source or DLP admission."""

    bounded_json(value)
    if not isinstance(value, dict) or value.get("state") not in ("generated", "not-applicable"):
        raise DiagramError("diagram submission state is invalid", path="/state")
    generated = value["state"] == "generated"
    raw = _object(
        value,
        {"state", "base_sha", "head_sha", "diagram"}
        if generated
        else {"state", "base_sha", "head_sha"},
    )
    try:
        review_range = ReviewRange(raw["base_sha"], raw["head_sha"])  # type: ignore[arg-type]
    except OcrResultContractError as exc:
        raise DiagramError("diagram immutable range is invalid") from exc
    if review_range != expected_range:
        raise DiagramError(
            "diagram refers to a different immutable range",
            path="/base_sha" if review_range.base != expected_range.base else "/head_sha",
        )
    if not generated:
        return DiagramSubmission(review_range, None)
    diagram = raw["diagram"]
    if not isinstance(diagram, dict):
        raise DiagramError("diagram variant must be an object")
    with at_pointer("/diagram"):
        if diagram.get("kind") == "flowchart":
            parsed: Diagram = _flowchart(diagram)
        elif diagram.get("kind") == "sequence":
            parsed = _sequence(diagram)
        else:
            raise DiagramError("diagram variant is unsupported", path="/kind")
    return DiagramSubmission(review_range, parsed)


def submission_payload(submission: DiagramSubmission) -> dict[str, object]:
    """Serialize the normalized grammar with no free-form transport metadata."""

    def refs(items: tuple[SourceReference, ...]) -> list[dict[str, object]]:
        return [
            {"path": item.path, "start_line": item.start_line, "end_line": item.end_line}
            for item in items
        ]

    def sequence_steps(items: tuple[SequenceStep, ...]) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for item in items:
            if isinstance(item, SequenceMessage):
                result.append(
                    {
                        "kind": "message",
                        "source": item.source,
                        "target": item.target,
                        "message_type": item.message_type,
                        "label": item.label,
                        "references": refs(item.references),
                    }
                )
            else:
                result.append(
                    {
                        "kind": "alt",
                        "branches": [
                            {
                                "condition": branch.condition,
                                "references": refs(branch.references),
                                "steps": sequence_steps(branch.steps),
                            }
                            for branch in item.branches
                        ],
                    }
                )
        return result

    payload: dict[str, object] = {
        "state": "generated" if submission.diagram is not None else "not-applicable",
        "base_sha": submission.review_range.base,
        "head_sha": submission.review_range.head,
    }
    if isinstance(submission.diagram, Flowchart):
        payload["diagram"] = {
            "kind": "flowchart",
            "nodes": [
                {
                    "id": item.identifier,
                    "kind": item.kind,
                    "label": item.label,
                    "references": refs(item.references),
                }
                for item in submission.diagram.nodes
            ],
            "edges": [
                {
                    "source": item.source,
                    "target": item.target,
                    "condition": item.condition,
                    "references": refs(item.references),
                }
                for item in submission.diagram.edges
            ],
        }
    elif isinstance(submission.diagram, SequenceDiagram):
        payload["diagram"] = {
            "kind": "sequence",
            "participants": [
                {"id": item.identifier, "label": item.label, "references": refs(item.references)}
                for item in submission.diagram.participants
            ],
            "steps": sequence_steps(submission.diagram.steps),
        }
    return payload


def diagram_text_units(diagram: Diagram) -> tuple[tuple[str, tuple[SourceReference, ...]], ...]:
    """Enumerate complete labels/conditions with their proof spans for admission."""

    units: list[tuple[str, tuple[SourceReference, ...]]] = []
    if isinstance(diagram, Flowchart):
        units.extend((node.label, node.references) for node in diagram.nodes)
        units.extend((edge.condition, edge.references) for edge in diagram.edges)
    else:
        units.extend(
            (participant.label, participant.references) for participant in diagram.participants
        )

        def visit(steps: tuple[SequenceStep, ...]) -> None:
            for step in steps:
                if isinstance(step, SequenceMessage):
                    units.append((step.label, step.references))
                else:
                    for branch in step.branches:
                        units.append((branch.condition, branch.references))
                        visit(branch.steps)

        visit(diagram.steps)
    return tuple(units)
