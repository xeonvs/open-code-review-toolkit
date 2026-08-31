"""Serve bounded repository evidence through read-only MCP over stdio."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from ocr_toolkit import __version__
from ocr_toolkit.context.mcp import (
    GET_TOOL,
    LIST_TOOL,
    ContextMCPError,
    call_context_tool,
    tool_definitions,
)
from ocr_toolkit.context.store import ContextStore
from ocr_toolkit.evidence.actions import record_action
from ocr_toolkit.evidence.model import CoverageRecord, EvidenceDelta, EvidenceRecord
from ocr_toolkit.evidence.policy.schema import is_legacy_policy_value
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError

TOOL_NAME = "ocr_toolkit_evidence"
SEARCH_TOOL_NAME = "ocr_toolkit_evidence_search"
COVERAGE_TOOL_NAME = "ocr_toolkit_evidence_coverage"
SERVER_NAME = "open-code-review-toolkit-evidence"
PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    PROTOCOL_VERSION,
}
MAX_REQUEST_BYTES = 64_000
MAX_RESPONSE_BYTES = 64_000
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
DEFAULT_SEARCH_RESULTS = 20
MAX_SEARCH_RESULTS = 50
MAX_SEARCH_QUERY_CHARS = 128
MAX_SEARCH_QUERY_TOKENS = 8
_SEARCH_OPERATOR_CHARACTERS = frozenset("*?[]{}()|\\^$~:=!<>`\"'")
_SEARCH_VALUE_KEYS: dict[str, frozenset[str]] = {
    "dependency": frozenset({"identity", "name", "package", "requirement", "version"}),
    "runtime": frozenset({"identity", "name", "runtime", "version"}),
    "container": frozenset({"digest", "identity", "image", "name", "tag", "version"}),
    "ci": frozenset({"digest", "identity", "image", "name", "tag", "version"}),
    "application": frozenset({"identity", "name", "version"}),
    "framework": frozenset({"framework", "identity", "name", "plugin", "version"}),
    "template": frozenset({"engine", "identity", "name", "path"}),
    "repository": frozenset(
        {"decision_id", "identity", "matched_paths", "name", "path", "scope", "scopes"}
    ),
    "ansible": frozenset({"collection", "group", "identity", "name", "role", "version"}),
}
_MISSING_REQUEST_ID = object()


class EvidenceMCPError(ValueError):
    """Describe one safe client-visible evidence MCP request error."""


@dataclass(frozen=True, slots=True)
class _Query:
    """Hold normalized list filters used to bind an opaque cursor."""

    kind: str | None
    delta_kind: str | None
    component: str | None
    ref: str | None

    def key(self) -> str:
        """Return a stable fingerprint for cursor/query binding."""

        value = json.dumps(
            {
                "component": self.component,
                "delta_kind": self.delta_kind,
                "kind": self.kind,
                "ref": self.ref,
            },
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


def evidence_summary(store: EvidenceStore) -> dict[str, object]:
    """Build compact counts and immutable refs without detailed values."""

    kinds: dict[str, int] = {}
    components: dict[str, int] = {}
    changes: dict[str, int] = {}
    delta_kinds: dict[str, int] = {}
    for record in store.records:
        kinds[record.kind] = kinds.get(record.kind, 0) + 1
        components[record.component] = components.get(record.component, 0) + 1
    for delta in store.safe_deltas:
        changes[delta.change] = changes.get(delta.change, 0) + 1
        delta_kinds[delta.kind] = delta_kinds.get(delta.kind, 0) + 1
    coverage_states: dict[str, int] = {}
    for coverage_record in store.coverage:
        coverage_states[coverage_record.state.value] = (
            coverage_states.get(coverage_record.state.value, 0) + 1
        )
    policy_records = tuple(
        record
        for record in store.records
        if record.kind in {"repository.accepted_decision", "repository.guidance"}
    )
    mr_context_records = tuple(
        record for record in store.records if record.kind == "review.merge_request_context"
    )
    merge_request_context = {
        "contract": ("review.merge-request-context/v1" if mr_context_records else "absent"),
        "records": len(mr_context_records),
        "trust": "invocation" if mr_context_records else None,
        "content_role": "untrusted_data" if mr_context_records else None,
        "authoritative_for_actions": False,
    }
    policy = {
        "accepted_decisions": sum(
            record.kind == "repository.accepted_decision" for record in policy_records
        ),
        "guidance_documents": sum(
            record.kind == "repository.guidance" for record in policy_records
        ),
        "structured_target_records": sum(
            not is_legacy_policy_value(record.value)
            and record.ref.value in {"base", "policy"}
            and record.trust.value == "target_repository"
            for record in policy_records
        ),
        "legacy_text_records": sum(
            is_legacy_policy_value(record.value) for record in policy_records
        ),
        "target_only": all(
            record.ref.value in {"base", "policy"} and record.trust.value == "target_repository"
            for record in policy_records
        ),
        "authoritative_for_actions": False,
    }
    return {
        "schema_version": store.schema_version,
        "policy": policy,
        "merge_request_context": merge_request_context,
        "policy_ref": store.policy.commit_sha if store.policy else None,
        "coverage_contract": ("repository.evidence-coverage/v1" if store.coverage else "absent"),
        "base": store.base.commit_sha if store.base else None,
        "head": store.head.commit_sha if store.head else None,
        "records": len(store.records),
        "coverage_records": len(store.coverage),
        "coverage_states": dict(sorted(coverage_states.items())),
        "kinds": dict(sorted(kinds.items())),
        "components": dict(sorted(components.items())),
        "deltas": dict(sorted(changes.items())),
        "delta_kinds": dict(sorted(delta_kinds.items())),
        "diagnostics": sorted(store.diagnostics),
    }


def _optional_filter(arguments: dict[str, object], name: str) -> str | None:
    """Read one bounded optional exact-match filter."""

    value = arguments.get(name)
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > 256:
        raise EvidenceMCPError(f"{name} must be a non-empty string of at most 256 characters")
    if any(
        character == "\x7f" or unicodedata.category(character) in {"Cc", "Cf"}
        for character in value
    ):
        raise EvidenceMCPError(f"{name} must not contain control or format characters")
    return value


def _encode_cursor(offset: int, query: _Query) -> str:
    """Encode an opaque, query-bound self-validating pagination position."""

    state = f"{offset}:{query.key()}"
    checksum = hashlib.sha256(f"ocr-evidence-v1:{state}".encode()).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{state}:{checksum}".encode()).decode().rstrip("=")


def _decode_cursor(value: object, query: _Query) -> int:
    """Validate and decode a cursor bound to the current filters."""

    if value is None or value == "":
        return 0
    if not isinstance(value, str) or len(value) > 256:
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
        delta_kind=_optional_filter(arguments, "delta_kind"),
        component=_optional_filter(arguments, "component"),
        ref=_optional_filter(arguments, "ref"),
    )
    if query.delta_kind is not None and query.kind != "repository.evidence_delta":
        raise EvidenceMCPError("delta_kind requires kind=repository.evidence_delta")
    if query.kind == "repository.evidence_delta" and query.ref is not None:
        raise EvidenceMCPError("evidence deltas span base and head and do not accept ref")
    if query.ref not in {None, "base", "head", "policy", "shared"}:
        raise EvidenceMCPError("ref must be base, head, policy, or shared")
    page_size = arguments.get("page_size", DEFAULT_PAGE_SIZE)
    if isinstance(page_size, bool) or not isinstance(page_size, int):
        raise EvidenceMCPError("page_size must be an integer")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise EvidenceMCPError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    offset = _decode_cursor(arguments.get("cursor"), query)
    if query.kind == "repository.evidence_delta":
        candidates: tuple[EvidenceRecord | CoverageRecord | EvidenceDelta, ...] = store.safe_deltas
    else:
        candidates = (*store.records, *store.coverage)
    records = [
        record
        for record in candidates
        if (query.kind is None or (isinstance(record, EvidenceDelta) or record.kind == query.kind))
        and (
            query.delta_kind is None
            or (isinstance(record, EvidenceDelta) and record.kind == query.delta_kind)
        )
        and (query.component is None or record.component == query.component)
        and (
            query.ref is None
            or (not isinstance(record, EvidenceDelta) and record.ref.value == query.ref)
        )
    ]
    if offset > len(records):
        raise EvidenceMCPError("cursor points beyond the available evidence")
    page = records[offset : offset + page_size]
    next_offset = offset + len(page)
    return {
        "records": [
            record.to_mcp_dict() if isinstance(record, EvidenceDelta) else record.to_dict()
            for record in page
        ],
        "next_cursor": _encode_cursor(next_offset, query) if next_offset < len(records) else None,
        "returned": len(page),
    }


def _get_record(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
    """Return one record selected by its stable content-addressed ID."""

    record_id = arguments.get("id")
    valid_id = isinstance(record_id, str) and (
        (len(record_id) == 68 and record_id.startswith("ev1_"))
        or (len(record_id) == 69 and record_id.startswith(("cov1_", "del1_")))
    )
    if not valid_id:
        raise EvidenceMCPError("id must be a stable ev1, cov1, or del1 evidence identifier")
    all_records: tuple[EvidenceRecord | CoverageRecord | EvidenceDelta, ...] = (
        *store.records,
        *store.coverage,
        *store.safe_deltas,
    )
    record = next((item for item in all_records if item.id == record_id), None)
    if record is None:
        raise EvidenceMCPError("evidence record was not found")
    return {
        "record": (record.to_mcp_dict() if isinstance(record, EvidenceDelta) else record.to_dict())
    }


def _search_query(value: object) -> tuple[str, ...]:
    """Normalize one bounded literal query without accepting search operators."""

    if not isinstance(value, str) or not 1 <= len(value) <= MAX_SEARCH_QUERY_CHARS:
        raise EvidenceMCPError(
            f"query must contain between 1 and {MAX_SEARCH_QUERY_CHARS} characters"
        )
    if any(
        character in _SEARCH_OPERATOR_CHARACTERS or unicodedata.category(character) in {"Cc", "Cf"}
        for character in value
    ):
        raise EvidenceMCPError("query must be literal text without operators or controls")
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    if len(normalized) > MAX_SEARCH_QUERY_CHARS:
        raise EvidenceMCPError("normalized query exceeds the character limit")
    tokens = tuple(normalized.split())
    if not tokens or len(tokens) > MAX_SEARCH_QUERY_TOKENS:
        raise EvidenceMCPError(
            f"query must contain between 1 and {MAX_SEARCH_QUERY_TOKENS} literal tokens"
        )
    if any(token in {"and", "or", "not"} for token in tokens):
        raise EvidenceMCPError("query must be literal text without boolean operators")
    return tokens


def _search_scalars(value: object, allowed_keys: frozenset[str], *, key: str = "") -> list[str]:
    """Extract only per-kind allowlisted scalar leaves from one admitted value."""

    if isinstance(value, Mapping):
        result: list[str] = []
        for child_key, child in value.items():
            if isinstance(child_key, str):
                result.extend(_search_scalars(child, allowed_keys, key=child_key))
        return result
    if isinstance(value, (list, tuple)):
        if key not in allowed_keys:
            return []
        return [
            str(item)
            for item in value
            if isinstance(item, (str, int)) and not isinstance(item, bool)
        ]
    if key in allowed_keys and isinstance(value, (str, int)) and not isinstance(value, bool):
        return [str(value)]
    return []


def _normalized_search_fields(record: EvidenceRecord | EvidenceDelta) -> tuple[str, ...]:
    """Return normalized searchable fields without widening the response projection."""

    if isinstance(record, EvidenceDelta):
        values = [record.kind, record.component, record.identity]
        allowed = _SEARCH_VALUE_KEYS.get(record.kind.split(".", 1)[0], frozenset({"identity"}))
        values.extend(_search_scalars(record.before, allowed))
        values.extend(_search_scalars(record.after, allowed))
    else:
        values = [record.kind, record.component, record.source_path]
        allowed = _SEARCH_VALUE_KEYS.get(record.kind.split(".", 1)[0], frozenset({"identity"}))
        values.extend(_search_scalars(record.value, allowed))
    return tuple(unicodedata.normalize("NFKC", value).casefold() for value in values)


def _search_records(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
    """Search admitted metadata and allowlisted scalars without returning matched values."""

    tokens = _search_query(arguments.get("query"))
    kind = _optional_filter(arguments, "kind")
    component = _optional_filter(arguments, "component")
    ref = _optional_filter(arguments, "ref")
    if ref not in {None, "base", "head", "policy", "shared"}:
        raise EvidenceMCPError("ref must be base, head, policy, or shared")
    max_results = arguments.get("max_results", DEFAULT_SEARCH_RESULTS)
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise EvidenceMCPError("max_results must be an integer")
    if not 1 <= max_results <= MAX_SEARCH_RESULTS:
        raise EvidenceMCPError(f"max_results must be between 1 and {MAX_SEARCH_RESULTS}")
    candidates: tuple[EvidenceRecord | EvidenceDelta, ...] = (*store.records, *store.safe_deltas)
    matches: list[dict[str, object]] = []
    total_matches = 0
    for record in candidates:
        record_kind = record.kind
        record_ref = None if isinstance(record, EvidenceDelta) else record.ref.value
        if (
            (kind is not None and record_kind != kind)
            or (component is not None and record.component != component)
            or (ref is not None and record_ref != ref)
        ):
            continue
        fields = _normalized_search_fields(record)
        if not all(any(token in field for field in fields) for token in tokens):
            continue
        total_matches += 1
        if len(matches) >= max_results:
            continue
        item: dict[str, object] = {
            "id": record.id,
            "kind": (
                "repository.evidence_delta" if isinstance(record, EvidenceDelta) else record.kind
            ),
            "component": record.component,
        }
        if isinstance(record, EvidenceDelta):
            item["delta_kind"] = record.kind
        else:
            item.update({"ref": record.ref.value, "source_path": record.source_path})
        matches.append(item)
    return {
        "schema_version": "ocr.evidence-search/v1",
        "matches": matches,
        "returned": len(matches),
        "total_matches": total_matches,
        "truncated": total_matches > len(matches),
    }


def _coverage_query(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
    """Return whether one exact evidence scope can support a negative conclusion."""

    kind = _optional_filter(arguments, "kind")
    ref = _optional_filter(arguments, "ref")
    component = _optional_filter(arguments, "component")
    source_path = _optional_filter(arguments, "path")
    if kind is None:
        raise EvidenceMCPError("kind is required")
    if ref not in {"base", "head"}:
        raise EvidenceMCPError("ref must be base or head")
    matching_records = [
        record
        for record in store.records
        if record.kind == kind
        and record.ref.value == ref
        and (component is None or record.component == component)
        and (source_path is None or record.source_path == source_path)
    ]
    applicable = [
        record
        for record in store.coverage
        if record.domain == kind
        and record.ref.value == ref
        and (component is None or record.component == component)
        and (source_path is None or record.scope == source_path)
    ]
    state_counts: dict[str, int] = {}
    for record in applicable:
        state_counts[record.state.value] = state_counts.get(record.state.value, 0) + 1
    complete = bool(applicable) and all(record.state.value == "complete" for record in applicable)
    return {
        "schema_version": "ocr.evidence-coverage-query/v1",
        "state": "complete" if complete else "unknown",
        "matches": len(matching_records),
        "coverage_records": len(applicable),
        "coverage_states": dict(sorted(state_counts.items())),
        "truncated": False,
        "absence_authoritative": complete and not matching_records,
    }


def call_tool(store: EvidenceStore, arguments: object) -> dict[str, object]:
    """Execute one closed, read-only evidence action."""

    if not isinstance(arguments, dict):
        raise EvidenceMCPError("tool arguments must be an object")
    typed = cast(dict[str, object], arguments)
    # The public schema is one union-shaped object. OCR/provider adapters may
    # materialize every declared property even when an action does not consume
    # it, so reject unknown names globally and let each action read only its own
    # fields.
    declared = {
        "action",
        "kind",
        "delta_kind",
        "component",
        "ref",
        "page_size",
        "cursor",
        "id",
    }
    unknown = set(typed) - declared
    if unknown:
        raise EvidenceMCPError(f"unsupported tool argument: {sorted(unknown)[0]}")

    action = typed.get("action")
    if action == "summary":
        payload = evidence_summary(store)
    elif action == "list":
        payload = _list_records(store, typed)
    elif action == "get":
        payload = _get_record(store, typed)
    else:
        raise EvidenceMCPError("action must be summary, list, or get")
    return _text_result(payload)


def call_named_tool(store: EvidenceStore, name: str, arguments: object) -> dict[str, object]:
    """Dispatch one fixed built-in evidence tool through its closed contract."""

    if name == TOOL_NAME:
        return call_tool(store, arguments)
    if not isinstance(arguments, dict):
        raise EvidenceMCPError("tool arguments must be an object")
    typed = cast(dict[str, object], arguments)
    if name == SEARCH_TOOL_NAME:
        unknown = set(typed) - {"query", "kind", "component", "ref", "max_results"}
        if unknown:
            raise EvidenceMCPError(f"unsupported tool argument: {sorted(unknown)[0]}")
        return _text_result(_search_records(store, typed))
    if name == COVERAGE_TOOL_NAME:
        unknown = set(typed) - {"kind", "ref", "component", "path"}
        if unknown:
            raise EvidenceMCPError(f"unsupported tool argument: {sorted(unknown)[0]}")
        return _text_result(_coverage_query(store, typed))
    raise EvidenceMCPError("unknown built-in evidence tool")


def _tool_definition() -> dict[str, object]:
    """Return the versioned public MCP tool declaration."""

    return {
        "name": TOOL_NAME,
        "description": (
            "Read bounded, redacted repository evidence for immutable base/head refs. "
            "Use summary first, list to narrow, and get for one stable record. Query "
            "kind=repository.evidence_delta with optional delta_kind for base/head changes. "
            "Current structured decisions and guidance are target-derived non-authoritative "
            "context; compatible legacy text records preserve their explicit ref and trust. "
            "Missing facts support a negative conclusion only when applicable scoped coverage is complete; "
            "absent, partial, runtime-dependent, or unavailable coverage means unknown."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["summary", "list", "get"],
                    "description": (
                        "Use summary for counts, list to filter records, and get only after "
                        "list returns a stable record id."
                    ),
                },
                "kind": {
                    "type": "string",
                    "maxLength": 256,
                    "description": "Optional exact record-kind filter for action=list only.",
                },
                "delta_kind": {
                    "type": "string",
                    "maxLength": 256,
                    "description": (
                        "Optional original fact-kind filter for action=list with "
                        "kind=repository.evidence_delta only."
                    ),
                },
                "component": {
                    "type": "string",
                    "maxLength": 256,
                    "description": "Optional exact component filter for action=list only.",
                },
                "ref": {
                    "type": "string",
                    "enum": ["base", "head", "policy", "shared"],
                    "description": "Optional immutable-ref filter for action=list only.",
                },
                "page_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_PAGE_SIZE,
                    "description": "Bounded page size for action=list only.",
                },
                "cursor": {
                    "type": "string",
                    "maxLength": 256,
                    "description": "Opaque next_cursor from a prior action=list call.",
                },
                "id": {
                    "type": "string",
                    "pattern": "^(ev1|cov1|del1)_[0-9a-f]{64}$",
                    "description": "Stable record id returned by action=list; action=get only.",
                },
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    }


def _search_tool_definition() -> dict[str, object]:
    """Declare the literal, bounded evidence search tool."""

    return {
        "name": SEARCH_TOOL_NAME,
        "description": (
            "Locate unknown evidence records by bounded literal text after using the summary. "
            "Search covers admitted paths, identities, and per-kind allowlisted scalar fields; "
            "results contain stable IDs but never matched values. Use the primary evidence tool "
            "with action=get for a selected ID."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_SEARCH_QUERY_CHARS,
                    "description": "One to eight literal NFKC/case-insensitive tokens; no operators.",
                },
                "kind": {"type": "string", "maxLength": 256},
                "component": {"type": "string", "maxLength": 256},
                "ref": {"type": "string", "enum": ["base", "head", "policy", "shared"]},
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_SEARCH_RESULTS,
                },
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    }


def _coverage_tool_definition() -> dict[str, object]:
    """Declare the exact scoped absence-proof tool."""

    return {
        "name": COVERAGE_TOOL_NAME,
        "description": (
            "Check exact scoped evidence completeness before making a negative claim. "
            "absence_authoritative is true only for applicable complete coverage with zero "
            "matching records and no truncation; every missing, partial, runtime-dependent, "
            "or unavailable scope returns unknown."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "ref"],
            "properties": {
                "kind": {
                    "type": "string",
                    "maxLength": 256,
                    "description": "Exact evidence kind and coverage domain.",
                },
                "ref": {"type": "string", "enum": ["base", "head"]},
                "component": {"type": "string", "maxLength": 256},
                "path": {
                    "type": "string",
                    "maxLength": 256,
                    "description": "Optional exact record source path and coverage scope.",
                },
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    }


def evidence_tool_definitions() -> list[dict[str, object]]:
    """Return the fixed built-in evidence tools in stable routing order."""

    return [_tool_definition(), _search_tool_definition(), _coverage_tool_definition()]


def _success(request_id: object, result: object) -> dict[str, object]:
    """Create a JSON-RPC success response."""

    response: dict[str, object] = {"jsonrpc": "2.0", "result": result}
    if request_id is not _MISSING_REQUEST_ID:
        response["id"] = request_id
    return response


def _error(request_id: object, code: int, message: str) -> dict[str, object]:
    """Create a JSON-RPC error response without repository-derived details."""

    response: dict[str, object] = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
    }
    if request_id is not _MISSING_REQUEST_ID:
        response["id"] = request_id
    return response


def handle_request(
    store: EvidenceStore,
    raw: object,
    context_store: ContextStore | None = None,
    *,
    action_receipt_path: Path | None = None,
) -> dict[str, object] | None:
    """Handle one validated JSON-RPC request or notification."""

    if not isinstance(raw, dict) or raw.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid Request")
    request_id = raw.get("id", _MISSING_REQUEST_ID)
    method = raw.get("method")
    params = raw.get("params", {})
    if isinstance(method, str) and method.startswith("notifications/") and "id" not in raw:
        return None
    if method == "initialize":
        if not isinstance(params, dict):
            return _error(request_id, -32602, "Invalid params")
        version = params.get("protocolVersion")
        negotiated_version = (
            version
            if isinstance(version, str) and version in SUPPORTED_PROTOCOL_VERSIONS
            else PROTOCOL_VERSION
        )
        return _success(
            request_id,
            {
                "protocolVersion": negotiated_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": __version__},
            },
        )
    if method == "ping":
        return _success(request_id, {})
    if method == "tools/list":
        tools = evidence_tool_definitions()
        if context_store is not None:
            tools.extend(tool_definitions())
        return _success(request_id, {"tools": tools})
    if method == "tools/call":
        if not isinstance(params, dict):
            return _error(request_id, -32602, "Invalid tool call")
        name = params.get("name")
        if isinstance(name, str) and name in {TOOL_NAME, SEARCH_TOOL_NAME, COVERAGE_TOOL_NAME}:
            try:
                result = call_named_tool(store, str(name), params.get("arguments", {}))
            except EvidenceMCPError as exc:
                return _success(
                    request_id,
                    {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                )
            if action_receipt_path is not None:
                arguments = params.get("arguments", {})
                if name == TOOL_NAME:
                    action = arguments.get("action") if isinstance(arguments, dict) else None
                else:
                    action = "search" if name == SEARCH_TOOL_NAME else "coverage"
                try:
                    record_action(action_receipt_path, action)
                except (OSError, ValueError):
                    pass
            return _success(request_id, result)
        if context_store is not None and isinstance(name, str) and name in {LIST_TOOL, GET_TOOL}:
            try:
                result = call_context_tool(context_store, str(name), params.get("arguments", {}))
            except ContextMCPError as exc:
                return _success(
                    request_id,
                    {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                )
            return _success(request_id, result)
        return _error(request_id, -32602, "Invalid tool call")
    return _error(request_id, -32601, "Method not found")


def _bounded_lines(stdin: TextIO) -> Iterator[str]:
    """Read protocol lines without allowing one request to grow without a bound."""

    while True:
        # TextIO limits code points rather than bytes. The byte check below remains
        # authoritative, while this cap prevents unbounded allocation before it.
        line = stdin.readline(MAX_REQUEST_BYTES + 2)
        if not line:
            return
        if not line.endswith("\n") or len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
            yield ""
            while line and not line.endswith("\n"):
                line = stdin.readline(MAX_REQUEST_BYTES + 2)
            continue
        yield line


def serve(
    store_path: Path,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    *,
    action_receipt_path: Path | None = None,
    context_path: Path | None = None,
    context_run_id: str = "",
    context_policy_digest: str = "",
) -> int:
    """Serve newline-delimited MCP JSON-RPC until the client closes stdin."""

    try:
        store = EvidenceStore.read(store_path)
    except (OSError, EvidenceStoreError) as exc:
        print(f"Cannot load evidence store: {exc}", file=sys.stderr)
        return 2
    context_store = None
    if context_path is not None:
        try:
            context_store = ContextStore.read(
                context_path,
                expected_run_id=context_run_id,
                expected_policy_digest=context_policy_digest,
                now=int(time.time()),
            )
        except (OSError, ValueError) as exc:
            print(f"Cannot load context store: {exc}", file=sys.stderr)
            return 2
    for line in _bounded_lines(stdin):
        has_request_id = True
        if not line or len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
            response = _error(None, -32700, "Request exceeds the byte limit")
        else:
            try:
                request = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                response = _error(None, -32700, "Parse error")
            else:
                has_request_id = isinstance(request, dict) and "id" in request
                response = handle_request(
                    store,
                    request,
                    context_store,
                    action_receipt_path=action_receipt_path,
                )
        if response is None or not has_request_id:
            continue
        serialized = json.dumps(response, separators=(",", ":"), ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_RESPONSE_BYTES:
            safe_id = response.get("id")
            if not isinstance(safe_id, (str, int)) or isinstance(safe_id, bool):
                safe_id = None
            serialized = json.dumps(_error(safe_id, -32603, "Response exceeds the byte limit"))
        stdout.write(serialized + "\n")
        stdout.flush()
    return 0
