"""Bounded static framework providers and template evidence inventory."""

from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_CONFIGURATION_PATHS,
    MAX_PLUGIN_FACTS,
    FrameworkPluginContext,
    FrameworkPluginResult,
    PluginCoverage,
    PluginFact,
    PluginSourceStatus,
)
from ocr_toolkit.evidence.frameworks.registry import (
    BUILTIN_FRAMEWORK_PLUGINS,
    collect_framework_plugins,
)
from ocr_toolkit.evidence.frameworks.schema import FRAMEWORK_SCHEMA, TEMPLATE_SCHEMA
from ocr_toolkit.evidence.frameworks.templates import collect_template_files


def framework_schema_versions() -> tuple[str, str]:
    """Expose the closed plugin schemas for storage validation."""

    return FRAMEWORK_SCHEMA, TEMPLATE_SCHEMA


__all__ = [
    "BUILTIN_FRAMEWORK_PLUGINS",
    "MAX_CONFIGURATION_PATHS",
    "MAX_PLUGIN_FACTS",
    "FrameworkPluginContext",
    "FrameworkPluginResult",
    "PluginCoverage",
    "PluginFact",
    "PluginSourceStatus",
    "collect_framework_plugins",
    "collect_template_files",
    "framework_schema_versions",
]
