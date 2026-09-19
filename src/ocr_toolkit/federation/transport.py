"""Byte-bounded SDK transports and owned POSIX subprocess cleanup."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any

import anyio
import httpx2
import mcp_types as types
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.message import SessionMessage

from .contracts import (
    RESPONSE_BYTES,
    RUN_SECONDS,
    WIRE_BYTES,
    WIRE_REQUESTS,
    FederationError,
    ServerSpec,
)


@dataclass
class WireBudget:
    """Charge every raw ingress/egress chunk and HTTP request on one event loop."""

    started: float
    bytes: int = 0
    requests: int = 0
    notifications: int = 0
    cleanup_failed: bool = False

    def charge(self, count: int, *, request: bool = False) -> None:
        """Reject excess work before yielding bytes into an SDK parser."""
        self.bytes += count
        self.requests += int(request)
        if (
            time.monotonic() - self.started > RUN_SECONDS
            or self.bytes > WIRE_BYTES
            or self.requests > WIRE_REQUESTS
        ):
            raise FederationError("budget_exceeded")


def parse_frame(raw: bytes) -> SessionMessage:
    """Check frame depth before bounded JSON parsing, then use the official wire model."""
    if len(raw) > RESPONSE_BYTES:
        raise FederationError("oversized")
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (123, 91):
            depth += 1
            if depth > 24:
                raise FederationError("oversized")
        elif char in (125, 93):
            depth -= 1
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        return SessionMessage(types.jsonrpc_message_adapter.validate_python(value, by_name=False))
    except Exception:
        raise FederationError("protocol_invalid") from None


async def read_frames(reader: asyncio.StreamReader, sink: Any, budget: WireBudget) -> None:
    """Consume bytes with a finite line buffer and no parser call after overflow."""
    pending = bytearray()
    while chunk := await reader.read(16 * 1024):
        budget.charge(len(chunk))
        for piece in chunk.splitlines(keepends=True):
            # JSON-RPC stdio is LF delimited; CR without LF is ordinary input.
            if len(pending) + len(piece) > RESPONSE_BYTES:
                raise FederationError("oversized")
            pending.extend(piece)
            if pending.endswith(b"\n"):
                message = parse_frame(bytes(pending))
                budget.charge(0, request=isinstance(message.message, types.JSONRPCRequest))
                await sink.send(message)
                pending.clear()
    if pending:
        raise FederationError("protocol_invalid")
    await sink.aclose()


async def write_frames(source: Any, writer: asyncio.StreamWriter, budget: WireBudget) -> None:
    """Write one bounded serialized SDK message per line with backpressure."""
    async for message in source:
        data = (
            message.message.model_dump_json(by_alias=True, exclude_unset=True).encode("utf-8")
            + b"\n"
        )
        if len(data) > RESPONSE_BYTES:
            raise FederationError("oversized")
        budget.charge(len(data), request=isinstance(message.message, types.JSONRPCRequest))
        writer.write(data)
        await writer.drain()


@asynccontextmanager
async def framed_streams(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, budget: WireBudget
) -> AsyncIterator[tuple[Any, Any]]:
    """Bridge a raw connection into zero-capacity official SDK message streams."""
    incoming, read = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    write, outgoing = anyio.create_memory_object_stream[SessionMessage](0)
    async with anyio.create_task_group() as tasks:

        async def receive() -> None:
            try:
                await read_frames(reader, incoming, budget)
            except Exception:
                with suppress(anyio.ClosedResourceError, anyio.BrokenResourceError):
                    await incoming.send(FederationError("transport_failed"))
            finally:
                await incoming.aclose()

        async def transmit() -> None:
            try:
                await write_frames(outgoing, writer, budget)
            except Exception:
                await incoming.aclose()

        tasks.start_soon(receive)
        tasks.start_soon(transmit)
        try:
            yield read, write
        finally:
            tasks.cancel_scope.cancel()
    await read.aclose()
    await write.aclose()


def _group_exists(pid: int) -> bool:
    """Treat permission errors and surviving group members as cleanup uncertainty."""
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


async def stop_process(process: asyncio.subprocess.Process, budget: WireBudget) -> None:
    """Stop the owned group even when its leader exited, then verify disappearance."""
    if process.stdin is not None:
        process.stdin.close()
    for sig in (None, signal.SIGTERM, signal.SIGKILL):
        if sig is not None:
            with suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, sig)
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            if process.returncode is not None and not _group_exists(process.pid):
                return
            await asyncio.sleep(0.01)
    budget.cleanup_failed = True


@asynccontextmanager
async def stdio_transport(
    spec: ServerSpec, environment: Mapping[str, str], cwd: str, budget: WireBudget
) -> AsyncIterator[tuple[Any, Any]]:
    """Launch an exact argv/env in a private cwd and own its pipes and process group."""
    assert spec.command is not None
    process = await asyncio.create_subprocess_exec(
        spec.command,
        *spec.args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=dict(environment),
        cwd=cwd,
        start_new_session=True,
        limit=32 * 1024,
    )
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None

    async def discard_stderr() -> None:
        consumed = 0
        while chunk := await process.stderr.read(8192):
            consumed += len(chunk)
            if consumed > 32 * 1024:
                raise FederationError("oversized")

    try:
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(discard_stderr)
            try:
                async with framed_streams(process.stdout, process.stdin, budget) as streams:
                    yield streams
            finally:
                with anyio.CancelScope(shield=True):
                    await stop_process(process, budget)
                tasks.cancel_scope.cancel()
    finally:
        if process.returncode is None or _group_exists(process.pid):
            with anyio.CancelScope(shield=True):
                await stop_process(process, budget)


class BoundedBody(httpx2.AsyncByteStream):
    """Cap a raw HTTP body before HTTPX decoding, SSE framing, or SDK JSON parsing."""

    def __init__(
        self, inner: httpx2.AsyncByteStream, budget: WireBudget, *, cleanup: bool = False
    ) -> None:
        self.inner = inner
        self.budget = budget
        self.cleanup = cleanup

    async def __aiter__(self) -> AsyncIterator[bytes]:
        total = 0
        try:
            async for chunk in self.inner:
                total += len(chunk)
                self.budget.charge(len(chunk))
                if total > RESPONSE_BYTES:
                    raise FederationError("oversized")
                yield chunk
        except BaseException:
            if self.cleanup:
                self.budget.cleanup_failed = True
            raise

    async def aclose(self) -> None:
        """Release the underlying connection on success, rejection, or cancellation."""
        try:
            await self.inner.aclose()
        except BaseException:
            if self.cleanup:
                self.budget.cleanup_failed = True
            raise


class BoundedHTTP(httpx2.AsyncBaseTransport):
    """Enforce an exact endpoint and bounded noncompressed bodies on every SDK request."""

    def __init__(self, endpoint: str, budget: WireBudget) -> None:
        self.endpoint = httpx2.URL(endpoint)
        self.budget = budget
        self.inner = httpx2.AsyncHTTPTransport(
            trust_env=False,
            retries=0,
            limits=httpx2.Limits(max_connections=4, max_keepalive_connections=4),
        )

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Reject redirects, cookies, compression and endpoint changes before adoption."""
        cleanup = request.method == "DELETE"
        response: httpx2.Response | None = None
        try:
            if request.url != self.endpoint or request.method not in {"GET", "POST", "DELETE"}:
                raise FederationError("transport_failed")
            # The SDK may retain cookies; they never become authority for a later request.
            request.headers.pop("cookie", None)
            request.headers["accept-encoding"] = "identity"
            self.budget.charge(len(request.content), request=True)
            response = await self.inner.handle_async_request(request)
            if (
                300 <= response.status_code < 400
                or response.headers.get("content-encoding", "identity").lower() != "identity"
            ):
                raise FederationError("transport_failed")
            if sum(len(k) + len(v) for k, v in response.headers.raw) > 16 * 1024:
                raise FederationError("oversized")
            response.headers.pop("set-cookie", None)
            content_length = response.headers.get("content-length")
            if content_length is not None and (
                not content_length.isdecimal() or int(content_length) > RESPONSE_BYTES
            ):
                raise FederationError("oversized")
            if cleanup and response.status_code not in {200, 204, 405}:
                self.budget.cleanup_failed = True
            assert isinstance(response.stream, httpx2.AsyncByteStream)
            response.stream = BoundedBody(response.stream, self.budget, cleanup=cleanup)
            return response
        except BaseException:
            if cleanup:
                self.budget.cleanup_failed = True
            if response is not None:
                await response.aclose()
            raise FederationError("transport_failed") from None

    async def aclose(self) -> None:
        """Close the finite HTTP connection pool."""
        await self.inner.aclose()


@asynccontextmanager
async def https_transport(
    spec: ServerSpec, headers: Mapping[str, str], budget: WireBudget
) -> AsyncIterator[tuple[Any, Any]]:
    """Use the SDK Streamable HTTP transport behind the public byte-stream guard."""
    assert spec.url is not None
    async with httpx2.AsyncClient(
        transport=BoundedHTTP(spec.url, budget),
        headers=dict(headers),
        trust_env=False,
        follow_redirects=False,
        max_redirects=0,
        timeout=httpx2.Timeout(30.0, connect=5.0, pool=5.0),
    ) as client:
        async with streamable_http_client(spec.url, http_client=client) as streams:
            yield streams


class FilteredRead:
    """Drop bounded unsolicited notifications and reject server-initiated authority."""

    def __init__(self, inner: Any, budget: WireBudget) -> None:
        self.inner = inner
        self.budget = budget

    async def receive(self) -> SessionMessage | Exception:
        """Read one response, charging ignored traffic before SDK dispatch."""
        while True:
            message = await self.inner.receive()
            if isinstance(message, Exception):
                return FederationError("transport_failed")
            if isinstance(message.message, types.JSONRPCNotification | types.JSONRPCRequest):
                self.budget.notifications += 1
                if self.budget.notifications > 128 or isinstance(
                    message.message, types.JSONRPCRequest
                ):
                    return FederationError("protocol_invalid")
                continue
            return message

    async def __aenter__(self) -> FilteredRead:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.aclose()

    def __aiter__(self) -> FilteredRead:
        return self

    async def __anext__(self) -> SessionMessage | Exception:
        try:
            return await self.receive()
        except anyio.EndOfStream:
            raise StopAsyncIteration from None

    async def aclose(self) -> None:
        """Close the source stream when the SDK session exits."""
        await self.inner.aclose()


@asynccontextmanager
async def filtered_transport(transport: Any, budget: WireBudget) -> AsyncIterator[tuple[Any, Any]]:
    """Apply bounded unsolicited-message filtering to either supported transport."""
    async with transport as (read, write):
        yield FilteredRead(read, budget), write
