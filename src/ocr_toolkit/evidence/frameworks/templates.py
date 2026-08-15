"""Bounded Jinja and Twig template inventory over immutable tree metadata."""

from __future__ import annotations

from pathlib import PurePosixPath

from ocr_toolkit.evidence.coverage import CoverageObservation
from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_PLUGIN_FACTS,
    FrameworkPluginContext,
    PluginCoverage,
    PluginFact,
)
from ocr_toolkit.evidence.frameworks.detection import (
    component_root,
    is_direct_declaration,
    owning_component,
    package_name,
    plugin_components,
)
from ocr_toolkit.evidence.frameworks.schema import TEMPLATE_SCHEMA
from ocr_toolkit.evidence.model import CoverageState, EvidenceRecord


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


def _template_description(
    path: str, context: FrameworkPluginContext
) -> tuple[str, str, str, str] | None:
    """Return plugin, engine, detection, and nearest component for one template path."""

    folded = path.casefold()
    role_component = _ansible_template_component(path)
    if folded.endswith((".j2", ".jinja", ".jinja2")):
        roots = plugin_components(context, "python")
        component = role_component or owning_component(path, roots) or component_root(path)
        return "jinja2", "jinja2", "jinja-extension", component
    if role_component is not None:
        return "jinja2", "jinja2", "ansible-role-template", role_component
    if folded.endswith(".twig"):
        roots = plugin_components(context, "php")
        component = owning_component(path, roots) or component_root(path)
        return "symfony-php", "twig", "twig-extension", component
    return None


def _applicable_template_components(
    records: tuple[EvidenceRecord, ...],
) -> tuple[tuple[str, str], ...]:
    """Return components with direct Jinja or Twig template-engine declarations."""

    applicable: set[tuple[str, str]] = set()
    for record in records:
        if record.kind != "dependency.declared":
            continue
        package = package_name(record)
        if package == "jinja2" and is_direct_declaration(record, "python"):
            applicable.add((component_root(record.source_path), "jinja2"))
        elif package in {"twig/twig", "symfony/twig-bundle"} and is_direct_declaration(
            record, "php"
        ):
            applicable.add((component_root(record.source_path), "symfony-php"))
    return tuple(sorted(applicable))


def collect_template_files(
    context: FrameworkPluginContext,
) -> tuple[tuple[PluginFact, ...], tuple[PluginCoverage, ...], tuple[str, ...]]:
    """Inventory Jinja/Twig blobs without reading or persisting template content."""

    facts: list[PluginFact] = []
    observations: dict[tuple[str, str], list[CoverageObservation]] = {
        key: [CoverageObservation(CoverageState.COMPLETE, "bounded-tree-complete")]
        for key in _applicable_template_components(context.records)
    }
    limited_components: set[tuple[str, str]] = set()
    truncated = False
    changed_paths = frozenset(context.changed_paths)
    for entry in sorted(
        context.entries, key=lambda item: (item.path not in changed_paths, item.path)
    ):
        description = _template_description(entry.path, context)
        if description is None:
            continue
        plugin, engine, detection, component = description
        key = (component, plugin)
        if entry.object_type != "blob" or entry.is_symlink or entry.is_submodule:
            observations.setdefault(key, []).append(
                CoverageObservation(CoverageState.PARTIAL, "unsafe-template-source", positive=True)
            )
            continue
        if len(facts) >= MAX_PLUGIN_FACTS:
            truncated = True
            if key not in limited_components:
                limited_components.add(key)
                observations.setdefault(key, []).append(
                    CoverageObservation(
                        CoverageState.PARTIAL,
                        "template-fact-limit",
                        positive=True,
                    )
                )
            continue
        facts.append(
            PluginFact(
                "template.file",
                component,
                entry.path,
                entry.path,
                {
                    "schema_version": TEMPLATE_SCHEMA,
                    "plugin": plugin,
                    "engine": engine,
                    "detection": detection,
                    "rendered_extension": _rendered_extension(entry.path),
                    "object_sha": entry.object_sha,
                },
            )
        )
        observations.setdefault(key, []).append(
            CoverageObservation(CoverageState.COMPLETE, "bounded-tree-complete", positive=True)
        )
    coverage = tuple(
        PluginCoverage(component, "template.inventory", plugin, observation)
        for (component, plugin), values in sorted(observations.items())
        for observation in values
    )
    notices = ("template plugin fact limit reached",) if truncated else ()
    return tuple(facts), coverage, notices
