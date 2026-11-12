"""Environment-to-native URL routing through the real config writer and TLS peer."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit import configure, preflight
from ocr_toolkit.config_writer import update_ocr_config
from tests.test_gitlab_provider import _GitLabHandler, _https_gitlab
from tests.test_ocr_compat import load_script


@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="native Go trusts the private SSL_CERT_FILE fixture on Linux, not macOS Keychain",
)
@pytest.mark.parametrize(
    "protocol,raw_path,expected_path",
    (
        ("openai", "", "/v1/chat/completions"),
        ("openai-responses", "", "/v1/responses"),
        ("anthropic", "", "/v1/messages"),
        ("openai", "/chat/completions", "/chat/completions"),
        ("openai-responses", "/responses", "/responses"),
        ("openai", "/gateway/v2", "/gateway/v2/chat/completions"),
        ("anthropic", "/gateway/v1/messages", "/gateway/v1/messages"),
    ),
)
def test_preflight_configure_and_native_agree_on_endpoint(
    tmp_path: Path, monkeypatch, qualified_native_ocr, protocol, raw_path, expected_path
):
    binary, _version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    module = load_script()
    env = module.execution._isolated_probe_environment(tmp_path / "home")
    repo, base, head = module.execution._synthetic_repo(tmp_path, env)
    observed = []

    def capture_request(handler):
        size = int(handler.headers.get("Content-Length", "0"))
        assert 0 < size <= 1024 * 1024
        assert len(observed) < 12
        request = json.loads(handler.rfile.read(size))
        observed.append((handler.path, handler.headers.get("Authorization"), request.get("model")))
        # Fail after capture: this proves routing without invoking any real model.
        handler.send_response(400)
        handler.send_header("Content-Length", "2")
        handler.end_headers()
        handler.wfile.write(b"{}")

    monkeypatch.setattr(_GitLabHandler, "do_POST", capture_request, raising=False)
    with _https_gitlab(tmp_path / "tls") as api_url:
        origin = api_url.removesuffix("/api/v4")
        values = {
            "OCR_LLM_AUTH_MODE": "api-key",
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_URL": origin + raw_path,
            "OCR_LLM_TOKEN": "synthetic-token",
            "OCR_LLM_MODEL": "synthetic-model",
            "OCR_LLM_VALIDATE_MODEL": "false",
        }
        for key in tuple(os.environ):
            if key.startswith("OCR_LLM_") or key in {
                "OCR_USE_ANTHROPIC",
                "OCR_ANTHROPIC_DISABLE_THINKING",
            }:
                monkeypatch.delenv(key)
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        provider = preflight.validate_llm_configuration()
        assert provider.require_inference_endpoint() == origin + expected_path
        config_path = Path(env["HOME"]) / ".opencodereview" / "config.json"
        update_ocr_config(configure.build_config_updates(local=True), config_path)
        env["SSL_CERT_FILE"] = str(tmp_path / "tls" / "cert.pem")
        completed = subprocess.run(
            [
                binary,
                "review",
                "--from",
                base,
                "--to",
                head,
                "--format",
                "json",
                "--audience",
                "agent",
                "--effort",
                "low",
                "--concurrency",
                "1",
            ],
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            timeout=30,
        )
    assert completed.returncode >= 0, completed.stderr.decode(errors="replace")
    assert observed, completed.stderr.decode(errors="replace")
    assert all(
        item == (expected_path, "Bearer synthetic-token", "synthetic-model") for item in observed
    ), observed
