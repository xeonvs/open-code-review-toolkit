"""Exercise DLP grammars and whole-unit safety independently of model/provider calls."""

from __future__ import annotations

import html
import unicodedata
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text, normalize_text

BUDGETS = TextBudgets(2000, 8000, 30)
COMPARISONS = st.sampled_from(
    (
        " ",
        "<",
        " <= ",
        " > ",
        ">=",
        " == ",
        " != ",
        " = ",
        " ≤ ",
        " ≥ ",
        " ≠ ",
        "\u00a0<\u00a0",
        "\u202f>=\u202f",
    )
)


@st.composite
def mermaid_comparison(draw: st.DrawFn) -> str:
    """Vary comparison syntax independently of the detector and renderer."""

    is_date = draw(st.booleans())
    prefix = (
        draw(st.sampled_from(("date", "expires on", "since")))
        if is_date
        else draw(st.sampled_from(("version", "release", "build", "pin", "VERSION")))
    )
    operator = draw(
        st.sampled_from(
            (
                "<",
                "<=",
                ">",
                ">=",
                "==",
                "!=",
                "=",
                "≤",
                "≥",
                "≠",
                "\uff1c\uff1d",
                "\uff1e\uff1d",
                "\uff1d\uff1d",
                "\uff01\uff1d",
                "﹤﹦",
                "﹥﹦",
                "﹦﹦",
                "﹗﹦",
            )
        )
    )
    encoded = draw(st.lists(st.booleans(), min_size=len(operator), max_size=len(operator)))
    operator = "".join(
        f"#{ord(character)};" if encode else character
        for character, encode in zip(operator, encoded, strict=True)
    )
    space = draw(st.sampled_from(("", " ", "  ", "\u00a0", "\u202f")))
    if is_date:
        value = str(draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))))
    else:
        value = ".".join(
            str(draw(st.integers(low, high))) for low, high in ((2020, 2030), (0, 99), (0, 999))
        )
    return f"{prefix}{space}{operator}{space}{value}"


@given(
    mermaid_comparison(),
    st.sampled_from((("", ""), ("`", "`"), ("**", "**"), ('n0 -->|"', '"| n1'))),
    st.sampled_from(("plain", "escaped", "double-escaped", "entities")),
    st.booleans(),
)
def test_mermaid_technical_comparisons_survive_whole_text_checks(
    value: str, wrapper: tuple[str, str], representation: str, publication: bool
) -> None:
    text = display_representation(wrapper[0] + value + wrapper[1], representation)
    checked = check_text(text, budgets=BUDGETS, publication=publication)
    assert checked.admitted, (text, checked.reason, checked.detector)
    assert checked.text == text


@given(
    mermaid_comparison(),
    st.sampled_from(
        (
            "Call +1 202 555 0142",
            "Call +1.202.555.0142",
            "person@example.invalid",
            "person&#64;example.invalid",
            'login_password: "synthetic-secret-value"',
        )
    ),
    st.sampled_from(("; ", "\n", " | ")),
    st.booleans(),
)
def test_mermaid_comparison_does_not_exempt_mixed_contacts_or_secrets(
    technical: str, sensitive: str, separator: str, prepend: bool
) -> None:
    text = sensitive + separator + technical if prepend else technical + separator + sensitive
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason in {"pii", "secret"}


@pytest.mark.parametrize(
    "operator",
    (
        "#60;",
        "#60;#61;",
        "#62;",
        "#62;#61;",
        "#61;#61;",
        "#33;#61;",
        "#61;",
        "#8804;",
        "#8805;",
        "#8800;",
        "#65308;#65309;",
        "#65310;#65309;",
        "#65309;#65309;",
        "#65281;#65309;",
        "#65124;#65126;",
        "#65125;#65126;",
        "#65126;#65126;",
        "#65111;#65126;",
    ),
)
@pytest.mark.parametrize("prefix,value", (("version", "2020.1.10"), ("date", "2020-01-01")))
def test_mermaid_comparison_minimized_false_positive(prefix, value, operator) -> None:
    text = f"Expected `{prefix} {operator} {value}` on the rendered edge."
    assert check_text(text, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("operator", ("#60", "#0x3c;", "#59;", "#33;", "#61;#61;#61;", "#60;#62;"))
def test_unknown_or_malformed_mermaid_comparison_is_not_an_exception(operator) -> None:
    checked = check_text(f"version {operator} 2020.1.10", budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "pii"


@given(
    st.integers(0, 0x10FFFF).filter(
        lambda code: (
            unicodedata.normalize("NFKC", chr(code))
            not in {"<", "<=", ">", ">=", "=", "==", "!=", "≤", "≥", "≠"}
            and not unicodedata.normalize("NFKC", chr(code)).isspace()
        )
    ),
    st.sampled_from(("version", "date")),
    st.booleans(),
)
def test_other_mermaid_entities_cannot_create_technical_context(code, prefix, publication) -> None:
    value = "2020.1.10" if prefix == "version" else "2020-01-01"
    checked = check_text(f"{prefix} #{code}; {value}", budgets=BUDGETS, publication=publication)
    assert not checked.admitted and checked.reason in {"pii", "invalid_text", "laundering"}


@pytest.mark.parametrize("spaces,admitted", ((0, True), (52, True), (53, False), (512, False)))
def test_mermaid_comparison_cannot_expand_the_bounded_prefix(spaces, admitted) -> None:
    checked = check_text(
        "version" + " " * spaces + "#60; 2020.1.10", budgets=BUDGETS, publication=True
    )
    assert checked.admitted is admitted


@given(mermaid_comparison(), st.sampled_from(("login_password", "api_key", "access_token")))
def test_mermaid_comparisons_never_exempt_secret_values_or_forbidden_units(value, key) -> None:
    checked = check_text(f'{key}: "{value}"', budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "secret"
    forbidden = check_text(value, budgets=BUDGETS, publication=True, forbidden=(value,))
    assert not forbidden.admitted and forbidden.reason == "forbidden"


@given(mermaid_comparison(), st.sampled_from(("\x00", "\x1b", "\u202e", "\u200b", "\ud800")))
def test_mermaid_comparisons_do_not_hide_controls(value, control) -> None:
    checked = check_text(value + control, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "invalid_text"


@pytest.mark.parametrize("count", (2, 16, 400, 1000))
def test_long_mermaid_near_match_remains_bounded_and_is_not_a_comparison(count) -> None:
    checked = check_text(
        "version " + "#60;" * count + "2020.1.10", budgets=BUDGETS, publication=True
    )
    assert not checked.admitted and checked.reason == ("limit" if count == 1000 else "pii")


@pytest.mark.parametrize(
    "text", ("version < 2020.1.10/docs", "date < 2020-01-01/notes", "IP 192.0.2.100/help")
)
def test_nonnumeric_path_suffix_is_not_misclassified_as_a_cidr_mask(text):
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text == text


@st.composite
def technical_text(draw: st.DrawFn) -> str:
    """Construct parsed-safe technical values without reusing the detector regex."""

    kind = draw(
        st.sampled_from(("version", "date", "ip", "cidr", "port", "decimal", "id", "reference"))
    )
    if kind == "version":
        prefix = draw(st.sampled_from(("version", "release", "build", "pin", "VERSION")))
        value = ".".join(
            str(draw(st.integers(low, high))) for low, high in ((2020, 2030), (0, 99), (0, 999))
        )
        return prefix + draw(COMPARISONS) + value
    if kind == "date":
        prefix = draw(st.sampled_from(("date", "expires on", "until", "since")))
        value = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
        return prefix + draw(COMPARISONS) + value.isoformat()
    if kind in {"ip", "cidr", "port"}:
        address = f"192.0.2.{draw(st.integers(1, 254))}"
        if kind == "port":
            return f"IP {address}:{draw(st.integers(1, 65535))}"
        return f"IP {address}" if kind == "ip" else f"network {address}/{draw(st.integers(0, 32))}"
    if kind == "decimal":
        integer = draw(st.integers(100_000_000, 999_999_999))
        fraction = draw(st.integers(1000, 9999))
        quote = draw(st.sampled_from(("'", '"')))
        return f"Decimal({quote}{integer}.{fraction}{quote})"
    if kind == "id":
        return f"request_id == {draw(st.integers(100_000_000, 999_999_999_999_999))}"
    key = draw(st.sampled_from(("login_password", '"login_password"', "'login_password'")))
    value = draw(st.sampled_from(('"{{ service_password }}"', "''", '""')))
    return f"{key}: {value}"


@given(technical_text(), st.booleans())
def test_technical_values_survive_admission(value: str, publication: bool) -> None:
    """Technical syntax remains visible in both ingress and publication checks."""

    result = check_text(value, budgets=BUDGETS, publication=publication)
    assert result.admitted, (value, result.reason, result.detector)
    assert result.text == normalize_text(value)


@given(
    technical_text(),
    st.sampled_from(("; ", "\n", " | ")),
    st.sampled_from(
        (
            "Call +1 202 555 0142",
            "Call +1.202.555.0142",
            "person@example.invalid",
            'login_password: "synthetic-secret-value"',
        )
    ),
    st.booleans(),
)
def test_technical_exception_never_exempts_the_whole_unit(
    technical: str, separator: str, sensitive: str, publication: bool
) -> None:
    """A parsed technical token cannot hide another contact or credential."""

    result = check_text(technical + separator + sensitive, budgets=BUDGETS, publication=publication)
    assert not result.admitted
    assert result.reason in {"secret", "pii"}


def display_representation(text: str, kind: str) -> str:
    if kind == "escaped":
        return html.escape(text, quote=False)
    if kind == "double-escaped":
        return html.escape(html.escape(text, quote=False), quote=False)
    if kind == "entities":
        return "".join(f"&#{ord(character)};" for character in text)
    if kind == "markdown":
        return f"**{text}**"
    if kind == "html":
        return f"<span>{html.escape(text)}</span>"
    return text


REPRESENTATIONS = st.sampled_from(
    ("plain", "escaped", "double-escaped", "entities", "markdown", "html")
)


@given(technical_text().filter(lambda value: ": " not in value), REPRESENTATIONS)
def test_rendered_technical_values_do_not_become_contacts(value: str, representation: str) -> None:
    # Pure credential references have a deliberately narrower whole-line grammar;
    # this property exercises numeric technical syntax in display representations.
    result = check_text(
        display_representation(value, representation), budgets=BUDGETS, publication=True
    )
    if representation == "html":
        # Raw HTML is forbidden independently of the technical value within it.
        assert not result.admitted
        return
    assert result.admitted, (value, representation, result.reason, result.detector)


@given(
    technical_text(),
    st.sampled_from(
        (
            "Call +1 202 555 0142",
            "person@example.invalid",
            'login_password: "synthetic-secret-value"',
        )
    ),
    REPRESENTATIONS,
    st.sampled_from(("; ", "\n", " | ")),
)
def test_sensitive_additions_survive_display_obfuscation(
    technical: str, sensitive: str, representation: str, separator: str
) -> None:
    result = check_text(
        technical + separator + display_representation(sensitive, representation),
        budgets=BUDGETS,
        publication=True,
    )
    assert not result.admitted and result.reason in {"secret", "pii", "laundering"}


def test_entity_encoded_credential_is_checked_before_markdown_underscore_removal() -> None:
    value = display_representation('login_password: "synthetic-secret-value"', "entities")
    checked = check_text("IP 192.0.2.1; " + value, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "secret" and checked.detector == "decoded"


@pytest.mark.parametrize("prefix,value", (("version", "2020.0.10"), ("date", "2020-01-01")))
@pytest.mark.parametrize("space", ("\u00a0", "\u202f"))
def test_technical_comparison_with_nonbreaking_spaces_is_not_a_contact(
    prefix, value, space
) -> None:
    text = f"{prefix}{space}<{space}{value}"
    for publication in (False, True):
        checked = check_text(text, budgets=BUDGETS, publication=publication)
        assert checked.admitted and checked.text == text
        mixed = check_text(
            text + "; Call +1 202 555 0142", budgets=BUDGETS, publication=publication
        )
        assert not mixed.admitted and mixed.reason == "pii"


@pytest.mark.parametrize(
    "value", ('login_password: ""', "'login_password': '{{ service_password }}'")
)
@pytest.mark.parametrize("representation", ("entities", "escaped", "double-escaped"))
def test_encoded_pure_references_keep_the_exact_no_value_exception(
    value: str, representation: str
) -> None:
    checked = check_text(
        display_representation(value, representation), budgets=BUDGETS, publication=True
    )
    assert checked.admitted


@pytest.mark.parametrize(
    ("text", "detector"),
    (("opaque-**sentinel**-123", "displayed"), ("<!-- OPAQUE-SENTINEL-123 -->safe", "source")),
)
def test_decoded_check_preserves_later_display_and_hidden_source_checks(
    monkeypatch: pytest.MonkeyPatch, text: str, detector: str
) -> None:
    sentinel = "opaque" + "-sentinel-123"
    monkeypatch.setenv("OCR_LLM_TOKEN", sentinel)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == "secret" and checked.detector == detector


@given(technical_text(), st.sampled_from(("\x00", "\x1b", "\u202e", "\u200b", "\ud800")))
def test_technical_syntax_does_not_hide_controls(value: str, control: str) -> None:
    """Reject hostile controls and surrogates before UTF-8 conversion."""

    result = check_text(value + control, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "invalid_text"


@given(st.integers(0, 90), st.sampled_from(("a", "é", "漢", "😀")))
def test_text_budgets_keep_independent_character_and_byte_units(count: int, character: str) -> None:
    """No multibyte input may bypass either budget at its exact boundary."""

    value = character * count
    result = check_text(value, budgets=TextBudgets(80, 160, 1), publication=True)
    assert result.admitted == (len(value) <= 80 and len(value.encode("utf-8")) <= 160)


@given(st.one_of(st.none(), st.booleans(), st.integers(), st.lists(st.integers(), max_size=4)))
def test_nontext_inputs_fail_closed(value: object) -> None:
    """Hostile wire types cannot become text through string conversion."""

    result = check_text(value, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "invalid_text"


@pytest.mark.parametrize("prefix", ("version", "release", "build", "pin", "date", "expires on"))
@pytest.mark.parametrize(
    "operator", ("<", "<=", ">", ">=", "==", "!=", "=", "≤", "≥", "≠", "&lt;", "&gt;=", "&amp;lt;")
)
def test_minimized_comparison_regressions(prefix: str, operator: str) -> None:
    """Preserve the minimized release/date failures and their equivalent operators."""

    value = "2020-01-01" if prefix in {"date", "expires on"} else "2020.1.10"
    assert check_text(f"{prefix} {operator} {value}", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "date < 2020-02-30",
        "date >= 2020-13-01",
        "version < 2020.1.10.42",
        "version >= +1 202 555 0142",
        "date != +1.202.555.0142",
        "Call 2020-01-01",
    ),
)
def test_comparison_context_does_not_admit_invalid_or_contact_values(value: str) -> None:
    """Only exact parsed technical syntax earns a phone-candidate exception."""

    result = check_text(value, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "pii"


@pytest.mark.parametrize("value", ("version\t>=\t2020.1.10", "date\t<\t2020-01-01"))
def test_tabs_require_the_explicit_code_context(value: str) -> None:
    """A technical prefix does not weaken the normal control-character policy."""

    assert check_text(value, budgets=BUDGETS, publication=True).reason == "invalid_text"
    assert check_text(value, budgets=BUDGETS, publication=True, allow_horizontal_tabs=True).admitted


@pytest.mark.parametrize("key", ("login_password", '"login_password"', "'login_password'"))
@pytest.mark.parametrize(
    "value", ('"synthetic-secret', "'synthetic-secret", "'escaped\\'secret", '"trailing-secret\\')
)
def test_truncated_quoted_credentials_remain_sensitive(key: str, value: str) -> None:
    """Losing a value's closing quote never turns it into a pure placeholder."""

    result = check_text(f"{key}: {value}", budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "secret"


@pytest.mark.parametrize("key", ("login_password", '"login_password"', "'login_password'"))
@pytest.mark.parametrize("value", ('"{{ service_password }}"', "''", '""'))
def test_quoted_keys_preserve_exact_pure_reference_and_empty_grammar(key: str, value: str) -> None:
    """Recognizing a quoted credential key does not reject its proven no-value forms."""

    text = f"{key}: {value}"
    assert check_text(text, budgets=BUDGETS).admitted
    assert check_text(text, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "'login_password': \"{{ service_password }}\" # suffix",
        "'login_password': \"literal-value\"",
        "\"login_password\": '{{ service_password'",
    ),
)
def test_quoted_key_does_not_widen_the_placeholder_exception(value: str) -> None:
    """Suffixes, incomplete references and nonempty credential literals retain rejection."""

    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_malformed_empty_key_is_not_sensitive_but_known_values_still_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not call benign malformed syntax a secret or exempt a known value in it."""

    assert check_text("'login_password\": ''", budgets=BUDGETS, publication=True).admitted
    secret = "synthetic-known-secret"
    monkeypatch.setenv("OCR_LLM_TOKEN", secret)
    assert (
        check_text(f"'login_password\": '{secret}", budgets=BUDGETS, publication=True).reason
        == "secret"
    )


@pytest.mark.parametrize(
    "value",
    (
        "x" * 16_000 + " Call +1 202 555 0142",
        "<" * 16_000 + "person@example.invalid",
        "login_password: '" + "{" * 16_000,
    ),
    ids=("phone-suffix", "email-prefix", "unterminated-credential"),
)
def test_long_near_matches_keep_the_intended_rejection(value: str) -> None:
    """Reach real detector branches with bounded long input, not an earlier size rejection."""

    result = check_text(value, budgets=TextBudgets(20_000, 80_000, 2), publication=True)
    admitted, reason = result.admitted, result.reason
    assert not admitted
    assert reason in {"pii", "secret"}
