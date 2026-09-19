"""Closed federation configuration, limits, and content-free failures."""

from __future__ import annotations

from dataclasses import dataclass

REGISTRY_BYTES = 64 * 1024
SCHEMA_BYTES = 16 * 1024
ARGUMENT_BYTES = 32 * 1024
RESPONSE_BYTES = 256 * 1024
RESPONSE_CHARS = 128 * 1024
RESPONSE_ITEMS = 128
DELIVERY_BYTES = 2 * 1024 * 1024
METADATA_BYTES = 128 * 1024
WIRE_BYTES = 8 * 1024 * 1024
WIRE_REQUESTS = 256
MAX_CALLS = 64
CONCURRENCY = 4
CALL_SECONDS = 30.0
RUN_SECONDS = 300.0
CACHE_ENTRIES = 32
CACHE_BYTES = 1024 * 1024
COUNTERS = (
    "attempted",
    "completed",
    "denied",
    "failed",
    "timed_out",
    "dlp_rejected",
    "oversized",
    "cache_hits",
    "single_flight",
)


class FederationError(ValueError):
    """Expose only one closed, content-free failure code."""

    def __init__(self, code: str = "federation_failed") -> None:
        allowed = {
            "registry_invalid",
            "secret_missing",
            "schema_invalid",
            "arguments_invalid",
            "origin_denied",
            "dlp_rejected",
            "oversized",
            "budget_exceeded",
            "timed_out",
            "transport_failed",
            "protocol_invalid",
            "inventory_invalid",
            "cleanup_failed",
            "gateway_unavailable",
            "federation_failed",
            "tool_failed",
        }
        self.code = code if code in allowed else "federation_failed"
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """Bind a single selected upstream tool to operator-only authority."""

    name: str
    alias: str
    assurance: str = "advisory"
    resource_origins: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ServerSpec:
    """Hold validated transport locations and secret variable names only."""

    name: str
    transport: str
    tools: tuple[ToolPolicy, ...]
    url: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    env_from: tuple[tuple[str, str], ...] = ()
    token_from: str | None = None
    headers_from: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Registry:
    """Represent one exact version-two operator registry."""

    servers: tuple[ServerSpec, ...]
    version: int = 2
