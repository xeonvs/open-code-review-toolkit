"""Minimized actual-review regressions cross the production publication boundary."""

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.common.redaction import has_sensitive_material
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenMatcher, check_text

BUDGETS = TextBudgets(10_000, 40_000, 100)


@pytest.mark.parametrize(
    "value",
    (
        "https://example.invalid?x=1;%74oken=synthetic-material",
        'password = """;synthetic-material"""',
    ),
)
def test_complete_material_survives_query_separators_and_quote_runs(value):
    assert has_sensitive_material(value, values=())
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "secret"
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


def test_real_html_parser_failure_cannot_escape_dlp_or_publication():
    value = "<div>\n<![BOGUS]>\n</div>"
    # Python 3.12 asserts in HTMLParser; later stdlibs can tolerate the section.
    # Neither parser behavior makes the HTML safe or permits an exception out.
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    matcher = ForbiddenMatcher.compile((value,))
    assert matcher.match_details("ordinary text")[0] in {None, "limit"}
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@pytest.mark.parametrize("role", ("prose", "literal"))
def test_encoded_empty_field_preserves_original_source_carrier(role):
    from ocr_toolkit.context.code_text import TextSink

    value = """        ('"login_password": ""', "#34;login_password#34;#58; #34;#34;"),"""
    sink = TextSink.PROSE if role == "prose" else TextSink.LITERAL_CODE
    assert check_text(value, budgets=BUDGETS, publication=True, sink=sink).admitted
    assert not check_text(
        value + ' api_key="synthetic-material"', budgets=BUDGETS, publication=True, sink=sink
    ).admitted


@pytest.mark.parametrize("encoded", (False, True))
def test_absent_field_spans_enforce_their_construction_budget(encoded):
    from ocr_toolkit.context.dlp.credentials import (
        MAX_CREDENTIAL_FIELDS,
        _encoded_absent_carriers,
        credential_reference_spans,
    )
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit

    field = '"token=&#34;&#34;"' if encoded else 'token=""'
    acquire = _encoded_absent_carriers if encoded else credential_reference_spans
    separator = ",\n" if encoded else "\n"
    value = separator.join([field] * MAX_CREDENTIAL_FIELDS)
    assert len(acquire(value)) == MAX_CREDENTIAL_FIELDS
    with pytest.raises(RepresentationLimit):
        acquire(value + separator + field)
    assert (
        check_text(
            value + separator + field,
            budgets=TextBudgets(200_000, 800_000, MAX_CREDENTIAL_FIELDS + 2),
            publication=True,
        ).reason
        == "limit"
    )


def test_reference_and_carrier_spans_share_one_budget():
    value = "\n".join(['token=""', '"token=&#34;&#34;",'] * 2049)
    assert (
        check_text(value, budgets=TextBudgets(200_000, 800_000, 5000), publication=True).reason
        == "limit"
    )


@pytest.mark.parametrize(
    "tail", (' + "material"', ' "material"', '.format("material")', '#43;"material"')
)
def test_encoded_absent_carrier_cannot_waive_a_computed_value(tail):
    value = '"token=&#34;&#34;"' + tail
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("prefix", ("", "components/", "https://example.invalid?"))
@pytest.mark.parametrize(
    "tail", ('\n "synthetic-material"', '\n + "synthetic-material"', ')\n+ "synthetic-material"')
)
def test_raw_and_encoded_carrier_cannot_end_before_multiline_continuation(prefix, tail):
    for field in (prefix + "token=***", prefix + "token=&#34;***&#34;"):
        value = '("' + field + '"' + tail + ")"
        assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("wrapper", ("({},)[0]", "[{},][0]", "(({},),)[0][0]"))
def test_trailing_container_separator_cannot_hide_a_carrier_postfix(wrapper):
    value = wrapper.format('"token=&#34;***&#34;"') + ' + "synthetic-material"'
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@pytest.mark.parametrize(
    "gap", ("# comment\n", "// comment\n", "/* comment */", "<!-- comment -->")
)
def test_unknown_separator_tokens_cannot_qualify_a_carrier_before_its_postfix(gap):
    value = '("token=&#34;***&#34;", ' + gap + ')[0] + "synthetic-material"'
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
