"""Bounded provider HTTP properties cover structure rather than one gateway."""

from urllib.parse import urlencode, urlsplit

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.common.provider_http import (
    FORGE_API_USER_AGENT_VARIABLE,
    resolve_forge_api_user_agent,
)
from ocr_toolkit.native_capabilities import require_native_inference_url
from ocr_toolkit.preflight import RECOMMENDED_OCR_VERSION
from ocr_toolkit.provider_config import (
    TERMINAL_ENDPOINTS,
    provider_config_from_environment,
    provider_endpoint_summary,
)


@given(
    st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=1, max_size=256)
)
def test_printable_agent_is_preserved_unless_blank(value):
    if not value.strip():
        with pytest.raises(ValueError):
            resolve_forge_api_user_agent({FORGE_API_USER_AGENT_VARIABLE: value})
    else:
        assert resolve_forge_api_user_agent({FORGE_API_USER_AGENT_VARIABLE: value}) == value


@given(
    st.one_of(
        st.integers(min_value=0, max_value=31), st.integers(min_value=127, max_value=0x10FFFF)
    )
)
def test_control_or_non_ascii_agent_is_rejected_without_echo(codepoint):
    value = "synthetic-" + chr(codepoint) + "-agent"
    with pytest.raises(ValueError) as error:
        resolve_forge_api_user_agent({FORGE_API_USER_AGENT_VARIABLE: value})
    assert value not in str(error.value)


@given(
    st.sampled_from(tuple(TERMINAL_ENDPOINTS)),
    st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=12),
        min_size=1,
        max_size=4,
    ),
    st.booleans(),
)
def test_custom_prefix_is_preserved_for_each_protocol(protocol, segments, terminal):
    prefix = "/" + "/".join(segments) + "/base"
    suffix = TERMINAL_ENDPOINTS[protocol]
    raw = "https://gateway.example.invalid" + prefix + (suffix if terminal else "/")
    provider = provider_config_from_environment({"OCR_LLM_PROTOCOL": protocol, "OCR_LLM_URL": raw})
    assert provider.api_root_url == "https://gateway.example.invalid" + prefix
    assert (
        provider.require_inference_endpoint() == "https://gateway.example.invalid" + prefix + suffix
    )
    assert not provider.defaulted_api_version


@given(
    st.sampled_from(tuple(TERMINAL_ENDPOINTS)),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=40),
)
def test_valid_query_requires_native_support_without_disclosing_values(protocol, value):
    provider = provider_config_from_environment(
        {
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_URL": "https://gateway.example.invalid?tenant=" + value,
        }
    )
    assert provider.require_inference_url().endswith("?tenant=" + value)
    with pytest.raises(ValueError, match="query parameters") as error:
        require_native_inference_url(RECOMMENDED_OCR_VERSION, provider.require_inference_url())
    assert "tenant=" not in str(error.value)
    assert "tenant=" not in provider_endpoint_summary(provider)


@given(
    st.sampled_from(tuple(TERMINAL_ENDPOINTS)),
    st.lists(
        st.tuples(
            st.text(alphabet="abcXYZ012_-", min_size=1, max_size=5),
            st.text(alphabet="abc012 &+=/é漢字", max_size=20),
        ),
        min_size=1,
        max_size=8,
    ),
)
def test_query_normalization_preserves_repeated_empty_and_encoded_values(protocol, items):
    query = urlencode(items)
    suffix = TERMINAL_ENDPOINTS[protocol]
    provider = provider_config_from_environment(
        {
            "OCR_LLM_PROTOCOL": protocol,
            "OCR_LLM_URL": "https://gateway.example.invalid/custom" + suffix + "?" + query,
        }
    )
    assert provider.require_inference_url() == "https://gateway.example.invalid/custom?" + query
    endpoint = urlsplit(provider.require_inference_endpoint())
    assert endpoint.path == "/custom" + suffix
    assert endpoint.query == query
    assert provider.models_url is None
    assert "?" not in provider_endpoint_summary(provider)


@pytest.mark.parametrize("value", (None, True, 1, [], {}))
def test_supplied_nonstring_agent_does_not_select_the_unset_default(value):
    with pytest.raises(ValueError):
        resolve_forge_api_user_agent({FORGE_API_USER_AGENT_VARIABLE: value})
