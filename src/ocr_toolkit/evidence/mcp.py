"""Serve bounded repository evidence through read-only MCP over stdio."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from ocr_toolkit import __version__
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError

TOOL_NAME = "ocr_toolkit_evidence"
SERVER_NAME = "open-code-review-toolkit-evidence"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", PROTOCOL_VERSION}
MAX_REQUEST_BYTES = 64_000
MAX_RESPONSE_BYTES = 64_000
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


class EvidenceMCPError(ValueError):
    """Describe one safe client-visible evidence MCP request error."""


@dataclass(frozen=True, slots=True)
class _Query:
    """Hold normalized list filters used to bind an opaque cursor."""

    kind: str | None
    component: str | None
    ref: str | None

    def key(self) -> str:
        """Return a stable fingerprint for cursor/query binding."""

        value = json.dumps(
            {"component": self.component, "kind": self.kind, "ref": self.ref},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _text_result(payload: object) -> dict[str, object]:
    """Return one MCP text result containing deterministic bounded JSON."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES - 1_024:
        raise EvidenceMCPError("evidence response exceeds the bounded response budget")
    return {"content": [{"type": "text", "text": text}]}


def _summary(store: EvidenceStore) -> dict[str, object]:
    """Build compact counts and immutable refs without detailed values."""

    kinds: dict[str, int] = {}
    components: dict[str, int] = {}
    changes: dict[str, int] = {}
    for record in store.records:
        kinds[record.kind] = kinds.get(record.kind, 0) + 1
        components[record.component] = components.get(record.component, 0) + 1
    for delta in store.deltas:
        changes[delta.change] = changes.get(delta.change, 0) + 1
    return {
        "schema_version": 1,
        "base": store.base.commit_sha if store.base else None,
        "head": store.head.commit_sha if store.head else None,
        "records": len(store.records),
        "kinds": dict(sorted(kinds.items())),
        "components": dict(sorted(components.items())),
        "deltas": dict(sorted(changes.items())),
        "diagnostics": sorted(store.diagnostics),
    }


def _optional_filter(arguments: dict[str, object], name: str) -> str | None:
    """Read one bounded optional exact-match filter."""

    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 256:
        raise EvidenceMCPError(f"{name} must be a non-empty string of at most 256 characters")
    return value


def _encode_cursor(offset: int, query: _Query) -> str:
    """Encode an opaque, tamper-evident pagination position."""

    state = f"{offset}:{query.key()}"
    checksum = hashlib.sha256(f"ocr-evidence-v1:{state}".encode()).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{state}:{checksum}".encode()).decode().rstrip("=")


def _decode_cursor(value: object, query: _Query) -> int:
    """Validate and decode a cursor bound to the current filters."""

    if value is None:
        return 0
    if not isinstance(value, str) or not value or len(value) > 256:
        raise EvidenceMCPError("cursor must be a bounded opaque string")
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True).decode("ascii")
        offset_raw, fingerprint, checksum = raw.split(":")
        offset = int(offset_raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise EvidenceMCPError("cursor is invalid") from exc
    state = f"{offset}:{fingerprint}"
    expected = hashlib.sha256(f"ocr-evidence-v1:{state}".encode()).hexdigest()[:16]
    if offset < 0 or fingerprint != query.key() or checksum != expected:
        raise EvidenceMCPError("cursor is invalid for this evidence query")
    return offset


def _list_records(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
    """Return one bounded deterministic page of filtered records."""

    query = _Query(
        kind=_optional_filter(arguments, "kind"),
        component=_optional_filter(arguments, "component"),
        ref=_optional_filter(arguments, "ref"),
    )
    if query.ref not in {None, "base", "head", "shared"}:
        raise EvidenceMCPError("ref must be base, head, or shared")
    page_size = arguments.get("page_size", DEFAULT_PAGE_SIZE)
    if isinstance(page_size, bool) or not isinstance(page_size, int):
        raise EvidenceMCPError("page_size must be an integer")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise EvidenceMCPError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    offset = _decode_cursor(arguments.get("cursor"), query)
    records = [
        record
        for record in store.records
        if (query.kind is None or record.kind == query.kind)
        and (query.component is None or record.component == query.component)
        and (query.ref is None or record.ref.value == query.ref)
    ]
    if offset > len(records):
        raise EvidenceMCPError("cursor points beyond the available evidence")
    page = records[offset : offset + page_size]
    next_offset = offset + len(page)
    return {
        "records": [record.to_dict() for record in page],
        "next_cursor": _encode_cursor(next_offset, query) if next_offset < len(records) else None,
        "returned": len(page),
    }


def _get_record(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
    """Return one record selected by its stable content-addressed ID."""

    record_id = arguments.get("id")
    if not isinstance(record_id, str) or len(record_id) != 68 or not record_id.startswith("ev1_"):
        raise EvidenceMCPError("id must be a stable ev1 evidence identifier")
    record = next((item for item in store.records if item.id == record_id), None)
    if record is None:
        raise EvidenceMCPError("evidence record was not found")
    return {"record": record.to_dict()}


def call_tool(store: EvidenceStore, arguments: object) -> dict[str, object]:
    """Execute one closed, read-only evidence action."""

    if not isinstance(arguments, dict):
        raise EvidenceMCPError("tool arguments must be an object")
    typed = cast(dict[str, object], arguments)
    action = typed.get("action")
    if action == "summary":
        allowed = {"action"}
        payload = _summary(store)
    elif action == "list":
        allowed = {"action", "kind", "component", "ref", "page_size", "cursor"}
        payload = _list_records(store, typed)
    elif action == "get":
        allowed = {"action", "id"}
        payload = _get_record(store, typed)
    else:
        raise EvidenceMCPError("action must be summary, list, or get")
    unknown = set(typed) - allowed
    if unknown:
        raise EvidenceMCPError(f"unsupported tool argument: {sorted(unknown)[0]}")
    return _text_result(payload)


def _tool_definition() -> dict[str, object]:
    """Return the versioned public MCP tool declaration."""

    return {
        "name": TOOL_NAME,
        "description": (
            "Read bounded, redacted repository evidence for immutable base/head refs. "
            "Use summary first, list to narrow, and get for one stable record."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["summary", "list", "get"]},
                "kind": {"type": "string", "maxLength": 256},
                "component": {"type": "string", "maxLength": 256},
                "ref": {"type": "string", "enum": ["base", "head", "shared"]},
                "page_size": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
                "cursor": {"type": "string", "maxLength": 256},
                "id": {"type": "string", "pattern": "^ev1_[0-9a-f]{64}$"},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    }


def _success(request_id: object, result: object) -> dict[str, object]:
    """Create a JSON-RPC success response."""

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict[str, object]:
    """Create a JSON-RPC error response without repository-derived details."""

    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(store: EvidenceStore, raw: object) -> dict[str, object] | None:
    """Handle one validated JSON-RPC request or notification."""

    if not isinstance(raw, dict) or raw.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid Request")
    request_id = raw.get("id")
    method = raw.get("method")
    params = raw.get("params", {})
    if method == "notifications/initialized" and "id" not in raw:
        return None
    if method == "initialize":
        if not isinstance(params, dict):
            return _error(request_id, -32602, "Invalid params")
        version = params.get("protocolVersion")
        if version not in SUPPORTED_PROTOCOL_VERSIONS:
            return _error(request_id, -32602, "Unsupported protocol version")
        return _success(
            request_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": __version__},
            },
        )
    if method == "ping":
        return _success(request_id, {})
    if method == "tools/list":
        return _success(request_id, {"tools": [_tool_definition()]})
    if method == "tools/call":
        if not isinstance(params, dict) or params.get("name") != TOOL_NAME:
            return _error(request_id, -32602, "Invalid tool call")
        try:
            result = call_tool(store, params.get("arguments", {}))
        except EvidenceMCPError as exc:
            return _success(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
        return _success(request_id, result)
    return _error(request_id, -32601, "Method not found")


def serve(store_path: Path, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Serve newline-delimited MCP JSON-RPC until the client closes stdin."""

    try:
        store = EvidenceStore.read(store_path)
    except (OSError, EvidenceStoreError) as exc:
        print(f"Cannot load evidence store: {exc}", file=sys.stderr)
        return 2
    for line in stdin:
        if len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
            response = _error(None, -32700, "Request exceeds the byte limit")
        else:
            try:
                request = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                response = _error(None, -32700, "Parse error")
            else:
                response = handle_request(store, request)
        if response is None:
            continue
        serialized = json.dumps(response, separators=(",", ":"), ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_RESPONSE_BYTES:
            serialized = json.dumps(_error(response.get("id"), -32603, "Response exceeds the byte limit"))
        stdout.write(serialized + "\n")
        stdout.flush()
    return 0
