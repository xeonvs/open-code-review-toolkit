"""Parse bounded Ansible Galaxy requirements without executing repository code."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ocr_toolkit.common.redaction import redact_url_userinfo

MAX_GALAXY_REQUIREMENTS = 512
_SECTION_RE = re.compile(r"^(roles|collections)\s*:\s*(.*)$")
_FIELD_RE = re.compile(r"^(include|name|src|source|version)\s*:\s*(.*)$")
_EMPTY_SEQUENCE_VALUES = {"[]", "null", "Null", "NULL", "~"}


@dataclass(frozen=True, slots=True)
class GalaxyRequirement:
    """Describe one normalized role or collection declaration."""

    requirement_type: str
    name: str
    version: str | None
    source: str | None


@dataclass(frozen=True, slots=True)
class GalaxyParseResult:
    """Return deterministic requirements and bounded coverage notices."""

    requirements: tuple[GalaxyRequirement, ...]
    include_paths: tuple[str, ...] = ()
    notices: tuple[str, ...] = ()


def _clean_scalar(raw: object) -> str | None:
    """Normalize one scalar while removing comments and URL credentials."""

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return str(raw)
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if value.startswith(("'", '"')):
        quote = value[0]
        end = value.find(quote, 1)
        trailing = value[end + 1 :].strip() if end >= 0 else ""
        if end < 0 or (trailing and not trailing.startswith("#")):
            return None
        value = value[1:end]
    else:
        value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
    if not value or value in {"null", "Null", "NULL", "~"}:
        return None
    return redact_url_userinfo(value)[:2_048]


def _requirement(requirement_type: str, raw: object) -> GalaxyRequirement | None:
    """Normalize one JSON-compatible Galaxy requirement item."""

    if isinstance(raw, str):
        name = _clean_scalar(raw)
        if name is None:
            return None
        name, version = _role_shorthand(requirement_type, name, None)
        source = name if requirement_type == "role" and _looks_like_role_source(name) else None
        return GalaxyRequirement(requirement_type, name, version, source)
    if not isinstance(raw, dict):
        return None
    name = _clean_scalar(raw.get("name"))
    source = _clean_scalar(raw.get("src")) or _clean_scalar(raw.get("source"))
    identifier = name or source
    if identifier is None:
        return None
    identifier, version = _role_shorthand(
        requirement_type, identifier, _clean_scalar(raw.get("version"))
    )
    return GalaxyRequirement(requirement_type, identifier, version, source)


def _role_shorthand(
    requirement_type: str, identifier: str, version: str | None
) -> tuple[str, str | None]:
    """Split the documented comma-separated role shorthand when unambiguous."""

    if requirement_type != "role" or version is not None or "," not in identifier:
        return identifier, version
    candidate, separator, candidate_version = identifier.rpartition(",")
    if separator and candidate.strip() and candidate_version.strip():
        return candidate.strip(), candidate_version.strip()
    return identifier, version


def _looks_like_role_source(value: str) -> bool:
    """Return whether role shorthand identifies a non-Galaxy source."""

    return value.startswith(("git+", "git@", "file:")) or "://" in value


def _bounded_result(candidates: list[tuple[str, object]], malformed: int) -> GalaxyParseResult:
    """Normalize candidates under the public item bound and report omissions."""

    requirements: list[GalaxyRequirement] = []
    include_paths: list[str] = []
    seen_includes: set[str] = set()
    seen: dict[tuple[str, str], GalaxyRequirement] = {}
    conflicts = 0
    truncated = len(candidates) > MAX_GALAXY_REQUIREMENTS
    for requirement_type, raw in candidates[:MAX_GALAXY_REQUIREMENTS]:
        if requirement_type == "include":
            include_path = _clean_scalar(raw)
            if include_path is None:
                malformed += 1
            elif include_path not in seen_includes:
                seen_includes.add(include_path)
                include_paths.append(include_path)
            continue
        item = _requirement(requirement_type, raw)
        if item is None:
            malformed += 1
            continue
        key = (item.requirement_type, item.name.casefold())
        previous = seen.get(key)
        if previous is None:
            seen[key] = item
            requirements.append(item)
        elif previous != item:
            conflicts += 1
    notices = []
    if malformed:
        notices.append(f"Ansible Galaxy skipped {malformed} malformed requirement item(s)")
    if conflicts:
        notices.append(
            f"Ansible Galaxy skipped {conflicts} conflicting duplicate requirement item(s)"
        )
    if truncated:
        notices.append(
            f"Ansible Galaxy requirements were truncated after {MAX_GALAXY_REQUIREMENTS} items"
        )
    return GalaxyParseResult(tuple(requirements), tuple(include_paths), tuple(notices))


def _json_candidates(data: object) -> tuple[list[tuple[str, object]], int]:
    """Extract role and collection candidates from JSON-compatible YAML."""

    if isinstance(data, list):
        candidates = []
        for item in data:
            if isinstance(item, dict) and "include" in item:
                candidates.append(("include", item.get("include")))
            else:
                candidates.append(("role", item))
        return candidates, 0
    if not isinstance(data, dict):
        return [], 1
    candidates: list[tuple[str, object]] = []
    malformed = 0
    for section, requirement_type in (("roles", "role"), ("collections", "collection")):
        raw = data.get(section)
        if raw is None:
            continue
        if not isinstance(raw, list):
            malformed += 1
            continue
        candidates.extend((requirement_type, item) for item in raw)
    return candidates, malformed


def _yaml_candidates(text: str) -> tuple[list[tuple[str, object]], int]:
    """Extract common Galaxy YAML shapes with an indentation-bounded parser."""

    candidates: list[tuple[str, object]] = []
    malformed = 0
    section: str | None = None
    section_indent = -1
    item_indent: int | None = None
    field_indent: int | None = None
    fields: dict[str, str] = {}

    def flush() -> None:
        nonlocal malformed
        if section is None or item_indent is None:
            fields.clear()
            return
        if fields:
            if "include" in fields:
                candidates.append(("include", fields["include"]))
            else:
                candidates.append((section, dict(fields)))
        else:
            malformed += 1
        fields.clear()

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith(("#", "---", "...")):
            continue
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            malformed += 1
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        section_match = _SECTION_RE.match(stripped) if indent == 0 else None
        if section_match:
            flush()
            section = "role" if section_match.group(1) == "roles" else "collection"
            section_indent = indent
            item_indent = None
            inline = section_match.group(2).strip()
            if inline and inline not in _EMPTY_SEQUENCE_VALUES:
                malformed += 1
            continue
        if section is None:
            # A top-level sequence is the historical role-only Galaxy format.
            if indent == 0 and stripped.startswith("-"):
                section = "role"
                section_indent = -1
            else:
                malformed += 1
                continue
        if indent <= section_indent:
            flush()
            section = None
            item_indent = None
            malformed += 1
            continue
        if stripped.startswith("-"):
            flush()
            item_indent = indent
            field_indent = None
            body = stripped[1:].strip()
            if not body:
                continue
            field = _FIELD_RE.match(body)
            if field:
                value = _clean_scalar(field.group(2))
                if value is not None:
                    fields[field.group(1)] = value
            else:
                scalar = _clean_scalar(body)
                if scalar is not None and (_looks_like_role_source(scalar) or ":" not in scalar):
                    if section == "role" and _looks_like_role_source(scalar):
                        fields["src"] = scalar
                    else:
                        fields["name"] = scalar
                elif scalar is None:
                    malformed += 1
                    item_indent = None
            continue
        if item_indent is None or indent <= item_indent:
            malformed += 1
            continue
        if field_indent is None:
            field_indent = indent
        if indent != field_indent:
            continue
        field = _FIELD_RE.match(stripped)
        if field:
            value = _clean_scalar(field.group(2))
            if value is not None:
                fields[field.group(1)] = value
        # Nested installer options are intentionally ignored; they do not
        # identify the dependency and must not become self-authorizing facts.
    flush()
    return candidates, malformed


def parse_galaxy_requirements(text: str) -> GalaxyParseResult:
    """Parse common role/collection YAML shapes with explicit degradation."""

    stripped = text.lstrip()
    if not stripped:
        return GalaxyParseResult(())
    if stripped.startswith(("{", "[")):
        try:
            candidates, malformed = _json_candidates(json.loads(text))
        except json.JSONDecodeError:
            return GalaxyParseResult((), (), ("Ansible Galaxy requirements are malformed",))
    else:
        candidates, malformed = _yaml_candidates(text)
    return _bounded_result(candidates, malformed)
