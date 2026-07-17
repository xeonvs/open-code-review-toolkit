"""Ansible-specific context discovery for OCR."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from ocr_toolkit.common.redaction import redact_sensitive, redact_url_userinfo
from ocr_toolkit.context import repo as context_repo
from ocr_toolkit.context.settings import (
    DEFAULT_MAX_FILE_BYTES,
    MAX_BACKGROUND_SECTION_ITEMS,
    is_env_file,
)

VERSION_PIN_BACKGROUND_SKIP_PARTS = {
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


def _is_background_version_fixture_path(rel_path: str) -> bool:
    """Return whether auto-discovery should skip a version-pin candidate."""

    return any(part in VERSION_PIN_BACKGROUND_SKIP_PARTS for part in Path(rel_path).parts)


def _nested_image_pins(text: str) -> tuple[list[str], set[int]]:
    """Extract image.name or image.repository plus tag/digest mappings."""

    pins: list[str] = []
    consumed_lines: set[int] = set()
    image_indent: int | None = None
    fields: dict[str, str] = {}
    image_line = -1

    def flush() -> None:
        name = fields.get("name") or fields.get("repository")
        if name:
            if fields.get("digest"):
                pins.append(f"{name}@{fields['digest']}")
            elif fields.get("tag"):
                pins.append(f"{name}:{fields['tag']}")
            else:
                pins.append(name)
        fields.clear()

    source_lines = text.splitlines()
    for line_number, raw in enumerate([*source_lines, ""]):
        line = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        at_eof = line_number == len(source_lines)
        if image_indent is not None and (
            at_eof or (line and not line.startswith("#") and indent <= image_indent)
        ):
            flush()
            image_indent = None
        if not line or line.startswith("#"):
            continue
        if image_indent is None:
            if re.match(r"(?i)^image\s*:\s*$", line):
                image_indent = indent
                image_line = line_number
            continue
        field = re.match(
            r"(?i)^(name|repository|tag|digest)\s*:\s*[\"']?([^\"'#\s]+)",
            line,
        )
        if field:
            fields[field.group(1).lower()] = redact_url_userinfo(field.group(2).strip())
            consumed_lines.add(line_number)
            consumed_lines.add(image_line)
    return pins, consumed_lines


def _ansible_requirement_items(path: Path, limit: int) -> list[tuple[str, str | None]]:
    """Parse bounded Galaxy requirement items without interpreting nested lists."""

    items: list[tuple[str, str | None]] = []
    item_indent: int | None = None
    field_indent: int | None = None
    fields: dict[str, str] = {}

    def flush() -> None:
        if len(items) >= limit:
            fields.clear()
            return
        identifier = fields.get("name") or fields.get("src")
        if identifier:
            items.append((redact_url_userinfo(identifier), fields.get("version")))
        fields.clear()

    for raw in context_repo.read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        list_item = re.match(r"-\s*(name|src|version):\s*[\"']?([^\"'#]+)", line)
        if line.startswith("-") and (item_indent is None or indent <= item_indent):
            if item_indent is not None:
                flush()
                if len(items) >= limit:
                    break
            item_indent = indent if list_item else None
            field_indent = None
            if list_item:
                fields[list_item.group(1)] = list_item.group(2).strip()
            continue
        if item_indent is None or line.startswith("-") or indent <= item_indent:
            continue
        if field_indent is None:
            field_indent = indent
        if indent != field_indent:
            continue
        field = re.match(r"(name|src|version):\s*[\"']?([^\"'#]+)", line)
        if field:
            fields[field.group(1)] = field.group(2).strip()

    if item_indent is not None and len(items) < limit:
        flush()
    return items


def parse_ansible_requirements(path: Path) -> list[str]:
    """Extract common collection/role names and versions from requirements.yml.

    This is a lightweight parser that avoids adding PyYAML to the CI image.
    """

    items: list[str] = []
    for identifier, version in _ansible_requirement_items(path, MAX_BACKGROUND_SECTION_ITEMS):
        items.append(f"{identifier}: {redact_url_userinfo(version)}" if version else identifier)
        if len(items) >= MAX_BACKGROUND_SECTION_ITEMS:
            break
    return items


def parse_ansible_requirement_version_pins(path: Path, limit: int = 80) -> list[str]:
    """Extract collection/role version pins with their names for context output."""

    items: list[str] = []
    rel_path = path.relative_to(context_repo.ROOT)
    for identifier, version in _ansible_requirement_items(path, limit):
        if version:
            items.append(f"{rel_path}: {identifier}={redact_url_userinfo(version)}")
        if len(items) >= limit:
            break
    return items


def is_root_ansible_playbook(rel_path: str) -> bool:
    """Return whether a root YAML file looks like an Ansible playbook.

    An Ansible playbook is a list of plays, so the top level must be a
    sequence (``- ...``) and at least one play must contain a ``hosts``
    key. A bare ``hosts:`` at the top level belongs to inventory/Compose/
    etc. and is intentionally rejected to keep the background context
    free of false positives.
    """

    path = Path(rel_path)
    if len(path.parts) != 1 or path.suffix.lower() not in {".yml", ".yaml"}:
        return False

    text = context_repo.read_text(context_repo.ROOT / rel_path, max_bytes=64_000)
    if not text:
        return False

    hosts_key = re.compile(r"^[\"']?hosts[\"']?\s*:")
    import_playbook_key = re.compile(r"^[\"']?import_playbook[\"']?\s*:")
    top_level_list_item = False
    play_child_indent: int | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or stripped in {"---", "..."}:
            continue

        indent = len(line) - len(line.lstrip(" "))

        if indent == 0 and stripped.startswith("-"):
            top_level_list_item = True
            play_child_indent = None
            item = stripped[1:].lstrip()
            if hosts_key.match(item) or import_playbook_key.match(item):
                return True
            continue

        if indent == 0:
            # A top-level mapping rules the file out: playbooks must start
            # with a sequence. Reset list-item tracking and move on.
            top_level_list_item = False
            play_child_indent = None
            continue

        if not top_level_list_item:
            continue

        if play_child_indent is None:
            play_child_indent = indent

        if indent == play_child_indent and (
            hosts_key.match(stripped) or import_playbook_key.match(stripped)
        ):
            return True

    return False


def detect_root_ansible_playbooks(
    limit: int = MAX_BACKGROUND_SECTION_ITEMS,
) -> list[str]:
    """Detect root playbook entrypoints without classifying every root YAML file."""

    candidates = context_repo.rel_glob_files(["*.yml", "*.yaml"], limit=500)
    playbooks = [rel_path for rel_path in candidates if is_root_ansible_playbook(rel_path)]
    return sorted(playbooks)[:limit]


def is_inventory_topology_file(rel_path: str) -> bool:
    """Return whether a path is likely an Ansible inventory topology file."""

    path = Path(rel_path)
    if any(part.startswith(".") for part in path.parts):
        return False

    parts = {part.lower() for part in path.parts}
    name = path.name.lower()

    if "group_vars" in parts or "host_vars" in parts:
        return False

    if name in {
        "hosts",
        "hosts.ini",
        "hosts.yml",
        "hosts.yaml",
        "inventory",
        "inventory.ini",
        "inventory.yml",
        "inventory.yaml",
    }:
        return True

    if "inventory" in parts or "inventories" in parts:
        return Path(rel_path).suffix.lower() in {
            "",
            ".ini",
            ".cfg",
            ".conf",
            ".yml",
            ".yaml",
        }

    return False


def extract_inventory_topology(paths: Sequence[str], limit: int = 120) -> list[str]:
    """Extract a bounded list of Ansible inventory group-like names.

    The parser is intentionally conservative. INI groups are detected from
    `[group]` headers. YAML inventory groups are detected only under `children`
    sections or as the top-level `all` group, avoiding hostnames under `hosts`.
    """

    groups: set[str] = set()

    for rel_path in paths:
        path = context_repo.ROOT / rel_path
        if context_repo.resolve_repo_file(path) is None:
            continue

        # The indentation step inside `children:` is whatever the first
        # nested key uses (commonly 2, but inventories with 4-space indent
        # exist). Lock it in on first sighting so we only pick up direct
        # children, not deeper descendants such as `hosts:` entries.
        yaml_children_indent: int | None = None
        yaml_child_step: int | None = None

        for raw in context_repo.read_text(path, max_bytes=128_000).splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue

            stripped = raw.strip()
            indent = len(raw) - len(raw.lstrip(" "))

            ini_match = re.match(r"^\[([A-Za-z0-9_.-]+)(?::(?:children|vars))?\]$", stripped)
            if ini_match:
                groups.add(ini_match.group(1))
                if len(groups) >= limit:
                    break
                continue

            key_match = re.match(r"^([A-Za-z0-9_.-]+):\s*$", stripped)
            if not key_match:
                continue

            key = key_match.group(1)

            if key == "all" and indent == 0:
                groups.add(key)
            elif key == "children":
                yaml_children_indent = indent
                yaml_child_step = None
            elif yaml_children_indent is not None and indent > yaml_children_indent:
                if yaml_child_step is None:
                    yaml_child_step = indent - yaml_children_indent
                if indent == yaml_children_indent + yaml_child_step and key not in {
                    "vars",
                    "hosts",
                    "children",
                }:
                    groups.add(key)
            elif yaml_children_indent is not None and indent <= yaml_children_indent:
                yaml_children_indent = None
                yaml_child_step = None

            if len(groups) >= limit:
                break

    return sorted(groups)[:limit]


def extract_application_versions(
    files: Sequence[str], limit: int = 160, *, include_discovered: bool = True
) -> list[str]:
    """Extract likely application/runtime version pins from common config files.

    The scanner is heuristic and intentionally conservative. It looks for
    version-like keys in configuration/manifests while avoiding ordinary Ansible
    `tags` and arbitrary source-code variables.
    """

    candidate_patterns = [
        "*.yml",
        "*.yaml",
        "*.json",
        "*.toml",
        "*.tf",
        "*.tfvars",
        "*.hcl",
        "Dockerfile",
        "Dockerfile.*",
        "Containerfile",
        "Containerfile.*",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "Chart.yaml",
        "values*.yaml",
        "values*.yml",
        "**/Chart.yaml",
        "**/Dockerfile",
        "**/Dockerfile.*",
        "**/Containerfile",
        "**/Containerfile.*",
        "**/values*.yaml",
        "**/values*.yml",
    ]

    candidate_suffixes = (
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".tf",
        ".tfvars",
        ".hcl",
    )
    candidate_basenames = {
        "Dockerfile",
        "Containerfile",
        "Chart.yaml",
        "docker-compose.yml",
        "docker-compose.yaml",
    }

    candidate_files = {
        file_path
        for file_path in files
        if not is_env_file(file_path)
        and not _is_background_version_fixture_path(file_path)
        and (
            Path(file_path).name in candidate_basenames
            or Path(file_path).name.lower().startswith(("dockerfile.", "containerfile."))
            or file_path.endswith(candidate_suffixes)
        )
    }

    if include_discovered:
        auto_discovery_limit = max(80, limit * 4)
        for pattern in candidate_patterns:
            candidate_files.update(
                rel_path
                for rel_path in context_repo.rel_glob_files(
                    [pattern],
                    limit=auto_discovery_limit,
                    exclude_dirs=context_repo.DEFAULT_EXCLUDE_DIRS
                    | VERSION_PIN_BACKGROUND_SKIP_PARTS,
                )
                if not _is_background_version_fixture_path(rel_path)
            )

    results: list[str] = []
    seen: set[str] = set()

    version_line = re.compile(
        r"(?i)^\s*-?\s*[\"']?("
        r"[A-Za-z0-9_.-]*(?:version|image|chart|app[_-]?version)[A-Za-z0-9_.-]*"
        r"|tag"
        r")[\"']?\s*[:=]\s*[\"']?([^\"'#\s]+)"
    )

    image_line = re.compile(r"(?i)^\s*-?\s*[\"']?image[\"']?\s*[:=]\s*[\"']?([^\"'#\s]+)")

    changed_candidate_files = {file_path for file_path in files if file_path in candidate_files}
    for rel_path in sorted(
        candidate_files,
        key=lambda item: (item not in changed_candidate_files, item),
    ):
        if Path(rel_path).name in {"requirements.yml", "requirements.yaml"}:
            continue
        if is_env_file(rel_path):
            continue

        path = context_repo.ROOT / rel_path
        safe_path = context_repo.resolve_repo_file(path)
        if safe_path is None:
            continue

        try:
            if safe_path.stat().st_size > DEFAULT_MAX_FILE_BYTES:
                continue
        except OSError:
            continue

        text = context_repo.read_text(safe_path, max_bytes=128_000)
        is_containerfile = Path(rel_path).name.lower().startswith(("dockerfile", "containerfile"))
        nested_pins, consumed_lines = _nested_image_pins(text)
        scan_lines = [f"image: {image_ref}" for image_ref in nested_pins]
        scan_lines.extend(
            raw
            for line_number, raw in enumerate(text.splitlines())
            if line_number not in consumed_lines
        )
        for raw in scan_lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if is_containerfile:
                from_match = re.match(r"(?i)^FROM\s+([^\s]+)", line)
                if not from_match:
                    continue
                from_parts = line.split()[1:]
                while from_parts and from_parts[0].startswith("--"):
                    from_parts.pop(0)
                if not from_parts:
                    continue
                key = "image"
                value = redact_url_userinfo(from_parts[0])
            else:
                # Skip ordinary Ansible tags, but allow singular `tag: 1.2.3`.
                if re.match(r"(?i)^\s*-?\s*[\"']?tags[\"']?\s*:", line):
                    continue

                version_match = version_line.search(line)
                image_match = image_line.search(line)

                if not version_match and not image_match:
                    continue

                if not re.search(
                    r"(?i)(version|image|chart|app[_-]?version|tag)\s*[:=]",
                    line,
                ):
                    continue

                if image_match:
                    key = "image"
                    value = redact_url_userinfo(image_match.group(1).strip())
                elif version_match:
                    key = version_match.group(1).strip()
                    normalized_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower().replace("-", "_")
                    if normalized_key in {
                        "api_version",
                        "config_version",
                        "format_version",
                        "kind",
                        "kind_version",
                        "schema",
                        "schema_version",
                        "spec_version",
                        "$schema",
                    }:
                        continue
                    value = redact_url_userinfo(version_match.group(2).strip())
                else:
                    continue

            key_lower = key.lower()
            is_image_key = key_lower == "image" or key_lower.endswith("image")
            normalized_value = value.strip().lower()
            image_ref = normalized_value.rsplit("/", 1)[-1]
            image_name, _, _image_digest = image_ref.partition("@")
            has_digest = "@" in normalized_value
            image_tag = image_name.rsplit(":", 1)[-1] if ":" in image_name else ""
            if (
                not value
                or normalized_value
                in {
                    "true",
                    "false",
                    "yes",
                    "no",
                    "null",
                    "none",
                    "latest",
                }
                or (is_image_key and not has_digest and image_tag in {"", "latest"})
                or any(marker in value for marker in ("{{", "{%", "${"))
                or (not is_image_key and not re.search(r"\d", value))
            ):
                continue

            item = redact_sensitive(f"{rel_path}: {key}={value}")
            if item in seen:
                continue

            seen.add(item)
            results.append(item)

            if len(results) >= limit:
                return results[:limit]

    return results[:limit]
