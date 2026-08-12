"""Synthetic contracts for static framework and template evidence plugins."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.framework_plugins import (
    BUILTIN_FRAMEWORK_PLUGINS,
    MAX_CONFIGURATION_PATHS,
    MAX_PLUGIN_FACTS,
    FrameworkPluginContext,
    FrameworkPluginResult,
    collect_framework_plugins,
)
from ocr_toolkit.evidence.mcp import call_tool
from ocr_toolkit.evidence.model import Confidence, EvidenceRecord, RefRole, TrustClass
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import RepositoryObject
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError


def git(root: Path, *args: str) -> str:
    """Run one deterministic Git command in a synthetic repository."""

    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def commit(root: Path, message: str) -> str:
    """Commit all synthetic files and return the immutable commit SHA."""

    git(root, "add", ".")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def mcp_payload(result: dict[str, object]) -> dict[str, Any]:
    """Decode one MCP text result into its synthetic JSON payload."""

    content = result["content"]
    assert isinstance(content, list) and isinstance(content[0], dict)
    return json.loads(content[0]["text"])


def framework_records(store: EvidenceStore, ref: RefRole = RefRole.HEAD) -> list[Any]:
    """Return framework records for one immutable ref."""

    return [
        record
        for record in store.records
        if record.kind == "framework.detected" and record.ref is ref
    ]


def initialize(root: Path) -> None:
    """Initialize one synthetic repository identity."""

    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic")
    git(root, "config", "user.email", "synthetic@example.invalid")


def test_jinja_framework_and_templates_are_component_scoped_and_visible_in_mcp(
    tmp_path: Path,
) -> None:
    """Expose direct Jinja version evidence and extensionless role templates."""

    initialize(tmp_path)
    service = tmp_path / "services" / "renderer"
    role_templates = tmp_path / "collections" / "demo" / "roles" / "web" / "templates"
    service.mkdir(parents=True)
    role_templates.mkdir(parents=True)
    (service / "pyproject.toml").write_text(
        '[project]\nname="renderer"\nversion="1.0.0"\ndependencies=["Jinja2>=3.1"]\n',
        encoding="utf-8",
    )
    (service / "pylock.toml").write_text(
        'lock-version = "1.0"\n[[packages]]\nname = "jinja2"\nversion = "3.1.6"\n',
        encoding="utf-8",
    )
    (service / "templates").mkdir()
    (service / "templates" / "app.conf.j2").write_text("port={{ port }}\n", encoding="utf-8")
    (role_templates / "daemon.conf").write_text("user={{ daemon_user }}\n", encoding="utf-8")
    base = commit(tmp_path, "base")
    (service / "templates" / "app.conf.j2").write_text(
        "port={{ port }}\nsecure={{ secure }}\n", encoding="utf-8"
    )
    head = commit(tmp_path, "update template")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    jinja = next(
        record
        for record in framework_records(store)
        if record.value["fact"]["framework"] == "jinja2"
    )
    assert jinja.component == "services/renderer"
    assert jinja.value["fact"]["version_state"] == "resolved"
    assert jinja.value["fact"]["resolutions"][0]["version"] == "3.1.6"

    templates = [
        record
        for record in store.records
        if record.kind == "template.file" and record.ref is RefRole.HEAD
    ]
    assert {record.source_path for record in templates} == {
        "services/renderer/templates/app.conf.j2",
        "collections/demo/roles/web/templates/daemon.conf",
    }
    role_template = next(
        record for record in templates if record.source_path.endswith("daemon.conf")
    )
    assert role_template.component == "collections/demo/roles/web"
    role_fact = cast(dict[str, Any], role_template.to_dict()["value"])["fact"]
    assert role_fact["detection"] == "ansible-role-template"
    assert any(
        delta.kind == "template.file"
        and delta.identity == "services/renderer/templates/app.conf.j2"
        and delta.change == "changed"
        for delta in store.deltas
    )

    listed = mcp_payload(
        call_tool(
            store,
            {
                "action": "list",
                "kind": "framework.detected",
                "component": "services/renderer",
                "ref": "head",
            },
        )
    )
    assert [record["value"]["fact"]["framework"] for record in listed["records"]] == ["jinja2"]


def test_lock_only_and_transitive_go_packages_do_not_activate_frameworks(tmp_path: Path) -> None:
    """Require direct declarations rather than lock/checksum package presence."""

    initialize(tmp_path)
    (tmp_path / "go.mod").write_text(
        "module synthetic.invalid/service\n\ngo 1.24\n", encoding="utf-8"
    )
    (tmp_path / "go.sum").write_text(
        "github.com/labstack/echo/v4 v4.13.4 h1:synthetic\n", encoding="utf-8"
    )
    (tmp_path / "pylock.toml").write_text(
        'lock-version = "1.0"\n[[packages]]\nname = "jinja2"\nversion = "3.1.6"\n',
        encoding="utf-8",
    )
    base = commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("synthetic\n", encoding="utf-8")
    head = commit(tmp_path, "docs")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    assert framework_records(store) == []


def test_go_php_and_frontend_plugins_keep_related_signals_in_the_same_component(
    tmp_path: Path,
) -> None:
    """Detect direct core frameworks and related stacks without code graphs."""

    initialize(tmp_path)
    api = tmp_path / "api"
    web = tmp_path / "web"
    ui = tmp_path / "ui"
    for path in (api, web, ui):
        path.mkdir()
    (api / "go.mod").write_text(
        """module synthetic.invalid/api

go 1.24

require (
 github.com/labstack/echo/v4 v4.13.4
 google.golang.org/grpc v1.71.0
)
""",
        encoding="utf-8",
    )
    (web / "composer.json").write_text(
        json.dumps(
            {
                "require": {
                    "php": "^8.3",
                    "symfony/framework-bundle": "^7.2",
                    "twig/twig": "^3.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (web / "composer.lock").write_text(
        json.dumps(
            {
                "packages": [
                    {"name": "symfony/framework-bundle", "version": "v7.2.4"},
                    {"name": "twig/twig", "version": "v3.19.0"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (web / "templates").mkdir()
    (web / "templates" / "page.twig").write_text("{{ title }}\n", encoding="utf-8")
    (ui / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"typescript": "^5.8", "vite": "^6.2"},
            }
        ),
        encoding="utf-8",
    )
    base = commit(tmp_path, "base")
    (ui / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    head = commit(tmp_path, "add frontend config")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    facts = {
        (record.component, record.value["fact"]["framework"]): record.value["fact"]
        for record in framework_records(store)
    }
    assert ("api", "echo") in facts
    assert facts[("api", "echo")]["related"][0]["name"] == "grpc"
    assert ("web", "symfony") in facts and ("web", "twig") in facts
    assert facts[("web", "symfony")]["version_state"] == "resolved"
    assert ("ui", "react") in facts
    assert {item["name"] for item in facts[("ui", "react")]["related"]} == {
        "typescript",
        "vite",
    }
    twig = next(
        record
        for record in store.records
        if record.kind == "template.file" and record.source_path.endswith("page.twig")
    )
    twig_fact = cast(dict[str, Any], twig.to_dict()["value"])["fact"]
    assert twig_fact["engine"] == "twig"


def test_cross_provider_evidence_projects_through_deltas_bootstrap_and_one_mcp(
    tmp_path: Path,
) -> None:
    """Project framework, template, and coverage changes through shared contracts."""

    initialize(tmp_path)
    renderer = tmp_path / "services" / "renderer"
    api = tmp_path / "services" / "api"
    web = tmp_path / "services" / "web"
    ui = tmp_path / "apps" / "portal"
    for component in (renderer, api, web, ui):
        component.mkdir(parents=True)

    (renderer / "pyproject.toml").write_text(
        '[project]\nname="renderer"\nversion="1"\ndependencies=["jinja2>=3.1"]\n',
        encoding="utf-8",
    )
    (renderer / "pylock.toml").write_text(
        'lock-version = "1.0"\n[[packages]]\nname = "jinja2"\nversion = "3.1.5"\n',
        encoding="utf-8",
    )
    (renderer / "templates").mkdir()
    (renderer / "templates" / "service.conf.j2").write_text("port={{ port }}\n", encoding="utf-8")
    (api / "go.mod").write_text(
        """module example.invalid/api

go 1.24

require github.com/labstack/echo/v4 v4.13.4
""",
        encoding="utf-8",
    )
    (web / "composer.json").write_text(
        json.dumps(
            {
                "require": {
                    "php": "^8.3",
                    "symfony/framework-bundle": "^7.2",
                    "twig/twig": "^3.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (web / "composer.lock").write_text(
        json.dumps(
            {
                "packages": [
                    {"name": "symfony/framework-bundle", "version": "v7.2.4"},
                    {"name": "twig/twig", "version": "v3.19.0"},
                ],
                "packages-dev": [],
            }
        ),
        encoding="utf-8",
    )
    (web / "templates").mkdir()
    (web / "templates" / "page.twig").write_text("{{ title }}\n", encoding="utf-8")
    (ui / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^18.3.0"},
                "devDependencies": {"typescript": "^5.8", "vite": "^6.2"},
            }
        ),
        encoding="utf-8",
    )
    (ui / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/react": {"version": "18.3.1"},
                    "node_modules/typescript": {"version": "5.8.3"},
                    "node_modules/vite": {"version": "6.2.0"},
                },
            }
        ),
        encoding="utf-8",
    )
    base = commit(tmp_path, "base ecosystems")

    # Exercise semantic change, removal, and addition without requiring checkout
    # or provider-specific projection code after the immutable refs are committed.
    (renderer / "pylock.toml").unlink()
    (renderer / "templates" / "service.conf.j2").write_text(
        "port={{ port }}\ntls={{ tls }}\n", encoding="utf-8"
    )
    (api / "go.mod").write_text(
        """module example.invalid/api

go 1.24

require github.com/gofiber/fiber/v2 v2.52.6
""",
        encoding="utf-8",
    )
    (web / "composer.lock").write_text(
        json.dumps(
            {
                "packages": [
                    {"name": "symfony/framework-bundle", "version": "v7.2.5"},
                    {"name": "twig/twig", "version": "v3.19.0"},
                ],
                "packages-dev": [],
            }
        ),
        encoding="utf-8",
    )
    (web / "templates" / "page.twig").unlink()
    (ui / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"next": "^15.2.0", "react": "^19.0.0"},
                "devDependencies": {"typescript": "^5.8", "vite": "^6.2"},
            }
        ),
        encoding="utf-8",
    )
    (ui / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/next": {"version": "15.2.4"},
                    "node_modules/react": {"version": "19.0.0"},
                    "node_modules/typescript": {"version": "5.8.3"},
                    "node_modules/vite": {"version": "6.2.0"},
                },
            }
        ),
        encoding="utf-8",
    )
    (ui / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    role_templates = tmp_path / "automation" / "roles" / "worker" / "templates"
    role_templates.mkdir(parents=True)
    (role_templates / "worker.service").write_text("User={{ worker_user }}\n", encoding="utf-8")
    head = commit(tmp_path, "head ecosystems")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    framework_deltas = {
        (delta.component, delta.identity): delta.change
        for delta in store.deltas
        if delta.kind == "framework.detected"
    }
    assert framework_deltas == {
        ("apps/portal", "react-typescript:next"): "added",
        ("apps/portal", "react-typescript:react"): "changed",
        ("services/api", "go-web:echo"): "removed",
        ("services/api", "go-web:fiber"): "added",
        ("services/renderer", "jinja2:jinja2"): "changed",
        ("services/web", "symfony-php:symfony"): "changed",
        ("services/web", "symfony-php:twig"): "changed",
    }
    template_deltas = {
        delta.identity: delta.change for delta in store.deltas if delta.kind == "template.file"
    }
    assert template_deltas == {
        "automation/roles/worker/templates/worker.service": "added",
        "services/renderer/templates/service.conf.j2": "changed",
        "services/web/templates/page.twig": "removed",
    }
    coverage_deltas = [
        delta for delta in store.deltas if delta.kind == "repository.evidence_coverage"
    ]
    assert any(
        delta.component == "services/renderer"
        and '"framework.resolution","jinja2:jinja2"' in delta.identity
        and delta.change == "changed"
        and delta.before == {"state": "complete", "reasons": ("lock-version-present",)}
        and delta.after == {"state": "partial", "reasons": ("lock-version-missing",)}
        for delta in coverage_deltas
    )
    assert any(
        delta.component == "automation/roles/worker"
        and '"template.inventory","jinja2"' in delta.identity
        and delta.change == "added"
        for delta in coverage_deltas
    )

    framework_count = sum(record.kind == "framework.detected" for record in store.records)
    template_count = sum(record.kind == "template.file" for record in store.records)
    summary = mcp_payload(call_tool(store, {"action": "summary"}))
    kinds = cast(dict[str, int], summary["kinds"])
    assert kinds["framework.detected"] == framework_count
    assert kinds["template.file"] == template_count
    assert cast(dict[str, int], summary["delta_kinds"])["framework.detected"] == len(
        framework_deltas
    )
    assert cast(dict[str, int], summary["delta_kinds"])["template.file"] == len(template_deltas)
    assert cast(dict[str, int], summary["coverage_states"])["partial"] >= 1
    assert all(summary[key] for key in ("records", "coverage_records", "deltas"))

    listed_frameworks = mcp_payload(
        call_tool(
            store,
            {
                "action": "list",
                "kind": "framework.detected",
                "component": "apps/portal",
                "ref": "head",
            },
        )
    )
    framework_rows = cast(list[dict[str, Any]], listed_frameworks["records"])
    assert {
        cast(dict[str, Any], cast(dict[str, Any], row["value"])["fact"])["framework"]
        for row in framework_rows
    } == {"next", "react"}
    fetched_framework = mcp_payload(
        call_tool(store, {"action": "get", "id": framework_rows[0]["id"]})
    )
    assert fetched_framework["record"] == framework_rows[0]

    listed_coverage = mcp_payload(
        call_tool(
            store,
            {
                "action": "list",
                "kind": "repository.evidence_coverage",
                "component": "services/renderer",
                "ref": "head",
            },
        )
    )
    coverage_rows = cast(list[dict[str, Any]], listed_coverage["records"])
    assert {row["domain"] for row in coverage_rows} >= {
        "framework.configuration",
        "framework.declaration",
        "framework.resolution",
        "template.inventory",
    }
    resolution_coverage = next(
        row
        for row in coverage_rows
        if row["domain"] == "framework.resolution" and row["scope"] == "jinja2:jinja2"
    )
    fetched_coverage = mcp_payload(
        call_tool(store, {"action": "get", "id": resolution_coverage["id"]})
    )
    assert fetched_coverage["record"] == resolution_coverage

    listed_deltas = mcp_payload(
        call_tool(
            store,
            {
                "action": "list",
                "kind": "repository.evidence_delta",
                "delta_kind": "framework.detected",
                "component": "services/api",
            },
        )
    )
    delta_rows = cast(list[dict[str, Any]], listed_deltas["records"])
    assert {(row["identity"], row["change"]) for row in delta_rows} == {
        ("go-web:echo", "removed"),
        ("go-web:fiber", "added"),
    }
    fetched_delta = mcp_payload(call_tool(store, {"action": "get", "id": delta_rows[0]["id"]}))
    assert fetched_delta["record"] == delta_rows[0]

    bootstrap = render_bootstrap(store)
    assert f"framework.detected={framework_count}" in bootstrap
    assert f"template.file={template_count}" in bootstrap
    assert f"framework.detected={len(framework_deltas)}" in bootstrap
    assert f"template.file={len(template_deltas)}" in bootstrap
    assert "kind=repository.evidence_delta" in bootstrap
    assert "delta_kind" in bootstrap
    assert "automation/roles/worker" in bootstrap
    assert "action=summary" in bootstrap
    assert "action=list" in bootstrap
    assert "action=get" in bootstrap
    assert "service.conf.j2" not in bootstrap
    assert "page.twig" not in bootstrap
    assert "v7.2.5" not in bootstrap


def test_plugin_nested_schema_is_revalidated_on_store_load(tmp_path: Path) -> None:
    """Reject unknown nested fields in persisted framework evidence."""

    initialize(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="1"\ndependencies=["jinja2==3.1.6"]\n',
        encoding="utf-8",
    )
    base = commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("change\n", encoding="utf-8")
    head = commit(tmp_path, "head")
    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    payload = cast(dict[str, Any], store.to_dict())
    record = next(item for item in payload["records"] if item["kind"] == "framework.detected")
    record["value"]["fact"]["unknown"] = True
    record.pop("id")
    path = tmp_path / "hostile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match=r"invalid framework.detected"):
        EvidenceStore.read(path)


def coverage_record(
    store: EvidenceStore, *, component: str, domain: str, scope: str, ref: RefRole = RefRole.HEAD
) -> Any:
    """Return one exact framework coverage record from a synthetic store."""

    return next(
        item
        for item in store.coverage
        if item.component == component
        and item.domain == domain
        and item.scope == scope
        and item.ref is ref
    )


def test_go_versions_and_replacements_use_effective_go_mod_semantics(tmp_path: Path) -> None:
    """Treat direct Go requirements as resolved and replacement targets as effective."""

    initialize(tmp_path)
    (tmp_path / "go.mod").write_text(
        """module synthetic.invalid/api

go 1.24

require github.com/labstack/echo/v4 v4.13.4
replace github.com/labstack/echo/v4 => synthetic.invalid/echo/v4 v4.13.5
""",
        encoding="utf-8",
    )
    base = commit(tmp_path, "module replacement")
    (tmp_path / "go.mod").write_text(
        """module synthetic.invalid/api

go 1.24

require github.com/labstack/echo/v4 v4.13.4
replace github.com/labstack/echo/v4 => ./local-echo
""",
        encoding="utf-8",
    )
    head = commit(tmp_path, "local replacement")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    base_echo = next(
        record
        for record in framework_records(store, RefRole.BASE)
        if record.value["fact"]["framework"] == "echo"
    )
    head_echo = next(
        record for record in framework_records(store) if record.value["fact"]["framework"] == "echo"
    )
    assert base_echo.value["fact"]["version_state"] == "resolved"
    assert base_echo.value["fact"]["resolutions"] == (
        {
            "package": "github.com/labstack/echo/v4",
            "version": "v4.13.5",
            "source": "go.replace",
            "source_path": "go.mod",
        },
    )
    assert head_echo.value["fact"]["version_state"] == "local-override"
    assert head_echo.value["fact"]["resolutions"] == ()
    assert head_echo.value["fact"]["replacement"] == {
        "target": "./local-echo",
        "type": "local",
        "version": None,
    }
    resolution = coverage_record(
        store,
        component="repository",
        domain="framework.resolution",
        scope="go-web:echo",
    )
    assert resolution.state.value == "partial"
    assert resolution.reasons == ("local-replacement",)


def test_template_components_follow_nearest_manifest_root_and_configuration_isolated(
    tmp_path: Path,
) -> None:
    """Bind templates/configuration to the nearest owning manifest component."""

    initialize(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="root"\nversion="1"\ndependencies=["jinja2==3.1.6"]\n',
        encoding="utf-8",
    )
    nested = tmp_path / "services" / "renderer"
    (nested / "templates").mkdir(parents=True)
    (nested / "pyproject.toml").write_text(
        '[project]\nname="renderer"\nversion="1"\ndependencies=["jinja2==3.1.6"]\n',
        encoding="utf-8",
    )
    (nested / "templates" / "service.conf.j2").write_text("x={{ x }}\n", encoding="utf-8")
    (tmp_path / "root.conf.j2").write_text("root={{ root }}\n", encoding="utf-8")
    base = commit(tmp_path, "templates")
    (tmp_path / "README.md").write_text("head\n", encoding="utf-8")
    head = commit(tmp_path, "head")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    templates = {
        record.source_path: record.component
        for record in store.records
        if record.kind == "template.file" and record.ref is RefRole.HEAD
    }
    assert templates == {
        "root.conf.j2": "repository",
        "services/renderer/templates/service.conf.j2": "services/renderer",
    }
    frameworks = {record.component: record.value["fact"] for record in framework_records(store)}
    assert "services/renderer/pyproject.toml" not in frameworks["repository"]["configuration_paths"]
    assert (
        "services/renderer/pyproject.toml" in frameworks["services/renderer"]["configuration_paths"]
    )


def test_configuration_and_template_limits_degrade_exact_coverage(tmp_path: Path) -> None:
    """Never claim complete inventory after plugin-owned output truncation."""

    initialize(tmp_path)
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "19.0.0"}}), encoding="utf-8"
    )
    for index in range(MAX_CONFIGURATION_PATHS + 1):
        path = tmp_path / f"tsconfig-{index:03}.json"
        path.write_text("{}\n", encoding="utf-8")
    for index in range(MAX_PLUGIN_FACTS + 1):
        path = tmp_path / "templates" / f"page-{index:03}.j2"
        path.parent.mkdir(exist_ok=True)
        path.write_text("{{ value }}\n", encoding="utf-8")
    base = commit(tmp_path, "bounded files")
    (tmp_path / "README.md").write_text("head\n", encoding="utf-8")
    head = commit(tmp_path, "head")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    react = next(
        record
        for record in framework_records(store)
        if record.value["fact"]["framework"] == "react"
    )
    assert react.value["fact"]["configuration_state"] == "partial"
    assert len(react.value["fact"]["configuration_paths"]) == MAX_CONFIGURATION_PATHS
    config_coverage = coverage_record(
        store,
        component="repository",
        domain="framework.configuration",
        scope="react-typescript:react",
    )
    assert config_coverage.state.value == "partial"
    assert config_coverage.reasons == ("configuration-path-limit",)
    template_coverage = coverage_record(
        store,
        component="templates",
        domain="template.inventory",
        scope="jinja2",
    )
    assert template_coverage.state.value == "partial"
    assert template_coverage.reasons == ("bounded-tree-complete", "template-fact-limit")
    assert any("template plugin fact limit reached" in message for message in store.diagnostics)


def test_plugin_failure_isolated_from_sibling_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Degrade one package-owned provider without suppressing sibling output."""

    class BrokenPlugin:
        plugin_id = "broken"

        def collect(self, context: FrameworkPluginContext) -> FrameworkPluginResult:
            raise RuntimeError("synthetic provider failure")

    jinja_record = EvidenceRecord(
        kind="repository.manifest",
        value={"identity": "pyproject.toml", "fact": {"path": "pyproject.toml"}},
        source_path="pyproject.toml",
        ref=RefRole.HEAD,
        commit_sha="a" * 40,
        component="python",
        provenance="synthetic",
        confidence=Confidence.EXACT,
        trust=TrustClass.SOURCE_REPOSITORY,
    )
    declaration = EvidenceRecord(
        kind="dependency.declared",
        value={
            "identity": "pyproject.toml:project:jinja2",
            "fact": {"name": "jinja2", "version": "3.1.6", "scope": "project"},
        },
        source_path="pyproject.toml",
        ref=RefRole.HEAD,
        commit_sha="a" * 40,
        component="python",
        provenance="synthetic",
        confidence=Confidence.EXACT,
        trust=TrustClass.SOURCE_REPOSITORY,
    )
    monkeypatch.setattr(
        "ocr_toolkit.evidence.framework_plugins.BUILTIN_FRAMEWORK_PLUGINS",
        (BrokenPlugin(), BUILTIN_FRAMEWORK_PLUGINS[0]),
    )
    facts, _coverage, notices = collect_framework_plugins(
        FrameworkPluginContext(
            records=(jinja_record, declaration),
            entries=(RepositoryObject("pyproject.toml", "100644", "blob", "b" * 40),),
            source_statuses=(),
            ref=RefRole.HEAD,
            commit_sha="a" * 40,
        )
    )
    assert [fact.identity for fact in facts] == ["jinja2:jinja2"]
    assert notices == ("framework plugin unavailable: broken",)


def test_nested_schema_rejects_identity_and_plugin_relationship_mismatches(tmp_path: Path) -> None:
    """Bind persisted framework identity, plugin, framework, and ecosystem fields."""

    initialize(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nversion="1"\ndependencies=["jinja2==3.1.6"]\n',
        encoding="utf-8",
    )
    base = commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("head\n", encoding="utf-8")
    head = commit(tmp_path, "head")
    payload = cast(
        dict[str, Any],
        collect_repository_evidence(tmp_path, base_ref=base, head_ref=head).to_dict(),
    )
    record = next(item for item in payload["records"] if item["kind"] == "framework.detected")
    record["value"]["identity"] = "jinja2:react"
    record.pop("id")
    path = tmp_path / "mismatch.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match=r"invalid framework.detected"):
        EvidenceStore.read(path)


def test_malformed_and_truncated_manifests_degrade_applicable_coverage(tmp_path: Path) -> None:
    """Keep absence unknown when a supported declaration source cannot be fully parsed."""

    initialize(tmp_path)
    (tmp_path / "pyproject.toml").write_text("not = [valid\n", encoding="utf-8")
    packages = {f"synthetic-{index}": "1.0.0" for index in range(512)}
    packages["react"] = "19.0.0"
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": packages}), encoding="utf-8")
    base = commit(tmp_path, "sources")
    (tmp_path / "README.md").write_text("head\n", encoding="utf-8")
    head = commit(tmp_path, "head")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    jinja_declarations = coverage_record(
        store,
        component="repository",
        domain="framework.declaration",
        scope="jinja2",
    )
    assert jinja_declarations.state.value == "unavailable"
    assert jinja_declarations.reasons == ("parse-unavailable",)
    react_declarations = coverage_record(
        store,
        component="repository",
        domain="framework.declaration",
        scope="react-typescript",
    )
    assert react_declarations.state.value == "partial"
    assert react_declarations.reasons == ("source-item-limit",)
    assert not any(
        cast(dict[str, Any], record.to_dict()["value"])["fact"]["framework"] == "react"
        for record in framework_records(store)
    )
