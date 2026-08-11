"""Derive bounded framework and template facts through static built-in plugins."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from ocr_toolkit.evidence.coverage import CoverageObservation
from ocr_toolkit.evidence.model import CoverageState, EvidenceRecord, EvidenceValue, RefRole
from ocr_toolkit.evidence.repository import RepositoryObject

MAX_PLUGIN_FACTS = 512
MAX_CONFIGURATION_PATHS = 128
_FRAMEWORK_SCHEMA = "repository.framework-evidence/v1"
_TEMPLATE_SCHEMA = "repository.template-evidence/v1"


@dataclass(frozen=True, slots=True)
class PluginFact:
    """Describe one validated plugin fact before ref provenance is attached."""

    kind: str
    component: str
    identity: str
    source_path: str
    value: Mapping[str, EvidenceValue]


@dataclass(frozen=True, slots=True)
class PluginCoverage:
    """Describe one plugin-owned scoped coverage observation."""

    component: str
    domain: str
    scope: str
    observation: CoverageObservation


@dataclass(frozen=True, slots=True)
class FrameworkPluginContext:
    """Expose immutable normalized facts and bounded tree metadata to one plugin."""

    records: tuple[EvidenceRecord, ...]
    entries: tuple[RepositoryObject, ...]
    omitted_paths: tuple[str, ...]
    ref: RefRole
    commit_sha: str


@dataclass(frozen=True, slots=True)
class FrameworkPluginResult:
    """Return bounded plugin facts, coverage, and safe machine notices."""

    facts: tuple[PluginFact, ...]
    coverage: tuple[PluginCoverage, ...]
    notices: tuple[str, ...] = ()


class FrameworkPlugin(Protocol):
    """Define the package-owned static framework plugin boundary."""

    plugin_id: str

    def collect(self, context: FrameworkPluginContext) -> FrameworkPluginResult:
        """Derive facts without I/O, execution, network access, or mutation."""


def component_root(path: str) -> str:
    """Return the canonical manifest directory component or repository root."""

    parent = PurePosixPath(path).parent.as_posix()
    return "repository" if parent == "." else parent


def _fact_value(record: EvidenceRecord) -> Mapping[str, EvidenceValue] | None:
    """Return one normalized manifest fact mapping from a stored evidence record."""

    if not isinstance(record.value, Mapping):
        return None
    fact = record.value.get("fact")
    return fact if isinstance(fact, Mapping) else None


def _package(record: EvidenceRecord) -> str | None:
    """Return the normalized package name carried by one dependency record."""

    fact = _fact_value(record)
    name = fact.get("name") if fact is not None else None
    return name.casefold() if isinstance(name, str) else None


def _version(record: EvidenceRecord) -> str | None:
    """Return the resolved version carried by one lock record."""

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


def _is_direct(record: EvidenceRecord, ecosystem: str) -> bool:
    """Return whether a declaration directly establishes plugin applicability."""

    scope = _scope(record)
    if ecosystem == "go":
        return scope == "direct"
    return scope not in {"indirect", "exclude", "replace", "provide", "conflict"}


def _configuration_paths(
    entries: Iterable[RepositoryObject], patterns: tuple[re.Pattern[str], ...]
) -> tuple[str, ...]:
    """Select bounded regular configuration paths without reading their content."""

    selected = sorted(
        entry.path
        for entry in entries
        if entry.object_type == "blob"
        and not entry.is_symlink
        and not entry.is_submodule
        and any(pattern.search(entry.path) for pattern in patterns)
    )
    return tuple(selected[:MAX_CONFIGURATION_PATHS])


def _related(
    name: str,
    role: str,
    declarations: tuple[EvidenceRecord, ...],
    resolutions: tuple[EvidenceRecord, ...],
) -> dict[str, EvidenceValue]:
    """Build one deterministic related-stack value."""

    value: dict[str, EvidenceValue] = {
        "name": name,
        "role": role,
    }
    value["declared_values"] = sorted({_declared_value(record) for record in declarations})
    value["resolved_versions"] = sorted(
        {version for record in resolutions if (version := _version(record)) is not None}
    )
    value["source_paths"] = sorted({record.source_path for record in (*declarations, *resolutions)})
    return value


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
    related: tuple[dict[str, EvidenceValue], ...] = (),
    version_state: str | None = None,
) -> PluginFact:
    """Build one closed framework fact with version data outside stable identity."""

    versions = sorted(
        {version for record in resolutions if (version := _version(record)) is not None}
    )
    state = version_state or (
        "declared-only" if not versions else "resolved" if len(versions) == 1 else "conflicting"
    )
    declaration_values: list[dict[str, EvidenceValue]] = []
    for record in declarations:
        package = _package(record)
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
    resolution_values: list[dict[str, EvidenceValue]] = []
    for record in resolutions:
        package = _package(record)
        version = _version(record)
        if package is None or version is None:
            continue
        resolution_values.append(
            {
                "package": package,
                "version": version,
                "source": _scope(record),
                "source_path": record.source_path,
            }
        )
    source_path = min(record.source_path for record in declarations)
    value: dict[str, EvidenceValue] = {
        "schema_version": _FRAMEWORK_SCHEMA,
        "plugin": plugin,
        "framework": framework,
        "ecosystem": ecosystem,
        "category": category,
        "version_state": state,
    }
    value["declarations"] = sorted(
        declaration_values,
        key=lambda item: (
            str(item.get("package")),
            str(item.get("scope")),
            str(item.get("source_path")),
        ),
    )
    value["resolutions"] = sorted(
        resolution_values,
        key=lambda item: (
            str(item.get("package")),
            str(item.get("version")),
            str(item.get("source_path")),
        ),
    )
    value["configuration_paths"] = list(configuration_paths)
    value["related"] = list(related)
    return PluginFact(
        "framework.detected",
        component,
        f"{plugin}:{framework}",
        source_path,
        value,
    )


def _coverage(
    *,
    component: str,
    plugin: str,
    framework: str | None,
    state: CoverageState,
    reason: str,
    positive: bool = False,
) -> PluginCoverage:
    """Build one plugin coverage observation using closed scopes."""

    domain = "framework.declaration" if framework is None else "framework.resolution"
    scope = plugin if framework is None else f"{plugin}:{framework}"
    return PluginCoverage(component, domain, scope, CoverageObservation(state, reason, positive))


def _components(records: tuple[EvidenceRecord, ...], ecosystem: str) -> tuple[str, ...]:
    """Return supported manifest components for one ecosystem."""

    return tuple(
        sorted(
            {
                component_root(record.source_path)
                for record in records
                if record.kind == "repository.manifest" and record.component == ecosystem
            }
        )
    )


def _component_records(
    records: tuple[EvidenceRecord, ...], component: str, ecosystem: str
) -> tuple[EvidenceRecord, ...]:
    """Return dependency records rooted in one canonical component."""

    return tuple(
        record
        for record in records
        if record.component == ecosystem
        and record.kind in {"dependency.declared", "dependency.locked"}
        and component_root(record.source_path) == component
    )


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
        """Derive direct framework declarations and matching lock evidence."""

        facts: list[PluginFact] = []
        coverage: list[PluginCoverage] = []
        config_paths = _configuration_paths(context.entries, self.configuration_patterns)
        for component in _components(context.records, self.ecosystem):
            records = _component_records(context.records, component, self.ecosystem)
            declarations = tuple(
                record
                for record in records
                if record.kind == "dependency.declared" and _is_direct(record, self.ecosystem)
            )
            locked = tuple(record for record in records if record.kind == "dependency.locked")
            replacements = tuple(
                record
                for record in records
                if self.ecosystem == "go"
                and record.kind == "dependency.declared"
                and _scope(record) == "replace"
            )
            component_positive = False
            related_values: list[dict[str, EvidenceValue]] = []
            for item in self.related:
                item_declarations = tuple(
                    record for record in declarations if _package(record) in item.packages
                )
                if not item_declarations:
                    continue
                item_locked = tuple(
                    record for record in locked if _package(record) in item.packages
                )
                related_values.append(
                    _related(item.name, item.role, item_declarations, item_locked)
                )
            for spec in self.frameworks:
                direct = tuple(
                    record for record in declarations if _package(record) in spec.packages
                )
                if not direct:
                    continue
                component_positive = True
                resolved = tuple(record for record in locked if _package(record) in spec.packages)
                replacement = next(
                    (record for record in replacements if _package(record) in spec.packages),
                    None,
                )
                replacement_fact = _fact_value(replacement) if replacement is not None else None
                explicit_state: str | None = None
                if replacement_fact is not None:
                    replacement_type = replacement_fact.get("replacement_type")
                    replacement_version = replacement_fact.get("replacement_version")
                    if replacement_type == "local":
                        explicit_state = "local-override"
                        resolved = ()
                    elif isinstance(replacement_version, str) and replacement_version:
                        resolved = (*resolved, replacement)
                component_config = tuple(
                    path
                    for path in config_paths
                    if component == "repository"
                    or path == component
                    or path.startswith(component + "/")
                )
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
                        related=tuple(related_values),
                        version_state=explicit_state,
                    )
                )
                coverage.append(
                    _coverage(
                        component=component,
                        plugin=self.plugin_id,
                        framework=spec.framework,
                        state=CoverageState.COMPLETE if resolved else CoverageState.PARTIAL,
                        reason="lock-version-present" if resolved else "lock-version-missing",
                        positive=True,
                    )
                )
            coverage.append(
                _coverage(
                    component=component,
                    plugin=self.plugin_id,
                    framework=None,
                    state=CoverageState.COMPLETE,
                    reason="direct-manifest-complete",
                    positive=component_positive,
                )
            )
        return FrameworkPluginResult(tuple(facts[:MAX_PLUGIN_FACTS]), tuple(coverage))


JINJA2_PLUGIN = PackageFrameworkPlugin(
    "jinja2",
    "python",
    (PackageFrameworkSpec("jinja2", ("jinja2",), "template-engine"),),
    configuration_patterns=(
        re.compile(r"(^|/)(pyproject\.toml|requirements[^/]*\.(txt|in)|.*\.lock)$", re.I),
    ),
)
GO_WEB_PLUGIN = PackageFrameworkPlugin(
    "go-web",
    "go",
    (
        PackageFrameworkSpec("echo", ("github.com/labstack/echo/v4",)),
        PackageFrameworkSpec("fiber", ("github.com/gofiber/fiber/v2",)),
    ),
    related=(RelatedSpec("grpc", "rpc-stack", ("google.golang.org/grpc",)),),
    configuration_patterns=(re.compile(r"(^|/)go\.(mod|sum)$", re.I),),
)
SYMFONY_PLUGIN = PackageFrameworkPlugin(
    "symfony-php",
    "php",
    (
        PackageFrameworkSpec("symfony", ("symfony/framework-bundle", "symfony/symfony")),
        PackageFrameworkSpec("twig", ("twig/twig", "symfony/twig-bundle"), "template-engine"),
    ),
    configuration_patterns=(
        re.compile(r"(^|/)composer\.(json|lock)$", re.I),
        re.compile(r"(^|/)config/(bundles\.php|packages/|routes(?:\.|/|$))", re.I),
        re.compile(r"\.twig$", re.I),
    ),
)
REACT_PLUGIN = PackageFrameworkPlugin(
    "react-typescript",
    "javascript",
    (
        PackageFrameworkSpec("react", ("react",)),
        PackageFrameworkSpec("next", ("next",)),
    ),
    related=(
        RelatedSpec("typescript", "language-toolchain", ("typescript",)),
        RelatedSpec("vite", "build-tool", ("vite",)),
    ),
    configuration_patterns=(
        re.compile(r"(^|/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$", re.I),
        re.compile(r"(^|/)tsconfig[^/]*\.json$", re.I),
        re.compile(r"(^|/)(vite|next)\.config\.[^.]+$", re.I),
    ),
)

BUILTIN_FRAMEWORK_PLUGINS: tuple[FrameworkPlugin, ...] = (
    JINJA2_PLUGIN,
    GO_WEB_PLUGIN,
    SYMFONY_PLUGIN,
    REACT_PLUGIN,
)


def collect_framework_plugins(
    context: FrameworkPluginContext,
) -> tuple[tuple[PluginFact, ...], tuple[PluginCoverage, ...], tuple[str, ...]]:
    """Run every static plugin independently and return deterministic bounded output."""

    facts: list[PluginFact] = []
    coverage: list[PluginCoverage] = []
    notices: list[str] = []
    for plugin in BUILTIN_FRAMEWORK_PLUGINS:
        try:
            result = plugin.collect(context)
        except (TypeError, ValueError, RecursionError):
            notices.append(f"framework plugin unavailable: {plugin.plugin_id}")
            continue
        facts.extend(result.facts[:MAX_PLUGIN_FACTS])
        coverage.extend(result.coverage)
        notices.extend(result.notices)
        if len(result.facts) > MAX_PLUGIN_FACTS:
            notices.append(f"framework plugin fact limit reached: {plugin.plugin_id}")
    return (
        tuple(sorted(facts, key=lambda item: (item.kind, item.component, item.identity))),
        tuple(sorted(coverage, key=lambda item: (item.component, item.domain, item.scope))),
        tuple(dict.fromkeys(notices)),
    )


def framework_schema_versions() -> tuple[str, str]:
    """Expose the closed plugin schemas for storage validation."""

    return _FRAMEWORK_SCHEMA, _TEMPLATE_SCHEMA


def _rendered_extension(path: str) -> str | None:
    """Return the target extension before a Jinja marker when one is present."""

    suffixes = PurePosixPath(path).suffixes
    if len(suffixes) >= 2 and suffixes[-1].casefold() in {".j2", ".jinja", ".jinja2"}:
        return suffixes[-2].casefold()
    return None


def _ansible_template_component(path: str) -> str | None:
    """Return a role-root component for conventional nested Ansible templates."""

    parts = PurePosixPath(path).parts
    folded = tuple(part.casefold() for part in parts)
    for index, part in enumerate(folded):
        if part == "roles" and index + 3 <= len(parts) and folded[index + 2] == "templates":
            return "/".join(parts[: index + 2])
    return None


def collect_template_files(
    entries: tuple[RepositoryObject, ...],
) -> tuple[tuple[PluginFact, ...], tuple[PluginCoverage, ...]]:
    """Inventory Jinja/Twig regular blobs without reading or persisting template content."""

    facts: list[PluginFact] = []
    coverage_components: set[tuple[str, str]] = set()
    for entry in entries:
        if entry.object_type != "blob" or entry.is_symlink or entry.is_submodule:
            continue
        folded = entry.path.casefold()
        role_component = _ansible_template_component(entry.path)
        if folded.endswith((".j2", ".jinja", ".jinja2")):
            plugin = engine = "jinja2"
            detection = "jinja-extension"
            component = role_component or component_root(entry.path)
        elif role_component is not None:
            plugin = engine = "jinja2"
            detection = "ansible-role-template"
            component = role_component
        elif folded.endswith(".twig"):
            plugin = "symfony-php"
            engine = "twig"
            detection = "twig-extension"
            component = component_root(entry.path)
        else:
            continue
        facts.append(
            PluginFact(
                "template.file",
                component,
                entry.path,
                entry.path,
                {
                    "schema_version": _TEMPLATE_SCHEMA,
                    "plugin": plugin,
                    "engine": engine,
                    "detection": detection,
                    "rendered_extension": _rendered_extension(entry.path),
                    "object_sha": entry.object_sha,
                },
            )
        )
        coverage_components.add((component, plugin))
        if len(facts) >= MAX_PLUGIN_FACTS:
            break
    coverage = tuple(
        PluginCoverage(
            component,
            "template.inventory",
            plugin,
            CoverageObservation(CoverageState.COMPLETE, "bounded-tree-complete", positive=True),
        )
        for component, plugin in sorted(coverage_components)
    )
    return tuple(facts), coverage
