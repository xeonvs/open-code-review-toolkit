"""Vary calendar structure, representation and independent sensitive material."""

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.context.dlp.datetimes import complete_datetime
from tests.fuzz.test_dlp_representations import ENCODING, SENSITIVE, encode

BUDGETS = TextBudgets(20_000, 80_000, 300)


@given(st.dates(), st.times(), st.integers(0, 260), st.sampled_from((" ", "\t")), st.booleans())
def test_incomplete_timezone_continuation_is_rejected_across_lookahead_splits(
    day, clock, gap, whitespace, publication
):
    value = f"{day.isoformat()} {clock.hour:02}:{clock.minute:02}" + whitespace * gap + "UTCinvalid"
    assert not complete_datetime(value, 0, 13)
    assert not check_text(
        value,
        budgets=BUDGETS,
        publication=publication,
        sink=TextSink.LITERAL_CODE,
        allow_horizontal_tabs=True,
    ).admitted


@st.composite
def calendar_stamp(draw):
    instant = draw(st.datetimes(min_value=datetime(1, 1, 1), max_value=datetime(9999, 12, 31)))
    clock = f"{instant.hour:02}:{instant.minute:02}"
    if draw(st.booleans()):
        clock += f":{instant.second:02}"
        fraction = draw(st.text(alphabet="0123456789", min_size=0, max_size=9))
        if fraction:
            clock += draw(st.sampled_from((".", ","))) + fraction
    zone = draw(st.sampled_from(("", "Z", "z", " UTC", " utc", "offset")))
    if zone == "offset":
        zone = (
            draw(st.sampled_from(("+", "-")))
            + f"{draw(st.integers(0, 23)):02}"
            + draw(st.sampled_from(("", ":")))
            + f"{draw(st.integers(0, 59)):02}"
        )
    separator = draw(st.sampled_from(("T", "t", " ", "   ")))
    return instant.date().isoformat() + separator + clock + zone


@given(
    calendar_stamp(),
    ENCODING,
    st.sampled_from(("{}", "updated {}", "({}).", "`{}`", "**{}**")),
    st.sampled_from((0x30, 0xFF10, 0x660, 0x966)),
)
def test_calendar_values_survive_all_material_views(stamp, encoding, wrapper, digit_zero):
    digit_alphabet = "".join(chr(digit_zero + digit) for digit in range(10))
    stamp = stamp.translate(str.maketrans("0123456789", digit_alphabet))
    value = encode(wrapper.format(stamp), encoding)
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, (stamp, encoding, checked.reason, checked.detector)
    assert checked.text == value


@given(calendar_stamp(), SENSITIVE, ENCODING, st.booleans(), st.sampled_from(("; ", "\n", " | ")))
def test_timestamp_never_waives_independent_original_or_encoded_material(
    stamp, material, encoding, before, separator
):
    material = encode(material, encoding)
    value = material + separator + stamp if before else stamp + separator + material
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(
    calendar_stamp(),
    st.sampled_from(("call", "phone", "tel", "contact")),
    st.sampled_from((" ", ": ", " = '", ': "', " = [")),
)
def test_contact_intent_precedes_calendar_interpretation(stamp, label, punctuation):
    assert not check_text(label + punctuation + stamp, budgets=BUDGETS).admitted


@given(
    st.dates(),
    st.sampled_from(("hour", "minute", "second", "offset", "continued")),
    st.integers(60, 99),
)
def test_invalid_components_or_continued_tokens_never_form_a_complete_timestamp(day, field, bad):
    clock = {"hour": "24:00", "minute": f"12:{bad}", "second": f"12:00:{bad}"}.get(field, "12:00")
    suffix = f"+01:{bad}" if field == "offset" else " UTCsuffix" if field == "continued" else " UTC"
    stamp = day.isoformat() + " " + clock + suffix
    assert not complete_datetime(stamp, 0, 13)
    assert not check_text(stamp, budgets=BUDGETS, publication=True).admitted


@given(calendar_stamp(), st.sampled_from(("1", "_", ".", ":", "+", "/", "-")), st.booleans())
def test_larger_numeric_token_cannot_borrow_a_timestamp_substring(stamp, continuation, prepend):
    # A digit or period alone can legitimately extend fractional seconds.
    # Make suffixes unambiguously non-calendar rather than rejecting valid data.
    value = continuation + stamp if prepend else stamp + continuation + "x7"
    start = len(continuation) if prepend else 0
    assert not complete_datetime(value, start, start + len(stamp))
