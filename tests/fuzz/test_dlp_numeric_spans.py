"""Vary numeric grammar, composition and material boundaries independently."""

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from tests.fuzz.test_dlp_representations import ENCODING, SENSITIVE, encode

BUDGETS = TextBudgets(20_000, 80_000, 300)


@st.composite
def fraction(draw):
    """Generate complete decimals with independent grouping and precision choices."""
    integer = draw(st.integers(0, 10**15))
    digits = format(integer, ",").replace(",", " ") if draw(st.booleans()) else str(integer)
    places = draw(st.text(alphabet="0123456789", min_size=1, max_size=24))
    return digits + "." + places


@given(
    fraction(),
    fraction(),
    ENCODING,
    st.sampled_from(["{} ({})", "{} {}", "{} versus {}", "({}) ({})"]),
)
def test_independent_decimals_keep_their_complete_spans(left, right, encoding, wrapper):
    """Prevent the phone detector from joining independently valid decimal tokens."""
    text = encode(wrapper.format(left, right), encoding)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted, (left, right, encoding, checked.detector)


@given(
    fraction(),
    ENCODING,
    st.sampled_from(["{}", "{}.", "({}).", "`{}`", "amount < {}", "Decimal('{}')"]),
    st.sampled_from([0x30, 0xFF10, 0x660, 0x966]),
)
def test_numeric_syntax_survives_representation_and_unicode_views(number, encoding, wrapper, zero):
    """Keep numeric admission consistent across Unicode and encoded material views."""
    number = number.translate(
        str.maketrans("0123456789", "".join(chr(zero + n) for n in range(10)))
    )
    text = encode(wrapper.format(number), encoding)
    checked = check_text(text, budgets=BUDGETS, publication=True)
    assert checked.admitted, (number, encoding, wrapper, checked.detector)


@given(fraction(), SENSITIVE, ENCODING, st.booleans(), st.sampled_from([" ", "; ", " (", "\n"]))
def test_decimal_does_not_cover_adjacent_raw_or_encoded_sensitive_material(
    number, material, encoding, before, separator
):
    """Require independent contact and secret checks beside an admitted decimal."""
    material = encode(material, encoding)
    text = material + separator + number if before else number + separator + material
    assert not check_text(text, budgets=BUDGETS, publication=True).admitted


@given(fraction(), st.sampled_from(["phone: ", "call ", 'tel = "', "+"]), ENCODING)
def test_explicit_contact_intent_is_independent_of_decimal_grammar(number, label, encoding):
    # Ensure this property reaches the minimum detector shape, independently of
    # whether the generated fraction alone happens to be a short identifier.
    """Ensure explicit contact intent takes priority over decimal interpretation."""
    text = encode(label + number + "0000000", encoding)
    assert not check_text(text, budgets=BUDGETS, publication=True).admitted


@given(fraction(), ENCODING)
def test_configured_protection_remains_independent_of_numeric_admission(number, encoding):
    """Keep configured protected material blocked beside otherwise safe numbers."""
    protected = "A protected synthetic sentence"
    text = number + "; " + encode(protected, encoding)
    assert not check_text(text, budgets=BUDGETS, publication=True, forbidden=(protected,)).admitted


@given(
    st.sampled_from(["tel", "Phone no", "contact", "office_phone_number"]),
    st.text(alphabet='.:#\u2018\u2019"[({\t \u00a0\u3000', min_size=1, max_size=12),
    ENCODING,
)
def test_label_punctuation_preserves_contact_priority(label, separator, encoding):
    """Vary bounded punctuation independently of contact words and encoded views."""
    value = encode(label + separator + "1234.567", encoding)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(fraction(), st.sampled_from(["offset + ({})", '"prefix" + "{}"', "length(data) + ({})"]))
def test_unrelated_addition_does_not_grant_contact_intent(number, wrapper):
    """Distinguish arithmetic and concatenation from a numeric telephone prefix."""
    assert check_text(wrapper.format(number), budgets=BUDGETS, publication=True).admitted


@given(
    fraction(),
    st.sampled_from(
        ["print(phone); {}", "phone(); {}", "[phone], {}", "phone != {}", "phone ? {} : other"]
    ),
    ENCODING,
)
def test_closed_expressions_and_operators_do_not_supply_contact_intent(number, wrapper, encoding):
    """Keep label adjacency from crossing completed expressions and operator boundaries."""
    assert check_text(
        encode(wrapper.format(number), encoding), budgets=BUDGETS, publication=True
    ).admitted


@given(
    st.text(
        alphabet=st.characters(categories=("Ll", "Lu", "Lt", "Lo", "Lm")), min_size=1, max_size=12
    ),
    st.sampled_from(["camel", "_", "-", "."]),
)
def test_contact_identifier_components_keep_intent_under_arbitrary_prefixes(prefix, style):
    """Preserve contact intent across naming styles without absorbing version fields."""
    label = prefix + "PhoneNumber" if style == "camel" else style.join([prefix, "phone", "number"])
    assert not check_text(label + ": 1234.567", budgets=BUDGETS, publication=True).admitted
    assert check_text(prefix + "PhoneVersion: 1234.567", budgets=BUDGETS, publication=True).admitted


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=20),
    st.sampled_from([('["', '"]'), ("['", "']"), ("[", "]")]),
    st.lists(st.integers(0, 999), max_size=4),
    st.sampled_from([" = ", ": ", "\u00a0=\u3000"]),
    ENCODING,
)
def test_structured_labels_vary_closing_delimiters_and_terminal_members(
    receiver, quotes, indexes, binding, encoding
):
    """Vary closed-key grammar and its noncontact counterpart rather than only label values."""
    opening, closing = quotes
    target = receiver + opening + "phone" + closing + "".join(f"[{index}]" for index in indexes)
    value = encode(target + binding + '"202555.0114"', encoding)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    ordinary = encode(target + ".version" + binding + '"202555.0114"', encoding)
    assert check_text(ordinary, budgets=BUDGETS, publication=True).admitted


@given(
    st.dates(),
    st.integers(0, 23),
    st.integers(0, 59),
    st.sampled_from(("Z", "+01:30", " UTC")),
    st.sampled_from((":", ": ", ":\n", ": event")),
)
def test_closed_zone_punctuation_does_not_hide_adjacent_contacts(day, hour, minute, zone, tail):
    """Vary complete timestamps and punctuation while preserving independent contact checks."""
    value = f"{day.isoformat()}T{hour:02}:{minute:02}:00{zone}{tail}"
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(value + "; +1 202 555 0114", budgets=BUDGETS, publication=True).admitted
