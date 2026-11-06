"""Safe presentation does not erase material or grant source authority."""

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text

BUDGETS = TextBudgets(20_000, 80_000, 200)


@pytest.mark.parametrize(
    "value",
    (
        "Read [documentation](https://example.invalid/guide).",
        "See [local](../guide.md#usage) and [section](#usage).",
        "Read [guide](docs/My%20Guide.md).",
        "Use `List<Entry>` and `(?P<label>[a-z]+)`.",
        "<!-- generated section marker -->",
        "Stage one<br/>stage two",
        "Reply `@mr.bot resolve`.",
        "Use `@mr.bot` and `@mr.bot`.",
        "# Reply `@mr.bot resolve`\n\nNext paragraph `@mr.bot`.",
    ),
)
def test_benign_markup_is_prepared_and_idempotent(value):
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted, checked
    again = check_text(checked.text, budgets=BUDGETS, publication=True)
    assert again.admitted and again.text == checked.text


@pytest.mark.parametrize(
    "value",
    (
        "[guide](javascript:alert%281%29)",
        "[guide](data:text/html,hello)",
        "[guide](https://reader@example.invalid/guide)",
        "[guide](https://example.invalid/%0ahello)",
        "[guide](//example.invalid/guide)",
        "[guide](%20//example.invalid/path)",
        "[guide](%2520%252F%252Fexample.invalid/path)",
        "[guide](https://[broken/guide)",
        "[guide](java%73cript:hello)",
        "[guide](https://example.invalid/%FF)",
        "[guide](https://example.invalid:99999/)",
        "[guide](http:///missing)",
        "[guide](https://example.invalid/%5cpath)",
        "[guide](javascript%25253Ahello)",
        "[guide]: javascript:hello\n\nordinary text",
    ),
)
def test_unsafe_destinations_are_rejected(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "material",
    (
        "author@example.invalid",
        "+1 202-555-0117",
        "password=synthetic-value",
    ),
)
@pytest.mark.parametrize(
    "wrapper",
    (
        "{}",
        "<!-- {} -->",
        '<span title="{}">visible</span>',
        "[guide](https://example.invalid/ '{}')",
        "`{}`",
        "`@mr.bot` {} `@mr.bot`",
    ),
)
def test_protected_material_stays_protected(material, wrapper):
    assert not check_text(wrapper.format(material), budgets=BUDGETS, publication=True).admitted


def test_html_and_images_are_visible_but_inert():
    from html import unescape

    checked = check_text(
        '<img src="https://example.invalid/pixel">\n\n![plot](https://example.invalid/plot)',
        budgets=BUDGETS,
        publication=True,
    )
    assert checked.admitted
    assert "<img" not in checked.text and "![" not in checked.text
    assert (
        "example.invalid/pixel" in unescape(checked.text) and "example.invalid/plot" in checked.text
    )
    assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text


def test_projection_expansion_has_an_independent_budget():
    value = "<b>" * 8
    checked = check_text(value, budgets=TextBudgets(len(value), 1000, 10), publication=True)
    assert not checked.admitted and checked.reason == "limit"


def test_finalization_prepares_prose_without_filtering_or_mutating_input():
    from html import unescape

    from ocr_toolkit.context.dlp.markup import interpret_markdown

    content = "Read [guide](https://example.invalid). <!-- marker -->"
    payload = {"status": "success", "comments": [{"path": "sample", "line": 1, "content": content}]}
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert not filtered and state["state"] == "passed"
    assert payload["comments"][0]["content"] == content
    prepared = projected["comments"][0]["content"]
    assert "<!--" not in prepared
    assert unescape(prepared) == content
    assert interpret_markdown(prepared).links == ("https://example.invalid",)
    again, state, filtered = review_runner._publication_projection(
        projected, forbidden=(), allowed_tools=frozenset()
    )
    assert again == projected and not filtered


def test_diagram_encoding_remains_owned_by_its_sink():
    value = "List<Entry>"
    checked = check_text(value, budgets=BUDGETS, publication=True, sink=TextSink.DIAGRAM_LABEL)
    assert checked.admitted and checked.text == value


@pytest.mark.parametrize(
    "value",
    (
        "\uff40@mr.bot\uff40",
        "&#96;@mr.bot&#96;",
        "\\`@mr.bot\\`",
        "`` `@mr.bot` ``",
        "`@mr.bot` outside`@mr.bot",
    ),
)
def test_decoding_and_other_spans_cannot_supply_delimiter_authority(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    ("<!-- ![x](https://example.invalid/pixel) -->", '<span title="**text** `literal`">ok</span>'),
)
def test_html_literal_projection_cannot_activate_its_inner_markdown(value):
    from html import unescape

    import mistune

    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted
    assert unescape(checked.text) == value
    rendered = mistune.create_markdown(escape=False)(checked.text)
    assert "<img" not in rendered and "<span" not in rendered and "<strong" not in rendered
    assert "<code" not in rendered


def test_actual_persisted_current_result_rechecks_prepared_prose(tmp_path):
    import json

    from ocr_toolkit.ocr_result import TOOLKIT_RESULT_KEY, OcrResultMalformed, load_ocr_result
    from tests.test_review_receipt_v13 import _receipt_v13

    raw = "<!-- marker -->"
    prepared = check_text(raw, budgets=BUDGETS, publication=True).text
    payload = {
        "status": "success",
        "comments": [{"path": "sample", "line": 1, "content": prepared}],
        TOOLKIT_RESULT_KEY: _receipt_v13(),
    }
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    assert load_ocr_result(result)["comments"][0]["content"] == prepared
    for hostile in (
        raw,
        "[guide](javascript:hello)",
        "author@example.invalid",
        "password=synthetic-value",
    ):
        payload["comments"][0]["content"] = hostile
        result.write_text(json.dumps(payload))
        with pytest.raises(OcrResultMalformed, match="prose is not prepared"):
            load_ocr_result(result)


def test_filtered_sibling_does_not_reindex_prepared_content_or_warnings():
    payload = {
        "status": "success",
        "warnings": ["author@example.invalid", "<!-- marker -->"],
        "comments": [
            {"path": "first", "content": "author@example.invalid"},
            {"path": "second", "content": "<b>review</b>"},
        ],
    }
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert filtered and state["state"] == "publication-filtered"
    assert len(projected["comments"]) == len(projected["warnings"]) == 1
    assert projected["comments"][0]["path"] == "second"
    assert "<b>" not in projected["comments"][0]["content"]
    assert projected["warnings"][0] == payload["warnings"][1]


def test_prose_projection_has_one_closed_path_contract_for_nested_values(tmp_path):
    import json

    from ocr_toolkit.ocr_result import TOOLKIT_RESULT_KEY, OcrResultMalformed, load_ocr_result
    from tests.test_review_receipt_v13 import _receipt_v13

    payload = {
        "status": "success",
        "message": {"detail": "<i>done</i>"},
        "comments": [
            {"path": "src", "content": {"detail": ["<b>review</b>", 1]}},
        ],
        "warnings": [{"type": "other", "message": ["<!-- marker -->", {"detail": "<i>safe</i>"}]}],
    }
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert not filtered and state["state"] == "passed"
    assert "<b>" not in str(projected["comments"]) and "<i>" not in str(projected["message"])
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["warnings"] == projected["warnings"]
    payload["comments"][0]["content"] = {"<img src=x>": "value"}
    assert (
        review_runner._publication_projection(payload, forbidden=(), allowed_tools=frozenset())[0][
            "comments"
        ]
        == []
    )
    projected["comments"][0]["content"] = {"<img src=x>": "value"}
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    with pytest.raises(OcrResultMalformed, match="prose is not prepared"):
        load_ocr_result(result)


def test_prose_fences_are_literal_and_their_code_bytes_survive():
    value = "```mermaid\nflowchart LR\nA[Read] --> B[Done]\n```"
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted and checked.text.startswith("```text\n")
    assert checked.text.splitlines()[1:-1] == value.splitlines()[1:-1]
    assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text


def test_escaping_respects_byte_and_line_limits_before_delivery():
    assert (
        check_text("<b>Ω</b>", budgets=TextBudgets(100, 10, 10), publication=True).reason == "limit"
    )
    assert (
        check_text("<b>x</b>", budgets=TextBudgets(100, 400, 1), publication=True).reason == "limit"
    )


@pytest.mark.parametrize("sink", tuple(TextSink))
def test_hidden_formatted_phone_is_checked_independently_of_literal_source(sink):
    assert not check_text(
        "<!-- 202*555*0114 -->",
        budgets=BUDGETS,
        publication=True,
        sink=sink,
        allow_opaque_code=True,
    ).admitted


def test_safe_presentation_and_private_redaction_do_not_filter_findings():
    payload = {
        "status": "success",
        "comments": [{"path": "sample", "content": "<b>review</b>"}],
        "warnings": [{"message": "<!-- marker -->", "detail": ["<i>detail</i>"]}],
        "internal": "password=synthetic-value",
    }
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert not filtered and state["state"] == "private-sanitized"
    assert len(projected["comments"]) == 1 and "<b>" not in projected["comments"][0]["content"]
    assert payload["comments"][0]["content"] == "<b>review</b>"
    assert payload["warnings"][0]["detail"] == ["<i>detail</i>"]
    assert projected["warnings"] == payload["warnings"]


@pytest.mark.parametrize(
    "value", ('"Unicode control: &#x202e;hidden."', '"private con&#x200b;text sentence"')
)
def test_literal_source_does_not_activate_control_entities(value):
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    comment = {
        "path": "sample.txt",
        "line": 1,
        "content": "Inspect this declaration.",
        "existing_code": value,
    }
    projected, state, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(item, "sample.txt", lambda _path: value + "\n"),
    )
    assert not filtered and state["state"] == "passed"
    assert projected["comments"][0]["existing_code"] == value
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        value.replace("&#x202e;", "\u202e").replace("&#x200b;", "\u200b"),
        budgets=BUDGETS,
        publication=True,
        sink=TextSink.LITERAL_CODE,
        allow_opaque_code=True,
    ).admitted


def test_prepared_prose_reaches_both_real_report_adapters():
    import mistune

    from ocr_toolkit.posting.formatting import format_fallback_comment, format_inline_comment
    from ocr_toolkit.providers.local import local_report_parts
    from ocr_toolkit.reporting.model import ReviewReport
    from ocr_toolkit.reporting.result import normalize_coverage_diagnostics
    from ocr_toolkit.result_contract import ReviewOutcome

    original = '<span title="**look**">Review</span> Read [guide](https://example.invalid/).'
    projected, publication, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample.txt", "line": 1, "content": original}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert not filtered
    comment = projected["comments"][0]
    outcome = ReviewOutcome(status="success", kind="success", budget_exceeded=False)
    report = ReviewReport(
        outcome=outcome,
        comments=(comment,),
        warnings=(),
        diagnostics=normalize_coverage_diagnostics(outcome, ()),
        publication=publication,
        prepared_prose=True,
    )
    for body in (
        format_inline_comment(comment),
        format_fallback_comment(comment),
        "".join(local_report_parts(report)),
    ):
        assert comment["content"] in body
        rendered = mistune.create_markdown(escape=False)(body)
        assert "<span title=" not in rendered and "<strong>look</strong>" not in rendered
        assert 'href="https://example.invalid/"' in rendered


@pytest.mark.parametrize(
    "value",
    (
        '[guide](https://example.invalid/ "202*555*0114")',
        "[guide](https://example.invalid/contact%40example.invalid)",
        "[guide](https://example.invalid/%2B1%20202-555-0117)",
        "[unused]: https://example.invalid/contact%40example.invalid\n\nordinary text",
        '<span title="contact%40example.invalid">ordinary text</span>',
        "<!-- contact%40example.invalid -->",
    ),
)
def test_hidden_link_material_and_encoded_destinations_cannot_lose_protection(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_encoded_link_material_retains_forbidden_source_attribution():
    from ocr_toolkit.context.dlp import ForbiddenValue

    checked = check_text(
        "[guide](https://example.invalid/private%20phrase%20unavailable)",
        budgets=BUDGETS,
        publication=True,
        forbidden=(ForbiddenValue("private phrase unavailable", "external_context"),),
    )
    assert not checked.admitted and checked.reason == "forbidden"
    assert checked.source_classes == ("external_context",)


@pytest.mark.parametrize("enabled", (True, False))
def test_real_finalizer_transfers_prose_authority_to_local_report(tmp_path, enabled):
    import json

    from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
    from ocr_toolkit.providers.local import local_report_parts
    from tests.test_review_runner import (
        BUILTIN_EVIDENCE_TOOLS,
        LOCAL_IDENTITY,
        SUMMARY_ACTION_COUNTS,
    )

    content = "<b>Review</b> [guide](https://example.invalid/)"
    payload = {
        "status": "complete",
        "comments": [{"path": "sample.txt", "line": 1, "content": content}],
        "warnings": [],
        "prepared_prose": True,
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "one"}],
                "completed": [{"item_id": "one"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),),
        external_servers=(),
        secret_values=(),
    )
    reports = []
    review_runner._finalize_ocr_result(
        result,
        composition,
        LOCAL_IDENTITY,
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        dlp_enabled=enabled,
        report_consumer=reports.append,
    )
    report = reports[0]
    assert report.prepared_prose is enabled
    body = "".join(local_report_parts(report))
    saved = json.loads(result.read_text())
    assert saved["comments"][0]["content"] in body
    if enabled:
        assert "<b>" not in body and "```" not in body
    else:
        assert "<b>" in body and "```" in body


def test_explicit_publication_mode_owns_prepared_prose_authority():
    from ocr_toolkit.context.dlp import dlp_mode

    payload = {
        "status": "success",
        "comments": [{"path": "sample", "content": "<b>review</b>"}],
        "internal": "password=synthetic-value",
    }
    with dlp_mode(False):
        projected, state, filtered = review_runner._publication_projection(
            payload, forbidden=(), allowed_tools=frozenset(), dlp_enabled=True
        )
        assert not filtered and state["state"] == "private-sanitized"
        assert "<b>" not in projected["comments"][0]["content"]
        assert projected["internal"] != payload["internal"]
        payload["comments"][0]["content"] = "author@example.invalid"
        assert (
            review_runner._publication_projection(
                payload, forbidden=(), allowed_tools=frozenset(), dlp_enabled=True
            )[0]["comments"]
            == []
        )


@pytest.mark.parametrize(
    "payload", ("token=${SOURCE}", 'password="{{ config.value }}"', "api_key='${SOURCE}'")
)
def test_complete_reference_carrier_is_independent_of_encoding(payload):
    raw = "(" + repr(payload) + ",)"
    encoded = "(" + repr("".join(f"&#{ord(c)};" for c in payload)) + ",)"
    assert check_text(raw, budgets=BUDGETS, publication=True).admitted
    assert check_text(encoded, budgets=BUDGETS, publication=True).admitted
    for tail in (
        ' + "literal-material"',
        '.format("literal-material")',
        '[0] + "literal-material"',
    ):
        assert not check_text(raw + tail, budgets=BUDGETS, publication=True).admitted
    assert not check_text(
        raw + '\npassword="literal-material"', budgets=BUDGETS, publication=True
    ).admitted
