"""Parse bounded Composer declarations and lock metadata into normalized facts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import urlsplit

from ocr_toolkit.common.redaction import redact_url_userinfo
from ocr_toolkit.evidence.manifest_model import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import EvidenceValue

_PLATFORM_PREFIXES = ("ext-", "lib-", "composer-")
_COMPOSER_PLATFORM_NAMES = frozenset({"php", "php-64bit", "php-ipv6", "hhvm", "composer"})
_SOURCE_TYPES = frozenset({"git", "hg", "fossil", "svn"})


def _object(text: str, format_name: str) -> dict[str, object]:
    """Decode one Composer JSON object with a format-specific error contract."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{format_name} must contain an object")
    return data


def _bounded_result(
    facts: list[ManifestFact], notices: list[str], format_name: str
) -> ManifestParseResult:
    """Apply one aggregate fact limit and deterministic coverage notices."""

    if len(facts) > MAX_MANIFEST_ITEMS:
        notices.append(f"{format_name} facts were truncated after {MAX_MANIFEST_ITEMS} items")
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), tuple(dict.fromkeys(notices)))


def _constraint(value: object) -> str | None:
    """Return Composer's scalar constraint forms without accepting containers."""

    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _package_name(name: str) -> str:
    """Normalize Composer package identity case-insensitively."""

    return name.casefold()


def _is_platform_package(name: str) -> bool:
    """Identify Composer virtual platform packages."""

    normalized = _package_name(name)
    return normalized in _COMPOSER_PLATFORM_NAMES or normalized.startswith(_PLATFORM_PREFIXES)


def _declared_fact(name: str, raw_constraint: object, scope: str) -> ManifestFact | None:
    """Create one package or platform declaration with a stable scoped identity."""

    constraint = _constraint(raw_constraint)
    if not name or constraint is None:
        return None
    value: dict[str, EvidenceValue] = {
        "name": name,
        "constraint": constraint,
        "scope": scope,
    }
    if _is_platform_package(name):
        value["platform"] = True
    return ManifestFact(
        "runtime.declared" if _is_platform_package(name) else "dependency.declared",
        "php",
        f"{scope}:{_package_name(name)}",
        value,
    )


def _mapping_facts(data: object, scope: str) -> list[ManifestFact]:
    """Normalize one Composer link mapping in deterministic name order."""

    if not isinstance(data, Mapping):
        return []
    facts: list[ManifestFact] = []
    for raw_name, raw_constraint in sorted(data.items(), key=lambda item: str(item[0]).casefold()):
        if isinstance(raw_name, str):
            fact = _declared_fact(raw_name, raw_constraint, scope)
            if fact is not None:
                facts.append(fact)
    return facts


def _repository_identity(data: Mapping[str, object]) -> str | None:
    """Classify repository transport without persisting a credential-bearing URL."""

    repository_type = data.get("type")
    url = data.get("url")
    if not isinstance(repository_type, str):
        return None
    classification = repository_type.casefold()
    if isinstance(url, str):
        safe_url = redact_url_userinfo(url)
        parsed = urlsplit(safe_url)
        if parsed.hostname:
            classification = f"{classification}:{parsed.hostname.casefold()}"
        elif safe_url.startswith(("./", "../", "/")):
            classification = f"{classification}:local"
    return classification


def _repository_facts(data: object) -> list[ManifestFact]:
    """Represent configured repositories as safe transport classifications."""

    if data is None:
        return []
    if isinstance(data, Mapping):
        entries: list[object] = [
            ({**entry, "name": name} if isinstance(entry, Mapping) else entry)
            for name, entry in sorted(data.items(), key=lambda item: str(item[0]).casefold())
        ]
    elif isinstance(data, list):
        entries = data
    else:
        return []
    facts: list[ManifestFact] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            continue
        classification = _repository_identity(entry)
        if classification is None:
            continue
        name = entry.get("name")
        identity = str(name).casefold() if isinstance(name, str) else f"index-{index}"
        facts.append(
            ManifestFact(
                "repository.manifest",
                "php",
                f"composer:repository:{identity}",
                {"manifest_type": "composer.repository", "source": classification},
            )
        )
    return facts


def _root_metadata(data: Mapping[str, object]) -> list[ManifestFact]:
    """Preserve root identity and dependency-resolution preferences."""

    facts: list[ManifestFact] = []
    name = data.get("name")
    package_type = data.get("type")
    if isinstance(name, str):
        value: dict[str, EvidenceValue] = {
            "manifest_type": "composer.package",
            "name": name,
        }
        if isinstance(package_type, str):
            value["package_type"] = package_type
        facts.append(ManifestFact("repository.manifest", "php", "composer:package", value))
    resolution: dict[str, EvidenceValue] = {"manifest_type": "composer.resolution"}
    for key in ("minimum-stability", "prefer-stable", "prefer-lowest"):
        item = data.get(key)
        if isinstance(item, (str, bool)):
            resolution[key.replace("-", "_")] = item
    if len(resolution) > 1:
        facts.append(ManifestFact("repository.manifest", "php", "composer:resolution", resolution))
    return facts


def parse_composer_json(text: str) -> ManifestParseResult:
    """Parse composer.json links, platform overrides, repositories, and preferences."""

    data = _object(text, "composer.json")
    facts = _root_metadata(data)
    for key, scope in (
        ("require", "production"),
        ("require-dev", "development"),
        ("provide", "provide"),
        ("replace", "replace"),
        ("conflict", "conflict"),
    ):
        facts.extend(_mapping_facts(data.get(key), scope))
    config = data.get("config")
    if isinstance(config, Mapping):
        facts.extend(_mapping_facts(config.get("platform"), "platform-override"))
    facts.extend(_repository_facts(data.get("repositories")))
    return _bounded_result(facts, [], "composer.json")


def _source_classification(package: Mapping[str, object]) -> str | None:
    """Classify one locked package source without storing its repository URL."""

    source_type = package.get("source")
    if isinstance(source_type, Mapping):
        source_type = source_type.get("type")
    if not isinstance(source_type, str):
        dist = package.get("dist")
        if isinstance(dist, Mapping):
            source_type = dist.get("type")
    if not isinstance(source_type, str):
        return None
    normalized = source_type.casefold()
    return "vcs" if normalized in _SOURCE_TYPES else normalized


def _locked_package(package: object, scope: str) -> ManifestFact | None:
    """Create one locked Composer package fact with safe resolution metadata."""

    if not isinstance(package, Mapping):
        return None
    name = package.get("name")
    version = package.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        return None
    value: dict[str, EvidenceValue] = {
        "name": name,
        "version": version,
        "scope": scope,
    }
    for key in ("type", "time"):
        item = package.get(key)
        if isinstance(item, str):
            value["package_type" if key == "type" else key] = item
    for key in ("source", "dist"):
        item = package.get(key)
        if not isinstance(item, Mapping):
            continue
        reference = item.get("reference")
        if isinstance(reference, str):
            value[f"{key}_reference"] = reference
    if (source := _source_classification(package)) is not None:
        value["source"] = source
    return ManifestFact(
        "dependency.locked",
        "php",
        f"{scope}:{_package_name(name)}",
        value,
    )


def _lock_metadata(data: Mapping[str, object]) -> list[ManifestFact]:
    """Preserve deterministic lock identity and resolution metadata."""

    value: dict[str, EvidenceValue] = {"manifest_type": "composer.lock"}
    for key in ("content-hash", "plugin-api-version"):
        item = data.get(key)
        if isinstance(item, str):
            value[key.replace("-", "_")] = item
    for key in ("minimum-stability", "prefer-stable", "prefer-lowest"):
        item = data.get(key)
        if isinstance(item, (str, bool)):
            value[key.replace("-", "_")] = item
    return (
        [ManifestFact("repository.manifest", "php", "composer:lock", value)]
        if len(value) > 1
        else []
    )


def parse_composer_lock(text: str) -> ManifestParseResult:
    """Parse composer.lock resolved packages, platforms, and lock metadata."""

    data = _object(text, "composer.lock")
    facts = _lock_metadata(data)
    notices: list[str] = []
    for key, scope in (("packages", "production"), ("packages-dev", "development")):
        packages = data.get(key)
        if packages is None:
            continue
        if not isinstance(packages, list):
            notices.append(f"composer.lock ignored non-array {key}")
            continue
        for package in packages:
            fact = _locked_package(package, scope)
            if fact is None:
                notices.append(f"composer.lock skipped malformed {scope} package entry")
            else:
                facts.append(fact)
    facts.extend(_mapping_facts(data.get("platform"), "locked-platform"))
    facts.extend(_mapping_facts(data.get("platform-dev"), "locked-platform-dev"))
    return _bounded_result(facts, notices, "composer.lock")
