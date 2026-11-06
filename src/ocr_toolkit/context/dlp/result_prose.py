"""Closed result prose paths and pure copy updates; identities and code stay literal."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp.decoding import RepresentationLimit

_REPR_SPECIAL = re.compile(r"[\\'\"\x00-\x1f\x7f-\U0010ffff]")


def bounded_prose_text(value: Any, budgets: TextBudgets) -> str:
    """Bound the exact JSON-to-text representation before allocating it.

    Consumers use Python's container representation. Account for its quoting,
    escapes and punctuation, rather than assuming independently bounded leaves
    imply a bounded or safe complete string. No custom repr is executed.
    """

    chars = size = nodes = 0

    def charge(characters: int, byte_count: int) -> None:
        nonlocal chars, size
        chars += characters
        size += byte_count
        if chars > budgets.max_chars or size > budgets.max_bytes:
            raise RepresentationLimit("rendered prose budget")

    if type(value) is str:
        charge(len(value), 0)
        for start in range(0, len(value), 4096):
            charge(0, len(value[start : start + 4096].encode("utf-8")))
        if value.count("\n") + 1 > budgets.max_lines:
            raise RepresentationLimit("rendered prose lines")
        return value.strip()
    if value is None:
        return ""
    if budgets.max_lines < 1:
        raise RepresentationLimit("rendered prose lines")
    ancestors: set[int] = set()
    stack = [(value, 0, False)]
    while stack:
        item, depth, closing = stack.pop()
        if closing:
            ancestors.remove(id(item))
            continue
        nodes += 1
        if nodes > 32768 or depth > 64:
            raise RepresentationLimit("rendered prose structure")
        if type(item) is str:
            quote = '"' if "'" in item and '"' not in item else "'"
            charge(len(item) + 2, 2)
            for start in range(0, len(item), 4096):
                charge(0, len(item[start : start + 4096].encode("utf-8")))
            for match in _REPR_SPECIAL.finditer(item):
                char = match[0]
                if char in {quote, "\\", "\t", "\n", "\r"}:
                    charge(1, 1)
                elif not char.isprintable():
                    width = 4 if ord(char) <= 255 else 6 if ord(char) <= 65535 else 10
                    charge(width - 1, width - len(char.encode("utf-8")))
        elif type(item) in {list, dict}:
            children_count = len(item) * (2 if isinstance(item, dict) else 1)
            if id(item) in ancestors or nodes + len(stack) + children_count > 32768:
                raise RepresentationLimit("rendered prose structure")
            ancestors.add(id(item))
            stack.append((item, depth, True))
            punctuation = 2 + max(0, len(item) - 1) * 2
            if isinstance(item, dict):
                punctuation += 2 * len(item)
                if any(type(key) is not str for key in item):
                    raise RepresentationLimit("rendered prose key")
                children = (part for pair in item.items() for part in pair)
            else:
                children = iter(item)
            charge(punctuation, punctuation)
            stack.extend((child, depth + 1, False) for child in children)
        elif item is None or type(item) in {bool, int, float}:
            # The diagnostic prose channel does not need unbounded decimal
            # conversion, including when a host disables Python's digit guard.
            if type(item) is int and item.bit_length() > 16384:
                raise RepresentationLimit("rendered prose scalar")
            try:
                length = len(repr(item))
            except ValueError as exc:
                raise RepresentationLimit("rendered prose scalar") from exc
            charge(length, length)
        else:
            raise RepresentationLimit("rendered prose type")
    return str(value).strip()


def prose_slots(payload: dict[str, Any]) -> Iterator[tuple[tuple[object, ...], Any]]:
    """Select complete consumer slots; structured warnings retain their metadata."""

    if "message" in payload:
        yield ("message",), payload["message"]
    comments = payload.get("comments")
    if isinstance(comments, list):
        for index, item in enumerate(comments):
            if isinstance(item, dict) and "content" in item:
                yield ("comments", index, "content"), item["content"]
    warnings = payload.get("warnings")
    if isinstance(warnings, list):
        for index, item in enumerate(warnings):
            yield ("warnings", index), item


def is_prose_path(path: tuple[object, ...]) -> bool:
    return bool(
        (path and path[0] == "message")
        or (len(path) >= 3 and path[0] == "comments" and path[2] == "content")
        or (path and path[0] == "warnings")
    )


def apply_prepared(payload: dict[str, Any], prepared: Mapping[tuple[object, ...], str]) -> None:
    """Update an already independent JSON tree without renaming a field or identity."""

    for path, text in prepared.items():
        target: Any = payload
        try:
            for key in path[:-1]:
                target = target[key]
            # Sanitization may remove an ancestor or the destination itself.
            # Never recreate a removed field through a presentation update.
            if isinstance(target, dict):
                if path[-1] in target:
                    target[path[-1]] = text
            elif isinstance(target, list):
                index = path[-1]
                if isinstance(index, int):
                    target[index] = text
        except (KeyError, IndexError, TypeError):
            continue


def prepared_copy(
    payload: dict[str, Any], prepared: Mapping[tuple[object, ...], str]
) -> dict[str, Any]:
    """Clone each changed ancestor once; preserve the raw tree for policy checks."""

    result = dict(payload)
    copies: dict[tuple[object, ...], Any] = {(): result}
    for path, text in prepared.items():
        for i, key in enumerate(path[:-1], 1):
            prefix = path[:i]
            if prefix not in copies:
                parent = copies[path[: i - 1]]
                child = parent[key]
                copied = dict(child) if isinstance(child, dict) else list(child)
                parent[key] = copies[prefix] = copied
        copies[path[:-1]][path[-1]] = text
    return result


def prose_values(
    payload: dict[str, Any], *, include_keys: bool = False
) -> Iterator[tuple[tuple[object, ...], str]]:
    """Enumerate the closed prose projection, optionally including hostile map keys."""

    stack: list[tuple[tuple[object, ...], Any]] = []
    if "message" in payload:
        stack.append((("message",), payload["message"]))
    comments = payload.get("comments")
    if isinstance(comments, list):
        stack.extend(
            (("comments", i, "content"), item["content"])
            for i, item in enumerate(comments)
            if isinstance(item, dict) and "content" in item
        )
    if "warnings" in payload:
        stack.append((("warnings",), payload["warnings"]))
    while stack:
        path, value = stack.pop()
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, dict):
            stack.extend(((*path, k), v) for k, v in value.items())
            if include_keys:
                yield from (((*path, k), k) for k in value if isinstance(k, str))
        elif isinstance(value, list):
            stack.extend(((*path, i), v) for i, v in enumerate(value))
