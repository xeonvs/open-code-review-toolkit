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
from ocr_toolkit.config_writer import OCRConfigError, update_ocr_config

MAX_MCP_CONFIG_BYTES = 64_000
MAX_MCP_SERVERS = 16
MAX_MCP_ARGS = 64
MAX_MCP_ENV = 64
MAX_MCP_TOOLS = 128
MCP_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MCP_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class MCPConfigError(Exception):
    """The MCP CI configuration is invalid."""


@dataclass(frozen=True)
class MCPServerConfig:
    """Validated OCR MCP server configuration for one stdio bridge."""

    name: str
    command: str
    args: list[str]
    tools: list[str]
    setup: str
    env: list[str]
    secret_values: list[str]


def _string_list(value: Any, field: str, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        raise MCPConfigError(f"{field} must be a JSON array of strings")
    if len(value) > limit:
        raise MCPConfigError(f"{field} exceeds maximum item count {limit}")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise MCPConfigError(f"{field}[{index}] must be a string")
        result.append(item)
    return result


def _env_assignments(value: Any, env_from: Any, server_name: str) -> tuple[list[str], list[str]]:
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


def parse_mcp_servers(raw: str | None = None) -> list[MCPServerConfig]:
    """Return validated MCP server configs from OCR_MCP_SERVERS_JSON."""

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
        seen.add(name)

        command = server.get("command")
        if not isinstance(command, str) or not command.strip():
            raise MCPConfigError(f"servers.{name}.command must be a non-empty string")
        command = command.strip()

        args = _string_list(server.get("args", []), f"servers.{name}.args", limit=MAX_MCP_ARGS)
        tools = _string_list(server.get("tools", []), f"servers.{name}.tools", limit=MAX_MCP_TOOLS)
        setup = server.get("setup", "")
        if not isinstance(setup, str):
            raise MCPConfigError(f"servers.{name}.setup must be a string")

        env, secret_values = _env_assignments(server.get("env"), server.get("env_from"), name)
        servers.append(
            MCPServerConfig(
                name=name,
                command=command,
                args=args,
                tools=tools,
                setup=setup,
                env=env,
                secret_values=secret_values,
            )
        )

    return servers


def _redact_extra_values(text: str, values: list[str]) -> str:
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
    """Configure OCR MCP servers from CI and return a process exit code."""

    try:
        servers = parse_mcp_servers()
    except MCPConfigError as exc:
        print(f"Invalid OCR_MCP_SERVERS_JSON: {redact_sensitive(str(exc))}", file=sys.stderr)
        return 1

    if not servers:
        try:
            update_ocr_config({"mcp_servers": {}})
        except OCRConfigError as exc:
            print(
                f"Failed to clear OCR MCP servers: {redact_sensitive(str(exc))}",
                file=sys.stderr,
            )
            return 1
        print("OCR MCP servers: none configured")
        return 0

    mcp_servers: dict[str, Any] = {}
    secret_values: list[str] = []
    for server in servers:
        mcp_servers[server.name] = {
            "command": server.command,
            "args": server.args,
            "env": server.env,
            "tools": server.tools,
            "setup": server.setup,
        }
        secret_values.extend(server.secret_values)
        for assignment in server.env:
            _env_name, _sep, env_value = assignment.partition("=")
            if env_value:
                secret_values.append(env_value)

    try:
        update_ocr_config({"mcp_servers": mcp_servers})
    except OCRConfigError as exc:
        print(
            "Failed to configure OCR MCP servers: "
            f"{redact_sensitive(_redact_extra_values(str(exc), secret_values))}",
            file=sys.stderr,
        )
        return 1

    for server in servers:
        print(
            "OCR MCP server configured: "
            f"{server.name} command={server.command!r} "
            f"args={len(server.args)} env={len(server.env)} tools={len(server.tools)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(configure_mcp_servers())
