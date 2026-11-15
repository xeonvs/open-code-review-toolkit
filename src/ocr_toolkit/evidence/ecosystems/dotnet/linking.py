"""Associate central declarations only when bounded inputs prove a static link."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import PurePosixPath

from ocr_toolkit.evidence.ecosystems.contracts import MAX_MANIFEST_ITEMS
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceValue

PROJECT_SUFFIXES = {".csproj", ".fsproj", ".vbproj"}


def fact_value(record: EvidenceRecord) -> Mapping[str, EvidenceValue]:
    """Return one normalized typed fact from an admitted evidence record."""

    value = record.value
    nested = value.get("fact") if isinstance(value, Mapping) else None
    return nested if isinstance(nested, Mapping) else {}


def project_path(path: str) -> bool:
    return PurePosixPath(path).suffix.casefold() in PROJECT_SUFFIXES


def nearest_file(path: str, basename: str, paths: frozenset[str]) -> str | None:
    """Use exact canonical automatic-discovery names, not casefold guesses."""

    for parent in PurePosixPath(path).parents:
        candidate = str(parent / basename)
        if candidate in paths:
            return candidate
    return None


def central_links(
    records: tuple[EvidenceRecord, ...],
    paths: frozenset[str],
    source_states: Mapping[str, str],
) -> tuple[tuple[EvidenceRecord, ...], tuple[str, ...]]:
    """Keep links project-scoped; do not claim an effective MSBuild version."""

    grouped: dict[str, list[EvidenceRecord]] = {}
    for record in records:
        if record.component == "dotnet":
            grouped.setdefault(record.source_path, []).append(record)

    def safe(path: str) -> bool:
        sources = [record for record in grouped.get(path, ()) if record.kind == "dotnet.source"]
        return (
            source_states.get(path) == "complete"
            and len(sources) == 1
            and fact_value(sources[0]).get("interpretation") == "declared"
        )

    def settings(path: str) -> list[EvidenceValue]:
        return [
            fact_value(record).get("value")
            for record in grouped.get(path, ())
            if record.kind == "dotnet.property"
            and str(fact_value(record).get("name")).casefold() == "managepackageversionscentrally"
        ]

    links = []
    for project in sorted(path for path in grouped if project_path(path)):
        central = nearest_file(project, "Directory.Packages.props", paths)
        if central is None or not safe(project) or not safe(central):
            continue
        build_files = [
            nearest_file(project, name, paths)
            for name in ("Directory.Build.props", "Directory.Build.targets")
        ]
        if any(path is not None and (not safe(path) or settings(path)) for path in build_files):
            continue
        if [str(value).casefold() for value in settings(central)] != ["true"]:
            continue
        if settings(project) and [str(value).casefold() for value in settings(project)] != ["true"]:
            continue
        versions: dict[str, list[EvidenceRecord]] = {}
        for record in grouped[central]:
            value = fact_value(record)
            if record.kind == "dotnet.package_version":
                versions.setdefault(str(value.get("name")).casefold(), []).append(record)
        references = [
            record
            for record in grouped[project]
            if record.kind == "dependency.declared"
            and fact_value(record).get("scope") == "packagereference"
        ]
        counts: dict[str, int] = {}
        for record in references:
            name = str(fact_value(record).get("name")).casefold()
            counts[name] = counts.get(name, 0) + 1
        for record in references:
            value = fact_value(record)
            name = str(value.get("name")).casefold()
            candidates = versions.get(name, [])
            if counts[name] != 1 or value.get("version") is not None or len(candidates) != 1:
                continue
            central_value = fact_value(candidates[0])
            version = central_value.get("version")
            if (
                not isinstance(version, str)
                or not version
                or central_value.get("operation") != "Include"
            ):
                continue
            if len(links) == MAX_MANIFEST_ITEMS // 2:
                return tuple(links), (".NET central declaration links were truncated",)
            links.append(
                replace(
                    record,
                    kind="dotnet.central_version",
                    value={
                        "identity": f"{project}:{name}",
                        "fact": {
                            "name": value["name"],
                            "version": version,
                            "project_path": project,
                            "central_source_path": central,
                            "version_state": "central-declared",
                            "effective_version": False,
                        },
                    },
                    provenance="static central declaration link",
                )
            )
    return tuple(links), ()
