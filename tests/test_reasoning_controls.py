"""Protocol-specific reasoning overlays share configure and preflight validation."""

import json

import pytest

from ocr_toolkit import configure, preflight
from ocr_toolkit.provider_config import ProviderConfigError, request_controls_from_environment


@pytest.mark.parametrize("protocol", ["openai", "openai-responses"])
@pytest.mark.parametrize("effort", ["none", "minimal", "low", "medium", "high", "xhigh", "max"])
def test_explicit_effort_is_normalized_and_mapped(protocol: str, effort: str) -> None:
    controls = request_controls_from_environment(
        {
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_REASONING_EFFORT": " " + effort.upper() + " ",
        }
    )
    expected = (
        {"reasoning_effort": effort} if protocol == "openai" else {"reasoning": {"effort": effort}}
    )
    assert controls.extra_body == expected


@pytest.mark.parametrize("value", [None, "", "  "])
@pytest.mark.parametrize("protocol", ["openai", "openai-responses", "anthropic"])
def test_unset_effort_does_not_add_an_overlay(protocol: str, value: str | None) -> None:
    environment = {"OCR_LLM_PROTOCOL": protocol}
    if value is not None:
        environment["OCR_LLM_REASONING_EFFORT"] = value
    assert request_controls_from_environment(environment).extra_body is None
    environment["OCR_LLM_EXTRA_BODY"] = '{"vendor_field":true}'
    assert request_controls_from_environment(environment).extra_body == {"vendor_field": True}


@pytest.mark.parametrize("protocol", ["openai", "openai-responses"])
def test_equal_overlay_preserves_siblings_and_completion_cap(protocol: str) -> None:
    body = (
        {"temperature": 0, "reasoning_effort": "none"}
        if protocol == "openai"
        else {"temperature": 0, "reasoning": {"effort": "none", "summary": "auto", "mode": "pro"}}
    )
    expected = {
        **body,
        ("max_completion_tokens" if protocol == "openai" else "max_output_tokens"): 4096,
    }
    controls = request_controls_from_environment(
        {
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_REASONING_EFFORT": "none",
            "OCR_LLM_EXTRA_BODY": json.dumps(body),
            "OCR_LLM_MAX_COMPLETION_TOKENS": "4096",
        }
    )
    assert controls.extra_body == expected


@pytest.mark.parametrize("conflict", [None, False, 0, 1.0, [], {}, "low", "NONE"])
@pytest.mark.parametrize("protocol", ["openai", "openai-responses"])
def test_conflicting_existing_effort_is_rejected(protocol: str, conflict: object) -> None:
    body = (
        {"reasoning_effort": conflict}
        if protocol == "openai"
        else {"reasoning": {"effort": conflict}}
    )
    with pytest.raises(ProviderConfigError, match="conflicts"):
        request_controls_from_environment(
            {
                "OCR_LLM_PROTOCOL": protocol,
                "OCR_LLM_REASONING_EFFORT": "none",
                "OCR_LLM_EXTRA_BODY": json.dumps(body),
            }
        )


@pytest.mark.parametrize("reasoning", [None, False, 1, [], "none"])
def test_responses_reasoning_must_be_an_object(reasoning: object) -> None:
    with pytest.raises(ProviderConfigError, match="must be an object"):
        request_controls_from_environment(
            {
                "OCR_LLM_PROTOCOL": "openai-responses",
                "OCR_LLM_REASONING_EFFORT": "none",
                "OCR_LLM_EXTRA_BODY": json.dumps({"reasoning": reasoning}),
            }
        )


@pytest.mark.parametrize("value", ["none", "high"])
def test_anthropic_rejects_nonempty_shortcut(value: str) -> None:
    with pytest.raises(ProviderConfigError, match="not supported with anthropic"):
        request_controls_from_environment(
            {
                "OCR_LLM_PROTOCOL": "anthropic",
                "OCR_LLM_REASONING_EFFORT": value,
            }
        )


def test_invalid_effort_does_not_echo_operator_value() -> None:
    with pytest.raises(ProviderConfigError) as error:
        request_controls_from_environment({"OCR_LLM_REASONING_EFFORT": "private-unsupported-value"})
    assert "private-unsupported-value" not in str(error.value)


def test_configure_and_disabled_model_preflight_share_conflict_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "OCR_LLM_URL": "https://provider.example.invalid/v1",
        "OCR_LLM_MODEL": "synthetic-model",
        "OCR_LLM_TOKEN": "synthetic-token",
        "OCR_LLM_PROTOCOL": "openai",
        "OCR_LLM_VALIDATE_MODEL": "false",
        "OCR_LLM_REASONING_EFFORT": "none",
        "OCR_LLM_EXTRA_BODY": '{"reasoning_effort":"high"}',
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(configure.OCRRuntimeConfigError, match="conflicts"):
        configure.build_config_updates()
    with pytest.raises(preflight.PreflightError, match="conflicts"):
        preflight.validate_llm_model()
