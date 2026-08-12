"""Static package-owned framework provider registry and failure isolation."""

from __future__ import annotations

from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_PLUGIN_FACTS,
    FrameworkPlugin,
    FrameworkPluginContext,
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
from ocr_toolkit.evidence.model import CoverageState

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
        # A package-owned provider is isolated so one defect cannot suppress siblings.
        except Exception:
            notices.append(f"framework plugin unavailable: {plugin.plugin_id}")
            continue
        ordered = sorted(result.facts, key=lambda item: (item.component, item.identity))
        remaining = max(0, MAX_PLUGIN_FACTS - len(facts))
        facts.extend(ordered[:remaining])
        coverage.extend(result.coverage)
        notices.extend(result.notices)
        omitted = ordered[remaining:]
        for fact in omitted:
            framework = fact.value.get("framework")
            if isinstance(framework, str):
                coverage.extend(
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
            notices.append(f"framework plugin fact limit reached: {plugin.plugin_id}")
    return (
        tuple(sorted(facts, key=lambda item: (item.kind, item.component, item.identity))),
        tuple(sorted(coverage, key=lambda item: (item.component, item.domain, item.scope))),
        tuple(dict.fromkeys(notices)),
    )
