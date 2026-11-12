"""Exact qualified toolkit handoffs, independent of runtime version acceptance."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

NativeCapability = Literal["diagram_output", "gitlink_projection", "inference_query"]

# Adjacent patches require the real controlled-peer consumer suite before entry.
# A supported OCR version does not automatically qualify an optional handoff.
_QUALIFIED_HANDOFFS = {
    "1.13.3": frozenset({"diagram_output", "gitlink_projection"}),
    "1.13.4": frozenset({"diagram_output", "gitlink_projection"}),
    "1.13.5": frozenset({"diagram_output", "gitlink_projection"}),
    "1.13.6": frozenset({"diagram_output", "gitlink_projection"}),
    "1.13.7": frozenset({"diagram_output", "gitlink_projection"}),
    "1.13.8": frozenset({"diagram_output", "gitlink_projection"}),
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
