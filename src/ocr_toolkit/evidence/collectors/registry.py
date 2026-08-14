"""Register bounded manifest adapters without owning immutable Git reads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

from ocr_toolkit.evidence.ecosystems.ansible.requirements import parse_galaxy_requirements
from ocr_toolkit.evidence.ecosystems.contracts import (
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.ecosystems.go import parse_go_mod, parse_go_sum
from ocr_toolkit.evidence.ecosystems.javascript import (
    parse_package_json,
    parse_package_lock,
    parse_pnpm_lock,
    parse_yarn_lock,
)
from ocr_toolkit.evidence.ecosystems.php import parse_composer_json, parse_composer_lock
from ocr_toolkit.evidence.ecosystems.python import (
    parse_pipfile_lock,
    parse_poetry_lock,
    parse_pylock,
    parse_pyproject,
    parse_requirements,
    parse_uv_lock,
)
from ocr_toolkit.evidence.model import EvidenceValue


@dataclass(frozen=True, slots=True)
class ManifestCollector:
    """Bind manifest path matching, ecosystem metadata, role, and bounded parser."""

    ecosystem: str
    source_roles: tuple[str, ...]
    matches: Callable[[str], bool]
    parse: Callable[[str], ManifestParseResult]


def _parse_ansible_requirements(text: str) -> ManifestParseResult:
    """Parse Galaxy roles and collections while preserving optional fields."""

    parsed = parse_galaxy_requirements(text)
    facts = []
    for item in parsed.requirements:
        value: dict[str, EvidenceValue] = {
            "name": item.name,
            "requirement_type": item.requirement_type,
            "scope": item.requirement_type,
            "version": item.version,
            "version_state": "declared" if item.version is not None else "unspecified",
        }
        if item.source is not None:
            value["source"] = item.source
        facts.append(
            ManifestFact(
                "dependency.declared",
                "ansible",
                f"{item.requirement_type}:{item.name.casefold()}",
                value,
            )
        )
    return ManifestParseResult(tuple(facts), parsed.notices, parsed.include_paths)


def _name_is(*names: str) -> Callable[[str], bool]:
    """Build a case-insensitive basename matcher for the manifest registry."""

    normalized = frozenset(name.casefold() for name in names)
    return lambda path: PurePosixPath(path).name.casefold() in normalized


def is_python_requirements(path: str) -> bool:
    """Match Python requirement manifests without matching Ansible YAML."""

    name = PurePosixPath(path).name.casefold()
    return name.startswith("requirements") and name.endswith((".txt", ".in"))


def _is_pylock(path: str) -> bool:
    """Match the standardized pylock.toml name and its permitted variants."""

    name = PurePosixPath(path).name.casefold()
    return name == "pylock.toml" or (name.startswith("pylock.") and name.endswith(".toml"))


MANIFEST_COLLECTORS = (
    ManifestCollector("python", ("declaration",), _name_is("pyproject.toml"), parse_pyproject),
    ManifestCollector("python", ("declaration",), is_python_requirements, parse_requirements),
    ManifestCollector("python", ("resolution",), _name_is("uv.lock"), parse_uv_lock),
    ManifestCollector("python", ("resolution",), _name_is("poetry.lock"), parse_poetry_lock),
    ManifestCollector("python", ("resolution",), _name_is("Pipfile.lock"), parse_pipfile_lock),
    ManifestCollector("python", ("resolution",), _is_pylock, parse_pylock),
    ManifestCollector("javascript", ("declaration",), _name_is("package.json"), parse_package_json),
    ManifestCollector(
        "javascript",
        ("resolution",),
        _name_is("package-lock.json"),
        parse_package_lock,
    ),
    ManifestCollector("javascript", ("resolution",), _name_is("yarn.lock"), parse_yarn_lock),
    ManifestCollector("javascript", ("resolution",), _name_is("pnpm-lock.yaml"), parse_pnpm_lock),
    ManifestCollector("go", ("declaration", "resolution"), _name_is("go.mod"), parse_go_mod),
    ManifestCollector("go", ("checksum",), _name_is("go.sum"), parse_go_sum),
    ManifestCollector("php", ("declaration",), _name_is("composer.json"), parse_composer_json),
    ManifestCollector("php", ("resolution",), _name_is("composer.lock"), parse_composer_lock),
    ManifestCollector(
        "ansible",
        ("declaration",),
        _name_is("requirements.yml", "requirements.yaml"),
        _parse_ansible_requirements,
    ),
)


def manifest_collector(path: str) -> ManifestCollector | None:
    """Return the single registered collector for a repository path."""

    matches = tuple(collector for collector in MANIFEST_COLLECTORS if collector.matches(path))
    if len(matches) > 1:
        raise ValueError(f"manifest registry has ambiguous collectors for {path}")
    return matches[0] if matches else None


def parse_manifest(path: str, text: str) -> list[ManifestFact]:
    """Parse a supported manifest through the authoritative collector registry."""

    collector = manifest_collector(path)
    return list(collector.parse(text).facts) if collector else []


def is_supported_manifest(path: str) -> bool:
    """Return whether a repository path has a registered typed parser."""

    return manifest_collector(path) is not None
