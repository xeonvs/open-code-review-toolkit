"""Vary source scope and representations without exempting original sensitive text."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.evidence.opaque_code import prove_opaque_code

BUDGETS = TextBudgets(20000, 80000, 300)
KEYS = st.sampled_from(["token", "api_token", "password", "client_secret", "ACCESS_TOKEN"])
REFERENCES = st.sampled_from(["parts", "None", '"".join(parts)', "parts[start:end]", "read(parts)"])


def source_decision(expression, *, prefix="", filename="source", docstring=False):
    body = f"    {prefix}{expression}"
    if docstring:
        source = f'"""Example:\n{body}\n"""\ndef parse(parts):\n    pass\n'
    else:
        source = f"def parse(parts, start=None, end=None):\n{body}\n"
    comment = {"path": filename, "start_line": 2, "end_line": 2, "existing_code": body}
    proof = prove_opaque_code(comment, filename, lambda _path: source)
    assert proof.existing_verified
    return check_text(
        body,
        budgets=BUDGETS,
        publication=True,
        allow_horizontal_tabs=True,
        allow_opaque_code=True,
        code_context=proof.existing_context,
        sink=TextSink.LITERAL_CODE,
    )


@given(
    KEYS,
    REFERENCES,
    st.sampled_from(["", "π = parts; ", "𝛑 = parts; "]),
    st.sampled_from(["source", "code.py", "code.pyi", "code.txt"]),
)
def test_reference_role_survives_unicode_columns_and_filename_changes(
    key, expression, prefix, filename
):
    assert source_decision(f"{key} = {expression}", prefix=prefix, filename=filename).admitted


@given(KEYS, REFERENCES)
def test_identical_code_shaped_text_inside_docstring_is_not_authorized(key, expression):
    assert not source_decision(f"{key} = {expression}", docstring=True).admitted


@given(
    KEYS,
    REFERENCES,
    st.sampled_from(
        [
            "# password=synthetic-short-value",
            "# person@example.invalid",
            "# contact +1 202-555-0114",
            "# contact +1.202.555.0114",
            "# person&#64;example.invalid",
            "# contact &#43;1 202-555-0114",
        ]
    ),
)
def test_independent_material_appended_to_a_reference_always_blocks(key, expression, material):
    assert not source_decision(f"{key} = {expression}  {material}").admitted


@given(KEYS, st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=80))
def test_nonempty_literal_material_is_not_a_reference(key, value):
    assert not source_decision(f"{key} = {value!r}").admitted


@given(
    st.sampled_from(["c", "cpp", "js", "txt", ""]),
    st.integers(10, 9999),
    st.integers(10, 9999),
    st.sampled_from(["*", " *", "* ", " * ", " ** "]),
    st.sampled_from(["*", " *", "* ", " * ", " ** "]),
)
def test_fixed_literal_sink_preserves_multiplication_for_any_language(
    _extension, left, right, first, second
):
    value = f"bytes = 2{first}{left}{second}{right};"
    assert check_text(value, budgets=BUDGETS, publication=True, sink=TextSink.LITERAL_CODE).admitted


@given(
    st.sampled_from(
        [
            "call +1 **202**-555-0114",
            "call +1 *202-555-0114",
            "call 202 **555** 0114",
            "call +1 <b>202</b>-555-0114",
            "person**@**example.invalid",
            "pass**word**=syntheticShortCredential",
            r"202\-555\-0114",
            "202 **555** 0114",
            "202 *555* 0114",
        ]
    ),
    st.sampled_from(["plain", "html", "mermaid", "fullwidth"]),
    st.sampled_from([TextSink.LITERAL_CODE, TextSink.DIAGRAM_LABEL]),
)
def test_literal_sinks_retain_obfuscated_material_detection(value, representation, sink):
    if representation == "html":
        value = "".join(f"&#{ord(char)};" for char in value)
    elif representation == "mermaid":
        value = "".join(f"#{ord(char)};" for char in value)
    elif representation == "fullwidth":
        value = "".join(chr(ord(char) + 0xFEE0) if "!" <= char <= "~" else char for char in value)
    assert not check_text(
        value,
        budgets=BUDGETS,
        publication=True,
        allow_opaque_code=True,
        sink=sink,
    ).admitted


@given(
    st.sampled_from(["*", "_", "~", "`", "**", "<b>"]),
    st.integers(min_value=1, max_value=1000),
)
def test_markup_near_matches_never_hide_appended_material(marker, repeats):
    value = (marker + "near match ") * repeats + " contact +1 202-555-0114"
    result = check_text(value, budgets=BUDGETS, publication=True, sink=TextSink.LITERAL_CODE)
    assert not result.admitted


@given(st.text(alphabet=["a", "b", "é", "Ω", "\u0301"], min_size=8, max_size=24), st.booleans())
def test_known_secret_survives_unicode_and_whitespace_canonicalization(suffix, outer_spaces):
    import unicodedata

    from pytest import MonkeyPatch

    secret = "synthetic-" + suffix
    if outer_spaces:
        secret = " " + secret + " "
    with MonkeyPatch.context() as patch:
        patch.setenv("OCR_LLM_TOKEN", secret)
        for value in (secret, unicodedata.normalize("NFC", secret)):
            assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=40))
def test_material_stored_as_mapping_key_cannot_cross_reference_waiver(value):
    source = f"def parse():\n    values={{{value!r}: None}}\n    password=next(iter(values))\n"
    comment = dict(path="source", start_line=1, end_line=3, existing_code=source.rstrip("\n"))
    proof = prove_opaque_code(comment, "source", lambda _path: source)
    assert not check_text(
        comment["existing_code"],
        budgets=BUDGETS,
        publication=True,
        allow_opaque_code=proof.existing_verified,
        code_context=proof.existing_context,
        sink=TextSink.LITERAL_CODE,
    ).admitted


@given(
    st.sampled_from(["x*", "word~", "x_", "prefix*~"]),
    st.sampled_from(["ｐａｓｓｗｏｒｄ", "ａｐｉ＿ｋｅｙ", "ｔｏｋｅｎ"]),  # noqa: RUF001 - security variants
    st.sampled_from(["=", " = "]),
)
def test_audit_checks_both_sink_roles_instead_of_assuming_dominance(prefix, key, separator):
    from ocr_toolkit import review_runner
    from ocr_toolkit.dlp_audit.scanner import evaluate, scanner_identity

    value = prefix + key + separator + "syntheticShortCredential"
    item = dict(path="source", slot="b" * 32, digest="c" * 64, units=2, lines=1, error=None)
    request = dict(
        key="00" * 32, corpus="a" * 32, item=item, source=value, scanner=scanner_identity()
    )
    result = evaluate(request)
    comment = dict(
        path="source",
        start_line=1,
        end_line=1,
        existing_code=value,
        content="Inspect this source excerpt.",
    )
    proof = prove_opaque_code(comment, "source", lambda _path: value)
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [comment], "warnings": []},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    expected = {
        "text": check_text(value, budgets=BUDGETS, publication=True).admitted,
        "existing_code": "existing_code" in projected["comments"][0],
    }
    for role, admitted in expected.items():
        assert any(hit["unit"] == 0 and hit["role"] == role for hit in result["hits"]) == (
            not admitted
        )
