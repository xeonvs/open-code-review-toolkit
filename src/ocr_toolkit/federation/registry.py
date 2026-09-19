"""Parse the bounded operator registry without resolving or storing credentials."""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from .contracts import REGISTRY_BYTES, FederationError, Registry, ServerSpec, ToolPolicy

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_ENV = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_HEADER = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,63}\Z")
_RESERVED_HEADERS = {
    "authorization",
    "host",
    "cookie",
    "connection",
    "content-length",
    "content-type",
    "accept",
    "accept-encoding",
    "transfer-encoding",
}
_RESERVED_SERVERS = frozenset({"ocr_toolkit_evidence", "ocr_toolkit_federation"})


def _object(value: object, fields: set[str], required: set[str]) -> dict[str, object]:
    """Require one closed JSON object with the specified mandatory fields."""
    if not isinstance(value, dict) or set(value) - fields or not required <= set(value):
        raise FederationError("registry_invalid")
    return value


def _name(value: object) -> str:
    """Reject ambiguous alias components before constructing exported names."""
    if not isinstance(value, str) or not _NAME.fullmatch(value) or "__" in value:
        raise FederationError("registry_invalid")
    return value


def origin(value: str, *, endpoint: bool = False) -> str:
    """Canonicalize an explicit HTTPS origin without userinfo or ambiguous hosts."""
    try:
        parsed = urlsplit(value)
        if (
            len(value) > 2048
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or "\\" in value
            or any(c.isspace() for c in value)
            or (not endpoint and (parsed.path not in {"", "/"} or parsed.query))
            or parsed.hostname.endswith(".")
            or "%" in parsed.netloc
        ):
            raise ValueError
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
        if ":" in host:
            host = f"[{host}]"
        return f"https://{host}" + (f":{port}" if port is not None and port != 443 else "")
    except (ValueError, UnicodeError):
        raise FederationError("registry_invalid") from None


def _pairs(value: object, *, headers: bool = False) -> tuple[tuple[str, str], ...]:
    """Validate finite environment projections and reject protocol-header overrides."""
    if not isinstance(value, dict) or len(value) > 32:
        raise FederationError("registry_invalid")
    seen: set[str] = set()
    for target, source in value.items():
        regex = _HEADER if headers else _ENV
        if (
            not isinstance(target, str)
            or not regex.fullmatch(target)
            or not isinstance(source, str)
            or not _ENV.fullmatch(source)
        ):
            raise FederationError("registry_invalid")
        key = target.lower() if headers else target
        if key in seen or (
            headers and (key in _RESERVED_HEADERS or key.startswith(("mcp-", "proxy-", "sec-")))
        ):
            raise FederationError("registry_invalid")
        seen.add(key)
    return tuple(sorted(value.items()))


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys instead of silently replacing authority."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise FederationError("registry_invalid")
        result[key] = value
    return result


def parse_registry(raw: str, profile: str = "local") -> Registry:
    """Parse only the closed v2 registry and the provider-permitted transports."""
    try:
        if (
            profile not in {"local", "gitlab_mr"}
            or not isinstance(raw, str)
            or len(raw.encode("utf-8")) > REGISTRY_BYTES
        ):
            raise FederationError("registry_invalid")
        data = _object(
            json.loads(raw, object_pairs_hook=_unique),
            {"version", "servers"},
            {"version", "servers"},
        )
        if (
            type(data["version"]) is not int
            or data["version"] != 2
            or not isinstance(data["servers"], dict)
            or len(data["servers"]) > 16
        ):
            raise FederationError("registry_invalid")
        servers: list[ServerSpec] = []
        aliases: set[str] = set()
        for name, value in data["servers"].items():
            _name(name)
            if name in _RESERVED_SERVERS:
                raise FederationError("registry_invalid")
            value = _object(
                value, {"transport", "auth", "headers_from", "tools"}, {"transport", "tools"}
            )
            transport = _object(
                value["transport"], {"type", "url", "command", "args", "env_from"}, {"type"}
            )
            kind = transport["type"]
            url = command = token_from = None
            args: tuple[str, ...] = ()
            env_from: tuple[tuple[str, str], ...] = ()
            headers_from: tuple[tuple[str, str], ...] = ()
            if kind == "https":
                _object(transport, {"type", "url"}, {"type", "url"})
                url = transport["url"]
                if not isinstance(url, str):
                    raise FederationError("registry_invalid")
                origin(url, endpoint=True)
                headers_from = _pairs(value.get("headers_from", {}), headers=True)
                if "auth" in value:
                    auth = _object(
                        value["auth"], {"scheme", "token_from"}, {"scheme", "token_from"}
                    )
                    token_from = auth["token_from"]
                    if (
                        auth["scheme"] != "Bearer"
                        or not isinstance(token_from, str)
                        or not _ENV.fullmatch(token_from)
                    ):
                        raise FederationError("registry_invalid")
            elif kind == "stdio" and profile == "local":
                _object(transport, {"type", "command", "args", "env_from"}, {"type", "command"})
                command = transport["command"]
                raw_args = transport.get("args", [])
                if (
                    not isinstance(command, str)
                    or not command.startswith("/")
                    or len(command) > 4096
                    or "\0" in command
                ):
                    raise FederationError("registry_invalid")
                if (
                    not isinstance(raw_args, list)
                    or len(raw_args) > 32
                    or any(not isinstance(a, str) or len(a) > 4096 or "\0" in a for a in raw_args)
                ):
                    raise FederationError("registry_invalid")
                args = tuple(raw_args)
                env_from = _pairs(transport.get("env_from", {}))
                if "auth" in value or "headers_from" in value:
                    raise FederationError("registry_invalid")
            else:
                raise FederationError("registry_invalid")
            selected = value["tools"]
            if not isinstance(selected, dict) or not selected:
                raise FederationError("registry_invalid")
            policies: list[ToolPolicy] = []
            for tool_name, policy in selected.items():
                _name(tool_name)
                policy = _object(policy, {"assurance", "resource_origins"}, set())
                assurance = policy.get("assurance", "advisory")
                origins = policy.get("resource_origins", [])
                if (
                    assurance not in {"advisory", "review_read"}
                    or not isinstance(origins, list)
                    or len(origins) > 16
                    or any(not isinstance(o, str) for o in origins)
                ):
                    raise FederationError("registry_invalid")
                alias = f"{name}__{tool_name}"
                if len(alias) > 64 or alias in aliases:
                    raise FederationError("registry_invalid")
                aliases.add(alias)
                allowed_origins = {origin(o) for o in origins}
                if url is not None:
                    allowed_origins.add(origin(url, endpoint=True))
                policies.append(
                    ToolPolicy(tool_name, alias, assurance, tuple(sorted(allowed_origins)))
                )
            servers.append(
                ServerSpec(
                    name,
                    kind,
                    tuple(policies),
                    url,
                    command,
                    args,
                    env_from,
                    token_from,
                    headers_from,
                )
            )
        if len(aliases) > 128:
            raise FederationError("registry_invalid")
        return Registry(tuple(servers))
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise FederationError("registry_invalid") from None
