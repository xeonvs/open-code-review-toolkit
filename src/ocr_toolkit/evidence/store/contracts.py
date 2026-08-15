"""Closed evidence-store versions, kinds, limits, and public errors."""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = 4
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3, SCHEMA_VERSION}
POLICY_KINDS = frozenset({"repository.accepted_decision", "repository.guidance"})
MAX_SERIALIZED_BYTES = 20_000_000
KNOWN_KINDS = frozenset(
    {
        "repository.file",
        "repository.guidance",
        "repository.accepted_decision",
        "repository.manifest",
        "repository.change_category",
        "ansible.playbook",
        "ansible.role_metadata",
        "ansible.role_defaults",
        "ansible.role_vars",
        "ansible.inventory",
        "ansible.inventory_group",
        "review.ci_context",
        "dependency.declared",
        "dependency.locked",
        "runtime.declared",
        "runtime.detected",
        "container.image",
        "ci.image",
        "application.version",
        "diagnostic.coverage",
        "framework.detected",
        "template.file",
    }
)


class EvidenceStoreError(ValueError):
    """Report an invalid, unsafe, or over-limit evidence store operation."""


@dataclass(frozen=True, slots=True)
class EvidenceStoreLimits:
    """Declare deterministic record, per-kind, and serialized byte budgets."""

    max_records: int = 4096
    max_records_per_kind: int = 512
    max_bytes: int = 2_000_000
    max_value_chars: int = 64_000

    def __post_init__(self) -> None:
        """Reject unusable or unbounded limit configurations."""

        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (
                self.max_records,
                self.max_records_per_kind,
                self.max_bytes,
                self.max_value_chars,
            )
        ):
            raise EvidenceStoreError("evidence store limits must be integers")
        if not 1 <= self.max_records <= 100_000:
            raise EvidenceStoreError("max_records must be between 1 and 100000")
        if not 1 <= self.max_records_per_kind <= self.max_records:
            raise EvidenceStoreError(
                "max_records_per_kind must be positive and no greater than max_records"
            )
        if not 1024 <= self.max_bytes <= MAX_SERIALIZED_BYTES:
            raise EvidenceStoreError(f"max_bytes must be between 1024 and {MAX_SERIALIZED_BYTES}")
        if not 1 <= self.max_value_chars <= 1_000_000:
            raise EvidenceStoreError("max_value_chars must be between 1 and 1000000")
