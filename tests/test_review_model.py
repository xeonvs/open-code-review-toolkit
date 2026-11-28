"""Bind public model identity to trusted review selection and independent DLP admission."""

import json

import pytest

from ocr_toolkit import review_analysis, review_runner
from ocr_toolkit.context.dlp import ForbiddenValue
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.ocr_result import load_ocr_result
from ocr_toolkit.posting.formatting import summarize_result
from ocr_toolkit.review_model import admitted_model
from ocr_toolkit.review_receipt import toolkit_receipt_is_valid
from tests.test_review_analysis import REPORT_TEXT, _combined
from tests.test_review_receipt_v11 import _receipt_v11
from tests.test_review_runner import (
    BUILTIN_EVIDENCE_TOOLS,
    DEFAULT_IDENTITY,
    SUMMARY_ACTION_COUNTS,
    complete_review_payload,
)


@pytest.mark.parametrize(
    ("model", "admitted"),
    [
        ("openai/gpt-5.4", True),
        ("Qwen/Qwen3-235B-A22B:free", True),
        ("https://models.example.invalid/v1", False),
        ("https:example", False),
        ("eyJabc.def.ghi", False),
        ("../private/model", False),
        ("alice@example.invalid", False),
        ("sk-synthetic-model-key", False),
        ("private-tenant-model", False),
        ("model\n- Review model v1", False),
        ("a" * 129, False),
        ("a" * 48, False),
        (None, False),
    ],
)
def test_model_admission_keeps_only_closed_public_names(model, admitted):
    assert (admitted_model(model) is not None) is admitted


@pytest.mark.parametrize(
    ("native", "configured", "forbidden", "expected"),
    [
        ("openai/gpt-5.4", "openai/gpt-5.4", (), "openai/gpt-5.4"),
        ("gateway/another-model", "openai/gpt-5.4", (), None),
        ("openai/gpt-5.4", None, (), None),
        (None, "openai/gpt-5.4", (), None),
        (
            "tenant/alpha",
            "tenant/alpha",
            (ForbiddenValue("tenant/alpha", "external_context"),),
            None,
        ),
        ("https://private.invalid/v1", "https://private.invalid/v1", (), None),
        ("claude-sonnet-4-5-20250929", "claude-sonnet-4-5-20250929", (), None),
    ],
)
def test_finalized_public_model_requires_matching_native_and_config(
    tmp_path, native, configured, forbidden, expected
):
    payload = complete_review_payload(
        tool_calls={"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}
    )
    if native:
        payload["llm"] = {"model": native}
    payload["summary"] = {"model": "forged-summary-model"}
    result = tmp_path / "review.json"
    result.write_text(json.dumps(payload))
    composition = MCPComposition(
        {}, (MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),), (), ()
    )
    review_runner._finalize_ocr_result(
        result,
        composition,
        DEFAULT_IDENTITY,
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=forbidden,
        configured_model=configured,
    )
    finalized = load_ocr_result(result)
    assert finalized["comments"] == payload["comments"]
    receipt = finalized["_ocr_toolkit"]
    assert toolkit_receipt_is_valid(receipt)
    assert receipt.get("review_model") == expected
    lines = summarize_result(0, 0, 0, 0, review_model=receipt.get("review_model")).splitlines()
    assert [line for line in lines if line.startswith("- Review model v1:")] == (
        [f"- Review model v1: `{expected}`"] if expected else []
    )


def test_historical_receipts_keep_exact_model_free_schema():
    receipt = _receipt_v11()
    assert toolkit_receipt_is_valid(receipt)
    receipt["review_model"] = "openai/gpt-5.4"
    assert not toolkit_receipt_is_valid(receipt)


def test_secret_value_in_the_post_environment_omits_only_the_optional_line(monkeypatch):
    monkeypatch.setenv("OCR_LLM_TOKEN", "public-looking-model")
    message = summarize_result(0, 0, 0, 0, review_model="public-looking-model")
    assert "- Review model v1:" not in message
    assert "<summary>Technical details</summary>" in message


@pytest.mark.parametrize("filtered", (False, True))
def test_model_identity_yields_to_requested_analysis_at_handoff_limit(
    tmp_path, monkeypatch, filtered
):
    result = tmp_path / "result.json"
    model = "openai/gpt-5.4"
    payload = complete_review_payload(
        tool_calls={"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}
    )
    payload.update(_combined())
    payload["llm"] = {"model": model, "diagnostic": "native-only diagnostic"}
    if filtered:
        payload["warnings"] = ["synthetic protected warning"]
    composition = MCPComposition(
        {}, (MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),), (), ()
    )

    def finalize(configured_model):
        result.write_text(json.dumps(payload))
        review_runner._finalize_ocr_result(
            result,
            composition,
            DEFAULT_IDENTITY,
            None,
            SUMMARY_ACTION_COUNTS,
            forbidden=("synthetic protected warning",),
            analysis_requested=True,
            configured_model=configured_model,
        )
        return load_ocr_result(result)

    expected = finalize(None)
    assert expected[review_analysis.PRIVATE_RESULT_KEY]["markdown"] == REPORT_TEXT
    assert expected["comments"] == payload["comments"]
    budget = result.stat().st_size
    with_model = finalize(model)
    assert with_model["_ocr_toolkit"]["review_model"] == model
    if filtered:
        assert with_model["_ocr_toolkit"]["publication"]["state"] == "publication-filtered"
        assert with_model["llm"] == {"model": model}
    monkeypatch.setenv("OCR_MAX_RESULT_BYTES", str(budget))
    assert finalize(model) == expected
