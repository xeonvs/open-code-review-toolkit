"""Closed immutable data contracts for bounded review context."""

from __future__ import annotations

from dataclasses import dataclass

POLICY_SCHEMA_V1 = "ocr.review-context-policy/v1"
POLICY_SCHEMA_V2 = "ocr.review-context-policy/v2"
POLICY_SCHEMA_V3 = "ocr.review-context-policy/v3"
POLICY_SCHEMAS = frozenset({POLICY_SCHEMA_V1, POLICY_SCHEMA_V2, POLICY_SCHEMA_V3})
POLICY_SCHEMA = POLICY_SCHEMA_V3
STORE_SCHEMA = "ocr.context-store/v2"
REQUEST_SCHEMA = "ocr.context-adapter-request/v1"
RESPONSE_SCHEMA = "ocr.context-adapter-response/v1"
ACCOUNT_CLASSES = frozenset({"user", "automation", "system", "toolkit_bot"})
REFERENCE_RESOURCE_CLASSES = frozenset({"issue", "document"})
STORE_RESOURCE_CLASSES = frozenset(
    {*REFERENCE_RESOURCE_CLASSES, "remediation_thread", "ci_outcome"}
)
PROJECTION_FIELDS = frozenset(
    {
        "descriptor",
        "text",
        "state",
        "author_class",
        "author_pseudonym",
        "anchor",
        "resolved",
        "outdated",
        "created_at",
        "updated_at",
        "count",
        "digest",
        "version",
        "expiry",
    }
)
REMEDIATION_MODEL_FIELD = "remediation_thread"
CI_OUTCOME_MODEL_FIELD = "ci_outcome"
STORE_PROJECTION_FIELDS = frozenset(
    {*PROJECTION_FIELDS, REMEDIATION_MODEL_FIELD, CI_OUTCOME_MODEL_FIELD}
)
RETENTION_FIELDS = frozenset({"state", "count", "digest", "version", "expiry"})


class ContextContractError(ValueError):
    """One closed context contract was malformed or impossible."""


@dataclass(frozen=True, slots=True)
class TextBudgets:
    """Apply independent text units to one source or record."""

    max_chars: int
    max_bytes: int
    max_lines: int


@dataclass(frozen=True, slots=True)
class AggregateBudgets(TextBudgets):
    """Apply aggregate count and time bounds independently of text units."""

    max_records: int
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class ContextProjections:
    """Separate acquisition, model, publication, and retention fields."""

    retrieve: tuple[str, ...]
    model: tuple[str, ...]
    publish: tuple[str, ...]
    retain: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DiscussionPolicy:
    """Select one bounded GitLab discussion snapshot."""

    required: bool
    account_classes: tuple[str, ...]
    include_resolved: bool
    include_outdated: bool
    max_age_seconds: int
    max_threads: int
    max_replies_per_thread: int
    max_items: int
    budgets: TextBudgets
    projections: ContextProjections


@dataclass(frozen=True, slots=True)
class RemediationThreadPolicy:
    """Select verified toolkit-owned GitLab remediation threads."""

    required: bool
    account_classes: tuple[str, ...]
    include_resolved: bool
    include_outdated: bool
    max_age_seconds: int
    max_threads: int
    max_replies_per_thread: int
    max_items: int
    budgets: TextBudgets


@dataclass(frozen=True, slots=True)
class CIOutcomeCheckPolicy:
    """Authorize one exact forge check and its protected path scope."""

    name: str
    path_prefixes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CIOutcomePolicy:
    """Select bounded same-revision forge outcomes under protected policy."""

    required: bool
    max_age_seconds: int
    checks: tuple[CIOutcomeCheckPolicy, ...]


@dataclass(frozen=True, slots=True)
class RecognizerPolicy:
    """Hold one fixed toolkit-authored candidate grammar."""

    type: str
    prefix: str | None = None
    origin: str | None = None
    path_prefix: str | None = None


@dataclass(frozen=True, slots=True)
class ReferencePolicy:
    """Bind one operator adapter selection to a protected grammar and limits."""

    adapter: str
    tenant: str
    resource_class: str
    recognizer: RecognizerPolicy
    required: bool
    max_records: int
    max_age_seconds: int
    budgets: TextBudgets
    projections: ContextProjections


@dataclass(frozen=True, slots=True)
class ContextPolicy:
    """Represent the complete validated protected-target policy."""

    schema_version: str
    budgets: AggregateBudgets
    forge_discussions: DiscussionPolicy | None
    remediation_threads: RemediationThreadPolicy | None
    ci_outcomes: CIOutcomePolicy | None
    references: tuple[ReferencePolicy, ...]
    digest: str
