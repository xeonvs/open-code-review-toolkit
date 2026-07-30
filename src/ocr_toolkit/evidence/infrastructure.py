"""Extract bounded application and infrastructure pins from declarative configuration."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ocr_toolkit.common.redaction import redact_sensitive, redact_url_userinfo
from ocr_toolkit.evidence.manifest_model import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)

_SUPPORTED_SUFFIXES = frozenset({".yml", ".yaml", ".json", ".toml", ".tf", ".tfvars", ".hcl"})
_SUPPORTED_NAMES = frozenset(
    {"dockerfile", "containerfile", "chart.yaml", "docker-compose.yml", "docker-compose.yaml"}
)
_DEPLOYMENT_PARTS = frozenset(
    {"defaults", "vars", "deploy", "deployment", "infra", "infrastructure"}
)
_EXCLUDED_PARTS = frozenset(
    {
        ".cache",
        ".git",
        ".molecule",
        ".review-context",
        ".terraform",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "fixtures",
        "node_modules",
        "site-packages",
        "testdata",
        "tests",
        "vendor",
        "venv",
    }
)
_METADATA_KEYS = frozenset(
    {
        "$schema",
        "api_version",
        "config_version",
        "format_version",
        "kind",
        "kind_version",
        "schema",
        "schema_version",
        "spec_version",
    }
)
_VERSION_LINE_RE = re.compile(
    r"(?i)^\s*-?\s*[\"']?([A-Za-z0-9_.-]*(?:version|image|chart|app[_-]?version)[A-Za-z0-9_.-]*|tag)"
    r"[\"']?\s*[:=]\s*[\"']?([^\"'#\s]+)"
)
_IMAGE_LINE_RE = re.compile(r"(?i)^\s*-?\s*[\"']?image[\"']?\s*[:=]\s*[\"']?([^\"'#\s]+)")
_FROM_RE = re.compile(r"(?i)^FROM\s+(?P<arguments>.+)$")


def infrastructure_candidate(path: str) -> bool:
    """Return whether a safe path uses a legacy-supported declarative surface."""

    pure_path = PurePosixPath(path)
    if {part.casefold() for part in pure_path.parts} & _EXCLUDED_PARTS or _is_environment_path(
        pure_path
    ):
        return False
    name = pure_path.name.casefold()
    # Match the legacy global-discovery surface: generic YAML/JSON/TOML files
    # outside canonical deployment locations were not scanned unconditionally.
    generic_declarative = (
        pure_path.suffix.casefold() in {".tf", ".tfvars", ".hcl"}
        or name.startswith("values")
        or name == "chart.yaml"
        or bool({part.casefold() for part in pure_path.parts} & _DEPLOYMENT_PARTS)
    )
    return (
        (pure_path.suffix.casefold() in _SUPPORTED_SUFFIXES and generic_declarative)
        or name in _SUPPORTED_NAMES
        or name.startswith(("dockerfile.", "containerfile.", "docker-compose."))
    )


def _is_environment_path(path: PurePosixPath) -> bool:
    """Exclude dotenv-style files because they commonly contain credentials."""

    name = path.name.casefold()
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def _image_reference(reference: str) -> tuple[str, str | None]:
    """Split an OCI reference into stable name and mutable version dimensions."""

    if "@" in reference:
        name, digest = reference.rsplit("@", 1)
        return name, digest
    slash = reference.rfind("/")
    colon = reference.rfind(":")
    return (reference[:colon], reference[colon + 1 :]) if colon > slash else (reference, None)


def _resolved_image(reference: str) -> tuple[str, str] | None:
    """Reject templated, unpinned, or latest image references."""

    safe_reference = redact_url_userinfo(reference.strip())
    if not safe_reference or any(marker in safe_reference for marker in ("{{", "{%", "${", "$")):
        return None
    name, version = _image_reference(safe_reference)
    if not name or version is None or version.casefold() == "latest":
        return None
    return name, version


def _nested_image_references(text: str) -> tuple[tuple[str, str, bool], ...]:
    """Recognize bounded YAML image name/tag or name/digest mappings."""

    references: list[tuple[str, str, bool]] = []
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        match = re.match(r"(?i)^(?P<indent>\s*)image\s*:\s*$", raw)
        if match is None:
            continue
        indent = len(match.group("indent"))
        fields: dict[str, str] = {}
        for child in lines[index + 1 :]:
            stripped = child.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if len(child) - len(child.lstrip()) <= indent:
                break
            field = re.match(
                r"(?i)^(repository|name|tag|digest)\s*:\s*[\"']?([^\"'#\s]+)", stripped
            )
            if field is not None:
                fields[field.group(1).casefold()] = field.group(2)
        name = fields.get("repository") or fields.get("name")
        digest = fields.get("digest")
        version = digest or fields.get("tag")
        if name and version:
            references.append((name, version, digest is not None))
    return tuple(references)


def _dockerfile_images(text: str) -> tuple[str, ...]:
    """Collect resolved image arguments from Dockerfile FROM instructions."""

    images: list[str] = []
    for raw in text.splitlines():
        match = _FROM_RE.match(raw.strip())
        if match is None:
            continue
        parts = match.group("arguments").split()
        while parts and parts[0].startswith("--"):
            parts.pop(0)
        if parts:
            images.append(parts[0])
    return tuple(images)


def _image_fact(path: str, key: str, reference: str) -> ManifestFact | None:
    """Create one pinned image fact using stable path/key/name identity."""

    resolved = _resolved_image(reference)
    if resolved is None:
        return None
    name, version = resolved
    kind = (
        "ci.image"
        if PurePosixPath(path).name.casefold().startswith(".gitlab-ci")
        else "container.image"
    )
    return ManifestFact(
        kind,
        "infrastructure",
        f"{path}:{key.casefold()}:{name.casefold()}",
        {"name": name, "version": version, "source_path": path, "key": key},
    )


def parse_infrastructure_pins(path: str, text: str) -> ManifestParseResult:
    """Parse conservative version and image pins from one immutable config blob."""

    if not infrastructure_candidate(path):
        return ManifestParseResult(())
    facts: list[ManifestFact] = []
    seen: set[tuple[str, str]] = set()

    for name, version, is_digest in _nested_image_references(text):
        separator = "@" if is_digest else ":"
        fact = _image_fact(path, "image", f"{name}{separator}{version}")
        if fact is not None:
            facts.append(fact)
            seen.add((fact.kind, fact.identity))

    if PurePosixPath(path).name.casefold().startswith(("dockerfile", "containerfile")):
        stage_names: set[str] = set()
        for raw in text.splitlines():
            match = _FROM_RE.match(raw.strip())
            if match is None:
                continue
            parts = match.group("arguments").split()
            for index, part in enumerate(parts[:-1]):
                if part.casefold() == "as":
                    stage_names.add(parts[index + 1].casefold())
        for reference in _dockerfile_images(text):
            fact = (
                None
                if reference.casefold() in stage_names
                else _image_fact(path, "FROM", reference)
            )
            if fact is not None and (fact.kind, fact.identity) not in seen:
                facts.append(fact)
                seen.add((fact.kind, fact.identity))

    nested_indents: list[int] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        nested_indents = [parent for parent in nested_indents if indent > parent]
        if re.match(r"(?i)^image\s*:\s*$", stripped):
            nested_indents.append(indent)
            continue
        if nested_indents:
            continue
        match = _VERSION_LINE_RE.match(raw)
        if match is None:
            image_match = _IMAGE_LINE_RE.match(raw)
            if image_match is None:
                continue
            key, value = "image", image_match.group(1)
        else:
            key, value = match.group(1), match.group(2)
        normalized_key = key.casefold().replace("-", "_")
        if normalized_key in _METADATA_KEYS or any(marker in value for marker in ("{{", "{%", "$")):
            continue
        is_image = normalized_key == "image" or normalized_key.endswith("image")
        if is_image:
            fact = _image_fact(path, key, value)
        else:
            safe_value = redact_sensitive(redact_url_userinfo(value.strip()))
            if (
                not safe_value
                or not re.search(r"\d", safe_value)
                or safe_value.casefold() in {"true", "false", "yes", "no", "null", "none", "latest"}
            ):
                continue
            fact = ManifestFact(
                "application.version",
                "infrastructure",
                f"{path}:{normalized_key}",
                {"key": key, "version": safe_value, "source_path": path},
            )
        if fact is not None and (fact.kind, fact.identity) not in seen:
            facts.append(fact)
            seen.add((fact.kind, fact.identity))

    notices = (
        (f"infrastructure facts were truncated after {MAX_MANIFEST_ITEMS} items",)
        if len(facts) > MAX_MANIFEST_ITEMS
        else ()
    )
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), notices)
