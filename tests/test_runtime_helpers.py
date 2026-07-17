"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from ocr_toolkit import config_writer, mcp_config, preflight
from ocr_toolkit import configure as ocr_configure
from tests.support import (
    patched_attr,
    patched_env,
)


class MCPConfigTests(unittest.TestCase):
    def test_runtime_config_updates_parse_headers_body_and_language(self) -> None:
        with patched_env(
            OCR_CLI_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_USE_ANTHROPIC="false",
            OCR_LLM_AUTH_HEADER="authorization",
            OCR_LLM_EXTRA_HEADERS='{"X-Workspace":"review"}',
            OCR_LLM_EXTRA_BODY='{"temperature":0}',
            OCR_TELEMETRY_ENABLED="true",
            OCR_TELEMETRY_CONTENT_LOGGING="false",
            OCR_TELEMETRY_EXPORTER="otlp",
            OCR_TELEMETRY_OTLP_ENDPOINT="http://otel.example",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["language"], "English")
        self.assertEqual(updates["llm.auth_token"], "llm-secret")
        self.assertEqual(updates["llm.protocol"], "openai")
        self.assertEqual(updates["llm.auth_header"], "authorization")
        self.assertEqual(updates["llm.extra_headers"], {"X-Workspace": "review"})
        self.assertEqual(updates["llm.extra_body"], {"temperature": 0})
        self.assertEqual(updates["telemetry.exporter"], "otlp")

    def test_runtime_config_default_auth_header_matches_preflight(self) -> None:
        with patched_env(
            OCR_CLI_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_USE_ANTHROPIC="false",
            OCR_LLM_AUTH_HEADER="",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.auth_header"], "Authorization")

    def test_runtime_config_rejects_duplicate_auth_extra_header(self) -> None:
        with (
            patched_env(
                OCR_CLI_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_USE_ANTHROPIC="false",
                OCR_LLM_AUTH_HEADER="Authorization",
                OCR_LLM_EXTRA_HEADERS='{"authorization":"other-token"}',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError) as ctx,
        ):
            ocr_configure.build_config_updates()

        self.assertIn("must not duplicate", str(ctx.exception))

    def test_runtime_config_supports_openai_responses_protocol(self) -> None:
        with patched_env(
            OCR_CLI_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/responses",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_PROTOCOL="openai-responses",
            OCR_USE_ANTHROPIC="false",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.protocol"], "openai-responses")
        self.assertFalse(updates["llm.use_anthropic"])

    def test_runtime_config_rejects_conflicting_protocol_modes(self) -> None:
        with (
            patched_env(
                OCR_CLI_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/responses",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_PROTOCOL="openai-responses",
                OCR_USE_ANTHROPIC="true",
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError) as ctx,
        ):
            ocr_configure.build_config_updates()

        self.assertIn("conflicts", str(ctx.exception))

    def test_runtime_config_requires_core_llm_env(self) -> None:
        with (
            patched_env(
                OCR_CLI_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_USE_ANTHROPIC="false",
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError) as ctx,
        ):
            ocr_configure.build_config_updates()

        self.assertIn("OCR_LLM_TOKEN is required", str(ctx.exception))

    def test_runtime_config_rejects_header_line_breaks(self) -> None:
        with (
            patched_env(
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_USE_ANTHROPIC="false",
                OCR_LLM_EXTRA_HEADERS='{"X-Test":"bad\\nvalue"}',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError),
        ):
            ocr_configure.build_config_updates()

    def test_runtime_config_rejects_non_string_extra_header_values(self) -> None:
        with (
            patched_env(
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_USE_ANTHROPIC="false",
                OCR_LLM_EXTRA_HEADERS='{"X-Test":{"bad":true}}',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError),
        ):
            ocr_configure.build_config_updates()

    def test_runtime_config_rejects_non_object_extra_body(self) -> None:
        with (
            patched_env(
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_USE_ANTHROPIC="false",
                OCR_LLM_EXTRA_BODY='["bad"]',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError),
        ):
            ocr_configure.build_config_updates()

    def test_runtime_config_preserves_explicit_empty_extra_body(self) -> None:
        with patched_env(
            OCR_CLI_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_PROTOCOL="openai",
            OCR_USE_ANTHROPIC="false",
            OCR_LLM_EXTRA_BODY="{}",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.extra_body"], {})

    def test_runtime_config_merges_anthropic_disable_thinking_with_extra_body(self) -> None:
        with patched_env(
            OCR_CLI_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="anthropic/claude-test",
            OCR_USE_ANTHROPIC="true",
            OCR_ANTHROPIC_DISABLE_THINKING="true",
            OCR_LLM_EXTRA_BODY='{"temperature":0}',
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(
            updates["llm.extra_body"],
            {"temperature": 0, "thinking": {"type": "disabled"}},
        )

    def test_runtime_config_rejects_conflicting_anthropic_thinking_body(self) -> None:
        with (
            patched_env(
                OCR_CLI_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="anthropic/claude-test",
                OCR_USE_ANTHROPIC="true",
                OCR_ANTHROPIC_DISABLE_THINKING="true",
                OCR_LLM_EXTRA_BODY='{"thinking":{"type":"enabled"}}',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError),
        ):
            ocr_configure.build_config_updates()

    def test_parse_remote_bridge_server_with_env_from(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "codegraph",
                        "command": "mcp-remote",
                        "args": ["https://mcp.example/sse"],
                        "tools": ["search"],
                        "env": {"MODE": "readonly"},
                        "env_from": {"AUTH_TOKEN": "OCR_MCP_CODEGRAPH_TOKEN"},
                    }
                ]
            }
        )

        with patched_env(OCR_MCP_CODEGRAPH_TOKEN="secret-token"):
            servers = mcp_config.parse_mcp_servers(raw)

        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0].command, "mcp-remote")
        self.assertEqual(servers[0].args, ["https://mcp.example/sse"])
        self.assertIn("AUTH_TOKEN=secret-token", servers[0].env)
        self.assertIn("MODE=readonly", servers[0].env)

    def test_parse_documented_named_server_map(self) -> None:
        raw = json.dumps(
            {
                "documentation": {
                    "command": "bridge",
                    "args": ["https://docs.example.invalid/mcp"],
                },
                "source": {"command": "source-bridge"},
            }
        )

        servers = mcp_config.parse_mcp_servers(raw)

        self.assertEqual([server.name for server in servers], ["documentation", "source"])
        self.assertEqual(servers[0].command, "bridge")

    def test_parse_mcp_servers_rejects_mixed_schema(self) -> None:
        raw = json.dumps({"servers": [], "documentation": {"command": "bridge"}})

        with self.assertRaises(mcp_config.MCPConfigError):
            mcp_config.parse_mcp_servers(raw)

    def test_parse_rejects_missing_env_from_secret(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "remote",
                        "command": "bridge",
                        "env_from": {"TOKEN": "MISSING_MCP_TOKEN"},
                    }
                ]
            }
        )

        old_value = os.environ.pop("MISSING_MCP_TOKEN", None)
        try:
            with self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(raw)
        finally:
            if old_value is not None:
                os.environ["MISSING_MCP_TOKEN"] = old_value

    def test_disabled_server_is_ignored(self) -> None:
        raw = json.dumps({"servers": [{"name": "off", "enabled": False, "command": "missing"}]})

        self.assertEqual(mcp_config.parse_mcp_servers(raw), [])

    def test_enabled_field_must_be_boolean(self) -> None:
        raw = json.dumps({"servers": [{"name": "off", "enabled": "false", "command": "bridge"}]})

        with self.assertRaises(mcp_config.MCPConfigError):
            mcp_config.parse_mcp_servers(raw)

    def test_configure_mcp_servers_writes_config_without_subprocess(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "remote",
                        "command": "bridge",
                        "args": ["https://mcp.example/sse"],
                        "setup": "",
                        "env_from": {"AUTH": "OCR_MCP_REMOTE_TOKEN"},
                    }
                ]
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                with patched_env(
                    OCR_MCP_SERVERS_JSON=raw,
                    OCR_MCP_REMOTE_TOKEN="bridge-secret-value",
                ):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(
                    (Path(tmp) / ".opencodereview" / "config.json").read_text(encoding="utf-8")
                )
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(config["mcp_servers"]["remote"]["command"], "bridge")
        self.assertEqual(config["mcp_servers"]["remote"]["setup"], "")
        self.assertEqual(config["mcp_servers"]["remote"]["env"], ["AUTH=bridge-secret-value"])

    def test_configure_mcp_servers_replaces_stale_servers(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "fresh",
                        "command": "bridge",
                    }
                ]
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            config_path.parent.mkdir()
            config_path.write_text(
                json.dumps({"mcp_servers": {"stale": {"command": "old"}}}),
                encoding="utf-8",
            )
            try:
                with patched_env(OCR_MCP_SERVERS_JSON=raw):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(config_path.read_text(encoding="utf-8"))
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(set(config["mcp_servers"]), {"fresh"})

    def test_configure_mcp_servers_clears_config_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            config_path.parent.mkdir()
            config_path.write_text(
                json.dumps({"mcp_servers": {"stale": {"command": "old"}}}),
                encoding="utf-8",
            )
            try:
                with patched_env(OCR_MCP_SERVERS_JSON=""):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(config_path.read_text(encoding="utf-8"))
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(config["mcp_servers"], {})

    def test_config_writer_sets_nested_values_with_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            config_writer.update_ocr_config(
                {
                    "llm.auth_token": "secret-value",
                    "mcp_servers.remote.setup": "",
                },
                path=config_path,
            )
            config = json.loads(config_path.read_text(encoding="utf-8"))
            mode = config_path.stat().st_mode & 0o777

        self.assertEqual(config["llm"]["auth_token"], "secret-value")
        self.assertEqual(config["mcp_servers"]["remote"]["setup"], "")
        self.assertEqual(mode, 0o600)

    def test_config_writer_rejects_non_object_parent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            config_path.parent.mkdir()
            config_path.write_text('{"llm":"legacy"}', encoding="utf-8")

            with self.assertRaises(config_writer.OCRConfigError):
                config_writer.update_ocr_config(
                    {"llm.auth_token": "secret-value"}, path=config_path
                )

    def test_config_writer_wraps_invalid_utf8_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            config_path.parent.mkdir()
            config_path.write_bytes(b"\xff")

            with self.assertRaises(config_writer.OCRConfigError):
                config_writer.read_ocr_config(config_path)

    def test_invalid_json_error_does_not_echo_secret_payload(self) -> None:
        stderr = io.StringIO()
        with patched_env(OCR_MCP_SERVERS_JSON='{"secret":"bridge-secret-value"'):
            with redirect_stderr(stderr):
                exit_code = mcp_config.configure_mcp_servers()

        self.assertEqual(exit_code, 1)
        self.assertNotIn("bridge-secret-value", stderr.getvalue())
        self.assertIn("not valid JSON", stderr.getvalue())


class PreflightTests(unittest.TestCase):
    def test_validate_ocr_binary_accepts_supported_version(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.7.11\n", stderr=""
        )
        with (
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", lambda *_args, **_kwargs: completed),
        ):
            preflight.validate_ocr_binary()

    def test_validate_ocr_binary_rejects_unsupported_version(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.7.10\n", stderr=""
        )
        with (
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", lambda *_args, **_kwargs: completed),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.validate_ocr_binary()

    def test_validate_ocr_binary_requires_external_executable(self) -> None:
        with (
            patched_attr(preflight.shutil, "which", lambda _name: None),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.validate_ocr_binary()

    def test_request_json_rejects_credentials_over_plain_http(self) -> None:
        with self.assertRaises(preflight.PreflightError) as ctx:
            preflight._request_json(
                "http://gateway.example/v1/models",
                {"Authorization": "Bearer secret-value"},
            )

        self.assertIn("non-HTTPS URL", str(ctx.exception))
        self.assertNotIn("secret-value", str(ctx.exception))

    def test_request_json_allows_plain_http_without_credentials(self) -> None:
        class FakeResponse:
            headers = {"Content-Length": "2"}

            def __init__(self) -> None:
                self.sent = False

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, _limit: int) -> bytes:
                if self.sent:
                    return b""
                self.sent = True
                return b"{}"

        with patched_attr(
            preflight.URL_OPENER,
            "open",
            lambda *_args, **_kwargs: FakeResponse(),
        ):
            self.assertEqual(
                preflight._request_json("http://localhost:11434/api/tags", {}),
                {},
            )

    def test_models_url_accepts_trailing_chat_completions_slash(self) -> None:
        with patched_env(
            OCR_LLM_MODELS_URL="",
            OCR_LLM_API_BASE_REMOVED="",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions/",
        ):
            self.assertEqual(preflight._models_url(), "https://gateway.example/v1/models")

    def test_models_url_accepts_responses_endpoint(self) -> None:
        with patched_env(
            OCR_LLM_MODELS_URL="",
            OCR_LLM_API_BASE_REMOVED="",
            OCR_LLM_URL="https://gateway.example/v1/responses",
        ):
            self.assertEqual(preflight._models_url(), "https://gateway.example/v1/models")

    def test_request_json_uses_urllib_transport_and_redacts_errors(self) -> None:
        calls: list[tuple[Any, dict[str, Any]]] = []

        def fake_open(request: Any, **kwargs: Any) -> Any:
            calls.append((request, kwargs))
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b"token=super-secret-value"),
            )

        with patched_env(OCR_LLM_TOKEN="super-secret-value"):
            with patched_attr(preflight.URL_OPENER, "open", fake_open):
                with self.assertRaises(preflight.PreflightError) as ctx:
                    preflight._request_json(
                        "https://gateway.example/v1/models",
                        {"Authorization": "Bearer super-secret-value"},
                    )

        self.assertEqual(calls[0][0].headers["Authorization"], "Bearer super-secret-value")
        self.assertEqual(calls[0][0].headers["Accept"], "application/json")
        self.assertEqual(
            calls[0][0].headers["User-agent"],
            "open-code-review-ci-preflight/1.0",
        )
        self.assertGreater(calls[0][1]["timeout"], 0)
        self.assertLessEqual(calls[0][1]["timeout"], preflight.HTTP_TIMEOUT_SECONDS)
        self.assertNotIn("super-secret-value", str(ctx.exception))
        self.assertIn("token=***", str(ctx.exception))

    def test_request_json_redacts_sensitive_url_in_errors(self) -> None:
        def fake_open(request: Any, **_kwargs: Any) -> Any:
            raise urllib.error.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs=None,
                fp=io.BytesIO(b""),
            )

        with patched_attr(preflight.URL_OPENER, "open", fake_open):
            with self.assertRaises(preflight.PreflightError) as ctx:
                preflight._request_json("https://gateway.example/models?private_token=secret", {})

        self.assertNotIn("secret", str(ctx.exception))
        self.assertIn("private_token=***", str(ctx.exception))

    def test_preflight_redirect_handler_blocks_redirects(self) -> None:
        handler = preflight._NoRedirectHandler()

        self.assertIsNone(
            handler.redirect_request(None, None, 302, "Found", {}, "https://other.example")
        )

    def test_request_json_parses_response_body(self) -> None:
        read_limits: list[int] = []

        class FakeResponse:
            def __init__(self) -> None:
                self.sent = False

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, limit: int) -> bytes:
                read_limits.append(limit)
                if self.sent:
                    return b""
                self.sent = True
                return b'{"data":[{"id":"model","context_length":10}]}'

        def fake_open(_request: Any, **_kwargs: Any) -> FakeResponse:
            return FakeResponse()

        with patched_attr(preflight.URL_OPENER, "open", fake_open):
            payload = preflight._request_json("https://gateway.example/v1/models", {})

        self.assertEqual(payload["data"][0]["id"], "model")
        self.assertEqual(read_limits, [64 * 1024, 64 * 1024])

    def test_request_json_rejects_oversized_success_body(self) -> None:
        class FakeResponse:
            def __init__(self) -> None:
                self.remaining = preflight.MAX_RESPONSE_BODY_BYTES

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, limit: int) -> bytes:
                if self.remaining <= 0:
                    return b"x"
                chunk = b" " * min(limit, self.remaining)
                self.remaining -= len(chunk)
                return chunk

        def fake_open(_request: Any, **_kwargs: Any) -> FakeResponse:
            return FakeResponse()

        with patched_attr(preflight.URL_OPENER, "open", fake_open):
            with self.assertRaises(preflight.PreflightError) as ctx:
                preflight._request_json("https://gateway.example/v1/models", {})

        self.assertIn("response exceeds", str(ctx.exception))

    def test_validate_llm_model_accepts_context_length_metadata(self) -> None:
        calls: list[tuple[str, dict[str, str]]] = []

        def fake_request(url: str, headers: dict[str, str]) -> dict[str, Any]:
            calls.append((url, headers))
            return {"data": [{"id": "openai/gpt-test", "context_length": 128000}]}

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="true",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_API_BASE_REMOVED="",
            ),
            patched_attr(preflight, "_request_json", fake_request),
        ):
            preflight.validate_llm_model()

        self.assertEqual(calls[0][0], "https://gateway.example/v1/models")
        self.assertEqual(calls[0][1], {"Authorization": "Bearer llm-secret"})

    def test_validate_llm_model_accepts_offline_allowed_model(self) -> None:
        def fail_request(_url: str, _headers: dict[str, str]) -> None:
            raise AssertionError("/models should not be queried")

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="false",
                OCR_LLM_ALLOWED_MODELS="openai/gpt-test,anthropic/claude-test",
                OCR_LLM_MODEL="openai/gpt-test",
            ),
            patched_attr(preflight, "_request_json", fail_request),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                preflight.validate_llm_model()

        self.assertIn("OCR model allowed by OCR_LLM_ALLOWED_MODELS", stdout.getvalue())
        self.assertIn("/models validation disabled", stdout.getvalue())

    def test_validate_llm_model_auto_continues_on_unavailable_metadata_when_allowlisted(
        self,
    ) -> None:
        def fail_request(_url: str, _headers: dict[str, str]) -> None:
            raise preflight.PreflightError(
                "GET https://gateway.example/v1/models failed with HTTP 403: error code: 1010"
            )

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="auto",
                OCR_LLM_ALLOWED_MODELS="openai/gpt-test",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_API_BASE_REMOVED="",
            ),
            patched_attr(preflight, "_request_json", fail_request),
        ):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                preflight.validate_llm_model()

        self.assertIn("validation unavailable", stderr.getvalue())

    def test_validate_llm_model_auto_fails_on_unavailable_metadata_without_allowlist(self) -> None:
        def fail_request(_url: str, _headers: dict[str, str]) -> None:
            raise preflight.PreflightError("metadata unavailable")

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="auto",
                OCR_LLM_ALLOWED_MODELS="",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_API_BASE_REMOVED="",
            ),
            patched_attr(preflight, "_request_json", fail_request),
        ):
            with self.assertRaises(preflight.PreflightError):
                preflight.validate_llm_model()

    def test_validate_llm_model_rejects_disallowed_offline_model(self) -> None:
        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="false",
                OCR_LLM_ALLOWED_MODELS="openai/gpt-test",
                OCR_LLM_MODEL="openai/typo",
            ),
            self.assertRaises(preflight.PreflightError) as ctx,
        ):
            preflight.validate_llm_model()

        self.assertIn("OCR_LLM_ALLOWED_MODELS", str(ctx.exception))

    def test_validate_llm_model_requires_model_when_metadata_disabled(self) -> None:
        with patched_env(OCR_LLM_VALIDATE_MODEL="false", OCR_LLM_MODEL=""):
            with self.assertRaises(preflight.PreflightError) as ctx:
                preflight.validate_llm_model()

        self.assertIn("OCR_LLM_MODEL is required", str(ctx.exception))

    def test_validate_llm_model_uses_configured_auth_and_extra_headers(self) -> None:
        calls: list[dict[str, str]] = []

        def fake_request(_url: str, headers: dict[str, str]) -> dict[str, Any]:
            calls.append(headers)
            return {"data": [{"id": "openai/gpt-test", "context_length": 128000}]}

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="true",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_AUTH_HEADER="X-Api-Key",
                OCR_LLM_EXTRA_HEADERS=json.dumps({"X-Workspace": "review"}),
                OCR_LLM_API_BASE_REMOVED="",
            ),
            patched_attr(preflight, "_request_json", fake_request),
        ):
            preflight.validate_llm_model()

        self.assertEqual(calls[0]["X-Api-Key"], "Bearer llm-secret")
        self.assertEqual(calls[0]["X-Workspace"], "review")

    def test_validate_llm_model_rejects_invalid_header_config(self) -> None:
        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="true",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_AUTH_HEADER="Bad Header",
                OCR_LLM_API_BASE_REMOVED="",
            ),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.validate_llm_model()

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="true",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_EXTRA_HEADERS=json.dumps({"X-Test": "ok\nbad"}),
                OCR_LLM_API_BASE_REMOVED="",
            ),
            self.assertRaises(preflight.PreflightError),
        ):
            preflight.validate_llm_model()

    def test_validate_llm_model_accepts_missing_context_length(self) -> None:
        def fake_request(_url: str, _headers: dict[str, str]) -> dict[str, Any]:
            return {"data": [{"id": "openai/gpt-test"}]}

        with (
            patched_env(
                OCR_LLM_VALIDATE_MODEL="true",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_MODELS_URL="",
                OCR_LLM_API_BASE_REMOVED="",
            ),
            patched_attr(preflight, "_request_json", fake_request),
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                preflight.validate_llm_model()

        self.assertIn("context_length=unknown", stdout.getvalue())

    def test_validate_llm_model_can_be_disabled_explicitly(self) -> None:
        def fail_request(_url: str, _headers: dict[str, str]) -> None:
            raise AssertionError("/models should not be queried")

        with patched_env(OCR_LLM_VALIDATE_MODEL="false", OCR_LLM_MODEL="openai/gpt-test"):
            with patched_attr(preflight, "_request_json", fail_request):
                preflight.validate_llm_model()
