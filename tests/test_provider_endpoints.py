"""Provider URL defaults retain explicit routing and precede all preflight I/O."""

from __future__ import annotations

import json
import os
import urllib.request

import pytest

from ocr_toolkit import configure, preflight, review_runner
from ocr_toolkit.native_capabilities import require_native_inference_url
from ocr_toolkit.provider_config import (
    ProviderConfigError,
    provider_config_from_environment,
    provider_endpoint_summary,
    provider_url_notice,
)
from tests.test_gitlab_provider import _GitLabHandler, _https_gitlab


@pytest.fixture
def api_environment(monkeypatch):
    for key in tuple(os.environ):
        if key.startswith("OCR_LLM_") or key in {
            "OCR_ANTHROPIC_DISABLE_THINKING",
            "OCR_USE_ANTHROPIC",
        }:
            monkeypatch.delenv(key)
    values = {
        "OCR_LLM_AUTH_MODE": "api-key",
        "OCR_LLM_URL": "https://llm.example.invalid",
        "OCR_LLM_TOKEN": "synthetic-token",
        "OCR_LLM_MODEL": "synthetic-model",
        "OCR_LLM_PROTOCOL": "openai",
        "OCR_LLM_VALIDATE_MODEL": "false",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


@pytest.mark.parametrize(
    "protocol,root,path,defaulted",
    (
        ("openai", "", "/v1/chat/completions", True),
        ("openai-responses", "/", "/v1/responses", True),
        ("anthropic", "", "/v1/messages", False),
        ("openai", "/v1/", "/v1/chat/completions", False),
        ("openai", "/chat/completions", "/chat/completions", False),
        ("openai-responses", "/responses", "/responses", False),
        ("openai", "/proxy/v2/", "/proxy/v2/chat/completions", False),
        ("openai-responses", "/proxy/v2/responses/", "/proxy/v2/responses", False),
        ("anthropic", "/proxy/v1/messages", "/proxy/v1/messages", False),
        ("anthropic", "/proxy/v2/", "/proxy/v2/v1/messages", False),
    ),
)
def test_protocol_root_and_explicit_endpoint_handoff(
    api_environment, monkeypatch, capsys, protocol, root, path, defaulted
):
    origin = "https://llm.example.invalid"
    monkeypatch.setenv("OCR_LLM_PROTOCOL", protocol)
    monkeypatch.setenv("OCR_LLM_URL", origin + root)
    provider = provider_config_from_environment()
    assert provider.require_inference_endpoint() == origin + path
    assert provider.defaulted_api_version is defaulted
    assert (provider_url_notice(provider) is not None) is defaulted
    updates = configure.build_config_updates()
    assert updates["llm.url"] == provider.inference_url
    assert configure.build_config_updates() == updates
    output = capsys.readouterr()
    assert ("WARNING:" in output.err) is defaulted
    if defaulted:
        assert provider.api_root_url in output.err


@pytest.mark.parametrize("protocol", ("openai", "openai-responses", "anthropic"))
def test_query_is_valid_data_but_requires_native_capability(protocol):
    provider = provider_config_from_environment(
        {
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_URL": "https://llm.example.invalid?access_key=synthetic-private-value",
        }
    )
    assert provider.require_inference_url().endswith("?access_key=synthetic-private-value")
    with pytest.raises(ValueError, match="query parameters") as error:
        require_native_inference_url(
            preflight.RECOMMENDED_OCR_VERSION, provider.require_inference_url()
        )
    assert "access_key" not in str(error.value)
    assert "synthetic-private-value" not in str(error.value)
    assert "access_key" not in provider_endpoint_summary(provider)


@pytest.mark.parametrize("missing", ("OCR_LLM_URL", "OCR_LLM_TOKEN", "OCR_LLM_MODEL"))
def test_missing_api_input_is_rejected_before_binary_or_http(
    api_environment, monkeypatch, capsys, missing
):
    monkeypatch.delenv(missing)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid configuration reached external I/O")

    monkeypatch.setattr(preflight, "validate_ocr_binary", forbidden)
    monkeypatch.setattr(preflight, "validate_gitlab_access", forbidden)
    monkeypatch.setattr(preflight, "_request_json", forbidden)
    assert preflight.main() == 1
    assert missing in capsys.readouterr().err


def test_preflight_reuses_one_provider_and_does_not_probe_inference(
    api_environment, monkeypatch, capsys
):
    calls = []
    factory = provider_config_from_environment

    def build():
        provider = factory()
        calls.append(provider)
        return provider

    def forbidden(*args, **kwargs):
        raise AssertionError("disabled metadata validation sent an HTTP request")

    monkeypatch.setattr(preflight, "provider_config_from_environment", build)
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: preflight.RECOMMENDED_OCR_VERSION)
    monkeypatch.setattr(preflight, "_request_json", forbidden)
    assert preflight.main(local=True) == 0
    assert len(calls) == 1
    output = capsys.readouterr()
    assert "base=https://llm.example.invalid/v1" in output.out
    assert "inference=https://llm.example.invalid/v1/chat/completions" in output.out
    assert output.err.count("WARNING:") == 1


def test_preflight_rejects_unsupported_native_query_before_forge_or_metadata(
    api_environment, monkeypatch, capsys
):
    monkeypatch.setenv("OCR_LLM_URL", "https://llm.example.invalid/v1?private=synthetic-value")
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: preflight.RECOMMENDED_OCR_VERSION)

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported native routing reached HTTP")

    monkeypatch.setattr(preflight, "validate_gitlab_access", forbidden)
    monkeypatch.setattr(preflight, "validate_llm_model", forbidden)
    assert preflight.main() == 1
    output = capsys.readouterr()
    assert "query parameters" in output.err
    assert "private=" not in output.err + output.out
    assert "synthetic-value" not in output.err + output.out


def test_runner_gates_query_before_writing_isolated_config(api_environment, monkeypatch):
    monkeypatch.setenv("OCR_LLM_URL", "https://llm.example.invalid/v1?private=synthetic-value")
    monkeypatch.setattr(review_runner, "_resolve_ocr_binary", lambda: "/synthetic/ocr")
    monkeypatch.setattr(
        preflight, "validate_ocr_binary", lambda **kwargs: preflight.RECOMMENDED_OCR_VERSION
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported native routing was written or launched")

    monkeypatch.setattr(review_runner, "update_ocr_config", forbidden)
    with pytest.raises(review_runner.ReviewRunnerError, match="query parameters"):
        review_runner._write_isolated_runtime_config(local=True)


@pytest.mark.parametrize(
    "url",
    (
        "https://user:synthetic-private-value@llm.example.invalid",
        "https://llm.example.invalid/#synthetic-private-value",
        "http://llm.example.invalid",
    ),
)
def test_unsafe_url_is_not_repaired_or_echoed(url):
    with pytest.raises(ProviderConfigError) as error:
        provider_config_from_environment({"OCR_LLM_URL": url})
    assert "synthetic-private-value" not in str(error.value)


def test_explicit_metadata_endpoint_and_custom_root_are_preserved():
    provider = provider_config_from_environment(
        {
            "OCR_LLM_PROTOCOL": "openai-responses",
            "OCR_LLM_URL": "https://llm.example.invalid/custom/responses",
            "OCR_LLM_MODELS_URL": "https://metadata.example.invalid/catalog?tenant=synthetic",
        }
    )
    assert provider.require_inference_url() == "https://llm.example.invalid/custom"
    assert (
        provider.require_models_url() == "https://metadata.example.invalid/catalog?tenant=synthetic"
    )
    assert "tenant" not in provider_endpoint_summary(provider)
    assert not provider.defaulted_api_version


@pytest.mark.parametrize(
    "payload,error",
    (
        (
            {
                "data": [
                    {
                        "id": "synthetic-model",
                        "context_length": "unknown",
                        "contextLength": {},
                        "max_context_length": 2048,
                    }
                ]
            },
            None,
        ),
        ({"data": {}}, "not a model list"),
        ({"data": [{"id": "different-model"}]}, "not found"),
    ),
)
def test_metadata_query_and_shape_cross_real_preflight_tls(
    api_environment, tmp_path, monkeypatch, capsys, payload, error
):
    seen = []

    def respond(peer):
        seen.append(peer.path)
        body = json.dumps(payload).encode()
        peer.send_response(200)
        peer.send_header("Content-Length", str(len(body)))
        peer.end_headers()
        peer.wfile.write(body)

    monkeypatch.setattr(_GitLabHandler, "do_GET", respond)
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: preflight.RECOMMENDED_OCR_VERSION)
    with _https_gitlab(tmp_path) as root:
        monkeypatch.setattr(
            preflight, "URL_OPENER", urllib.request.build_opener(preflight._NoRedirectHandler)
        )
        monkeypatch.setenv("OCR_LLM_VALIDATE_MODEL", "true")
        monkeypatch.setenv("OCR_LLM_MODELS_URL", root + "/catalog?tenant=synthetic")
        assert preflight.main(local=True) == (1 if error else 0)
    assert seen == ["/api/v4/catalog?tenant=synthetic"]
    output = capsys.readouterr()
    assert "tenant=" not in output.err + output.out
    if error:
        assert error in output.err
    else:
        assert "context_length=2048" in output.out


@pytest.mark.parametrize("output", ("ocr development", "ocr 0.0.0 and 0.0.1"))
def test_binary_identity_requires_one_unambiguous_stable_version(tmp_path, output):
    binary = tmp_path / "ocr"
    binary.write_text("#!/bin/sh\nprintf '%s\\n' '" + output + "'\n")
    binary.chmod(0o700)
    with pytest.raises(preflight.PreflightError, match="expected one qualified stable version"):
        preflight.validate_ocr_binary(executable=str(binary))


@pytest.mark.parametrize("mode", ("auto", "true"))
def test_metadata_derivation_has_explicit_offline_fallback(api_environment, monkeypatch, mode):
    monkeypatch.delenv("OCR_LLM_URL")
    monkeypatch.setenv("OCR_LLM_VALIDATE_MODEL", mode)
    monkeypatch.setenv("OCR_LLM_ALLOWED_MODELS", "synthetic-model")
    if mode == "auto":
        preflight.validate_llm_model()
    else:
        with pytest.raises(preflight.PreflightError, match="OCR_LLM_MODELS_URL"):
            preflight.validate_llm_model()


def test_preflight_url_diagnostics_never_render_userinfo_query_or_fragment():
    assert (
        preflight._safe_url(
            "https://synthetic-user:private-value@gateway.example.invalid/catalog?custom=private-value#private-value"
        )
        == "https://gateway.example.invalid/catalog"
    )
    assert preflight._safe_url("https://[private-value") == "<invalid URL>"
