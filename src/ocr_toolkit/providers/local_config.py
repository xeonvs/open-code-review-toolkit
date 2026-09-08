"""Validate the input capabilities supported by standalone review."""

from collections.abc import Mapping

from ocr_toolkit.evidence.review_context import parse_review_context_mode


def validate_local_context(environment: Mapping[str, str]) -> None:
    """Reject explicit unsupported channels before acquiring inputs or credentials."""

    if parse_review_context_mode(environment.get("OCR_REVIEW_CONTEXT_MODE")) != "off":
        raise ValueError("local review does not support change-request context")
    if environment.get("OCR_REVIEW_CONTEXT_ADAPTERS_JSON") is not None:
        raise ValueError("local review does not support context adapters")
