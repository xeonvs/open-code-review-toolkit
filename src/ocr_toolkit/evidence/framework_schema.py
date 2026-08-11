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
TEMPLATE_ENGINES = {"jinja2", "twig"}
TEMPLATE_DETECTIONS = {"jinja-extension", "ansible-role-template", "twig-extension"}
OBJECT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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


def validate_framework_value(value: EvidenceValue) -> None:
    """Validate one `framework.detected` fact against its exact nested schema."""

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
            "configuration_paths",
            "related",
        },
        "framework evidence",
    )
    if root["schema_version"] != FRAMEWORK_SCHEMA:
        raise ValueError("framework evidence schema is unsupported")
    _string(root["plugin"], "framework plugin", choices=PLUGIN_IDS)
    _string(root["framework"], "framework name")
    _string(root["ecosystem"], "framework ecosystem", choices=ECOSYSTEMS)
    _string(root["category"], "framework category", choices=CATEGORIES)
    _string(root["version_state"], "framework version state", choices=VERSION_STATES)
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
    for item in _objects(
        root["resolutions"],
        "framework resolution",
        {"package", "version", "source", "source_path"},
    ):
        _string(item["package"], "framework package")
        _string(item["version"], "framework version")
        _string(item["source"], "framework resolution source")
        _path(item["source_path"], "framework resolution source path")
    paths = root["configuration_paths"]
    if not isinstance(paths, (list, tuple)) or len(paths) > 128:
        raise ValueError("framework configuration paths are invalid")
    for path in paths:
        _path(path, "framework configuration path")
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


def validate_template_value(value: EvidenceValue) -> None:
    """Validate one `template.file` fact against its exact nested schema."""

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
    _string(root["plugin"], "template plugin", choices=PLUGIN_IDS)
    _string(root["engine"], "template engine", choices=TEMPLATE_ENGINES)
    _string(root["detection"], "template detection", choices=TEMPLATE_DETECTIONS)
    rendered = root["rendered_extension"]
    if rendered is not None:
        _string(rendered, "rendered extension")
    object_sha = _string(root["object_sha"], "template object SHA")
    if not OBJECT_SHA_RE.fullmatch(object_sha):
        raise ValueError("template object SHA is invalid")


def validate_plugin_record(kind: str, value: EvidenceValue) -> None:
    """Validate one plugin fact nested below the common identity envelope."""

    envelope = _exact_mapping(value, {"identity", "fact"}, "plugin evidence envelope")
    _string(envelope["identity"], "plugin evidence identity")
    fact = envelope["fact"]
    if kind == "framework.detected":
        validate_framework_value(fact)
    elif kind == "template.file":
        validate_template_value(fact)
