"""Metamorphic checks across the actual typed renderer and text DLP boundary."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenValue, check_text
from ocr_toolkit.diagrams.contracts import parse_submission
from ocr_toolkit.reporting.diagram import diagram_mermaid
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission
from tests.fuzz.test_dlp import technical_text

BUDGETS = TextBudgets(2000, 8000, 30)


def rendered(technical, sensitive, sequence):
    payload = sequence_submission() if sequence else flow_submission()
    elements = payload["diagram"]["participants" if sequence else "nodes"]
    elements[0]["label"] = technical
    if sensitive:
        elements[1]["label"] = sensitive
    submission = parse_submission(payload, expected_range=REVIEW_RANGE)
    return diagram_mermaid(submission.diagram)


@given(technical_text().filter(lambda text: ": " not in text), st.booleans())
def test_actual_renderer_preserves_safe_numeric_technical_values(technical, sequence):
    text = rendered(technical, None, sequence)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted, (technical, sequence, checked.reason, checked.detector)
    assert checked.text == text


@given(
    st.sampled_from(("version < 2020.1.10", "date >= 2020-01-01", "IP 192.0.2.1")),
    st.sampled_from(
        ("Call +1 202 555 0142", "person@example.invalid", 'api_key: "synthetic-secret"')
    ),
    st.booleans(),
)
def test_actual_renderer_cannot_hide_contacts_or_secrets_next_to_technical_values(
    technical, sensitive, sequence
):
    checked = check_text(
        rendered(technical, sensitive, sequence), budgets=BUDGETS, publication=True
    )
    assert not checked.admitted and checked.reason in {"pii", "secret"}


@pytest.mark.parametrize(
    "technical", ("version\u00a0<\u00a02020.1.10", "Decimal('123456789.1234')")
)
def test_minimized_renderer_representation_false_positives(technical):
    checked = check_text(rendered(technical, None, False), budgets=BUDGETS, publication=True)
    assert checked.admitted, (technical, checked.detector)


@pytest.mark.parametrize("sensitive", ("person@example.invalid", 'api_key: "synthetic-secret"'))
def test_minimized_renderer_representation_sensitive_regressions(sensitive):
    text = rendered("version < 2020.1.10", sensitive, False)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason in {"pii", "secret"}


@pytest.mark.parametrize(
    "text",
    (
        "Literal #35;8238#59;",
        "Issue #123456789;",
        "Unknown #1114112;",
        "Unknown #55296;",
        "Version #060; 2020.1.10",
    ),
)
def test_literal_hashes_invalid_scalars_and_decimal_padding_do_not_create_false_positives(text):
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == text


@pytest.mark.parametrize("code", (0, 27, 8238, 8203, 65039))
def test_decimal_encoded_controls_are_not_normalized_away(code):
    checked = check_text(f"value #{code};", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason in {"invalid_text", "laundering"}


def test_decimal_encoded_line_budget_is_independent_of_the_raw_line_count():
    checked = check_text("first#10;second", budgets=TextBudgets(100, 400, 1), publication=True)
    assert not checked.admitted and checked.reason == "limit" and checked.detector == "lines"


def test_decimal_encoded_protected_content_keeps_its_forbidden_source_attribution():
    forbidden = ForbiddenValue("A protected synthetic repository sentence", "external_context")
    text = "".join(f"#{ord(c)};" for c in forbidden.value)
    checked = check_text(text, budgets=BUDGETS, publication=True, forbidden=(forbidden,))
    assert not checked.admitted and checked.reason == "forbidden"
    assert checked.source_classes == ("external_context",)


@pytest.mark.parametrize(
    "text", ('login_password: ""', "'login_password': '{{ service_password }}'")
)
def test_decimal_encoded_empty_or_template_credentials_preserve_the_exact_safe_grammar(text):
    encoded = "".join(f"#{ord(c)};" for c in text)
    checked = check_text(encoded, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == encoded


def test_plain_and_decimal_encoded_forbidden_sources_are_reconciled_together():
    plain = ForbiddenValue("A plain protected synthetic sentence", "forge_discussions")
    encoded = ForbiddenValue("A different protected synthetic sentence", "external_context")
    text = plain.value + "; " + "".join(f"#{ord(c)};" for c in encoded.value)
    checked = check_text(text, budgets=BUDGETS, publication=True, forbidden=(plain, encoded))
    assert not checked.admitted and checked.reason == "forbidden"
    assert checked.source_classes == ("external_context", "forge_discussions")


@pytest.mark.parametrize("value", ("synthetic-operator-token-value", 'login_password: ""'))
def test_decimal_encoded_environment_values_keep_priority_over_safe_reference_grammar(
    monkeypatch, value
):
    monkeypatch.setenv("OCR_LLM_TOKEN", value)
    text = "".join(f"#{ord(c)};" for c in value)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "secret" and checked.detector == "mermaid"
