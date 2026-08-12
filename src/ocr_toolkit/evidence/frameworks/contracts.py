"""Static framework plugin contracts shared by collectors and providers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from ocr_toolkit.evidence.coverage import CoverageObservation
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceValue, RefRole

if TYPE_CHECKING:
    from ocr_toolkit.evidence.repository import RepositoryObject

# Each evidence kind shares a 512-record store limit across base and head. Capping
# each immutable side at half keeps accepted records, deltas, and coverage atomic.
MAX_PLUGIN_FACTS = 256
MAX_CONFIGURATION_PATHS = 128


@dataclass(frozen=True, slots=True)
class PluginFact:
    """Describe one validated plugin fact before ref provenance is attached."""

    kind: str
    component: str
    identity: str
    source_path: str
    value: Mapping[str, EvidenceValue]


@dataclass(frozen=True, slots=True)
class PluginCoverage:
    """Describe one plugin-owned scoped coverage observation."""

    component: str
    domain: str
    scope: str
    observation: CoverageObservation


@dataclass(frozen=True, slots=True)
class PluginSourceStatus:
    """Describe one supported manifest source and its bounded collection state."""

    path: str
    ecosystem: str
    roles: tuple[str, ...]
    state: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class FrameworkPluginContext:
    """Expose immutable normalized facts and bounded tree metadata to one plugin."""

    records: tuple[EvidenceRecord, ...]
    entries: tuple[RepositoryObject, ...]
    source_statuses: tuple[PluginSourceStatus, ...]
    ref: RefRole
    commit_sha: str


@dataclass(frozen=True, slots=True)
class FrameworkPluginResult:
    """Return bounded plugin facts, coverage, and safe machine notices."""

    facts: tuple[PluginFact, ...]
    coverage: tuple[PluginCoverage, ...]
    notices: tuple[str, ...] = ()


class FrameworkPlugin(Protocol):
    """Define the package-owned static framework plugin boundary."""

    plugin_id: str

    def collect(self, context: FrameworkPluginContext) -> FrameworkPluginResult:
        """Derive facts without I/O, execution, network access, or mutation."""
