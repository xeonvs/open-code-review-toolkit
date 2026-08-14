"""Orchestrate bounded typed evidence collection for one immutable Git ref."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import PurePosixPath

from ocr_toolkit.evidence.collectors.graphs import (
    ManifestBlobSet,
    PythonRequirementBlobSet,
    read_manifest_graph,
    read_python_requirement_graph,
)
from ocr_toolkit.evidence.collectors.projections import plugin_coverage, plugin_records
from ocr_toolkit.evidence.collectors.registry import (
    is_python_requirements,
    is_supported_manifest,
    manifest_collector,
)
from ocr_toolkit.evidence.collectors.sources import image_facts, is_context_yaml
from ocr_toolkit.evidence.coverage import CoverageObservation, compose_coverage
from ocr_toolkit.evidence.ecosystems.ansible.topology import (
    collect_topology,
    inventory_scope,
    role_coverage_scope,
    selected_role_paths,
    topology_candidate,
    topology_coverage,
)
from ocr_toolkit.evidence.ecosystems.contracts import ManifestFact, ManifestParseResult
from ocr_toolkit.evidence.frameworks import (
    FrameworkPluginContext,
    PluginSourceStatus,
    collect_framework_plugins,
    collect_template_files,
)
from ocr_toolkit.evidence.infrastructure import infrastructure_candidate, parse_infrastructure_pins
from ocr_toolkit.evidence.model import (
    Confidence,
    CoverageRecord,
    CoverageState,
    EvidenceRecord,
    RefRole,
    TrustClass,
)
from ocr_toolkit.evidence.policy import (
    MAX_GUIDANCE_DIAGNOSTICS,
    MAX_GUIDANCE_DOCUMENTS,
    applicable_guidance_paths,
    guidance_document,
    guidance_precedence_key,
    is_guidance_path,
    parse_accepted_decisions,
)
from ocr_toolkit.evidence.repository import (
    BoundedBlobRead,
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryObject,
)

MAX_TOPOLOGY_FACTS_PER_KIND = 256
ACCEPTED_DECISIONS_PATH = ".opencodereview/accepted-decisions.md"


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
    changed_exact = tuple(sorted(set(changed_paths)))
    changed = {path.casefold() for path in changed_exact}
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
    applicable_paths = (
        set(
            applicable_guidance_paths(
                (
                    entry.path
                    for entry in entries
                    if entry.path not in changed_exact and is_guidance_path(entry.path)
                ),
                changed_exact,
            )
        )
        if ref is RefRole.BASE
        else set()
    )
    applicable_guidance = tuple(
        sorted(
            (entry for entry in entries if entry.path in applicable_paths),
            key=lambda entry: guidance_precedence_key(entry.path),
        )
    )
    rejected_guidance = tuple(
        entry
        for entry in applicable_guidance
        if entry.is_symlink or entry.is_submodule or entry.object_type != "blob"
    )
    for entry in rejected_guidance[:MAX_GUIDANCE_DIAGNOSTICS]:
        reason = (
            "symlink-source"
            if entry.is_symlink
            else "submodule-source"
            if entry.is_submodule
            else "non-blob-source"
        )
        diagnostics.append(f"{ref.value}:{entry.path}: guidance rejected ({reason})")
    if len(rejected_guidance) > MAX_GUIDANCE_DIAGNOSTICS:
        diagnostics.append(f"{ref.value}: guidance rejection diagnostics were truncated")

    regular_guidance = tuple(
        entry
        for entry in applicable_guidance
        if not entry.is_symlink and not entry.is_submodule and entry.object_type == "blob"
    )
    if len(regular_guidance) > MAX_GUIDANCE_DOCUMENTS:
        diagnostics.append(
            f"{ref.value}: applicable guidance truncated after {MAX_GUIDANCE_DOCUMENTS} documents"
        )
        regular_guidance = regular_guidance[:MAX_GUIDANCE_DOCUMENTS]
    target_decision_entry = next(
        (
            entry
            for entry in entries
            if ref is RefRole.BASE and entry.path == ACCEPTED_DECISIONS_PATH
        ),
        None,
    )
    # Keep the canonical decision document ahead of guidance inside the shared
    # policy byte budget; applicable guidance must not evict decision authority.
    policy_candidates = tuple(
        entry
        for entry in (
            *((target_decision_entry,) if target_decision_entry is not None else ()),
            *regular_guidance,
        )
        if not entry.is_symlink and not entry.is_submodule and entry.object_type == "blob"
    )
    policy_paths = {entry.path for entry in policy_candidates}
    if target_decision_entry is not None and target_decision_entry.path not in policy_paths:
        reason = (
            "symlink-source"
            if target_decision_entry.is_symlink
            else "submodule-source"
            if target_decision_entry.is_submodule
            else "non-blob-source"
        )
        diagnostics.append(
            f"{ref.value}:{ACCEPTED_DECISIONS_PATH}: accepted decisions rejected ({reason})"
        )

    candidates = tuple(
        entry
        for entry in entries
        if (
            is_supported_manifest(entry.path)
            or PurePosixPath(entry.path).name.casefold().startswith(".gitlab-ci")
            or is_context_yaml(entry.path, changed)
            or entry in topology_entries
            or infrastructure_candidate(entry.path)
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
    policy_blobs: dict[str, bytes] = {}
    if policy_candidates:
        try:
            policy_read = reader.read_candidate_blobs(policy_candidates)
        except RepositoryEvidenceError as exc:
            diagnostics.append(f"policy batch read failed: {exc}")
        else:
            policy_blobs = policy_read.blobs
            diagnostics.extend(f"{ref.value}:{message}" for message in policy_read.diagnostics)
    try:
        read = reader.read_candidate_blobs(candidates)
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"collector batch read failed: {exc}")
        # Policy has an independent authenticated batch and remains usable when an
        # unrelated source domain fails before ordinary candidate acquisition.
        read = BoundedBlobRead({}, ())
    blobs = {**policy_blobs, **read.blobs}
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
        graph = read_manifest_graph(reader, entries_by_path, galaxy_roots, blobs)
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"collector include batch read failed: {exc}")
        graph = ManifestBlobSet(blobs, galaxy_roots, ())
    python_roots = tuple(sorted(path for path in blobs if is_python_requirements(path)))
    try:
        python_graph = read_python_requirement_graph(
            reader, entries_by_path, python_roots, graph.blobs
        )
    except RepositoryEvidenceError as exc:
        diagnostics.append(f"Python requirements include batch read failed: {exc}")
        python_graph = PythonRequirementBlobSet(graph.blobs, python_roots, ())
    # Included requirements may use arbitrary .txt/.in names that the initial
    # manifest registry intentionally does not match. They still feed framework
    # declarations, so register their exact source state before graph/parser
    # degradation is projected into completeness.
    python_declaration = manifest_collector("requirements.txt")
    if python_declaration is None:  # pragma: no cover - static registry invariant
        raise ValueError("Python requirements collector is unavailable")
    for path in python_graph.requirement_paths:
        source_statuses.setdefault(
            path,
            PluginSourceStatus(
                path,
                python_declaration.ecosystem,
                python_declaration.source_roles,
                "accepted",
            ),
        )
    degraded_roots = dict((*graph.degraded_roots, *python_graph.degraded_roots))
    for path, reason in sorted(degraded_roots.items()):
        status = source_statuses.get(path)
        if status is not None and status.state not in {"omitted", "unavailable"}:
            source_statuses[path] = PluginSourceStatus(
                status.path,
                status.ecosystem,
                status.roles,
                "partial",
                reason,
            )
    blobs = python_graph.blobs
    for message in (*graph.diagnostics, *python_graph.diagnostics):
        qualified = f"{ref.value}:{message}"
        if qualified not in diagnostics:
            diagnostics.append(qualified)
    paths = dict.fromkeys(
        (
            *tuple(entry.path for entry in policy_candidates),
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
        image_source = PurePosixPath(path).name.casefold().startswith(
            ".gitlab-ci"
        ) or is_context_yaml(path, changed)
        guidance_source = is_guidance_path(path) or path == ACCEPTED_DECISIONS_PATH
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
                    if source_status is not None and source_status.state != "partial":
                        source_statuses[path] = PluginSourceStatus(
                            source_status.path,
                            source_status.ecosystem,
                            source_status.roles,
                            "partial",
                            "source-item-limit",
                        )
                elif source_status is not None and source_status.state != "partial":
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
            elif path == ACCEPTED_DECISIONS_PATH:
                facts = []
                if ref == RefRole.BASE:
                    parsed_decisions = parse_accepted_decisions(text, changed_paths=changed_exact)
                    diagnostics.extend(
                        f"{ref.value}:{path}: {notice}" for notice in parsed_decisions.diagnostics
                    )
                    facts = [
                        ManifestFact(
                            "repository.accepted_decision",
                            "repository",
                            decision.decision_id,
                            decision.evidence_value()["fact"],
                        )
                        for decision in parsed_decisions.decisions
                    ]
            elif guidance_source:
                facts = []
                if ref == RefRole.BASE and path in policy_paths:
                    document = guidance_document(path, text, changed_exact)
                    facts = [
                        ManifestFact(
                            "repository.guidance",
                            "repository",
                            path,
                            document.evidence_value()["fact"],
                        )
                    ]
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
                    *(image_facts(path, text) if image_source else []),
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
            policy_provenance = {
                "repository.accepted_decision": "policy:accepted-decisions",
                "repository.guidance": "policy:project-guidance",
            }.get(fact.kind)
            records.append(
                EvidenceRecord(
                    kind=fact.kind,
                    value={"identity": identity, "fact": fact.value},
                    source_path=path,
                    ref=ref,
                    commit_sha=commit_sha,
                    component=fact.component,
                    provenance=policy_provenance or f"typed parser:{PurePosixPath(path).name}",
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
        plugin_records(
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
            plugin_coverage(
                (*plugin_observations, *template_observations),
                ref=ref,
                commit_sha=commit_sha,
            )
        )
    return records, diagnostics
