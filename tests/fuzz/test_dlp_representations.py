"""Independent material controls for typed data and composed representations."""

import html
from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit import review_runner
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
    from ocr_toolkit.context.code_text import TextSink
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    value = f"    capacity = {left} * {right}"
    source = "def compute():\n" + value + "\n"
    proof = prove_opaque_code(
        {"path": "sample", "start_line": 2, "end_line": 2, "existing_code": value},
        "sample",
        lambda _: source,
    )
    assert proof.existing_verified and proof.existing_context is not None
    kwargs = dict(
        sink=TextSink.LITERAL_CODE, allow_opaque_code=True, code_context=proof.existing_context
    )
    assert check_text(value, budgets=BUDGETS, publication=True, **kwargs).admitted
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        value + "; " + encode(material, encoding), budgets=BUDGETS, publication=True, **kwargs
    ).admitted


@given(st.integers(100, 999), st.integers(100, 199), st.sampled_from(("_", "*", "~", "`")))
def test_markup_cannot_obscure_an_independently_phone_shaped_fragment(prefix, tail, marker):
    from ocr_toolkit.context.code_text import TextSink

    value = f"{prefix} {marker}555-0{tail}"
    assert not check_text(
        value, budgets=BUDGETS, publication=True, sink=TextSink.LITERAL_CODE
    ).admitted


@given(st.text(alphabet="abcdefghijk", min_size=1, max_size=20), st.integers(100, 999))
def test_fragment_detection_preserves_identifier_boundaries(name, number):
    value = f"{name}_{number}.456.789"
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@given(
    st.sampled_from(("token", "api_key", "%74oken", "password")),
    st.sampled_from(("***", '"***"', "''")),
    st.sampled_from((",", ";", ")", "]", "}", "%2C", "+", "=")),
    st.text(alphabet="abcdefghijkLMNOPQ0123456789", min_size=1, max_size=40),
    st.sampled_from(("{}", 'value = "{}"', "value = '{}'")),
    ENCODING,
)
def test_nonempty_query_suffix_never_inherits_mask_authority(
    key, mask, separator, suffix, wrapper, encoding
):
    value = encode(
        wrapper.format(f"https://example.invalid?{key}={mask}{separator}{suffix}"), encoding
    )
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {
            "status": "success",
            "warnings": [],
            "comments": [{"path": "sample", "line": 1, "content": value}],
        },
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.sampled_from(("password", "token", "api_key")),
    st.sampled_from(("read", "write", "none")),
    st.sampled_from(
        ("{}", 'payload = """\n{}\n"""', "const x = `\n{}\n`;", "payload: |\n{}", "payload: >\n{}")
    ),
    st.integers(0, 3),
)
def test_foreign_or_scalar_enclosure_cannot_grant_permission_role(key, access, wrapper, indent):
    from ocr_toolkit import review_runner
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    block = " " * indent + "permissions:\n" + " " * (indent + 2) + key + ": " + access
    source = wrapper.format(block)
    assert check_text(source, budgets=BUDGETS, publication=True).reason == "secret"
    lines = source.splitlines()
    number = next(i for i, line in enumerate(lines, 1) if line.strip() == key + ": " + access)
    comment = {
        "path": "sample",
        "start_line": number,
        "end_line": number,
        "content": "Inspect the field.",
        "existing_code": lines[number - 1],
    }
    proof = prove_opaque_code(comment, "sample", lambda _: source)
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _: proof,
    )
    assert "existing_code" not in projected["comments"][0]


@given(
    st.sampled_from(("password", "token", "api_key", "private_token")),
    st.text(alphabet="abcdefghijLMNOPQ0123456789", min_size=1, max_size=30),
    st.sampled_from(("field", "query", "fragment")),
    ENCODING,
)
def test_masked_uri_and_adjacent_material_are_independent(key, material, placement, encoding):
    import json

    safe = "https://example.invalid?token=***"
    if placement == "field":
        value = json.dumps({"url": safe, key: material}, separators=(",", ":"))
    elif placement == "query":
        value = json.dumps(
            {"a": safe, "b": f"https://example.invalid?{key}={material}"}, separators=(",", ":")
        )
    else:
        value = safe + f"#{key}={material}"
    assert not check_text(encode(value, encoding), budgets=BUDGETS, publication=True).admitted


@given(
    st.sampled_from(("password", "token", "%74oken")),
    st.text(alphabet=" \t\n\u2000", min_size=1, max_size=12),
    st.sampled_from(("", "https://example.invalid?")),
    st.text(alphabet="abcdefghijLMNOPQ0123456789", min_size=1, max_size=30),
    ENCODING,
)
def test_leading_value_whitespace_never_proves_absent_material(
    key, space, prefix, material, encoding
):
    value = encode(prefix + key + "=" + space + material, encoding)
    assert not check_text(
        value, budgets=BUDGETS, publication=True, allow_horizontal_tabs=True
    ).admitted


@given(
    st.sampled_from(("%74oken", "pa%73sword", "access%5Ftoken", "api%5Fkey")),
    st.sampled_from(("?", "&", ";", ";;")),
    st.sampled_from(("", "https://example.invalid?public=word")),
    st.text(alphabet="abcdefghijLMNOPQ0123456789", min_size=1, max_size=30),
    ENCODING,
)
def test_query_key_separators_cannot_hide_encoded_material(
    key, separator, prefix, material, encoding
):
    value = encode(prefix + separator + key + "=" + material, encoding)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.sampled_from(("password", "token", "api_key")),
    st.sampled_from(('"', "'")),
    st.sampled_from((";", ",", ")", "]", "}", "#", "\n")),
    st.sampled_from(("{}", '"{}"', "'{}'", "value = {}")),
    st.text(alphabet="abcdefghijLMNOPQ0123456789", min_size=1, max_size=30),
    ENCODING,
)
def test_quote_runs_cannot_prove_an_empty_prefix_is_the_whole_value(
    key, quote, punctuation, wrapper, material, encoding
):
    from ocr_toolkit.common.redaction import has_sensitive_material

    source = wrapper.format(f"{key} = {quote * 3}{punctuation}{material}{quote * 3}")
    assert has_sensitive_material(source, values=())
    value = encode(source, encoding)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=20), st.booleans())
def test_malformed_marked_sections_never_escape_publication_or_forbidden_checks(keyword, closed):
    from ocr_toolkit import review_runner
    from ocr_toolkit.context.dlp import ForbiddenMatcher

    value = "<div>\n<![" + keyword + ("]>" if closed else "[") + "\n</div>"
    decision = check_text(value, budgets=BUDGETS, publication=True)
    assert not decision.admitted
    matcher = ForbiddenMatcher.compile((value,))
    assert matcher.match_details("ordinary text")[0] in {None, "limit"}
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.sampled_from(("token", "login_password", "api_key")),
    st.sampled_from(("", "***", "${REF}", "${{ source.value }}", "{{ NAME }}")),
    st.sampled_from(("html", "numeric", "mermaid")),
    st.sampled_from(('"', "'")),
    SENSITIVE,
    ENCODING,
)
def test_encoded_absent_field_keeps_its_original_carrier_and_independent_material(
    key, mask, encoding, quote, material, outer_encoding
):
    field = f'"{key}": "{mask}"'
    carrier = "(" + quote + encode(field, encoding) + quote + ",)"
    assert check_text(carrier, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        carrier + "; " + encode(material, outer_encoding), budgets=BUDGETS, publication=True
    ).admitted
    nonempty = "(" + quote + encode(f'"{key}": "{material}"', encoding) + quote + ",)"
    assert not check_text(nonempty, budgets=BUDGETS, publication=True).admitted


@given(st.sampled_from(("numeric", "mermaid")), st.sampled_from(('"', "'")), st.integers(3, 5))
def test_encoded_key_cannot_make_ambiguous_quote_runs_an_absent_carrier(encoding, quote, size):
    value = (
        encode("password", encoding) + " = " + quote * size + ";synthetic-material" + quote * size
    )
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(
    st.text(alphabet="abcdef_-/", min_size=1, max_size=40),
    st.sampled_from(("token", "password", "api_key")),
    st.sampled_from(('"', "'")),
    st.sampled_from(("{}", "assert value == {}", "items = [{}]")),
    st.text(alphabet="abcdefghijLMNOPQ0123456789", min_size=1, max_size=30),
)
def test_unquoted_mask_keeps_its_whole_original_carrier(prefix, key, quote, wrapper, material):
    safe = wrapper.format(quote + prefix + "/" + key + "=***" + quote)
    assert check_text(safe, budgets=BUDGETS, publication=True).admitted
    unsafe = wrapper.format(quote + prefix + "/" + key + "=***" + material + quote)
    assert not check_text(unsafe, budgets=BUDGETS, publication=True).admitted


@given(
    st.sampled_from(("token", "password", "api_key")),
    st.sampled_from(("***", '"***"', "${REF}")),
    st.sampled_from(("html", "numeric", "mermaid")),
    st.text(alphabet=" \t\n", min_size=1, max_size=12),
    st.sampled_from(("", "+ ")),
    st.integers(1, 4),
)
def test_carrier_completion_crosses_newlines_and_parentheses(
    key, mask, encoding, space, operator, depth
):
    field = encode(key + "=" + mask, encoding)
    carrier = "(" * depth + '"' + field + '"' + ")" * depth
    value = carrier + space + operator + '"synthetic-material"'
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.sampled_from(("token", "login_password", "api_key")),
    st.sampled_from(("", "***", "${REF}", "{{ NAME }}")),
    st.sampled_from(("html", "numeric", "mermaid")),
    st.sampled_from(('"', "'")),
    st.text(alphabet=" \t\n,;()[]{}+.#/\"'_abc012-", max_size=40),
)
def test_encoded_absent_carrier_matches_the_canonical_raw_field(key, absent, encoding, quote, tail):
    raw = "('" + key + '="***"' + "')" + tail
    encoded = "(" + quote + encode(f'"{key}": "{absent}"', encoding) + quote + ")" + tail
    assert (
        check_text(encoded, budgets=BUDGETS, publication=True).admitted
        == check_text(raw, budgets=BUDGETS, publication=True).admitted
    )


@given(
    st.sampled_from(("password", "token", "api_key")),
    st.sampled_from(('""', '"***"', "${REF}", '"${REF}"')),
    st.sampled_from(("", "# note", "// note", "/* note */", "<!-- note -->")),
    st.sampled_from(("\n", "\r\n", "\r")),
    st.sampled_from(("+ ", "", "or ")),
    ENCODING,
)
def test_empty_or_reference_field_keeps_its_key_through_multiline_continuation(
    key, value, comment, newline, operator, encoding
):
    source = key + "=" + value + " " + comment + newline + operator + '"synthetic-material"'
    assert not check_text(encode(source, encoding), budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {
            "status": "success",
            "comments": [{"path": "sample", "line": 1, "content": encode(source, encoding)}],
        },
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.sampled_from(('"', "'")),
    st.integers(2, 5),
    st.sampled_from(("token", "%74oken", "password", "api_key")),
    st.sampled_from((";", ",", ")", "]", "}", "#", " ")),
    ENCODING,
)
def test_ambiguous_uri_carrier_opening_cannot_prove_an_empty_query(
    quote, run, key, separator, encoding
):
    source = (
        "payload = "
        + quote * run
        + "https://example.invalid?"
        + key
        + "=***"
        + quote
        + separator
        + "synthetic-material"
        + quote * run
    )
    assert not check_text(encode(source, encoding), budgets=BUDGETS, publication=True).admitted


@given(
    st.sampled_from(("password", "token", "api_key")),
    st.sampled_from(('""', '"***"', "${REF}", '"${REF}"')),
    st.sampled_from(("", " # note", " // note", " /* note */")),
    st.sampled_from(
        (' + "synthetic-material"', '\n + "synthetic-material"', ' "synthetic-material"')
    ),
    ENCODING,
)
def test_separately_encoded_continuation_cannot_gain_an_invented_field_boundary(
    key, value, comment, continuation, encoding
):
    if comment.startswith((" #", " //")) and "\n" not in continuation:
        continuation = "\n" + continuation
    source = key + "=" + value + comment + encode(continuation, encoding)
    assert not check_text(source, budgets=BUDGETS, publication=True).admitted
    projected, _, _ = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": source}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []


@given(
    st.text(
        st.characters(categories=("Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Nd", "Pc")),
        min_size=1,
        max_size=24,
    ).filter(str.isidentifier),
    ENCODING,
)
def test_unicode_next_field_preserves_empty_value_and_independent_material(name, encoding):
    # A prefix avoids generating a sensitive key and keeps the oracle structural.
    source = 'password=""\npublic_' + name + "=ready"
    baseline = check_text(
        encode("public_" + name + "=ready", encoding), budgets=BUDGETS, publication=True
    )
    # Identifier syntax can contain variation selectors; independent display
    # controls must retain their rejection rather than gain a field-name waiver.
    assert (
        check_text(encode(source, encoding), budgets=BUDGETS, publication=True).admitted
        == baseline.admitted
    )
    assert not check_text(
        encode(source + ' api_key="synthetic-material"', encoding),
        budgets=BUDGETS,
        publication=True,
    ).admitted
