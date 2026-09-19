"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
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


class RuntimeConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(cleared_env("OCR_USE_ANTHROPIC"))

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

    def test_runtime_config_preserves_explicit_tool_choice_without_defaulting_it(self) -> None:
        """Leave tool selection absent unless the operator explicitly owns it."""

        common = {
            "OCR_LLM_URL": "https://gateway.example/v1/chat/completions",
            "OCR_LLM_TOKEN": "llm-secret",
            "OCR_LLM_MODEL": "openai/gpt-test",
            "OCR_LLM_PROTOCOL": "openai",
        }
        with cleared_env("OCR_LLM_EXTRA_BODY"), patched_env(**common):
            inherited = ocr_configure.build_config_updates()
        with patched_env(**common, OCR_LLM_EXTRA_BODY='{"tool_choice":"auto"}'):
            explicit = ocr_configure.build_config_updates()

        self.assertNotIn("llm.extra_body", inherited)
        self.assertEqual(explicit["llm.extra_body"], {"tool_choice": "auto"})

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
        self.assertIn("Invalid governed MCP registry", stderr.getvalue())


class PreflightTests(unittest.TestCase):
    def test_validate_ocr_binary_accepts_supported_version(self) -> None:
        """Exercise the accepted identity using the production pin owner."""

        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"],
            returncode=0,
            stdout=f"ocr {preflight.EXPECTED_OCR_VERSION}\n",
            stderr="",
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

    def test_validate_ocr_binary_warns_for_exact_deprecated_patch(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.10.2\n", stderr=""
        )
        stderr = io.StringIO()
        with (
            patched_attr(preflight.shutil, "which", lambda _name: "/usr/bin/ocr"),
            patched_attr(preflight.subprocess, "run", lambda *_args, **_kwargs: completed),
            redirect_stderr(stderr),
        ):
            preflight.validate_ocr_binary()
        self.assertIn("deprecated", stderr.getvalue())
        self.assertIn(preflight.RECOMMENDED_OCR_VERSION, stderr.getvalue())

    def test_validate_ocr_binary_rejects_unqualified_patch_in_supported_line(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["ocr", "--version"], returncode=0, stdout="ocr 1.12.99\n", stderr=""
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
