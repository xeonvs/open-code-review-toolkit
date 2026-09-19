"""Bounded JSON Schema, argument authorization, and atomic result admission."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from typing import Any

import mcp_types as types
from jsonschema import Draft202012Validator
from referencing import Registry as SchemaRegistry

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenMatcher, check_text

from .contracts import (
    ARGUMENT_BYTES,
    RESPONSE_BYTES,
    RESPONSE_CHARS,
    RESPONSE_ITEMS,
    SCHEMA_BYTES,
    FederationError,
    ToolPolicy,
)
from .registry import origin

_KEYWORDS = {
    "$schema",
    "type",
    "title",
    "description",
    "default",
    "examples",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "prefixItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "enum",
    "const",
    "allOf",
    "anyOf",
    "oneOf",
}
_URL = re.compile(r"(?:[A-Za-z][A-Za-z0-9+.-]*:)?//[^\s<>\"']+")
_TEXT_BUDGETS = TextBudgets(RESPONSE_CHARS, RESPONSE_BYTES, RESPONSE_CHARS)


def encode(value: object) -> bytes:
    """Produce exact canonical finite JSON for bounds and run-local cache identity."""
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise FederationError("protocol_invalid") from None


def strings(value: object, *, depth: int = 16, nodes: int = 1024) -> Iterator[str]:
    """Walk a finite JSON tree with bounds before recursively visiting descendants."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, level = pending.pop()
        count += 1
        if count > nodes or level > depth:
            raise FederationError("oversized")
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            if len(item) > nodes - count:
                raise FederationError("oversized")
            for key, child in item.items():
                if not isinstance(key, str):
                    raise FederationError("protocol_invalid")
                yield key
                pending.append((child, level + 1))
        elif isinstance(item, list):
            if len(item) > nodes - count:
                raise FederationError("oversized")
            pending.extend((child, level + 1) for child in item)
        elif item is None or isinstance(item, bool):
            pass
        elif isinstance(item, int | float):
            if abs(item) > 1e100 or not math.isfinite(item):
                raise FederationError("protocol_invalid")
        else:
            raise FederationError("protocol_invalid")


def check_dlp(value: object, matcher: ForbiddenMatcher, *, dlp_enabled: bool = True) -> None:
    """Reject a complete JSON value if any string discloses protected content."""
    chars = 0
    for text in strings(value):
        chars += len(text)
        if chars > RESPONSE_CHARS:
            raise FederationError("oversized")
        if not dlp_enabled:
            continue
        checked = check_text(
            text, budgets=_TEXT_BUDGETS, forbidden_matcher=matcher, allow_horizontal_tabs=True
        )
        if not checked.admitted:
            raise FederationError("oversized" if checked.reason == "limit" else "dlp_rejected")


def compile_schema(
    schema: object, matcher: ForbiddenMatcher, *, dlp_enabled: bool = True
) -> Draft202012Validator:
    """Compile only the closed, nonrecursive, nonregex draft-2020-12 profile."""
    if not isinstance(schema, dict) or len(encode(schema)) > SCHEMA_BYTES:
        raise FederationError("schema_invalid")
    try:
        list(strings(schema, depth=12, nodes=512))
        pending: list[tuple[object, int]] = [(schema, 1)]
        while pending:
            node, work = pending.pop()
            if isinstance(node, bool):
                continue
            if not isinstance(node, dict) or set(node) - _KEYWORDS:
                raise FederationError("schema_invalid")
            if (
                "$schema" in node
                and node["$schema"] != "https://json-schema.org/draft/2020-12/schema"
            ):
                raise FederationError("schema_invalid")
            properties = node.get("properties", {})
            if not isinstance(properties, dict) or len(properties) > 64:
                raise FederationError("schema_invalid")
            pending.extend((child, work) for child in properties.values())
            for key in ("items", "additionalProperties"):
                if key in node:
                    pending.append((node[key], work))
            if "enum" in node and (not isinstance(node["enum"], list) or len(node["enum"]) > 32):
                raise FederationError("schema_invalid")
            for key in ("prefixItems", "allOf", "anyOf", "oneOf"):
                if key not in node:
                    continue
                branches = node[key]
                limit = 64 if key == "prefixItems" else 8
                if not isinstance(branches, list) or not branches or len(branches) > limit:
                    raise FederationError("schema_invalid")
                multiplied = work * (len(branches) if key != "prefixItems" else 1)
                if multiplied > 64:
                    raise FederationError("schema_invalid")
                pending.extend((child, multiplied) for child in branches)
        check_dlp(schema, matcher, dlp_enabled=dlp_enabled)
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema, registry=SchemaRegistry())
    except FederationError:
        raise
    except Exception:
        raise FederationError("schema_invalid") from None


def arguments(
    value: object,
    policy: ToolPolicy,
    validator: Draft202012Validator,
    matcher: ForbiddenMatcher,
    *,
    dlp_enabled: bool = True,
) -> tuple[dict[str, Any], bytes]:
    """Validate and authorize every nested model-selected argument before dispatch."""
    if not isinstance(value, dict):
        raise FederationError("arguments_invalid")
    leaves = list(strings(value))
    canonical = encode(value)
    if len(canonical) > ARGUMENT_BYTES:
        raise FederationError("oversized")
    if next(validator.iter_errors(value), None) is not None:
        raise FederationError("arguments_invalid")
    for leaf in leaves:
        for match in _URL.finditer(leaf):
            try:
                candidate = origin(match.group(0), endpoint=True)
            except FederationError:
                raise FederationError("origin_denied") from None
            if candidate not in policy.resource_origins:
                raise FederationError("origin_denied")
    check_dlp(value, matcher, dlp_enabled=dlp_enabled)
    return value, canonical


def result(
    value: types.CallToolResult,
    validator: Draft202012Validator | None,
    matcher: ForbiddenMatcher,
    *,
    dlp_enabled: bool = True,
) -> types.CallToolResult:
    """Return text/structured data only after whole-result schema, limits and DLP admission."""
    if value.is_error:
        raise FederationError("tool_failed")
    if len(value.content) > RESPONSE_ITEMS or any(
        not isinstance(block, types.TextContent) for block in value.content
    ):
        raise FederationError("protocol_invalid")
    content = [types.TextContent(type="text", text=block.text) for block in value.content]
    structured = value.structured_content
    candidate = {"content": [block.text for block in content], "structured": structured}
    check_dlp(candidate, matcher, dlp_enabled=dlp_enabled)
    if len(encode(candidate)) > RESPONSE_BYTES:
        raise FederationError("oversized")
    if validator is not None and (
        structured is None or next(validator.iter_errors(structured), None) is not None
    ):
        raise FederationError("protocol_invalid")
    return types.CallToolResult(content=content, structured_content=structured, is_error=False)


def string_values(value: object) -> Iterator[str]:
    """Project already bounded external string values without inventing protected keys."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from string_values(child)
