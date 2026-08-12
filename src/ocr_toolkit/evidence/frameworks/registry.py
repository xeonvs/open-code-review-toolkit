"""Static package-owned framework provider registry and failure isolation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath

from ocr_toolkit.evidence.coverage import compose_coverage
from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_PLUGIN_COVERAGE,
    MAX_PLUGIN_FACTS,
    MAX_PLUGIN_NOTICES,
    FrameworkPlugin,
    FrameworkPluginContext,
    FrameworkPluginResult,
    PluginCoverage,
    PluginFact,
)
from ocr_toolkit.evidence.frameworks.detection import coverage_observation
from ocr_toolkit.evidence.frameworks.providers import (
    GO_WEB_PLUGIN,
    JINJA2_PLUGIN,
    REACT_PLUGIN,
    SYMFONY_PLUGIN,
)
from ocr_toolkit.evidence.frameworks.schema import validate_plugin_record
from ocr_toolkit.evidence.model import CoverageState

BUILTIN_FRAMEWORK_PLUGINS: tuple[FrameworkPlugin, ...] = (
    JINJA2_PLUGIN,
    GO_WEB_PLUGIN,
    SYMFONY_PLUGIN,
    REACT_PLUGIN,
)


def _safe_component(value: object) -> bool:
    """Return whether one component is the root marker or a normalized bounded path."""

    return isinstance(value, str) and (
        value == "."
        or (
            0 < len(value) <= 256
            and not PurePosixPath(value).is_absolute()
            and all(part not in {"", ".", ".."} for part in value.split("/"))
            and not any(ord(character) < 32 for character in value)
        )
    )


def _safe_source_path(value: object) -> bool:
    """Return whether one plugin source is a normalized bounded repository path."""

    return (
        isinstance(value, str)
        and 0 < len(value) <= 4_096
        and not PurePosixPath(value).is_absolute()
        and all(part not in {"", ".", ".."} for part in value.split("/"))
        and not any(ord(character) < 32 for character in value)
    )


def _bounded_result(
    plugin: FrameworkPlugin, context: FrameworkPluginContext
) -> FrameworkPluginResult:
    """Validate one provider result before any output reaches shared registry state."""

    result = plugin.collect(context)
    if (
        not isinstance(result, FrameworkPluginResult)
        or not isinstance(result.facts, tuple)
        or len(result.facts) > MAX_PLUGIN_FACTS
        or not all(
            isinstance(fact, PluginFact) and isinstance(fact.value, Mapping)
            for fact in result.facts
        )
        or not isinstance(result.coverage, tuple)
        or len(result.coverage) > MAX_PLUGIN_COVERAGE
        or not all(isinstance(item, PluginCoverage) for item in result.coverage)
        or not isinstance(result.notices, tuple)
        or len(result.notices) > MAX_PLUGIN_NOTICES
        or not all(
            isinstance(notice, str) and 0 < len(notice) <= 1_024 for notice in result.notices
        )
    ):
        raise TypeError("framework plugin result is malformed")
    for fact in result.facts:
        if not _safe_component(fact.component) or not _safe_source_path(fact.source_path):
            raise TypeError("framework plugin fact metadata is malformed")
        validate_plugin_record(
            fact.kind,
            {"identity": fact.identity, "fact": fact.value},
        )
    for item in result.coverage:
        if not _safe_component(item.component):
            raise TypeError("framework plugin coverage metadata is malformed")
        # Apply the exact closed coverage contract before shared registry state
        # receives any observation from this provider.
        compose_coverage(
            component=item.component,
            domain=item.domain,
            scope=item.scope,
            observations=(item.observation,),
            ref=context.ref,
            commit_sha=context.commit_sha,
        )
    return result


def collect_framework_plugins(
    context: FrameworkPluginContext,
) -> tuple[tuple[PluginFact, ...], tuple[PluginCoverage, ...], tuple[str, ...]]:
    """Run every static plugin independently and return deterministic bounded output."""

    facts: list[PluginFact] = []
    coverage: list[PluginCoverage] = []
    notices: list[str] = []
    for plugin in BUILTIN_FRAMEWORK_PLUGINS:
        try:
            result = _bounded_result(plugin, context)
            ordered = sorted(result.facts, key=lambda item: (item.component, item.identity))
            remaining = max(0, MAX_PLUGIN_FACTS - len(facts))
            accepted = ordered[:remaining]
            omitted = ordered[remaining:]
            plugin_coverage = list(result.coverage)
            plugin_notices = list(result.notices)
            for fact in omitted:
                framework = fact.value.get("framework")
                if isinstance(framework, str):
                    plugin_coverage.extend(
                        (
                            coverage_observation(
                                component=fact.component,
                                plugin=plugin.plugin_id,
                                framework=framework,
                                state=CoverageState.PARTIAL,
                                reason="plugin-fact-limit",
                                positive=True,
                            ),
                            coverage_observation(
                                component=fact.component,
                                plugin=plugin.plugin_id,
                                framework=None,
                                state=CoverageState.PARTIAL,
                                reason="plugin-fact-limit",
                                positive=True,
                            ),
                        )
                    )
            if omitted:
                plugin_notices.append(f"framework plugin fact limit reached: {plugin.plugin_id}")
        # A package-owned provider is isolated so one defect cannot suppress siblings.
        except Exception:
            notices.append(f"framework plugin unavailable: {plugin.plugin_id}")
            continue
        # Commit one provider's output only after every validation and derived
        # truncation observation succeeded, so failure cannot leak partial state.
        facts.extend(accepted)
        coverage.extend(plugin_coverage)
        notices.extend(plugin_notices)
    return (
        tuple(sorted(facts, key=lambda item: (item.kind, item.component, item.identity))),
        tuple(sorted(coverage, key=lambda item: (item.component, item.domain, item.scope))),
        tuple(dict.fromkeys(notices)),
    )
