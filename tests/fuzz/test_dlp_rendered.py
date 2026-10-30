"""Metamorphic checks across the actual typed renderer and text DLP boundary."""

import html
import json
import sys

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenValue, _html_decode, check_text
from ocr_toolkit.diagrams.contracts import parse_submission
from ocr_toolkit.reporting.diagram import diagram_mermaid
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission
from tests.fuzz.test_dlp import technical_text
from tests.fuzz.test_dlp_networks import network_text

BUDGETS = TextBudgets(2000, 8000, 30)


def rendered(technical, sensitive, sequence):
    payload = sequence_submission() if sequence else flow_submission()
    elements = payload["diagram"]["participants" if sequence else "nodes"]
    elements[0]["label"] = technical
    if sensitive:
        elements[1]["label"] = sensitive
    submission = parse_submission(payload, expected_range=REVIEW_RANGE)
    return diagram_mermaid(submission.diagram)


@given(
    st.one_of(
        technical_text().filter(lambda text: ": " not in text),
        network_text().map(lambda text: text + "."),
    ),
    st.booleans(),
    st.sampled_from(("plain", "html", "double-html")),
)
def test_actual_renderer_preserves_safe_numeric_technical_values(
    technical, sequence, representation
):
    if representation != "plain":
        technical = html.escape(technical, quote=False)
        if representation == "double-html":
            technical = html.escape(technical, quote=False)
    text = rendered(technical, None, sequence)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted, (technical, sequence, checked.reason, checked.detector)
    assert checked.text == text


@given(
    st.sampled_from(("version < 2020.1.10", "date >= 2020-01-01", "IP 192.0.2.1")),
    st.sampled_from(
        (
            "Call +1 202 555 0142",
            "person@example.invalid",
            'api_key: "synthetic-secret"',
            "Call ::ffff:192.0.2.100/96",
        )
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
    "technical",
    (
        "version\u00a0<\u00a02020.1.10",
        "Decimal('123456789.1234')",
        "network 192.0.2.1/0.255.255.255.",
    ),
)
def test_minimized_renderer_representation_false_positives(technical):
    checked = check_text(rendered(technical, None, False), budgets=BUDGETS, publication=True)
    assert checked.admitted, (technical, checked.detector)


def test_decimal_encoded_letters_cannot_hide_a_phone_already_present_in_the_raw_unit():
    checked = check_text("#65;1234-5678#66;", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


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


@pytest.mark.parametrize(
    "reference", ("&#10;", "&#13;", "&amp;#10;", "#38;#35;10;", "&#" + "0" * 5000 + "10;")
)
def test_numeric_html_newlines_obey_the_same_line_budget_as_plain_text(reference):
    text = "first" + reference + "second"
    checked = check_text(text, budgets=TextBudgets(24000, 96000, 1), publication=True)
    assert not checked.admitted and checked.reason == "limit"
    allowed = check_text(text, budgets=TextBudgets(24000, 96000, 2), publication=True)
    assert allowed.admitted and allowed.text == text


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


@pytest.mark.parametrize("zeros", (4300, 5000, 10000))
@pytest.mark.parametrize(
    "kind,base",
    (("html", 10), ("html", 16), ("mermaid", 10), ("mermaid-html", 10), ("mermaid-html", 16)),
)
def test_long_zero_padded_entity_keeps_contact_detection_without_integer_parse_failure(
    zeros, kind, base
):
    opener = {"html": "&#", "mermaid": "#", "mermaid-html": "#38;#35;"}[kind]
    number = ("x" if base == 16 else "") + "0" * zeros + ("40" if base == 16 else "64")
    text = "person" + opener + number + ";example.invalid"
    integer_limit = sys.get_int_max_str_digits()
    checked = check_text(text, budgets=TextBudgets(24000, 96000, 30), publication=True)
    assert not checked.admitted and checked.reason == "pii"
    assert sys.get_int_max_str_digits() == integer_limit


@pytest.mark.parametrize("digits", ("9" * 5000, "0" * 5000 + "1114112"))
def test_overlong_out_of_range_html_entity_is_a_safe_literal_not_a_parser_crash(digits):
    text = f"Entity &#{digits};"
    checked = check_text(text, budgets=TextBudgets(24000, 96000, 30), publication=True)
    assert checked.admitted and checked.text == text


@given(
    st.one_of(
        st.sampled_from((0, 9, 10, 13, 128, 159, 160, 0xD800, 0xDFFF, 0x10FFFF, 0x110000)),
        st.integers(0, 10**12),
    ),
    st.sampled_from(("", "x", "X")),
    st.integers(0, 32),
    st.booleans(),
    st.booleans(),
)
def test_bounded_html_numbers_preserve_standard_library_scalar_and_legacy_mappings(
    code, hexadecimal, zeros, semicolon, escaped
):
    number = hexadecimal + "0" * zeros + (format(code, "x") if hexadecimal else str(code))
    text = "prefix &#" + number + (";" if semicolon else "") + " suffix"
    if escaped:
        text = html.escape(text)
    assert _html_decode(text) == html.unescape(html.unescape(text))


@given(
    st.text(alphabet="abcXYZéΩ\u0301", min_size=8, max_size=20),
    st.sampled_from(["pass word", "api key", "access token", "client secret"]),
    st.sampled_from(["plain", "html", "double-html", "mermaid", "mermaid-html"]),
    st.booleans(),
)
def test_any_configured_passphrase_survives_supported_representation_order(
    prefix, words, encoding, spaces
):
    secret = prefix + " " + words + " credential"
    if spaces:
        secret = " " + secret + " "
    value = secret
    if encoding in {"html", "double-html", "mermaid-html"}:
        value = "".join(f"&#{ord(char)};" for char in value)
    if encoding == "double-html":
        value = html.escape(value)
    if encoding in {"mermaid", "mermaid-html"}:
        value = "".join(f"#{ord(char)};" for char in value)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("OCR_LLM_TOKEN", secret)
        checked = check_text(value, budgets=TextBudgets(20000, 80000, 30), publication=True)
    assert not checked.admitted and checked.reason == "secret"


@given(
    st.sampled_from(["*", "**", "_", "__", "~", "~~", "`"]),
    st.booleans(),
    st.sampled_from(["", "call ", "phone=", "tel: ", "value: ", "value = "]),
    st.integers(0, 9999),
    st.sampled_from(list(TextSink)),
    st.sampled_from(["plain", "html", "mermaid"]),
)
def test_contacts_survive_matched_and_unmatched_markup_without_labels(
    marker, paired, prefix, tail, sink, encoding
):
    value = prefix + "999 " + marker + "555" + (marker if paired else "") + f"-{tail:04d}"
    if encoding == "html":
        value = "".join(f"&#{ord(char)};" for char in value)
    elif encoding == "mermaid":
        value = "".join(f"#{ord(char)};" for char in value)
    checked = check_text(value, budgets=TextBudgets(20000, 80000, 30), publication=True, sink=sink)
    assert not checked.admitted and checked.reason == "pii"


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=12),
    st.integers(10, 9999),
    st.integers(10, 9999),
    st.sampled_from(["*", " *", "* ", " * ", "**"]),
    st.sampled_from(["*", " *", "* ", " * ", "**"]),
    st.sampled_from(["text", "json", "configuration", "log"]),
    st.sampled_from([TextSink.LITERAL_CODE, TextSink.DIAGRAM_LABEL]),
)
def test_arbitrary_data_does_not_gain_authority_by_parsing_as_numeric_syntax(
    field, left, right, first, second, container, sink
):
    value = f"{field} > 2{first}{left:_}{second}{right:_}"
    if container == "json":
        value = json.dumps({"value": value})
    elif container == "configuration":
        value = "limit: '" + value + "'"
    elif container == "log":
        value = "INFO " + value
    checked = check_text(value, budgets=TextBudgets(20000, 80000, 30), publication=True, sink=sink)
    prose = check_text(value, budgets=TextBudgets(20000, 80000, 30), publication=True)
    assert not checked.admitted or prose.admitted
