"""Minimized raw-review findings, including cases hidden by publication DLP."""

from __future__ import annotations

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.evidence.opaque_code import prove_opaque_code

BUDGETS = TextBudgets(20000, 80000, 300)


@pytest.mark.parametrize("marker", ["*", "**", "_", "~", "`"])
@pytest.mark.parametrize("sink", [TextSink.LITERAL_CODE, TextSink.DIAGRAM_LABEL])
def test_unmatched_markup_cannot_hide_an_unlabelled_phone(marker, sink):
    value = f"202 {marker}555-0114"
    assert not check_text(value, budgets=BUDGETS, publication=True, sink=sink).admitted
    source = "def parse(parts):\n    token=parts  # " + value + "\n"
    excerpt = source.splitlines()[1]
    comment = dict(
        path="source",
        start_line=2,
        end_line=2,
        content="Inspect the expression.",
        existing_code=excerpt,
    )
    proof = prove_opaque_code(comment, "source", lambda _path: source)
    projected, _, _ = review_runner._publication_projection(
        dict(status="success", warnings=[], comments=[comment]),
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    assert "existing_code" not in projected["comments"][0]


@pytest.mark.parametrize("phrase", ["pass word", "api key", "access token"])
@pytest.mark.parametrize("encoding", ["plain", "html", "mermaid"])
@pytest.mark.parametrize("outer_spaces", [False, True])
def test_decoded_known_passphrase_is_checked_before_token_rewriting(
    monkeypatch, phrase, encoding, outer_spaces
):
    secret = "synthetic " + phrase + " credential"
    if outer_spaces:
        secret = " " + secret + " "
    monkeypatch.setenv("OCR_LLM_TOKEN", secret)
    value = secret
    if encoding == "html":
        value = "".join(f"&#{ord(char)};" for char in secret)
    elif encoding == "mermaid":
        value = "".join(f"#{ord(char)};" for char in secret)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        dict(status="success", warnings=[], comments=[dict(path="example", line=1, content=value)]),
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@pytest.mark.parametrize(
    "content,reason",
    [
        ("The rendered example is 202 555-0114.", "pii"),
        ('The example sets OCR_LLM_TOKEN="synthetic pass word credential".', "secret"),
        ("The example sets OCR_LLM_TOKEN=source.", "secret"),
    ],
)
def test_hidden_review_examples_remain_sensitive_prose(content, reason):
    checked = check_text(content, budgets=BUDGETS, publication=True)
    assert not checked.admitted and checked.reason == reason


@pytest.mark.parametrize(
    "value",
    [
        "size=2 *1024*1024",
        "size = 2 * 1_024 *1_024",
        "return 2 *1024 *1024",
        "limit > 2 **8 *16",
        "size=(2*1024*1024)",
    ],
)
def test_numeric_operators_need_full_source_proof(value):
    source = "def calculate(limit):\n    " + value + "\n"
    comment = dict(path="source", start_line=2, end_line=2, existing_code=source.splitlines()[1])
    proof = prove_opaque_code(comment, "source", lambda _path: source)
    checked = check_text(
        comment["existing_code"],
        budgets=BUDGETS,
        publication=True,
        sink=TextSink.LITERAL_CODE,
        allow_opaque_code=proof.existing_verified,
        code_context=proof.existing_context,
    )
    assert checked.admitted


@pytest.mark.parametrize(
    "value",
    [
        "value: 999 *555-1114",
        "value: 999 **555-1114",
        "value = 999 *555* 1114",
        'value: "999 **555** 1114"',
    ],
)
@pytest.mark.parametrize("sink", list(TextSink))
def test_untrusted_data_never_becomes_arithmetic_authority(value, sink):
    assert not check_text(value, budgets=BUDGETS, publication=True, sink=sink).admitted
    comment = dict(
        path="source",
        start_line=1,
        end_line=1,
        existing_code=value,
        content="Inspect the expression.",
    )
    proof = prove_opaque_code(comment, "source", lambda _path: value)
    result, _, _ = review_runner._publication_projection(
        dict(status="success", warnings=[], comments=[comment]),
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    assert "existing_code" not in result["comments"][0]


@pytest.mark.parametrize(
    "expression",
    [
        'value="999 *555-1114"',
        "value: 999 *555-1114",
        'value=f"999 *555-1114"',
        'value=f"{999 *555-1114}"',
        "type Value = 999 *555-1114",
        "value=0  # 999 *555-1114",
    ],
)
def test_data_literals_and_annotations_inside_programs_get_no_operator_proof(expression):
    source = "def parse():\n    " + expression + "\n"
    value = source.splitlines()[1]
    comment = dict(path="source", start_line=2, end_line=2, existing_code=value)
    proof = prove_opaque_code(comment, "source", lambda _path: source)
    assert not check_text(
        value,
        budgets=BUDGETS,
        publication=True,
        sink=TextSink.LITERAL_CODE,
        allow_opaque_code=proof.existing_verified,
        code_context=proof.existing_context,
    ).admitted


def test_operator_context_is_exact_and_cannot_replace_arbitrary_characters():
    from dataclasses import replace

    source = "def parse():\n    size=2 *1024*1024\n"
    value = source.splitlines()[1].strip()
    proof = prove_opaque_code(
        dict(start_line=2, end_line=2, existing_code=source.splitlines()[1]),
        "source",
        lambda _path: source,
    )
    context = proof.existing_context
    assert context is not None and context.operator_spans
    assert context.phone_view(value) != value
    assert context.phone_view(value + " ") == value + " "
    assert replace(context, operator_spans=((0, 1),)).phone_view(value) == value


@pytest.mark.parametrize("sensitive", ['"person@example.invalid"', '"999 *555-1114"'])
def test_proven_numeric_computation_does_not_hide_other_material(sensitive):
    source = "def calculate():\n    value=(2 *1024*1024, " + sensitive + ")\n"
    excerpt = source.splitlines()[1]
    proof = prove_opaque_code(
        dict(start_line=2, end_line=2, existing_code=excerpt), "source", lambda _path: source
    )
    assert proof.existing_context is not None and proof.existing_context.operator_spans
    assert not check_text(
        excerpt,
        budgets=BUDGETS,
        publication=True,
        sink=TextSink.LITERAL_CODE,
        allow_opaque_code=proof.existing_verified,
        code_context=proof.existing_context,
    ).admitted


def test_unicode_columns_and_unrelated_entities_preserve_only_proven_operators():
    source = 'def calculate():\n    размер=(2 *1024*1024, "&#65;")\n'
    excerpt = source.splitlines()[1]
    proof = prove_opaque_code(
        dict(start_line=2, end_line=2, existing_code=excerpt), "source", lambda _path: source
    )
    assert proof.existing_context is not None and proof.existing_context.operator_spans
    assert check_text(
        excerpt,
        budgets=BUDGETS,
        publication=True,
        sink=TextSink.LITERAL_CODE,
        allow_opaque_code=proof.existing_verified,
        code_context=proof.existing_context,
    ).admitted


def test_operator_token_budget_fails_closed(monkeypatch):
    from ocr_toolkit.evidence import source_syntax

    monkeypatch.setattr(source_syntax, "MAX_KEY_SPANS", 0)
    assert source_syntax.analyze_python_source("def calculate():\n    return 2*1024*1024\n") is None
