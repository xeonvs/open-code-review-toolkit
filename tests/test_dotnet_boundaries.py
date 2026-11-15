"""Resource and unsupported-semantics boundaries for static .NET evidence."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit.evidence.ecosystems.dotnet import parse_msbuild
from ocr_toolkit.evidence.ecosystems.dotnet.linking import central_links
from ocr_toolkit.evidence.frameworks.contracts import FrameworkPluginContext, PluginSourceStatus
from ocr_toolkit.evidence.frameworks.providers.dotnet import ASPNET_CORE_PLUGIN
from ocr_toolkit.evidence.frameworks.registry import collect_framework_plugins
from ocr_toolkit.evidence.model import EvidenceRecord, RefRole


def context(projects: tuple[str, ...], declarations: int = 1) -> FrameworkPluginContext:
    """Build immutable provider inputs without replacing the provider under test."""
    records = tuple(
        EvidenceRecord(
            "dotnet.sdk",
            {
                "identity": str(index),
                "fact": {
                    "name": "Microsoft.NET.Sdk.Web",
                    "version": None,
                },
            },
            path,
            RefRole.HEAD,
            "a" * 40,
            component="dotnet",
        )
        for path in projects
        for index in range(declarations)
    )
    return FrameworkPluginContext(
        records,
        (),
        tuple(
            PluginSourceStatus(path, "dotnet", ("declaration",), "complete") for path in projects
        ),
        (),
        RefRole.HEAD,
        "a" * 40,
    )


def test_framework_provider_bounds_projects_and_keeps_partial_coverage() -> None:
    """Bound project/fact expansion and preserve explicit incomplete coverage."""
    selected = context(tuple(f"project{i:04}.csproj" for i in range(513)))
    result = ASPNET_CORE_PLUGIN.collect(selected)
    assert len(result.facts) == 256 and len(result.coverage) <= 1024
    assert any(
        item.component == "." and item.observation.state.value == "partial"
        for item in result.coverage
    )
    assert len(result.notices) == 2
    facts, coverage, notices = collect_framework_plugins(selected)
    assert len(facts) == 256 and coverage and notices
    assert not any("unavailable" in notice for notice in notices)


def test_framework_provider_bounds_declarations_and_long_paths() -> None:
    """Keep one oversized declaration or path from invalidating other project evidence."""
    selected = context(("web.csproj",), 129)
    result = ASPNET_CORE_PLUGIN.collect(selected)
    assert len(result.facts[0].value["declarations"]) == 128
    assert {item.domain: item.observation.state.value for item in result.coverage} == {
        "framework.declaration": "partial",
        "framework.resolution": "runtime-dependent",
    }
    too_long = context(("a" * 250 + "/web.csproj",))
    assert ASPNET_CORE_PLUGIN.collect(too_long).facts == ()
    assert ASPNET_CORE_PLUGIN.collect(too_long).notices
    bad_name = replace(
        selected.records[0],
        value={
            "identity": "x",
            "fact": {
                "name": "Microsoft.NET.Sdk.Web/" + "x" * 512,
            },
        },
    )
    result = ASPNET_CORE_PLUGIN.collect(replace(selected, records=(bad_name,)))
    assert not result.facts and result.notices
    assert {item.domain: item.observation.state.value for item in result.coverage} == {
        "framework.declaration": "partial",
        "framework.resolution": "unavailable",
    }


def test_unknown_attributes_missing_items_and_child_sdk_are_explicit() -> None:
    """Preserve unsupported XML semantics and conditional metadata as partial evidence."""
    result = parse_msbuild("""<Project InitialTargets="custom"><Sdk Name="Microsoft.NET.Sdk.Web" Version="9.0"/>
<PropertyGroup><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>
<PackageReference/><PackageReference Include="P"><Version Condition="flag">1.0</Version></PackageReference>
</ItemGroup></Project>""")
    source = next(fact for fact in result.facts if fact.kind == "dotnet.source")
    assert {
        "other-attributes",
        "other-properties",
        "build-evaluation",
        "missing-item-identity",
        "item-evaluation",
    } <= set(source.value["reasons"])
    sdk = next(fact for fact in result.facts if fact.kind == "dotnet.sdk")
    assert sdk.value["version"] == "9.0"
    dependency = next(fact for fact in result.facts if fact.kind == "dependency.declared")
    assert dependency.value["metadata"][0]["condition"] == "flag"


def test_framework_unknown_value_does_not_turn_into_a_detection() -> None:
    """Avoid inventing a framework signal from a malformed declaration value."""
    selected = context(("web.csproj",))
    missing = replace(selected.records[0], value={"identity": "x", "fact": {}})
    result = ASPNET_CORE_PLUGIN.collect(replace(selected, records=(missing,)))
    assert not result.facts
    assert all(not item.observation.positive for item in result.coverage)


def test_central_link_budget_is_explicit_and_a_missing_version_is_not_linked() -> None:
    """Make central-link truncation visible and refuse absent version evidence."""
    records = []
    for path, text in {
        "web.csproj": "<Project><ItemGroup>"
        + "".join(f'<PackageReference Include="P{i}"/>' for i in range(257))
        + "</ItemGroup></Project>",
        "Directory.Packages.props": "<Project><PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup><ItemGroup>"
        + "".join(f'<PackageVersion Include="P{i}" Version="1.0"/>' for i in range(257))
        + "</ItemGroup></Project>",
    }.items():
        records.extend(
            EvidenceRecord(
                fact.kind,
                {"identity": fact.identity, "fact": fact.value},
                path,
                RefRole.HEAD,
                "a" * 40,
                component="dotnet",
            )
            for fact in parse_msbuild(text).facts
        )
    states = {"web.csproj": "complete", "Directory.Packages.props": "complete"}
    links, notices = central_links(tuple(records), frozenset(states), states)
    assert len(links) == 256 and notices and "truncated" in notices[0]
    stripped = tuple(
        replace(
            record,
            value={
                "identity": "missing",
                "fact": {
                    "name": "P0",
                    "operation": "Include",
                    "version": None,
                },
            },
        )
        if record.kind == "dotnet.package_version"
        else record
        for record in records
        if record.kind != "dotnet.package_version" or record.value["fact"]["name"] == "P0"
    )
    links, _ = central_links(stripped, frozenset(states), states)
    assert links == ()


def test_source_adapters_do_not_import_execution_or_higher_lifecycle_owners() -> None:
    """Enforce the pure source-adapter dependency and execution boundary."""
    directory = Path(__file__).parents[1] / "src/ocr_toolkit/evidence/ecosystems/dotnet"
    for source in directory.glob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            )
            assert not any(
                module.split(".")[0] in {"os", "subprocess", "socket", "http", "urllib"}
                or module.startswith(
                    (
                        "ocr_toolkit.evidence.frameworks",
                        "ocr_toolkit.evidence.repository",
                        "ocr_toolkit.evidence.store",
                        "ocr_toolkit.evidence.collectors",
                    )
                )
                for module in modules
            )
            if isinstance(node, ast.ImportFrom) and node.module == "pathlib":
                assert {alias.name for alias in node.names} == {"PurePosixPath"}


@pytest.mark.parametrize(
    "xml",
    [
        "<Project><ItemGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></ItemGroup></Project>",
        '<Project><PackageReference Include="P"/></Project>',
        '<Project><PropertyGroup><Sdk Name="Microsoft.NET.Sdk.Web"/></PropertyGroup></Project>',
        "<Project><ItemGroup><PropertyGroup><Nullable>enable</Nullable></PropertyGroup></ItemGroup></Project>",
        '<Project><Project Sdk="Microsoft.NET.Sdk.Web"/></Project>',
        "<Project><PropertyGroup><Nullable><Nullable>enable</Nullable></Nullable></PropertyGroup></Project>",
    ],
)
def test_invalid_xml_placement_cannot_prove_static_evaluation(xml: str) -> None:
    """Refuse static inclusion claims from structurally misplaced declarations."""
    result = parse_msbuild(xml)
    assert result.runtime_dependent
    source = next(fact for fact in result.facts if fact.kind == "dotnet.source")
    assert "unsupported-structure" in source.value["reasons"]


def test_unknown_namespace_and_invalid_signal_do_not_suppress_other_projects() -> None:
    """Isolate unsupported XML and malformed framework signals by project."""
    result = parse_msbuild(
        '<Project xmlns="urn:unqualified"><PropertyGroup><Nullable>enable</Nullable></PropertyGroup></Project>'
    )
    assert result.runtime_dependent
    selected = context(("bad.csproj", "good.csproj"))
    bad = replace(
        selected.records[0],
        value={
            "identity": "x",
            "fact": {
                "name": "Microsoft.NET.Sdk.Web",
                "version": "invalid\nvalue",
            },
        },
    )
    result = ASPNET_CORE_PLUGIN.collect(replace(selected, records=(bad, selected.records[1])))
    assert {fact.component for fact in result.facts} == {"good.csproj"}
    assert {
        item.domain: item.observation.state.value
        for item in result.coverage
        if item.component == "bad.csproj"
    } == {
        "framework.declaration": "partial",
        "framework.resolution": "unavailable",
    }
