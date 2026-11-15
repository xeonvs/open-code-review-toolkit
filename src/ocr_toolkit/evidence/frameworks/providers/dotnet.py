"""Detect ASP.NET Core declarations without inventing a runtime from its TFM."""

from __future__ import annotations

from dataclasses import dataclass

from ocr_toolkit.evidence.ecosystems.dotnet.linking import fact_value, project_path
from ocr_toolkit.evidence.frameworks.contracts import (
    MAX_PLUGIN_FACTS,
    FrameworkPluginContext,
    FrameworkPluginResult,
    PluginFact,
)
from ocr_toolkit.evidence.frameworks.detection import coverage_observation
from ocr_toolkit.evidence.frameworks.schema import FRAMEWORK_SCHEMA
from ocr_toolkit.evidence.model import CoverageState, EvidenceValue


@dataclass(frozen=True, slots=True)
class AspNetCorePlugin:
    plugin_id: str = "aspnet-core"

    def collect(self, context: FrameworkPluginContext) -> FrameworkPluginResult:
        """Use project filename components so colocated projects cannot mix."""

        projects = sorted(
            {
                item.path
                for item in context.source_statuses
                if item.ecosystem == "dotnet" and project_path(item.path)
            }
        )
        facts: list[PluginFact] = []
        coverage = []
        notices = []
        grouped = {}
        source_states = {item.path: item.state for item in context.source_statuses}
        for record in context.records:
            if record.component == "dotnet":
                grouped.setdefault(record.source_path, []).append(record)
        if len(projects) > 511:
            notices.append("ASP.NET Core project coverage was truncated")
            coverage.append(
                coverage_observation(
                    component=".",
                    plugin=self.plugin_id,
                    framework=None,
                    state=CoverageState.PARTIAL,
                    reason="project-coverage-limit",
                    positive=True,
                )
            )
            projects = projects[:511]
        for project in projects:
            if len(project) > 256:
                notices.append("ASP.NET Core project component exceeded its path limit")
                continue
            records = grouped.get(project, [])
            declarations: list[EvidenceValue] = []
            partial = source_states.get(project) != "complete"
            for record in records:
                value = fact_value(record)
                name = value.get("name")
                if not isinstance(name, str):
                    continue
                signal = (
                    record.kind == "dotnet.sdk"
                    and name.split("/", 1)[0].casefold() == "microsoft.net.sdk.web"
                ) or (
                    record.kind == "dependency.declared"
                    and name.casefold() in {"microsoft.aspnetcore.app", "microsoft.aspnetcore.all"}
                    and value.get("operation") == "Include"
                )
                if signal:
                    declared = str(value.get("version") or "unspecified")
                    if (
                        len(declarations) == 128
                        or len(name) > 512
                        or any(ord(c) < 32 for c in name)
                        or any(ord(c) < 32 for c in declared)
                    ):
                        partial = True
                        notices.append("ASP.NET Core declarations were truncated")
                        continue
                    declarations.append(
                        {
                            "package": name,
                            "scope": "web-sdk"
                            if record.kind == "dotnet.sdk"
                            else str(value.get("scope")),
                            "declared_value": declared,
                            "source_path": project,
                        }
                    )
            positive = bool(declarations)
            limited = positive and len(facts) >= MAX_PLUGIN_FACTS
            if limited:
                partial = True
                notices.append("ASP.NET Core facts were truncated")
            if positive and not limited:
                # A Web SDK or framework reference is a signal, not a NuGet lock
                # identity or an effective runtime version. Keep resolutions empty.
                facts.append(
                    PluginFact(
                        "framework.detected",
                        project,
                        "aspnet-core:aspnet-core",
                        project,
                        {
                            "schema_version": FRAMEWORK_SCHEMA,
                            "plugin": self.plugin_id,
                            "framework": "aspnet-core",
                            "ecosystem": "dotnet",
                            "category": "framework",
                            "declarations": declarations,
                            "resolutions": [],
                            "version_state": "declared-only",
                            "configuration_state": "complete",
                            "configuration_paths": [project],
                            "related": [],
                            "replacement": None,
                        },
                    )
                )
            for framework in (None, "aspnet-core"):
                state = CoverageState.PARTIAL if partial else CoverageState.COMPLETE
                reason = "static-declarations-partial" if partial else "static-declarations-read"
                if framework is not None:
                    state = (
                        CoverageState.RUNTIME_DEPENDENT if positive else CoverageState.UNAVAILABLE
                    )
                    reason = (
                        "runtime-version-not-evaluated" if positive else "no-direct-declaration"
                    )
                coverage.append(
                    coverage_observation(
                        component=project,
                        plugin=self.plugin_id,
                        framework=framework,
                        state=state,
                        reason=reason,
                        positive=positive,
                    )
                )
        return FrameworkPluginResult(tuple(facts), tuple(coverage), tuple(dict.fromkeys(notices)))


ASPNET_CORE_PLUGIN = AspNetCorePlugin()
