"""Configure OCR MCP servers from CI environment variables."""

from __future__ import annotations

import os
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, read_ocr_config, update_ocr_config
from ocr_toolkit.context.mcp import GET_TOOL as CONTEXT_GET_TOOL
from ocr_toolkit.context.mcp import LIST_TOOL as CONTEXT_LIST_TOOL
from ocr_toolkit.evidence.mcp import COVERAGE_TOOL_NAME, SEARCH_TOOL_NAME, TOOL_NAME
from ocr_toolkit.federation.contracts import FederationError, ServerSpec
from ocr_toolkit.federation.registry import parse_registry

MAX_MCP_CONFIG_BYTES = 64 * 1024
MAX_MCP_SERVERS = 16
BUILTIN_EVIDENCE_SERVER = "ocr_toolkit_evidence"
FEDERATION_SERVER = "ocr_toolkit_federation"
MCP_PROFILES = frozenset({"local", "gitlab_mr"})
MCPServerConfig = ServerSpec


class MCPConfigError(Exception):
    """The operator MCP registry or mandatory composition is invalid."""


@dataclass(frozen=True, slots=True)
class MCPCapability:
    """Describe one validated MCP server without transport credentials."""

    server: str
    tools: tuple[str, ...]
    builtin: bool = False
    transport: str = "stdio"


@dataclass(frozen=True, slots=True)
class MCPComposition:
    """Hold one validated OCR MCP payload and its safe capability inventory."""

    payload: dict[str, dict[str, Any]]
    capabilities: tuple[MCPCapability, ...]
    external_servers: tuple[MCPServerConfig, ...]
    secret_values: tuple[str, ...]
    federation_receipt: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class MCPContextConfig:
    """Bind the optional built-in context tools to one committed local store."""

    store_path: str
    run_id: str
    policy_digest: str
    dlp_enabled: bool = True


def parse_mcp_servers(raw: str | None = None, *, profile: str = "local") -> list[ServerSpec]:
    """Parse only version-two governed operator configuration."""

    if "OCR_MCP_REPLACE" in os.environ:
        raise MCPConfigError("OCR_MCP_REPLACE was removed; use the governed version 2 registry")
    source = os.environ.get("OCR_MCP_SERVERS_JSON", "") if raw is None else raw
    if not source.strip():
        return []
    try:
        registry = parse_registry(source, profile=profile)
    except FederationError as exc:
        raise MCPConfigError(
            "Invalid governed MCP registry; migrate OCR_MCP_SERVERS_JSON to version 2"
        ) from exc
    return list(registry.servers)


def compose_mcp_servers(
    servers: list[ServerSpec],
    *,
    replace: bool = True,
    profile: str = "local",
    context: MCPContextConfig | None = None,
    allow_external: bool = True,
    gateway: Any = None,
) -> MCPComposition:
    """Expose mandatory evidence and only a ready governed federation relay."""

    if profile not in MCP_PROFILES:
        raise MCPConfigError("internal MCP execution profile is invalid")
    if not allow_external and servers:
        raise MCPConfigError("unprotected-target reviews do not allow external MCP servers")
    if profile == "gitlab_mr" and any(server.transport != "https" for server in servers):
        raise MCPConfigError("GitLab merge-request reviews require HTTPS MCP")
    try:
        current = read_ocr_config().get("mcp_servers", {})
    except OCRConfigError as exc:
        raise MCPConfigError("Existing MCP configuration cannot be read") from exc
    if not isinstance(current, dict) or any(
        name not in {BUILTIN_EVIDENCE_SERVER, FEDERATION_SERVER} for name in current
    ):
        raise MCPConfigError(
            "Inherited direct MCP configuration was removed; migrate to registry version 2"
        )
    payload: dict[str, dict[str, Any]] = {}
    capabilities: list[MCPCapability] = []
    secret_values: list[str] = []
    if servers:
        if gateway is None:
            raise MCPConfigError("External MCP requires the review-owned prepared gateway")
        expected = tuple(sorted(tool.alias for server in servers for tool in server.tools))
        if tuple(sorted(gateway.aliases)) != expected:
            raise MCPConfigError("Prepared MCP inventory differs from operator registry")
        payload[FEDERATION_SERVER] = gateway.ocr_server
        secret_values.extend(gateway.secret_values)
        for server in servers:
            capabilities.append(
                MCPCapability(
                    server.name,
                    tuple(tool.alias for tool in server.tools),
                    transport="remote" if server.transport == "https" else "stdio",
                )
            )
    if not sys.executable or not os.path.isabs(sys.executable):
        raise MCPConfigError(
            "the running Python executable must be absolute for built-in MCP launch"
        )
    builtin_args = ["-I", "-m", "ocr_toolkit.evidence"]
    builtin_tools = [TOOL_NAME, SEARCH_TOOL_NAME, COVERAGE_TOOL_NAME]
    if context is not None:
        if not os.path.isabs(context.store_path):
            raise MCPConfigError("built-in context store path must be absolute")
        builtin_args.extend(
            [
                "--context-store",
                context.store_path,
                "--context-run-id",
                context.run_id,
                "--context-policy-digest",
                context.policy_digest,
                "--dlp-enabled",
                "true" if context.dlp_enabled else "false",
            ]
        )
        builtin_tools.extend((CONTEXT_LIST_TOOL, CONTEXT_GET_TOOL))
    payload[BUILTIN_EVIDENCE_SERVER] = {
        "type": "stdio",
        # OCR starts MCP servers in the untrusted repository and may use a
        # restricted PATH. Isolated mode prevents repository files from
        # shadowing the toolkit while the venv path binds this exact install.
        "command": sys.executable,
        "args": builtin_args,
        "env": [],
        "tools": builtin_tools,
        # OCR executes setup through a shell in the analyzed repository root.
        "setup": "",
    }
    capabilities.append(MCPCapability(BUILTIN_EVIDENCE_SERVER, tuple(builtin_tools), builtin=True))
    capabilities.sort(key=lambda capability: (not capability.builtin, capability.server))
    owners: dict[str, str] = {}
    for capability in capabilities:
        for tool in capability.tools:
            owner = owners.setdefault(tool, capability.server)
            if owner != capability.server:
                raise MCPConfigError(
                    f"MCP tool name {tool!r} is declared by both {owner!r} "
                    f"and {capability.server!r}"
                )
    return MCPComposition(
        payload=payload,
        capabilities=tuple(capabilities),
        external_servers=tuple(servers),
        secret_values=tuple(secret_values),
    )


def build_mcp_composition(
    *,
    profile: str = "local",
    context: MCPContextConfig | None = None,
    allow_external: bool = True,
    gateway: Any = None,
) -> MCPComposition:
    return compose_mcp_servers(
        parse_mcp_servers(profile=profile),
        profile=profile,
        context=context,
        allow_external=allow_external,
        gateway=gateway,
    )


def apply_mcp_composition(composition: MCPComposition) -> None:
    """Persist one validated MCP composition with redacted failures."""

    try:
        update_ocr_config({"mcp_servers": composition.payload})
    except (OCRConfigError, OSError) as exc:
        safe_error = _redact_extra_values(str(exc), list(composition.secret_values))
        raise MCPConfigError(f"Failed to update OCR MCP configuration: {safe_error}") from exc


def verify_mcp_composition(composition: MCPComposition) -> None:
    """Confirm OCR configuration retained every independently composed MCP entry."""

    try:
        configured = read_ocr_config().get("mcp_servers")
    except (OCRConfigError, OSError) as exc:
        raise MCPConfigError("Failed to read back OCR MCP configuration") from exc
    if not isinstance(configured, dict):
        raise MCPConfigError("OCR MCP configuration readback is not an object")
    if configured != composition.payload:
        raise MCPConfigError("OCR MCP configuration readback does not match the composed registry")


def _redact_extra_values(text: str, values: list[str]) -> str:
    """Redact raw and URL-encoded secret variants from an error string."""

    redacted = text
    for value in values:
        if value and len(value) >= 4:
            for variant in {
                value,
                urllib.parse.quote(value, safe=""),
                urllib.parse.quote_plus(value, safe=""),
            }:
                if variant:
                    redacted = redacted.replace(variant, "***")
    return redacted


def configure_mcp_servers() -> int:
    """Validate the operator registry; live external composition belongs to review."""

    try:
        servers = parse_mcp_servers()
        composition = compose_mcp_servers([])
        apply_mcp_composition(composition)
    except MCPConfigError as exc:
        print(f"Invalid OCR MCP configuration: {redact_sensitive(str(exc))}", file=sys.stderr)
        return 1
    for server in servers:
        for tool in server.tools:
            print(
                f"OCR MCP tool admitted: server={server.name} tool={tool.alias} assurance={tool.assurance}"
            )
    print(
        f"OCR MCP configured: mandatory={BUILTIN_EVIDENCE_SERVER}; external sessions start at review"
    )
    return 0
