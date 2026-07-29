"""Parse bounded immutable manifest blobs into typed repository evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

import tomllib  # type: ignore[import-untyped]

from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceValue,
    RefRole,
    TrustClass,
)
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError

MAX_MANIFEST_ITEMS = 512
REQUIREMENT_RE = re.compile(
    r"^([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)\s*"
    r"(?:===|==|~=|>=|<=|!=|>|<)\s*([^;\s]+)"
)
IMAGE_LINE_RE = re.compile(r"^\s*image\s*:\s*['\"]?([^'\"\s#]+)")
ANSIBLE_NAME_RE = re.compile(r"^\s*-?\s*name\s*:\s*['\"]?([^'\"#\s]+)")
ANSIBLE_VERSION_RE = re.compile(r"^\s*version\s*:\s*['\"]?([^'\"#\s]+)")
GUIDANCE_PATHS = {
    "PR_REVIEW.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
}
ACCEPTED_DECISIONS_PATH = ".opencodereview/accepted-decisions.md"
CONTEXT_YAML_DIRECTORIES = (
    ".circleci/",
    ".github/workflows/",
    "deploy/",
    "k8s/",
    "kubernetes/",
    "manifests/",
)


@dataclass(frozen=True, slots=True)
class ManifestFact:
    """Describe one normalized typed fact before ref provenance is attached."""

    kind: str
    component: str
    identity: str
    value: EvidenceValue


@dataclass(frozen=True, slots=True)
class ManifestCollector:
    """Bind manifest path matching, ecosystem metadata, and a bounded parser."""

    ecosystem: str
    matches: Callable[[str], bool]
    parse: Callable[[str], list[ManifestFact]]


def _dependency(kind: str, component: str, name: str, version: object, scope: str) -> ManifestFact:
    """Create one normalized dependency fact."""

    return ManifestFact(
        kind,
        component,
        f"{scope}:{name.casefold()}",
        {"name": name, "version": str(version), "scope": scope},
    )


def _mapping_dependencies(
    data: Mapping[str, object], kind: str, component: str, scope: str
) -> list[ManifestFact]:
    """Collect bounded string dependency entries from one mapping."""

    facts = []
    for name, version in sorted(data.items())[:MAX_MANIFEST_ITEMS]:
        if isinstance(name, str) and isinstance(version, (str, int, float)):
            facts.append(_dependency(kind, component, name, version, scope))
    return facts


def _parse_pyproject(text: str) -> list[ManifestFact]:
    """Parse PEP 621 and Poetry dependency declarations."""

    data = tomllib.loads(text)
    facts: list[ManifestFact] = []
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
            for value in dependencies[:MAX_MANIFEST_ITEMS]:
                if not isinstance(value, str):
                    continue
                match = REQUIREMENT_RE.match(value)
                name = match.group(1) if match else value.split(";", 1)[0].strip()
                version = match.group(2) if match else value
                if name:
                    facts.append(
                        _dependency("dependency.declared", "python", name, version, "project")
                    )
    tool = data.get("tool") if isinstance(data, dict) else None
    dependency_groups = data.get("dependency-groups") if isinstance(data, dict) else None
    if isinstance(dependency_groups, dict):
        for group_name, dependencies in sorted(dependency_groups.items()):
            if not isinstance(dependencies, list):
                continue
            for value in dependencies[:MAX_MANIFEST_ITEMS]:
                if not isinstance(value, str):
                    continue
                match = REQUIREMENT_RE.match(value)
                name = match.group(1) if match else value.split(";", 1)[0].strip()
                version = match.group(2) if match else value
                if name:
                    facts.append(
                        _dependency(
                            "dependency.declared",
                            "python",
                            name,
                            version,
                            f"group:{group_name}",
                        )
                    )
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    if isinstance(poetry, dict):
        dependencies = poetry.get("dependencies")
        if isinstance(dependencies, dict):
            facts.extend(
                _mapping_dependencies(dependencies, "dependency.declared", "python", "poetry")
            )
        groups = poetry.get("group")
        if isinstance(groups, dict):
            for group_name, raw_group in sorted(groups.items()):
                dependencies = (
                    raw_group.get("dependencies") if isinstance(raw_group, dict) else None
                )
                if isinstance(dependencies, dict):
                    facts.extend(
                        _mapping_dependencies(
                            dependencies,
                            "dependency.declared",
                            "python",
                            f"poetry-group:{group_name}",
                        )
                    )
    return facts


def _parse_requirements(text: str) -> list[ManifestFact]:
    """Parse bounded pinned or constrained Python requirement lines."""

    facts = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith(("#", "-")):
            continue
        match = REQUIREMENT_RE.match(clean)
        if match:
            facts.append(
                _dependency(
                    "dependency.declared", "python", match.group(1), match.group(2), "requirements"
                )
            )
        if len(facts) >= MAX_MANIFEST_ITEMS:
            break
    return facts


def _parse_package_json(text: str) -> list[ManifestFact]:
    """Parse JavaScript runtime and dependency declarations."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("package.json must contain an object")
    facts = []
    for key, scope in (("dependencies", "runtime"), ("devDependencies", "development")):
        values = data.get(key)
        if isinstance(values, dict):
            facts.extend(_mapping_dependencies(values, "dependency.declared", "javascript", scope))
    engines = data.get("engines")
    if isinstance(engines, dict):
        for name, constraint in sorted(engines.items()):
            if isinstance(name, str) and isinstance(constraint, str):
                facts.append(
                    ManifestFact(
                        "runtime.declared",
                        "javascript",
                        name.casefold(),
                        {"name": name, "constraint": constraint},
                    )
                )
    return facts[:MAX_MANIFEST_ITEMS]


def _parse_package_lock(text: str) -> list[ManifestFact]:
    """Parse resolved versions from npm lockfile packages or dependencies."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("package-lock.json must contain an object")
    packages = data.get("packages")
    facts = []
    if isinstance(packages, dict):
        for path, raw in sorted(packages.items()):
            if not path or not isinstance(raw, dict):
                continue
            version = raw.get("version")
            name = raw.get("name") or str(path).removeprefix("node_modules/")
            if isinstance(name, str) and isinstance(version, str):
                facts.append(_dependency("dependency.locked", "javascript", name, version, "npm"))
            if len(facts) >= MAX_MANIFEST_ITEMS:
                break
    return facts


def _parse_go_mod(text: str) -> list[ManifestFact]:
    """Parse Go language and module requirement declarations."""

    facts = []
    in_require = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("go "):
            facts.append(
                ManifestFact(
                    "runtime.declared", "go", "go", {"name": "go", "constraint": line[3:].strip()}
                )
            )
        elif line == "require (":
            in_require = True
        elif line == ")" and in_require:
            in_require = False
        elif line.startswith("require ") or in_require:
            body = line.removeprefix("require ").split("//", 1)[0].strip()
            parts = body.split()
            if len(parts) >= 2:
                facts.append(_dependency("dependency.declared", "go", parts[0], parts[1], "module"))
        if len(facts) >= MAX_MANIFEST_ITEMS:
            break
    return facts


def _parse_composer(text: str, *, locked: bool) -> list[ManifestFact]:
    """Parse Composer declared or locked package versions."""

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Composer manifest must contain an object")
    facts = []
    if locked:
        for scope in ("packages", "packages-dev"):
            packages = data.get(scope)
            if isinstance(packages, list):
                for raw in packages:
                    if (
                        isinstance(raw, dict)
                        and isinstance(raw.get("name"), str)
                        and isinstance(raw.get("version"), str)
                    ):
                        facts.append(
                            _dependency(
                                "dependency.locked", "php", raw["name"], raw["version"], scope
                            )
                        )
    else:
        for scope in ("require", "require-dev"):
            values = data.get(scope)
            if isinstance(values, dict):
                facts.extend(_mapping_dependencies(values, "dependency.declared", "php", scope))
    return facts[:MAX_MANIFEST_ITEMS]


def _parse_ansible_requirements(text: str) -> list[ManifestFact]:
    """Parse bounded Ansible collection/role name and version pairs."""

    facts = []
    pending_name: str | None = None
    for line in text.splitlines():
        name = ANSIBLE_NAME_RE.match(line)
        if name:
            pending_name = name.group(1)
            continue
        version = ANSIBLE_VERSION_RE.match(line)
        if version and pending_name:
            facts.append(
                _dependency(
                    "dependency.declared",
                    "ansible",
                    pending_name,
                    version.group(1),
                    "requirements",
                )
            )
            pending_name = None
        if len(facts) >= MAX_MANIFEST_ITEMS:
            break
    return facts


def _parse_composer_declared(text: str) -> list[ManifestFact]:
    """Parse declared Composer requirements through the shared bounded parser."""

    return _parse_composer(text, locked=False)


def _parse_composer_locked(text: str) -> list[ManifestFact]:
    """Parse resolved Composer packages through the shared bounded parser."""

    return _parse_composer(text, locked=True)


def _name_is(*names: str) -> Callable[[str], bool]:
    """Build a case-insensitive basename matcher for the manifest registry."""

    normalized = frozenset(name.casefold() for name in names)
    return lambda path: PurePosixPath(path).name.casefold() in normalized


def _is_python_requirements(path: str) -> bool:
    """Match Python requirement manifests without matching Ansible YAML."""

    name = PurePosixPath(path).name.casefold()
    return name.startswith("requirements") and name.endswith(".txt")


MANIFEST_COLLECTORS = (
    ManifestCollector("python", _name_is("pyproject.toml"), _parse_pyproject),
    ManifestCollector("python", _is_python_requirements, _parse_requirements),
    ManifestCollector("javascript", _name_is("package.json"), _parse_package_json),
    ManifestCollector("javascript", _name_is("package-lock.json"), _parse_package_lock),
    ManifestCollector("go", _name_is("go.mod"), _parse_go_mod),
    ManifestCollector("php", _name_is("composer.json"), _parse_composer_declared),
    ManifestCollector("php", _name_is("composer.lock"), _parse_composer_locked),
    ManifestCollector(
        "ansible",
        _name_is("requirements.yml", "requirements.yaml"),
        _parse_ansible_requirements,
    ),
)


def manifest_collector(path: str) -> ManifestCollector | None:
    """Return the single registered collector for a repository path."""

    matches = tuple(collector for collector in MANIFEST_COLLECTORS if collector.matches(path))
    if len(matches) > 1:
        raise ValueError(f"manifest registry has ambiguous collectors for {path}")
    return matches[0] if matches else None


def parse_manifest(path: str, text: str) -> list[ManifestFact]:
    """Parse a supported manifest through the authoritative collector registry."""

    collector = manifest_collector(path)
    return collector.parse(text) if collector else []


def is_supported_manifest(path: str) -> bool:
    """Return whether a repository path has a registered typed parser."""

    return manifest_collector(path) is not None


def _image_reference(reference: str) -> tuple[str, str | None]:
    """Split an OCI-style reference into stable name and mutable version parts."""

    if "@" in reference:
        name, digest = reference.rsplit("@", 1)
        return name, digest
    slash = reference.rfind("/")
    colon = reference.rfind(":")
    if colon > slash:
        return reference[:colon], reference[colon + 1 :]
    return reference, None


def _image_facts(path: str, text: str) -> list[ManifestFact]:
    """Extract bounded exact image references from CI/container YAML lines."""

    kind = (
        "ci.image"
        if PurePosixPath(path).name.casefold().startswith(".gitlab-ci")
        else "container.image"
    )
    facts = []
    for line in text.splitlines():
        match = IMAGE_LINE_RE.match(line)
        if match:
            image = match.group(1)
            name, version = _image_reference(image)
            facts.append(
                ManifestFact(
                    kind,
                    "ci" if kind == "ci.image" else "container",
                    name.casefold(),
                    {"image": image, "name": name, "version": version},
                )
            )
        if len(facts) >= MAX_MANIFEST_ITEMS:
            break
    return facts


def _is_context_yaml(path: str, changed: set[str]) -> bool:
    """Select YAML that can affect this review or a known CI/container surface."""

    folded = path.casefold()
    if not folded.endswith((".yml", ".yaml")):
        return False
    name = PurePosixPath(folded).name
    return (
        folded in changed
        or name.startswith((".gitlab-ci", "compose.", "docker-compose."))
        or folded.startswith(CONTEXT_YAML_DIRECTORIES)
    )


def collect_ref_facts(
    reader: GitRepositoryReader,
    commit_sha: str,
    ref: RefRole,
    *,
    changed_paths: Iterable[str] = (),
) -> tuple[list[EvidenceRecord], list[str]]:
    """Collect supported facts from one immutable tree with explicit diagnostics."""

    records = []
    diagnostics = []
    trust = TrustClass.TARGET_REPOSITORY if ref == RefRole.BASE else TrustClass.SOURCE_REPOSITORY
    changed = {path.casefold() for path in changed_paths}
    entries = reader.list_objects(commit_sha)
    candidates = tuple(
        entry
        for entry in entries
        if (
            is_supported_manifest(entry.path)
            or PurePosixPath(entry.path).name.casefold().startswith(".gitlab-ci")
            or _is_context_yaml(entry.path, changed)
            or entry.path in GUIDANCE_PATHS
            or entry.path.casefold() == ACCEPTED_DECISIONS_PATH
        )
        and not entry.is_symlink
        and not entry.is_submodule
        and entry.object_type == "blob"
    )
    try:
        read = reader.read_candidate_blobs(candidates)
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"collector batch read failed: {exc}")
        return records, diagnostics
    blobs = read.blobs
    diagnostics.extend(f"{ref.value}:{message}" for message in read.diagnostics)
    for entry in candidates:
        path = entry.path
        if path not in blobs:
            # Bounded candidate omissions are already represented by explicit
            # coverage diagnostics; they must not abort the remaining facts.
            continue
        path_folded = path.casefold()
        image_source = PurePosixPath(path).name.casefold().startswith(
            ".gitlab-ci"
        ) or _is_context_yaml(path, changed)
        guidance_source = path in GUIDANCE_PATHS or path_folded == ACCEPTED_DECISIONS_PATH
        if not is_supported_manifest(path) and not image_source and not guidance_source:
            continue
        try:
            blob = blobs[path]
            text = blob.decode("utf-8")
            if is_supported_manifest(path):
                collector = manifest_collector(path)
                if collector is None:  # pragma: no cover - guarded by registry predicate
                    raise ValueError("supported manifest has no collector")
                facts = [
                    ManifestFact(
                        "repository.manifest",
                        collector.ecosystem,
                        path,
                        {"path": path, "ecosystem": collector.ecosystem},
                    ),
                    *collector.parse(text),
                ]
            elif guidance_source:
                facts = (
                    []
                    if ref == RefRole.HEAD and path_folded in changed
                    else [
                        ManifestFact(
                            "repository.accepted_decision"
                            if path_folded == ACCEPTED_DECISIONS_PATH
                            else "repository.guidance",
                            "repository",
                            path_folded,
                            {"text": text},
                        )
                    ]
                )
            else:
                facts = _image_facts(path, text)
        except (
            RepositoryEvidenceError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            tomllib.TOMLDecodeError,
            ValueError,
            RecursionError,
        ) as exc:
            diagnostics.append(
                f"{ref.value}:{path}: typed collection unavailable ({type(exc).__name__})"
            )
            continue
        for fact in facts:
            identity = (
                f"{path}:{fact.identity}"
                if fact.kind.startswith(("dependency.", "runtime.", "ci.", "container."))
                else fact.identity
            )
            records.append(
                EvidenceRecord(
                    kind=fact.kind,
                    value={"identity": identity, "fact": fact.value},
                    source_path=path,
                    ref=ref,
                    commit_sha=commit_sha,
                    component=fact.component,
                    provenance=f"typed parser:{PurePosixPath(path).name}",
                    confidence=Confidence.EXACT,
                    trust=trust,
                )
            )
    return records, diagnostics


def fact_deltas(records: Iterable[EvidenceRecord]) -> tuple[EvidenceDelta, ...]:
    """Build reproducible typed deltas keyed by kind/component/identity."""

    base: dict[tuple[str, str, str], EvidenceRecord] = {}
    head: dict[tuple[str, str, str], EvidenceRecord] = {}
    for record in records:
        if not isinstance(record.value, dict) or not isinstance(record.value.get("identity"), str):
            continue
        key = (record.kind, record.component, record.value["identity"])
        if record.ref == RefRole.BASE:
            base[key] = record
        elif record.ref == RefRole.HEAD:
            head[key] = record
    deltas = []
    for key in sorted(set(base) | set(head)):
        before = base.get(key)
        after = head.get(key)
        before_value = (
            before.value.get("fact") if before and isinstance(before.value, dict) else None
        )
        after_value = after.value.get("fact") if after and isinstance(after.value, dict) else None
        change = "removed" if after is None else "added" if before is None else "changed"
        if before is not None and after is not None and before_value == after_value:
            continue
        deltas.append(EvidenceDelta(key[0], key[1], key[2], change, before_value, after_value))
    return tuple(deltas)
