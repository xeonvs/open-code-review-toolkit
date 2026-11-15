"""Bounded SDK and NuGet lock declarations, without restore or configuration reads."""

from __future__ import annotations

import json
from typing import Any

from ocr_toolkit.evidence.ecosystems.contracts import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.ecosystems.dotnet.limits import (
    MAX_SCALAR,
    ConstructionBudget,
    bounded_text,
)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys instead of choosing an ambiguous declaration."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate .NET JSON key")
        result[key] = value
    return result


def _without_comments(text: str) -> str:
    """Replace SDK JSON comments with whitespace without altering strings or token boundaries."""
    output = list(text)
    quoted = escaped = False
    cursor = 0
    while cursor < len(text):
        char = text[cursor]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif text[cursor : cursor + 2] in {"//", "/*"}:
            if text[cursor + 1] == "/":
                end = cursor + 2
                while end < len(text) and text[end] not in "\r\n":
                    end += 1
            else:
                closing = text.find("*/", cursor + 2)
                if closing < 0:
                    raise ValueError("unterminated .NET SDK JSON comment")
                end = closing + 2
            for index in range(cursor, end):
                if text[index] not in "\r\n":
                    output[index] = " "
            cursor = end
            continue
        cursor += 1
    return "".join(output)


def _load(text: str, *, comments: bool = False) -> dict[str, Any]:
    """Decode one bounded JSON object and validate its nesting, scalars and traversal cost."""
    bounded_text(text)
    text = text.removeprefix("\ufeff")
    if comments:
        text = _without_comments(text)
    try:
        data = json.loads(text, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except RecursionError as exc:
        raise ValueError(".NET JSON nesting limit exceeded") from exc
    if not isinstance(data, dict):
        raise ValueError(".NET JSON requires an object")
    stack = [(data, 0)]
    count = 0
    while stack:
        value, depth = stack.pop()
        count += 1
        if depth > 32 or count > 16_384:
            raise ValueError(".NET JSON construction limit exceeded")
        if isinstance(value, dict):
            stack.extend((entry, depth + 1) for pair in value.items() for entry in pair)
        elif isinstance(value, list):
            stack.extend((entry, depth + 1) for entry in value)
        elif isinstance(value, str) and len(value) > MAX_SCALAR:
            raise ValueError(".NET JSON scalar limit exceeded")
    return data


def _invalid_constant(value: str) -> None:
    """Reject non-JSON constants before they can masquerade as manifest values."""
    raise ValueError("non-JSON numeric constant in .NET manifest")


def parse_global_json(text: str) -> ManifestParseResult:
    """Keep SDK selection as declared settings, never as an installed SDK claim."""

    sdk = _load(text, comments=True).get("sdk", {})
    if not isinstance(sdk, dict):
        raise ValueError("invalid .NET SDK declaration")
    values = {
        key: sdk[key]
        for key in ("version", "rollForward", "allowPrerelease", "paths")
        if key in sdk
    }
    if any(not isinstance(values[key], str) for key in ("version", "rollForward") if key in values):
        raise ValueError("invalid .NET SDK version or rollForward")
    if "allowPrerelease" in values and type(values["allowPrerelease"]) is not bool:
        raise ValueError("invalid .NET SDK allowPrerelease")
    if "paths" in values and (
        not isinstance(values["paths"], list)
        or not all(isinstance(path, str) for path in values["paths"])
    ):
        raise ValueError("invalid .NET SDK paths")
    budget = ConstructionBudget.for_text(text)
    value = {**values, "name": "dotnet-sdk", "version_state": "declared"}
    if not budget.admit("runtime.declared", "sdk", value):
        return ManifestParseResult(
            (), (".NET SDK fact payload was truncated",), runtime_dependent=True
        )
    return ManifestParseResult(
        (
            ManifestFact(
                "runtime.declared",
                "dotnet",
                "sdk",
                value,
            ),
        )
    )


def parse_packages_lock(text: str) -> ManifestParseResult:
    """Preserve framework and direct/transitive scope from NuGet's lock format."""

    root = _load(text)
    if type(root.get("version")) is not int or root["version"] not in {1, 2}:
        raise ValueError("unsupported NuGet lock version")
    dependencies = root.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ValueError("invalid NuGet lock dependencies")
    facts = []
    notices = []
    budget = ConstructionBudget.for_text(text)
    for framework, packages in dependencies.items():
        if not framework or not isinstance(packages, dict):
            raise ValueError("invalid NuGet framework dependencies")
        for name, entry in packages.items():
            if (
                not name
                or not isinstance(entry, dict)
                or not isinstance(entry.get("type"), str)
                or entry.get("type") not in {"Direct", "Transitive", "CentralTransitive", "Project"}
            ):
                raise ValueError("invalid NuGet lock package")
            if entry["type"] == "Project":
                continue
            if not isinstance(entry.get("resolved"), str) or not entry["resolved"]:
                raise ValueError("missing NuGet resolved version")
            if entry.get("requested") is not None and not isinstance(entry["requested"], str):
                raise ValueError("invalid NuGet requested range")
            if len(facts) == MAX_MANIFEST_ITEMS:
                notices.append(f"NuGet lock facts were truncated after {MAX_MANIFEST_ITEMS} items")
                return ManifestParseResult(tuple(facts), tuple(notices))
            identity = f"{framework}:{name.casefold()}"
            value = {
                "name": name,
                "version": entry["resolved"],
                "framework": framework,
                "scope": entry["type"].casefold(),
                "requested": entry.get("requested"),
                "source": "packages.lock.json",
            }
            if not budget.admit("dependency.locked", identity, value):
                notices.append(f"NuGet lock fact payload was truncated at {budget.limit} bytes")
                return ManifestParseResult(tuple(facts), tuple(notices), runtime_dependent=True)
            facts.append(
                ManifestFact(
                    "dependency.locked",
                    "dotnet",
                    identity,
                    value,
                )
            )
    return ManifestParseResult(tuple(facts), tuple(notices))
