"""Parent-owned federation thread with READY-before-OCR startup and bounded closure."""

from __future__ import annotations

import asyncio
import copy
import logging
import os
import re
import shutil
import sys
import tempfile
import threading
from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from .contracts import CALL_SECONDS, RUN_SECONDS, FederationError, Registry
from .gateway import Gateway


class RunningGateway:
    """Expose a secret-free OCR stanza and finalized accounting from one owned thread."""

    def __init__(
        self,
        registry: Registry,
        environment: Mapping[str, str],
        forbidden: tuple[str, ...],
        run_id: str,
        *,
        dlp_enabled: bool = True,
    ) -> None:
        self._dlp_enabled = dlp_enabled
        if not isinstance(run_id, str) or re.fullmatch(r"[a-f0-9]{32}", run_id) is None:
            raise FederationError("registry_invalid")
        names = {
            source
            for spec in registry.servers
            for _, source in (*spec.env_from, *spec.headers_from)
        } | {spec.token_from for spec in registry.servers if spec.token_from is not None}
        selected: dict[str, str] = {}
        for name in names:
            value = environment.get(name)
            if (
                not isinstance(value, str)
                or not value
                or len(value.encode("utf-8")) > 8192
                or any(char in value for char in "\r\n\0")
            ):
                raise FederationError("secret_missing")
            selected[name] = value
        if sum(len(v.encode("utf-8")) for v in selected.values()) > 64 * 1024:
            raise FederationError("secret_missing")
        self._secrets = tuple(sorted(set(selected.values())))
        self.aliases = tuple(tool.alias for spec in registry.servers for tool in spec.tools)
        # nosec B108 -- mkdtemp creates the random owner-only root; /tmp keeps the
        # Unix-socket path below the platform limit before the isolated relay starts.
        self._directory = tempfile.mkdtemp(prefix="ocr-fed-", dir="/tmp")  # nosec B108
        os.chmod(self._directory, 0o700)
        self._socket = str(Path(self._directory) / "gateway.sock")
        self.ocr_server = {
            "command": sys.executable,
            "args": ["-I", "-m", "ocr_toolkit.federation.relay", "--socket", self._socket],
            "tools": list(self.aliases),
        }
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._main_task: asyncio.Task[Any] | None = None
        self._stop: asyncio.Event | None = None
        self._error: str | None = None
        self._receipt: dict[str, Any] | None = None
        self._gateway: Gateway | None = None
        self._closed = False
        # Third-party diagnostics are not an authorized content publication channel.
        for namespace in ("mcp", "httpx2", "httpcore"):
            logger = logging.getLogger(namespace)
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
        self._thread = threading.Thread(
            target=self._run,
            args=(registry, selected, forbidden, run_id),
            name="ocr-federation",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(CALL_SECONDS + 5):
            self._request_stop(cancel=True)
            self._thread.join(20)
            if not self._thread.is_alive():
                shutil.rmtree(self._directory)
            raise FederationError("gateway_unavailable")
        if self._error is not None:
            self._thread.join(20)
            if not self._thread.is_alive():
                shutil.rmtree(self._directory)
            raise FederationError(self._error)

    @property
    def secret_values(self) -> tuple[str, ...]:
        """Return ephemeral operator values for the runner's source-class DLP registry."""
        return self._secrets

    @property
    def forbidden_publication(self) -> tuple[str, ...]:
        """Return bounded admitted external strings only; never include them in receipts."""
        return tuple(sorted(self._gateway.publication)) if self._gateway is not None else ()

    def _run(
        self,
        registry: Registry,
        selected: Mapping[str, str],
        forbidden: tuple[str, ...],
        run_id: str,
    ) -> None:
        """Keep every SDK context entered and exited on its owning event-loop task."""
        try:
            asyncio.run(self._serve(registry, selected, forbidden, run_id))
        except BaseException:
            if self._error is None:
                self._error = "cleanup_failed"
        finally:
            self._ready.set()

    async def _serve(
        self,
        registry: Registry,
        selected: Mapping[str, str],
        forbidden: tuple[str, ...],
        run_id: str,
    ) -> None:
        """Prepare once, serve one relay, then close sessions before making a receipt."""
        self._loop = asyncio.get_running_loop()
        self._main_task = asyncio.current_task()
        self._stop = asyncio.Event()
        gateway = Gateway(
            registry,
            selected,
            (*forbidden, *self._secrets),
            run_id,
            self._directory,
            dlp_enabled=self._dlp_enabled,
        )
        self._gateway = gateway
        stack = AsyncExitStack()
        listener: asyncio.Server | None = None
        try:
            await gateway.prepare(stack)
            listener = await asyncio.start_unix_server(
                gateway.connect, path=self._socket, limit=32 * 1024
            )
            os.chmod(self._socket, 0o600)
            self._ready.set()
            try:
                await asyncio.wait_for(self._stop.wait(), RUN_SECONDS)
            except TimeoutError:
                self._error = "timed_out"
        except FederationError as error:
            self._error = error.code
        except BaseException:
            self._error = "gateway_unavailable"
        finally:
            if listener is not None:
                listener.close()
                await listener.wait_closed()
            await gateway.stop()
            try:
                await stack.aclose()
            except BaseException:
                self._error = "cleanup_failed"
            if self._error is None:
                try:
                    self._receipt = gateway.receipt()
                except FederationError:
                    self._error = "cleanup_failed"
            self._ready.set()

    def _request_stop(self, *, cancel: bool = False) -> None:
        """Signal the owning task without transferring any SDK context across threads."""
        if self._loop is None or self._loop.is_closed():
            return
        try:
            if cancel and self._main_task is not None:
                self._loop.call_soon_threadsafe(self._main_task.cancel)
            elif self._stop is not None:
                self._loop.call_soon_threadsafe(self._stop.set)
        except RuntimeError:
            pass

    def close(self) -> dict[str, Any]:
        """Join owned work and return a defensive content-free receipt after cleanup."""
        if not self._closed:
            self._request_stop()
            self._thread.join(35)
            if self._thread.is_alive():
                self._request_stop(cancel=True)
                self._thread.join(5)
            if self._thread.is_alive():
                raise FederationError("cleanup_failed")
            self._closed = True
            shutil.rmtree(self._directory)
        if self._error is not None or self._receipt is None:
            raise FederationError("cleanup_failed")
        return copy.deepcopy(self._receipt)


def start_gateway(
    registry: Registry,
    *,
    environment: Mapping[str, str],
    forbidden: tuple[str, ...] = (),
    run_id: str,
    dlp_enabled: bool = True,
) -> RunningGateway:
    """Start and verify the frozen upstream inventory before returning the OCR stanza."""
    return RunningGateway(registry, environment, forbidden, run_id, dlp_enabled=dlp_enabled)
