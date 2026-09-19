"""Frozen tool discovery, per-attempt admission, and run-owned dispatch/cache."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass
from typing import Any

import mcp_types as types
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.server.lowlevel import Server

from ocr_toolkit.context.dlp import ForbiddenMatcher

from . import admission
from .contracts import (
    CACHE_BYTES,
    CACHE_ENTRIES,
    CALL_SECONDS,
    CONCURRENCY,
    COUNTERS,
    DELIVERY_BYTES,
    MAX_CALLS,
    METADATA_BYTES,
    FederationError,
    Registry,
    ServerSpec,
    ToolPolicy,
)
from .transport import (
    WireBudget,
    filtered_transport,
    framed_streams,
    https_transport,
    stdio_transport,
)


@dataclass(frozen=True)
class ExportedTool:
    """Freeze an operator policy, sanitized declaration, validator and live SDK session."""

    server: ServerSpec
    policy: ToolPolicy
    definition: types.Tool
    validator: Draft202012Validator
    output_validator: Draft202012Validator | None
    client: Client


class Gateway:
    """Own one immutable inventory and the bounded lifetime of model-selected calls."""

    def __init__(
        self,
        registry: Registry,
        environment: Mapping[str, str],
        forbidden: tuple[str, ...],
        run_id: str,
        directory: str,
        *,
        dlp_enabled: bool = True,
    ) -> None:
        self.registry = registry
        self.environment = environment
        self.run_id = run_id
        self.directory = directory
        self.dlp_enabled = dlp_enabled
        self.budget = WireBudget(time.monotonic())
        self.matcher = ForbiddenMatcher.compile(forbidden)
        self.tools: dict[str, ExportedTool] = {}
        self.counts: dict[str, dict[str, Any]] = {
            tool.alias: {
                "server": spec.name,
                "assurance": tool.assurance,
                **dict.fromkeys(COUNTERS, 0),
            }
            for spec in registry.servers
            for tool in spec.tools
        }
        self.total_calls = 0
        self.delivered_bytes = 0
        self.publication: set[str] = set()
        self.dispatches: dict[bytes, asyncio.Task[types.CallToolResult]] = {}
        self.cache: OrderedDict[bytes, tuple[types.CallToolResult, int]] = OrderedDict()
        self.cache_bytes = 0
        self.semaphore = asyncio.Semaphore(CONCURRENCY)
        self.connections: set[asyncio.Task[Any]] = set()
        self.connected = False
        self.closing = False
        self.server = Server(
            "ocr-federation", on_list_tools=self.list_tools, on_call_tool=self.call_tool
        )

    async def prepare(self, stack: AsyncExitStack) -> None:
        """Establish selected peers and reject incomplete discovery before OCR starts."""
        metadata_bytes = 0
        for spec in self.registry.servers:
            if spec.transport == "stdio":
                env = {target: self.environment[source] for target, source in spec.env_from}
                transport = stdio_transport(spec, env, self.directory, self.budget)
            else:
                headers = {target: self.environment[source] for target, source in spec.headers_from}
                if spec.token_from is not None:
                    headers["Authorization"] = "Bearer " + self.environment[spec.token_from]
                transport = https_transport(spec, headers, self.budget)
            client = await stack.enter_async_context(
                Client(
                    filtered_transport(transport, self.budget),
                    cache=None,
                    mode="auto",
                    read_timeout_seconds=CALL_SECONDS,
                )
            )
            found: dict[str, types.Tool] = {}
            cursor: str | None = None
            cursors: set[str] = set()
            for _page in range(16):
                listing = await client.session.send_request(
                    types.ListToolsRequest(params=types.PaginatedRequestParams(cursor=cursor)),
                    types.ListToolsResult,
                    request_read_timeout_seconds=CALL_SECONDS,
                )
                for tool in listing.tools:
                    if tool.name in found or len(found) >= 128:
                        raise FederationError("inventory_invalid")
                    found[tool.name] = tool
                cursor = listing.next_cursor
                if cursor is None:
                    break
                if len(cursor) > 1024 or cursor in cursors:
                    raise FederationError("inventory_invalid")
                cursors.add(cursor)
            else:
                raise FederationError("inventory_invalid")
            for policy in spec.tools:
                tool = found.get(policy.name)
                if tool is None:
                    raise FederationError("inventory_invalid")
                validator = admission.compile_schema(
                    tool.input_schema, self.matcher, dlp_enabled=self.dlp_enabled
                )
                output_validator = (
                    admission.compile_schema(
                        tool.output_schema, self.matcher, dlp_enabled=self.dlp_enabled
                    )
                    if tool.output_schema is not None
                    else None
                )
                description = tool.description or ""
                admission.check_dlp(description, self.matcher, dlp_enabled=self.dlp_enabled)
                definition = types.Tool(
                    name=policy.alias, description=description, input_schema=tool.input_schema
                )
                metadata_bytes += len(definition.model_dump_json(by_alias=True).encode("utf-8"))
                if metadata_bytes > METADATA_BYTES:
                    raise FederationError("oversized")
                self.tools[policy.alias] = ExportedTool(
                    spec, policy, definition, validator, output_validator, client
                )

    async def list_tools(
        self, _context: Any, params: types.PaginatedRequestParams
    ) -> types.ListToolsResult:
        """Serve only the startup-frozen selected inventory, with no dynamic authority."""
        if params.cursor is not None or self.closing:
            raise FederationError("protocol_invalid")
        return types.ListToolsResult(tools=[tool.definition for tool in self.tools.values()])

    async def _dispatch(
        self, key: bytes, tool: ExportedTool, arguments: dict[str, Any]
    ) -> types.CallToolResult:
        """Make exactly one upstream request and cache only completely admitted success."""
        try:
            async with asyncio.timeout(CALL_SECONDS):
                async with self.semaphore:
                    value = await tool.client.session.send_request(
                        types.CallToolRequest(
                            params=types.CallToolRequestParams(
                                name=tool.policy.name, arguments=arguments
                            )
                        ),
                        types.CallToolResult,
                        request_read_timeout_seconds=CALL_SECONDS,
                    )
                    admitted = admission.result(
                        value, tool.output_validator, self.matcher, dlp_enabled=self.dlp_enabled
                    )
            size = len(admitted.model_dump_json(by_alias=True).encode("utf-8")) + len(key)
            if size <= CACHE_BYTES and not self.closing:
                while self.cache and (
                    len(self.cache) >= CACHE_ENTRIES or self.cache_bytes + size > CACHE_BYTES
                ):
                    _, (_, removed) = self.cache.popitem(last=False)
                    self.cache_bytes -= removed
                self.cache[key] = (admitted, size)
                self.cache_bytes += size
            return admitted
        except TimeoutError:
            raise FederationError("timed_out") from None
        except FederationError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            raise FederationError("tool_failed") from None
        finally:
            self.dispatches.pop(key, None)

    def _terminal(self, alias: str, reason: str) -> None:
        """Record one outcome and optional diagnostic subset without retaining content."""
        counts = self.counts[alias]
        if reason in {
            "arguments_invalid",
            "origin_denied",
            "budget_exceeded",
            "dlp_rejected",
            "oversized",
        }:
            outcome = "denied"
        elif reason == "timed_out":
            outcome = "timed_out"
        else:
            outcome = "failed"
        counts[outcome] += 1
        if reason in {"dlp_rejected", "oversized"}:
            counts[reason] += 1

    async def call_tool(
        self, _context: Any, params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        """Account for each caller independently, including cache hits and cancelled waiters."""
        tool = self.tools.get(params.name)
        if tool is None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="federation_denied")], is_error=True
            )
        if self.total_calls >= MAX_CALLS:
            # An over-budget request cannot fit the closed bounded receipt. Stop admission
            # and refuse finalization rather than hiding an unaccounted model attempt.
            self.closing = True
            self.budget.cleanup_failed = True
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="federation_unavailable")],
                is_error=True,
            )
        counts = self.counts[params.name]
        counts["attempted"] += 1
        self.total_calls += 1
        try:
            self.budget.charge(0)
            if self.closing:
                raise FederationError("budget_exceeded")
            values, canonical = admission.arguments(
                params.arguments or {},
                tool.policy,
                tool.validator,
                self.matcher,
                dlp_enabled=self.dlp_enabled,
            )
            key = params.name.encode("ascii") + b"\0" + canonical
            if cached := self.cache.get(key):
                result = cached[0]
                self.cache.move_to_end(key)
                counts["cache_hits"] += 1
            else:
                dispatch = self.dispatches.get(key)
                if dispatch is None:
                    dispatch = asyncio.create_task(self._dispatch(key, tool, values))
                    # Retrieve orphan exceptions when every caller was cancelled.
                    dispatch.add_done_callback(
                        lambda task: None if task.cancelled() else task.exception()
                    )
                    self.dispatches[key] = dispatch
                else:
                    counts["single_flight"] += 1
                result = await asyncio.shield(dispatch)
            size = len(result.model_dump_json(by_alias=True).encode("utf-8"))
            if self.delivered_bytes + size > DELIVERY_BYTES:
                raise FederationError("budget_exceeded")
            self.delivered_bytes += size
            self.publication.update(
                admission.string_values(
                    [*[block.text for block in result.content], result.structured_content]
                )
            )
            counts["completed"] += 1
            return result
        except asyncio.CancelledError:
            self._terminal(params.name, "tool_failed")
            raise
        except FederationError as error:
            self._terminal(params.name, error.code)
        except Exception:
            self._terminal(params.name, "tool_failed")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="federation_unavailable")], is_error=True
        )

    async def connect(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Accept one OCR relay in the private run directory and bound its lifecycle."""
        task = asyncio.current_task()
        assert task is not None
        if self.connected or self.closing:
            writer.close()
            return
        self.connected = True
        self.connections.add(task)
        try:
            async with framed_streams(reader, writer, self.budget) as (read, write):
                await self.server.run(read, write, self.server.create_initialization_options())
        except asyncio.CancelledError:
            raise
        except Exception:
            self.budget.cleanup_failed = True
        finally:
            self.connections.discard(task)
            writer.close()
            with suppress(OSError, ConnectionError):
                await writer.wait_closed()

    async def stop(self) -> None:
        """Settle all owned work before upstream teardown and receipt finalization."""
        self.closing = True
        pending = tuple(self.connections) + tuple(self.dispatches.values())
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self.cache.clear()
        self.cache_bytes = 0

    def receipt(self) -> dict[str, Any]:
        """Return only finalized, reconciliable accounting after verified cleanup."""
        if self.budget.cleanup_failed:
            raise FederationError("cleanup_failed")
        for counts in self.counts.values():
            if counts["attempted"] != sum(
                counts[key] for key in ("completed", "denied", "failed", "timed_out")
            ):
                raise FederationError("cleanup_failed")
        return {
            "schema": "ocr.federation/v1",
            "run_id": self.run_id,
            "state": "finalized",
            "cleanup": "clean",
            "tools": self.counts,
        }
