"""Configure OCR MCP servers from CI environment variables."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.config_writer import OCRConfigError, read_ocr_config, update_ocr_config
from ocr_toolkit.evidence.mcp import TOOL_NAME

MAX_MCP_CONFIG_BYTES = 64_000
MAX_MCP_SERVERS = 16
MAX_MCP_ARGS = 64
MAX_MCP_ENV = 64
MAX_MCP_HEADERS = 32
MAX_MCP_TOOLS = 128
MAX_MCP_URL_CHARS = 2_048
MAX_MCP_HEADER_VALUE_CHARS = 2_048
MAX_MCP_SETUP_CHARS = 4_096
MAX_MCP_STRING_CHARS = 4_096
MCP_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MCP_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MCP_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
SENSITIVE_HEADER_NAME_RE = re.compile(
    r"(?:^|[-_])(?:authorization|authentication|auth|cookie|api[-_]?key|"
    r"subscription[-_]?key|key|token|secret|credential)(?:$|[-_])",
    flags=re.IGNORECASE,
)
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
BUILTIN_EVIDENCE_SERVER = "ocr_toolkit_evidence"


class MCPConfigError(Exception):
    """The MCP CI configuration is invalid."""


@dataclass(frozen=True)
class MCPServerConfig:
    """Validated OCR MCP server configuration for one transport."""

    name: str
    transport: str
    command: str | None
    url: str | None
    args: list[str]
    tools: list[str]
    setup: str
    env: list[str]
    headers: dict[str, str]
    secret_values: list[str]


@dataclass(frozen=True, slots=True)
class MCPCapability:
    """Describe one validated MCP server without transport credentials."""

    server: str
    tools: tuple[str, ...]
    builtin: bool = False


@dataclass(frozen=True, slots=True)
class MCPComposition:
    """Hold one validated OCR MCP payload and its safe capability inventory."""

    payload: dict[str, dict[str, Any]]
    capabilities: tuple[MCPCapability, ...]
    external_servers: tuple[MCPServerConfig, ...]
    secret_values: tuple[str, ...]


def _string_list(value: Any, field: str, *, limit: int) -> list[str]:
    """Validate one bounded JSON string list and preserve its order."""

    if not isinstance(value, list):
        raise MCPConfigError(f"{field} must be a JSON array of strings")
    if len(value) > limit:
        raise MCPConfigError(f"{field} exceeds maximum item count {limit}")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise MCPConfigError(f"{field}[{index}] must be a string")
        if len(item) > MAX_MCP_STRING_CHARS:
            raise MCPConfigError(f"{field}[{index}] exceeds maximum length {MAX_MCP_STRING_CHARS}")
        result.append(item)
    return result


def _env_assignments(value: Any, env_from: Any, server_name: str) -> tuple[list[str], list[str]]:
    """Build stdio environment assignments and collect values for redaction."""

    assignments: list[str] = []
    secret_values: list[str] = []

    if value is None:
        value = {}
    if env_from is None:
        env_from = {}
    if not isinstance(value, dict):
        raise MCPConfigError(f"servers.{server_name}.env must be an object")
    if not isinstance(env_from, dict):
        raise MCPConfigError(f"servers.{server_name}.env_from must be an object")
    if len(value) + len(env_from) > MAX_MCP_ENV:
        raise MCPConfigError(
            f"servers.{server_name}.env/env_from exceed maximum item count {MAX_MCP_ENV}"
        )

    for key, item in value.items():
        if not isinstance(key, str) or not MCP_ENV_NAME_RE.fullmatch(key):
            raise MCPConfigError(f"servers.{server_name}.env contains invalid env name")
        if not isinstance(item, str):
            raise MCPConfigError(f"servers.{server_name}.env.{key} must be a string")
        if len(key) + len(item) + 1 > MAX_MCP_STRING_CHARS:
            raise MCPConfigError(
                f"servers.{server_name}.env.{key} exceeds maximum length {MAX_MCP_STRING_CHARS}"
            )
        assignments.append(f"{key}={item}")

    for key, source_name in env_from.items():
        if not isinstance(key, str) or not MCP_ENV_NAME_RE.fullmatch(key):
            raise MCPConfigError(f"servers.{server_name}.env_from contains invalid env name")
        if key in value:
            raise MCPConfigError(
                f"servers.{server_name}.env_from.{key} duplicates servers.{server_name}.env.{key}"
            )
        if not isinstance(source_name, str) or not MCP_ENV_NAME_RE.fullmatch(source_name):
            raise MCPConfigError(f"servers.{server_name}.env_from.{key} must name a CI variable")
        if source_name not in os.environ:
            raise MCPConfigError(
                f"servers.{server_name}.env_from.{key} references missing CI variable {source_name}"
            )
        secret_value = os.environ[source_name]
        assignments.append(f"{key}={secret_value}")
        if secret_value:
            secret_values.append(secret_value)

    return assignments, secret_values


def _validate_header_name(name: Any, field: str) -> str:
    """Return an HTTP token header name or reject the input."""

    if not isinstance(name, str) or not MCP_HEADER_NAME_RE.fullmatch(name):
        raise MCPConfigError(f"{field} contains an invalid HTTP header name")
    return name


def _headers(value: Any, env_from: Any, server_name: str) -> tuple[dict[str, str], list[str]]:
    """Project bounded literal and environment-backed headers into OCR syntax."""

    if value is None:
        value = {}
    if env_from is None:
        env_from = {}
    if not isinstance(value, dict):
        raise MCPConfigError(f"servers.{server_name}.headers must be an object")
    if not isinstance(env_from, dict):
        raise MCPConfigError(f"servers.{server_name}.headers_from must be an object")
    if len(value) + len(env_from) > MAX_MCP_HEADERS:
        raise MCPConfigError(
            f"servers.{server_name}.headers/headers_from exceed maximum item count "
            f"{MAX_MCP_HEADERS}"
        )

    result: dict[str, str] = {}
    normalized_names: set[str] = set()
    secret_values: list[str] = []
    for raw_name, item in value.items():
        name = _validate_header_name(raw_name, f"servers.{server_name}.headers")
        normalized = name.casefold()
        if normalized in normalized_names:
            raise MCPConfigError(f"servers.{server_name} contains duplicate HTTP header {name!r}")
        normalized_names.add(normalized)
        # Literal credentials would be copied into both CI input and OCR's on-disk
        # config. Sensitive header families must cross this boundary only through
        # an environment-variable reference.
        if SENSITIVE_HEADER_NAME_RE.search(name):
            raise MCPConfigError(
                f"servers.{server_name}.headers.{name} is sensitive; use headers_from"
            )
        if not isinstance(item, str):
            raise MCPConfigError(f"servers.{server_name}.headers.{name} must be a string")
        if not item or len(item) > MAX_MCP_HEADER_VALUE_CHARS:
            raise MCPConfigError(
                f"servers.{server_name}.headers.{name} must be non-empty and at most "
                f"{MAX_MCP_HEADER_VALUE_CHARS} characters"
            )
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in item):
            raise MCPConfigError(
                f"servers.{server_name}.headers.{name} contains invalid control characters"
            )
        result[name] = item

    for raw_name, source_name in env_from.items():
        name = _validate_header_name(raw_name, f"servers.{server_name}.headers_from")
        normalized = name.casefold()
        if normalized in normalized_names:
            raise MCPConfigError(f"servers.{server_name} contains duplicate HTTP header {name!r}")
        normalized_names.add(normalized)
        if not isinstance(source_name, str) or not MCP_ENV_NAME_RE.fullmatch(source_name):
            raise MCPConfigError(
                f"servers.{server_name}.headers_from.{name} must name a CI variable"
            )
        secret_value = os.environ.get(source_name)
        if not secret_value:
            raise MCPConfigError(
                f"servers.{server_name}.headers_from.{name} references missing or empty CI "
                f"variable {source_name}"
            )
        if len(secret_value) > MAX_MCP_HEADER_VALUE_CHARS:
            raise MCPConfigError(
                f"servers.{server_name}.headers_from.{name} references a CI variable "
                f"exceeding {MAX_MCP_HEADER_VALUE_CHARS} characters"
            )
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in secret_value):
            raise MCPConfigError(
                f"servers.{server_name}.headers_from.{name} references a CI variable "
                "containing invalid HTTP control characters"
            )
        # OCR 1.8 expands $VARNAME when it creates the remote client. Keeping the
        # reference avoids serializing the secret into config.json. Read the value
        # once so missing credentials fail early and downstream errors can redact it.
        result[name] = f"${source_name}"
        secret_values.append(secret_value)

    return result, secret_values


def _remote_url(value: Any, server_name: str) -> str:
    """Validate a bounded HTTPS Streamable HTTP endpoint for OCR."""

    if not isinstance(value, str) or not value or len(value) > MAX_MCP_URL_CHARS:
        raise MCPConfigError(
            f"servers.{server_name}.url must be a non-empty HTTPS URL of at most "
            f"{MAX_MCP_URL_CHARS} characters"
        )
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise MCPConfigError(f"servers.{server_name}.url contains invalid control characters")
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise MCPConfigError(f"servers.{server_name}.url is not a valid HTTPS URL") from exc
    # OCR accepts plain HTTP, but the toolkit's CI contract is stricter because
    # credentials can traverse this endpoint. Userinfo and fragments are rejected
    # because they add leak-prone ambiguity; queries are accepted but never logged.
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65_535)
    ):
        raise MCPConfigError(
            f"servers.{server_name}.url must be absolute HTTPS without userinfo or fragment"
        )
    return value


def parse_mcp_servers(raw: str | None = None) -> list[MCPServerConfig]:
    """Return bounded stdio and remote configs from OCR_MCP_SERVERS_JSON."""

    raw = os.environ.get("OCR_MCP_SERVERS_JSON", "") if raw is None else raw
    raw = raw.strip()
    if not raw:
        return []
    if len(raw.encode("utf-8")) > MAX_MCP_CONFIG_BYTES:
        raise MCPConfigError(f"OCR_MCP_SERVERS_JSON exceeds {MAX_MCP_CONFIG_BYTES} bytes")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MCPConfigError(
            "OCR_MCP_SERVERS_JSON is not valid JSON; check CI variable formatting"
        ) from exc
    except RecursionError as exc:
        raise MCPConfigError("OCR_MCP_SERVERS_JSON is too deeply nested") from exc

    if not isinstance(payload, dict):
        raise MCPConfigError("OCR_MCP_SERVERS_JSON top-level value must be an object")
    if "servers" in payload:
        if len(payload) != 1:
            raise MCPConfigError(
                "OCR_MCP_SERVERS_JSON cannot mix the servers envelope with named servers"
            )
        servers_value = payload["servers"]
        if not isinstance(servers_value, list):
            raise MCPConfigError("OCR_MCP_SERVERS_JSON.servers must be an array")
    else:
        servers_value = []
        for name, value in payload.items():
            if not isinstance(value, dict):
                raise MCPConfigError(f"OCR MCP server {name!r} configuration must be an object")
            if "name" in value and value["name"] != name:
                raise MCPConfigError(f"OCR MCP server {name!r} must not declare a different name")
            servers_value.append({**value, "name": name})
    if len(servers_value) > MAX_MCP_SERVERS:
        raise MCPConfigError(f"OCR_MCP_SERVERS_JSON has more than {MAX_MCP_SERVERS} servers")

    seen: set[str] = set()
    servers: list[MCPServerConfig] = []
    for index, server in enumerate(servers_value):
        if not isinstance(server, dict):
            raise MCPConfigError(f"servers[{index}] must be an object")
        enabled = server.get("enabled", True)
        if not isinstance(enabled, bool):
            raise MCPConfigError(f"servers[{index}].enabled must be a boolean")
        if enabled is False:
            continue

        name = server.get("name")
        if not isinstance(name, str) or not MCP_NAME_RE.fullmatch(name):
            raise MCPConfigError(f"servers[{index}].name is invalid")
        if name in seen:
            raise MCPConfigError(f"duplicate MCP server name {name!r}")
        if name == BUILTIN_EVIDENCE_SERVER:
            raise MCPConfigError(
                f"MCP server name {BUILTIN_EVIDENCE_SERVER!r} is reserved by the toolkit"
            )
        seen.add(name)
        transport = server.get("type", "stdio")
        if transport not in {"stdio", "remote"}:
            raise MCPConfigError(f"servers.{name}.type must be 'stdio' or 'remote'")
        common_fields = {"name", "type", "enabled", "tools", "setup"}
        transport_fields = (
            {"command", "args", "env", "env_from"}
            if transport == "stdio"
            else {"url", "headers", "headers_from"}
        )
        unknown_fields = set(server) - common_fields - transport_fields
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise MCPConfigError(f"servers.{name} has unsupported fields for {transport}: {fields}")

        tools = _string_list(server.get("tools", []), f"servers.{name}.tools", limit=MAX_MCP_TOOLS)
        if not tools:
            raise MCPConfigError(f"servers.{name}.tools must explicitly allow at least one tool")
        if TOOL_NAME in tools:
            raise MCPConfigError(f"MCP tool name {TOOL_NAME!r} is reserved by the toolkit")
        setup = server.get("setup", "")
        if not isinstance(setup, str):
            raise MCPConfigError(f"servers.{name}.setup must be a string")
        if len(setup) > MAX_MCP_SETUP_CHARS:
            raise MCPConfigError(
                f"servers.{name}.setup exceeds maximum length {MAX_MCP_SETUP_CHARS}"
            )

        command: str | None = None
        url: str | None = None
        args: list[str] = []
        env: list[str] = []
        headers: dict[str, str] = {}
        secret_values: list[str] = []
        if transport == "stdio":
            command_value = server.get("command")
            if not isinstance(command_value, str) or not command_value.strip():
                raise MCPConfigError(f"servers.{name}.command must be a non-empty string")
            command = command_value.strip()
            if len(command) > MAX_MCP_STRING_CHARS:
                raise MCPConfigError(
                    f"servers.{name}.command exceeds maximum length {MAX_MCP_STRING_CHARS}"
                )
            args = _string_list(server.get("args", []), f"servers.{name}.args", limit=MAX_MCP_ARGS)
            env, secret_values = _env_assignments(server.get("env"), server.get("env_from"), name)
        else:
            url = _remote_url(server.get("url"), name)
            headers, secret_values = _headers(
                server.get("headers"), server.get("headers_from"), name
            )
        servers.append(
            MCPServerConfig(
                name=name,
                transport=transport,
                command=command,
                url=url,
                args=args,
                tools=tools,
                setup=setup,
                env=env,
                headers=headers,
                secret_values=secret_values,
            )
        )

    return servers


def _replace_configured_servers() -> bool:
    """Return whether generated servers replace, rather than merge with, OCR state."""

    value = os.environ.get("OCR_MCP_REPLACE", "false").strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise MCPConfigError("OCR_MCP_REPLACE must be a boolean (true/false, 1/0, yes/no, or on/off)")


def _existing_capability(name: str, value: Any) -> MCPCapability:
    """Validate the safe capability fields of one existing OCR MCP entry."""

    if not isinstance(name, str) or not MCP_NAME_RE.fullmatch(name):
        raise MCPConfigError("Existing OCR MCP server name is invalid")
    if not isinstance(value, dict):
        raise MCPConfigError(f"Existing OCR MCP server {name!r} is not a JSON object")
    tools = _string_list(value.get("tools", []), f"existing.{name}.tools", limit=MAX_MCP_TOOLS)
    if not tools:
        raise MCPConfigError(
            f"Existing OCR MCP server {name!r} must explicitly allow at least one tool"
        )
    if TOOL_NAME in tools:
        raise MCPConfigError(f"Existing MCP tool name {TOOL_NAME!r} is reserved by the toolkit")
    return MCPCapability(name, tuple(tools))


def compose_mcp_servers(servers: list[MCPServerConfig], *, replace: bool) -> MCPComposition:
    """Build OCR's registry from independent optional and mandatory MCP entries."""

    payload: dict[str, dict[str, Any]] = {}
    capabilities: list[MCPCapability] = []
    if not replace:
        try:
            current = read_ocr_config().get("mcp_servers", {})
        except OCRConfigError as exc:
            raise MCPConfigError(str(exc)) from exc
        if not isinstance(current, dict):
            raise MCPConfigError("Existing OCR mcp_servers value is not a JSON object")
        for name, value in current.items():
            if name == BUILTIN_EVIDENCE_SERVER:
                continue
            capability = _existing_capability(name, value)
            payload[name] = value
            capabilities.append(capability)

    secret_values: list[str] = []
    for server in servers:
        payload[server.name] = {
            "type": server.transport,
            "setup": server.setup,
            "tools": server.tools,
        }
        if server.transport == "stdio":
            payload[server.name].update(
                {"command": server.command, "args": server.args, "env": server.env}
            )
        else:
            payload[server.name].update({"url": server.url, "headers": server.headers})
        secret_values.extend(server.secret_values)
        capability = MCPCapability(server.name, tuple(server.tools))
        capabilities = [item for item in capabilities if item.server != server.name]
        capabilities.append(capability)

    payload[BUILTIN_EVIDENCE_SERVER] = {
        "type": "stdio",
        "command": "ocr-ci",
        "args": ["evidence-serve"],
        "env": [],
        "tools": [TOOL_NAME],
        # OCR executes setup through a shell in the analyzed repository root.
        "setup": "",
    }
    capabilities.append(MCPCapability(BUILTIN_EVIDENCE_SERVER, (TOOL_NAME,), builtin=True))
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


def build_mcp_composition() -> MCPComposition:
    """Parse environment settings into the complete OCR MCP composition."""

    return compose_mcp_servers(parse_mcp_servers(), replace=_replace_configured_servers())


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
    """Configure the composed OCR MCP set and return a process exit code."""

    try:
        composition = build_mcp_composition()
        apply_mcp_composition(composition)
    except MCPConfigError as exc:
        print(f"Invalid OCR MCP configuration: {redact_sensitive(str(exc))}", file=sys.stderr)
        return 1

    for server in composition.external_servers:
        if server.transport == "stdio":
            detail = f"args={len(server.args)} env={len(server.env)}"
        else:
            detail = f"headers={len(server.headers)}"
        print(
            f"OCR MCP server configured: {server.name} type={server.transport} "
            f"{detail} tools={len(server.tools)}"
        )
    print(f"OCR MCP server configured: {BUILTIN_EVIDENCE_SERVER} type=stdio args=1 env=0 tools=1")

    return 0


if __name__ == "__main__":
    raise SystemExit(configure_mcp_servers())
