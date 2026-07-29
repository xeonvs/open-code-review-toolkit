"""Application and infrastructure evidence tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.infrastructure import infrastructure_candidate, parse_infrastructure_pins
from ocr_toolkit.evidence.manifest_model import MAX_MANIFEST_ITEMS
from ocr_toolkit.evidence.mcp import handle_request


def _git(root: Path, *args: str) -> str:
    """Run one Git command against a synthetic repository."""

    completed = subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True, capture_output=True
    )
    return completed.stdout.strip()


def test_infrastructure_candidate_preserves_surfaces_and_exclusions() -> None:
    """Cover legacy config surfaces without fixtures, dependencies, or dotenv files."""

    assert infrastructure_candidate("deploy/values.yaml")
    assert infrastructure_candidate("deploy/services/api/config.toml")
    assert infrastructure_candidate("infra/main.tfvars")
    assert infrastructure_candidate("containers/Dockerfile.runtime")
    assert not infrastructure_candidate("tests/fixtures/values.yaml")
    assert not infrastructure_candidate("vendor/package/config.json")
    assert not infrastructure_candidate("service/.env.production")
    assert not infrastructure_candidate("src/application.py")


def test_infrastructure_parser_extracts_versions_and_nested_images() -> None:
    """Preserve conservative application pins and nested image tag/digest forms."""

    parsed = parse_infrastructure_pins(
        "deploy/values.yaml",
        """
appVersion: '2.4.1'
runtime_version: 8.3.7
schema_version: 3
image:
  repository: registry.example.invalid/acme/service
  tag: 2.4.1
worker:
  image:
    name: registry.example.invalid/acme/worker
    digest: sha256:0123456789abcdef
templated_version: ${RELEASE_VERSION}
""",
    )

    versions = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "application.version"
    }
    assert versions == {
        "deploy/values.yaml:appversion": {
            "key": "appVersion",
            "version": "2.4.1",
            "source_path": "deploy/values.yaml",
        },
        "deploy/values.yaml:runtime_version": {
            "key": "runtime_version",
            "version": "8.3.7",
            "source_path": "deploy/values.yaml",
        },
    }
    images = {
        fact.value["name"]: fact.value for fact in parsed.facts if fact.kind == "container.image"
    }
    assert images["registry.example.invalid/acme/service"]["version"] == "2.4.1"
    assert images["registry.example.invalid/acme/worker"]["version"] == "sha256:0123456789abcdef"
    assert not any("schema_version" in fact.identity for fact in parsed.facts)
    assert not any("RELEASE_VERSION" in json.dumps(fact.value) for fact in parsed.facts)


def test_infrastructure_parser_handles_dockerfile_platform_and_rejects_unpinned_images() -> None:
    """Keep pinned FROM references while rejecting latest, aliases, and interpolation."""

    parsed = parse_infrastructure_pins(
        "containers/Dockerfile",
        """
FROM --platform=$BUILDPLATFORM python:3.12-slim AS builder
FROM registry.example.invalid/acme/runtime@sha256:fedcba9876543210
FROM alpine:latest AS ignored
FROM builder AS final
""",
    )

    images = [fact.value for fact in parsed.facts if fact.kind == "container.image"]
    assert images == [
        {
            "name": "python",
            "version": "3.12-slim",
            "source_path": "containers/Dockerfile",
            "key": "FROM",
        },
        {
            "name": "registry.example.invalid/acme/runtime",
            "version": "sha256:fedcba9876543210",
            "source_path": "containers/Dockerfile",
            "key": "FROM",
        },
    ]


def test_infrastructure_parser_redacts_and_bounds_untrusted_values() -> None:
    """Redact URL credentials and apply one aggregate bound with a safe notice."""

    values = [
        f"service_{index:04d}_version: 1.0.{index}" for index in range(MAX_MANIFEST_ITEMS + 1)
    ]
    values.append("registry_version: https://user:secret@example.invalid/v1")
    parsed = parse_infrastructure_pins("deploy/config.yaml", "\n".join(values))

    assert len(parsed.facts) == MAX_MANIFEST_ITEMS
    assert parsed.notices == (
        f"infrastructure facts were truncated after {MAX_MANIFEST_ITEMS} items",
    )
    assert "secret" not in json.dumps([fact.value for fact in parsed.facts])


def test_infrastructure_base_head_deltas_and_mcp_visibility(tmp_path: Path) -> None:
    """Expose application and image upgrades as changed facts through built-in MCP."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")
    (tmp_path / "values.yaml").write_text(
        "app_version: 1.0.0\nimage: registry.example.invalid/acme/app:1.0.0\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "values.yaml")
    _git(tmp_path, "commit", "-qm", "base infrastructure pins")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "values.yaml").write_text(
        "app_version: 2.0.0\nimage: registry.example.invalid/acme/app:2.0.0\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "values.yaml")
    _git(tmp_path, "commit", "-qm", "head infrastructure pins")
    head = _git(tmp_path, "rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    deltas = [delta for delta in store.deltas if delta.component == "infrastructure"]
    assert {delta.kind for delta in deltas} == {"application.version", "container.image"}
    assert {delta.change for delta in deltas} == {"changed"}
    assert {delta.before["version"] for delta in deltas} == {"1.0.0"}
    assert {delta.after["version"] for delta in deltas} == {"2.0.0"}

    response = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ocr_toolkit_evidence",
                "arguments": {"action": "list", "component": "infrastructure", "ref": "head"},
            },
        },
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert {record["kind"] for record in payload["records"]} == {
        "application.version",
        "container.image",
    }
