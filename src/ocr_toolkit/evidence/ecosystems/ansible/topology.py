"""Derive bounded Ansible topology facts from immutable repository blobs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from ocr_toolkit.evidence.coverage import CoverageObservation
from ocr_toolkit.evidence.model import CoverageState

MAX_TOPOLOGY_ITEMS = 256
PLAYBOOK_KEY_RE = re.compile(r"^(?P<indent>\s*)[\"']?(?P<key>hosts|import_playbook)[\"']?\s*:")
INI_GROUP_RE = re.compile(r"^\s*\[(?P<group>[^]#:]+)(?::children|:vars)?]\s*$")
YAML_GROUP_RE = re.compile(
    r"^(?P<indent>\s*)(?P<quote>[\"']?)(?P<group>[A-Za-z0-9_.:-]+)(?P=quote):"
    r"(?:\s*\{\s*})?\s*$"
)
YAML_CHILDREN_RE = re.compile(r"^(?P<indent>\s*)children:\s*$")
DYNAMIC_PLUGIN_RE = re.compile(r"^[\"']?plugin[\"']?\s*:\s*(?P<value>[^#\r\n]+?)\s*$", re.MULTILINE)
ROLE_EXTENSIONS = {"", ".json", ".yaml", ".yml"}
UNSUPPORTED_STATIC_YAML_RE = re.compile(r"(?:\{\{|{%|&[A-Za-z]|\*[A-Za-z]|<<\s*:)")


@dataclass(frozen=True, slots=True)
class AnsibleTopologyFact:
    """Describe one normalized Ansible path or inventory-group fact."""

    kind: str
    identity: str
    value: dict[str, str]


def topology_candidate(path: str, *, executable: bool = False) -> bool:
    """Return whether a normalized path can contribute Ansible topology."""

    parts = PurePosixPath(path).parts
    if not parts:
        return False
    name = parts[-1].casefold()
    return (
        (len(parts) == 1 and name.endswith((".yml", ".yaml")))
        or _role_surface(path) is not None
        or _is_inventory_path(path, executable=executable)
    )


def _role_surface(path: str) -> tuple[str, str] | None:
    """Return role name and supported topology surface for a canonical role path."""

    parts = PurePosixPath(path).parts
    folded = tuple(part.casefold() for part in parts)
    if (
        len(parts) < 4
        or folded[0] != "roles"
        or folded[2]
        not in {
            "meta",
            "defaults",
            "vars",
        }
    ):
        return None
    canonical_file = len(parts) == 4 and folded[3] in {
        "main",
        "main.json",
        "main.yml",
        "main.yaml",
    }
    recursive_main = (
        len(parts) > 4
        and folded[2] in {"defaults", "vars"}
        and folded[3] == "main"
        and _supported_role_main_descendant(parts[4:])
    )
    if canonical_file or recursive_main:
        surface = "metadata" if folded[2] == "meta" else folded[2]
        return parts[1], surface
    return None


def _supported_role_main_descendant(parts: tuple[str, ...]) -> bool:
    """Mirror Ansible 2.17-2.21/devel recursive vars-file selection."""

    if not parts:
        return False
    if any(part.startswith(".") or part.endswith("~") for part in parts):
        return False
    if any(PurePosixPath(part).suffix for part in parts[:-1]):
        return False
    return PurePosixPath(parts[-1]).suffix.casefold() in ROLE_EXTENSIONS


def _is_inventory_path(path: str, *, executable: bool = False) -> bool:
    """Recognize conventional inventory paths while excluding variable payloads."""

    pure = PurePosixPath(path)
    parts = pure.parts
    if not parts:
        return False
    name = parts[-1].casefold()
    folded = tuple(part.casefold() for part in parts)
    if "group_vars" in folded or "host_vars" in folded:
        return False
    conventional = name in {
        "hosts",
        "hosts.ini",
        "hosts.yml",
        "hosts.yaml",
        "inventory",
        "inventory.ini",
        "inventory.yml",
        "inventory.yaml",
    } or (
        ("inventory" in folded or "inventories" in folded)
        and pure.suffix.casefold() in {"", ".ini", ".yml", ".yaml"}
    )
    return conventional or (executable and ("inventory" in folded or "inventories" in folded))


def inventory_scope(path: str) -> str:
    """Return the conservative directory scope for one inventory source."""

    parent = PurePosixPath(path).parent.as_posix()
    return "." if parent == "." else parent


def role_coverage_scope(path: str) -> tuple[str, str] | None:
    """Return coverage domain and role loader scope for defaults/vars paths."""

    parts = PurePosixPath(path).parts
    folded = tuple(part.casefold() for part in parts)
    if len(parts) < 4 or folded[0] != "roles" or folded[2] not in {"defaults", "vars"}:
        return None
    if _role_surface(path) is None:
        return None
    return f"role.{folded[2]}", "/".join((*parts[:3], "main"))


def selected_role_paths(paths: tuple[str, ...]) -> frozenset[str]:
    """Select the role files Ansible loads, including recursive main directories."""

    grouped: dict[tuple[str, str], set[str]] = {}
    for path in paths:
        role_surface = _role_surface(path)
        if role_surface is None:
            continue
        role, name = role_surface
        grouped.setdefault((role, name), set()).add(path)
    selected: set[str] = set()
    for (role, surface), candidates in grouped.items():
        directory = "meta" if surface == "metadata" else surface
        prefix = f"roles/{role}/{directory}"
        for name in ("main.yml", "main.yaml", "main.json", "main"):
            candidate = f"{prefix}/{name}"
            if candidate in candidates:
                selected.add(candidate)
                break
        else:
            selected.update(path for path in candidates if path.startswith(f"{prefix}/main/"))
    return frozenset(selected)


def _is_root_playbook(path: str, text: str) -> bool:
    """Recognize a root-level playbook from bounded YAML structure signals."""

    pure = PurePosixPath(path)
    if len(pure.parts) != 1 or pure.suffix.casefold() not in {".yml", ".yaml"}:
        return False
    top_level_list_item = False
    play_child_indent: int | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in {"---", "..."}:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0 and stripped.startswith("-"):
            top_level_list_item = True
            play_child_indent = None
            if PLAYBOOK_KEY_RE.match(stripped[1:].lstrip()):
                return True
            continue
        if indent == 0:
            top_level_list_item = False
            play_child_indent = None
            continue
        if not top_level_list_item:
            continue
        if play_child_indent is None:
            play_child_indent = indent
        if indent == play_child_indent and PLAYBOOK_KEY_RE.match(stripped):
            return True
    return False


def _inventory_groups(text: str) -> tuple[tuple[str, ...], bool]:
    """Extract bounded INI and YAML inventory group names without a YAML runtime."""

    groups: set[str] = set()
    children_indent: int | None = None
    group_indent: int | None = None
    top_level_group: str | None = None
    for raw_line in text.splitlines():
        ini = INI_GROUP_RE.match(raw_line)
        if ini:
            groups.add(ini.group("group").strip())
            if len(groups) >= MAX_TOPOLOGY_ITEMS:
                return tuple(sorted(groups)), True
            continue
        children = YAML_CHILDREN_RE.match(raw_line)
        if children:
            children_indent = len(children.group("indent"))
            group_indent = None
            continue
        yaml_group = YAML_GROUP_RE.match(raw_line)
        if yaml_group and len(yaml_group.group("indent")) == 0:
            group = yaml_group.group("group")
            top_level_group = group if group not in {"all", "ungrouped"} else None
            if top_level_group is not None and re.search(r"\{\s*\}\s*$", raw_line):
                groups.add(top_level_group)
                if len(groups) >= MAX_TOPOLOGY_ITEMS:
                    return tuple(sorted(groups)), True
            children_indent = None
            group_indent = None
            continue
        if (
            yaml_group
            and top_level_group is not None
            and yaml_group.group("group") in {"hosts", "children", "vars"}
        ):
            groups.add(top_level_group)
            if yaml_group.group("group") == "children":
                children_indent = len(yaml_group.group("indent"))
                group_indent = None
            continue
        if yaml_group and children_indent is not None:
            indent = len(yaml_group.group("indent"))
            if indent <= children_indent:
                children_indent = None
                group_indent = None
            else:
                # YAML indentation width is repository-defined; the first key
                # below children establishes the sibling group depth.
                if group_indent is None:
                    group_indent = indent
                if indent == group_indent:
                    groups.add(yaml_group.group("group"))
                    if len(groups) >= MAX_TOPOLOGY_ITEMS:
                        return tuple(sorted(groups)), True
    return tuple(sorted(groups)), False


def _dynamic_inventory(text: str) -> bool:
    """Recognize a scalar plugin declaration without resolving its value."""

    match = DYNAMIC_PLUGIN_RE.search(text)
    if match is None:
        return False
    value = match.group("value").strip().strip("\"'")
    return bool(value)


def _static_inventory_supported(path: str, text: str) -> bool:
    """Recognize the closed static syntax for which group enumeration is complete."""

    if "\t" in text or "\x00" in text:
        return False
    logical = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not logical:
        return True
    ini_source = PurePosixPath(path).suffix.casefold() == ".ini" or logical[0].startswith("[")
    if ini_source:
        return all(
            not line.startswith("[") or INI_GROUP_RE.match(line) is not None for line in logical
        )
    if UNSUPPORTED_STATIC_YAML_RE.search(text):
        return False
    for line in logical:
        if line in {"---", "..."} or line.startswith("-"):
            continue
        if ":" not in line:
            return False
        key, value = (part.strip() for part in line.split(":", 1))
        if key.startswith(('"', "'")) and not key.endswith(key[0]):
            return False
        if (
            value
            and value != "{}"
            and any(marker in value for marker in ("[", "]", "{", "}", "|", ">"))
        ):
            return False
    return True


def topology_coverage(
    path: str, text: str, *, executable: bool = False
) -> tuple[str, str, CoverageObservation] | None:
    """Return one source-level completeness observation for aggregation."""

    if _is_inventory_path(path, executable=executable):
        groups, truncated = _inventory_groups(text)
        if executable or _dynamic_inventory(text):
            return (
                "inventory.groups",
                inventory_scope(path),
                CoverageObservation(
                    CoverageState.RUNTIME_DEPENDENT,
                    "executable-source" if executable else "dynamic-source",
                    positive=bool(groups),
                ),
            )
        supported = _static_inventory_supported(path, text)
        state = (
            CoverageState.PARTIAL
            if truncated or (not supported and bool(groups))
            else CoverageState.COMPLETE
            if supported
            else CoverageState.UNAVAILABLE
        )
        return (
            "inventory.groups",
            inventory_scope(path),
            CoverageObservation(
                state,
                "group-limit"
                if truncated
                else "static-source"
                if supported
                else "unsupported-static-syntax",
                positive=bool(groups) or supported,
            ),
        )
    role_scope = role_coverage_scope(path)
    if role_scope is not None:
        return (
            role_scope[0],
            role_scope[1],
            CoverageObservation(CoverageState.COMPLETE, "bounded-role-source", positive=True),
        )
    return None


def collect_topology(
    path: str, text: str, *, executable: bool = False
) -> tuple[AnsibleTopologyFact, ...]:
    """Collect typed Ansible topology facts for one immutable path and blob."""

    facts = []
    if _is_root_playbook(path, text):
        facts.append(AnsibleTopologyFact("ansible.playbook", path, {"path": path, "scope": "root"}))
    role_surface = _role_surface(path)
    if role_surface is not None:
        role, surface = role_surface
        facts.append(
            AnsibleTopologyFact(
                f"ansible.role_{surface}",
                path,
                {"role": role, "path": path},
            )
        )
    if _is_inventory_path(path, executable=executable):
        groups, truncated = _inventory_groups(text)
        source_type = (
            "executable" if executable else "dynamic" if _dynamic_inventory(text) else "static"
        )
        static_supported = _static_inventory_supported(path, text)
        group_coverage = (
            "runtime-dependent"
            if source_type in {"dynamic", "executable"}
            else "partial"
            if truncated or (not static_supported and bool(groups))
            else "unavailable"
            if not static_supported
            else "complete"
        )
        facts.append(
            AnsibleTopologyFact(
                "ansible.inventory",
                path,
                {
                    "path": path,
                    "source_type": source_type,
                    "group_coverage": group_coverage,
                },
            )
        )
        facts.extend(
            AnsibleTopologyFact(
                "ansible.inventory_group",
                f"{path}:{group}",
                {"path": path, "group": group},
            )
            for group in groups
        )
    return tuple(facts)
