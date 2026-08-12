"""Validate closed framework and template plugin evidence values."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import cast

from ocr_toolkit.evidence.model import EvidenceValue

FRAMEWORK_SCHEMA = "repository.framework-evidence/v1"
TEMPLATE_SCHEMA = "repository.template-evidence/v1"
PLUGIN_IDS = {"jinja2", "go-web", "symfony-php", "react-typescript"}
ECOSYSTEMS = {"python", "go", "php", "javascript"}
CATEGORIES = {"framework", "template-engine"}
VERSION_STATES = {"declared-only", "resolved", "conflicting", "local-override"}
CONFIGURATION_STATES = {"complete", "partial"}
TEMPLATE_ENGINES = {"jinja2", "twig"}
TEMPLATE_DETECTIONS = {"jinja-extension", "ansible-role-template", "twig-extension"}
OBJECT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PLUGIN_FRAMEWORKS = {
    "jinja2": {"jinja2"},
    "go-web": {"echo", "fiber"},
    "symfony-php": {"symfony", "twig"},
    "react-typescript": {"react", "next"},
}
PLUGIN_ECOSYSTEMS = {
    "jinja2": "python",
    "go-web": "go",
    "symfony-php": "php",
    "react-typescript": "javascript",
}
TEMPLATE_PLUGIN_ENGINES = {"jinja2": "jinja2", "symfony-php": "twig"}
TEMPLATE_ENGINE_DETECTIONS = {
    "jinja2": {"jinja-extension", "ansible-role-template"},
    "twig": {"twig-extension"},
}


def _exact_mapping(value: object, keys: set[str], label: str) -> Mapping[str, EvidenceValue]:
    """Require one JSON mapping with exactly the closed key set."""

    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{label} fields are invalid")
    return cast(Mapping[str, EvidenceValue], value)


def _string(value: object, label: str, *, choices: set[str] | None = None) -> str:
    """Require one bounded safe string and optional closed enum membership."""

    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or any(ord(character) < 32 for character in value)
        or (choices is not None and value not in choices)
    ):
        raise ValueError(f"{label} is invalid")
    return value


def _path(value: object, label: str) -> str:
    """Require one normalized repository-relative POSIX path."""

    path = _string(value, label)
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in path.split("/")):
        raise ValueError(f"{label} is invalid")
    return path


def _objects(value: object, label: str, keys: set[str]) -> tuple[Mapping[str, EvidenceValue], ...]:
    """Require a bounded sequence of closed objects."""

    if not isinstance(value, (list, tuple)) or len(value) > 128:
        raise ValueError(f"{label} is invalid")
    return tuple(_exact_mapping(item, keys, label) for item in value)


def validate_framework_value(value: EvidenceValue) -> tuple[str, str]:
    """Validate one `framework.detected` fact and return plugin/framework identity."""

    root = _exact_mapping(
        value,
        {
            "schema_version",
            "plugin",
            "framework",
            "ecosystem",
            "category",
            "declarations",
            "resolutions",
            "version_state",
            "configuration_state",
            "configuration_paths",
            "related",
            "replacement",
        },
        "framework evidence",
    )
    if root["schema_version"] != FRAMEWORK_SCHEMA:
        raise ValueError("framework evidence schema is unsupported")
    plugin = _string(root["plugin"], "framework plugin", choices=PLUGIN_IDS)
    framework = _string(root["framework"], "framework name", choices=PLUGIN_FRAMEWORKS[plugin])
    ecosystem = _string(root["ecosystem"], "framework ecosystem", choices=ECOSYSTEMS)
    if ecosystem != PLUGIN_ECOSYSTEMS[plugin]:
        raise ValueError("framework plugin ecosystem is inconsistent")
    category = _string(root["category"], "framework category", choices=CATEGORIES)
    if (framework in {"jinja2", "twig"}) != (category == "template-engine"):
        raise ValueError("framework category is inconsistent")
    version_state = _string(
        root["version_state"], "framework version state", choices=VERSION_STATES
    )
    configuration_state = _string(
        root["configuration_state"],
        "framework configuration state",
        choices=CONFIGURATION_STATES,
    )
    declarations = _objects(
        root["declarations"],
        "framework declaration",
        {"package", "scope", "declared_value", "source_path"},
    )
    if not declarations:
        raise ValueError("framework evidence requires a direct declaration")
    for item in declarations:
        _string(item["package"], "framework package")
        _string(item["scope"], "framework scope")
        _string(item["declared_value"], "framework declared value")
        _path(item["source_path"], "framework declaration source")
    resolutions = _objects(
        root["resolutions"],
        "framework resolution",
        {"package", "version", "source", "source_path"},
    )
    for item in resolutions:
        _string(item["package"], "framework package")
        _string(item["version"], "framework version")
        _string(item["source"], "framework resolution source")
        _path(item["source_path"], "framework resolution source path")
    replacement = root["replacement"]
    if replacement is not None:
        replacement_value = _exact_mapping(
            replacement, {"target", "type", "version"}, "framework replacement"
        )
        _string(replacement_value["target"], "framework replacement target")
        replacement_type = _string(
            replacement_value["type"],
            "framework replacement type",
            choices={"local", "module"},
        )
        replacement_version = replacement_value["version"]
        if replacement_version is not None:
            _string(replacement_version, "framework replacement version")
        if plugin != "go-web" or (replacement_type == "local") != (
            version_state == "local-override"
        ):
            raise ValueError("framework replacement state is inconsistent")
    elif version_state == "local-override":
        raise ValueError("framework local override requires replacement metadata")
    if version_state == "resolved" and not resolutions:
        raise ValueError("resolved framework evidence requires a resolution")
    if version_state == "declared-only" and resolutions:
        raise ValueError("declared-only framework evidence cannot contain resolutions")
    if version_state == "conflicting" and len({item["version"] for item in resolutions}) < 2:
        raise ValueError("conflicting framework evidence requires distinct versions")
    paths = root["configuration_paths"]
    if not isinstance(paths, (list, tuple)) or len(paths) > 128:
        raise ValueError("framework configuration paths are invalid")
    normalized_paths = [_path(path, "framework configuration path") for path in paths]
    if normalized_paths != sorted(set(normalized_paths)):
        raise ValueError("framework configuration paths are not canonical")
    if configuration_state == "partial" and len(normalized_paths) != 128:
        raise ValueError("partial framework configuration requires the path limit")
    for item in _objects(
        root["related"],
        "related framework evidence",
        {"name", "role", "declared_values", "resolved_versions", "source_paths"},
    ):
        _string(item["name"], "related framework name")
        _string(item["role"], "related framework role")
        for key in ("declared_values", "resolved_versions"):
            values = item[key]
            if not isinstance(values, (list, tuple)) or len(values) > 128:
                raise ValueError("related framework versions are invalid")
            for entry in values:
                _string(entry, "related framework value")
        sources = item["source_paths"]
        if not isinstance(sources, (list, tuple)) or len(sources) > 128:
            raise ValueError("related framework source paths are invalid")
        for source in sources:
            _path(source, "related framework source path")
    return plugin, framework


def validate_template_value(value: EvidenceValue) -> tuple[str, str]:
    """Validate one `template.file` fact and return plugin/engine identity."""

    root = _exact_mapping(
        value,
        {
            "schema_version",
            "plugin",
            "engine",
            "detection",
            "rendered_extension",
            "object_sha",
        },
        "template evidence",
    )
    if root["schema_version"] != TEMPLATE_SCHEMA:
        raise ValueError("template evidence schema is unsupported")
    plugin = _string(root["plugin"], "template plugin", choices=set(TEMPLATE_PLUGIN_ENGINES))
    engine = _string(root["engine"], "template engine", choices=TEMPLATE_ENGINES)
    if engine != TEMPLATE_PLUGIN_ENGINES[plugin]:
        raise ValueError("template plugin engine is inconsistent")
    detection = _string(root["detection"], "template detection", choices=TEMPLATE_DETECTIONS)
    if detection not in TEMPLATE_ENGINE_DETECTIONS[engine]:
        raise ValueError("template detection is inconsistent")
    rendered = root["rendered_extension"]
    if rendered is not None:
        rendered_extension = _string(rendered, "rendered extension")
        if not rendered_extension.startswith(".") or detection != "jinja-extension":
            raise ValueError("template rendered extension is inconsistent")
    object_sha = _string(root["object_sha"], "template object SHA")
    if not OBJECT_SHA_RE.fullmatch(object_sha):
        raise ValueError("template object SHA is invalid")
    return plugin, engine


def validate_plugin_record(kind: str, value: EvidenceValue) -> None:
    """Validate one plugin fact and bind its envelope identity to nested values."""

    envelope = _exact_mapping(value, {"identity", "fact"}, "plugin evidence envelope")
    identity = _string(envelope["identity"], "plugin evidence identity")
    fact = envelope["fact"]
    if kind == "framework.detected":
        plugin, framework = validate_framework_value(fact)
        if identity != f"{plugin}:{framework}":
            raise ValueError("framework evidence identity is inconsistent")
    elif kind == "template.file":
        validate_template_value(fact)
        _path(identity, "template evidence identity")
    else:
        raise ValueError("plugin evidence kind is unsupported")
