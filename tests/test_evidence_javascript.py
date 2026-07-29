"""JavaScript manifest, npm lock, delta, and MCP evidence tests."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors import collect_ref_facts, parse_manifest
from ocr_toolkit.evidence.javascript_manifests import (
    parse_package_json,
    parse_package_lock,
    parse_pnpm_lock,
    parse_yarn_lock,
)
from ocr_toolkit.evidence.manifest_model import MAX_MANIFEST_ITEMS
from ocr_toolkit.evidence.mcp import handle_request
from ocr_toolkit.evidence.model import RefRole
from ocr_toolkit.evidence.repository import GitRepositoryReader


def _git(root: Path, *args: str) -> str:
    """Run bounded Git commands against one synthetic repository."""

    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def test_package_json_preserves_runtime_manager_and_dependency_scopes() -> None:
    """Keep declaration scopes and package-manager constraints distinct."""

    parsed = parse_package_json(
        json.dumps(
            {
                "engines": {"node": ">=20", "npm": ">=10", "editor": "ignored"},
                "packageManager": "pnpm@10.13.1",
                "dependencies": {
                    "@scope/runtime": "^1.0.0",
                    "private": "https://build:secret@example.invalid/private.tgz",
                },
                "devDependencies": {"vitest": "^3.2.0"},
                "peerDependencies": {"react": "^19.0.0"},
                "peerDependenciesMeta": {"react": {"optional": True}},
                "optionalDependencies": {"fsevents": "^2.3.3"},
            }
        )
    )

    runtimes = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "runtime.declared"
    }
    declarations = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "dependency.declared"
    }
    assert runtimes["node"]["constraint"] == ">=20"
    assert runtimes["npm"]["source"] == "engines"
    assert runtimes["pnpm"]["constraint"] == "10.13.1"
    assert declarations["production:@scope/runtime"]["scope"] == "production"
    assert declarations["development:vitest"]["scope"] == "development"
    assert declarations["peer:react"]["optional"] is True
    assert declarations["optional:fsevents"]["scope"] == "optional"
    assert "secret" not in declarations["production:private"]["constraint"]


def test_package_json_truncates_across_all_sections_with_notice() -> None:
    """Apply one aggregate fact budget instead of a per-section multiplier."""

    parsed = parse_package_json(
        json.dumps(
            {
                "dependencies": {
                    f"runtime-{index:04d}": "1.0.0" for index in range(MAX_MANIFEST_ITEMS)
                },
                "devDependencies": {"overflow": "2.0.0"},
            }
        )
    )

    assert len(parsed.facts) == MAX_MANIFEST_ITEMS
    assert parsed.notices == (
        f"package.json facts were truncated after {MAX_MANIFEST_ITEMS} items",
    )


def test_package_lock_versions_preserve_resolved_metadata_and_nested_v1() -> None:
    """Support npm lock versions 1 through 3 without conflating path variants."""

    v1 = parse_package_lock(
        json.dumps(
            {
                "lockfileVersion": 1,
                "dependencies": {
                    "alpha": {
                        "version": "1.0.0",
                        "resolved": "https://user:secret@example.invalid/alpha.tgz",
                        "dependencies": {"beta": {"version": "2.0.0", "dev": True}},
                    }
                },
            }
        )
    )
    v3 = parse_package_lock(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "root", "version": "1.0.0"},
                    "node_modules/@scope/pkg": {
                        "version": "3.0.0",
                        "integrity": "sha512-synthetic",
                        "optional": True,
                        "engines": {"node": ">=20"},
                    },
                    "packages/workspace": {"name": "workspace", "link": True},
                },
            }
        )
    )

    assert [fact.value["name"] for fact in v1.facts] == ["alpha", "beta"]
    assert v1.facts[0].value["source"] == "registry:example.invalid"
    assert "resolved" not in v1.facts[0].value
    assert v1.facts[1].value["path"] == "node_modules/alpha/node_modules/beta"
    assert len(v3.facts) == 1
    assert v3.facts[0].value["name"] == "@scope/pkg"
    assert v3.facts[0].value["optional"] is True
    assert v3.facts[0].value["engines"] == {"node": ">=20"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"lockfileVersion": 4, "packages": {}},
        {"lockfileVersion": 3},
        {"lockfileVersion": 1},
    ],
)
def test_package_lock_rejects_unknown_or_incomplete_contracts(payload: object) -> None:
    """Degrade rather than guessing when the npm lock contract is unsupported."""

    with pytest.raises(ValueError):
        parse_package_lock(json.dumps(payload))


def test_yarn_classic_and_modern_locks_preserve_selectors_and_versions() -> None:
    """Parse generated Yarn v1 and Berry entries without a YAML dependency."""

    classic = parse_yarn_lock(
        """
# yarn lockfile v1

"@scope/pkg@^1.0.0", "@scope/pkg@~1.1.0":
  version "1.1.2"
  resolved "https://user:secret@registry.example.invalid/pkg.tgz"

plain@^2.0.0:
  version "2.1.0"
"""
    )
    modern = parse_yarn_lock(
        """
__metadata:
  version: 8
  cacheKey: 10c0

"@scope/pkg@npm:^3.0.0":
  version: 3.2.1
  resolution: "@scope/pkg@npm:3.2.1"
  checksum: 10/synthetic
  languageName: node
  linkType: hard

"workspace@workspace:.":
  version: 0.0.0-use.local
  resolution: "workspace@workspace:."
"""
    )

    assert [(fact.value["name"], fact.value["version"]) for fact in classic.facts] == [
        ("@scope/pkg", "1.1.2"),
        ("plain", "2.1.0"),
    ]
    assert classic.facts[0].value["source"] == "registry:registry.example.invalid"
    assert [(fact.value["name"], fact.value["version"]) for fact in modern.facts] == [
        ("@scope/pkg", "3.2.1"),
        ("workspace", "0.0.0-use.local"),
    ]
    assert modern.facts[0].value["source"] == "npm"


def test_pnpm_lock_versions_preserve_package_keys_and_peer_variants() -> None:
    """Parse pnpm v5-v9 package and snapshot keys with scoped names."""

    modern = parse_pnpm_lock(
        """
lockfileVersion: '9.0'

importers:
  .:
    dependencies: {}

packages:
  '@scope/pkg@1.2.3':
    resolution: {integrity: sha512-synthetic}
  plain@2.0.0(peer@1.0.0):
    resolution: {integrity: sha512-other}

snapshots:
  plain@2.0.0(peer@1.0.0): {}
"""
    )
    legacy = parse_pnpm_lock(
        """
lockfileVersion: 6.0
packages:
  /@scope/pkg/1.2.3:
    resolution: {integrity: sha512-synthetic}
  /plain/2.0.0:
    resolution: {integrity: sha512-other}
"""
    )
    older = parse_pnpm_lock(
        """
lockfileVersion: 5.4
packages:
  /@scope/pkg/1.2.3:
    resolution: {integrity: sha512-synthetic}
"""
    )

    assert {(fact.value["name"], fact.value["version"]) for fact in modern.facts} == {
        ("@scope/pkg", "1.2.3"),
        ("plain", "2.0.0"),
    }
    assert len(modern.facts) == 2
    assert {(fact.value["name"], fact.value["version"]) for fact in legacy.facts} == {
        ("@scope/pkg", "1.2.3"),
        ("plain", "2.0.0"),
    }
    assert older.facts[0].value["name"] == "@scope/pkg"


@pytest.mark.parametrize(
    ("parser", "text"),
    [
        (parse_yarn_lock, "not a generated lock\n"),
        (parse_pnpm_lock, "packages: {}\n"),
        (parse_pnpm_lock, "lockfileVersion: '10.0'\npackages: {}\n"),
    ],
)
def test_text_lock_parsers_reject_unknown_contracts(
    parser: Callable[[str], object], text: str
) -> None:
    """Fail closed when generated text lock versions cannot be identified."""

    with pytest.raises(ValueError):
        parser(text)


def test_javascript_deltas_and_builtin_mcp_preserve_version_changes(tmp_path: Path) -> None:
    """Expose runtime, declared, and locked changes through typed deltas and MCP."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")

    def write_state(node: str, constraint: str, locked: str) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"engines": {"node": node}, "dependencies": {"demo": constraint}}),
            encoding="utf-8",
        )
        (tmp_path / "package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {"node_modules/demo": {"version": locked}},
                }
            ),
            encoding="utf-8",
        )

    write_state(">=20", "^1", "1.0.0")
    _git(tmp_path, "add", "package.json", "package-lock.json")
    _git(tmp_path, "commit", "-qm", "base JavaScript evidence")
    base = _git(tmp_path, "rev-parse", "HEAD")
    write_state(">=22", "^2", "2.0.0")
    _git(tmp_path, "add", "package.json", "package-lock.json")
    _git(tmp_path, "commit", "-qm", "head JavaScript evidence")
    head = _git(tmp_path, "rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    locked_delta = next(delta for delta in store.deltas if delta.kind == "dependency.locked")
    assert locked_delta.change == "changed"
    assert locked_delta.before["version"] == "1.0.0"
    assert locked_delta.after["version"] == "2.0.0"
    assert {delta.kind for delta in store.deltas} >= {
        "runtime.declared",
        "dependency.declared",
        "dependency.locked",
    }

    response = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ocr_toolkit_evidence",
                "arguments": {
                    "action": "list",
                    "component": "javascript",
                    "ref": "head",
                },
            },
        },
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert {record["kind"] for record in payload["records"]} >= {
        "runtime.declared",
        "dependency.declared",
        "dependency.locked",
    }


def test_malformed_package_lock_is_bounded_diagnostic(tmp_path: Path) -> None:
    """Report only the safe parser type for untrusted malformed npm locks."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 4, "packages": {}}), encoding="utf-8"
    )
    _git(tmp_path, "add", "package-lock.json")
    _git(tmp_path, "commit", "-qm", "unsupported npm lock")

    records, diagnostics = collect_ref_facts(
        GitRepositoryReader(tmp_path), _git(tmp_path, "rev-parse", "HEAD"), RefRole.HEAD
    )

    assert not records
    assert diagnostics == ["head:package-lock.json: typed collection unavailable (ValueError)"]
    assert parse_manifest("package.json", "{}") == []
