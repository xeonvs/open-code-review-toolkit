"""Derive bounded Ansible topology facts from immutable repository blobs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_TOPOLOGY_ITEMS = 256
PLAYBOOK_KEY_RE = re.compile(r"^(?P<indent>\s*)[\"']?(?P<key>hosts|import_playbook)[\"']?\s*:")
INI_GROUP_RE = re.compile(r"^\s*\[(?P<group>[^]#:]+)(?::children|:vars)?]\s*$")
YAML_GROUP_RE = re.compile(r"^(?P<indent>\s*)(?P<group>[A-Za-z0-9_.:-]+):(?:\s*\{\s*})?\s*$")
YAML_CHILDREN_RE = re.compile(r"^(?P<indent>\s*)children:\s*$")


@dataclass(frozen=True, slots=True)
class AnsibleTopologyFact:
    """Describe one normalized Ansible path or inventory-group fact."""

    kind: str
    identity: str
    value: dict[str, str]


def topology_candidate(path: str) -> bool:
    """Return whether a normalized path can contribute Ansible topology."""

    parts = PurePosixPath(path).parts
    if not parts:
        return False
    name = parts[-1].casefold()
    return (
        (len(parts) == 1 and name.endswith((".yml", ".yaml")))
        or _role_surface(path) is not None
        or _is_inventory_path(path)
    )


def _role_surface(path: str) -> tuple[str, str] | None:
    """Return role name and supported topology surface for a canonical role path."""

    parts = PurePosixPath(path).parts
    folded = tuple(part.casefold() for part in parts)
    if (
        len(parts) == 4
        and folded[0] == "roles"
        and folded[2] in {"meta", "defaults", "vars"}
        and folded[3] in {"main.yml", "main.yaml"}
    ):
        surface = "metadata" if folded[2] == "meta" else folded[2]
        return parts[1], surface
    return None


def _is_inventory_path(path: str) -> bool:
    """Recognize conventional inventory paths while excluding variable payloads."""

    parts = PurePosixPath(path).parts
    if not parts:
        return False
    name = parts[-1].casefold()
    folded = tuple(part.casefold() for part in parts)
    if "group_vars" in folded or "host_vars" in folded:
        return False
    return (
        name
        in {
            "hosts",
            "hosts.ini",
            "hosts.yml",
            "hosts.yaml",
            "inventory",
            "inventory.ini",
            "inventory.yml",
            "inventory.yaml",
        }
        or "inventory" in folded
        or "inventories" in folded
    )


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


def _inventory_groups(text: str) -> tuple[str, ...]:
    """Extract bounded INI and YAML inventory group names without a YAML runtime."""

    groups: set[str] = set()
    children_indent: int | None = None
    for raw_line in text.splitlines():
        ini = INI_GROUP_RE.match(raw_line)
        if ini:
            groups.add(ini.group("group").strip())
            if len(groups) >= MAX_TOPOLOGY_ITEMS:
                break
            continue
        children = YAML_CHILDREN_RE.match(raw_line)
        if children:
            children_indent = len(children.group("indent"))
            continue
        yaml_group = YAML_GROUP_RE.match(raw_line)
        if yaml_group and children_indent is not None:
            indent = len(yaml_group.group("indent"))
            if indent <= children_indent:
                children_indent = None
            elif indent == children_indent + 2:
                groups.add(yaml_group.group("group"))
                if len(groups) >= MAX_TOPOLOGY_ITEMS:
                    break
    return tuple(sorted(groups))


def collect_topology(path: str, text: str) -> tuple[AnsibleTopologyFact, ...]:
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
    if _is_inventory_path(path):
        facts.append(AnsibleTopologyFact("ansible.inventory", path, {"path": path}))
        facts.extend(
            AnsibleTopologyFact(
                "ansible.inventory_group",
                f"{path}:{group}",
                {"path": path, "group": group},
            )
            for group in _inventory_groups(text)
        )
    return tuple(facts)
