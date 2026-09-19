"""Actual local TLS and HTTP byte boundaries, including SDK Streamable HTTP framing."""

from __future__ import annotations

import asyncio
import json
import os
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx2
import pytest

from ocr_toolkit.federation import FederationError, parse_registry, start_gateway
from ocr_toolkit.federation.contracts import WIRE_REQUESTS
from tests.federation.test_gateway import relay_client


@contextmanager
def tls_peer(
    directory: Path, mode: str = "json", *, trust_certificate: bool = True
) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Provide a controlled TLS peer beyond the actual HTTP adapter and SDK transport."""
    directory.mkdir()
    cert, key = directory / "cert.pem", directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    observed: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args: Any) -> None:
            pass

        def do_POST(self) -> None:
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed.append(
                {
                    "path": self.path,
                    "method": request["method"],
                    "auth": self.headers.get("authorization"),
                    "cookie": self.headers.get("cookie"),
                }
            )
            legacy = mode in {"legacy", "delete_failure"}
            if "id" not in request:
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if request["method"] == "server/discover":
                result = {"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}}
            elif request["method"] == "initialize":
                result = {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "synthetic", "version": "1"},
                }
            elif request["method"] == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Return controlled text.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                                "required": ["text"],
                                "additionalProperties": False,
                            },
                        }
                    ]
                }
            else:
                result = {
                    "content": [{"type": "text", "text": request["params"]["arguments"]["text"]}],
                    "isError": False,
                }
            if not legacy:
                result["resultType"] = "complete"
                if request["method"] in {"server/discover", "tools/list"}:
                    result.update(cacheScope="private", ttlMs=0)
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
            if legacy and request["method"] == "server/discover":
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -32601, "message": "unsupported"},
                }
            body = json.dumps(response).encode()
            content_type = "application/json"
            if mode == "sse":
                body = b"event: message\ndata: " + body + b"\n\n"
                content_type = "text/event-stream"
            if mode in {"oversized", "unterminated_sse"}:
                body = (b"data: " if mode == "unterminated_sse" else b'"') + b"x" * (256 * 1024 + 1)
                content_type = (
                    "text/event-stream" if mode == "unterminated_sse" else "application/json"
                )
            self.send_response(307 if mode == "redirect" else 200)
            self.send_header("Content-Type", content_type)
            self.send_header("Set-Cookie", "synthetic_state=untrusted")
            if legacy and request["method"] == "initialize":
                self.send_header("Mcp-Session-Id", "synthetic-session")
            if mode == "redirect":
                self.send_header("Location", "/redirected")
            if mode == "gzip":
                self.send_header("Content-Encoding", "gzip")
            if mode in {"oversized", "unterminated_sse"}:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            with suppress(OSError):
                if mode in {"oversized", "unterminated_sse"}:
                    for offset in range(0, len(body), 8192):
                        chunk = body[offset : offset + 8192]
                        self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                        self.wfile.flush()
                    self.wfile.write(b"0\r\n\r\n")
                else:
                    self.wfile.write(body)

        def do_GET(self) -> None:
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_DELETE(self) -> None:
            observed.append(
                {
                    "path": self.path,
                    "method": "DELETE",
                    "auth": self.headers.get("authorization"),
                    "cookie": self.headers.get("cookie"),
                }
            )
            self.send_response(503 if mode == "delete_failure" else 204)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    previous = os.environ.get("SSL_CERT_FILE")
    os.environ["SSL_CERT_FILE"] = str(cert)
    patch = pytest.MonkeyPatch()
    original_transport = httpx2.AsyncHTTPTransport

    def trusted_transport(**kwargs: Any) -> httpx2.AsyncHTTPTransport:
        # Change only the test CA; HTTP, TLS verification and the bounded adapter stay real.
        assert kwargs["trust_env"] is False
        production_context = kwargs.pop("verify")
        assert isinstance(production_context, ssl.SSLContext)
        assert production_context.minimum_version == ssl.TLSVersion.TLSv1_2
        return original_transport(verify=ssl.create_default_context(cafile=str(cert)), **kwargs)

    if trust_certificate:
        patch.setattr(httpx2, "AsyncHTTPTransport", trusted_transport)
    try:
        yield f"https://localhost:{server.server_port}/mcp", observed
    finally:
        patch.undo()
        server.shutdown()
        thread.join(5)
        server.server_close()
        if previous is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = previous


def registry(url: str) -> str:
    """Select a fixed HTTPS endpoint and environment-backed operator header."""
    return json.dumps(
        {
            "version": 2,
            "servers": {
                "synthetic": {
                    "transport": {"type": "https", "url": url},
                    "auth": {"scheme": "Bearer", "token_from": "SYNTHETIC_TOKEN"},
                    "tools": {"echo": {"assurance": "review_read"}},
                }
            },
        }
    )


@pytest.mark.parametrize("mode", ["json", "sse", "legacy"])
def test_actual_tls_sdk_streams_admit_bounded_text_without_cookie_authority(
    tmp_path: Path, mode: str
) -> None:
    with tls_peer(tmp_path / mode, mode) as (url, observed):
        gateway = start_gateway(
            parse_registry(registry(url), profile="gitlab_mr"),
            environment={"SYNTHETIC_TOKEN": "synthetic-auth-value"},
            run_id="a" * 32,
        )

        async def exercise() -> None:
            async with relay_client(gateway) as client:
                result = await client.call_tool(
                    "synthetic__echo", {"text": "controlled TLS result"}
                )
                assert result.content[0].text == "controlled TLS result"

        try:
            asyncio.run(exercise())
        finally:
            receipt = gateway.close()
        assert receipt["tools"]["synthetic__echo"]["completed"] == 1
        assert all(item["cookie"] is None for item in observed)
        assert all(item["auth"] == "Bearer synthetic-auth-value" for item in observed)
        assert "synthetic-auth-value" not in json.dumps(gateway.ocr_server)
        assert "synthetic-auth-value" not in json.dumps(receipt)
        if mode == "legacy":
            assert any(item["method"] == "initialize" for item in observed)
            assert any(item["method"] == "DELETE" for item in observed)


@pytest.mark.parametrize("mode", ["redirect", "gzip", "oversized", "unterminated_sse"])
def test_actual_tls_hostile_body_is_rejected_before_ready(tmp_path: Path, mode: str) -> None:
    with tls_peer(tmp_path / mode, mode) as (url, observed):
        with pytest.raises(FederationError):
            start_gateway(
                parse_registry(registry(url)),
                environment={"SYNTHETIC_TOKEN": "synthetic-auth-value"},
                run_id="a" * 32,
            )
        assert observed
        assert all(item["path"] == "/mcp" for item in observed)
        assert not any(item["method"] == "tools/call" for item in observed)


def test_tls_does_not_trust_ambient_certificate_environment(tmp_path: Path) -> None:
    with tls_peer(tmp_path / "untrusted", trust_certificate=False) as (url, observed):
        with pytest.raises(FederationError):
            start_gateway(
                parse_registry(registry(url)),
                environment={"SYNTHETIC_TOKEN": "synthetic-auth-value"},
                run_id="a" * 32,
            )
        assert not observed


def test_failed_http_session_deletion_prevents_finalized_receipt(tmp_path: Path) -> None:
    with tls_peer(tmp_path / "delete_failure", "delete_failure") as (url, observed):
        gateway = start_gateway(
            parse_registry(registry(url)),
            environment={"SYNTHETIC_TOKEN": "synthetic-auth-value"},
            run_id="a" * 32,
        )
        with pytest.raises(FederationError, match="cleanup_failed"):
            gateway.close()
        assert any(item["method"] == "DELETE" for item in observed)


def test_exhausted_wire_budget_before_session_delete_blocks_receipt(tmp_path: Path) -> None:
    with tls_peer(tmp_path / "delete_budget", "legacy") as (url, observed):
        gateway = start_gateway(
            parse_registry(registry(url)),
            environment={"SYNTHETIC_TOKEN": "synthetic-auth-value"},
            run_id="a" * 32,
        )
        assert gateway._gateway is not None
        gateway._gateway.budget.requests = WIRE_REQUESTS
        with pytest.raises(FederationError, match="cleanup_failed"):
            gateway.close()
        assert not any(item["method"] == "DELETE" for item in observed)


def test_https_endpoint_origin_is_always_allowed() -> None:
    value = json.loads(registry("https://synthetic.invalid:443/mcp"))
    value["servers"]["synthetic"]["tools"]["echo"]["resource_origins"] = [
        "https://additional.invalid"
    ]
    configured = parse_registry(json.dumps(value))
    assert configured.servers[0].tools[0].resource_origins == (
        "https://additional.invalid",
        "https://synthetic.invalid",
    )
    assert parse_registry(registry("https://synthetic.invalid/mcp")).servers[0].tools[
        0
    ].resource_origins == ("https://synthetic.invalid",)
