"""Parse bounded immutable manifest blobs into typed repository evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

from ocr_toolkit.evidence.ansible import (
    collect_topology,
    inventory_scope,
    role_coverage_scope,
    selected_role_paths,
    topology_candidate,
    topology_coverage,
)
from ocr_toolkit.evidence.ansible_requirements import parse_galaxy_requirements
from ocr_toolkit.evidence.composer_manifests import parse_composer_json, parse_composer_lock
from ocr_toolkit.evidence.coverage import CoverageObservation, compose_coverage
from ocr_toolkit.evidence.framework_plugins import (
    FrameworkPluginContext,
    PluginCoverage,
    PluginFact,
    PluginSourceStatus,
    collect_framework_plugins,
    collect_template_files,
)
from ocr_toolkit.evidence.go_manifests import parse_go_mod, parse_go_sum
from ocr_toolkit.evidence.infrastructure import infrastructure_candidate, parse_infrastructure_pins
from ocr_toolkit.evidence.javascript_manifests import (
    parse_package_json,
    parse_package_lock,
    parse_pnpm_lock,
    parse_yarn_lock,
)
from ocr_toolkit.evidence.manifest_model import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import (
    Confidence,
    CoverageRecord,
    CoverageState,
    EvidenceDelta,
    EvidenceRecord,
    EvidenceValue,
    RefRole,
    TrustClass,
)
from ocr_toolkit.evidence.python_manifests import (
    parse_pipfile_lock,
    parse_poetry_lock,
    parse_pylock,
    parse_pyproject,
    parse_requirements,
    parse_uv_lock,
)
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryObject,
)

MAX_MANIFEST_INCLUDE_FILES = 32
MAX_MANIFEST_INCLUDE_DEPTH = 8
MAX_MANIFEST_INCLUDE_DIAGNOSTICS = 64
MAX_MANIFEST_INCLUDE_EDGES = 4_096
MAX_TOPOLOGY_FACTS_PER_KIND = 256
IMAGE_LINE_RE = re.compile(r"^\s*image\s*:\s*['\"]?([^'\"\s#]+)")
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
class ManifestCollector:
    """Bind manifest path matching, ecosystem metadata, role, and bounded parser."""

    ecosystem: str
    source_roles: tuple[str, ...]
    matches: Callable[[str], bool]
    parse: Callable[[str], ManifestParseResult]


@dataclass(frozen=True, slots=True)
class ManifestBlobSet:
    """Return immutable Galaxy blobs and explicit graph-read diagnostics."""

    blobs: dict[str, bytes]
    galaxy_paths: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PythonRequirementBlobSet:
    """Return immutable requirements blobs and graph-read diagnostics."""

    blobs: dict[str, bytes]
    requirement_paths: tuple[str, ...]
    diagnostics: tuple[str, ...]


def _parse_ansible_requirements(text: str) -> ManifestParseResult:
    """Parse Galaxy roles and collections while preserving optional fields."""

    parsed = parse_galaxy_requirements(text)
    facts = []
    for item in parsed.requirements:
        value: dict[str, EvidenceValue] = {
            "name": item.name,
            "requirement_type": item.requirement_type,
            "scope": item.requirement_type,
            "version": item.version,
            "version_state": "declared" if item.version is not None else "unspecified",
        }
        if item.source is not None:
            value["source"] = item.source
        facts.append(
            ManifestFact(
                "dependency.declared",
                "ansible",
                f"{item.requirement_type}:{item.name.casefold()}",
                value,
            )
        )
    return ManifestParseResult(tuple(facts), parsed.notices, parsed.include_paths)


def _name_is(*names: str) -> Callable[[str], bool]:
    """Build a case-insensitive basename matcher for the manifest registry."""

    normalized = frozenset(name.casefold() for name in names)
    return lambda path: PurePosixPath(path).name.casefold() in normalized


def _is_python_requirements(path: str) -> bool:
    """Match Python requirement manifests without matching Ansible YAML."""

    name = PurePosixPath(path).name.casefold()
    return name.startswith("requirements") and name.endswith((".txt", ".in"))


def _is_pylock(path: str) -> bool:
    """Match the standardized pylock.toml name and its permitted variants."""

    name = PurePosixPath(path).name.casefold()
    return name == "pylock.toml" or (name.startswith("pylock.") and name.endswith(".toml"))


MANIFEST_COLLECTORS = (
    ManifestCollector("python", ("declaration",), _name_is("pyproject.toml"), parse_pyproject),
    ManifestCollector("python", ("declaration",), _is_python_requirements, parse_requirements),
    ManifestCollector("python", ("resolution",), _name_is("uv.lock"), parse_uv_lock),
    ManifestCollector("python", ("resolution",), _name_is("poetry.lock"), parse_poetry_lock),
    ManifestCollector("python", ("resolution",), _name_is("Pipfile.lock"), parse_pipfile_lock),
    ManifestCollector("python", ("resolution",), _is_pylock, parse_pylock),
    ManifestCollector("javascript", ("declaration",), _name_is("package.json"), parse_package_json),
    ManifestCollector(
        "javascript",
        ("resolution",),
        _name_is("package-lock.json"),
        parse_package_lock,
    ),
    ManifestCollector("javascript", ("resolution",), _name_is("yarn.lock"), parse_yarn_lock),
    ManifestCollector("javascript", ("resolution",), _name_is("pnpm-lock.yaml"), parse_pnpm_lock),
    ManifestCollector("go", ("declaration", "resolution"), _name_is("go.mod"), parse_go_mod),
    ManifestCollector("go", ("checksum",), _name_is("go.sum"), parse_go_sum),
    ManifestCollector("php", ("declaration",), _name_is("composer.json"), parse_composer_json),
    ManifestCollector("php", ("resolution",), _name_is("composer.lock"), parse_composer_lock),
    ManifestCollector(
        "ansible",
        ("declaration",),
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
    return list(collector.parse(text).facts) if collector else []


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


def _resolve_manifest_include(
    path: str, include_path: str, *, suffixes: tuple[str, ...]
) -> str | None:
    """Resolve a local manifest include inside the immutable repository tree."""

    if (
        not include_path
        or include_path.startswith(("/", "~"))
        or "\x00" in include_path
        or ":" in include_path
        or "\\" in include_path
    ):
        return None
    parts: list[str] = []
    for part in (PurePosixPath(path).parent / include_path).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    resolved = "/".join(parts)
    return resolved if resolved.casefold().endswith(suffixes) else None


def _include_cycle_diagnostics(edges: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Describe one canonical closing edge per cyclic Galaxy component."""

    nodes = set(edges)
    nodes.update(target for targets in edges.values() for target in targets)
    visited: set[str] = set()
    finish_order: list[str] = []
    for root in sorted(nodes):
        if root in visited:
            continue
        visited.add(root)
        traversal: list[tuple[str, bool]] = [(root, False)]
        while traversal:
            path, expanded = traversal.pop()
            if expanded:
                finish_order.append(path)
                continue
            traversal.append((path, True))
            for target in reversed(sorted(edges.get(path, ()))):
                if target not in visited:
                    visited.add(target)
                    traversal.append((target, False))

    reverse_edges: dict[str, list[str]] = {path: [] for path in nodes}
    for path, targets in edges.items():
        for target in targets:
            reverse_edges[target].append(path)
    components: list[tuple[str, ...]] = []
    assigned: set[str] = set()
    for root in reversed(finish_order):
        if root in assigned:
            continue
        component: list[str] = []
        component_stack = [root]
        assigned.add(root)
        while component_stack:
            path = component_stack.pop()
            component.append(path)
            for source in reversed(sorted(reverse_edges[path])):
                if source not in assigned:
                    assigned.add(source)
                    component_stack.append(source)
        components.append(tuple(component))

    diagnostics: list[str] = []

    def component_key(path: str) -> tuple[int, str, str]:
        """Order graph paths by repository depth and stable spelling."""

        return path.count("/"), path.casefold(), path

    for component in sorted(components, key=lambda item: min(component_key(path) for path in item)):
        members = set(component)
        anchor = min(component, key=component_key)
        if len(component) == 1 and anchor not in edges.get(anchor, ()):
            continue
        # Every predecessor inside a strongly connected component closes a
        # path back to the canonical anchor; selecting one makes diagnostics
        # independent from root discovery and traversal order.
        source = min(
            (path for path in members if anchor in edges.get(path, ())),
            key=component_key,
        )
        diagnostics.append(f"{source}: Ansible Galaxy include cycle skipped: {anchor}")
    return tuple(diagnostics)


def _bound_include_diagnostics(
    diagnostics: list[str],
    *,
    truncation_notice: str = "Ansible Galaxy include diagnostics were truncated",
) -> tuple[str, ...]:
    """Cap graph diagnostics and retain one explicit truncation notice."""

    if len(diagnostics) <= MAX_MANIFEST_INCLUDE_DIAGNOSTICS:
        return tuple(diagnostics)
    return (
        *diagnostics[: MAX_MANIFEST_INCLUDE_DIAGNOSTICS - 1],
        truncation_notice,
    )


def _read_manifest_graph(
    reader: GitRepositoryReader,
    entries_by_path: Mapping[str, RepositoryObject],
    initial_paths: tuple[str, ...],
    initial_blobs: dict[str, bytes],
) -> ManifestBlobSet:
    """Read bounded Galaxy includes in one immutable Git batch per graph depth."""

    blobs = dict(initial_blobs)
    diagnostics: list[str] = []
    visited: set[str] = set()
    admitted = set(initial_paths)
    root_paths = set(initial_paths)
    edges: dict[str, list[str]] = {}
    pending = [(path, "") for path in initial_paths]
    included_files = 0
    file_limit_reported = False
    included_edges = 0
    edge_limit_reported = False
    for depth in range(MAX_MANIFEST_INCLUDE_DEPTH + 1):
        if not pending:
            break
        level_sources: dict[str, list[str]] = {}
        for path, included_from in pending:
            level_sources.setdefault(path, []).append(included_from)
        level = [
            (path, tuple(dict.fromkeys(level_sources[path]))) for path in sorted(level_sources)
        ]
        pending = []
        to_read: list[RepositoryObject] = []
        process_paths: list[str] = []
        for path, included_from_values in level:
            if path in visited:
                continue
            included_from = next((value for value in included_from_values if value), "")
            entry = entries_by_path.get(path)
            if entry is None or entry.is_symlink or entry.is_submodule:
                for source in included_from_values:
                    diagnostics.append(f"{source}: Ansible Galaxy include is missing: {path}")
                visited.add(path)
                continue
            if path not in root_paths and path not in admitted:
                if included_files >= MAX_MANIFEST_INCLUDE_FILES:
                    if not file_limit_reported:
                        diagnostics.append(
                            f"{included_from}: Ansible Galaxy includes were truncated after "
                            f"{MAX_MANIFEST_INCLUDE_FILES} files"
                        )
                        file_limit_reported = True
                    continue
                admitted.add(path)
                included_files += 1
            if path not in blobs:
                to_read.append(entry)
            process_paths.append(path)
        if to_read:
            read = reader.read_candidate_blobs(tuple(to_read))
            blobs.update(read.blobs)
            diagnostics.extend(read.diagnostics)
        for path in process_paths:
            visited.add(path)
            blob = blobs.get(path)
            if blob is None:
                continue
            try:
                parsed = parse_galaxy_requirements(blob.decode("utf-8"))
            except UnicodeDecodeError:
                diagnostics.append(f"{path}: Ansible Galaxy include is not UTF-8")
                continue
            for include_path in parsed.include_paths:
                resolved = _resolve_manifest_include(path, include_path, suffixes=(".yml", ".yaml"))
                if resolved is None:
                    diagnostics.append(f"{path}: invalid Ansible Galaxy include skipped")
                    continue
                if included_edges >= MAX_MANIFEST_INCLUDE_EDGES:
                    if not edge_limit_reported:
                        diagnostics.append(
                            f"{path}: Ansible Galaxy include graph was truncated after "
                            f"{MAX_MANIFEST_INCLUDE_EDGES} edges"
                        )
                        edge_limit_reported = True
                    continue
                included_edges += 1
                edges.setdefault(path, []).append(resolved)
                if depth >= MAX_MANIFEST_INCLUDE_DEPTH:
                    diagnostics.append(
                        f"{path}: Ansible Galaxy include depth exceeded at {resolved}"
                    )
                else:
                    pending.append((resolved, path))
    normalized_edges = {path: tuple(dict.fromkeys(targets)) for path, targets in edges.items()}
    diagnostics.extend(_include_cycle_diagnostics(normalized_edges))
    galaxy_paths = tuple(sorted(path for path in visited if path in blobs))
    return ManifestBlobSet(blobs, galaxy_paths, _bound_include_diagnostics(diagnostics))


def _read_python_requirement_graph(
    reader: GitRepositoryReader,
    entries_by_path: Mapping[str, RepositoryObject],
    initial_paths: tuple[str, ...],
    initial_blobs: dict[str, bytes],
) -> PythonRequirementBlobSet:
    """Read bounded local requirements includes from one immutable Git ref."""

    blobs = dict(initial_blobs)
    diagnostics: list[str] = []
    visited: set[str] = set()
    admitted = set(initial_paths)
    pending = [(path, "") for path in initial_paths]
    included_files = 0
    included_edges = 0
    file_limit_reported = False
    edge_limit_reported = False
    for depth in range(MAX_MANIFEST_INCLUDE_DEPTH + 1):
        if not pending:
            break
        level_sources: dict[str, list[str]] = {}
        for path, included_from in pending:
            level_sources.setdefault(path, []).append(included_from)
        pending = []
        to_read: list[RepositoryObject] = []
        process_paths: list[str] = []
        for path in sorted(level_sources):
            if path in visited:
                continue
            sources = tuple(dict.fromkeys(level_sources[path]))
            source = next((value for value in sources if value), path)
            entry = entries_by_path.get(path)
            if entry is None or entry.is_symlink or entry.is_submodule:
                diagnostics.append(f"{source}: Python requirements include is missing: {path}")
                visited.add(path)
                continue
            if path not in admitted:
                if included_files >= MAX_MANIFEST_INCLUDE_FILES:
                    if not file_limit_reported:
                        diagnostics.append(
                            f"{source}: Python requirements includes were truncated after "
                            f"{MAX_MANIFEST_INCLUDE_FILES} files"
                        )
                        file_limit_reported = True
                    continue
                admitted.add(path)
                included_files += 1
                to_read.append(entry)
            process_paths.append(path)
        if to_read:
            read = reader.read_candidate_blobs(tuple(sorted(to_read, key=lambda item: item.path)))
            blobs.update(read.blobs)
            diagnostics.extend(read.diagnostics)
        for path in process_paths:
            visited.add(path)
            if path not in blobs:
                continue
            try:
                parsed = parse_requirements(blobs[path].decode("utf-8"))
            except UnicodeDecodeError:
                diagnostics.append(f"{path}: Python requirements include is not UTF-8")
                continue
            for include_path in parsed.include_paths:
                resolved = _resolve_manifest_include(path, include_path, suffixes=(".txt", ".in"))
                if resolved is None:
                    diagnostics.append(
                        f"{path}: Python requirements include is outside the supported tree"
                    )
                    continue
                if included_edges >= MAX_MANIFEST_INCLUDE_EDGES:
                    if not edge_limit_reported:
                        diagnostics.append(
                            "Python requirements include graph was truncated after "
                            f"{MAX_MANIFEST_INCLUDE_EDGES} edges"
                        )
                        edge_limit_reported = True
                    continue
                included_edges += 1
                if depth == MAX_MANIFEST_INCLUDE_DEPTH:
                    diagnostics.append(
                        f"{path}: Python requirements include depth exceeded at {resolved}"
                    )
                else:
                    pending.append((resolved, path))
    requirement_paths = tuple(sorted(path for path in visited if path in blobs))
    return PythonRequirementBlobSet(
        blobs,
        requirement_paths,
        _bound_include_diagnostics(
            diagnostics,
            truncation_notice="Python requirements include diagnostics were truncated",
        ),
    )


def _plugin_records(
    facts: tuple[PluginFact, ...],
    *,
    ref: RefRole,
    commit_sha: str,
    trust: TrustClass,
) -> list[EvidenceRecord]:
    """Attach immutable ref provenance to validated static plugin facts."""

    return [
        EvidenceRecord(
            kind=fact.kind,
            value={"identity": fact.identity, "fact": fact.value},
            source_path=fact.source_path,
            ref=ref,
            commit_sha=commit_sha,
            component=fact.component,
            provenance=f"framework plugin:{fact.value['plugin']}",
            confidence=Confidence.EXACT,
            trust=trust,
        )
        for fact in facts
    ]


def _plugin_coverage(
    observations: tuple[PluginCoverage, ...], *, ref: RefRole, commit_sha: str
) -> list[CoverageRecord]:
    """Compose plugin coverage by semantic component/domain/scope identity."""

    grouped: dict[tuple[str, str, str], list[CoverageObservation]] = {}
    for item in observations:
        grouped.setdefault((item.component, item.domain, item.scope), []).append(item.observation)
    return [
        compose_coverage(
            component=component,
            domain=domain,
            scope=scope,
            observations=tuple(values),
            ref=ref,
            commit_sha=commit_sha,
        )
        for (component, domain, scope), values in sorted(grouped.items())
    ]


def collect_ref_facts(
    reader: GitRepositoryReader,
    commit_sha: str,
    ref: RefRole,
    *,
    changed_paths: Iterable[str] = (),
    coverage_sink: list[CoverageRecord] | None = None,
) -> tuple[list[EvidenceRecord], list[str]]:
    """Collect supported facts from one immutable tree with explicit diagnostics."""

    records = []
    diagnostics = []
    trust = TrustClass.TARGET_REPOSITORY if ref == RefRole.BASE else TrustClass.SOURCE_REPOSITORY
    changed = {path.casefold() for path in changed_paths}
    entries = reader.list_objects(commit_sha)
    entries_by_path = {entry.path: entry for entry in entries}
    role_paths = selected_role_paths(tuple(entry.path for entry in entries))
    topology_entries = tuple(
        entry
        for entry in entries
        if (
            topology_candidate(entry.path, executable=entry.mode == "100755")
            and (role_coverage_scope(entry.path) is None or entry.path in role_paths)
        )
    )

    def unavailable_topology(entry: RepositoryObject, reason: str) -> None:
        """Record one recognized topology source whose static coverage is unavailable."""

        role_scope = role_coverage_scope(entry.path)
        domain, scope = (
            role_scope
            if role_scope is not None
            else ("inventory.groups", inventory_scope(entry.path))
        )
        coverage_observations.setdefault((domain, scope), []).append(
            CoverageObservation(CoverageState.UNAVAILABLE, reason)
        )

    coverage_observations: dict[tuple[str, str], list[CoverageObservation]] = {}
    topology_kind_counts: dict[str, int] = {}
    topology_truncation_scopes: set[tuple[str, str]] = set()
    candidates = tuple(
        entry
        for entry in entries
        if (
            is_supported_manifest(entry.path)
            or PurePosixPath(entry.path).name.casefold().startswith(".gitlab-ci")
            or _is_context_yaml(entry.path, changed)
            or entry in topology_entries
            or infrastructure_candidate(entry.path)
            or entry.path in GUIDANCE_PATHS
            or entry.path.casefold() == ACCEPTED_DECISIONS_PATH
        )
        and not entry.is_symlink
        and not entry.is_submodule
        and entry.object_type == "blob"
    )
    source_statuses: dict[str, PluginSourceStatus] = {
        entry.path: PluginSourceStatus(
            entry.path,
            collector.ecosystem,
            collector.source_roles,
            "pending",
        )
        for entry in candidates
        if (collector := manifest_collector(entry.path)) is not None
    }
    try:
        read = reader.read_candidate_blobs(candidates)
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"collector batch read failed: {exc}")
        for entry in topology_entries:
            unavailable_topology(entry, "bounded-read-omission")
        if coverage_sink is not None:
            for (domain, scope), observations in sorted(coverage_observations.items()):
                coverage_sink.append(
                    compose_coverage(
                        component="ansible",
                        domain=domain,
                        scope=scope,
                        observations=tuple(observations),
                        ref=ref,
                        commit_sha=commit_sha,
                    )
                )
        return records, diagnostics
    blobs = read.blobs
    for path, status in tuple(source_statuses.items()):
        source_statuses[path] = PluginSourceStatus(
            status.path,
            status.ecosystem,
            status.roles,
            "accepted" if path in blobs else "omitted",
        )
    diagnostics.extend(f"{ref.value}:{message}" for message in read.diagnostics)
    galaxy_roots = tuple(
        entry.path
        for entry in candidates
        if (collector := manifest_collector(entry.path)) is not None
        and collector.ecosystem == "ansible"
        and entry.path in blobs
    )
    try:
        graph = _read_manifest_graph(reader, entries_by_path, galaxy_roots, blobs)
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"collector include batch read failed: {exc}")
        graph = ManifestBlobSet(blobs, galaxy_roots, ())
    python_roots = tuple(sorted(path for path in blobs if _is_python_requirements(path)))
    try:
        python_graph = _read_python_requirement_graph(
            reader, entries_by_path, python_roots, graph.blobs
        )
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"Python requirements include batch read failed: {exc}")
        python_graph = PythonRequirementBlobSet(graph.blobs, python_roots, ())
    blobs = python_graph.blobs
    diagnostics.extend(f"{ref.value}:{message}" for message in graph.diagnostics)
    diagnostics.extend(f"{ref.value}:{message}" for message in python_graph.diagnostics)
    paths = dict.fromkeys(
        (
            *tuple(entry.path for entry in candidates),
            *graph.galaxy_paths,
            *python_graph.requirement_paths,
        )
    )
    galaxy_paths = set(graph.galaxy_paths)
    python_requirement_paths = set(python_graph.requirement_paths)
    for entry in topology_entries:
        if entry.path in blobs:
            continue
        reason = (
            "symlink-source"
            if entry.is_symlink
            else "submodule-source"
            if entry.is_submodule
            else "bounded-read-omission"
        )
        unavailable_topology(entry, reason)
    for path in paths:
        if path not in blobs:
            # Bounded candidate omissions are already represented by explicit
            # coverage diagnostics; they must not abort the remaining facts.
            continue
        path_folded = path.casefold()
        image_source = PurePosixPath(path).name.casefold().startswith(
            ".gitlab-ci"
        ) or _is_context_yaml(path, changed)
        guidance_source = path in GUIDANCE_PATHS or path_folded == ACCEPTED_DECISIONS_PATH
        entry = entries_by_path.get(path)
        executable = entry is not None and entry.mode == "100755"
        topology_source = topology_candidate(path, executable=executable) and (
            role_coverage_scope(path) is None or path in role_paths
        )
        infrastructure_source = infrastructure_candidate(path)
        if (
            not is_supported_manifest(path)
            and path not in galaxy_paths
            and path not in python_requirement_paths
            and not image_source
            and not guidance_source
            and not topology_source
            and not infrastructure_source
        ):
            continue
        try:
            blob = blobs[path]
            text = blob.decode("utf-8")
            if (
                is_supported_manifest(path)
                or path in galaxy_paths
                or path in python_requirement_paths
            ):
                collector = (
                    manifest_collector(path)
                    if is_supported_manifest(path)
                    else manifest_collector(
                        "requirements.yml" if path in galaxy_paths else "requirements.txt"
                    )
                )
                if collector is None:  # pragma: no cover - guarded by registry predicate
                    raise ValueError("supported manifest has no collector")
                parsed = collector.parse(text)
                diagnostics.extend(f"{ref.value}:{path}: {notice}" for notice in parsed.notices)
                source_status = source_statuses.get(path)
                if any("truncated" in notice for notice in parsed.notices):
                    if source_status is not None:
                        source_statuses[path] = PluginSourceStatus(
                            source_status.path,
                            source_status.ecosystem,
                            source_status.roles,
                            "partial",
                        )
                elif source_status is not None:
                    source_statuses[path] = PluginSourceStatus(
                        source_status.path,
                        source_status.ecosystem,
                        source_status.roles,
                        "complete",
                    )
                facts = [
                    ManifestFact(
                        "repository.manifest",
                        collector.ecosystem,
                        path,
                        {"path": path, "ecosystem": collector.ecosystem},
                    ),
                    *parsed.facts,
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
                infrastructure = (
                    parse_infrastructure_pins(path, text)
                    if infrastructure_source
                    else ManifestParseResult(())
                )
                diagnostics.extend(
                    f"{ref.value}:{path}: {notice}" for notice in infrastructure.notices
                )
                facts = [
                    *(_image_facts(path, text) if image_source else []),
                    *infrastructure.facts,
                    *(
                        ManifestFact(fact.kind, "ansible", fact.identity, fact.value)
                        for fact in collect_topology(path, text, executable=executable)
                    ),
                ]
                observation = topology_coverage(path, text, executable=executable)
                if observation is not None:
                    domain, scope, value = observation
                    coverage_observations.setdefault((domain, scope), []).append(value)
        except (
            RepositoryEvidenceError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            RecursionError,
        ) as exc:
            diagnostics.append(
                f"{ref.value}:{path}: typed collection unavailable ({type(exc).__name__})"
            )
            if topology_source and entry is not None:
                unavailable_topology(entry, "parse-unavailable")
            source_status = source_statuses.get(path)
            if source_status is not None:
                source_statuses[path] = PluginSourceStatus(
                    source_status.path,
                    source_status.ecosystem,
                    source_status.roles,
                    "unavailable",
                )
            continue
        for fact in facts:
            if fact.kind.startswith("ansible.") and fact.kind != "dependency.declared":
                count = topology_kind_counts.get(fact.kind, 0)
                if count >= MAX_TOPOLOGY_FACTS_PER_KIND:
                    observation = topology_coverage(path, text, executable=executable)
                    if observation is not None:
                        domain, scope, _value = observation
                        key = (domain, scope)
                        if key not in topology_truncation_scopes:
                            coverage_observations.setdefault(key, []).append(
                                CoverageObservation(
                                    CoverageState.PARTIAL,
                                    "topology-fact-limit",
                                    positive=True,
                                )
                            )
                            topology_truncation_scopes.add(key)
                    continue
                topology_kind_counts[fact.kind] = count + 1
            identity = (
                f"{path}:{fact.identity}"
                if fact.kind.startswith(("dependency.", "runtime.", "ci.", "container."))
                and not fact.identity.startswith(f"{path}:")
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
    plugin_context = FrameworkPluginContext(
        records=tuple(records),
        entries=entries,
        source_statuses=tuple(sorted(source_statuses.values(), key=lambda item: item.path)),
        ref=ref,
        commit_sha=commit_sha,
    )
    plugin_facts, plugin_observations, plugin_notices = collect_framework_plugins(plugin_context)
    template_facts, template_observations, template_notices = collect_template_files(plugin_context)
    records.extend(
        _plugin_records(
            (*plugin_facts, *template_facts),
            ref=ref,
            commit_sha=commit_sha,
            trust=trust,
        )
    )
    diagnostics.extend(f"{ref.value}:{notice}" for notice in (*plugin_notices, *template_notices))
    if coverage_sink is not None:
        for (domain, scope), observations in sorted(coverage_observations.items()):
            coverage_sink.append(
                compose_coverage(
                    component="ansible",
                    domain=domain,
                    scope=scope,
                    observations=tuple(observations),
                    ref=ref,
                    commit_sha=commit_sha,
                )
            )
        coverage_sink.extend(
            _plugin_coverage(
                (*plugin_observations, *template_observations),
                ref=ref,
                commit_sha=commit_sha,
            )
        )
    return records, diagnostics


def fact_deltas(records: Iterable[EvidenceRecord]) -> tuple[EvidenceDelta, ...]:
    """Build reproducible typed deltas keyed by kind/component/identity."""

    base: dict[tuple[str, str, str], EvidenceRecord] = {}
    head: dict[tuple[str, str, str], EvidenceRecord] = {}
    for record in records:
        if not isinstance(record.value, Mapping) or not isinstance(
            record.value.get("identity"), str
        ):
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
            before.value.get("fact") if before and isinstance(before.value, Mapping) else None
        )
        after_value = (
            after.value.get("fact") if after and isinstance(after.value, Mapping) else None
        )
        change = "removed" if after is None else "added" if before is None else "changed"
        if before is not None and after is not None and before_value == after_value:
            continue
        deltas.append(EvidenceDelta(key[0], key[1], key[2], change, before_value, after_value))
    return tuple(deltas)
