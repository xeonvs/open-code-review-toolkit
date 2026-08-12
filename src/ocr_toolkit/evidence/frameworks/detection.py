"""Generic bounded package-backed framework detection without repository I/O."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ocr_toolkit.evidence.coverage import CoverageObservation
from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_CONFIGURATION_PATHS,
    MAX_PLUGIN_FACTS,
    FrameworkPluginContext,
    FrameworkPluginResult,
    PluginCoverage,
    PluginFact,
)
from ocr_toolkit.evidence.frameworks.schema import FRAMEWORK_SCHEMA
from ocr_toolkit.evidence.model import CoverageState, EvidenceRecord, EvidenceValue

if TYPE_CHECKING:
    from ocr_toolkit.evidence.repository import RepositoryObject


def component_root(path: str) -> str:
    """Return the canonical manifest directory component or repository root."""

    parent = PurePosixPath(path).parent.as_posix()
    return "repository" if parent == "." else parent


def _fact_value(record: EvidenceRecord | None) -> Mapping[str, EvidenceValue] | None:
    """Return one normalized manifest fact mapping from a stored evidence record."""

    if record is None or not isinstance(record.value, Mapping):
        return None
    fact = record.value.get("fact")
    return fact if isinstance(fact, Mapping) else None


def package_name(record: EvidenceRecord) -> str | None:
    """Return the normalized package name carried by one dependency record."""

    fact = _fact_value(record)
    name = fact.get("name") if fact is not None else None
    return name.casefold() if isinstance(name, str) else None


def _version(record: EvidenceRecord) -> str | None:
    """Return the exact version carried by one declaration or lock record."""

    fact = _fact_value(record)
    value = fact.get("version") if fact is not None else None
    return value if isinstance(value, str) and value else None


def _declared_value(record: EvidenceRecord) -> str:
    """Return the exact bounded declaration value without resolving it."""

    fact = _fact_value(record)
    if fact is None:
        return "unspecified"
    for key in ("requirement", "constraint", "version"):
        value = fact.get(key)
        if isinstance(value, str) and value:
            return value
    return "unspecified"


def _scope(record: EvidenceRecord) -> str:
    """Return one exact declaration or resolution scope label."""

    fact = _fact_value(record)
    value = fact.get("scope") if fact is not None else None
    return value if isinstance(value, str) and value else "unknown"


def is_direct_declaration(record: EvidenceRecord, ecosystem: str) -> bool:
    """Return whether a declaration directly establishes plugin applicability."""

    scope = _scope(record)
    if ecosystem == "go":
        return scope == "direct"
    return scope not in {"indirect", "exclude", "replace", "provide", "conflict"}


def _path_is_within(path: str, component: str) -> bool:
    """Return whether one repository path is inside a canonical component."""

    return component == "repository" or path == component or path.startswith(component + "/")


def owning_component(path: str, components: tuple[str, ...]) -> str | None:
    """Return the nearest manifest-root component that owns one repository path."""

    matches = tuple(component for component in components if _path_is_within(path, component))
    return (
        max(matches, key=lambda item: 0 if item == "repository" else item.count("/") + 1)
        if matches
        else None
    )


def _configuration_paths(
    entries: Iterable[RepositoryObject],
    patterns: tuple[re.Pattern[str], ...],
    *,
    component: str,
    components: tuple[str, ...],
) -> tuple[tuple[str, ...], bool]:
    """Select component-owned regular configuration paths and report truncation."""

    selected: list[str] = []
    truncated = False
    for entry in sorted(entries, key=lambda item: item.path):
        if (
            entry.object_type != "blob"
            or entry.is_symlink
            or entry.is_submodule
            or owning_component(entry.path, components) != component
            or not any(pattern.search(entry.path) for pattern in patterns)
        ):
            continue
        if len(selected) >= MAX_CONFIGURATION_PATHS:
            truncated = True
            continue
        selected.append(entry.path)
    return tuple(selected), truncated


def _related(
    name: str,
    role: str,
    declarations: tuple[EvidenceRecord, ...],
    resolutions: tuple[EvidenceRecord, ...],
    *,
    declarations_resolve: bool = False,
) -> dict[str, EvidenceValue]:
    """Build one deterministic related-stack value."""

    resolved_records = declarations if declarations_resolve else resolutions
    value: dict[str, EvidenceValue] = {"name": name, "role": role}
    value["declared_values"] = sorted({_declared_value(record) for record in declarations})
    value["resolved_versions"] = sorted(
        {version for record in resolved_records if (version := _version(record)) is not None}
    )
    value["source_paths"] = sorted({record.source_path for record in (*declarations, *resolutions)})
    return value


def _replacement_applies(
    replacement: EvidenceRecord, declarations: tuple[EvidenceRecord, ...]
) -> bool:
    """Return whether one Go replacement applies to a direct required version."""

    package = package_name(replacement)
    source_version = _version(replacement)
    if package is None:
        return False
    if source_version is None:
        return any(package_name(record) == package for record in declarations)
    return any(
        package_name(record) == package and _version(record) == source_version
        for record in declarations
    )


def _replacement_value(record: EvidenceRecord | None) -> dict[str, EvidenceValue] | None:
    """Return one closed Go replacement object without reading replacement content."""

    fact = _fact_value(record)
    if fact is None:
        return None
    target = fact.get("replacement")
    replacement_type = fact.get("replacement_type")
    version = fact.get("replacement_version")
    if not isinstance(target, str) or replacement_type not in {"local", "module"}:
        return None
    return {
        "target": target,
        "type": replacement_type,
        "version": version if isinstance(version, str) and version else None,
    }


def _resolution_values(
    declarations: tuple[EvidenceRecord, ...],
    resolutions: tuple[EvidenceRecord, ...],
    *,
    replacement: EvidenceRecord | None,
    declarations_resolve: bool,
) -> list[dict[str, EvidenceValue]]:
    """Build deterministic effective resolution rows for one framework."""

    replacement_value = _replacement_value(replacement)
    if replacement_value is not None:
        version = replacement_value["version"]
        package = package_name(replacement) if replacement is not None else None
        if replacement_value["type"] == "module" and isinstance(version, str) and package:
            return [
                {
                    "package": package,
                    "version": version,
                    "source": "go.replace",
                    "source_path": replacement.source_path,
                }
            ]
        return []

    records = declarations if declarations_resolve else resolutions
    values = {
        (
            package,
            version,
            "go.mod" if declarations_resolve and record in declarations else _scope(record),
            record.source_path,
        )
        for record in records
        if (package := package_name(record)) is not None
        and (version := _version(record)) is not None
    }
    return [
        {"package": package, "version": version, "source": source, "source_path": path}
        for package, version, source, path in sorted(values)
    ]


def _framework_fact(
    *,
    plugin: str,
    framework: str,
    ecosystem: str,
    category: str,
    component: str,
    declarations: tuple[EvidenceRecord, ...],
    resolutions: tuple[EvidenceRecord, ...],
    configuration_paths: tuple[str, ...],
    configuration_state: str,
    related: tuple[dict[str, EvidenceValue], ...] = (),
    replacement: EvidenceRecord | None = None,
    declarations_resolve: bool = False,
) -> PluginFact:
    """Build one closed framework fact with mutable version data outside identity."""

    resolution_values = _resolution_values(
        declarations,
        resolutions,
        replacement=replacement,
        declarations_resolve=declarations_resolve,
    )
    versions = sorted({str(item["version"]) for item in resolution_values})
    replacement_value = _replacement_value(replacement)
    state = (
        "local-override"
        if replacement_value is not None and replacement_value["type"] == "local"
        else "declared-only"
        if not versions
        else "resolved"
        if len(versions) == 1
        else "conflicting"
    )
    declaration_values: list[dict[str, EvidenceValue]] = []
    for record in declarations:
        package = package_name(record)
        if package is None:
            continue
        declaration_values.append(
            {
                "package": package,
                "scope": _scope(record),
                "declared_value": _declared_value(record),
                "source_path": record.source_path,
            }
        )
    source_path = min(record.source_path for record in declarations)
    value: dict[str, EvidenceValue] = {
        "schema_version": FRAMEWORK_SCHEMA,
        "plugin": plugin,
        "framework": framework,
        "ecosystem": ecosystem,
        "category": category,
        "version_state": state,
        "configuration_state": configuration_state,
    }
    value["declarations"] = sorted(
        declaration_values,
        key=lambda item: (
            str(item.get("package")),
            str(item.get("scope")),
            str(item.get("source_path")),
        ),
    )
    value["resolutions"] = resolution_values
    value["configuration_paths"] = list(configuration_paths)
    value["related"] = list(related)
    value["replacement"] = replacement_value
    return PluginFact(
        "framework.detected",
        component,
        f"{plugin}:{framework}",
        source_path,
        value,
    )


def coverage_observation(
    *,
    component: str,
    plugin: str,
    framework: str | None,
    state: CoverageState,
    reason: str,
    positive: bool = False,
    domain: str | None = None,
) -> PluginCoverage:
    """Build one plugin coverage observation using closed scopes."""

    selected_domain = domain or (
        "framework.declaration" if framework is None else "framework.resolution"
    )
    scope = plugin if framework is None else f"{plugin}:{framework}"
    return PluginCoverage(
        component,
        selected_domain,
        scope,
        CoverageObservation(state, reason, positive),
    )


def plugin_components(context: FrameworkPluginContext, ecosystem: str) -> tuple[str, ...]:
    """Return components with parsed or recognized declaration sources."""

    parsed = {
        component_root(record.source_path)
        for record in context.records
        if record.kind == "repository.manifest" and record.component == ecosystem
    }
    recognized = {
        component_root(source.path)
        for source in context.source_statuses
        if source.ecosystem == ecosystem and "declaration" in source.roles
    }
    return tuple(sorted(parsed | recognized))


def _component_declarations(
    records: tuple[EvidenceRecord, ...], component: str, ecosystem: str
) -> tuple[EvidenceRecord, ...]:
    """Return dependency declarations rooted in one canonical component."""

    return tuple(
        record
        for record in records
        if record.component == ecosystem
        and record.kind == "dependency.declared"
        and component_root(record.source_path) == component
    )


def _component_resolutions(
    records: tuple[EvidenceRecord, ...], component: str, ecosystem: str
) -> tuple[EvidenceRecord, ...]:
    """Return resolution records rooted in one exact manifest component."""

    return tuple(
        record
        for record in records
        if record.component == ecosystem
        and record.kind == "dependency.locked"
        and component_root(record.source_path) == component
    )


def _source_observation(
    context: FrameworkPluginContext,
    *,
    component: str,
    ecosystem: str,
    role: str,
) -> CoverageObservation | None:
    """Return the strongest degradation from exact supported source statuses."""

    for state, reason in (
        ("unavailable", "parse-unavailable"),
        ("omitted", "bounded-source-omission"),
        ("partial", "source-item-limit"),
    ):
        matching = tuple(
            source
            for source in context.source_statuses
            if source.ecosystem == ecosystem
            and role in source.roles
            and component_root(source.path) == component
            and source.state == state
        )
        if matching:
            selected_reason = next(
                (source.reason for source in matching if source.reason is not None), reason
            )
            return CoverageObservation(
                CoverageState.PARTIAL,
                selected_reason,
                positive=state == "partial",
            )
    return None


@dataclass(frozen=True, slots=True)
class PackageFrameworkSpec:
    """Declare one directly detectable package-backed framework."""

    framework: str
    packages: tuple[str, ...]
    category: str = "framework"


@dataclass(frozen=True, slots=True)
class RelatedSpec:
    """Declare one directly detectable related package group."""

    name: str
    role: str
    packages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PackageFrameworkPlugin:
    """Implement a deterministic package-backed built-in framework plugin."""

    plugin_id: str
    ecosystem: str
    frameworks: tuple[PackageFrameworkSpec, ...]
    related: tuple[RelatedSpec, ...] = ()
    configuration_patterns: tuple[re.Pattern[str], ...] = ()

    def collect(self, context: FrameworkPluginContext) -> FrameworkPluginResult:
        """Derive direct declarations and nearest deterministic resolution evidence."""

        facts: list[PluginFact] = []
        coverage: list[PluginCoverage] = []
        notices: list[str] = []
        components = plugin_components(context, self.ecosystem)
        for component in components:
            component_declarations = _component_declarations(
                context.records, component, self.ecosystem
            )
            declarations = tuple(
                record
                for record in component_declarations
                if is_direct_declaration(record, self.ecosystem)
            )
            locked = _component_resolutions(context.records, component, self.ecosystem)
            replacements = tuple(
                record
                for record in component_declarations
                if self.ecosystem == "go" and _scope(record) == "replace"
            )
            component_config, config_truncated = _configuration_paths(
                context.entries,
                self.configuration_patterns,
                component=component,
                components=components,
            )
            related_values: list[dict[str, EvidenceValue]] = []
            for item in self.related:
                item_declarations = tuple(
                    record for record in declarations if package_name(record) in item.packages
                )
                if not item_declarations:
                    continue
                item_locked = tuple(
                    record for record in locked if package_name(record) in item.packages
                )
                related_values.append(
                    _related(
                        item.name,
                        item.role,
                        item_declarations,
                        item_locked,
                        declarations_resolve=self.ecosystem == "go",
                    )
                )

            component_positive = False
            component_fact_limit = False
            for spec in self.frameworks:
                direct = tuple(
                    record for record in declarations if package_name(record) in spec.packages
                )
                if not direct:
                    continue
                component_positive = True
                resolved = tuple(
                    record for record in locked if package_name(record) in spec.packages
                )
                applicable_replacements = tuple(
                    record
                    for record in replacements
                    if package_name(record) in spec.packages
                    and _replacement_applies(record, direct)
                )
                replacement = min(
                    applicable_replacements,
                    key=lambda record: (
                        _version(record) is None,
                        _version(record) or "",
                        str(_replacement_value(record)),
                        record.source_path,
                    ),
                    default=None,
                )
                replacement_value = _replacement_value(replacement)
                declarations_resolve = self.ecosystem == "go" and replacement is None
                if len(facts) >= MAX_PLUGIN_FACTS:
                    component_fact_limit = True
                    coverage.append(
                        coverage_observation(
                            component=component,
                            plugin=self.plugin_id,
                            framework=spec.framework,
                            state=CoverageState.PARTIAL,
                            reason="plugin-fact-limit",
                            positive=True,
                        )
                    )
                    continue
                facts.append(
                    _framework_fact(
                        plugin=self.plugin_id,
                        framework=spec.framework,
                        ecosystem=self.ecosystem,
                        category=spec.category,
                        component=component,
                        declarations=direct,
                        resolutions=resolved,
                        configuration_paths=component_config,
                        configuration_state="partial" if config_truncated else "complete",
                        related=tuple(related_values),
                        replacement=replacement,
                        declarations_resolve=declarations_resolve,
                    )
                )
                resolution_source = _source_observation(
                    context,
                    component=component,
                    ecosystem=self.ecosystem,
                    role="resolution",
                )
                if replacement_value is not None and replacement_value["type"] == "local":
                    state = CoverageState.PARTIAL
                    reason = "local-replacement"
                elif resolution_source is not None:
                    state = resolution_source.state
                    reason = resolution_source.reason
                elif (
                    resolved
                    or declarations_resolve
                    or (
                        replacement_value is not None
                        and isinstance(replacement_value["version"], str)
                    )
                ):
                    state = CoverageState.COMPLETE
                    reason = (
                        "direct-version-present" if declarations_resolve else "lock-version-present"
                    )
                else:
                    state = CoverageState.PARTIAL
                    reason = "lock-version-missing"
                coverage.append(
                    coverage_observation(
                        component=component,
                        plugin=self.plugin_id,
                        framework=spec.framework,
                        state=state,
                        reason=reason,
                        positive=True,
                    )
                )
                coverage.append(
                    coverage_observation(
                        component=component,
                        plugin=self.plugin_id,
                        framework=spec.framework,
                        domain="framework.configuration",
                        state=CoverageState.PARTIAL if config_truncated else CoverageState.COMPLETE,
                        reason=(
                            "configuration-path-limit"
                            if config_truncated
                            else "bounded-tree-complete"
                        ),
                        positive=bool(component_config),
                    )
                )

            declaration_source = _source_observation(
                context,
                component=component,
                ecosystem=self.ecosystem,
                role="declaration",
            )
            declaration_state = (
                CoverageState.PARTIAL
                if component_fact_limit
                else declaration_source.state
                if declaration_source is not None
                else CoverageState.COMPLETE
            )
            declaration_reason = (
                "plugin-fact-limit"
                if component_fact_limit
                else declaration_source.reason
                if declaration_source is not None
                else "direct-manifest-complete"
            )
            coverage.append(
                coverage_observation(
                    component=component,
                    plugin=self.plugin_id,
                    framework=None,
                    state=declaration_state,
                    reason=declaration_reason,
                    positive=(
                        component_positive
                        or (declaration_source is not None and declaration_source.positive)
                    ),
                )
            )
        if len(facts) >= MAX_PLUGIN_FACTS:
            notices.append(f"framework plugin fact limit reached: {self.plugin_id}")
        return FrameworkPluginResult(tuple(facts), tuple(coverage), tuple(notices))
