"""Read bounded local manifest include graphs from immutable repository objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

from ocr_toolkit.evidence.ecosystems.ansible.requirements import parse_galaxy_requirements
from ocr_toolkit.evidence.ecosystems.python import parse_requirements
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryObject

MAX_MANIFEST_INCLUDE_FILES = 32
MAX_MANIFEST_INCLUDE_DEPTH = 8
MAX_MANIFEST_INCLUDE_DIAGNOSTICS = 64
MAX_MANIFEST_INCLUDE_EDGES = 4_096


@dataclass(frozen=True, slots=True)
class ManifestBlobSet:
    """Return immutable Galaxy blobs, diagnostics, and affected graph roots."""

    blobs: dict[str, bytes]
    galaxy_paths: tuple[str, ...]
    diagnostics: tuple[str, ...]
    degraded_roots: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class PythonRequirementBlobSet:
    """Return immutable requirements blobs, diagnostics, and affected roots."""

    blobs: dict[str, bytes]
    requirement_paths: tuple[str, ...]
    diagnostics: tuple[str, ...]
    degraded_roots: tuple[tuple[str, str], ...] = ()


def resolve_manifest_include(
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


def include_cycle_diagnostics(edges: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
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


def bound_include_diagnostics(
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


def roots_reaching_graph_degradation(
    roots: tuple[str, ...],
    edges: Mapping[str, tuple[str, ...]],
    degraded_paths: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    """Return roots whose accepted graph reaches a bounded degraded source."""

    supported_reasons = {"bounded-source-omission", "include-graph-truncation"}
    if any(reason not in supported_reasons for reason in degraded_paths.values()):
        raise ValueError("include graph has an unsupported degradation reason")
    affected: list[tuple[str, str]] = []
    for root in sorted(set(roots)):
        pending = [root]
        visited: set[str] = set()
        reasons: set[str] = set()
        while pending:
            path = pending.pop()
            if path in visited:
                continue
            visited.add(path)
            reason = degraded_paths.get(path)
            if reason is not None:
                reasons.add(reason)
            pending.extend(reversed(edges.get(path, ())))
        if reasons:
            # A bounded omission is stronger than a traversal/item limit because
            # the source itself was never parsed.
            reason = (
                "bounded-source-omission"
                if "bounded-source-omission" in reasons
                else "include-graph-truncation"
            )
            affected.append((root, reason))
    return tuple(affected)


def read_manifest_graph(
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
    degraded_paths: dict[str, str] = {}
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
                entry = entries_by_path.get(path)
                if entry is None or entry.is_symlink or entry.is_submodule:
                    for source in included_from_values:
                        diagnostics.append(
                            f"{source or path}: Ansible Galaxy include is missing: {path}"
                        )
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
                    degraded_paths[path] = "include-graph-truncation"
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
            for path in (entry.path for entry in to_read if entry.path not in read.blobs):
                degraded_paths[path] = "bounded-source-omission"
        for path in process_paths:
            visited.add(path)
            blob = blobs.get(path)
            if blob is None:
                continue
            try:
                parsed = parse_galaxy_requirements(blob.decode("utf-8"))
                if any("truncated" in notice for notice in parsed.notices):
                    degraded_paths[path] = "include-graph-truncation"
            except UnicodeDecodeError:
                diagnostics.append(f"{path}: Ansible Galaxy include is not UTF-8")
                continue
            for include_path in parsed.include_paths:
                resolved = resolve_manifest_include(path, include_path, suffixes=(".yml", ".yaml"))
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
                    degraded_paths[path] = "include-graph-truncation"
                    continue
                included_edges += 1
                edges.setdefault(path, []).append(resolved)
                if depth >= MAX_MANIFEST_INCLUDE_DEPTH:
                    diagnostics.append(
                        f"{path}: Ansible Galaxy include depth exceeded at {resolved}"
                    )
                    degraded_paths[path] = "include-graph-truncation"
                else:
                    pending.append((resolved, path))
    normalized_edges = {path: tuple(dict.fromkeys(targets)) for path, targets in edges.items()}
    diagnostics.extend(include_cycle_diagnostics(normalized_edges))
    galaxy_paths = tuple(sorted(path for path in visited if path in blobs))
    return ManifestBlobSet(
        blobs,
        galaxy_paths,
        bound_include_diagnostics(diagnostics),
        roots_reaching_graph_degradation(initial_paths, normalized_edges, degraded_paths),
    )


def read_python_requirement_graph(
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
    edges: dict[str, list[str]] = {}
    degraded_paths: dict[str, str] = {}
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
                entry = entries_by_path.get(path)
                if entry is None or entry.is_symlink or entry.is_submodule:
                    for include_source in tuple(dict.fromkeys(level_sources[path])):
                        diagnostics.append(
                            f"{include_source or path}: Python requirements include is missing: "
                            f"{path}"
                        )
                continue
            sources = tuple(dict.fromkeys(level_sources[path]))
            source = next((value for value in sources if value), path)
            entry = entries_by_path.get(path)
            if entry is None or entry.is_symlink or entry.is_submodule:
                for include_source in sources:
                    diagnostics.append(
                        f"{include_source or path}: Python requirements include is missing: {path}"
                    )
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
                    degraded_paths[path] = "include-graph-truncation"
                    continue
                admitted.add(path)
                included_files += 1
                to_read.append(entry)
            process_paths.append(path)
        if to_read:
            read = reader.read_candidate_blobs(tuple(sorted(to_read, key=lambda item: item.path)))
            blobs.update(read.blobs)
            diagnostics.extend(read.diagnostics)
            for path in (entry.path for entry in to_read if entry.path not in read.blobs):
                degraded_paths[path] = "bounded-source-omission"
        for path in process_paths:
            visited.add(path)
            if path not in blobs:
                continue
            try:
                parsed = parse_requirements(blobs[path].decode("utf-8"))
                if any("truncated" in notice for notice in parsed.notices):
                    degraded_paths[path] = "include-graph-truncation"
            except UnicodeDecodeError:
                diagnostics.append(f"{path}: Python requirements include is not UTF-8")
                continue
            for include_path in parsed.include_paths:
                resolved = resolve_manifest_include(path, include_path, suffixes=(".txt", ".in"))
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
                    degraded_paths[path] = "include-graph-truncation"
                    continue
                included_edges += 1
                edges.setdefault(path, []).append(resolved)
                if depth == MAX_MANIFEST_INCLUDE_DEPTH:
                    diagnostics.append(
                        f"{path}: Python requirements include depth exceeded at {resolved}"
                    )
                    degraded_paths[path] = "include-graph-truncation"
                else:
                    pending.append((resolved, path))
    requirement_paths = tuple(sorted(path for path in visited if path in blobs))
    normalized_edges = {path: tuple(dict.fromkeys(targets)) for path, targets in edges.items()}
    return PythonRequirementBlobSet(
        blobs,
        requirement_paths,
        bound_include_diagnostics(
            diagnostics,
            truncation_notice="Python requirements include diagnostics were truncated",
        ),
        roots_reaching_graph_degradation(initial_paths, normalized_edges, degraded_paths),
    )
