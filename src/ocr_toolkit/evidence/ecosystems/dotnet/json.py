"""Bounded SDK and NuGet lock declarations, without restore or configuration reads."""

from __future__ import annotations

import json
from typing import Any

from ocr_toolkit.evidence.ecosystems.contracts import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.ecosystems.dotnet.xml import MAX_SCALAR, bounded_text


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate .NET JSON key")
        result[key] = value
    return result


def _load(text: str) -> dict[str, Any]:
    bounded_text(text)
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
    raise ValueError("non-JSON numeric constant in .NET manifest")


def parse_global_json(text: str) -> ManifestParseResult:
    """Keep SDK selection as declared settings, never as an installed SDK claim."""

    sdk = _load(text).get("sdk", {})
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
    return ManifestParseResult(
        (
            ManifestFact(
                "runtime.declared",
                "dotnet",
                "sdk",
                {
                    **values,
                    "name": "dotnet-sdk",
                    "version_state": "declared",
                },
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
    for framework, packages in dependencies.items():
        if not framework or not isinstance(packages, dict):
            raise ValueError("invalid NuGet framework dependencies")
        for name, entry in packages.items():
            if (
                not name
                or not isinstance(entry, dict)
                or not isinstance(entry.get("type"), str)
                or entry.get("type") not in {"Direct", "Transitive", "Project"}
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
            facts.append(
                ManifestFact(
                    "dependency.locked",
                    "dotnet",
                    f"{framework}:{name.casefold()}",
                    {
                        "name": name,
                        "version": entry["resolved"],
                        "framework": framework,
                        "scope": entry["type"].casefold(),
                        "requested": entry.get("requested"),
                        "source": "packages.lock.json",
                    },
                )
            )
    return ManifestParseResult(tuple(facts), tuple(notices))
