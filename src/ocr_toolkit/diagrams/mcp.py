"""Fixed private output capability; evidence actions retain read-only behavior."""

from __future__ import annotations

import json
from typing import Any

from ocr_toolkit.diagrams.collector import DiagramCollector
from ocr_toolkit.diagrams.contracts import DIAGRAM_TOOL_NAME as DIAGRAM_TOOL_NAME
from ocr_toolkit.diagrams.contracts import bounded_json
from ocr_toolkit.diagrams.lifecycle import diagram_warning


def diagram_tool_definition() -> dict[str, object]:
    """Describe the closed tagged union without granting paths or provider writes."""

    def obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False,
        }

    label = {"type": "string", "minLength": 1, "maxLength": 80}
    identifier = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]{0,31}$"}
    refs = {
        "type": "array",
        "minItems": 1,
        "maxItems": 2,
        "items": obj(
            {
                "path": {"type": "string", "minLength": 1, "maxLength": 512},
                "start_line": {"type": "integer", "minimum": 1, "maximum": 1000000},
                "end_line": {"type": "integer", "minimum": 1, "maximum": 1000000},
            }
        ),
    }
    message = obj(
        {
            "kind": {"const": "message"},
            "source": identifier,
            "target": identifier,
            "message_type": {"type": "string", "enum": ["call", "return"]},
            "label": label,
            "references": refs,
        }
    )
    steps = {"type": "array", "maxItems": 20, "items": {"$ref": "#/$defs/step"}}
    alt = obj(
        {
            "kind": {"const": "alt"},
            "branches": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": obj({"condition": label, "references": refs, "steps": steps}),
            },
        }
    )
    flow = obj(
        {
            "kind": {"const": "flowchart"},
            "nodes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": obj(
                    {
                        "id": identifier,
                        "kind": {"type": "string", "enum": ["step", "decision"]},
                        "label": label,
                        "references": refs,
                    }
                ),
            },
            "edges": {
                "type": "array",
                "maxItems": 16,
                "items": obj(
                    {
                        "source": identifier,
                        "target": identifier,
                        "condition": {"type": "string", "maxLength": 80},
                        "references": {**refs, "minItems": 0},
                    }
                ),
            },
        }
    )
    sequence = obj(
        {
            "kind": {"const": "sequence"},
            "participants": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": obj({"id": identifier, "label": label, "references": refs}),
            },
            "steps": steps,
        }
    )
    schema = obj(
        {
            "state": {"type": "string", "enum": ["generated", "not-applicable"]},
            "base_sha": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
            "head_sha": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
            "diagram": {"oneOf": [flow, sequence]},
        },
        ["state", "base_sha", "head_sha"],
    )
    schema["$defs"] = {"step": {"oneOf": [message, alt]}}
    schema["oneOf"] = [
        {"properties": {"state": {"const": "generated"}}, "required": ["diagram"]},
        {"properties": {"state": {"const": "not-applicable"}}, "not": {"required": ["diagram"]}},
    ]
    return {
        "name": DIAGRAM_TOOL_NAME,
        "description": (
            "Submit one optional model-proposed summary for the exact full review range. "
            "Choose flowchart for decisions or sequence for ordered component interactions. "
            "Use not-applicable without diagram for changes with no useful behavioral summary. "
            "Do not send prose reasons, raw Mermaid, HTML, styles or output paths. "
            "Labels/conditions: one line, 80 code points/320 UTF-8 bytes. Candidate: 16 KiB. "
            "Sequence totals across ALL branches: 16 messages, four alt fragments, depth two. "
            "References point to reviewed head. Every node/participant/message/branch condition "
            "requires 1-2 references; conditional flow edges also require references. "
            "All groups share eight submissions/128 KiB; different candidates omit the diagram. "
            "A response confirms private collection only, not final admission or publication."
        ),
        "inputSchema": schema,
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    }


def call_diagram_tool(
    collector: DiagramCollector | None, arguments: object, *, request_bytes: int | None = None
) -> dict[str, object]:
    """Return a normal optional-state response even when a candidate is omitted."""

    try:
        if collector is None:
            raise ValueError("diagram output unavailable")
        snapshot = collector.submit(arguments, input_bytes=request_bytes)
        result = (
            {"state": "received"}
            if snapshot.reason == "none"
            else {"state": "omitted-invalid", "reason": snapshot.reason}
        )
        return {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}]}
    except Exception:
        # Only this optional output boundary catches unexpected implementation
        # failures. Mandatory evidence actions preserve their own error contract.
        diagram_warning()
        return {
            "content": [
                {"type": "text", "text": '{"reason":"unavailable","state":"omitted-invalid"}'}
            ]
        }


def optional_diagram_tool_definition() -> dict[str, object]:
    """Keep evidence registration usable if optional schema construction fails."""

    try:
        definition = diagram_tool_definition()
        if (
            not isinstance(definition, dict)
            or definition.get("name") != DIAGRAM_TOOL_NAME
            or not isinstance(definition.get("inputSchema"), dict)
        ):
            raise ValueError("diagram definition is invalid")
        bounded_json(definition)
        return definition
    except Exception:
        diagram_warning()
        return {
            "name": DIAGRAM_TOOL_NAME,
            "description": "Optional diagram unavailable; review may continue without it.",
            "inputSchema": {"type": "object", "properties": {}},
        }
