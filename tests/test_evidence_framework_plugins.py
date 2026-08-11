"""Synthetic contracts for static framework and template evidence plugins."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.mcp import call_tool
from ocr_toolkit.evidence.model import RefRole
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
    assert role_template.value["fact"]["detection"] == "ansible-role-template"
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
    assert twig.value["fact"]["engine"] == "twig"


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
    payload = store.to_dict()
    record = next(item for item in payload["records"] if item["kind"] == "framework.detected")
    record["value"]["fact"]["unknown"] = True
    record.pop("id")
    path = tmp_path / "hostile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceStoreError, match=r"invalid framework.detected"):
        EvidenceStore.read(path)
