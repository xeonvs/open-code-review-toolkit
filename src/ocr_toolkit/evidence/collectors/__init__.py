"""Bounded immutable source collection with explicit responsibility modules."""

from ocr_toolkit.evidence.collectors.graphs import (
    MAX_MANIFEST_INCLUDE_DIAGNOSTICS,
    MAX_MANIFEST_INCLUDE_EDGES,
    MAX_MANIFEST_INCLUDE_FILES,
)
from ocr_toolkit.evidence.collectors.orchestration import (
    MAX_TOPOLOGY_FACTS_PER_KIND,
    collect_ref_facts,
)
from ocr_toolkit.evidence.collectors.projections import fact_deltas
from ocr_toolkit.evidence.collectors.registry import manifest_collector, parse_manifest

__all__ = [
    "MAX_MANIFEST_INCLUDE_DIAGNOSTICS",
    "MAX_MANIFEST_INCLUDE_EDGES",
    "MAX_MANIFEST_INCLUDE_FILES",
    "MAX_TOPOLOGY_FACTS_PER_KIND",
    "collect_ref_facts",
    "fact_deltas",
    "manifest_collector",
    "parse_manifest",
]
