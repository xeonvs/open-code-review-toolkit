"""Normalize and validate bounded untrusted merge-request context evidence."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from ocr_toolkit.common.redaction import redact_env_secret_values, redact_sensitive
from ocr_toolkit.evidence.model import (
    Confidence,
    EvidenceRecord,
    RefRole,
    Sensitivity,
    TrustClass,
)

CONTEXT_KIND = "review.merge_request_context"
CONTEXT_SCHEMA = "review.merge-request-context/v1"
CONTEXT_SOURCE = ".ocr-toolkit/merge-request-context"
FIELD_STATUSES = frozenset(
    {
        "absent",
        "admitted",
        "omitted_invalid",
        "omitted_limit",
        "omitted_redaction_limit",
    }
)
LABEL_STATUSES = frozenset(
    {
        "absent",
        "admitted",
        "omitted_invalid",
        "omitted_limit",
        "partial",
        "omitted_collision",
    }
)
MAX_LABELS = 32
CONTEXT_MODES = frozenset({"off", "metadata", "enriched"})


class ReviewContextModeError(ValueError):
    """Report an unsupported or unavailable review-context mode safely."""


def parse_review_context_mode(raw: str | None) -> str:
    """Return the closed context mode without echoing untrusted configuration."""

    mode = (raw or "").strip().lower() or "off"
    if mode not in CONTEXT_MODES:
        raise ReviewContextModeError("OCR_REVIEW_CONTEXT_MODE is invalid")
    return mode or "off"


def context_provenance(provider: str) -> str:
    """Return closed provenance for one normalized code-host adapter name."""

    return f"provider.{provider}.merge_request"


@dataclass(frozen=True, slots=True)
class TextLimit:
    """Declare independent complete-field text bounds."""

    chars: int
    bytes: int
    lines: int


TEXT_LIMITS = {
    "title": TextLimit(chars=512, bytes=2_048, lines=1),
    "description": TextLimit(chars=12_000, bytes=32_000, lines=200),
    "source_branch": TextLimit(chars=512, bytes=2_048, lines=1),
}
LABEL_LIMIT = TextLimit(chars=128, bytes=512, lines=1)


@dataclass(frozen=True, slots=True)
class MergeRequestContext:
    """Hold one provider-neutral normalized point-in-time intent descriptor."""

    provider: str
    project_id: str
    merge_request_iid: str
    source_sha: str
    fields: Mapping[str, object]

    @property
    def admitted(self) -> bool:
        """Return whether any author-controlled value survived normalization."""

        for name in ("title", "description", "source_branch"):
            field = self.fields.get(name)
            if isinstance(field, Mapping) and field.get("status") == "admitted":
                return True
        labels = self.fields.get("labels")
        return bool(isinstance(labels, Mapping) and labels.get("values"))

    @property
    def state(self) -> str:
        """Return whether every selected metadata field is completely represented."""

        complete_text = {"absent", "admitted"}
        complete_labels = {"absent", "admitted"}
        for name in ("title", "description", "source_branch"):
            field = self.fields.get(name)
            if not isinstance(field, Mapping) or field.get("status") not in complete_text:
                return "degraded"
        labels = self.fields.get("labels")
        if not isinstance(labels, Mapping) or labels.get("status") not in complete_labels:
            return "degraded"
        return "complete"

    def evidence_value(self) -> dict[str, object]:
        """Return the closed persisted descriptor value."""

        return {
            "schema_version": CONTEXT_SCHEMA,
            "provider": self.provider,
            "project_id": self.project_id,
            "merge_request_iid": self.merge_request_iid,
            "source_sha": self.source_sha,
            "content_role": "untrusted_data",
            "authoritative_for_actions": False,
            "fields": dict(self.fields),
        }


def _normalized_text(value: object) -> str | None:
    """Return NFC text without provider-controlled Unicode controls."""

    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    return "".join(
        character
        for character in normalized
        if character == "\n"
        or unicodedata.category(character) not in {"Cc", "Cf", "Cs", "Zl", "Zp"}
    ).strip()


def _within(value: str, limit: TextLimit) -> bool:
    """Apply character, UTF-8 byte, and physical-line bounds together."""

    return (
        len(value) <= limit.chars
        and len(value.encode("utf-8")) <= limit.bytes
        and value.count("\n") + 1 <= limit.lines
    )


def _redacted(value: str) -> str:
    """Apply both generic and configured-secret redaction before persistence."""

    return redact_env_secret_values(redact_sensitive(value))


def _text_field(value: object, limit: TextLimit) -> dict[str, object]:
    """Admit one complete field or record only its closed omission status."""

    if value is None or value == "":
        return {"status": "absent", "value": None}
    normalized = _normalized_text(value)
    if normalized is None:
        return {"status": "omitted_invalid", "value": None}
    if not normalized:
        return {"status": "absent", "value": None}
    if not _within(normalized, limit):
        return {"status": "omitted_limit", "value": None}
    redacted = _redacted(normalized)
    if not _within(redacted, limit):
        return {"status": "omitted_redaction_limit", "value": None}
    return {"status": "admitted", "value": redacted}


def _labels_field(value: object) -> dict[str, object]:
    """Admit a bounded label prefix with explicit partial and collision states."""

    if value is None or value == []:
        return {"status": "absent", "values": [], "omitted_count": 0}
    if not isinstance(value, list):
        return {"status": "omitted_invalid", "values": [], "omitted_count": 0}
    accepted: list[str] = []
    omitted = min(100_000, max(0, len(value) - MAX_LABELS))
    seen: set[str] = set()
    collision = False
    for item in value[:MAX_LABELS]:
        normalized = _normalized_text(item)
        if normalized is None or not normalized or not _within(normalized, LABEL_LIMIT):
            omitted += 1
            continue
        redacted = _redacted(normalized)
        if not _within(redacted, LABEL_LIMIT):
            omitted += 1
            continue
        identity = redacted.casefold()
        if identity in seen:
            collision = True
            break
        seen.add(identity)
        accepted.append(redacted)
    if collision:
        return {
            "status": "omitted_collision",
            "values": [],
            "omitted_count": min(100_000, len(value)),
        }
    omitted = min(100_000, omitted)
    status = "partial" if omitted else "admitted"
    if not accepted:
        status = "omitted_limit" if value else "absent"
    return {"status": status, "values": accepted, "omitted_count": omitted}


def normalize_merge_request_context(
    *,
    provider: str,
    project_id: str,
    merge_request_iid: str,
    source_sha: str,
    title: object,
    description: object,
    labels: object,
    source_branch: object,
) -> MergeRequestContext:
    """Project one provider payload into the closed untrusted descriptor."""

    raw_fields = {
        "title": title,
        "description": description,
        "source_branch": source_branch,
    }
    fields: dict[str, object] = {
        name: _text_field(raw_fields[name], limit) for name, limit in TEXT_LIMITS.items()
    }
    fields["labels"] = _labels_field(labels)
    context = MergeRequestContext(
        provider=provider,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        source_sha=source_sha,
        fields=fields,
    )
    validate_merge_request_context(context.evidence_value())
    return context


def merge_request_context_record(context: MergeRequestContext) -> EvidenceRecord:
    """Bind one normalized provider snapshot to reviewed-head invocation trust."""
    return EvidenceRecord(
        kind=CONTEXT_KIND,
        value=context.evidence_value(),
        source_path=CONTEXT_SOURCE,
        ref=RefRole.SHARED,
        commit_sha=context.source_sha,
        component="review",
        provenance=context_provenance(context.provider),
        confidence=Confidence.EXACT,
        trust=TrustClass.INVOCATION,
        sensitivity=Sensitivity.REDACTED,
    )


def _safe_provider(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 32
        and value.isascii()
        and value[0].isalpha()
        and value == value.lower()
        and all(character.isalnum() or character == "_" for character in value)
    )


def _safe_identity(value: object) -> bool:
    return (
        isinstance(value, str) and 1 <= len(value) <= 32 and value.isascii() and value.isdecimal()
    )


def _validate_text_field(value: object, limit: TextLimit) -> None:
    if not isinstance(value, Mapping) or set(value) != {"status", "value"}:
        raise ValueError("merge-request text field shape is invalid")
    status = value["status"]
    text = value["value"]
    if status not in FIELD_STATUSES:
        raise ValueError("merge-request text field status is invalid")
    if status == "admitted":
        if (
            not isinstance(text, str)
            or not text
            or _normalized_text(text) != text
            or not _within(text, limit)
        ):
            raise ValueError("merge-request admitted text field is invalid")
        if _redacted(text) != text:
            raise ValueError("merge-request admitted text field is not fully redacted")
    elif text is not None:
        raise ValueError("merge-request omitted text field must not contain a value")


def validate_merge_request_context(value: object) -> None:
    """Revalidate the exact descriptor schema on admission and hostile readback."""

    if not isinstance(value, Mapping) or set(value) != {
        "schema_version",
        "provider",
        "project_id",
        "merge_request_iid",
        "source_sha",
        "content_role",
        "authoritative_for_actions",
        "fields",
    }:
        raise ValueError("merge-request context fields are invalid")
    if (
        value["schema_version"] != CONTEXT_SCHEMA
        or not _safe_provider(value["provider"])
        or value["content_role"] != "untrusted_data"
        or value["authoritative_for_actions"] is not False
        or not _safe_identity(value["project_id"])
        or not _safe_identity(value["merge_request_iid"])
        or not isinstance(value["source_sha"], str)
        or len(value["source_sha"]) != 40
        or any(character not in "0123456789abcdef" for character in value["source_sha"])
    ):
        raise ValueError("merge-request context identity is invalid")
    fields = value["fields"]
    if not isinstance(fields, Mapping) or set(fields) != {
        "title",
        "description",
        "source_branch",
        "labels",
    }:
        raise ValueError("merge-request context field inventory is invalid")
    for name, limit in TEXT_LIMITS.items():
        _validate_text_field(fields[name], limit)
    labels = fields["labels"]
    if not isinstance(labels, Mapping) or set(labels) != {"status", "values", "omitted_count"}:
        raise ValueError("merge-request labels field shape is invalid")
    status = labels["status"]
    values = labels["values"]
    omitted = labels["omitted_count"]
    if (
        status not in LABEL_STATUSES
        or not isinstance(values, (list, tuple))
        or len(values) > MAX_LABELS
        or not isinstance(omitted, int)
        or isinstance(omitted, bool)
        or omitted < 0
        or omitted > 100_000
        or not all(
            isinstance(item, str)
            and item
            and _normalized_text(item) == item
            and _within(item, LABEL_LIMIT)
            and _redacted(item) == item
            for item in values
        )
        or len({item.casefold() for item in values}) != len(values)
    ):
        raise ValueError("merge-request labels field is invalid")
    if status == "admitted" and (not values or omitted):
        raise ValueError("admitted merge-request labels are inconsistent")
    if status == "partial" and (not values or not omitted):
        raise ValueError("partial merge-request labels are inconsistent")
    if status not in {"admitted", "partial"} and values:
        raise ValueError("omitted merge-request labels must not contain values")
    if status in {"absent", "omitted_invalid"} and omitted:
        raise ValueError("merge-request label omission count is inconsistent")
    if status in {"omitted_limit", "omitted_collision"} and not omitted:
        raise ValueError("merge-request label omission count is inconsistent")
    if status == "omitted_collision" and omitted < 2:
        raise ValueError("merge-request label collision count is inconsistent")
