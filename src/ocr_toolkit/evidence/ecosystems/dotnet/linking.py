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
    """Identify project manifests without granting native review or build authority."""
    return PurePosixPath(path).suffix.casefold() in PROJECT_SUFFIXES


def nearest_file(
    path: str, basename: str, paths: Mapping[str, frozenset[str]]
) -> tuple[str | None, bool]:
    """Stop at the nearest discovery candidate, withholding case-ambiguous associations."""

    for parent in PurePosixPath(path).parents:
        candidate = str(parent / basename)
        aliases = paths.get(candidate.casefold(), frozenset())
        if aliases:
            return (candidate, False) if aliases == frozenset({candidate}) else (None, True)
    return None, False


def central_links(
    records: tuple[EvidenceRecord, ...],
    paths: frozenset[str],
    source_states: Mapping[str, str],
) -> tuple[tuple[EvidenceRecord, ...], tuple[str, ...]]:
    """Keep links project-scoped; do not claim an effective MSBuild version."""

    grouped: dict[str, list[EvidenceRecord]] = {}
    folded_paths: dict[str, set[str]] = {}
    for path in paths:
        folded_paths.setdefault(path.casefold(), set()).add(path)
    discovery = {key: frozenset(values) for key, values in folded_paths.items()}
    for record in records:
        if record.component == "dotnet":
            grouped.setdefault(record.source_path, []).append(record)

    def safe(path: str) -> bool:
        """Require a complete source with no unsupported evaluation before deriving a link."""
        sources = [record for record in grouped.get(path, ()) if record.kind == "dotnet.source"]
        return (
            source_states.get(path) == "complete"
            and len(sources) == 1
            and fact_value(sources[0]).get("interpretation") == "declared"
        )

    def settings(path: str) -> list[EvidenceValue]:
        """Read explicit central-management settings separately for each source path."""
        return [
            fact_value(record).get("value")
            for record in grouped.get(path, ())
            if record.kind == "dotnet.property"
            and str(fact_value(record).get("name")).casefold() == "managepackageversionscentrally"
        ]

    links = []
    for project in sorted(path for path in grouped if project_path(path)):
        central, ambiguous = nearest_file(project, "Directory.Packages.props", discovery)
        if ambiguous or central is None or not safe(project) or not safe(central):
            continue
        build_choices = [
            nearest_file(project, name, discovery)
            for name in ("Directory.Build.props", "Directory.Build.targets")
        ]
        if any(ambiguous for _, ambiguous in build_choices):
            continue
        build_files = [path for path, _ in build_choices]
        if any(path is not None and (not safe(path) or settings(path)) for path in build_files):
            continue
        if [str(value).casefold() for value in settings(central)] != ["true"]:
            continue
        if settings(project) and [str(value).casefold() for value in settings(project)] != ["true"]:
            continue
        versions: dict[str, list[EvidenceRecord]] = {}
        competing: set[str] = set()
        for source in (central, project, *build_files):
            if source is None:
                continue
            for record in grouped.get(source, ()):
                value = fact_value(record)
                if record.kind == "dotnet.package_version":
                    name = str(value.get("name")).casefold()
                    if source == central:
                        versions.setdefault(name, []).append(record)
                    else:
                        competing.add(name)
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
            if (
                name in competing
                or counts[name] != 1
                or value.get("version") is not None
                or len(candidates) != 1
            ):
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
