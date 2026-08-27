"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ocr_toolkit import config_writer, mcp_config, preflight, provider_config
from ocr_toolkit import configure as ocr_configure
from tests.support import (
    cleared_env,
    patched_attr,
    patched_env,
)


class MCPConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(cleared_env("OCR_USE_ANTHROPIC"))

    def test_composition_readback_preserves_independent_registry_entries(self) -> None:
        composition = mcp_config.MCPComposition(
            payload={
                mcp_config.BUILTIN_EVIDENCE_SERVER: {
                    "type": "stdio",
                    "tools": [mcp_config.TOOL_NAME],
                },
                "documentation": {"type": "remote", "tools": ["docs_read"]},
            },
            capabilities=(),
            external_servers=(),
            secret_values=(),
        )
        with patched_attr(
            mcp_config, "read_ocr_config", lambda: {"mcp_servers": composition.payload}
        ):
            mcp_config.verify_mcp_composition(composition)

        mismatched = {"mcp_servers": {mcp_config.BUILTIN_EVIDENCE_SERVER: {}}}
        with (
            patched_attr(mcp_config, "read_ocr_config", lambda: mismatched),
            self.assertRaisesRegex(mcp_config.MCPConfigError, "does not match"),
        ):
            mcp_config.verify_mcp_composition(composition)

    def test_composition_keeps_external_and_replaces_stale_builtin(self) -> None:
        external = mcp_config.MCPServerConfig(
            name="synthetic_docs",
            transport="stdio",
            command="synthetic-docs",
            url=None,
            args=[],
            tools=["docs_read"],
            setup="",
            env=[],
            headers={},
            secret_values=[],
        )
        current = {
            "mcp_servers": {
                "existing": {"type": "stdio", "command": "existing", "tools": ["existing_read"]},
                mcp_config.BUILTIN_EVIDENCE_SERVER: {
                    "type": "stdio",
                    "command": "stale-command",
                    "tools": [mcp_config.TOOL_NAME],
                },
            }
        }
        with patched_attr(mcp_config, "read_ocr_config", lambda: current):
            composition = mcp_config.compose_mcp_servers([external], replace=False)

        self.assertEqual(
            set(composition.payload),
            {"existing", "synthetic_docs", mcp_config.BUILTIN_EVIDENCE_SERVER},
        )
        builtin = composition.payload[mcp_config.BUILTIN_EVIDENCE_SERVER]
        self.assertEqual(builtin["command"], sys.executable)
        self.assertEqual(builtin["args"], ["-I", "-m", "ocr_toolkit.evidence"])
        self.assertEqual(builtin["setup"], "")
        self.assertIsNot(builtin, composition.payload["existing"])
        self.assertIsNot(builtin, composition.payload["synthetic_docs"])
        self.assertEqual(composition.payload["synthetic_docs"]["command"], "synthetic-docs")
        self.assertEqual(
            [capability.server for capability in composition.capabilities],
            [mcp_config.BUILTIN_EVIDENCE_SERVER, "existing", "synthetic_docs"],
        )

    def test_explicit_server_replaces_same_named_invalid_inherited_entry(self) -> None:
        replacement = mcp_config.MCPServerConfig(
            name="remote",
            transport="remote",
            command=None,
            url="https://mcp.synthetic.invalid/v1",
            args=[],
            tools=["docs_read"],
            setup="",
            env=[],
            headers={},
            secret_values=[],
        )
        current = {
            "mcp_servers": {
                "remote": {
                    "type": "stdio",
                    "command": "stale-local",
                    "tools": ["stale_read"],
                }
            }
        }

        with patched_attr(mcp_config, "read_ocr_config", lambda: current):
            composition = mcp_config.compose_mcp_servers(
                [replacement], replace=False, profile="gitlab_mr"
            )

        self.assertEqual(composition.payload["remote"]["type"], "remote")
        self.assertEqual(composition.payload["remote"]["tools"], ["docs_read"])
        self.assertNotIn("command", composition.payload["remote"])

    def test_composition_rejects_tool_names_shared_by_independent_servers(self) -> None:
        external = mcp_config.MCPServerConfig(
            name="synthetic_docs",
            transport="stdio",
            command="synthetic-docs",
            url=None,
            args=[],
            tools=["shared_read"],
            setup="",
            env=[],
            headers={},
            secret_values=[],
        )
        current = {
            "mcp_servers": {
                "existing": {"type": "stdio", "command": "existing", "tools": ["shared_read"]}
            }
        }

        with (
            patched_attr(mcp_config, "read_ocr_config", lambda: current),
            self.assertRaisesRegex(mcp_config.MCPConfigError, "declared by both"),
        ):
            mcp_config.compose_mcp_servers([external], replace=False)

    def test_composition_bounds_retained_and_declared_external_servers_together(self) -> None:
        current = {
            "mcp_servers": {
                f"retained_{index}": {
                    "type": "stdio",
                    "command": f"retained-{index}",
                    "tools": [f"read_{index}"],
                }
                for index in range(mcp_config.MAX_MCP_SERVERS)
            }
        }
        external = mcp_config.MCPServerConfig(
            name="synthetic_extra",
            transport="stdio",
            command="synthetic-extra",
            url=None,
            args=[],
            tools=["synthetic_extra_read"],
            setup="",
            env=[],
            headers={},
            secret_values=[],
        )

        with (
            patched_attr(mcp_config, "read_ocr_config", lambda: current),
            self.assertRaisesRegex(mcp_config.MCPConfigError, "more than 16 external servers"),
        ):
            mcp_config.compose_mcp_servers([external], replace=False)

    def test_replace_drops_external_state_but_keeps_builtin(self) -> None:
        with patched_attr(
            mcp_config,
            "read_ocr_config",
            lambda: (_ for _ in ()).throw(AssertionError("replace must not read state")),
        ):
            composition = mcp_config.compose_mcp_servers([], replace=True)

        self.assertEqual(set(composition.payload), {mcp_config.BUILTIN_EVIDENCE_SERVER})

    def test_external_server_cannot_claim_builtin_tool(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "synthetic_docs",
                        "command": "synthetic-docs",
                        "tools": [mcp_config.TOOL_NAME],
                    }
                ]
            }
        )
        with self.assertRaisesRegex(mcp_config.MCPConfigError, "reserved"):
            mcp_config.parse_mcp_servers(raw)

    def test_external_server_requires_explicit_tool_allowlist(self) -> None:
        raw = json.dumps({"synthetic_docs": {"command": "synthetic-docs", "tools": []}})

        with self.assertRaisesRegex(mcp_config.MCPConfigError, "explicitly allow"):
            mcp_config.parse_mcp_servers(raw)

    def test_runtime_config_defaults_review_language_to_english(self) -> None:
        with (
            cleared_env("OCR_REVIEW_LANGUAGE"),
            cleared_env("OCR_REVIEW_EFFORT"),
            patched_env(
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
            ),
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["language"], "English")
        self.assertEqual(updates["effort"], "medium")

    def test_runtime_config_accepts_closed_review_effort_presets(self) -> None:
        """Only upstream's three stable presets enter the generated root config."""

        for value in ("low", "medium", "high", " HIGH "):
            with (
                self.subTest(value=value),
                patched_env(
                    OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                    OCR_LLM_TOKEN="llm-secret",
                    OCR_LLM_MODEL="openai/gpt-test",
                    OCR_REVIEW_EFFORT=value,
                ),
            ):
                updates = ocr_configure.build_config_updates()

            self.assertEqual(updates["effort"], value.strip().lower())

    def test_runtime_config_rejects_unknown_review_effort(self) -> None:
        """Unknown effort never falls through to an OCR-owned implicit default."""

        with (
            patched_env(
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_REVIEW_EFFORT="extreme",
            ),
            self.assertRaisesRegex(
                ocr_configure.OCRRuntimeConfigError,
                "OCR_REVIEW_EFFORT must be one of",
            ),
        ):
            ocr_configure.build_config_updates()

    def test_runtime_config_rejects_non_https_llm_url_before_storing_token(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="http://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
        ):
            with self.assertRaisesRegex(
                ocr_configure.OCRRuntimeConfigError, "OCR_LLM_URL must be an absolute HTTPS URL"
            ):
                ocr_configure.build_config_updates()

    def test_runtime_config_rejects_llm_url_with_embedded_credentials(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://user:password@gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
        ):
            with self.assertRaisesRegex(
                ocr_configure.OCRRuntimeConfigError, "without embedded credentials"
            ):
                ocr_configure.build_config_updates()

    def test_runtime_config_rejects_llm_url_with_invalid_port(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example:not-a-port/v1/responses",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
        ):
            with self.assertRaisesRegex(ocr_configure.OCRRuntimeConfigError, "absolute HTTPS URL"):
                ocr_configure.build_config_updates()

    def test_runtime_config_updates_parse_headers_body_and_language(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
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
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_AUTH_HEADER="",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.auth_header"], "Authorization")

    def test_runtime_config_rejects_duplicate_auth_extra_header(self) -> None:
        with (
            patched_env(
                OCR_REVIEW_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="openai/gpt-test",
                OCR_LLM_AUTH_HEADER="Authorization",
                OCR_LLM_EXTRA_HEADERS='{"authorization":"other-token"}',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError) as ctx,
        ):
            ocr_configure.build_config_updates()

        self.assertIn("must not duplicate", str(ctx.exception))

    def test_runtime_config_supports_openai_responses_protocol(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/responses",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_PROTOCOL="openai-responses",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.protocol"], "openai-responses")
        self.assertFalse(updates["llm.use_anthropic"])
        self.assertEqual(updates["llm.url"], "https://gateway.example/v1")

    def test_provider_config_normalizes_roots_endpoints_and_query(self) -> None:
        cases = (
            ("openai", "https://gateway.example/v1/", "https://gateway.example/v1"),
            (
                "openai",
                "https://gateway.example/v1/chat/completions/",
                "https://gateway.example/v1",
            ),
            (
                "openai-responses",
                "https://gateway.example/v1/responses",
                "https://gateway.example/v1",
            ),
            (
                "anthropic",
                "https://gateway.example/proxy/v1/messages",
                "https://gateway.example/proxy",
            ),
        )
        for protocol, raw_url, expected_root in cases:
            with self.subTest(protocol=protocol, raw_url=raw_url):
                config = provider_config.provider_config_from_environment(
                    {"OCR_LLM_PROTOCOL": protocol, "OCR_LLM_URL": raw_url}
                )

            self.assertEqual(config.api_root_url, expected_root)
            self.assertEqual(config.inference_url, expected_root)
            self.assertEqual(config.models_url, f"{expected_root}/models")

        queried = provider_config.provider_config_from_environment(
            {
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_LLM_URL": "https://gateway.example/v1/chat/completions?tenant=review",
            }
        )
        self.assertEqual(queried.api_root_url, "https://gateway.example/v1")
        self.assertEqual(queried.inference_url, "https://gateway.example/v1?tenant=review")
        self.assertIsNone(queried.models_url)
        with self.assertRaisesRegex(provider_config.ProviderConfigError, "OCR_LLM_MODELS_URL"):
            queried.require_models_url()

    def test_provider_config_uses_explicit_models_url_for_queried_inference(self) -> None:
        config = provider_config.provider_config_from_environment(
            {
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_LLM_URL": "https://gateway.example/v1?tenant=review",
                "OCR_LLM_MODELS_URL": "https://metadata.example/catalog?tenant=review",
            }
        )

        self.assertEqual(
            config.models_url,
            "https://metadata.example/catalog?tenant=review",
        )

    def test_provider_config_rejects_protocol_mismatched_terminal_endpoints(self) -> None:
        cases = (
            ("openai", "https://gateway.example/v1/responses"),
            ("openai", "https://gateway.example/v1/messages"),
            ("openai-responses", "https://gateway.example/v1/chat/completions"),
            ("anthropic", "https://gateway.example/v1/responses"),
        )
        for protocol, url in cases:
            with (
                self.subTest(protocol=protocol, url=url),
                self.assertRaisesRegex(
                    provider_config.ProviderConfigError,
                    "terminal endpoint conflicts with OCR_LLM_PROTOCOL",
                ),
            ):
                provider_config.provider_config_from_environment(
                    {"OCR_LLM_PROTOCOL": protocol, "OCR_LLM_URL": url}
                )

    def test_provider_config_rejects_fragments_and_hides_secret_fields_from_repr(self) -> None:
        for name in ("OCR_LLM_URL", "OCR_LLM_MODELS_URL"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(provider_config.ProviderConfigError, "fragment"),
            ):
                provider_config.provider_config_from_environment(
                    {
                        "OCR_LLM_PROTOCOL": "openai",
                        name: "https://gateway.example/v1#private",
                    }
                )

        config = provider_config.provider_config_from_environment(
            {
                "OCR_LLM_EXTRA_HEADERS": '{"X-Secret":"private-header"}',
                "OCR_LLM_EXTRA_BODY": '{"private-body":"value"}',
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_LLM_TOKEN": "private-token",
                "OCR_LLM_URL": "https://gateway.example/v1",
            }
        )
        rendered = repr(config)
        self.assertNotIn("private-token", rendered)
        self.assertNotIn("private-header", rendered)
        self.assertNotIn("private-body", rendered)

    def test_provider_config_rejects_embedded_url_whitespace(self) -> None:
        """Reject URL characters that urllib would otherwise silently normalize."""

        for raw_url in (
            "https://gate\nway.example/v1",
            "https://gateway.example/v1\t/models",
            "https://gateway.example/v1 /models",
        ):
            with (
                self.subTest(raw_url=raw_url),
                self.assertRaisesRegex(provider_config.ProviderConfigError, "absolute HTTPS URL"),
            ):
                provider_config.provider_config_from_environment(
                    {"OCR_LLM_PROTOCOL": "openai", "OCR_LLM_URL": raw_url}
                )

    def test_runtime_config_rejects_removed_anthropic_switch_with_migration(self) -> None:
        for legacy_value in ("", "false", "true"):
            with (
                self.subTest(legacy_value=legacy_value),
                patched_env(
                    OCR_REVIEW_LANGUAGE="English",
                    OCR_LLM_URL="https://gateway.example/v1/responses",
                    OCR_LLM_TOKEN="llm-secret",
                    OCR_LLM_MODEL="openai/gpt-test",
                    OCR_LLM_PROTOCOL="openai-responses",
                    OCR_USE_ANTHROPIC=legacy_value,
                ),
                self.assertRaises(ocr_configure.OCRRuntimeConfigError) as ctx,
            ):
                ocr_configure.build_config_updates()

            self.assertEqual(
                str(ctx.exception),
                "OCR_USE_ANTHROPIC was removed; set OCR_LLM_PROTOCOL=anthropic explicitly",
            )

    def test_runtime_config_requires_core_llm_env(self) -> None:
        with (
            patched_env(
                OCR_REVIEW_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="",
                OCR_LLM_MODEL="openai/gpt-test",
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
                OCR_LLM_EXTRA_BODY='["bad"]',
            ),
            self.assertRaises(ocr_configure.OCRRuntimeConfigError),
        ):
            ocr_configure.build_config_updates()

    def test_runtime_config_preserves_explicit_empty_extra_body(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_PROTOCOL="openai",
            OCR_LLM_EXTRA_BODY="{}",
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(updates["llm.extra_body"], {})

    def test_runtime_config_maps_completion_cap_by_protocol(self) -> None:
        expected = {
            "openai": "max_completion_tokens",
            "openai-responses": "max_output_tokens",
            "anthropic": "max_tokens",
        }
        for protocol, field in expected.items():
            with (
                self.subTest(protocol=protocol),
                patched_env(
                    OCR_LLM_URL="https://gateway.example/v1",
                    OCR_LLM_TOKEN="llm-secret",
                    OCR_LLM_MODEL="provider/model",
                    OCR_LLM_PROTOCOL=protocol,
                    OCR_LLM_MAX_COMPLETION_TOKENS="4096",
                ),
            ):
                updates = ocr_configure.build_config_updates()

            self.assertEqual(updates["llm.extra_body"], {field: 4096})

    def test_runtime_config_deduplicates_equal_completion_cap(self) -> None:
        with patched_env(
            OCR_LLM_URL="https://gateway.example/v1/chat/completions",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="openai/gpt-test",
            OCR_LLM_PROTOCOL="openai",
            OCR_LLM_MAX_COMPLETION_TOKENS="4096",
            OCR_LLM_EXTRA_BODY='{"temperature":0,"max_completion_tokens":4096}',
        ):
            updates = ocr_configure.build_config_updates()

        self.assertEqual(
            updates["llm.extra_body"],
            {"temperature": 0, "max_completion_tokens": 4096},
        )

    def test_runtime_config_rejects_conflicting_completion_cap(self) -> None:
        for conflicting in (8192, 4096.0, True, None, "4096"):
            with (
                self.subTest(conflicting=conflicting),
                patched_env(
                    OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                    OCR_LLM_TOKEN="llm-secret",
                    OCR_LLM_MODEL="openai/gpt-test",
                    OCR_LLM_PROTOCOL="openai",
                    OCR_LLM_MAX_COMPLETION_TOKENS="4096",
                    OCR_LLM_EXTRA_BODY=json.dumps({"max_completion_tokens": conflicting}),
                ),
                self.assertRaisesRegex(
                    ocr_configure.OCRRuntimeConfigError,
                    "conflicts with OCR_LLM_EXTRA_BODY.max_completion_tokens",
                ),
            ):
                ocr_configure.build_config_updates()

    def test_runtime_config_rejects_invalid_completion_caps(self) -> None:
        for value in ("0", "-1", "+1", "1.5", "1000001", "9" * 5000):
            with (
                self.subTest(value=value),
                patched_env(
                    OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                    OCR_LLM_TOKEN="llm-secret",
                    OCR_LLM_MODEL="openai/gpt-test",
                    OCR_LLM_PROTOCOL="openai",
                    OCR_LLM_MAX_COMPLETION_TOKENS=value,
                ),
                self.assertRaises(ocr_configure.OCRRuntimeConfigError),
            ):
                ocr_configure.build_config_updates()

    def test_runtime_config_merges_anthropic_disable_thinking_with_extra_body(self) -> None:
        with patched_env(
            OCR_REVIEW_LANGUAGE="English",
            OCR_LLM_URL="https://gateway.example",
            OCR_LLM_TOKEN="llm-secret",
            OCR_LLM_MODEL="anthropic/claude-test",
            OCR_LLM_PROTOCOL="anthropic",
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
                OCR_REVIEW_LANGUAGE="English",
                OCR_LLM_URL="https://gateway.example/v1/chat/completions",
                OCR_LLM_TOKEN="llm-secret",
                OCR_LLM_MODEL="anthropic/claude-test",
                OCR_LLM_PROTOCOL="anthropic",
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
        self.assertEqual(servers[0].transport, "stdio")

    def test_parse_native_remote_server_with_env_backed_header(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "remote",
                        "type": "remote",
                        "url": "https://mcp.synthetic.invalid/v1/mcp?tenant=alpha",
                        "headers": {"X-Client": "ocr-toolkit"},
                        "headers_from": {"Authorization": "SYNTHETIC_MCP_TOKEN"},
                        "tools": ["search"],
                    }
                ]
            }
        )

        with patched_env(SYNTHETIC_MCP_TOKEN="remote-secret-value"):
            servers = mcp_config.parse_mcp_servers(raw)

        self.assertEqual(servers[0].transport, "remote")
        self.assertEqual(servers[0].url, "https://mcp.synthetic.invalid/v1/mcp?tenant=alpha")
        self.assertEqual(
            servers[0].headers,
            {"X-Client": "ocr-toolkit", "Authorization": "$SYNTHETIC_MCP_TOKEN"},
        )
        self.assertEqual(servers[0].secret_values, ["remote-secret-value"])

    def test_native_remote_server_rejects_unsafe_url_and_transport_fields(self) -> None:
        invalid_servers = (
            {"name": "remote", "type": "remote", "url": "http://mcp.invalid"},
            {"name": "remote", "type": "remote", "url": "https://mcp.invalid/v1\nnext"},
            {"name": "remote", "type": "remote", "url": "https://user@mcp.invalid/v1"},
            {"name": "remote", "type": "remote", "url": "https://mcp.invalid/v1#secret"},
            {
                "name": "remote",
                "type": "remote",
                "url": "https://mcp.invalid/v1",
                "command": "proxy",
            },
            {
                "name": "local",
                "type": "stdio",
                "command": "local",
                "url": "https://mcp.invalid",
            },
        )
        for server in invalid_servers:
            server["tools"] = ["docs_read"]
            with (
                self.subTest(server=server),
                self.assertRaisesRegex(mcp_config.MCPConfigError, "url|field|command"),
            ):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [server]}))

    def test_native_remote_server_rejects_unsafe_headers(self) -> None:
        cases = (
            {"Authorization": "Bearer literal-secret"},
            {"X-Auth": "literal-secret"},
            {"X-Api-Key": "literal-secret"},
            {"Ocp-Apim-Subscription-Key": "literal-secret"},
            {"X-Test": "line-one\r\nInjected: value"},
            {"X-Reference": "$SYNTHETIC_MCP_TOKEN"},
        )
        for headers in cases:
            raw = json.dumps(
                {
                    "servers": [
                        {
                            "name": "remote",
                            "type": "remote",
                            "url": "https://mcp.invalid/v1",
                            "tools": ["docs_read"],
                            "headers": headers,
                        }
                    ]
                }
            )
            with (
                self.subTest(headers=headers),
                self.assertRaisesRegex(mcp_config.MCPConfigError, "headers"),
            ):
                mcp_config.parse_mcp_servers(raw)

    def test_native_remote_server_rejects_duplicate_and_missing_env_headers(self) -> None:
        duplicate = {
            "name": "remote",
            "type": "remote",
            "url": "https://mcp.invalid/v1",
            "headers": {"X-Client": "toolkit"},
            "headers_from": {"x-client": "SYNTHETIC_MCP_TOKEN"},
        }
        missing = {
            "name": "remote",
            "type": "remote",
            "url": "https://mcp.invalid/v1",
            "headers_from": {"Authorization": "SYNTHETIC_MCP_TOKEN"},
        }
        with patched_env(SYNTHETIC_MCP_TOKEN="remote-secret-value"):
            with self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [duplicate]}))
        with cleared_env("SYNTHETIC_MCP_TOKEN"):
            with self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [missing]}))
        with patched_env(SYNTHETIC_MCP_TOKEN="token\r\nInjected: value"):
            with self.assertRaises(mcp_config.MCPConfigError, msg="header env must reject CRLF"):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [missing]}))
        with patched_env(SYNTHETIC_MCP_TOKEN="x" * (mcp_config.MAX_MCP_HEADER_VALUE_CHARS + 1)):
            with self.assertRaises(mcp_config.MCPConfigError, msg="header env must be bounded"):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [missing]}))

    def test_mcp_server_rejects_oversized_individual_fields(self) -> None:
        cases = (
            {"name": "local", "command": "x" * (mcp_config.MAX_MCP_STRING_CHARS + 1)},
            {
                "name": "local",
                "command": "tool",
                "args": ["x" * (mcp_config.MAX_MCP_STRING_CHARS + 1)],
            },
            {
                "name": "remote",
                "type": "remote",
                "url": "https://mcp.invalid/v1",
                "headers": {"X-Context": "x" * (mcp_config.MAX_MCP_HEADER_VALUE_CHARS + 1)},
            },
            {
                "name": "remote",
                "type": "remote",
                "url": "https://mcp.invalid/v1",
                "setup": "x" * (mcp_config.MAX_MCP_SETUP_CHARS + 1),
            },
        )
        for server in cases:
            with self.subTest(server=server), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [server]}))

    def test_parse_documented_named_server_map(self) -> None:
        raw = json.dumps(
            {
                "documentation": {
                    "command": "bridge",
                    "args": ["https://docs.example.invalid/mcp"],
                    "tools": ["docs_read"],
                },
                "source": {"command": "source-bridge", "tools": ["source_read"]},
            }
        )

        servers = mcp_config.parse_mcp_servers(raw)

        self.assertEqual([server.name for server in servers], ["documentation", "source"])
        self.assertEqual(servers[0].command, "bridge")

    def test_parse_mcp_servers_rejects_mixed_schema(self) -> None:
        raw = json.dumps({"servers": [], "documentation": {"command": "bridge"}})

        with self.assertRaises(mcp_config.MCPConfigError):
            mcp_config.parse_mcp_servers(raw)

    def test_parse_mcp_servers_rejects_malformed_registry_shapes(self) -> None:
        """Reject ambiguous registry, server, transport, and tool-list shapes."""

        cases: tuple[object, ...] = (
            [],
            {"servers": {}},
            {"documentation": "bridge"},
            {"documentation": {"name": "source", "command": "bridge"}},
            {"servers": ["bridge"]},
            {"servers": [{"name": "bad name", "command": "bridge"}]},
            {
                "servers": [
                    {"name": "duplicate", "command": "bridge", "tools": ["read"]},
                    {"name": "duplicate", "command": "bridge", "tools": ["search"]},
                ]
            },
            {"servers": [{"name": "bridge", "type": "socket", "tools": ["read"]}]},
            {"servers": [{"name": "bridge", "command": "bridge", "tools": "read"}]},
            {
                "servers": [
                    {
                        "name": "bridge",
                        "command": "bridge",
                        "tools": ["read"] * (mcp_config.MAX_MCP_TOOLS + 1),
                    }
                ]
            },
            {"servers": [{"name": "bridge", "command": "bridge", "tools": [7]}]},
            {
                "servers": [
                    {
                        "name": "bridge",
                        "command": "bridge",
                        "tools": ["x" * (mcp_config.MAX_MCP_STRING_CHARS + 1)],
                    }
                ]
            },
            {"servers": [{"name": "bridge", "command": "bridge", "tools": []}]},
            {
                "servers": [
                    {
                        "name": "bridge",
                        "command": "bridge",
                        "tools": [mcp_config.TOOL_NAME],
                    }
                ]
            },
            {"servers": [{"name": "bridge", "command": "bridge", "tools": ["read"], "setup": 7}]},
            {"servers": [{"name": "bridge", "command": "", "tools": ["read"]}]},
            {
                "servers": [
                    {
                        "name": "bridge",
                        "command": "x" * (mcp_config.MAX_MCP_STRING_CHARS + 1),
                        "tools": ["read"],
                    }
                ]
            },
            {"servers": [{"name": "bridge", "command": "bridge", "tools": ["read"], "args": {}}]},
        )
        cases += (
            {
                f"server-{index}": {"command": "bridge", "tools": [f"read-{index}"]}
                for index in range(mcp_config.MAX_MCP_SERVERS + 1)
            },
        )

        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps(payload))

        with self.assertRaisesRegex(mcp_config.MCPConfigError, "profile"):
            mcp_config.parse_mcp_servers("{}", profile="unknown")
        with self.assertRaisesRegex(mcp_config.MCPConfigError, "valid JSON"):
            mcp_config.parse_mcp_servers("{")
        with self.assertRaisesRegex(mcp_config.MCPConfigError, "exceeds"):
            mcp_config.parse_mcp_servers("x" * (mcp_config.MAX_MCP_CONFIG_BYTES + 1))

    def test_stdio_environment_rejects_ambiguous_or_unbounded_assignments(self) -> None:
        """Admit stdio environment only from bounded, distinct variable mappings."""

        base: dict[str, object] = {
            "name": "bridge",
            "command": "bridge",
            "tools": ["read"],
        }
        cases = (
            {"env": []},
            {"env_from": []},
            {"env": {"bad-name": "value"}},
            {"env": {"MODE": 7}},
            {"env": {"MODE": "x" * mcp_config.MAX_MCP_STRING_CHARS}},
            {"env_from": {"bad-name": "MCP_TOKEN"}},
            {"env": {"TOKEN": "literal"}, "env_from": {"TOKEN": "MCP_TOKEN"}},
            {"env_from": {"TOKEN": "bad-name"}},
            {"env": {f"VALUE_{index}": "safe" for index in range(mcp_config.MAX_MCP_ENV + 1)}},
        )
        with patched_env(MCP_TOKEN="provider-secret"):
            for fields in cases:
                payload = {"servers": [{**base, **fields}]}
                with self.subTest(fields=fields), self.assertRaises(mcp_config.MCPConfigError):
                    mcp_config.parse_mcp_servers(json.dumps(payload))

    def test_remote_headers_reject_ambiguous_or_unbounded_mappings(self) -> None:
        """Admit remote headers only from bounded HTTP-safe distinct mappings."""

        base: dict[str, object] = {
            "name": "remote",
            "type": "remote",
            "url": "https://mcp.invalid/v1",
            "tools": ["read"],
        }
        cases = (
            {"headers": []},
            {"headers_from": []},
            {"headers": {"Bad Header": "value"}},
            {"headers": {"X-Mode": "safe", "x-mode": "duplicate"}},
            {"headers": {"X-Mode": 7}},
            {"headers": {"X-Mode": ""}},
            {"headers_from": {"Authorization": "bad-name"}},
            {
                "headers": {
                    f"X-Value-{index}": "safe" for index in range(mcp_config.MAX_MCP_HEADERS + 1)
                }
            },
        )
        for fields in cases:
            payload = {"servers": [{**base, **fields}]}
            with self.subTest(fields=fields), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps(payload))

    def test_remote_url_rejects_invalid_bounds_and_ports(self) -> None:
        """Require one bounded absolute HTTPS endpoint with a valid port."""

        for url in (
            None,
            "",
            "https://mcp.invalid/" + "x" * mcp_config.MAX_MCP_URL_CHARS,
            "https://mcp.invalid:invalid/v1",
            "https://mcp.invalid:70000/v1",
        ):
            payload = {
                "servers": [
                    {
                        "name": "remote",
                        "type": "remote",
                        "url": url,
                        "tools": ["read"],
                    }
                ]
            }
            with self.subTest(url=url), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps(payload))

    def test_parse_rejects_missing_env_from_secret(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "remote",
                        "command": "bridge",
                        "tools": ["docs_read"],
                        "env_from": {"TOKEN": "MISSING_MCP_TOKEN"},
                    }
                ]
            }
        )

        old_value = os.environ.pop("MISSING_MCP_TOKEN", None)
        try:
            with self.assertRaisesRegex(mcp_config.MCPConfigError, "MISSING_MCP_TOKEN"):
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

    def test_parse_rejects_the_reserved_builtin_server_name(self) -> None:
        raw = json.dumps({mcp_config.BUILTIN_EVIDENCE_SERVER: {"command": "synthetic-override"}})

        with self.assertRaisesRegex(mcp_config.MCPConfigError, "reserved"):
            mcp_config.parse_mcp_servers(raw)

    def test_tool_allowlist_accepts_ocr_names_and_rejects_empty_or_duplicate_entries(self) -> None:
        accepted = json.dumps(
            {
                "remote": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "tools": ["repo.search", "records/read"],
                }
            }
        )
        self.assertEqual(
            mcp_config.parse_mcp_servers(accepted, profile="gitlab_mr")[0].tools,
            ["repo.search", "records/read"],
        )
        for tools in ([""], ["docs_read", "docs_read"]):
            candidate = json.dumps(
                {
                    "remote": {
                        "type": "remote",
                        "url": "https://mcp.synthetic.invalid/v1",
                        "tools": tools,
                    }
                }
            )
            with self.subTest(tools=tools), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(candidate, profile="gitlab_mr")

    def test_composer_rejects_prebuilt_stdio_under_gitlab_profile(self) -> None:
        prebuilt = mcp_config.MCPServerConfig(
            name="local",
            transport="stdio",
            command="bridge",
            url=None,
            args=[],
            tools=["docs_read"],
            setup="",
            env=[],
            headers={},
            secret_values=[],
        )

        with self.assertRaisesRegex(mcp_config.MCPConfigError, "external remote"):
            mcp_config.compose_mcp_servers([prebuilt], replace=True, profile="gitlab_mr")
        with self.assertRaisesRegex(mcp_config.MCPConfigError, "execution profile"):
            mcp_config.compose_mcp_servers([], replace=True, profile="unknown")

    def test_gitlab_profile_accepts_remote_without_setup_and_rejects_external_stdio(self) -> None:
        remote = json.dumps(
            {
                "remote": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "tools": ["docs_read"],
                }
            }
        )
        servers = mcp_config.parse_mcp_servers(remote, profile="gitlab_mr")
        self.assertEqual(servers[0].transport, "remote")
        composition = mcp_config.compose_mcp_servers(servers, replace=True, profile="gitlab_mr")
        self.assertNotIn("setup", composition.payload["remote"])

        stdio = json.dumps(
            {"local": {"type": "stdio", "command": "bridge", "tools": ["docs_read"]}}
        )
        with self.assertRaisesRegex(mcp_config.MCPConfigError, "external remote"):
            mcp_config.parse_mcp_servers(stdio, profile="gitlab_mr")

    def test_remote_schema_rejects_setup_and_all_stdio_only_fields(self) -> None:
        for field, value in (
            ("setup", "echo unsafe"),
            ("command", "bridge"),
            ("args", []),
            ("env", {}),
            ("env_from", {}),
        ):
            server = {
                "name": "remote",
                "type": "remote",
                "url": "https://mcp.synthetic.invalid/v1",
                "tools": ["docs_read"],
                field: value,
            }
            with self.subTest(field=field), self.assertRaises(mcp_config.MCPConfigError):
                mcp_config.parse_mcp_servers(json.dumps({"servers": [server]}))

    def test_gitlab_profile_revalidates_inherited_registry_without_bypass(self) -> None:
        inherited_stdio = {
            "mcp_servers": {
                "existing": {
                    "type": "stdio",
                    "command": "existing",
                    "tools": ["existing_read"],
                }
            }
        }
        with (
            patched_attr(mcp_config, "read_ocr_config", lambda: inherited_stdio),
            self.assertRaisesRegex(mcp_config.MCPConfigError, "external remote"),
        ):
            mcp_config.compose_mcp_servers([], replace=False, profile="gitlab_mr")

        legacy_remote_with_empty_setup = {
            "mcp_servers": {
                "existing": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "tools": ["existing_read"],
                    "setup": "",
                }
            }
        }
        with patched_attr(mcp_config, "read_ocr_config", lambda: legacy_remote_with_empty_setup):
            migrated = mcp_config.compose_mcp_servers([], replace=False, profile="gitlab_mr")
        self.assertNotIn("setup", migrated.payload["existing"])

        inherited_remote_with_setup = {
            "mcp_servers": {
                "existing": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "tools": ["existing_read"],
                    "setup": "echo unsafe",
                }
            }
        }
        with (
            patched_attr(mcp_config, "read_ocr_config", lambda: inherited_remote_with_setup),
            self.assertRaises(mcp_config.MCPConfigError),
        ):
            mcp_config.compose_mcp_servers([], replace=False, profile="gitlab_mr")

    def test_profiled_composition_revalidates_its_persisted_secret_references(self) -> None:
        raw = json.dumps(
            {
                "remote": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "headers_from": {"Authorization": "SYNTHETIC_MCP_TOKEN"},
                    "tools": ["docs_read"],
                }
            }
        )
        with patched_env(SYNTHETIC_MCP_TOKEN="remote-secret-value"):
            servers = mcp_config.parse_mcp_servers(raw, profile="gitlab_mr")
            first = mcp_config.compose_mcp_servers(servers, replace=True, profile="gitlab_mr")
            with patched_attr(
                mcp_config, "read_ocr_config", lambda: {"mcp_servers": first.payload}
            ):
                second = mcp_config.compose_mcp_servers([], replace=False, profile="gitlab_mr")

        self.assertEqual(second.payload, first.payload)
        self.assertEqual(
            second.payload["remote"]["headers"]["Authorization"],
            "$SYNTHETIC_MCP_TOKEN",
        )
        self.assertEqual(
            [(item.server, item.transport) for item in second.capabilities],
            [(mcp_config.BUILTIN_EVIDENCE_SERVER, "stdio"), ("remote", "remote")],
        )
        self.assertEqual(second.secret_values, ("remote-secret-value",))

    def test_persisted_remote_header_sources_reject_cross_form_duplicates(self) -> None:
        current = {
            "mcp_servers": {
                "remote": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1",
                    "headers": {"Authorization": "$SYNTHETIC_MCP_TOKEN"},
                    "headers_from": {"authorization": "SYNTHETIC_MCP_TOKEN"},
                    "tools": ["docs_read"],
                }
            }
        }
        with (
            patched_env(SYNTHETIC_MCP_TOKEN="remote-secret-value"),
            patched_attr(mcp_config, "read_ocr_config", lambda: current),
            self.assertRaisesRegex(mcp_config.MCPConfigError, "duplicate header sources"),
        ):
            mcp_config.compose_mcp_servers([], replace=False, profile="gitlab_mr")

    def test_local_composition_revalidates_its_persisted_stdio_environment(self) -> None:
        raw = json.dumps(
            {
                "local": {
                    "command": "synthetic-local",
                    "env": {"MODE": "readonly"},
                    "tools": ["local_read"],
                }
            }
        )
        servers = mcp_config.parse_mcp_servers(raw, profile="local")
        first = mcp_config.compose_mcp_servers(servers, replace=True, profile="local")
        with patched_attr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": first.payload}):
            second = mcp_config.compose_mcp_servers([], replace=False, profile="local")

        self.assertEqual(second.payload, first.payload)
        self.assertEqual(second.payload["local"]["env"], ["MODE=readonly"])

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
                        "tools": ["remote_read"],
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
        self.assertEqual(
            config["mcp_servers"][mcp_config.BUILTIN_EVIDENCE_SERVER]["tools"],
            ["ocr_toolkit_evidence"],
        )

    def test_configure_mcp_servers_replaces_stale_servers(self) -> None:
        raw = json.dumps(
            {
                "servers": [
                    {
                        "name": "fresh",
                        "command": "bridge",
                        "tools": ["fresh_read"],
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
                with patched_env(OCR_MCP_SERVERS_JSON=raw, OCR_MCP_REPLACE="true"):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(config_path.read_text(encoding="utf-8"))
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(set(config["mcp_servers"]), {"fresh", mcp_config.BUILTIN_EVIDENCE_SERVER})

    def test_configure_mcp_servers_replaces_external_config_with_builtin(self) -> None:
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
                with patched_env(OCR_MCP_SERVERS_JSON="", OCR_MCP_REPLACE="true"):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(config_path.read_text(encoding="utf-8"))
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(set(config["mcp_servers"]), {mcp_config.BUILTIN_EVIDENCE_SERVER})

    def test_configure_mcp_servers_merges_existing_servers_by_default(self) -> None:
        raw = json.dumps({"local": {"command": "new", "args": [], "tools": ["local_read"]}})
        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            config_path = Path(tmp) / ".opencodereview" / "config.json"
            try:
                config_writer.update_ocr_config(
                    {"mcp_servers": {"stale": {"command": "old", "tools": ["stale_read"]}}}
                )
                with patched_env(OCR_MCP_SERVERS_JSON=raw), cleared_env("OCR_MCP_REPLACE"):
                    exit_code = mcp_config.configure_mcp_servers()
                config = json.loads(config_path.read_text(encoding="utf-8"))
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            set(config["mcp_servers"]),
            {"local", "stale", mcp_config.BUILTIN_EVIDENCE_SERVER},
        )

    def test_configure_native_remote_server_does_not_print_url_or_secret(self) -> None:
        raw = json.dumps(
            {
                "remote": {
                    "type": "remote",
                    "url": "https://mcp.synthetic.invalid/v1?tenant=secret-query",
                    "headers_from": {"Authorization": "SYNTHETIC_MCP_TOKEN"},
                    "tools": ["remote_read"],
                }
            }
        )
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = tmp
            try:
                with (
                    patched_env(
                        OCR_MCP_SERVERS_JSON=raw,
                        SYNTHETIC_MCP_TOKEN="remote-secret-value",
                    ),
                    redirect_stdout(stdout),
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
        self.assertNotIn("secret-query", stdout.getvalue())
        self.assertNotIn("remote-secret-value", stdout.getvalue())
        self.assertEqual(
            config["mcp_servers"]["remote"]["headers"]["Authorization"],
            "$SYNTHETIC_MCP_TOKEN",
        )

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

    def test_config_writer_rejects_oversized_and_linked_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b"x" * config_writer.MAX_OCR_CONFIG_BYTES)
            with self.assertRaisesRegex(config_writer.OCRConfigError, "bounded byte limit"):
                config_writer.read_ocr_config(oversized)

            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            linked = root / "linked.json"
            os.link(target, linked)
            with self.assertRaisesRegex(config_writer.OCRConfigError, "one link"):
                config_writer.read_ocr_config(linked)

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
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.10.2\n", stderr=""
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

    def test_validate_ocr_binary_bounds_execution_and_redacts_failures(self) -> None:
        """Bound OCR version probes and redact timeout and process failures."""

        secret = "binary-secret-value"

        def timeout(*_args: Any, **_kwargs: Any) -> None:
            raise subprocess.TimeoutExpired(["ocr", "--version"], 10, stderr=secret)

        with (
            patched_env(OCR_LLM_TOKEN=secret),
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", timeout),
            self.assertRaises(preflight.PreflightError) as ctx,
        ):
            preflight.validate_ocr_binary()

        self.assertNotIn(secret, str(ctx.exception))
        self.assertIn("Cannot run", str(ctx.exception))

        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=23, stdout="", stderr=secret
        )
        with (
            patched_env(OCR_LLM_TOKEN=secret),
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", lambda *_args, **_kwargs: completed),
            self.assertRaises(preflight.PreflightError) as ctx,
        ):
            preflight.validate_ocr_binary()

        self.assertNotIn(secret, str(ctx.exception))
        self.assertIn("exited 23", str(ctx.exception))

    def test_validate_ocr_binary_rejects_version_prefix_collision(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.7.170\n", stderr=""
        )
        with (
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", lambda *_args, **_kwargs: completed),
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

    def test_request_json_rejects_invalid_headers_before_transport(self) -> None:
        """Reject malformed header names and values before any network call."""

        for headers in ({"Bad Header": "value"}, {"X-Test": "value\r\ninjected"}):
            with (
                self.subTest(headers=headers),
                patched_attr(
                    preflight.URL_OPENER,
                    "open",
                    lambda *_args, **_kwargs: self.fail("invalid header reached transport"),
                ),
                self.assertRaises(preflight.PreflightError, msg=str(headers)),
            ):
                preflight._request_json("https://gateway.example/v1/models", headers)

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

    def test_request_json_crosses_real_local_http_transport_without_credentials(self) -> None:
        requests: list[tuple[str, str | None, str | None]] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                requests.append(
                    (
                        self.path,
                        self.headers.get("Accept"),
                        self.headers.get("User-Agent"),
                    )
                )
                body = b'{"models":["synthetic-model"]}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            payload = preflight._request_json(
                f"http://127.0.0.1:{server.server_port}/v1/models?scope=synthetic",
                {},
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(payload, {"models": ["synthetic-model"]})
        self.assertEqual(
            requests,
            [
                (
                    "/v1/models?scope=synthetic",
                    "application/json",
                    "open-code-review-ci-preflight/1.0",
                )
            ],
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
            OCR_LLM_PROTOCOL="openai-responses",
            OCR_LLM_URL="https://gateway.example/v1/responses",
        ):
            self.assertEqual(preflight._models_url(), "https://gateway.example/v1/models")

    def test_request_json_unit_builds_request_and_redacts_mocked_http_error(self) -> None:
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

    def test_request_json_returns_none_for_empty_and_rejects_malformed_json(self) -> None:
        """Distinguish an empty response from a malformed JSON response."""

        class FakeResponse:
            def __init__(self, body: bytes) -> None:
                self.body = body
                self.sent = False

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, _limit: int) -> bytes:
                if self.sent:
                    return b""
                self.sent = True
                return self.body

        for body, expected in ((b"", None), (b"not-json", preflight.PreflightError)):
            with (
                self.subTest(body=body),
                patched_attr(
                    preflight.URL_OPENER,
                    "open",
                    lambda *_args, value=body, **_kwargs: FakeResponse(value),
                ),
            ):
                if expected is None:
                    self.assertIsNone(
                        preflight._request_json("https://gateway.example/v1/models", {})
                    )
                else:
                    with self.assertRaises(expected):
                        preflight._request_json("https://gateway.example/v1/models", {})

    def test_request_json_deadline_expires_before_transport(self) -> None:
        """Stop an expired request before opening a network connection."""

        ticks = iter((0.0, float(preflight.HTTP_TIMEOUT_SECONDS + 1)))
        with (
            patched_attr(preflight.time, "monotonic", lambda: next(ticks)),
            patched_attr(
                preflight.URL_OPENER,
                "open",
                lambda *_args, **_kwargs: self.fail("expired request reached transport"),
            ),
            self.assertRaisesRegex(preflight.PreflightError, "timed out"),
        ):
            preflight._request_json("https://gateway.example/v1/models", {})

    def test_request_json_retries_bounded_get_failures(self) -> None:
        """Retry transient GET responses within the shared attempt and delay bounds."""

        attempts = 0
        sleeps: list[float] = []

        class FakeResponse:
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
                return b'{"ok":true}'

        def fake_open(request: Any, **_kwargs: Any) -> Any:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    503,
                    "Unavailable",
                    hdrs=None,
                    fp=io.BytesIO(b"temporary"),
                )
            return FakeResponse()

        with (
            patched_attr(preflight.URL_OPENER, "open", fake_open),
            patched_attr(preflight.time, "sleep", sleeps.append),
        ):
            payload = preflight._request_json("https://gateway.example/v1/models", {})

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(attempts, 2)
        self.assertEqual(sleeps, [1.0])

    def test_request_json_retries_transport_failure_only_three_times(self) -> None:
        """Stop transport retries at the fixed bound and redact diagnostics."""

        attempts = 0
        sleeps: list[float] = []
        secret = "transport-secret-value"

        def fake_open(_request: Any, **_kwargs: Any) -> Any:
            nonlocal attempts
            attempts += 1
            raise OSError(f"connection failed token={secret}")

        with (
            patched_env(OCR_LLM_TOKEN=secret),
            patched_attr(preflight.URL_OPENER, "open", fake_open),
            patched_attr(preflight.time, "sleep", sleeps.append),
            self.assertRaises(preflight.PreflightError) as ctx,
        ):
            preflight._request_json("https://gateway.example/v1/models", {})

        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [1.0, 1.0])
        self.assertNotIn(secret, str(ctx.exception))

    def test_validate_gitlab_access_uses_authenticated_identity_and_mr_reads(self) -> None:
        """Validate GitLab access through authenticated identity and MR reads."""

        calls: list[tuple[str, dict[str, str]]] = []

        def fake_request(url: str, headers: dict[str, str]) -> dict[str, Any]:
            calls.append((url, headers))
            return {}

        with (
            patched_env(
                GITLAB_API_TOKEN="gitlab-secret",
                CI_PROJECT_ID="group/project",
                CI_MERGE_REQUEST_IID="17",
                CI_API_V4_URL="https://gitlab.example/api/v4/",
            ),
            patched_attr(preflight, "_request_json", fake_request),
        ):
            preflight.validate_gitlab_access()

        self.assertEqual(
            [url for url, _headers in calls],
            [
                "https://gitlab.example/api/v4/user",
                "https://gitlab.example/api/v4/projects/group%2Fproject",
                "https://gitlab.example/api/v4/projects/group%2Fproject/merge_requests/17",
            ],
        )
        self.assertTrue(
            all(headers == {"PRIVATE-TOKEN": "gitlab-secret"} for _url, headers in calls)
        )

    def test_validate_gitlab_access_requires_token_and_merge_request_identity(self) -> None:
        """Require both authentication and merge-request identity for GitLab access."""

        for values, message in (
            (
                {"GITLAB_API_TOKEN": "", "CI_PROJECT_ID": "7", "CI_MERGE_REQUEST_IID": "9"},
                "GITLAB_API_TOKEN",
            ),
            (
                {"GITLAB_API_TOKEN": "token", "CI_PROJECT_ID": "", "CI_MERGE_REQUEST_IID": ""},
                "CI_PROJECT_ID",
            ),
        ):
            with (
                self.subTest(values=values),
                patched_env(**values),
                self.assertRaisesRegex(preflight.PreflightError, message),
            ):
                preflight.validate_gitlab_access()

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
