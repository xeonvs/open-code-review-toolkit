"""Structured markup variation across production admission and real Markdown rendering."""

import re
from html import unescape

import mistune
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(20_000, 80_000, 200)
WORDS = st.text(alphabet="abcdefghijk éΩ中", max_size=50)
HTML_RENDER = mistune.create_markdown(escape=False)

JSON_TEXT = st.recursive(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(-(2**63), 2**63 - 1),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(st.characters(blacklist_categories=("Cs",)), max_size=20),
    ),
    lambda child: st.one_of(
        st.lists(child, max_size=3),
        st.dictionaries(
            st.text(st.characters(blacklist_categories=("Cs",)), max_size=8), child, max_size=3
        ),
    ),
    max_leaves=12,
)


@given(JSON_TEXT)
def test_bounded_complete_json_text_matches_the_actual_consumer(value):
    from ocr_toolkit.context.dlp.result_prose import bounded_prose_text

    expected = "" if value is None else str(value)
    budgets = TextBudgets(
        max(1, len(expected)), max(1, len(expected.encode())), expected.count("\n") + 1
    )
    assert bounded_prose_text(value, budgets) == expected.strip()


@given(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
    st.integers(1, 5),
    st.sampled_from(("references", "code-boundary", "structured")),
)
def test_prepared_fragments_remain_image_free_after_real_document_composition(label, width, shape):
    import json
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from ocr_toolkit import review_runner
    from ocr_toolkit.ocr_result import TOOLKIT_RESULT_KEY, load_ocr_result
    from tests.test_dlp_composition import rendered_bodies
    from tests.test_review_receipt_v13 import _receipt_v13

    uri = "https://example.invalid/pixel"
    if shape == "references":
        contents = [f"![{label}]", f"[{label}]: {uri}"]
    elif shape == "code-boundary":
        delimiter = "`" * width
        contents = [delimiter, delimiter + f"![{label}]({uri})" + delimiter]
    else:
        contents = [{"detail": [rf"\![{label}]({uri})"]}]
    projected, _, filtered = review_runner._publication_projection(
        {
            "status": "success",
            "comments": [{"path": "sample", "line": 1, "content": text} for text in contents],
        },
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert not filtered
    with TemporaryDirectory() as directory:
        path = Path(directory).resolve() / "result.json"
        path.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
        path.chmod(0o600)
        reloaded = load_ocr_result(path)
    for body in rendered_bodies(reloaded["comments"]):
        assert "<img " not in HTML_RENDER(body)


@given(st.text(alphabet="abcdef0123+.-:/?@%# \n\t\u0130\u0131\u017f\u212a", max_size=120))
def test_linear_uri_prefix_search_preserves_the_unanchored_redaction_contract(prefix):
    from ocr_toolkit.common.redaction import _is_url_userinfo_candidate, redact_url_userinfo_only

    value = prefix + "42+https://user%40name:material@localhost/resource"
    original = re.sub(
        r"(?i)([a-z][a-z0-9+.-]*://)([^/?#@]+)@(?=[^/?#\s@]+(?:[/?#]|[\s,;.!)]|$))",
        lambda match: f"{match[1]}***@" if _is_url_userinfo_candidate(match[2]) else match[0],
        value,
    )
    assert redact_url_userinfo_only(value) == original


STRUCTURES = st.recursive(
    st.text(alphabet="abcdef éΩ中", min_size=1, max_size=12),
    lambda child: st.one_of(
        child.map(lambda text: f'<span title="{text}">visible</span>'),
        child.map(lambda text: f"<!-- {text} -->"),
        child.map(lambda text: f"**{text}**"),
        child.map(lambda text: f"`{text}`"),
        child.map(lambda text: f"[{text}](https://example.invalid/)"),
        st.tuples(child, child).map(lambda pair: "\n\n".join(pair)),
    ),
    max_leaves=12,
)


@given(WORDS, st.sampled_from(("<!-- {} -->", '<span title="{}">ok</span>', "<List{}>")))
def test_html_is_literal_and_idempotent(word, wrapper):
    value = wrapper.format(word)
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, checked
    assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text
    assert unescape(checked.text) == value
    rendered = HTML_RENDER(checked.text)
    assert "<span" not in rendered and "<!--" not in rendered and "<List" not in rendered


@given(WORDS, st.integers(1, 20), st.sampled_from((" ", "\n", " &amp; ", " Ω ")))
def test_repeated_commands_keep_exact_delimiter_authority(prefix, count, separator):
    value = prefix + " " + separator.join(["`@mr.bot resolve`"] * count)
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, checked
    assert checked.text == value.strip()
    assert not check_text(
        value + " author@example.invalid", budgets=BUDGETS, publication=True
    ).admitted


@given(st.integers(1, 100))
def test_code_delimiter_width_does_not_invent_an_address(width):
    marker = "`" * width
    value = "Reply " + marker + "@mr.bot resolve" + marker + "."
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, (width, checked)
    assert not check_text(
        value + " author@example.invalid", budgets=BUDGETS, publication=True
    ).admitted


@given(
    WORDS,
    st.sampled_from(("author@example.invalid", "+1 202-555-0117", "password=synthetic-value")),
    st.sampled_from(
        (
            "<!-- {} -->",
            '<span title="{}">ok</span>',
            '[guide](https://example.invalid/ "{}")',
            "![{}](https://example.invalid/)",
            "`{}`",
        )
    ),
)
def test_any_material_carrier_keeps_protection(prefix, material, wrapper):
    assert not check_text(
        prefix + " " + wrapper.format(material), budgets=BUDGETS, publication=True
    ).admitted


@given(
    st.sampled_from(("http", "https")),
    WORDS,
    st.sampled_from(("", "#section", "?page=2", "/guide%20index")),
)
def test_safe_links_remain_links(scheme, word, suffix):
    value = f"[{word}]({scheme}://example.invalid/{suffix})"
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, checked
    assert checked.text == value
    assert "<img" not in HTML_RENDER(checked.text)


@given(
    st.integers(0, 3),
    st.sampled_from(
        (
            "javascript:hello",
            "data:text/plain,hello",
            "https://reader@example.invalid/",
            "https://example.invalid/\nmore",
        )
    ),
)
def test_encoded_destinations_cannot_acquire_link_authority(layers, destination):
    from urllib.parse import quote

    for _ in range(layers):
        destination = quote(destination, safe="")
    value = f"[guide]({destination})"
    checked = check_text(value, budgets=BUDGETS, publication=True)
    # A raw newline can make this ordinary text, not a Markdown link. Only
    # parsed/active destinations acquire URL authority and must be rejected.
    if checked.admitted:
        rendered = HTML_RENDER(checked.text)
        assert "href=" not in rendered and "src=" not in rendered


@given(STRUCTURES)
def test_composed_markup_remains_inert_and_has_a_fixed_point(value):
    checked = check_text(value, budgets=BUDGETS, publication=True)
    if checked.admitted:
        assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text
        rendered = HTML_RENDER(checked.text)
        assert "<span title=" not in rendered and "<!--" not in rendered and "<img" not in rendered
    else:
        assert checked.reason in {"limit", "laundering"}
    assert not check_text(
        value + " author@example.invalid", budgets=BUDGETS, publication=True
    ).admitted


@given(
    st.text(alphabet="abcdefghijk", min_size=1, max_size=12),
    st.sampled_from(("\uff20", "\ufe6b")),
    st.sampled_from(("link", "title", "html-attribute", "comment")),
    st.integers(min_value=1, max_value=2),
)
def test_percent_decoding_then_nfkc_retains_email_protection(name, at, shape, layers):
    from urllib.parse import quote

    value = name + at + "example.invalid"
    for _ in range(layers):
        value = quote(value, safe="")
    if shape == "link":
        value = f"[guide](https://example.invalid/{value})"
    elif shape == "title":
        value = f'[guide](https://example.invalid/ "{value}")'
    elif shape == "html-attribute":
        value = f'<span data-value="{value}">guide</span>'
    else:
        value = f"<!-- {value} -->"
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@given(st.sampled_from(("[", "]", "*", "_", "~", "\\", "`")), st.integers(1, 30))
def test_literal_delimiter_runs_remain_inert_and_idempotent(delimiter, count):
    value = "prefix " + delimiter * count + " literal!"
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted
    assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text
    assert "<a " not in HTML_RENDER(checked.text)
