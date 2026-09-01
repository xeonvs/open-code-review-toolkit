"""Redact and bound evidence values before admission or public projection."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from ocr_toolkit.common.redaction import (
    SENSITIVE_NAMED_KEY_PATTERN,
    redact_sensitive,
)
from ocr_toolkit.evidence.model import EvidenceValue
from ocr_toolkit.evidence.store.contracts import EvidenceStoreError


class EvidenceValueRedactionError(EvidenceStoreError):
    """Report an ambiguous mapping produced by recursive key redaction."""


def redact_value(value: EvidenceValue) -> EvidenceValue:
    """Recursively redact string leaves before evidence reaches persistent storage."""

    if isinstance(value, str):
        return redact_sensitive(value)
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    if isinstance(value, Mapping):
        redacted_mapping: dict[str, EvidenceValue] = {}
        for key, item in value.items():
            redacted_key = redact_sensitive(key)
            if not redacted_key:
                raise EvidenceValueRedactionError("evidence object key is empty after redaction")
            if redacted_key in redacted_mapping:
                raise EvidenceValueRedactionError("evidence object keys collide after redaction")
            redacted_mapping[redacted_key] = (
                "[REDACTED]"
                if re.fullmatch(
                    SENSITIVE_NAMED_KEY_PATTERN,
                    redacted_key,
                    flags=re.IGNORECASE,
                )
                else redact_value(item)
            )
        return redacted_mapping
    return value


def safe_value(value: EvidenceValue, max_chars: int) -> EvidenceValue:
    """Redact a nested value and enforce the schema's code-point budget."""

    redacted = redact_value(value)
    if len(json.dumps(redacted, ensure_ascii=False)) > max_chars:
        raise EvidenceStoreError(f"evidence value exceeds {max_chars} characters")
    return redacted


def safe_diagnostic(message: object) -> str:
    """Return one redacted diagnostic within the public schema limit."""

    if not isinstance(message, str) or not message or len(message) > 1024:
        raise EvidenceStoreError("evidence diagnostic must contain between 1 and 1024 characters")
    return redact_sensitive(message)


def safe_delta_metadata(value: str, *, name: str, max_chars: int) -> str:
    """Redact and bound one repository-derived delta metadata field."""

    redacted = redact_sensitive(value)
    if not redacted or len(redacted) > max_chars:
        raise EvidenceStoreError(f"evidence delta {name} exceeds its metadata budget")
    return redacted
