"""Parse bounded JavaScript dependency metadata into normalized evidence facts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import urlsplit

from ocr_toolkit.common.redaction import redact_url_userinfo
from ocr_toolkit.evidence.ecosystems.contracts import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import EvidenceValue

_DECLARATION_SCOPES = (
    ("dependencies", "production"),
    ("devDependencies", "development"),
    ("peerDependencies", "peer"),
    ("optionalDependencies", "optional"),
)
_RUNTIME_ENGINES = frozenset({"node", "npm", "yarn", "pnpm"})
_PACKAGE_MANAGER_NAMES = frozenset({"npm", "yarn", "pnpm"})
_MAX_LOCK_TRAVERSAL_ITEMS = MAX_MANIFEST_ITEMS * 16
_MAX_LOCK_LINES = MAX_MANIFEST_ITEMS * 64


def _require_object(text: str, format_name: str) -> dict[str, object]:
    """Decode one JSON manifest and require its top-level object contract."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{format_name} must contain an object")
    return data


def _bounded_result(
    facts: list[ManifestFact], notices: list[str], format_name: str
) -> ManifestParseResult:
    """Cap JavaScript facts and retain one deterministic coverage notice."""

    if len(facts) > MAX_MANIFEST_ITEMS:
        notices.append(f"{format_name} facts were truncated after {MAX_MANIFEST_ITEMS} items")
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), tuple(dict.fromkeys(notices)))


def _runtime_fact(name: str, constraint: str, source: str) -> ManifestFact:
    """Create one runtime or package-manager constraint fact."""

    normalized_name = name.casefold()
    return ManifestFact(
        "runtime.declared",
        "javascript",
        normalized_name,
        {
            "name": normalized_name,
            "constraint": redact_url_userinfo(constraint),
            "source": source,
        },
    )


def _package_manager_fact(value: object) -> ManifestFact | None:
    """Parse the packageManager field without running Corepack or a resolver."""

    if not isinstance(value, str):
        return None
    name, separator, constraint = value.partition("@")
    normalized_name = name.casefold()
    if not separator or normalized_name not in _PACKAGE_MANAGER_NAMES or not constraint:
        return None
    return _runtime_fact(normalized_name, constraint, "packageManager")


def parse_package_json(text: str) -> ManifestParseResult:
    """Parse package.json engines and scoped dependency declarations."""

    data = _require_object(text, "package.json")
    facts: list[ManifestFact] = []
    notices: list[str] = []

    engines = data.get("engines")
    if isinstance(engines, dict):
        for name, constraint in sorted(engines.items()):
            if (
                isinstance(name, str)
                and name.casefold() in _RUNTIME_ENGINES
                and isinstance(constraint, str)
            ):
                facts.append(_runtime_fact(name, constraint, "engines"))

    if (manager_fact := _package_manager_fact(data.get("packageManager"))) is not None:
        facts.append(manager_fact)

    peer_metadata = data.get("peerDependenciesMeta")
    for section, scope in _DECLARATION_SCOPES:
        dependencies = data.get(section)
        if not isinstance(dependencies, dict):
            continue
        for name, constraint in sorted(dependencies.items()):
            if not isinstance(name, str) or not isinstance(constraint, str):
                continue
            value: dict[str, EvidenceValue] = {
                "name": name,
                "constraint": redact_url_userinfo(constraint),
                "scope": scope,
            }
            if scope == "peer" and isinstance(peer_metadata, dict):
                metadata = peer_metadata.get(name)
                if isinstance(metadata, dict) and isinstance(metadata.get("optional"), bool):
                    value["optional"] = metadata["optional"]
            facts.append(
                ManifestFact(
                    "dependency.declared",
                    "javascript",
                    f"{scope}:{name}",
                    value,
                )
            )

    return _bounded_result(facts, notices, "package.json")


def _lock_name(path: str, package: Mapping[str, object]) -> str | None:
    """Resolve an npm lock package name from metadata or a node_modules path."""

    declared_name = package.get("name")
    if isinstance(declared_name, str) and declared_name:
        return declared_name
    marker = "node_modules/"
    if marker not in path:
        return None
    candidate = path.rsplit(marker, 1)[1]
    return candidate if candidate else None


def _resolved_source(value: object) -> str | None:
    """Classify an npm resolved reference without persisting its full URL or path."""

    if not isinstance(value, str) or not value:
        return None
    lowered = value.casefold()
    if lowered.startswith(("git+", "git://")):
        return "vcs"
    if lowered.startswith(("file:", "link:")):
        return "local"
    if lowered.startswith(("http://", "https://")):
        return f"registry:{urlsplit(redact_url_userinfo(value)).hostname or 'unknown'}"
    return "other"


def _lock_fact(name: str, version: str, path: str, package: Mapping[str, object]) -> ManifestFact:
    """Create one npm resolved package fact with audit-relevant metadata."""

    value: dict[str, EvidenceValue] = {
        "name": name,
        "version": version,
        "scope": "npm",
        "path": path,
    }
    if (source := _resolved_source(package.get("resolved"))) is not None:
        value["source"] = source
    for key in ("integrity", "license"):
        item = package.get(key)
        if isinstance(item, str):
            value[key] = item
    for key in ("dev", "optional", "devOptional", "peer", "link"):
        item = package.get(key)
        if isinstance(item, bool):
            value[key] = item
    engines = package.get("engines")
    if isinstance(engines, dict):
        value["engines"] = {
            key: constraint
            for key, constraint in sorted(engines.items())
            if isinstance(key, str) and isinstance(constraint, str)
        }
    return ManifestFact(
        "dependency.locked",
        "javascript",
        f"npm:{path or name}",
        value,
    )


def _v1_lock_facts(dependencies: object) -> tuple[list[ManifestFact], bool]:
    """Flatten an npm v1 tree and report traversal-budget exhaustion."""

    if not isinstance(dependencies, dict):
        raise ValueError("package-lock.json v1 must contain a dependencies object")
    facts: list[ManifestFact] = []
    stack: list[tuple[str, object]] = [
        (f"node_modules/{name}", package)
        for name, package in sorted(dependencies.items(), reverse=True)
        if isinstance(name, str)
    ]
    traversed = 0
    while stack and len(facts) <= MAX_MANIFEST_ITEMS:
        if traversed >= _MAX_LOCK_TRAVERSAL_ITEMS:
            return facts, True
        path, raw_package = stack.pop()
        traversed += 1
        if not isinstance(raw_package, dict):
            continue
        name = _lock_name(path, raw_package)
        version = raw_package.get("version")
        if name is not None and isinstance(version, str):
            facts.append(_lock_fact(name, version, path, raw_package))
        nested = raw_package.get("dependencies")
        if isinstance(nested, dict):
            stack.extend(
                (f"{path}/node_modules/{child_name}", child_package)
                for child_name, child_package in sorted(nested.items(), reverse=True)
                if isinstance(child_name, str)
            )
    return facts, False


def parse_package_lock(text: str) -> ManifestParseResult:
    """Parse npm package-lock.json versions 1, 2, and 3."""

    data = _require_object(text, "package-lock.json")
    version = data.get("lockfileVersion")
    if isinstance(version, bool) or not isinstance(version, int) or version not in {1, 2, 3}:
        raise ValueError("package-lock.json lockfileVersion must be 1, 2, or 3")
    notices: list[str] = []
    if version == 1:
        facts, traversal_truncated = _v1_lock_facts(data.get("dependencies"))
        if traversal_truncated:
            notices.append(
                f"package-lock.json traversal was truncated after {_MAX_LOCK_TRAVERSAL_ITEMS} items"
            )
        return _bounded_result(facts, notices, "package-lock.json")

    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("package-lock.json must contain a packages object")
    facts = []
    for path, package in sorted(packages.items()):
        if not isinstance(path, str) or not path or not isinstance(package, dict):
            continue
        name = _lock_name(path, package)
        package_version = package.get("version")
        if name is None or not isinstance(package_version, str):
            continue
        facts.append(_lock_fact(name, package_version, path, package))
        if len(facts) > MAX_MANIFEST_ITEMS:
            break
    return _bounded_result(facts, notices, "package-lock.json")


def _unquote_yaml_scalar(value: str) -> str:
    """Decode the conservative quoted scalars emitted by JS lock writers."""

    clean = value.strip()
    if len(clean) >= 2 and clean[0] == clean[-1] == '"':
        try:
            decoded = json.loads(clean)
        except json.JSONDecodeError:
            return clean[1:-1]
        return decoded if isinstance(decoded, str) else clean
    if len(clean) >= 2 and clean[0] == clean[-1] == "'":
        return clean[1:-1].replace("''", "'")
    return clean


def _yarn_descriptor_name(descriptor: str) -> str | None:
    """Extract a package name from one Yarn descriptor or resolution."""

    clean = _unquote_yaml_scalar(descriptor).split(",", 1)[0].strip()
    if clean.startswith("@"):
        slash = clean.find("/")
        boundary = clean.find("@", slash + 1) if slash >= 0 else -1
        return clean[:boundary] if boundary > 0 else None
    boundary = clean.find("@")
    return clean[:boundary] if boundary > 0 else None


def _yarn_fact(
    descriptor: str, version: str, *, resolution: str | None, format_name: str
) -> ManifestFact | None:
    """Create one Yarn resolved fact while retaining the selector as provenance data."""

    name = _yarn_descriptor_name(descriptor)
    if name is None or not version:
        return None
    value: dict[str, EvidenceValue] = {
        "name": name,
        "version": version,
        "scope": format_name,
        "descriptor": _unquote_yaml_scalar(descriptor),
    }
    if resolution is not None:
        value["source"] = (
            "npm" if "@npm:" in resolution else _resolved_source(resolution) or "other"
        )
    return ManifestFact(
        "dependency.locked",
        "javascript",
        f"{format_name}:{_unquote_yaml_scalar(descriptor)}",
        value,
    )


def parse_yarn_lock(text: str) -> ManifestParseResult:
    """Parse bounded Yarn Classic and Modern generated lock entries."""

    lines = text.splitlines()
    if not lines or len(lines) > _MAX_LOCK_LINES:
        raise ValueError("yarn.lock exceeds the supported line budget")
    classic = any("yarn lockfile v1" in line for line in lines[:8])
    modern = any(line.strip() == "__metadata:" for line in lines[:16])
    if not classic and not modern:
        raise ValueError("yarn.lock format is unsupported")
    format_name = "yarn-classic" if classic else "yarn-modern"
    facts: list[ManifestFact] = []
    notices: list[str] = []
    descriptor: str | None = None
    version: str | None = None
    resolution: str | None = None

    def finish_entry() -> None:
        """Flush one bounded top-level Yarn lock entry."""

        nonlocal descriptor, version, resolution
        if descriptor is not None and version is not None:
            fact = _yarn_fact(descriptor, version, resolution=resolution, format_name=format_name)
            if fact is not None:
                facts.append(fact)
        descriptor = version = resolution = None

    saw_metadata_version = False
    for line in lines:
        if line and not line[0].isspace() and line.rstrip().endswith(":"):
            finish_entry()
            candidate = line.rstrip()[:-1]
            if candidate != "__metadata":
                descriptor = candidate
            continue
        if descriptor is None:
            if not classic and line.startswith("  version:"):
                metadata_version = _unquote_yaml_scalar(line.partition(":")[2])
                if not metadata_version.isdigit():
                    raise ValueError("yarn.lock metadata version must be numeric")
                saw_metadata_version = True
            continue
        stripped = line.strip()
        if classic and stripped.startswith("version "):
            version = _unquote_yaml_scalar(stripped.removeprefix("version ").strip())
        elif classic and stripped.startswith("resolved "):
            resolution = _unquote_yaml_scalar(stripped.removeprefix("resolved ").strip())
        elif not classic and stripped.startswith("version:"):
            version = _unquote_yaml_scalar(stripped.partition(":")[2])
        elif not classic and stripped.startswith("resolution:"):
            resolution = _unquote_yaml_scalar(stripped.partition(":")[2])
        if len(facts) > MAX_MANIFEST_ITEMS:
            break
    finish_entry()
    if modern and not saw_metadata_version:
        raise ValueError("yarn.lock must declare a metadata version")
    return _bounded_result(facts, notices, "yarn.lock")


def _pnpm_package_key(value: str) -> tuple[str, str] | None:
    """Decode common pnpm v5-v9 package keys without interpreting YAML."""

    clean = _unquote_yaml_scalar(value).removeprefix("/")
    clean = clean.split("(", 1)[0]
    if clean.startswith("@"):
        boundary = clean.rfind("@")
        if boundary > clean.find("/"):
            return clean[:boundary], clean[boundary + 1 :]
        parts = clean.split("/")
        if len(parts) >= 3:
            return f"{parts[0]}/{parts[1]}", parts[2]
        return None
    boundary = clean.rfind("@")
    if boundary > 0:
        return clean[:boundary], clean[boundary + 1 :]
    parts = clean.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def parse_pnpm_lock(text: str) -> ManifestParseResult:
    """Parse bounded pnpm package snapshots from lockfile versions 5 through 9."""

    lines = text.splitlines()
    if not lines or len(lines) > _MAX_LOCK_LINES:
        raise ValueError("pnpm-lock.yaml exceeds the supported line budget")
    lock_version: str | None = None
    for line in lines[:32]:
        if line.startswith("lockfileVersion:"):
            lock_version = _unquote_yaml_scalar(line.partition(":")[2])
            break
    if lock_version is None:
        raise ValueError("pnpm-lock.yaml must declare lockfileVersion")
    try:
        major = int(lock_version.split(".", 1)[0])
    except ValueError as error:
        raise ValueError("pnpm lockfileVersion must be numeric") from error
    if major not in {5, 6, 7, 8, 9}:
        raise ValueError(f"unsupported pnpm lockfileVersion: {major}")

    facts: list[ManifestFact] = []
    notices: list[str] = []
    top_level_sections = {
        line.partition(":")[0]
        for line in lines
        if line and not line[0].isspace() and line.endswith(":")
    }
    selected_section = "packages" if "packages" in top_level_sections else "snapshots"
    if selected_section not in top_level_sections:
        raise ValueError("pnpm-lock.yaml must contain packages or snapshots")
    in_packages = False
    for line in lines:
        if line and not line[0].isspace():
            section = line.partition(":")[0]
            in_packages = section == selected_section
            continue
        if not in_packages:
            continue
        indent = len(line) - len(line.lstrip())
        if indent != 2:
            continue
        candidate = line.strip()
        if not candidate.endswith(":"):
            continue
        parsed = _pnpm_package_key(candidate[:-1])
        if parsed is None:
            continue
        name, version = parsed
        identity = f"pnpm:{candidate[:-1]}"
        facts.append(
            ManifestFact(
                "dependency.locked",
                "javascript",
                identity,
                {"name": name, "version": version, "scope": "pnpm"},
            )
        )
        if len(facts) > MAX_MANIFEST_ITEMS:
            break
    return _bounded_result(facts, notices, "pnpm-lock.yaml")
