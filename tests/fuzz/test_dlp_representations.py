"""Independent material controls for typed data and composed representations."""

import html
from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(20_000, 80_000, 300)
SENSITIVE = st.sampled_from(
    ("person@example.invalid", "+1 202 555 0114", 'api_key="synthetic-material"')
)
ENCODING = st.sampled_from(("raw", "html", "numeric", "mermaid"))


def encode(value, encoding):
    if encoding == "html":
        return html.escape(value)
    if encoding == "numeric":
        return "".join(f"&#{ord(c)};" for c in value)
    if encoding == "mermaid":
        return "".join(f"#{ord(c)};" for c in value)
    return value


@given(
    st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    st.sampled_from(("Last Updated: {}", "snapshot/{}/source", "## 0.14.4 - {}")),
    SENSITIVE,
    ENCODING,
)
def test_complete_calendar_data_never_exempts_adjacent_material(day, wrapper, material, encoding):
    technical = wrapper.format(day.isoformat())
    assert check_text(technical, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        technical + "; " + encode(material, encoding), budgets=BUDGETS, publication=True
    ).admitted


@given(
    st.text(alphabet="ABCDEFabcdef_", min_size=1, max_size=30),
    st.sampled_from(("${{{{ {} }}}}", "${{{}}}", '"{{{{ {} }}}}"')),
    SENSITIVE,
    ENCODING,
)
def test_symbolic_reference_and_adjacent_material_are_independent(
    name, wrapper, material, encoding
):
    reference = "TOKEN: " + wrapper.format(name)
    assert check_text(reference, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        reference + "\n" + encode(material, encoding), budgets=BUDGETS, publication=True
    ).admitted


@given(
    st.sampled_from(("⚠️", "👨‍👩‍👧", "🇺🇳", "1️⃣")),
    st.sampled_from(("\u200d", "\u202e", "\u2066", "\ufe0f", "\u0000")),
    st.booleans(),
)
def test_valid_emoji_never_qualifies_an_unrelated_control(emoji, control, before):
    value = control + "x " + emoji if before else emoji + " x" + control
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(
    st.lists(st.integers(0, 9), min_size=1, max_size=5), st.sampled_from((" ", ".", "-", "/", "()"))
)
def test_too_few_digits_do_not_become_a_phone_by_padding(numbers, separator):
    value = separator.join(map(str, numbers))
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@given(st.integers(1, 15), st.sampled_from(("*", "_", "~", "`")), st.booleans())
def test_delimiter_near_matches_have_closed_deterministic_results(size, delimiter, complete):
    value = (delimiter + "word") * size + (delimiter if complete else "")
    first = check_text(value, budgets=BUDGETS, publication=True)
    assert check_text(value, budgets=BUDGETS, publication=True) == first
    assert first.admitted or first.reason in {
        "invalid_text",
        "limit",
        "secret",
        "pii",
        "laundering",
        "forbidden",
    }


@given(st.lists(st.integers(0, 9), min_size=2, max_size=20), SENSITIVE)
def test_complete_small_integer_iteration_does_not_waive_adjacent_contacts(numbers, material):
    source = "for item in " + " ".join(map(str, numbers)) + "; do"
    assert check_text(source, budgets=BUDGETS, publication=True).admitted
    assert not check_text(source + "; " + material, budgets=BUDGETS, publication=True).admitted


@given(st.integers(0, 22), st.integers(1, 24))
def test_real_markup_tree_never_exceeds_the_shared_nesting_limit(blocks, markers):
    from mistune.core import token_depth

    from ocr_toolkit.context.dlp.markup import _PARSER, MAX_DEPTH, MAX_TOKENS, RepresentationLimit

    value = "> " * blocks + "*" * markers + "safe" + "*" * markers
    try:
        tokens, _ = _PARSER.parse(value)
    except RepresentationLimit:
        return
    assert token_depth(tokens) <= MAX_DEPTH
    pending = list(tokens)
    count = 0
    while pending:
        token = pending.pop()
        count += 1
        pending.extend(token.get("children", ()))
    assert count <= MAX_TOKENS


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=500), st.booleans())
def test_bounded_unicode_compatibility_matches_the_standard_oracle(value, fold):
    import unicodedata

    from ocr_toolkit.context.dlp.decoding import RepresentationLimit, bounded_nfkc

    expected = unicodedata.normalize("NFKC", value)
    folded = expected.casefold() if fold else expected
    limited = (
        len(expected) > 4 * len(value) + 4096
        or len(folded) > 4 * len(value) + 4096
        or len(folded.encode()) > 4 * len(value.encode()) + 4096
    )
    try:
        result = bounded_nfkc(value, fold=fold)
    except RepresentationLimit:
        assert limited
    else:
        assert not limited and result == folded


@given(st.integers(100, 999), st.integers(1000, 9999), SENSITIVE, ENCODING)
def test_unpaired_numeric_operator_and_sensitive_material_are_independent(
    left, right, material, encoding
):
    value = f"capacity = {left} * {right}"
    assert check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        value + "; " + encode(material, encoding), budgets=BUDGETS, publication=True
    ).admitted


@given(st.integers(100, 999), st.integers(100, 199), st.sampled_from(("_", "*", "~", "`")))
def test_markup_cannot_obscure_an_independently_phone_shaped_fragment(prefix, tail, marker):
    from ocr_toolkit.context.code_text import TextSink

    value = f"{prefix} {marker}555-0{tail}"
    assert not check_text(
        value, budgets=BUDGETS, publication=True, sink=TextSink.LITERAL_CODE
    ).admitted
