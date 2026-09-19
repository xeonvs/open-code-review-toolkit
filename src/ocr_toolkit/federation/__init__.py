"""Governed model-directed MCP federation, independent from built-in evidence."""

from .contracts import FederationError, Registry, ServerSpec, ToolPolicy
from .registry import parse_registry
from .runtime import RunningGateway, start_gateway

__all__ = [
    "FederationError",
    "Registry",
    "RunningGateway",
    "ServerSpec",
    "ToolPolicy",
    "parse_registry",
    "start_gateway",
]
