"""Synthetic material and representation regressions from the causal audit."""

# ruff: noqa: RUF001 -- deliberately exercise distinct Unicode data.

import pytest

from ocr_toolkit.common.redaction import has_sensitive_material
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(10_000, 40_000, 100)


@pytest.mark.parametrize(
    "value",
    (
        "assert obj.values == [\"login_password: ''\"]",
        'items = {"password": ""}',
        '[{"Authorization": ""}]',
        '[{"Authorization": "***"}]',
        'assert obj.values == ["token=***"]',
        'self.assertIn("token=***", text)',
    ),
)
def test_empty_or_masked_values_do_not_become_material_in_surrounding_syntax(value):
    assert not has_sensitive_material(value)


@pytest.mark.parametrize(
    "value",
    (
        'token = "" + "synthetic-secret"',
        'token = "" "synthetic-secret"',
        'token = "***" + "synthetic-secret"',
        'token = "".join(parts)',
        'token = "***actual-material"',
        'token = "unterminated',
        'token = "***"; password = "synthetic-secret"',
        '{"token": "***", "password": "synthetic-secret"}',
    ),
)
def test_mask_or_empty_prefix_does_not_exempt_adjacent_material(value):
    assert has_sensitive_material(value)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "Status: ⚠️",
        "Status: ℹ️",
        "Family: 👨‍👩‍👧",
        "Flag: 🇺🇳",
        "Key: 1️⃣",
    ),
)
def test_standard_unicode_presentation_is_not_laundering(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "a\u200db",
        "😀\u200d😀",
        "😀\u200dsecret",
        "⚠️\ufe0f",
        "x\u202ey",
        "\ufe0f",
        "⚠️ a\u200db",
        "&#x202e;hidden",
        "ℹ️ person@example.invalid",
    ),
)
def test_emoji_does_not_exempt_adjacent_or_unqualified_material(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "Last Updated: 2026-10-30",
        "snapshot/2026-10-30/source",
        "## 0.14.4 - 2026-10-30",
        "Releases 1.10.0-1.10.2",
        "Python 3.12/3.15",
        "for attempt in 1 2 3 4 5; do",
        'version = "4.26.0.20261006"',
        "00000000-0000-4000-8000-000000000001",
        "`@review.bot`",
        "Use `@review.bot` for discussion.",
    ),
)
def test_complete_technical_syntax_and_markdown_mentions_are_not_contacts(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "пользователь@example.com",
        '"quoted user"@example.invalid',
        "δοκιμή@παράδειγμα.δοκιμή",
        "user@[IPv6:2001:db8::1]",
        "Call 2026-10-30",
        "Phone: 1.10.0-1.10.2",
        "202 555-0114",
        "555-0114",
        "020 555 0114",
        "٠٢٠ ٥٥٥ ٠١١٤",
        "phone: 2025550114",
        "`person@example.invalid`",
        "`@example.invalid",
        "+1 202 555 0114",
    ),
)
def test_inverse_contacts_remain_protected_without_dns_or_default_region(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "202*555*0114",
        "202\\*555\\*0114",
        "<!-- 202*555*0114 -->",
        "2️⃣0️⃣2️⃣5️⃣5️⃣5️⃣0️⃣1️⃣1️⃣4️⃣",
        "202 5\u030155\u0301 0114",
    ),
)
def test_contact_decoration_cannot_manufacture_a_bare_safe_identifier(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        'assert obj.values == ["token=***"]',
        'self.assertIn("token=***", text)',
        "assert obj.values == [\"login_password: ''\"]",
    ),
)
def test_empty_masks_survive_every_material_representation(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "GH_TOKEN: ${{ github.token }}",
        "API_KEY: ${KEY}",
        'password: "{{ REF }}"',
        'token = "${TOKEN}"',
    ),
)
def test_complete_symbolic_fields_contain_no_literal_credential(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "token: write",
        "id-token: write",
        "permissions:\n  id-token: write\n  contents: read",
        "job:\n  permissions:\n    id-token: write",
        "permissions:\n  id-token: synthetic-material",
        "permissions:\n  nested:\n    token: write",
        "permissions:\n  id-token: write\ntoken: synthetic-material",
        'password: ${{ ref || "synthetic" }}',
        "password: ${REF:-synthetic-material}",
        "password: ${{ get() }}",
        'password: "${REF}" + "synthetic-material"',
        'password: "${REF}suffix"',
        "password: ${{ ref }}suffix",
        "password: ${{ ref }} # token: synthetic-material",
        "GH_TOKEN: ${{ github.token }}\nperson@example.invalid",
    ),
)
def test_reference_role_cannot_hide_literal_adjacent_or_unknown_material(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_symbolic_reference_does_not_waive_configured_values(monkeypatch):
    monkeypatch.setenv("OCR_LLM_TOKEN", "${REF}")
    assert check_text("token: ${REF}", budgets=BUDGETS, publication=True).reason == "secret"


def test_forbidden_representation_exhaustion_is_closed(monkeypatch):
    from ocr_toolkit.context.dlp import ForbiddenMatcher, admission
    from ocr_toolkit.context.dlp.markup import RepresentationLimit

    matcher = ForbiddenMatcher.compile(("protected material",))

    def exhausted(_value):
        raise RepresentationLimit("synthetic budget")

    monkeypatch.setattr(admission, "_display_normalize", exhausted)
    assert matcher.match_reason("candidate") == "limit"
    exhausted_matcher = ForbiddenMatcher.compile(("protected material",))
    assert exhausted_matcher.limited
    assert exhausted_matcher.match_reason("anything") == "limit"
    result = check_text("ordinary", budgets=BUDGETS, forbidden_matcher=exhausted_matcher)
    assert not result.admitted and result.reason == "limit"


def test_representation_token_and_depth_exhaustion_fail_closed(monkeypatch):
    from ocr_toolkit.context.dlp import markup

    original = markup._Budget
    monkeypatch.setattr(markup, "_Budget", lambda: original(remaining=2))
    checked = check_text("*one* *two* *three*", budgets=BUDGETS, publication=True)
    assert checked.reason == "limit" and not checked.admitted
    with pytest.raises(markup.RepresentationLimit):
        original().observe({"type": "text"}, markup.MAX_DEPTH + 1)
    budget = original(remaining=1)
    budget.html_event()
    with pytest.raises(markup.RepresentationLimit):
        budget.html_event()


def test_large_html_fragment_is_not_partially_interpreted():
    checked = check_text(
        "<!--" + "x" * 65_536 + "-->", budgets=TextBudgets(100_000, 200_000, 100), publication=True
    )
    assert checked.reason == "limit" and not checked.admitted


def test_source_span_search_exhaustion_is_closed(monkeypatch):
    from ocr_toolkit.context.dlp import email

    monkeypatch.setattr(email, "MAX_SOURCE_SEARCH", 1)
    checked = check_text("`@review.bot`", budgets=BUDGETS, publication=True)
    assert checked.reason == "limit" and not checked.admitted


def test_repeated_delimiter_mention_is_conservative_without_exact_position_proof():
    assert not check_text("`@review.bot` `@review.bot`", budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value", ("version < 2020.1.10.42", "version=4.26.0.20261006", "date ! 2020-01-01")
)
def test_typed_technical_data_and_digit_threshold_regressions(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "network _2001:db8::192.0.2.1/24",
        "network _2001:db8::192.0.2.1/32",
        "Call 2020.1.10.42",
        "555-0114",
        "256.0.0.0",
        "listen 127.0.0.1:99999",
        "55 - 0114",
    ),
)
def test_original_material_survives_lossy_display_interpretation(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "x*ｐａｓｓｗｏｒｄ=synthetic-material*",
        "x_ｐａｓｓｗｏｒｄ=synthetic-material_",
        'ａｐｉ＿ｋｅｙ="synthetic-material"',
    ),
)
def test_compatibility_normalization_cannot_remove_original_credential_boundaries(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        'token="",',
        'OCR_LLM_TOKEN="",',
        'assert x == "scheme:echo?token=***"',
        "https://example.invalid?token=***&next=1",
    ),
)
def test_query_material_classifier_keeps_complete_masks_and_empty_values(value):
    assert not has_sensitive_material(value)
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "https://example.invalid?token=***suffix",
        'https://example.invalid?token="***"+"synthetic"',
        "https://example.invalid?token=***&password=synthetic",
    ),
)
def test_query_masks_cannot_cover_suffixes_or_adjacent_fields(value):
    assert has_sensitive_material(value)


@pytest.mark.parametrize(
    "value",
    (
        "Final validation date: 2026-10-30.",
        "**Date: 2026-10-30.**",
        '"00000000-0000-4000-8000-000000000002.jsonl"',
        "size=1_000_000",
        "limit=50_000_000",
    ),
)
def test_technical_token_boundaries_do_not_activate_numeric_separators(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("value", ('"202*555*0114"', "202**555**0114", "202`555`0114"))
def test_literal_source_does_not_join_decorated_contacts_into_bare_identifiers(value):
    from ocr_toolkit.context.code_text import TextSink

    checked = check_text(
        value, budgets=BUDGETS, publication=True, allow_opaque_code=True, sink=TextSink.LITERAL_CODE
    )
    assert not checked.admitted and checked.reason == "pii"


@pytest.mark.parametrize("code", range(128))
def test_ascii_fast_paths_match_the_unicode_contract(code):
    import unicodedata

    from ocr_toolkit.common.redaction import strip_redaction_bypass_controls
    from ocr_toolkit.context.dlp.presentation import (
        canonical_whitespace,
        has_unsafe_controls,
        is_display_control,
    )

    char = chr(code)
    value = "prefix" + char + "suffix"
    expected = "".join(" " if c.isspace() else "" if is_display_control(c) else c for c in value)
    assert canonical_whitespace(value) == expected
    for allowed in ("\n", "\n\t"):
        assert has_unsafe_controls(value, allowed=allowed) == (
            unicodedata.category(char) == "Cc" and char not in allowed
        )
    assert has_unsafe_controls(value, display=True) == is_display_control(char)
    assert strip_redaction_bypass_controls(value) == "".join(
        c for c in value if unicodedata.category(c) not in {"Cc", "Cf", "Zl", "Zp"} or c in "\n\r\t"
    )


@pytest.mark.parametrize(
    "value", ("uses: vendor/action@[0-9a-f]{40}", "pattern = user@[a-z]+", "literal [x]@[A-Z]")
)
def test_regex_character_classes_do_not_become_email_address_literals(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        "user@[192.0.2.100]",
        "user@[999.999.999.999]",
        "user@[IPv6:2001:db8::1]",
        "user@[IPv6:malformed]",
        "user@[tag:synthetic]",
    ),
)
def test_numeric_and_tagged_address_literals_remain_protected_without_deliverability_checks(value):
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "pii"


@pytest.mark.parametrize(
    "value",
    (
        'condition?token="***"&&"synthetic-material":null',
        'condition?password=""&&"synthetic-material":null',
        'token="***"&&"synthetic-material"',
    ),
)
def test_ternary_or_boolean_syntax_cannot_supply_query_mask_authority(value):
    assert has_sensitive_material(value)
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_real_parser_cannot_combine_independent_block_and_inline_depths():
    value = "> " * 13 + "*" * 16 + "synthetic" + "*" * 16
    result = check_text(value, budgets=BUDGETS, publication=True)
    assert not result.admitted and result.reason == "limit"
    from ocr_toolkit.context.dlp.markup import _INLINE_SCOPE, interpret_markdown

    assert _INLINE_SCOPE.get() is None
    assert interpret_markdown("[*safe*](relative)").visible.strip() == "safe"
    assert _INLINE_SCOPE.get() is None


def test_native_emphasis_nodes_are_reserved_before_their_construction(monkeypatch):
    from mistune import inline_parser

    from ocr_toolkit.context.dlp.markup import RepresentationLimit, interpret_markdown

    original = inline_parser.finalize_emphasis_tokens
    calls = []

    def observed(*args):
        calls.append(True)
        return original(*args)

    monkeypatch.setattr(inline_parser, "finalize_emphasis_tokens", observed)
    with pytest.raises(RepresentationLimit):
        interpret_markdown("*" * 20_000 + "safe" + "*" * 20_000)
    assert calls == []


@pytest.mark.parametrize("fold", (True, False))
def test_compatibility_expansion_is_bounded_before_derived_processing(fold):
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit, bounded_nfkc

    with pytest.raises(RepresentationLimit, match="character expansion"):
        bounded_nfkc("\ufdfa" * 1000, fold=fold)
    with pytest.raises(RepresentationLimit, match="byte expansion"):
        bounded_nfkc("\ufdfa" * 200, fold=fold)
    assert bounded_nfkc("Straße", fold=fold) == ("strasse" if fold else "Straße")
    assert (
        check_text("\ufdfa" * 1000, budgets=TextBudgets(2000, 8000, 10), publication=True).reason
        == "limit"
    )


def test_invalid_normalization_input_is_closed_and_decoded_carrier_bounds_are_used():
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit, bounded_nfkc

    with pytest.raises(RepresentationLimit):
        bounded_nfkc("\ud800")
    # Entity carriers have their own original size, not the shorter decoded size.
    assert bounded_nfkc("\ufdfa" * 200, original="&#65018;" * 200)


def test_casefold_expansion_and_unbound_parser_finalization_are_closed():
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit, bounded_nfkc
    from ocr_toolkit.context.dlp.markup import _PARSER

    with pytest.raises(RepresentationLimit, match="character expansion"):
        bounded_nfkc("ß" * 5000, original="x" * 1000, fold=True)
    with pytest.raises(RepresentationLimit, match="unbound inline"):
        _PARSER.inline.finalize_tokens([], 0)


@pytest.mark.parametrize("value", ("size = 128 * 1024", "capacity = 512 * 1024"))
def test_numeric_operator_role_requires_exact_source_proof(value):
    from ocr_toolkit.context.code_text import TextSink
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    source = "def compute():\n    " + value + "\n"
    excerpt = source.splitlines()[1]
    proof = prove_opaque_code(
        {"path": "sample", "start_line": 2, "end_line": 2, "existing_code": excerpt},
        "sample",
        lambda _: source,
    )
    assert proof.existing_verified and proof.existing_context is not None
    kwargs = dict(
        sink=TextSink.LITERAL_CODE, allow_opaque_code=True, code_context=proof.existing_context
    )
    assert check_text(excerpt, budgets=BUDGETS, publication=True, **kwargs).admitted
    assert not check_text(excerpt, budgets=BUDGETS, publication=True).admitted
    for contact in ("012**345**6789", "+1*202*555*0100", "phone: 202*555*0100"):
        assert not check_text(
            excerpt + "; " + contact, budgets=BUDGETS, publication=True, **kwargs
        ).admitted
    assert not check_text(
        excerpt + "; pass*word=synthetic-material", budgets=BUDGETS, publication=True, **kwargs
    ).admitted


@pytest.mark.parametrize("value", ("metric_2020.1.10", "opaque_123.456.789"))
@pytest.mark.parametrize("literal", (False, True))
def test_identifier_underscores_cannot_create_an_independent_phone_fragment(value, literal):
    from ocr_toolkit.context.code_text import TextSink

    sink = TextSink.LITERAL_CODE if literal else TextSink.PROSE
    assert check_text(value, budgets=BUDGETS, publication=True, sink=sink).admitted


@pytest.mark.parametrize("encoding", ("plain", "html", "mermaid"))
def test_unmatched_marker_phone_is_protected_in_prose_and_projection(encoding):
    from ocr_toolkit import review_runner

    value = "202 _555-0114"
    if encoding != "plain":
        opener = "&#" if encoding == "html" else "#"
        value = "".join(f"{opener}{ord(c)};" for c in value)
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "pii"
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


@pytest.mark.parametrize(
    "suffix", (",synthetic", ";synthetic", ")synthetic", "]synthetic", "}synthetic", "%2Csynthetic")
)
@pytest.mark.parametrize("mask", ("***", '"***"', "''"))
def test_query_mask_must_cover_the_whole_uri_value(mask, suffix):
    value = f"https://example.invalid?token={mask}{suffix}"
    assert has_sensitive_material(value)
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "secret"


@pytest.mark.parametrize(
    "value",
    (
        'payload = """\npermissions:\n  password: write\n"""',
        "const payload = `\npermissions:\n  password: write\n`;",
        "payload: |\n  permissions:\n    password: write",
        "payload: >\n  permissions:\n    password: write",
        'payload: "\n  permissions:\n    password: write\n"',
        "payload: text\n  permissions:\n    password: write",
        "parent:\n  child:\n    other: item\n permissions:\n  password: write",
        "permissions:\n  password: write\nunknown source trailer",
    ),
)
def test_enclosing_text_cannot_declassify_a_literal_credential(value):
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "secret"


@pytest.mark.parametrize(
    "value",
    (
        "token=***,synthetic-secret",
        "https://example.invalid?token=***#password=synthetic-secret",
        '{"url":"https://example.invalid?token=***","password":"synthetic-secret"}',
        '{"a":"https://example.invalid?token=***","b":"https://example.invalid?%74oken=synthetic-secret"}',
    ),
)
def test_safe_query_value_cannot_suppress_an_adjacent_material_region(value):
    from ocr_toolkit import review_runner

    assert has_sensitive_material(value)
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "secret"
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


@pytest.mark.parametrize(
    "value",
    (
        "https://example.invalid?token=***#section",
        '{"url":"https://example.invalid?token=***","public":"word"}',
        '["https://example.invalid?token=***","https://example.invalid?api_key=***"]',
    ),
)
def test_complete_masks_keep_unrelated_wrapper_and_fragment_data(value):
    assert not has_sensitive_material(value)
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("prefix", ("", "https://example.invalid?"))
@pytest.mark.parametrize("space", (" ", "  ", "\t", "\n", "\u2000"))
def test_value_whitespace_cannot_grant_empty_assignment_authority(prefix, space):
    value = prefix + "password=" + space + "synthetic-secret"
    assert has_sensitive_material(value)
    assert not check_text(
        value, budgets=BUDGETS, publication=True, allow_horizontal_tabs=True
    ).admitted
