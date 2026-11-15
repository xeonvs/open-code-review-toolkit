"""Closed contact targets retain priority without borrowing unrelated expression context."""

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.context.dlp.contact_labels import _explicit_context
from ocr_toolkit.evidence.opaque_code import prove_opaque_code
from tests.fuzz.test_dlp_representations import encode

BUDGETS = TextBudgets(20_000, 80_000, 300)


@pytest.mark.parametrize(
    "target",
    [
        'record["phone"]',
        "record['telephone']",
        "[phone]",
        "(phone)",
        'record["office_phone_number"][0]',
        'record["phone"][0][1]',
        "record[\u201cphone\u201d]",
        "record[\u2018phone\u2019]",
    ],
)
@pytest.mark.parametrize("number", ["202555.0114", "25.10.2026", "192.168.1.1/24", "1.2.3-4.5.6"])
@pytest.mark.parametrize("encoding", ["raw", "html", "numeric", "mermaid"])
def test_closed_contact_labels_precede_all_technical_exemptions(target, number, encoding):
    """Protect indexed and grouped contact fields across material representations."""
    value = encode(f'{target} = "{number}"', encoding)
    for sink in TextSink:
        checked = check_text(value, budgets=BUDGETS, publication=True, sink=sink)
        assert not checked.admitted and checked.reason == "pii", (value, sink, checked)


@pytest.mark.parametrize(
    "target",
    [
        'record["phone"].version',
        'record["phone"]["version"]',
        'record["ph" + "one"]',
        'record["phone]',
        "record[phone)",
        "function(phone)",
        "PhoneVersion",
        "[version]",
        "record[phone - number]",
        "record[version.phone]",
        "record[phone number]",
        "function (phone)",
    ],
)
def test_noncontact_members_and_computed_or_malformed_keys_do_not_supply_intent(target):
    """Do not reinterpret ordinary decimals using an earlier or unevaluated label."""
    assert check_text(f"{target} = 202555.0114", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("separator", [" == ", " != ", " <= ", " >= ", " += ", " => ", ", ", "; "])
def test_closed_target_needs_a_binding_separator(separator):
    """Comparisons, compound operations and completed expressions do not bind a value."""
    value = 'record["phone"]' + separator + "202555.0114"
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("field", ["content", "existing_code", "suggestion_code"])
def test_publication_checks_contacts_even_with_source_proof(field):
    """Proven code has no authority to publish contact material."""
    value = 'record["phone"] = "202555.0114"'
    comment = dict(path="source", start_line=1, end_line=1, content="Inspect the value.")
    comment[field] = value
    proof = prove_opaque_code(comment, "source", lambda _path: value)
    result, state, filtered = review_runner._publication_projection(
        dict(status="success", warnings=[], comments=[comment]),
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    assert state["state"] != "passed"
    if field == "content":
        assert filtered and result["comments"] == []
    else:
        assert field not in result["comments"][0]


@pytest.mark.parametrize("length", [63, 64, 65, 255, 256, 257, 10_000])
def test_label_work_is_bounded_without_reading_an_entire_prefix(length):
    """A distant unrelated prefix cannot change a nearby complete contact target."""
    value = "x" * length + '; record["phone"][0] = "202555.0114"'
    assert _explicit_context(value, value.index("202555"))
    assert not _explicit_context("[" * length + " 202555.0114", length + 1)


@pytest.mark.parametrize("space", [" ", "\t", " " * 247, " " * 248, " " * 256])
def test_calls_and_truncated_prefixes_never_become_grouped_labels(space):
    """A bounded window cannot invent a grouping boundary by dropping the callable."""
    value = "function(phone)" + space + "= 202555.0114"
    assert not _explicit_context(value, value.index("202555"))
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.reason == "invalid_text" if space == "\t" else checked.admitted
    value = "mapping = {lookup" + space + "(phone): 202555.0114}"
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.reason == "invalid_text" if space == "\t" else checked.admitted
