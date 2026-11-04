"""Optional synthetic qualification probes, never a production admission policy.

Run in the isolated environment documented in docs/development.md. The normal
suite skips unavailable research packages; runtime dependencies do not expand.
"""

import pytest


def test_tree_sitter_recovered_expression_is_not_complete_source_proof():
    tree_sitter = pytest.importorskip("tree_sitter")
    grammar = pytest.importorskip("tree_sitter_c")
    parser = tree_sitter.Parser(tree_sitter.Language(grammar.language()))

    def roles(source):
        root = parser.parse(source.encode()).root_node
        pending, found = [root], set()
        while pending:
            node = pending.pop()
            found.add(node.type)
            pending.extend(node.children)
        return root.has_error, found

    failed, executable = roles("int f(){ return 7 * 1234567; }")
    assert not failed and "binary_expression" in executable
    failed, recovered = roles("int f(){ return (7 * 1234567; }")
    assert failed and "binary_expression" in recovered
    for source, kind in (
        ('char *x="7 * 1234567";', "string_literal"),
        ("// 7 * 1234567\n", "comment"),
    ):
        failed, data = roles(source)
        assert not failed and kind in data and "binary_expression" not in data


def test_pygments_numeric_token_does_not_distinguish_complete_from_broken_program():
    lexers = pytest.importorskip("pygments.lexers")
    lexer = lexers.CLexer()

    def token_roles(source):
        return [
            str(token)
            for _, token, value in lexer.get_tokens_unprocessed(source)
            if "1234567" in value
        ]

    assert token_roles("int f(){ return 7 * 1234567; }") == token_roles(
        "int f(){ return (7 * 1234567; }"
    )
    assert token_roles('char *x="7 * 1234567";') == ["Token.Literal.String"]
    assert token_roles("// 7 * 1234567\n") == ["Token.Comment.Single"]


def test_piisa_international_lexical_candidate_omission_is_not_contact_absence():
    candidate = pytest.importorskip(
        "pii_extract_plg_regex.modules.en.any.international_phone_number"
    )
    regex = pytest.importorskip("regex")
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    # Qualify the plugin's lexical stage only, without inventing a default region
    # or claiming its country/context task pipeline has been qualified.
    pattern = regex.compile(candidate.PII_TASKS[0]["task"], regex.VERBOSE)
    assert pattern.search("+1 202 555 0114")
    assert not pattern.search("phone: 1 202 555 0114")
    for contact in ("+1 202 555 0114", "phone: 1 202 555 0114"):
        assert not check_text(
            contact, budgets=TextBudgets(1000, 4000, 10), publication=True, enabled=True
        ).admitted
    for technical in ("version 2026.10.19", "updated 2026-10-23 08:52 UTC"):
        assert not pattern.search(technical)
        assert check_text(
            technical, budgets=TextBudgets(1000, 4000, 10), publication=True, enabled=True
        ).admitted
