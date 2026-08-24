"""Compose protected policy, operator adapters, DLP, and atomic store admission."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ocr_toolkit.context.adapters import (
    AdapterConfig,
    AdapterRequest,
    AdapterResponse,
    ContextAdapterError,
    authorize_and_resolve,
)
from ocr_toolkit.context.contracts import (
    ACCOUNT_CLASSES,
    ContextPolicy,
    ContextProjections,
    DiscussionPolicy,
    ReferencePolicy,
    RemediationThreadPolicy,
    TextBudgets,
)
from ocr_toolkit.context.dlp import check_text, normalize_text
from ocr_toolkit.context.recognizers import ReferenceCandidate
from ocr_toolkit.context.store import PendingContextRecord

MAX_ADAPTER_REQUESTS = 512


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    """Bind a syntax candidate to the exact protected reference policy."""

    policy: ReferencePolicy
    candidate: ReferenceCandidate


@dataclass(frozen=True, slots=True)
class BrokerResult:
    """Return admitted records and closed completeness without transport detail."""

    records: tuple[PendingContextRecord, ...]
    completeness: Mapping[str, str]
    degradation_counts: Mapping[str, int]
    required_degraded: bool


@dataclass(frozen=True, slots=True)
class ContextOrigin:
    """Name one provider composition edge without coupling the broker to its API."""

    source: str
    adapter: str
    tenant: str


class DiscussionView(Protocol):
    """Expose only normalized discussion fields needed for store projection."""

    thread: int
    reply: int
    author_class: str
    author_pseudonym: str
    body: str
    created_at: int
    updated_at: int
    resolved: bool
    outdated: bool
    anchor: Mapping[str, object]
    version: str
    digest: str


class RemediationReplyView(Protocol):
    """Expose one provider-normalized reply in a verified remediation thread."""

    order: int
    author_class: str
    author_pseudonym: str
    body: str
    created_at: int
    updated_at: int


class RemediationThreadView(Protocol):
    """Expose only the common verified remediation bundle contract."""

    root_author_pseudonym: str
    root_body: str
    anchor_state: str
    replies: Sequence[RemediationReplyView]
    completeness: str
    resolved_count: int
    outdated_count: int
    version: str
    digest: str


STATE_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
PSEUDONYM_RE = re.compile(r"actor-[0-9a-f]{16}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _project(
    record: Mapping[str, object],
    fields: Sequence[str],
) -> dict[str, object]:
    return {field: record[field] for field in fields if field in record}


def _publish_projection(
    record: Mapping[str, object],
    fields: Sequence[str],
    *,
    budgets: TextBudgets,
    forbidden: tuple[str, ...],
) -> dict[str, object] | None:
    """Project publishable fields only after publication-specific text DLP."""

    projected = _project(record, fields)
    text = projected.get("text")
    if isinstance(text, str):
        checked = check_text(
            text,
            budgets=budgets,
            publication=True,
            forbidden=forbidden,
        )
        if not checked.admitted or checked.text != text:
            return None
    return projected


def _normalized_record(
    record: Mapping[str, object],
    *,
    budgets: TextBudgets,
    projections: ContextProjections,
    resource_class: str,
    forbidden: tuple[str, ...],
) -> Mapping[str, object] | None:
    result: dict[str, object] = {}
    for field in projections.retrieve:
        if field not in record:
            continue
        value = record[field]
        if field == "text":
            checked = check_text(value, budgets=budgets, forbidden=forbidden)
            if not checked.admitted or checked.text is None:
                return None
            result[field] = checked.text
        elif field in {"descriptor", "state", "author_class", "author_pseudonym", "version"}:
            normalized = normalize_text(value)
            if normalized is None or not normalized or len(normalized) > 512:
                return None
            checked = check_text(
                normalized,
                budgets=TextBudgets(max_chars=512, max_bytes=2_048, max_lines=1),
                forbidden=forbidden,
            )
            if not checked.admitted:
                return None
            if field == "descriptor" and normalized != resource_class:
                return None
            if field == "state" and STATE_RE.fullmatch(normalized) is None:
                return None
            if field == "author_class" and normalized not in ACCOUNT_CLASSES:
                return None
            if field == "author_pseudonym" and PSEUDONYM_RE.fullmatch(normalized) is None:
                return None
            result[field] = normalized
        elif field in {"resolved", "outdated"}:
            if not isinstance(value, bool):
                return None
            result[field] = value
        elif field in {"created_at", "updated_at", "count", "expiry"}:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return None
            result[field] = value
        elif field == "digest":
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                return None
            result[field] = value
        elif field == "anchor":
            if not isinstance(value, Mapping) or set(value).difference({"path", "line"}):
                return None
            anchor: dict[str, object] = {}
            if "path" in value:
                path = normalize_text(value["path"])
                if path is None or not path or len(path) > 512 or len(path.encode()) > 2_048:
                    return None
                checked = check_text(
                    path,
                    budgets=TextBudgets(max_chars=512, max_bytes=2_048, max_lines=1),
                    forbidden=forbidden,
                )
                if not checked.admitted:
                    return None
                anchor["path"] = path
            if "line" in value:
                line = value["line"]
                if (
                    not isinstance(line, int)
                    or isinstance(line, bool)
                    or not 0 < line <= 10_000_000
                ):
                    return None
                anchor["line"] = line
            result[field] = anchor
    return result


def prepare_discussion_records(
    records: Sequence[DiscussionView],
    *,
    policy: DiscussionPolicy,
    origin: ContextOrigin,
    expiry: int,
    forbidden: tuple[str, ...] = (),
) -> tuple[PendingContextRecord, ...]:
    """Project provider-normalized discussions into the common private store contract."""

    pending: list[PendingContextRecord] = []
    for record in records:
        value: dict[str, object] = {
            "descriptor": "discussion",
            "text": record.body,
            "state": "resolved" if record.resolved else "open",
            "author_class": record.author_class,
            "author_pseudonym": record.author_pseudonym,
            "anchor": dict(record.anchor),
            "resolved": record.resolved,
            "outdated": record.outdated,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "digest": record.digest,
            "version": record.version,
            "expiry": expiry,
        }
        retrieved = _normalized_record(
            value,
            budgets=policy.budgets,
            projections=policy.projections,
            resource_class="discussion",
            forbidden=forbidden,
        )
        if (
            retrieved is None
            or not isinstance(record.digest, str)
            or SHA256_RE.fullmatch(record.digest) is None
            or normalize_text(record.version) != record.version
            or not record.version
            or len(record.version) > 512
        ):
            continue
        publish = _publish_projection(
            retrieved,
            policy.projections.publish,
            budgets=policy.budgets,
            forbidden=forbidden,
        )
        if publish is None:
            continue
        pending.append(
            PendingContextRecord(
                source=origin.source,
                adapter=origin.adapter,
                tenant=origin.tenant,
                canonical_object=hashlib.sha256(f"discussion:{record.digest}".encode()).hexdigest(),
                resource_class="issue",
                descriptor="discussion",
                projections={
                    "model": _project(retrieved, policy.projections.model),
                    "publish": publish,
                    "retain": _project(retrieved, policy.projections.retain),
                },
                version=record.version,
                digest=record.digest,
                mutable=True,
                expiry=expiry,
            )
        )
    return tuple(pending)


def prepare_remediation_records(
    records: Sequence[RemediationThreadView],
    *,
    policy: RemediationThreadPolicy,
    origin: ContextOrigin,
    expiry: int,
    forbidden: tuple[str, ...] = (),
) -> tuple[PendingContextRecord, ...]:
    """DLP-check normalized remediation views and build the fixed private projection."""

    pending: list[PendingContextRecord] = []
    for record in records:
        root = check_text(record.root_body, budgets=policy.budgets, forbidden=forbidden)
        if (
            not root.admitted
            or root.text != record.root_body
            or not isinstance(record.root_author_pseudonym, str)
            or PSEUDONYM_RE.fullmatch(record.root_author_pseudonym) is None
            or record.anchor_state not in {"current", "outdated", "unpositioned"}
            or record.completeness not in {"complete", "partial"}
            or not isinstance(record.digest, str)
            or SHA256_RE.fullmatch(record.digest) is None
            or normalize_text(record.version) != record.version
            or not record.version
            or len(record.version) > 512
            or not isinstance(record.resolved_count, int)
            or isinstance(record.resolved_count, bool)
            or not isinstance(record.outdated_count, int)
            or isinstance(record.outdated_count, bool)
            or record.resolved_count < 0
            or record.outdated_count < 0
        ):
            continue
        replies: list[dict[str, object]] = []
        valid = True
        for expected_order, reply in enumerate(record.replies):
            checked = check_text(reply.body, budgets=policy.budgets, forbidden=forbidden)
            if (
                reply.order != expected_order
                or reply.author_class not in policy.account_classes
                or reply.author_class == "toolkit_bot"
                or not isinstance(reply.author_pseudonym, str)
                or PSEUDONYM_RE.fullmatch(reply.author_pseudonym) is None
                or not checked.admitted
                or checked.text != reply.body
                or not isinstance(reply.created_at, int)
                or isinstance(reply.created_at, bool)
                or not isinstance(reply.updated_at, int)
                or isinstance(reply.updated_at, bool)
                or reply.created_at < 0
                or reply.updated_at < reply.created_at
                or reply.updated_at > expiry
            ):
                valid = False
                break
            replies.append(
                {
                    "order": reply.order,
                    "author_class": reply.author_class,
                    "author_pseudonym": reply.author_pseudonym,
                    "text": checked.text,
                    "created_at": reply.created_at,
                    "updated_at": reply.updated_at,
                }
            )
        if (
            not valid
            or not replies
            or len(replies) > policy.max_replies_per_thread
            or record.resolved_count > len(replies) + 1
            or record.outdated_count > len(replies) + 1
            or (record.anchor_state == "outdated" and record.outdated_count < 1)
        ):
            continue
        remediation = {
            "root": {
                "text": root.text,
                "author_pseudonym": record.root_author_pseudonym,
            },
            "anchor_state": record.anchor_state,
            "replies": replies,
            "completeness": record.completeness,
            "counts": {
                "replies": len(replies),
                "resolved": record.resolved_count,
                "outdated": record.outdated_count,
            },
        }
        pending.append(
            PendingContextRecord(
                source=origin.source,
                adapter=origin.adapter,
                tenant=origin.tenant,
                canonical_object=hashlib.sha256(
                    f"remediation:{record.digest}".encode()
                ).hexdigest(),
                resource_class="remediation_thread",
                descriptor="remediation_thread",
                projections={
                    "model": {
                        "descriptor": "remediation_thread",
                        "remediation_thread": remediation,
                    },
                    "publish": {"descriptor": "remediation_thread"},
                    "retain": {
                        "state": record.completeness,
                        "count": len(replies),
                        "digest": record.digest,
                        "version": record.version,
                        "expiry": expiry,
                    },
                },
                version=record.version,
                digest=record.digest,
                mutable=True,
                expiry=expiry,
            )
        )
    return tuple(pending)


def acquire_external_records(
    *,
    policy: ContextPolicy,
    adapters: Sequence[AdapterConfig],
    selections: Sequence[CandidateSelection],
    run_id: str,
    now: int,
    environment: Mapping[str, str],
    forbidden: tuple[str, ...] = (),
    deadline: float | None = None,
    invoke: Callable[..., AdapterResponse] = authorize_and_resolve,
) -> BrokerResult:
    """Authorize, normalize, DLP-check, and prepare all external records."""

    configs = {config.name: config for config in adapters}
    records: list[PendingContextRecord] = []
    completeness: dict[str, str] = {}
    degradation_counts = {"unavailable": 0, "invalid": 0, "limit": 0}
    required_degraded = False
    total_chars = total_bytes = total_lines = 0
    seen: dict[tuple[str, str, str, str], tuple[str, str, PendingContextRecord, int, int, int]] = {}
    invalidated: set[tuple[str, str, str, str]] = set()
    started_requests = 0
    acquisition_deadline = (
        time.monotonic() + policy.budgets.timeout_ms / 1000 if deadline is None else deadline
    )
    for reference in policy.references:
        source = f"reference:{reference.adapter}:{reference.tenant}:{reference.resource_class}"
        config = configs.get(reference.adapter)
        if (
            config is None
            or reference.tenant not in config.tenants
            or reference.resource_class not in config.resource_classes
        ):
            completeness[source] = "unavailable"
            degradation_counts["unavailable"] += 1
            required_degraded = required_degraded or reference.required
        else:
            completeness[source] = "complete"
    for selection in selections:
        reference = selection.policy
        if reference not in policy.references:
            degradation_counts["invalid"] += 1
            required_degraded = True
            continue
        source = f"reference:{reference.adapter}:{reference.tenant}:{reference.resource_class}"
        config = configs.get(reference.adapter)
        if (
            config is None
            or reference.tenant not in config.tenants
            or reference.resource_class not in config.resource_classes
            or selection.candidate.resource_class != reference.resource_class
            or selection.candidate.recognizer != reference.recognizer.type
        ):
            completeness[source] = "unavailable"
            degradation_counts["unavailable"] += 1
            required_degraded = required_degraded or reference.required
            continue
        if (
            started_requests >= MAX_ADAPTER_REQUESTS
            or len(records) >= policy.budgets.max_records
            or sum(1 for record in records if record.source == source) >= reference.max_records
        ):
            completeness[source] = "partial"
            degradation_counts["limit"] += 1
            required_degraded = required_degraded or reference.required
            continue
        remaining_ms = int((acquisition_deadline - time.monotonic()) * 1000)
        if remaining_ms < 100:
            completeness[source] = "partial"
            degradation_counts["limit"] += 1
            required_degraded = required_degraded or reference.required
            continue
        started_requests += 1
        request = AdapterRequest(
            request_id=secrets.token_urlsafe(24),
            run_id=run_id,
            adapter=reference.adapter,
            tenant=reference.tenant,
            resource_class=reference.resource_class,
            candidate=selection.candidate.value,
            requested_fields=reference.projections.retrieve,
            max_chars=reference.budgets.max_chars,
            max_bytes=reference.budgets.max_bytes,
            max_lines=reference.budgets.max_lines,
            max_age_seconds=reference.max_age_seconds,
            deadline_ms=min(policy.budgets.timeout_ms, remaining_ms),
        )
        try:
            response = invoke(config, request, environment=environment)
        except (ContextAdapterError, OSError, TimeoutError):
            completeness[source] = "unavailable"
            degradation_counts["unavailable"] += 1
            required_degraded = required_degraded or reference.required
            continue
        if not hasattr(response, "status") or response.status != "admitted":
            completeness[source] = "unavailable"
            degradation_counts["unavailable"] += 1
            required_degraded = required_degraded or reference.required
            continue
        if (
            response.record is None
            or response.canonical_object is None
            or response.version is None
            or response.expiry is None
            or response.expiry <= now
            or response.expiry > now + 86_400
        ):
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        normalized = _normalized_record(
            response.record,
            budgets=reference.budgets,
            projections=reference.projections,
            resource_class=reference.resource_class,
            forbidden=forbidden,
        )
        if normalized is None:
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        updated_at = normalized.get("updated_at")
        if isinstance(updated_at, int) and (
            updated_at > now + 300
            or (reference.max_age_seconds and now - updated_at > reference.max_age_seconds)
        ):
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        text = normalized.get("text", "")
        chars = len(text) if isinstance(text, str) else 0
        byte_count = len(text.encode()) if isinstance(text, str) else 0
        lines = text.count("\n") + 1 if isinstance(text, str) and text else 0
        digest = hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        identity = (
            reference.adapter,
            reference.tenant,
            reference.resource_class,
            response.canonical_object,
        )
        if identity in invalidated:
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        prior = seen.get(identity)
        if prior is not None:
            if prior[:2] == (response.version, digest):
                continue
            _version, _digest, prior_record, prior_chars, prior_bytes, prior_lines = seen.pop(
                identity
            )
            records.remove(prior_record)
            total_chars -= prior_chars
            total_bytes -= prior_bytes
            total_lines -= prior_lines
            invalidated.add(identity)
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        if (
            total_chars + chars > policy.budgets.max_chars
            or total_bytes + byte_count > policy.budgets.max_bytes
            or total_lines + lines > policy.budgets.max_lines
        ):
            completeness[source] = "partial"
            degradation_counts["limit"] += 1
            required_degraded = required_degraded or reference.required
            continue
        total_chars += chars
        total_bytes += byte_count
        total_lines += lines
        publish = _publish_projection(
            normalized,
            reference.projections.publish,
            budgets=reference.budgets,
            forbidden=forbidden,
        )
        if publish is None:
            completeness[source] = "unavailable"
            degradation_counts["invalid"] += 1
            required_degraded = required_degraded or reference.required
            continue
        admitted = PendingContextRecord(
            source=source,
            adapter=reference.adapter,
            tenant=reference.tenant,
            canonical_object=response.canonical_object,
            resource_class=reference.resource_class,
            descriptor=str(normalized.get("descriptor", reference.resource_class)),
            projections={
                "model": _project(normalized, reference.projections.model),
                "publish": publish,
                "retain": _project(normalized, reference.projections.retain),
            },
            version=response.version,
            digest=digest,
            mutable=True,
            expiry=response.expiry,
        )
        records.append(admitted)
        seen[identity] = (response.version, digest, admitted, chars, byte_count, lines)
    return BrokerResult(
        records=tuple(records),
        completeness=dict(sorted(completeness.items())),
        degradation_counts=dict(sorted(degradation_counts.items())),
        required_degraded=required_degraded,
    )
