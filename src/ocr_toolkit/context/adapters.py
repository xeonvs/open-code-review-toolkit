"""Fixed stdio and HTTPS transports for operator-managed context adapters."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.context.contracts import (
    REFERENCE_RESOURCE_CLASSES,
    REQUEST_SCHEMA,
    RESPONSE_SCHEMA,
)

MAX_ADAPTER_CONFIG_BYTES = 64 * 1024
MAX_ADAPTERS = 16
MAX_ARGS = 32
MAX_ENV_NAMES = 32
MAX_REQUEST_BYTES = 32 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MAX_STDERR_BYTES = 32 * 1024
NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
ENV_RE = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")
HEADER_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,63}\Z")
IDENTITY_RE = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")


class ContextAdapterError(ValueError):
    """An adapter configuration, transport, or fixed response failed closed."""


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    """Hold one closed operator-configured adapter allowlist entry."""

    name: str
    type: str
    tenants: tuple[str, ...]
    resource_classes: tuple[str, ...]
    command: str | None = None
    args: tuple[str, ...] = ()
    env_from: tuple[str, ...] = ()
    url: str | None = None
    headers_from: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    """Represent the sole fixed authorize-and-resolve operation."""

    request_id: str
    run_id: str
    adapter: str
    tenant: str
    resource_class: str
    candidate: str
    requested_fields: tuple[str, ...]
    max_chars: int
    max_bytes: int
    max_lines: int
    max_age_seconds: int
    deadline_ms: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": REQUEST_SCHEMA,
            "operation": "authorize_and_resolve",
            "request_id": self.request_id,
            "run_id": self.run_id,
            "adapter": self.adapter,
            "tenant": self.tenant,
            "resource_class": self.resource_class,
            "candidate": self.candidate,
            "requested_fields": list(self.requested_fields),
            "limits": {
                "max_chars": self.max_chars,
                "max_bytes": self.max_bytes,
                "max_lines": self.max_lines,
                "max_age_seconds": self.max_age_seconds,
                "deadline_ms": self.deadline_ms,
            },
        }


@dataclass(frozen=True, slots=True)
class AdapterResponse:
    """Collapse every non-admitted object into one unavailable response."""

    status: str
    canonical_object: str | None = None
    version: str | None = None
    expiry: int | None = None
    record: Mapping[str, object] | None = None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def configured_secret_values(
    configs: tuple[AdapterConfig, ...], environment: Mapping[str, str]
) -> tuple[str, ...]:
    """Return exact operator-projected values for admission and publication DLP."""

    names = {
        name
        for config in configs
        for name in (
            *config.env_from,
            *(environment_name for _header, environment_name in config.headers_from),
        )
    }
    return tuple(sorted({environment[name] for name in names if environment.get(name)}))


def _set_response_timeout(response: Any, timeout: float) -> None:
    """Best-effort apply the remaining aggregate deadline to the next socket read."""

    try:
        socket = response.fp.raw._sock
    except AttributeError:
        return
    socket.settimeout(timeout)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextAdapterError("adapter JSON contains a duplicate key")
        result[key] = value
    return result


def _object(value: object, keys: frozenset[str], label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContextAdapterError(f"{label} must be an object")
    if set(value).difference(keys):
        raise ContextAdapterError(f"{label} contains unknown fields")
    return value


def _names(value: object, *, label: str, allowed: frozenset[str] | None = None) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 32
        or any(
            not isinstance(item, str)
            or (allowed is None and NAME_RE.fullmatch(item) is None)
            or (allowed is not None and item not in allowed)
            for item in value
        )
    ):
        raise ContextAdapterError(f"{label} is invalid")
    if value != sorted(set(value)):
        raise ContextAdapterError(f"{label} is invalid")
    return tuple(value)


def parse_adapter_config(raw: str | None) -> tuple[AdapterConfig, ...]:
    """Parse the exact environment-only adapter array without echoing secrets."""

    if raw is None or not raw.strip():
        return ()
    encoded = raw.encode("utf-8")
    if len(encoded) > MAX_ADAPTER_CONFIG_BYTES:
        raise ContextAdapterError("adapter configuration exceeds its byte limit")
    try:
        payload = json.loads(raw, object_pairs_hook=_pairs)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ContextAdapterError("adapter configuration is not valid bounded JSON") from exc
    if not isinstance(payload, list) or len(payload) > MAX_ADAPTERS:
        raise ContextAdapterError("adapter configuration must be a bounded array")
    configs: list[AdapterConfig] = []
    for value in payload:
        common = frozenset({"name", "type", "tenants", "resource_classes"})
        item = _object(
            value,
            common | frozenset({"command", "args", "env_from", "url", "headers_from"}),
            "adapter",
        )
        name, kind = item.get("name"), item.get("type")
        if not isinstance(name, str) or NAME_RE.fullmatch(name) is None:
            raise ContextAdapterError("adapter name is invalid")
        tenants = _names(item.get("tenants"), label="adapter tenants")
        resource_classes = _names(
            item.get("resource_classes"),
            label="adapter resource classes",
            allowed=REFERENCE_RESOURCE_CLASSES,
        )
        if kind == "stdio":
            if set(item).difference(common | {"command", "args", "env_from"}):
                raise ContextAdapterError("stdio adapter contains remote fields")
            command, args, env_from = item.get("command"), item.get("args"), item.get("env_from")
            if (
                not isinstance(command, str)
                or not Path(command).is_absolute()
                or not isinstance(args, list)
                or len(args) > MAX_ARGS
                or any(
                    not isinstance(arg, str)
                    or len(arg) > 1024
                    or "\x00" in arg
                    or redact_sensitive(arg) != arg
                    for arg in args
                )
                or not isinstance(env_from, list)
                or len(env_from) > MAX_ENV_NAMES
                or any(
                    not isinstance(name, str) or ENV_RE.fullmatch(name) is None for name in env_from
                )
            ):
                raise ContextAdapterError("stdio adapter configuration is invalid")
            if env_from != sorted(set(env_from)):
                raise ContextAdapterError("stdio adapter configuration is invalid")
            configs.append(
                AdapterConfig(
                    name=name,
                    type=kind,
                    tenants=tenants,
                    resource_classes=resource_classes,
                    command=command,
                    args=tuple(args),
                    env_from=tuple(env_from),
                )
            )
            continue
        if kind == "remote":
            if set(item).difference(common | {"url", "headers_from"}):
                raise ContextAdapterError("remote adapter contains stdio fields")
            url, headers = item.get("url"), item.get("headers_from")
            if not isinstance(url, str) or not isinstance(headers, Mapping):
                raise ContextAdapterError("remote adapter configuration is invalid")
            try:
                parsed = urllib.parse.urlsplit(url)
                port = parsed.port
            except ValueError as exc:
                raise ContextAdapterError("remote adapter URL is invalid") from exc
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or (port is None and parsed.netloc.endswith(":"))
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
                or not parsed.path.startswith("/")
                or redact_sensitive(url) != url
            ):
                raise ContextAdapterError("remote adapter URL must be absolute HTTPS")
            header_pairs: list[tuple[str, str]] = []
            for header, environment_name in headers.items():
                if (
                    not isinstance(header, str)
                    or HEADER_RE.fullmatch(header) is None
                    or header.lower() in {"host", "content-length", "transfer-encoding"}
                    or not isinstance(environment_name, str)
                    or ENV_RE.fullmatch(environment_name) is None
                ):
                    raise ContextAdapterError("remote adapter header mapping is invalid")
                header_pairs.append((header, environment_name))
            lower_headers = [header.lower() for header, _name in header_pairs]
            if (
                header_pairs != sorted(header_pairs)
                or len(header_pairs) > MAX_ENV_NAMES
                or len(lower_headers) != len(set(lower_headers))
                or set(lower_headers).intersection({"accept", "content-type", "user-agent"})
            ):
                raise ContextAdapterError("remote adapter headers must be sorted and bounded")
            configs.append(
                AdapterConfig(
                    name=name,
                    type=kind,
                    tenants=tenants,
                    resource_classes=resource_classes,
                    url=url,
                    headers_from=tuple(header_pairs),
                )
            )
            continue
        raise ContextAdapterError("adapter type is unsupported")
    names = [config.name for config in configs]
    if len(names) != len(set(names)):
        raise ContextAdapterError("adapter names collide")
    return tuple(configs)


def _request_bytes(request: AdapterRequest) -> bytes:
    payload = (json.dumps(request.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(payload) > MAX_REQUEST_BYTES:
        raise ContextAdapterError("adapter request exceeds its byte limit")
    return payload


def _parse_response(raw: bytes, request: AdapterRequest) -> AdapterResponse:
    if not raw or len(raw) > MAX_RESPONSE_BYTES or raw.count(b"\n") > 1:
        raise ContextAdapterError("adapter response frame is invalid")
    try:
        payload = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContextAdapterError("adapter response is not valid bounded JSON") from exc
    item = _object(
        payload,
        frozenset(
            {
                "schema_version",
                "request_id",
                "run_id",
                "status",
                "reason",
                "canonical_object",
                "version",
                "expiry",
                "record",
            }
        ),
        "adapter response",
    )
    if (
        item.get("schema_version") != RESPONSE_SCHEMA
        or item.get("request_id") != request.request_id
        or item.get("run_id") != request.run_id
    ):
        raise ContextAdapterError("adapter response identity does not match")
    if item.get("status") == "unavailable":
        if set(item) != {"schema_version", "request_id", "run_id", "status", "reason"}:
            raise ContextAdapterError("unavailable adapter response fields are invalid")
        if item.get("reason") != "unavailable":
            raise ContextAdapterError("adapter unavailable reason is invalid")
        return AdapterResponse(status="unavailable")
    if item.get("status") != "admitted" or set(item) != {
        "schema_version",
        "request_id",
        "run_id",
        "status",
        "canonical_object",
        "version",
        "expiry",
        "record",
    }:
        raise ContextAdapterError("adapter admitted response fields are invalid")
    canonical, version, expiry, record = (
        item.get("canonical_object"),
        item.get("version"),
        item.get("expiry"),
        item.get("record"),
    )
    if (
        not isinstance(canonical, str)
        or not canonical
        or len(canonical) > 512
        or not isinstance(version, str)
        or not version
        or len(version) > 256
        or not isinstance(expiry, int)
        or isinstance(expiry, bool)
        or expiry < 0
        or not isinstance(record, Mapping)
        or any(not isinstance(key, str) for key in record)
        or set(record) != set(request.requested_fields)
    ):
        raise ContextAdapterError("adapter admitted response is invalid")
    if "version" in record and record["version"] != version:
        raise ContextAdapterError("adapter response version changed")
    if "expiry" in record and record["expiry"] != expiry:
        raise ContextAdapterError("adapter response expiry changed")
    return AdapterResponse(
        status="admitted",
        canonical_object=canonical,
        version=version,
        expiry=expiry,
        record=dict(record),
    )


def _stdio(config: AdapterConfig, request: AdapterRequest, environment: Mapping[str, str]) -> bytes:
    command = config.command
    if command is None:
        raise ContextAdapterError("stdio adapter command is unavailable")
    child_environment = {"PATH": "", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    for name in config.env_from:
        value = environment.get(name)
        if value is None or "\x00" in value:
            raise ContextAdapterError("stdio adapter environment is unavailable")
        child_environment[name] = value
    timeout = min(request.deadline_ms / 1000, 120.0)

    def terminate(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            return
        process.wait(timeout=5)

    with tempfile.TemporaryDirectory(prefix="ocr-context-adapter-") as directory:
        os.chmod(directory, 0o700)
        child_environment["HOME"] = directory
        child_environment["TMPDIR"] = directory
        process: subprocess.Popen[bytes] | None = None
        workers: tuple[threading.Thread, ...] = ()
        try:
            process = subprocess.Popen(
                [command, *config.args],
                cwd=directory,
                env=child_environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            stdin, stdout_pipe, stderr_pipe = process.stdin, process.stdout, process.stderr
            if stdin is None or stdout_pipe is None or stderr_pipe is None:
                terminate(process)
                raise ContextAdapterError("stdio adapter pipes are unavailable")
            stdout_chunks: list[bytes] = []
            stderr_chunks: list[bytes] = []
            stdout_overflow = threading.Event()
            stderr_overflow = threading.Event()
            writer_failed = threading.Event()

            def read_pipe(
                stream: Any,
                chunks: list[bytes],
                limit: int,
                overflow: threading.Event,
            ) -> None:
                size = 0
                while True:
                    chunk = stream.read(65_536)
                    if not chunk:
                        return
                    remaining = limit + 1 - size
                    if remaining > 0:
                        chunks.append(chunk[:remaining])
                        size += min(len(chunk), remaining)
                    if size > limit or len(chunk) > remaining:
                        overflow.set()
                        return

            def write_request(stream: Any, payload: bytes) -> None:
                try:
                    stream.write(payload)
                    stream.close()
                except (BrokenPipeError, OSError):
                    writer_failed.set()

            workers = (
                threading.Thread(
                    target=read_pipe,
                    args=(stdout_pipe, stdout_chunks, MAX_RESPONSE_BYTES, stdout_overflow),
                    daemon=True,
                ),
                threading.Thread(
                    target=read_pipe,
                    args=(stderr_pipe, stderr_chunks, MAX_STDERR_BYTES, stderr_overflow),
                    daemon=True,
                ),
                threading.Thread(
                    target=write_request,
                    args=(stdin, _request_bytes(request)),
                    daemon=True,
                ),
            )
            deadline = time.monotonic() + timeout
            for worker in workers:
                worker.start()
            timed_out = False
            while process.poll() is None:
                if stdout_overflow.is_set() or stderr_overflow.is_set() or writer_failed.is_set():
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    process.wait(timeout=min(0.05, remaining))
                except subprocess.TimeoutExpired:
                    continue
            if process.poll() is None:
                terminate(process)
            for worker in workers:
                worker.join(timeout=5)
            if any(worker.is_alive() for worker in workers):
                raise ContextAdapterError("stdio adapter pipes did not close")
            stdout = b"".join(stdout_chunks)
            if timed_out:
                raise ContextAdapterError("stdio adapter timed out")
            if stdout_overflow.is_set():
                raise ContextAdapterError("stdio adapter response exceeds its byte limit")
            if stderr_overflow.is_set():
                raise ContextAdapterError("stdio adapter diagnostics exceeded their bound")
            if writer_failed.is_set():
                raise ContextAdapterError("stdio adapter request delivery failed")
        except ContextAdapterError:
            raise
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired) as exc:
            if process is not None and process.poll() is None:
                terminate(process)
            raise ContextAdapterError("stdio adapter failed") from exc
        except BaseException:
            if process is not None and process.poll() is None:
                terminate(process)
            for worker in workers:
                worker.join(timeout=5)
            raise
    assert process is not None
    if process.returncode != 0:
        raise ContextAdapterError("stdio adapter failed")
    return stdout


def _remote(
    config: AdapterConfig, request: AdapterRequest, environment: Mapping[str, str]
) -> bytes:
    url = config.url
    if url is None:
        raise ContextAdapterError("remote adapter URL is unavailable")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "open-code-review-toolkit-context/1",
    }
    for header, environment_name in config.headers_from:
        value = environment.get(environment_name)
        if value is None or "\r" in value or "\n" in value or len(value) > 16_384:
            raise ContextAdapterError("remote adapter credential is unavailable")
        headers[header] = value
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler)
    body = _request_bytes(request).rstrip(b"\n")
    http_request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    timeout = min(request.deadline_ms / 1000, 120.0)
    deadline = time.monotonic() + timeout
    try:
        with opener.open(http_request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                raise ContextAdapterError("remote adapter content type is invalid")
            chunks: list[bytes] = []
            size = 0
            while size < MAX_RESPONSE_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                _set_response_timeout(response, remaining)
                chunk = response.read(min(65_536, MAX_RESPONSE_BYTES - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size == MAX_RESPONSE_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                _set_response_timeout(response, remaining)
                if response.read(1):
                    raise ContextAdapterError("remote adapter response exceeds its byte limit")
    except urllib.error.HTTPError as exc:
        raise ContextAdapterError("remote adapter returned an unavailable status") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ContextAdapterError("remote adapter request failed") from exc
    return b"".join(chunks)


def authorize_and_resolve(
    config: AdapterConfig,
    request: AdapterRequest,
    *,
    environment: Mapping[str, str],
) -> AdapterResponse:
    """Invoke the sole protocol operation through the selected closed transport."""

    if (
        IDENTITY_RE.fullmatch(request.request_id) is None
        or IDENTITY_RE.fullmatch(request.run_id) is None
        or request.adapter != config.name
        or request.tenant not in config.tenants
        or request.resource_class not in config.resource_classes
        or request.resource_class not in REFERENCE_RESOURCE_CLASSES
        or request.requested_fields != tuple(sorted(set(request.requested_fields)))
        or not 1 <= request.max_chars <= 100_000
        or not 1 <= request.max_bytes <= 400_000
        or not 1 <= request.max_lines <= 10_000
        or not 0 <= request.max_age_seconds <= 31_536_000
        or not 100 <= request.deadline_ms <= 120_000
    ):
        raise ContextAdapterError("adapter request is not authorized by operator configuration")
    raw = (
        _stdio(config, request, environment)
        if config.type == "stdio"
        else _remote(config, request, environment)
    )
    return _parse_response(raw.rstrip(b"\n"), request)
