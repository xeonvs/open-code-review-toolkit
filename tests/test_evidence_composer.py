"""Composer declaration, lock, delta, and MCP evidence tests."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors import collect_ref_facts, manifest_collector
from ocr_toolkit.evidence.ecosystems.contracts import MAX_MANIFEST_ITEMS, ManifestParseResult
from ocr_toolkit.evidence.ecosystems.php import parse_composer_json, parse_composer_lock
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


def test_composer_json_preserves_packages_platforms_and_resolution_policy() -> None:
    """Model root identity, link scopes, platform overrides, and preferences."""

    parsed = parse_composer_json(
        json.dumps(
            {
                "name": "acme/service",
                "type": "project",
                "require": {
                    "php": "^8.3",
                    "ext-json": "*",
                    "vendor/runtime": "^1.2",
                },
                "require-dev": {"vendor/tester": "^2.0"},
                "provide": {"virtual/interface": "1.0"},
                "replace": {"legacy/package": "self.version"},
                "conflict": {"unsafe/package": "<3.0"},
                "config": {"platform": {"php": "8.3.7", "ext-intl": "1.0"}},
                "minimum-stability": "beta",
                "prefer-stable": True,
                "prefer-lowest": False,
            }
        )
    )

    manifests = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "repository.manifest"
    }
    assert manifests["composer:package"] == {
        "manifest_type": "composer.package",
        "name": "acme/service",
        "package_type": "project",
    }
    assert manifests["composer:resolution"] == {
        "manifest_type": "composer.resolution",
        "minimum_stability": "beta",
        "prefer_stable": True,
        "prefer_lowest": False,
    }
    declarations = {
        fact.identity: fact for fact in parsed.facts if fact.kind == "dependency.declared"
    }
    assert declarations["production:vendor/runtime"].value["constraint"] == "^1.2"
    assert declarations["development:vendor/tester"].value["scope"] == "development"
    assert declarations["provide:virtual/interface"].value["constraint"] == "1.0"
    assert declarations["replace:legacy/package"].value["constraint"] == "self.version"
    assert declarations["conflict:unsafe/package"].value["constraint"] == "<3.0"
    runtimes = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "runtime.declared"
    }
    assert runtimes["production:php"] == {
        "name": "php",
        "constraint": "^8.3",
        "scope": "production",
        "platform": True,
    }
    assert runtimes["production:ext-json"]["platform"] is True
    assert runtimes["platform-override:php"]["constraint"] == "8.3.7"
    assert runtimes["platform-override:ext-intl"]["constraint"] == "1.0"


def test_composer_repositories_are_classified_without_credentials() -> None:
    """Do not persist repository-controlled URL credentials or path contents."""

    parsed = parse_composer_json(
        json.dumps(
            {
                "repositories": [
                    {
                        "type": "vcs",
                        "url": "https://user:secret@packages.example.invalid/repo",
                    },
                    {"type": "path", "url": "../private-component"},
                ]
            }
        )
    )

    values = [fact.value for fact in parsed.facts]
    assert values == [
        {
            "manifest_type": "composer.repository",
            "source": "vcs:packages.example.invalid",
        },
        {"manifest_type": "composer.repository", "source": "path:local"},
    ]
    assert "secret" not in json.dumps(values)
    assert "private-component" not in json.dumps(values)


def test_composer_json_isolates_bad_repository_urls_and_disabled_platforms() -> None:
    """Keep valid manifest facts when optional URLs are malformed or platforms hidden."""

    parsed = parse_composer_json(
        json.dumps(
            {
                "require": {"vendor/runtime": "^1.2"},
                "repositories": [{"type": "vcs", "url": "https://[invalid/repository"}],
                "config": {"platform": {"php": "8.3.0", "ext-xdebug": False}},
            }
        )
    )

    facts = {fact.identity: fact for fact in parsed.facts}
    assert facts["production:vendor/runtime"].value["constraint"] == "^1.2"
    assert facts["composer:repository:index-0"].value["source"] == "vcs"
    assert facts["platform-override:php"].value["constraint"] == "8.3.0"
    assert facts["platform-override:ext-xdebug"].component == "php"
    assert facts["platform-override:ext-xdebug"].value["constraint"] is False

    named = parse_composer_json(
        json.dumps(
            {
                "repositories": {
                    "internal": {
                        "type": "composer",
                        "url": "https://packages.example.invalid/index",
                    }
                }
            }
        )
    )
    assert named.facts[0].identity == "composer:repository:internal"
    assert named.facts[0].value["source"] == "composer:packages.example.invalid"


def test_composer_virtual_platform_package_set_matches_schema_semantics() -> None:
    """Treat Composer, HHVM, extensions, and libraries as runtime platform facts."""

    parsed = parse_composer_json(
        json.dumps(
            {
                "require": {
                    "composer": "^2.8",
                    "composer-runtime-api": "^2.2",
                    "composer-plugin-api": "^2.6",
                    "php-debug": "8.3",
                    "php-zts": "8.3",
                    "hhvm": "^4",
                    "lib-icu": ">=72",
                }
            }
        )
    )

    assert {fact.kind for fact in parsed.facts} == {"runtime.declared"}
    assert {fact.identity for fact in parsed.facts} == {
        "production:composer",
        "production:composer-runtime-api",
        "production:composer-plugin-api",
        "production:php-debug",
        "production:php-zts",
        "production:hhvm",
        "production:lib-icu",
    }


def test_composer_lock_preserves_packages_platforms_and_metadata() -> None:
    """Keep production/development locks, references, platforms, and lock identity."""

    parsed = parse_composer_lock(
        json.dumps(
            {
                "content-hash": "synthetic-content-hash",
                "plugin-api-version": "2.6.0",
                "minimum-stability": "stable",
                "prefer-stable": True,
                "prefer-lowest": False,
                "packages": [
                    {
                        "name": "vendor/runtime",
                        "version": "1.2.3",
                        "type": "library",
                        "time": "2026-07-01T00:00:00+00:00",
                        "source": {
                            "type": "git",
                            "url": "https://user:secret@example.invalid/runtime.git",
                            "reference": "0123456789abcdef",
                        },
                        "dist": {
                            "type": "zip",
                            "url": "https://token@example.invalid/archive.zip",
                            "reference": "0123456789abcdef",
                        },
                    }
                ],
                "packages-dev": [{"name": "vendor/tester", "version": "2.0.1"}],
                "platform": {"php": "^8.3", "ext-json": "*"},
                "platform-dev": {"ext-xdebug": "*"},
            }
        )
    )

    metadata = next(fact.value for fact in parsed.facts if fact.identity == "composer:lock")
    assert metadata == {
        "manifest_type": "composer.lock",
        "content_hash": "synthetic-content-hash",
        "plugin_api_version": "2.6.0",
        "minimum_stability": "stable",
        "prefer_stable": True,
        "prefer_lowest": False,
    }
    packages = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "dependency.locked"
    }
    assert packages["production:vendor/runtime"] == {
        "name": "vendor/runtime",
        "version": "1.2.3",
        "scope": "production",
        "package_type": "library",
        "time": "2026-07-01T00:00:00+00:00",
        "source_reference": "0123456789abcdef",
        "dist_reference": "0123456789abcdef",
        "source": "vcs",
    }
    assert packages["development:vendor/tester"]["scope"] == "development"
    runtimes = {
        fact.identity: fact.value for fact in parsed.facts if fact.kind == "runtime.declared"
    }
    assert runtimes["locked-platform:php"]["constraint"] == "^8.3"
    assert runtimes["locked-platform-dev:ext-xdebug"]["constraint"] == "*"
    serialized = json.dumps([fact.value for fact in parsed.facts])
    assert "secret" not in serialized
    assert "token@example" not in serialized


def test_composer_parsers_apply_aggregate_bounds_and_safe_notices() -> None:
    """Bound all formats once and report malformed lock entries without payloads."""

    composer_json = parse_composer_json(
        json.dumps(
            {
                "require": {
                    f"vendor/package-{index:04d}": "1.0.0"
                    for index in range(MAX_MANIFEST_ITEMS + 1)
                }
            }
        )
    )
    composer_lock = parse_composer_lock(
        json.dumps(
            {
                "packages": [
                    {"name": f"vendor/package-{index:04d}", "version": "1.0.0"}
                    for index in range(MAX_MANIFEST_ITEMS + 1)
                ],
                "packages-dev": [{"secret": "must-not-leak"}],
            }
        )
    )

    assert len(composer_json.facts) == MAX_MANIFEST_ITEMS
    assert composer_json.notices == (
        f"composer.json facts were truncated after {MAX_MANIFEST_ITEMS} items",
    )
    assert len(composer_lock.facts) == MAX_MANIFEST_ITEMS
    assert composer_lock.notices == (
        "composer.lock skipped malformed development package entry",
        f"composer.lock facts were truncated after {MAX_MANIFEST_ITEMS} items",
    )
    assert "must-not-leak" not in " ".join(composer_lock.notices)


@pytest.mark.parametrize(
    ("parser", "format_name"),
    [(parse_composer_json, "composer.json"), (parse_composer_lock, "composer.lock")],
)
def test_composer_parsers_reject_non_object_roots(
    parser: Callable[[str], ManifestParseResult], format_name: str
) -> None:
    """Reject syntactically valid non-object manifests as unavailable evidence."""

    with pytest.raises(ValueError, match=rf"{format_name} must contain an object"):
        parser("[]")


def test_composer_deltas_and_builtin_mcp_preserve_resolved_changes(tmp_path: Path) -> None:
    """Expose declaration and lock upgrades as changed facts through MCP."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")

    def write_state(constraint: str, version: str) -> None:
        """Write one synthetic Composer manifest and matching lock state."""

        (tmp_path / "composer.json").write_text(
            json.dumps({"require": {"php": "^8.3", "vendor/demo": constraint}}),
            encoding="utf-8",
        )
        (tmp_path / "composer.lock").write_text(
            json.dumps(
                {
                    "content-hash": f"hash-{version}",
                    "packages": [{"name": "vendor/demo", "version": version}],
                    "packages-dev": [],
                }
            ),
            encoding="utf-8",
        )

    write_state("^1.0", "1.0.0")
    _git(tmp_path, "add", "composer.json", "composer.lock")
    _git(tmp_path, "commit", "-qm", "base Composer evidence")
    base = _git(tmp_path, "rev-parse", "HEAD")
    write_state("^2.0", "2.0.0")
    _git(tmp_path, "add", "composer.json", "composer.lock")
    _git(tmp_path, "commit", "-qm", "head Composer evidence")
    head = _git(tmp_path, "rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    package_deltas = [delta for delta in store.deltas if delta.component == "php"]
    declared = next(delta for delta in package_deltas if delta.kind == "dependency.declared")
    locked = next(delta for delta in package_deltas if delta.kind == "dependency.locked")
    assert declared.change == "changed"
    assert declared.before["constraint"] == "^1.0"
    assert declared.after["constraint"] == "^2.0"
    assert locked.change == "changed"
    assert locked.before["version"] == "1.0.0"
    assert locked.after["version"] == "2.0.0"

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
                    "component": "php",
                    "ref": "head",
                },
            },
        },
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert {record["kind"] for record in payload["records"]} >= {
        "repository.manifest",
        "runtime.declared",
        "dependency.declared",
        "dependency.locked",
    }


def test_composer_malformed_lock_is_diagnostic_but_missing_lock_is_absence(
    tmp_path: Path,
) -> None:
    """Distinguish a present malformed lock from a repository without one."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")
    (tmp_path / "composer.json").write_text(
        json.dumps({"require": {"vendor/demo": "^1.0"}}), encoding="utf-8"
    )
    _git(tmp_path, "add", "composer.json")
    _git(tmp_path, "commit", "-qm", "Composer declarations without lock")
    reader = GitRepositoryReader(tmp_path)
    records, diagnostics = collect_ref_facts(
        reader, _git(tmp_path, "rev-parse", "HEAD"), RefRole.HEAD
    )
    assert diagnostics == []
    assert not any(record.kind == "dependency.locked" for record in records)

    (tmp_path / "composer.lock").write_text("{invalid-secret", encoding="utf-8")
    _git(tmp_path, "add", "composer.lock")
    _git(tmp_path, "commit", "-qm", "malformed Composer lock")
    records, diagnostics = collect_ref_facts(
        reader, _git(tmp_path, "rev-parse", "HEAD"), RefRole.HEAD
    )
    assert diagnostics == ["head:composer.lock: typed collection unavailable (JSONDecodeError)"]
    assert manifest_collector("services/app/composer.lock").ecosystem == "php"
