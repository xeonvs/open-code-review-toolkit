"""Calendar interpretation never replaces contact or whole-material controls."""

import pytest

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.context.dlp.datetimes import complete_datetime

BUDGETS = TextBudgets(20_000, 80_000, 300)


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-10-23 08:52 UTC",
        "2024-02-29T00:00:00Z",
        "2026-10-23 08:52",
        "2026-10-23t08:52:59z",
        "2026-10-23 08:52:59.123456789+01:30",
        "2026-10-23 08:52:59,000001-0000",
        "0001-01-01 00:00:00+23:59",
        "9999-12-31 23:59:59-23:59",
        "\uff12\uff10\uff10\uff10-\uff10\uff11-\uff10\uff11 \uff10\uff10:\uff10\uff10",
    ],
)
@pytest.mark.parametrize("wrapper", ["updated {}", "({})", '"{}"', "{}."])
def test_complete_timestamps_are_technical_without_a_special_keyword(stamp, wrapper):
    value = wrapper.format(stamp)
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert complete_datetime(value, value.index(stamp), value.index(stamp) + len(stamp))


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-02-29 08:52 UTC",
        "0000-01-01 08:52 UTC",
        "2026-13-01 08:52 UTC",
        "2026-10-23 24:00 UTC",
        "2026-10-23 08:60 UTC",
        "2026-10-23 08:52:60 UTC",
        "2026-10-23 08:52+01:60",
        "2026-10-23 08:52+24:00",
        "2026-10-23 08:52 UTCx",
        "2026-10-23 08:52 UTC+01:00",
        "2026-10-23 08:52 UTC UTC",
        "2026-10-23 08:52 Z",
        "2026-10-23 08:52:00.1234567890",
        "2026-10-23 08:52/35",
        "2026-10-23 08:52:00.1.2",
        "2026-10-23 08:52_01",
    ],
)
def test_invalid_or_continued_timestamp_cannot_supply_a_calendar_exception(stamp):
    # Exercise the detector-sized date/hour fragment, not only full-string parsing.
    assert not complete_datetime(stamp, 0, 13)
    assert not check_text("updated " + stamp, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("prefix", ["call ", "phone: ", "tel = '", "contact "])
def test_explicit_contact_priority_is_preserved(prefix):
    assert not check_text(prefix + "2026-10-23 08:52 UTC", budgets=BUDGETS).admitted


@pytest.mark.parametrize(
    "material",
    [
        "+1 202 555 0114",
        "person@example.invalid",
        'api_key="synthetic-material"',
    ],
)
@pytest.mark.parametrize("before", [False, True])
def test_datetime_never_authorizes_other_material(material, before):
    stamp = "2026-10-23 08:52 UTC"
    value = material + "; " + stamp if before else stamp + "; " + material
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_unrelated_valid_timestamp_cannot_prove_another_numeric_value():
    prefix = "2026-10-23 08:52 UTC; "
    value = prefix + "2026-02-30 08:52 UTC"
    assert not complete_datetime(value, len(prefix), len(prefix) + 13)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    [
        "\u03012026-10-23 08:52",
        "2026-10-23 08:52\u0301",
        "2026-10-23 08:52.\u0301",
    ],
)
def test_combining_marks_continue_the_token(value):
    start = value.index("2026")
    assert not complete_datetime(value, start, start + 13)


def test_unfinished_timezone_lookahead_does_not_supply_partial_proof():
    value = "2026-10-23 08:52" + " " * 256 + "UTCinvalid"
    assert not complete_datetime(value, 0, 13)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
