"""Exact qualified toolkit handoffs, independent of runtime version acceptance."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Literal
from urllib.parse import urlsplit

NativeCapability = Literal[
    "analysis", "chatgpt_auth", "diagram_output", "gitlink_projection", "inference_query"
]

# Generated during promotion from checksum-verified consumer evidence.
_QUALIFIED_HANDOFFS: dict[str, frozenset[str]] = {
    version: frozenset(capabilities)
    for version, capabilities in json.loads(
        files("ocr_toolkit").joinpath("_qualified_handoffs.json").read_bytes()
    ).items()
}


def supports_native_capability(version: str | None, capability: NativeCapability) -> bool:
    """Fail closed for absent, noncanonical or unqualified versions/capabilities."""

    return isinstance(version, str) and capability in _QUALIFIED_HANDOFFS.get(version, ())


def require_native_inference_url(version: str, url: str) -> None:
    """Reject a valid URL when the exact native client cannot preserve its query."""

    if urlsplit(url).query and not supports_native_capability(version, "inference_query"):
        raise ValueError(
            "The qualified OCR client does not support OCR_LLM_URL query parameters; "
            "use a query-free endpoint or provider-supported headers"
        )
