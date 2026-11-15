"""Complete numeric spans must not invent or hide adjacent contacts."""

import pytest

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(20_000, 80_000, 300)


@pytest.mark.parametrize(
    "value",
    [
        "0.000077",
        "1234.567",
        "123.4567",
        "3.141593",
        "3.14159265",
        "60 000.00",
        "1 000 000.00",
        "200 250 000.50",
        "0.135 (0.13 versus 0.14)",
        "0.000077 (3.14159265)",
        "25.10.2026",
        "22.03.2026 23:59",
        "22.03.2026 23:59 UTC",
        "29.02.2024 23:59:59.123456789+01:30",
    ],
)
def test_issue_numeric_forms_are_admitted_as_complete_tokens(value: str) -> None:
    """Reproduce the agreed decimal, grouping and dotted-calendar admission contract."""
    result = check_text(value, budgets=BUDGETS, publication=True)
    assert result.admitted, result


@pytest.mark.parametrize("technical", ["1234.567", "60 000.00", "25.10.2026", "22.03.2026 23:59"])
@pytest.mark.parametrize(
    "material",
    ["+1 202 555 0114", "(202) 555 0114", "person@example.invalid", 'api_key="synthetic-material"'],
)
@pytest.mark.parametrize("before", [False, True])
def test_technical_value_cannot_cover_independent_sensitive_material(
    technical: str, material: str, before: bool
) -> None:
    """Reject neighboring contacts and credentials in either composition order."""
    text = f"{material}; {technical}" if before else f"{technical}; {material}"
    assert not check_text(text, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "label",
    [
        "phone ",
        "contact: ",
        'tel = "',
        "call (",
        "phoneNumber: ",
        "phone_number=",
        "telephone: ",
        "office_phone: ",
        "phone no: ",
    ],
)
@pytest.mark.parametrize("value", ["1234.567", "60 000.00", "25.10.2026", "22.03.2026 23:59"])
def test_explicit_contact_context_precedes_technical_interpretation(label: str, value: str) -> None:
    """Keep contact labels authoritative over ambiguous numeric presentation."""
    assert not check_text(label + value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    [
        "+1234.567",
        "123.456.789.385",
        "123.4567/35",
        "123.4567#47;35",
        "123.4567&#47;35",
        "1234.567..89",
        "192.168.1.1:65536",
        "29.02.2026",
        "31.04.2026",
        "00.12.2026",
        "22.03.2026 24:00",
        "22.03.2026 23:60",
        "22.03.2026 23:59+24:00",
        "22.03.2026 23:59 UTCinvalid",
        "0.000077 (202) 555 0114",
        "0.000077 123/4567",
    ],
)
def test_near_matches_do_not_grant_partial_numeric_exemptions(value: str) -> None:
    """Reject malformed calendars and networks without borrowing a valid substring."""
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("prefix", ["call ", "phoneNumber: ", "+"])
def test_minimized_dotted_calendar_contact_boundary(prefix: str) -> None:
    """Preserve contact priority when a dotted date is immediately followed by a clock."""
    assert not check_text(prefix + "01.01.2000T00:00", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("length", [63, 64, 65])
def test_long_decimal_cannot_hide_a_neighboring_phone(length: int) -> None:
    """Exercise detector length boundaries without losing an adjacent phone."""
    value = "0." + "1" * (length - 2)
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(value + " (202) 555 0114", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    [
        "index = find(ranges, (position, length(data) + 1)) - 1",
        'prefix + "2026-10-23 08:52 UTC"',
        '"one" + " " * 2_000_000',
        '"text" + "1114112"',
        "offset + (1234.567)",
        "phone версия: 1234.567",
    ],
)
def test_unrelated_addition_is_not_a_phone_prefix(value: str) -> None:
    """Regress harmless source and prose compositions found by the corpus comparison."""
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("zone", ["Z", " UTC", "+01:00", "-0130"])
@pytest.mark.parametrize("tail", [":", ": ", ": event", ":\nnext line"])
def test_closed_timestamp_zone_can_precede_prose_colon(zone: str, tail: str) -> None:
    """Treat punctuation after a complete zone as a boundary, preserving the full scan."""
    value = "2026-10-25T12:30:45" + zone + tail
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(value + "; +1 202 555 0114", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("value", ["2026-10-25T12:30:", "2026-10-25T12:30:45+01:00:30"])
def test_colon_cannot_complete_an_unfinished_clock_or_continue_a_zone(value: str) -> None:
    """Reject numeric continuations rather than accepting a valid timestamp prefix."""
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("clock", ["12:30", "12:30:45", "12:30:45+01:30"])
@pytest.mark.parametrize("separator", [" ", "\n", r"\n", r"\r", r"\t"])
def test_timestamp_prose_boundary_preserves_original_and_escaped_whitespace(clock, separator):
    """Recognize a closed timestamp before punctuation without decoding adjacent material."""
    value = "2026-10-25T" + clock + ":" + separator + "event"
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        value + "; contact: 202.555.0114", budgets=BUDGETS, publication=True
    ).admitted
