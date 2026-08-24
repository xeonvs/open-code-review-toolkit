"""Expose only committed opaque context handles through fixed read-only tools."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import time
from collections.abc import Mapping

from ocr_toolkit.context.contracts import STORE_RESOURCE_CLASSES
from ocr_toolkit.context.store import HANDLE_RE, ContextStore

LIST_TOOL = "context_list"
GET_TOOL = "context_get"
MAX_PAGE_SIZE = 20


class ContextMCPError(ValueError):
    """One closed context tool request was invalid."""


def _text(value: object) -> dict[str, object]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(value, sort_keys=True, separators=(",", ":")),
            }
        ]
    }


def _query_key(resource_class: str | None, source: str | None) -> str:
    value = json.dumps([resource_class, source], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"ocr-context-query-v1:{value}".encode()).hexdigest()[:16]


def _records_key(handles: list[str]) -> str:
    value = json.dumps(handles, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"ocr-context-page-v1:{value}".encode()).hexdigest()[:16]


def _cursor(offset: int, query_key: str, records_key: str) -> str:
    state = json.dumps([offset, query_key, records_key], separators=(",", ":"))
    digest = hashlib.sha256(f"ocr-context-list-v1:{state}".encode()).hexdigest()[:16]
    envelope = json.dumps([state, digest], separators=(",", ":"), ensure_ascii=True)
    return base64.urlsafe_b64encode(envelope.encode()).decode().rstrip("=")


def _offset(value: object, query_key: str, records_key: str) -> int:
    if value is None or value == "":
        return 0
    if not isinstance(value, str) or len(value) > 256:
        raise ContextMCPError("cursor is invalid")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        envelope = json.loads(raw.decode("ascii"))
        if not isinstance(envelope, list) or len(envelope) != 2:
            raise ValueError
        state, digest = envelope
        selected_state = json.loads(state) if isinstance(state, str) else None
        if not isinstance(selected_state, list) or len(selected_state) != 3:
            raise ValueError
        offset, selected_query, selected_records = selected_state
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ContextMCPError("cursor is invalid") from exc
    state = json.dumps([offset, selected_query, selected_records], separators=(",", ":"))
    expected = hashlib.sha256(f"ocr-context-list-v1:{state}".encode()).hexdigest()[:16]
    if (
        not isinstance(offset, int)
        or isinstance(offset, bool)
        or offset < 0
        or selected_query != query_key
        or selected_records != records_key
        or not isinstance(digest, str)
        or digest != expected
    ):
        raise ContextMCPError("cursor is invalid")
    return offset


def call_context_tool(
    store: ContextStore,
    name: str,
    arguments: object,
    *,
    now: int | None = None,
) -> dict[str, object]:
    """Execute one handle-only operation against an already validated local store."""

    current = int(time.time()) if now is None else now
    if (
        isinstance(current, bool)
        or not isinstance(current, int)
        or current < store.created_at
        or current >= store.expiry
    ):
        raise ContextMCPError("context store is unavailable")
    if not isinstance(arguments, Mapping) or any(not isinstance(key, str) for key in arguments):
        raise ContextMCPError("tool arguments must be an object")
    if name == LIST_TOOL:
        if set(arguments).difference({"resource_class", "source", "page_size", "cursor"}):
            raise ContextMCPError("context_list arguments are invalid")
        resource_class = arguments.get("resource_class")
        if resource_class is not None and (
            not isinstance(resource_class, str) or resource_class not in STORE_RESOURCE_CLASSES
        ):
            raise ContextMCPError("resource_class is invalid")
        source = arguments.get("source")
        if source is not None and (
            not isinstance(source, str)
            or not source
            or len(source) > 256
            or source not in store.completeness
        ):
            raise ContextMCPError("source is invalid")
        page_size = arguments.get("page_size", 10)
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 20
        ):
            raise ContextMCPError("page_size is invalid")
        expired_sources = {record.source for record in store.records if current >= record.expiry}
        records = [
            record
            for record in store.records
            if current < record.expiry
            if resource_class is None or record.resource_class == resource_class
            if source is None or record.source == source
        ]
        query_key = _query_key(resource_class, source)
        records_key = _records_key([record.handle for record in records])
        offset = _offset(arguments.get("cursor"), query_key, records_key)
        if offset > len(records):
            raise ContextMCPError("cursor is invalid")
        page = records[offset : offset + page_size]
        next_offset = offset + len(page)
        return _text(
            {
                "completeness": {
                    name: "partial" if name in expired_sources else state
                    for name, state in store.completeness.items()
                },
                "records": [
                    {
                        "handle": record.handle,
                        "source": record.source,
                        "resource_class": record.resource_class,
                        "descriptor": record.descriptor,
                        "mutable": record.mutable,
                        "expiry": record.expiry,
                    }
                    for record in page
                ],
                "next_cursor": (
                    _cursor(next_offset, query_key, records_key)
                    if next_offset < len(records)
                    else None
                ),
            }
        )
    if name == GET_TOOL:
        if set(arguments) != {"handle"}:
            raise ContextMCPError("context_get arguments are invalid")
        handle = arguments.get("handle")
        if not isinstance(handle, str) or HANDLE_RE.fullmatch(handle) is None:
            raise ContextMCPError("handle is invalid")
        try:
            record = store.get(
                handle,
                run_id=store.run_id,
                policy_digest=store.policy_digest,
                now=current,
            )
        except ValueError as exc:
            raise ContextMCPError("context record is unavailable") from exc
        return _text(
            {
                "handle": record.handle,
                "resource_class": record.resource_class,
                "descriptor": record.descriptor,
                "mutable": record.mutable,
                "record": dict(record.projections["model"]),
            }
        )
    raise ContextMCPError("context tool is invalid")


def tool_definitions() -> list[dict[str, object]]:
    """Return the two fixed closed model-facing context tools."""

    return [
        {
            "name": LIST_TOOL,
            "description": "List committed opaque review-context handles and source completeness.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "resource_class": {
                        "type": "string",
                        "enum": sorted(STORE_RESOURCE_CLASSES),
                    },
                    "source": {"type": "string", "maxLength": 256},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
                    "cursor": {"type": "string", "maxLength": 256},
                },
            },
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        },
        {
            "name": GET_TOOL,
            "description": "Read one committed review-context record by an opaque listed handle.",
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["handle"],
                "properties": {"handle": {"type": "string", "pattern": "^ctx1_[A-Za-z0-9_-]{43}$"}},
            },
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
        },
    ]
