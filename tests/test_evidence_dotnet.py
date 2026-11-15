"""Bounded .NET declarations and immutable project-to-MCP integration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ocr_toolkit.evidence.categorize import categorize_paths
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors.registry import manifest_collector
from ocr_toolkit.evidence.container_paths import is_container_build_file
from ocr_toolkit.evidence.ecosystems.dotnet.linking import fact_value
from ocr_toolkit.evidence.infrastructure import infrastructure_candidate, parse_infrastructure_pins
from ocr_toolkit.evidence.mcp import call_tool, handle_request
from ocr_toolkit.evidence.model import RefRole
from ocr_toolkit.evidence.store import EvidenceStore


@pytest.mark.parametrize(
    "path,body",
    [
        (
            "src/web.csproj",
            '<Project><Import Project="unknown.props"/><ItemGroup><PackageReference Include="Example.Package"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><ItemGroup><PackageReference Include="Example.Package" VersionOverride="2.0"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><ItemGroup Condition="flag"><PackageReference Include="Example.Package"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><ItemGroup><PackageReference Update="Example.Package"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><ItemGroup><PackageReference Remove="Example.Package"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><ItemGroup><PackageReference Include="Example.Package"/><PackageReference Include="example.package"/></ItemGroup></Project>',
        ),
        (
            "src/web.csproj",
            '<Project><PropertyGroup><ManagePackageVersionsCentrally>false</ManagePackageVersionsCentrally></PropertyGroup><ItemGroup><PackageReference Include="Example.Package"/></ItemGroup></Project>',
        ),
        (
            "Directory.Packages.props",
            '<Project><PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup><ItemGroup><PackageVersion Include="Example.Package" Version="1.0"/><PackageVersion Include="example.package" Version="2.0"/></ItemGroup></Project>',
        ),
        (
            "Directory.Packages.props",
            '<Project><PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup><ItemGroup><PackageVersion Include="Example.Package" Version="$(Dynamic)"/></ItemGroup></Project>',
        ),
        (
            "Directory.Packages.props",
            '<Project><PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup><ItemGroup><PackageVersion Include="Example.Package" Version="1.0"/><PackageVersion Include="%45xample.Package" Version="2.0"/></ItemGroup></Project>',
        ),
        (
            "Directory.Packages.props",
            '<Project><ItemGroup><PackageVersion Include="Example.Package" Version="1.0"/></ItemGroup></Project>',
        ),
        (
            "Directory.Build.props",
            "<Project><PropertyGroup><ManagePackageVersionsCentrally>false</ManagePackageVersionsCentrally></PropertyGroup></Project>",
        ),
        ("Directory.Build.targets", '<Project><Import Project="unknown.targets"/></Project>'),
        ("src/Directory.Packages.props", "<Project>"),
    ],
)
def test_unproven_central_version_is_never_effective(
    dotnet_repo: Path, path: str, body: str
) -> None:
    """Refuse central associations whose inclusion or version evidence is unproven."""
    base = commit(dotnet_repo)
    write(dotnet_repo, path, body)
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert not any(
        record.kind == "dotnet.central_version" and record.ref is RefRole.HEAD
        for record in store.records
    )


@pytest.mark.parametrize(
    "identity", ["Microsoft.AspNetCore.App;Other.Framework", "Microsoft%2EAspNetCore%2EApp"]
)
def test_unevaluated_framework_identity_prevents_absence_claim(
    dotnet_repo: Path, identity: str
) -> None:
    """Propagate raw ItemSpec uncertainty through actual acquisition and framework coverage."""
    write(
        dotnet_repo,
        "src/web.csproj",
        f'<Project><ItemGroup><FrameworkReference Include="{identity}"/></ItemGroup></Project>',
    )
    base = commit(dotnet_repo)
    write(dotnet_repo, "README.md", "synthetic change")
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert any(
        record.kind == "dependency.declared"
        and record.ref is RefRole.HEAD
        and fact_value(record).get("name") == identity
        for record in store.records
    )
    assert any(
        coverage.component == "src/web.csproj"
        and coverage.domain == "framework.declaration"
        and coverage.state.value in {"partial", "runtime-dependent", "unavailable"}
        for coverage in store.coverage
    )


def test_construction_budget_omission_cannot_prove_a_central_version(
    dotnet_repo: Path, monkeypatch
) -> None:
    """Propagate parser-output omission through real Git collection and central-link admission."""
    from ocr_toolkit.evidence.ecosystems.dotnet.limits import ConstructionBudget

    base = commit(dotnet_repo)
    write(dotnet_repo, "README.md", "synthetic change")
    head = commit(dotnet_repo)
    complete = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert any(record.kind == "dotnet.central_version" for record in complete.records)
    original = ConstructionBudget.admit

    def budget(self, kind, identity, value):
        """Exhaust only the central source's output without changing input acquisition."""
        if kind == "dotnet.property" and value.get("name") == "ManagePackageVersionsCentrally":
            self.limit = 1
        return original(self, kind, identity, value)

    monkeypatch.setattr(ConstructionBudget, "admit", budget)
    partial = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert not any(record.kind == "dotnet.central_version" for record in partial.records)
    assert any(
        record.kind == "dotnet.source"
        and record.source_path == "Directory.Packages.props"
        and "fact-byte-limit" in fact_value(record)["reasons"]
        and fact_value(record)["interpretation"] == "runtime-dependent"
        for record in partial.records
    )


def test_nested_manifest_is_bounded_through_real_git_and_store(dotnet_repo: Path) -> None:
    """Recheck the original amplification trigger across immutable acquisition and persistence."""
    opening = '<ItemGroup Include="' + "x" * 4096 + '">'
    body = (
        "<Project>"
        + opening * 30
        + "<Nullable>enable</Nullable>" * 500
        + "</ItemGroup>" * 30
        + "</Project>"
    )
    base = commit(dotnet_repo)
    write(dotnet_repo, "src/hostile.csproj", body)
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    records = [
        record
        for record in store.records
        if record.source_path == "src/hostile.csproj" and record.kind.startswith("dotnet.")
    ]
    assert records and all(len(record.value["identity"]) < 256 for record in records)
    target = dotnet_repo / "private" / "evidence.json"
    store.write(target)
    restored = EvidenceStore.read(target)
    assert {record.id for record in restored.records} == {record.id for record in store.records}


def test_nested_and_colocated_projects_keep_distinct_central_scopes(dotnet_repo: Path) -> None:
    """Keep nearest central declarations and colocated project values isolated."""
    write(
        dotnet_repo,
        "src/nested/Directory.Packages.props",
        (dotnet_repo / "Directory.Packages.props").read_text().replace("1.2.3", "4.5.6"),
    )
    write(
        dotnet_repo,
        "src/nested/other.fsproj",
        '<Project><ItemGroup><PackageReference Include="Example.Package"/></ItemGroup></Project>',
    )
    write(
        dotnet_repo,
        "src/colocated.vbproj",
        '<Project><ItemGroup><PackageReference Include="Example.Package" Version="7.0"/></ItemGroup></Project>',
    )
    write(dotnet_repo, "nuget.config", "<!DOCTYPE evil><configuration/>")
    base = commit(dotnet_repo)
    write(dotnet_repo, "README.md", "synthetic change")
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    links = {
        record.source_path: fact_value(record)
        for record in store.records
        if record.kind == "dotnet.central_version" and record.ref is RefRole.HEAD
    }
    assert set(links) == {"src/web.csproj", "src/nested/other.fsproj"}
    assert links["src/nested/other.fsproj"]["version"] == "4.5.6"
    assert links["src/web.csproj"]["version"] == "1.2.3"
    assert not any(
        record.source_path == "nuget.config" and record.kind != "repository.file"
        for record in store.records
    )
    categories = categorize_paths(["src/nested/other.fsproj", "Program.cs", "script.csx"])
    assert categories["dependency_manifests"] == ("src/nested/other.fsproj",)
    assert categories["csharp"] == ("Program.cs", "script.csx")


@pytest.mark.parametrize(
    "path",
    [
        "Directory.Build.props",
        "Directory.Build.targets",
        "Directory.Packages.props",
        "packages.lock.json",
        "global.json",
        "Api.csproj",
        "lib.fsproj",
        "app.vbproj",
    ],
)
def test_registry_and_categories_agree_on_dotnet_manifests(path: str) -> None:
    """Align manifest discovery with .NET change categorization."""
    collector = manifest_collector("nested/" + path)
    assert collector is not None and collector.ecosystem == "dotnet"
    assert categorize_paths(["nested/" + path])["dependency_manifests"] == ("nested/" + path,)
    assert manifest_collector("nuget.config") is None


@pytest.mark.parametrize(
    "name",
    [
        "Dockerfile",
        "Containerfile",
        "Dockerfile.runtime",
        "Containerfile.debug",
        "api.Dockerfile",
        "worker.Containerfile",
        "API.CONTAINERFILE",
    ],
)
def test_container_grammar_shared_by_category_acquisition_and_parser(name: str) -> None:
    """Cross container classification, acquisition selection and actual FROM parsing."""
    path = "containers/" + name
    assert is_container_build_file(path) and infrastructure_candidate(path)
    assert categorize_paths([path])["containers"] == (path,)
    facts = parse_infrastructure_pins(
        path,
        "FROM --platform=linux/amd64 python:3.15 AS build\nFROM build AS runtime\nFROM alpine:3.24\n",
    ).facts
    assert {fact.value["name"] for fact in facts} == {"python", "alpine"}


@pytest.mark.parametrize(
    "path",
    [
        "Dockerfile.",
        ".Dockerfile",
        "notDockerfile",
        "DockerfileBackup",
        "api.Dockerfile.bak",
        "Containerfiles",
        "some/Containerfilex",
    ],
)
def test_container_grammar_rejects_near_matches(path: str) -> None:
    """Avoid treating similarly spelled ordinary files as container build inputs."""
    assert not is_container_build_file(path)
    assert "containers" not in categorize_paths([path])
    assert not parse_infrastructure_pins(path, "FROM example:1.0").facts


def test_dotnet_values_use_the_shared_redaction_boundary(dotnet_repo: Path) -> None:
    """Apply existing secret redaction to .NET facts before persistence."""
    write(
        dotnet_repo,
        "global.json",
        json.dumps({"sdk": {"version": "api_key='synthetic-placeholder'"}}),
    )
    base = commit(dotnet_repo)
    write(dotnet_repo, "README.md", "synthetic change")
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert "synthetic-placeholder" not in store.to_json()
    sdk = next(
        record
        for record in store.records
        if record.kind == "runtime.declared" and record.ref is RefRole.HEAD
    )
    assert fact_value(sdk)["version"] == "api_key=***"


def test_lock_only_aspnet_does_not_activate_framework(dotnet_repo: Path) -> None:
    """Require a project declaration rather than a lock-only ASP.NET package."""
    (dotnet_repo / "src/web.csproj").unlink()
    write(
        dotnet_repo,
        "packages.lock.json",
        json.dumps(
            {
                "version": 1,
                "dependencies": {
                    "net9.0": {"Microsoft.AspNetCore.App": {"type": "Direct", "resolved": "9.0.1"}},
                },
            }
        ),
    )
    base = commit(dotnet_repo)
    write(dotnet_repo, "README.md", "synthetic change")
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    assert any(
        record.kind == "dependency.locked" and record.component == "dotnet"
        for record in store.records
    )
    assert not any(record.kind == "framework.detected" for record in store.records)


def git(root: Path, *args: str) -> str:
    """Run deterministic Git plumbing in an isolated synthetic repository."""
    return subprocess.check_output(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(root),
            *args,
        ],
        text=True,
    ).strip()


def write(root: Path, path: str, text: str) -> None:
    """Create a synthetic repository input without modifying external sources."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def commit(root: Path) -> str:
    """Freeze the complete synthetic tree and return its immutable revision."""
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def dotnet_repo(tmp_path: Path) -> Path:
    """Provide isolated colocated projects with a declared central-package source."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Synthetic")
    git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    write(
        tmp_path,
        "Directory.Packages.props",
        """<Project><PropertyGroup>
<ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
</PropertyGroup><ItemGroup><PackageVersion Include="Example.Package" Version="1.2.3" />
</ItemGroup></Project>""",
    )
    write(
        tmp_path,
        "src/web.csproj",
        """<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup>
<TargetFrameworks>net8.0;net9.0</TargetFrameworks><Nullable>enable</Nullable>
</PropertyGroup><ItemGroup><PackageReference Include="Example.Package" />
<FrameworkReference Include="Microsoft.AspNetCore.App" /></ItemGroup></Project>""",
    )
    write(tmp_path, "src/console.csproj", '<Project Sdk="Microsoft.NET.Sdk"/>')
    return tmp_path


def test_real_git_central_link_framework_delta_readback_and_mcp(dotnet_repo: Path) -> None:
    """Cross collection, scoped deltas, private readback and a real stdio MCP child."""
    write(
        dotnet_repo,
        "src/console.csproj",
        "<Project><PropertyGroup><Nullable>enable</Nullable></PropertyGroup></Project>",
    )
    base = commit(dotnet_repo)
    central = dotnet_repo / "Directory.Packages.props"
    central.write_text(central.read_text().replace('Version="1.2.3"', 'Version="2.0.0"'))
    project = dotnet_repo / "src/web.csproj"
    project.write_text(project.read_text().replace("<Nullable>enable", "<Nullable>disable"))
    head = commit(dotnet_repo)
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=head)
    links = [record for record in store.records if record.kind == "dotnet.central_version"]
    settings = [delta for delta in store.deltas if delta.kind == "dotnet.property"]
    assert len(settings) == 1 and settings[0].identity.startswith("src/web.csproj:")
    assert settings[0].before["value"] == "enable" and settings[0].after["value"] == "disable"
    assert len(links) == 2
    assert {fact_value(record)["version"] for record in links} == {"1.2.3", "2.0.0"}
    assert all(fact_value(record)["effective_version"] is False for record in links)
    framework = [record for record in store.records if record.kind == "framework.detected"]
    assert len(framework) == 2
    assert {record.component for record in framework} == {"src/web.csproj"}
    assert {entry["scope"] for entry in fact_value(framework[0])["declarations"]} == {
        "web-sdk",
        "frameworkreference",
    }
    assert fact_value(framework[0])["resolutions"] == ()
    assert any(
        item.component == "src/web.csproj"
        and item.domain == "framework.resolution"
        and item.state.value == "runtime-dependent"
        for item in store.coverage
    )
    assert any(
        delta.kind == "dotnet.central_version" and delta.change == "changed"
        for delta in store.deltas
    )
    target = dotnet_repo / "private" / "store.json"
    store.write(target)
    restored = EvidenceStore.read(target)
    response = call_tool(
        restored,
        {"action": "list", "kind": "dotnet.central_version", "ref": "head", "page_size": 50},
    )
    payload = json.loads(response["content"][0]["text"])
    assert len(payload["records"]) == 1
    assert payload["records"][0]["commit_sha"] == head
    found = handle_request(
        restored,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ocr_toolkit_evidence_search",
                "arguments": {
                    "query": "enable",
                    "kind": "dotnet.property",
                    "ref": "head",
                },
            },
        },
    )
    assert found is not None and not found["result"].get("isError")
    assert json.loads(found["result"]["content"][0]["text"])["total_matches"] == 1
    # Exercise the actual stdio process against the same persisted production store.
    store.write(dotnet_repo / ".review-context" / "evidence.json")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "ocr_toolkit_evidence",
            "arguments": {
                "action": "get",
                "id": payload["records"][0]["id"],
            },
        },
    }
    peer = subprocess.run(
        [sys.executable, "-m", "ocr_toolkit.evidence"],
        cwd=dotnet_repo,
        input=json.dumps(request) + "\n",
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    response = json.loads(peer.stdout)
    assert not response["result"].get("isError"), response
    assert "2.0.0" in response["result"]["content"][0]["text"]
    assert peer.stderr == ""


def test_large_dotnet_snapshot_keeps_atomic_files_when_optional_kinds_truncate(
    dotnet_repo: Path,
) -> None:
    """Cross structural growth, .NET facts, typed limits and canonical delta/readback together."""
    projects = {f"projects/app{index:03}.csproj" for index in range(270)}
    for framework in ("net8.0", "net9.0"):
        for path in projects:
            write(
                dotnet_repo,
                path,
                f'<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>{framework}</TargetFramework></PropertyGroup></Project>',
            )
        revision = commit(dotnet_repo)
        if framework == "net8.0":
            base = revision
    store = collect_repository_evidence(dotnet_repo, base_ref=base, head_ref=revision)
    head_files = {
        record.source_path
        for record in store.records
        if record.kind == "repository.file" and record.ref is RefRole.HEAD
    }
    assert head_files == projects
    assert any("typed dotnet.sdk" in diagnostic for diagnostic in store.diagnostics)
    assert not any(delta.kind == "dotnet.sdk" for delta in store.deltas)
    target = dotnet_repo / "private" / "store.json"
    store.write(target)
    restored = EvidenceStore.read(target)
    encoded = json.loads(target.read_text())
    assert len(encoded["snapshots"]["head"]["record_ids"]) == len(projects)
    assert set(encoded["snapshots"]["head"]["record_ids"]) <= {
        record.id for record in restored.records
    }
    assert any(
        coverage.component in projects
        and coverage.domain == "framework.declaration"
        and coverage.state.value == "partial"
        for coverage in restored.coverage
    )
