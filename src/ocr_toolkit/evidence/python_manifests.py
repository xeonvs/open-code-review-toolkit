"""Parse bounded Python dependency metadata into normalized evidence facts."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import tomllib  # type: ignore[import-untyped]

from ocr_toolkit.common.redaction import redact_url_userinfo
from ocr_toolkit.evidence.manifest_model import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import EvidenceValue

MAX_PYTHON_GROUP_DEPTH = 8
MAX_PYTHON_GROUP_EDGES = 4_096
PYTHON_REQUIREMENT_INCLUDE_RE = re.compile(
    r"^(?:-r|--requirement)(?:\s+|=)(?P<path>.+)$", re.IGNORECASE
)
_REQUIREMENT_NAME_RE = re.compile(
    r"^([A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?(?:\[[A-Za-z0-9_,.-]+\])?)"
)
_SIMPLE_VERSION_RE = re.compile(r"^(?:===|==|~=|>=|<=|!=|>|<)\s*([^,;\s]+)")
_PYLOCK_SUPPORTED_MAJOR = 1


def _normalize_name(name: str) -> str:
    """Return the PEP 503 comparison form of a distribution name."""

    return re.sub(r"[-_.]+", "-", name.casefold())


def _declared_requirement(value: str, scope: str) -> ManifestFact | None:
    """Normalize one PEP 508-style requirement without running a resolver."""

    requirement = value.strip()
    match = _REQUIREMENT_NAME_RE.match(requirement)
    if match is None:
        return None
    name = match.group(1)
    distribution_name, _, raw_extras = name.partition("[")
    normalized_name = _normalize_name(distribution_name)
    fact_value: dict[str, EvidenceValue] = {
        "name": normalized_name,
        "requirement": redact_url_userinfo(requirement),
        "scope": scope,
    }
    if raw_extras:
        fact_value["extras"] = sorted(
            _normalize_name(item) for item in raw_extras.removesuffix("]").split(",") if item
        )
    simple_version = _SIMPLE_VERSION_RE.match(requirement[match.end() :].lstrip())
    if simple_version is not None:
        # Keep the scalar consumed by legacy delta users alongside the exact text.
        fact_value["version"] = simple_version.group(1)
    return ManifestFact(
        "dependency.declared",
        "python",
        f"{scope}:{normalized_name}",
        fact_value,
    )


def _locked_package(
    name: object, version: object, scope: str, **metadata: object
) -> ManifestFact | None:
    """Normalize one resolved package with redacted scalar metadata."""

    if (
        not isinstance(name, str)
        or not name
        or (version is not None and (not isinstance(version, str) or not version))
    ):
        return None
    normalized_name = _normalize_name(name)
    value: dict[str, EvidenceValue] = {
        "name": normalized_name,
        "scope": scope,
    }
    if isinstance(version, str):
        value["version"] = version
    identity_metadata: list[tuple[str, EvidenceValue]] = []
    for key, item in metadata.items():
        if isinstance(item, (str, bool, int, float)):
            safe_item = redact_url_userinfo(item) if isinstance(item, str) else item
            value[key] = safe_item
            identity_metadata.append((key, safe_item))
    identity = [scope, normalized_name]
    # Marker/source distinguish parallel lock variants; version remains fact data so
    # an upgrade produces one changed delta instead of unrelated remove/add events.
    identity.extend(
        f"{key}={item}"
        for key, item in sorted(identity_metadata)
        if key in {"marker", "source"} and item not in (None, "", False)
    )
    return ManifestFact("dependency.locked", "python", ":".join(identity), value)


def _safe_poetry_value(value: object) -> EvidenceValue | None:
    """Copy supported Poetry metadata while redacting URL credentials."""

    if isinstance(value, str):
        return redact_url_userinfo(value)
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [redact_url_userinfo(item) for item in value]
    return None


def _poetry_declaration(
    name: str, constraint: object, scope: str, identity_suffix: str = ""
) -> ManifestFact | None:
    """Normalize one Poetry dependency or interpreter declaration."""

    normalized_name = _normalize_name(name)
    is_interpreter = scope == "poetry" and normalized_name == "python"
    value: dict[str, EvidenceValue] = {"name": normalized_name, "scope": scope}
    version_key = "constraint" if is_interpreter else "version"
    if isinstance(constraint, bool):
        value[version_key] = "*" if constraint else "disabled"
    elif isinstance(constraint, (str, int, float)):
        value[version_key] = str(constraint)
    elif isinstance(constraint, dict):
        for key in (
            "version",
            "markers",
            "python",
            "platform",
            "source",
            "optional",
            "extras",
            "git",
            "branch",
            "rev",
            "tag",
            "subdirectory",
            "url",
            "path",
            "develop",
            "allow-prereleases",
        ):
            if (safe_value := _safe_poetry_value(constraint.get(key))) is not None:
                value[version_key if key == "version" and is_interpreter else key] = safe_value
    else:
        return None
    identity = f"{scope}:{normalized_name}{identity_suffix}"
    return ManifestFact(
        "runtime.declared" if is_interpreter else "dependency.declared",
        "python",
        identity,
        value,
    )


def _poetry_alternative_key(constraint: dict[object, object]) -> str:
    """Return the source-order-independent identity key for one constraint table."""

    # Version is fact data: changing only it must remain one typed delta. The
    # applicability fields distinguish alternatives for the same package.
    applicability = {
        key: safe_value
        for key, item in sorted(constraint.items(), key=lambda entry: str(entry[0]))
        if isinstance(key, str)
        and key != "version"
        and (safe_value := _safe_poetry_value(item)) is not None
    }
    digest = hashlib.sha256(
        json.dumps(applicability, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return f":alternative:{digest}"


def _poetry_alternative_sort_key(constraint: dict[object, object]) -> str:
    """Return a deterministic order for otherwise equivalent alternatives."""

    supported = {
        key: safe_value
        for key, item in sorted(constraint.items(), key=lambda entry: str(entry[0]))
        if isinstance(key, str) and (safe_value := _safe_poetry_value(item)) is not None
    }
    return json.dumps(supported, ensure_ascii=False, sort_keys=True)


def _poetry_declarations(data: object, scope: str) -> list[ManifestFact]:
    """Collect Poetry declarations under an explicit stable scope."""

    facts: list[ManifestFact] = []
    if not isinstance(data, dict):
        return facts
    for name, constraint in sorted(data.items()):
        if not isinstance(name, str):
            continue
        if not isinstance(constraint, list):
            if fact := _poetry_declaration(name, constraint, scope):
                facts.append(fact)
            continue
        alternatives = sorted(
            (item for item in constraint if isinstance(item, dict)),
            key=lambda item: (_poetry_alternative_key(item), _poetry_alternative_sort_key(item)),
        )
        suffix_counts: dict[str, int] = {}
        for alternative in alternatives:
            base_suffix = _poetry_alternative_key(alternative)
            duplicate = suffix_counts.get(base_suffix, 0) + 1
            suffix_counts[base_suffix] = duplicate
            suffix = f"{base_suffix}-{duplicate}" if duplicate > 1 else base_suffix
            if fact := _poetry_declaration(name, alternative, scope, suffix):
                facts.append(fact)
    return facts


def parse_pyproject(text: str) -> ManifestParseResult:
    """Parse PEP 621, PEP 735, and Poetry declarations from pyproject.toml."""

    data = tomllib.loads(text)
    facts: list[ManifestFact] = []
    notices: list[str] = []
    project = data.get("project") if isinstance(data, dict) else None
    if isinstance(project, dict):
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str):
            facts.append(
                ManifestFact(
                    "runtime.declared",
                    "python",
                    "python",
                    {"name": "python", "constraint": requires_python},
                )
            )
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            for value in dependencies:
                if isinstance(value, str) and (fact := _declared_requirement(value, "project")):
                    facts.append(fact)
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for extra, dependencies in sorted(optional.items()):
                if not isinstance(extra, str) or not isinstance(dependencies, list):
                    continue
                for value in dependencies:
                    if isinstance(value, str) and (
                        fact := _declared_requirement(value, f"optional:{extra}")
                    ):
                        facts.append(fact)

    groups = data.get("dependency-groups") if isinstance(data, dict) else None
    if isinstance(groups, dict):
        edge_count = 0
        normalized_groups: dict[str, tuple[str, list[object]] | None] = {}
        for raw_name, raw_dependencies in groups.items():
            if not isinstance(raw_name, str) or not isinstance(raw_dependencies, list):
                continue
            normalized_name = _normalize_name(raw_name)
            if normalized_name in normalized_groups:
                notices.append(
                    f"dependency group name is duplicated after normalization: {raw_name}"
                )
                # Ambiguous normalized names invalidate every colliding spelling.
                normalized_groups[normalized_name] = None
                continue
            normalized_groups[normalized_name] = (raw_name, raw_dependencies)

        def collect_group(name: str, root: str, stack: tuple[str, ...]) -> None:
            """Expand bounded PEP 735 includes into the consuming group scope."""

            nonlocal edge_count
            normalized_name = _normalize_name(name)
            if normalized_name in stack:
                notices.append(f"dependency group include cycle skipped: {name}")
                return
            if len(stack) >= MAX_PYTHON_GROUP_DEPTH:
                notices.append(f"dependency group include depth exceeded at {name}")
                return
            if normalized_name not in normalized_groups:
                notices.append(f"dependency group include is missing: {name}")
                return
            group_entry = normalized_groups[normalized_name]
            if group_entry is None:
                notices.append(f"dependency group include is ambiguous: {name}")
                return
            display_name, dependencies = group_entry
            for value in dependencies:
                if isinstance(value, str):
                    if fact := _declared_requirement(value, f"group:{root}"):
                        facts.append(fact)
                    continue
                if not isinstance(value, dict) or tuple(value) != ("include-group",):
                    notices.append(f"dependency group entry is unsupported: {display_name}")
                    continue
                included = value.get("include-group")
                if not isinstance(included, str) or not included:
                    notices.append(f"dependency group include is invalid: {display_name}")
                    continue
                if edge_count >= MAX_PYTHON_GROUP_EDGES:
                    notices.append("dependency group include graph was truncated")
                    continue
                edge_count += 1
                collect_group(included, root, (*stack, normalized_name))

        for display_name, _dependencies in sorted(
            (item for item in normalized_groups.values() if item is not None),
            key=lambda item: item[0],
        ):
            collect_group(display_name, display_name, ())

    tool = data.get("tool") if isinstance(data, dict) else None
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    if isinstance(poetry, dict):
        facts.extend(_poetry_declarations(poetry.get("dependencies"), "poetry"))
        poetry_groups = poetry.get("group")
        if isinstance(poetry_groups, dict):
            for name, raw_group in sorted(poetry_groups.items()):
                dependencies = (
                    raw_group.get("dependencies") if isinstance(raw_group, dict) else None
                )
                facts.extend(_poetry_declarations(dependencies, f"poetry-group:{name}"))

    if len(facts) > MAX_MANIFEST_ITEMS:
        notices.append(f"Python declarations were truncated after {MAX_MANIFEST_ITEMS} items")
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), tuple(dict.fromkeys(notices)))


def parse_requirements(text: str) -> ManifestParseResult:
    """Parse requirements entries and expose recursive local includes."""

    facts: list[ManifestFact] = []
    includes: list[str] = []
    notices: list[str] = []
    for raw_line in text.splitlines():
        clean = raw_line.split(" #", 1)[0].strip()
        if not clean or clean.startswith("#"):
            continue
        include = PYTHON_REQUIREMENT_INCLUDE_RE.match(clean)
        if include is not None:
            try:
                values = shlex.split(include.group("path"), posix=True)
            except ValueError:
                notices.append("Python requirements include has invalid quoting")
                continue
            if len(values) != 1:
                notices.append("Python requirements include must name one local file")
                continue
            includes.append(values[0])
            continue
        if clean.startswith("-"):
            continue
        if fact := _declared_requirement(clean, "requirements"):
            facts.append(fact)
        if len(facts) >= MAX_MANIFEST_ITEMS:
            notices.append(f"Python requirements were truncated after {MAX_MANIFEST_ITEMS} items")
            break
    return ManifestParseResult(
        tuple(facts), tuple(dict.fromkeys(notices)), tuple(dict.fromkeys(includes))
    )


def _parse_toml_lock(text: str, *, format_name: str) -> ManifestParseResult:
    """Parse package arrays shared by uv.lock and pylock.toml."""

    data = tomllib.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{format_name} must contain a table")
    if format_name == "pylock.toml":
        lock_version = data.get("lock-version")
        if not isinstance(lock_version, str):
            raise ValueError("pylock.toml must declare lock-version")
        try:
            major_version = int(lock_version.split(".", 1)[0])
        except ValueError as error:
            raise ValueError("pylock.toml lock-version must be numeric") from error
        if major_version != _PYLOCK_SUPPORTED_MAJOR:
            raise ValueError(f"unsupported pylock.toml major version: {major_version}")
    packages = data.get("package" if format_name == "uv.lock" else "packages")
    if not isinstance(packages, list):
        raise ValueError(f"{format_name} must contain a package array")
    facts = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        source = None
        if format_name == "pylock.toml":
            for key in ("vcs", "directory", "archive", "sdist", "wheels"):
                if key in package:
                    source = key
                    break
        fact = _locked_package(
            package.get("name"),
            package.get("version"),
            format_name,
            marker=package.get("marker"),
            requires_python=package.get("requires-python"),
            source=source,
        )
        if fact is not None:
            facts.append(fact)
    return _bounded_lock_result(facts, format_name)


def _bounded_lock_result(facts: list[ManifestFact], format_name: str) -> ManifestParseResult:
    """Return a deterministic bounded lock result with an explicit notice."""

    notices = (
        ((f"{format_name} packages were truncated after {MAX_MANIFEST_ITEMS} items"),)
        if len(facts) > MAX_MANIFEST_ITEMS
        else ()
    )
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), notices)


def parse_uv_lock(text: str) -> ManifestParseResult:
    """Parse resolved packages from uv.lock."""

    return _parse_toml_lock(text, format_name="uv.lock")


def parse_pylock(text: str) -> ManifestParseResult:
    """Parse resolved packages from the standardized pylock.toml format."""

    return _parse_toml_lock(text, format_name="pylock.toml")


def parse_poetry_lock(text: str) -> ManifestParseResult:
    """Parse resolved Poetry packages, groups, markers, and constraints."""

    data = tomllib.loads(text)
    packages = data.get("package") if isinstance(data, dict) else None
    if not isinstance(packages, list):
        raise ValueError("poetry.lock must contain a package array")
    facts = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        raw_groups = package.get("groups")
        groups = (
            sorted(value for value in raw_groups if isinstance(value, str))
            if isinstance(raw_groups, list)
            else [package.get("category")]
            if isinstance(package.get("category"), str)
            else ["main"]
        )
        for group in groups:
            fact = _locked_package(
                package.get("name"),
                package.get("version"),
                f"poetry:{group}",
                optional=package.get("optional"),
                python_versions=package.get("python-versions"),
                marker=package.get("markers"),
            )
            if fact is not None:
                facts.append(fact)
    return _bounded_lock_result(facts, "poetry.lock")


def parse_pipfile_lock(text: str) -> ManifestParseResult:
    """Parse resolved default and development packages from Pipfile.lock."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Pipfile.lock must contain an object")
    facts = []
    for section, scope in (("default", "pipenv:default"), ("develop", "pipenv:develop")):
        packages = data.get(section)
        if not isinstance(packages, dict):
            continue
        for name, package in sorted(packages.items()):
            if not isinstance(package, dict):
                continue
            version = package.get("version")
            if not isinstance(version, str):
                version = package.get("ref")
            fact = _locked_package(
                name,
                version,
                scope,
                marker=package.get("markers"),
                index=package.get("index"),
                source="vcs" if isinstance(package.get("ref"), str) else None,
            )
            if fact is not None:
                facts.append(fact)
    return _bounded_lock_result(facts, "Pipfile.lock")
