"""Exercise DLP grammars and whole-unit safety independently of model/provider calls."""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text, normalize_text

BUDGETS = TextBudgets(2000, 8000, 30)
COMPARISONS = st.sampled_from(
    (" ", "<", " <= ", " > ", ">=", " == ", " != ", " = ", " ≤ ", " ≥ ", " ≠ ")
)


@st.composite
def technical_text(draw: st.DrawFn) -> str:
    """Construct parsed-safe technical values without reusing the detector regex."""

    kind = draw(st.sampled_from(("version", "date", "ip", "cidr", "decimal", "id", "reference")))
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
    if kind in {"ip", "cidr"}:
        address = f"192.0.2.{draw(st.integers(1, 254))}"
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
