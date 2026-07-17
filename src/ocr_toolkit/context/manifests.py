"""Dependency manifest parsers for OCR context."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ocr_toolkit.common.redaction import redact_url_userinfo
from ocr_toolkit.context import repo as context_repo
from ocr_toolkit.context.settings import (
    DEFAULT_MANIFEST_PARSE_MAX_BYTES,
    JSON_OBJECT_PARSE_ERROR,
    MAX_BACKGROUND_SECTION_ITEMS,
    MAX_MANIFEST_PARSE_MAX_BYTES,
    getenv_int,
)


@dataclass(frozen=True)
class ManifestPathDiscovery:
    """Bounded manifest path discovery result."""

    paths: list[str]
    omitted: int = 0


def read_manifest_text(path: Path) -> tuple[str | None, str | None]:
    """Read a manifest after enforcing an explicit size budget."""

    safe_path = context_repo.resolve_repo_file(path)
    if safe_path is None:
        return None, "file is not a regular repository file"

    max_bytes = getenv_int(
        "OCR_MANIFEST_PARSE_MAX_BYTES",
        DEFAULT_MANIFEST_PARSE_MAX_BYTES,
        max_value=MAX_MANIFEST_PARSE_MAX_BYTES,
    )

    try:
        if safe_path.stat().st_size > max_bytes:
            return None, f"file exceeds OCR_MANIFEST_PARSE_MAX_BYTES ({max_bytes} bytes)"
        return safe_path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, str(exc)


def limited_manifest_items(items: list[str]) -> tuple[list[str], int]:
    """Return bounded manifest items plus the real omitted count."""

    return (
        items[:MAX_BACKGROUND_SECTION_ITEMS],
        max(0, len(items) - MAX_BACKGROUND_SECTION_ITEMS),
    )


def discover_pyproject_paths(
    changed: Sequence[str], limit: int = 20, max_depth: int = 40
) -> ManifestPathDiscovery:
    """Find pyproject.toml manifests relevant to this MR.

    Returns:
    - the repository root manifest, if any;
    - every changed `pyproject.toml` (so a manifest-only edit still
      gets its constraints into the background);
    - the nearest existing `pyproject.toml` walking up the directory
      tree from each changed Python file.

    The walk is bounded by `max_depth` steps and by fixed-point
    detection on `Path.parent`. Absolute paths and inputs that escape
    ROOT are rejected so a future caller cannot deadlock CI or probe
    manifests outside the repository.
    """

    if limit <= 0:
        return ManifestPathDiscovery([], 0)

    found: dict[str, None] = {}
    overflow_seen: set[str] = set()
    root_resolved = context_repo.ROOT.resolve()
    root_present = context_repo.path_exists("pyproject.toml")
    effective_limit = max(1, limit) if root_present else limit

    if root_present:
        found["pyproject.toml"] = None

    # Treat changed pyproject.toml paths as relevant directly.
    for rel in changed:
        if Path(rel).name == "pyproject.toml" and context_repo.path_exists(rel):
            if len(found) < effective_limit:
                found[rel] = None
            elif rel not in found:
                overflow_seen.add(rel)

    for rel in changed:
        if not rel.endswith((".py", ".pyi")):
            continue
        candidate_path = Path(rel)
        if candidate_path.is_absolute():
            continue

        cursor = candidate_path.parent
        steps = 0
        while steps < max_depth:
            candidate = cursor / "pyproject.toml"
            # Guard against probing outside ROOT (defence-in-depth in
            # case a malformed relative path resolves above repo root).
            try:
                resolved = (context_repo.ROOT / candidate).resolve()
                resolved.relative_to(root_resolved)
            except (OSError, ValueError):
                break

            if context_repo.path_exists(str(candidate)):
                if len(found) < effective_limit:
                    found[str(candidate)] = None
                elif str(candidate) not in found:
                    overflow_seen.add(str(candidate))
                # Nearest manifest is enough — outer manifests rarely
                # change the answer for a nested package.
                break

            parent = cursor.parent
            if parent == cursor:  # fixed point: walked off the tree
                break
            cursor = parent
            steps += 1

    return ManifestPathDiscovery(list(found)[:effective_limit], len(overflow_seen))


def discover_package_json_paths(
    changed: Sequence[str], limit: int = 20, max_depth: int = 40
) -> ManifestPathDiscovery:
    """Find package.json manifests relevant to changed JS/TS files."""

    found: dict[str, None] = {}
    overflow_seen: set[str] = set()
    root_resolved = context_repo.ROOT.resolve()

    if context_repo.path_exists("package.json"):
        found["package.json"] = None

    for rel in changed:
        if Path(rel).name == "package.json" and context_repo.path_exists(rel):
            if len(found) < limit:
                found.setdefault(rel, None)
            elif rel not in found:
                overflow_seen.add(rel)

    for rel in changed:
        if not rel.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            continue
        candidate_path = Path(rel)
        if candidate_path.is_absolute():
            continue

        cursor = candidate_path.parent
        steps = 0
        while steps < max_depth:
            candidate = cursor / "package.json"
            try:
                resolved = (context_repo.ROOT / candidate).resolve()
                resolved.relative_to(root_resolved)
            except (OSError, ValueError):
                break

            if context_repo.path_exists(str(candidate)):
                rel_candidate = str(candidate)
                if len(found) < limit:
                    found.setdefault(rel_candidate, None)
                elif rel_candidate not in found:
                    overflow_seen.add(rel_candidate)
                break

            parent = cursor.parent
            if parent == cursor:
                break
            cursor = parent
            steps += 1

    return ManifestPathDiscovery(list(found)[:limit], len(overflow_seen))


def parse_pyproject(path: Path) -> dict[str, Any]:
    """Parse Python dependency metadata from pyproject.toml."""

    text, parse_error = read_manifest_text(path)
    if parse_error:
        return {"present": True, "parse_error": parse_error}
    if not text:
        return {"requires_python": None, "dependencies": []}

    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[import-not-found]

        data = tomllib.loads(text)
    except ModuleNotFoundError:
        return {"present": True, "parse_error": "tomllib/tomli is unavailable"}
    except Exception as exc:
        return {"present": True, "parse_error": str(exc)}

    if not isinstance(data, dict):
        return {"present": True, "parse_error": JSON_OBJECT_PARSE_ERROR}

    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
    poetry = tool.get("poetry") if isinstance(tool.get("poetry"), dict) else {}

    dependencies: list[str] = []
    if isinstance(project.get("dependencies"), list):
        dependencies.extend(redact_url_userinfo(str(dep)) for dep in project["dependencies"])

    optional_dependencies = project.get("optional-dependencies")
    if isinstance(optional_dependencies, dict):
        for group_name, group_deps in optional_dependencies.items():
            if isinstance(group_deps, list):
                dependencies.extend(
                    f"optional.{group_name}: {redact_url_userinfo(str(dep))}" for dep in group_deps
                )

    dependency_groups = data.get("dependency-groups")
    if isinstance(dependency_groups, dict):
        for group_name, group_deps in dependency_groups.items():
            if isinstance(group_deps, list):
                dependencies.extend(
                    f"group.{group_name}: {redact_url_userinfo(str(dep))}" for dep in group_deps
                )

    poetry_deps = poetry.get("dependencies") if isinstance(poetry.get("dependencies"), dict) else {}
    for name, version in poetry_deps.items():
        if str(name).lower() != "python":
            dependencies.append(f"{name}: {redact_url_userinfo(str(version))}")

    poetry_groups = poetry.get("group") if isinstance(poetry.get("group"), dict) else {}
    for group_name, group_value in poetry_groups.items():
        if not isinstance(group_value, dict):
            continue
        group_deps = group_value.get("dependencies")
        if not isinstance(group_deps, dict):
            continue
        for name, version in group_deps.items():
            dependencies.append(f"poetry.{group_name}.{name}: {redact_url_userinfo(str(version))}")

    dependencies, dependencies_omitted = limited_manifest_items(dependencies)

    return {
        "requires_python": project.get("requires-python") or poetry_deps.get("python"),
        "dependencies": dependencies,
        "dependencies_omitted": dependencies_omitted,
    }


def parse_requirements_txt(path: Path, limit: int = 80) -> dict[str, Any]:
    """Parse dependency and include directives from a requirements-style file."""

    text, parse_error = read_manifest_text(path)
    if parse_error:
        return {"dependencies": [], "dependencies_omitted": 0, "parse_error": parse_error}
    if not text:
        return {"dependencies": [], "dependencies_omitted": 0}

    dependencies: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            dependencies.append(redact_url_userinfo(line))
            continue
        if line.startswith(("-e ", "--editable ")):
            dependencies.append(redact_url_userinfo(line))
            continue
        if line.startswith("--"):
            continue
        if line.startswith("-"):
            continue
        dependencies.append(redact_url_userinfo(line))

    return {
        "dependencies": dependencies[:limit],
        "dependencies_omitted": max(0, len(dependencies) - limit),
    }


def parse_go_mod(path: Path) -> dict[str, Any]:
    """Parse Go version, toolchain and modules from go.mod."""

    text, parse_error = read_manifest_text(path)
    if parse_error:
        return {"parse_error": parse_error, "modules": []}
    if not text:
        return {"modules": []}

    go_version: str | None = None
    toolchain: str | None = None
    modules: list[str] = []
    modules_seen = 0
    in_require_block = False

    for raw in text.splitlines():
        line = raw.strip()

        if line.startswith("go "):
            go_version = line.split(None, 1)[1]
        elif line.startswith("toolchain "):
            toolchain = line.split(None, 1)[1]
        elif line.startswith("require ("):
            in_require_block = True
        elif in_require_block and line == ")":
            in_require_block = False
        elif in_require_block:
            if not line or line.startswith("//"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                modules_seen += 1
                if len(modules) < MAX_BACKGROUND_SECTION_ITEMS:
                    modules.append(f"{parts[0]} {parts[1]}")
        elif line.startswith("require "):
            parts = line.split()
            if len(parts) >= 3:
                modules_seen += 1
                if len(modules) < MAX_BACKGROUND_SECTION_ITEMS:
                    modules.append(f"{parts[1]} {parts[2]}")

    return {
        "go": go_version,
        "toolchain": toolchain,
        "modules": modules,
        "modules_omitted": max(0, modules_seen - len(modules)),
    }


def parse_composer_json(path: Path) -> dict[str, Any]:
    """Parse PHP platform and package constraints from composer.json."""

    try:
        text, parse_error = read_manifest_text(path)
        if parse_error:
            return {"present": True, "parse_error": parse_error}
        data = json.loads(text or "")
    except json.JSONDecodeError as exc:
        return {"present": True, "parse_error": str(exc)}
    except (RecursionError, ValueError, TypeError) as exc:
        return {"present": True, "parse_error": str(exc)}

    if not isinstance(data, dict):
        return {"present": True, "parse_error": JSON_OBJECT_PARSE_ERROR}

    require = data.get("require") if isinstance(data.get("require"), dict) else {}
    require_dev = data.get("require-dev") if isinstance(data.get("require-dev"), dict) else {}
    config = data.get("config") if isinstance(data.get("config"), dict) else {}
    platform = config.get("platform") if isinstance(config.get("platform"), dict) else {}

    platform_items, platform_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in platform.items()]
    )
    require_items, require_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in require.items()]
    )
    require_dev_items, require_dev_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in require_dev.items()]
    )

    return {
        "platform": platform_items,
        "platform_omitted": platform_omitted,
        "require": require_items,
        "require_omitted": require_omitted,
        "require_dev": require_dev_items,
        "require_dev_omitted": require_dev_omitted,
    }


def parse_composer_lock(path: Path) -> dict[str, Any]:
    """Parse locked PHP package versions from composer.lock."""

    try:
        text, parse_error = read_manifest_text(path)
        if parse_error:
            return {"present": True, "parse_error": parse_error}
        data = json.loads(text or "")
    except json.JSONDecodeError as exc:
        return {"present": True, "parse_error": str(exc)}
    except (RecursionError, ValueError, TypeError) as exc:
        return {"present": True, "parse_error": str(exc)}

    if not isinstance(data, dict):
        return {"present": True, "parse_error": JSON_OBJECT_PARSE_ERROR}

    packages: list[str] = []
    packages_seen = 0
    for section in ("packages", "packages-dev"):
        entries = data.get(section)
        if not isinstance(entries, list):
            continue
        for package in entries:
            if not isinstance(package, dict):
                continue
            name = package.get("name")
            version = package.get("version")
            if name and version:
                packages_seen += 1
                if len(packages) < MAX_BACKGROUND_SECTION_ITEMS:
                    packages.append(f"{name}: {version}")

    return {
        "packages": packages,
        "packages_omitted": max(0, packages_seen - len(packages)),
    }


def parse_package_json(path: Path) -> dict[str, Any]:
    """Parse JS/TS runtime and dependency constraints from package.json."""

    try:
        text, parse_error = read_manifest_text(path)
        if parse_error:
            return {"present": True, "parse_error": parse_error}
        data = json.loads(text or "")
    except json.JSONDecodeError as exc:
        return {"present": True, "parse_error": str(exc)}
    except (RecursionError, ValueError, TypeError) as exc:
        return {"present": True, "parse_error": str(exc)}

    if not isinstance(data, dict):
        return {"present": True, "parse_error": JSON_OBJECT_PARSE_ERROR}

    engines = data.get("engines") if isinstance(data.get("engines"), dict) else {}
    dependencies = data.get("dependencies") if isinstance(data.get("dependencies"), dict) else {}
    dev_dependencies = (
        data.get("devDependencies") if isinstance(data.get("devDependencies"), dict) else {}
    )

    engines_items, engines_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in engines.items()]
    )
    dependencies_items, dependencies_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in dependencies.items()]
    )
    dev_dependencies_items, dev_dependencies_omitted = limited_manifest_items(
        [f"{name}: {version}" for name, version in dev_dependencies.items()]
    )

    return {
        "engines": engines_items,
        "engines_omitted": engines_omitted,
        "dependencies": dependencies_items,
        "dependencies_omitted": dependencies_omitted,
        "dev_dependencies": dev_dependencies_items,
        "dev_dependencies_omitted": dev_dependencies_omitted,
    }
