"""Admission must remain safe after actual report and note composition."""

import json

import mistune
import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import check_text
from ocr_toolkit.context.dlp.markup import interpret_markdown
from ocr_toolkit.ocr_result import TOOLKIT_RESULT_KEY, OcrResultMalformed, load_ocr_result
from ocr_toolkit.posting.formatting import format_fallback_comment_chunks, format_inline_comment
from ocr_toolkit.posting.suggestions import SuggestionDecision, SuggestionState
from ocr_toolkit.providers.local import local_report_parts
from ocr_toolkit.reporting.model import ReviewReport
from ocr_toolkit.reporting.result import normalize_coverage_diagnostics
from ocr_toolkit.result_contract import ReviewOutcome
from tests.test_review_receipt_v13 import _receipt_v13

BUDGETS = TextBudgets(20_000, 80_000, 200)


@pytest.fixture
def bounded_duration():
    import signal

    if not hasattr(signal, "SIGALRM"):
        pytest.skip("POSIX resource guard")

    def exhausted(_signal, _frame):
        raise AssertionError("bounded synthetic prose must not stall admission")

    previous = signal.signal(signal.SIGALRM, exhausted)
    signal.alarm(30)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def rendered_bodies(comments, warnings=()):
    outcome = ReviewOutcome(status="success", kind="success", budget_exceeded=False)
    report = ReviewReport(
        outcome=outcome,
        comments=tuple(comments),
        warnings=tuple(warnings),
        diagnostics=normalize_coverage_diagnostics(outcome, ()),
        prepared_prose=True,
    )
    return [
        "".join(local_report_parts(report)),
        *format_fallback_comment_chunks(
            [(comment, SuggestionDecision(SuggestionState.ABSENT)) for comment in comments]
        ),
        *(format_inline_comment(comment) for comment in comments),
    ]


@pytest.mark.parametrize(
    "contents",
    (
        [{"detail": r"\![plot](https://example.invalid/pixel)"}],
        [[r"\![plot](https://example.invalid/pixel)"]],
        ["![plot][asset]", "[asset]: https://example.invalid/pixel"],
        ["![asset][]", "[asset]: https://example.invalid/pixel"],
        ["![asset]", "[asset]: https://example.invalid/pixel"],
        ["`", "`![plot](https://example.invalid/pixel)`"],
    ),
)
def test_prepared_prose_stays_image_free_after_real_consumer_composition(contents, tmp_path):
    payload = {
        "status": "success",
        "comments": [{"path": "sample", "line": 1, "content": text} for text in contents],
    }
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert state["state"] == "passed" and not filtered
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    reloaded = load_ocr_result(result)
    for body in rendered_bodies(reloaded["comments"]):
        assert "<img " not in mistune.html(body)


def test_unterminated_prose_fence_does_not_absorb_the_next_finding():
    payload = {
        "status": "success",
        "comments": [
            {"path": "sample", "line": 1, "content": "```text\nliteral"},
            {"path": "sample", "line": 2, "content": "Second finding."},
        ],
    }
    projected, _, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert not filtered
    local = rendered_bodies(projected["comments"])[0]
    assert "<h3>Finding 1:" in mistune.html(local)
    assert "<h3>Finding 2:" in mistune.html(local)


def test_reserved_message_ancestor_cannot_break_safe_finding_finalization():
    projected, _, _ = review_runner._publication_projection(
        {
            "status": "success",
            "message": {"thinking": {"detail": "<b>done</b>"}},
            "comments": [{"path": "sample", "line": 1, "content": "Safe finding."}],
        },
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert projected["comments"][0]["content"] == "Safe finding."
    assert "thinking" not in str(projected)


def test_references_do_not_multiply_hidden_material_or_destination_work(monkeypatch):
    from ocr_toolkit.context.dlp import projection

    destination = "https://example.invalid/" + "a" * 4096
    text = " ".join(["[x][r]"] * 32) + "\n\n[r]: " + destination
    assert interpret_markdown(text).hidden == (destination,)
    calls = []
    original = projection.validate_destination

    def observed(value):
        calls.append(len(value))
        return original(value)

    monkeypatch.setattr(projection, "validate_destination", observed)
    assert check_text(text, budgets=BUDGETS, publication=True).admitted
    assert calls == [len(destination)]


def test_warning_metadata_stays_literal_and_its_actual_presentation_is_escaped(tmp_path):
    warning = {
        "type": "file_read_failed",
        "file": "src/My!Class.cs",
        "message": {"detail": "<b>diagnostic</b> ![plot](https://example.invalid/pixel)"},
    }
    projected, state, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [], "warnings": [warning]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert state["state"] == "passed" and not filtered
    assert projected["warnings"] == [warning]
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["warnings"] == [warning]
    local = rendered_bodies([], projected["warnings"])[0]
    assert "<img " not in mistune.html(local) and "<b>diagnostic" not in mistune.html(local)


@pytest.mark.parametrize(
    "value", ({"detail": 'one\'s "text"\n\u0085\u2028🧪'}, [None, True, -3, 2.5], {}, [], " text ")
)
def test_complete_container_representation_has_exact_preallocation_bounds(value):
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit
    from ocr_toolkit.context.dlp.result_prose import bounded_prose_text

    expected = str(value) if not isinstance(value, str) else value
    bounds = TextBudgets(len(expected), len(expected.encode()), expected.count("\n") + 1)
    assert bounded_prose_text(value, bounds) == expected.strip()
    with pytest.raises(RepresentationLimit):
        bounded_prose_text(
            value, TextBudgets(len(expected) - 1, bounds.max_bytes, bounds.max_lines)
        )
    with pytest.raises(RepresentationLimit):
        bounded_prose_text(
            value, TextBudgets(bounds.max_chars, bounds.max_bytes - 1, bounds.max_lines)
        )


def test_complete_container_structure_is_bounded_without_executing_custom_repr():
    from ocr_toolkit.context.dlp.decoding import RepresentationLimit
    from ocr_toolkit.context.dlp.result_prose import bounded_prose_text

    class Hostile:
        def __repr__(self):
            raise AssertionError("custom repr must not run")

    cycle = []
    cycle.append(cycle)
    deep = []
    for _ in range(66):
        deep = [deep]
    for value in (cycle, deep, [None] * 32768, {1: "value"}, [Hostile()], 1 << 20000):
        with pytest.raises(RepresentationLimit):
            bounded_prose_text(value, BUDGETS)


def test_aggregate_slot_limit_omits_only_the_oversize_finding(bounded_duration):
    payload = {
        "status": "success",
        "comments": [
            {"path": "sample", "line": 1, "content": ["a" * 1_100_000, "b" * 1_100_000]},
            {"path": "sample", "line": 2, "content": "Safe sibling."},
        ],
    }
    projected, state, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert filtered and state["state"] == "publication-filtered"
    assert len(projected["comments"]) == 1 and projected["comments"][0]["line"] == 2
    assert state["reason_counts"]["limit"] == 1


def test_long_scheme_near_match_preserves_later_real_userinfo(bounded_duration):
    from ocr_toolkit.common.redaction import redact_url_userinfo_only

    prefix = "a" * 1_000_000
    assert redact_url_userinfo_only(prefix) == prefix
    text = prefix + " 42+https://user:material@example.invalid/path"
    assert redact_url_userinfo_only(text) == prefix + " 42+https://***@example.invalid/path"


@pytest.mark.parametrize("encoded", ("%40", "%2F", "%3F", "%23"))
def test_encoded_userinfo_delimiters_do_not_erase_credential_material(encoded):
    value = f"https://user{encoded}name:synthetic-material@localhost/resource"
    assert check_text(value, budgets=BUDGETS, publication=True).reason == "secret"
    assert check_text(
        f"https://localhost/path{encoded}name@segment", budgets=BUDGETS, publication=True
    ).admitted


def test_new_prose_is_canonical_text_but_safe_legacy_containers_still_reload(tmp_path):
    payload = {
        "status": "success",
        "comments": [{"path": "sample", "line": 1, "content": {"detail": "plain"}}],
    }
    projected, _, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert not filtered and projected["comments"][0]["content"] == "{'detail': 'plain'}"
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**payload, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["comments"][0]["content"] == {"detail": "plain"}


def test_warning_selection_cycles_and_truncation_do_not_change_material_admission():
    from ocr_toolkit.reporting.warnings import ocr_warning_text

    nested = {"type": "failure", "code": 403, "error": {"message": "inner"}, "details": ["tail"]}
    assert ocr_warning_text(nested) == "failure\ncode: 403\ninner\n['tail']"
    assert ocr_warning_text([None, "first", {"error": {"message": "second"}}]) == "first\nsecond"
    cycle = {}
    cycle["error"] = cycle
    assert ocr_warning_text(cycle) == ""
    warning = {"message": "safe" * 2000, "hidden": "api_key=synthetic-material"}
    assert len(ocr_warning_text(warning)) == 4000
    projected, _, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [], "warnings": [warning]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert filtered and projected["warnings"] == []


def test_warning_path_provenance_survives_preparation():
    warning = {"type": "failure", "file": "src/My!Class.cs", "message": "read failed"}
    projected, _, filtered = review_runner._publication_projection(
        {"status": "completed_with_errors", "comments": [], "warnings": [warning]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    outcome = ReviewOutcome(status="completed_with_errors", kind="partial", budget_exceeded=False)
    assert not filtered
    assert (
        normalize_coverage_diagnostics(outcome, projected["warnings"]).records[0].path
        == warning["file"]
    )


@pytest.mark.parametrize(
    "value",
    (
        '["token=${SOURCE}", 1234][0] + str(1234)',
        '0 # compose("token=${SOURCE}", "literal-material")',
        '0 # compose("token=${SOURCE}", 1234)',
        'String.prototype.concat.call("token=${SOURCE}", [`synthetic-material`])',
        'compose("token=${SOURCE}", @"synthetic-material")',
        'compose("token=${SOURCE}", synthetic-material)',
        'compose("token=${SOURCE}")',
        'assert record.items[0].value == "component/token=***"',
    ),
)
def test_unproved_unquoted_or_discarded_operands_cannot_complete_a_carrier(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert filtered and not projected["comments"]


@pytest.mark.parametrize(
    "encoded", ("author%EF%BC%A0example.invalid", "author%40example%EF%BC%8Einvalid")
)
def test_decoding_and_compatibility_normalization_compose_without_delimiter_authority(encoded):
    value = f"[guide](https://example.invalid/{encoded})"
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    projected, _, filtered = review_runner._publication_projection(
        {"status": "success", "comments": [{"path": "sample", "line": 1, "content": value}]},
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert filtered and not projected["comments"]


def test_removed_publication_ancestor_preserves_prepared_quarantine_content(tmp_path):
    projected, _, _ = review_runner._publication_projection(
        {
            "status": "success",
            "comments": [{"path": "sample", "line": 1, "content": "<b>review</b>"}],
        },
        forbidden=("comments",),
        allowed_tools=frozenset(),
    )
    from html import unescape

    content = projected["comments"][0]["content"]
    assert unescape(content) == "<b>review</b>" and content != "<b>review</b>"
    assert "<b>" not in mistune.html(content)
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["comments"] == projected["comments"]


def test_oversize_string_warning_is_omitted_before_receipt_readback(tmp_path):
    projected, state, filtered = review_runner._publication_projection(
        {
            "status": "success",
            "comments": [{"path": "sample", "line": 1, "content": "Safe."}],
            "warnings": ["\n" * 100_001, "Safe warning."],
        },
        forbidden=(),
        allowed_tools=frozenset(),
    )
    assert filtered and state["reason_counts"]["limit"] == 1
    assert projected["warnings"] == ["Safe warning."]
    result = tmp_path / "result.json"
    result.write_text(json.dumps({**projected, TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["comments"] == projected["comments"]


@pytest.mark.parametrize("payload", ({}, {"comments": []}, {"comments": None}, {"comments": [{}]}))
def test_preparation_never_recreates_removed_destinations(payload):
    from copy import deepcopy

    from ocr_toolkit.context.dlp.result_prose import apply_prepared

    original = deepcopy(payload)
    apply_prepared(payload, {("comments", 0, "content"): "prepared"})
    assert payload == original


@pytest.mark.parametrize(
    "value",
    (
        'compare(actual, "token=***")',
        'contains("api_key=***", result.value())',
    ),
)
def test_unknown_call_references_cannot_prove_absence_of_credential_material(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_literal_markdown_delimiters_do_not_create_new_links_during_projection():
    value = r'pattern("([`*_{}\[\]()+.!|~-])")'
    checked = check_text(value, budgets=BUDGETS, publication=True)
    assert checked.admitted
    assert check_text(checked.text, budgets=BUDGETS, publication=True).text == checked.text
    assert "<a " not in mistune.html(checked.text)


@pytest.mark.parametrize("scalar", ("True", "false", "null", "None", "0xFF", "1e9"))
def test_unquoted_scalar_material_is_not_a_variable_reference(scalar):
    value = f'compose("token=${{SOURCE}}", {scalar})'
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted
    assert check_text(
        f'["token=${{SOURCE}}", {scalar}]', budgets=BUDGETS, publication=True
    ).admitted


@pytest.mark.parametrize(
    "value",
    (
        'enabled: true\ncommand: "token=${SOURCE}"',
        'count: 12\ncommand: "token=${SOURCE}"',
    ),
)
def test_complete_named_data_fields_preserve_independent_absent_values(value):
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize(
    "value",
    (
        'compose(1234, "token=${SOURCE}")',
        'compose(\n"token=${SOURCE}",\n1234\n)',
        'compose("token=${SOURCE}", str(1234))',
        '1234 + \\\n"token=${SOURCE}"',
    ),
)
def test_material_in_the_same_expression_record_still_requires_closed_proof(value):
    assert not check_text(value, budgets=BUDGETS, publication=True).admitted


def test_refining_absent_fields_preserves_neighboring_closed_data_grammar():
    value = json.dumps(
        {"link": "https://example.invalid/path?token=***", "token": "${REF}"}, indent=2
    )
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("empty", ("", "***", "${REF}"))
def test_complete_absent_carrier_proof_survives_lossy_display_views(empty):
    value = "count: 12\ncommand: " + repr('token="' + empty + '"')
    assert check_text(value, budgets=BUDGETS, publication=True).admitted


@pytest.mark.parametrize("slot", ("message", "content", "warning"))
def test_receipt_bounds_complete_slots_before_leaf_admission(tmp_path, monkeypatch, slot):
    from ocr_toolkit.context import dlp

    oversized = ["safe"] * 200_000
    payload = {"status": "success", "comments": [], TOOLKIT_RESULT_KEY: _receipt_v13()}
    if slot == "content":
        payload["comments"] = [{"path": "sample", "line": 1, "content": oversized}]
    elif slot == "warning":
        payload["warnings"] = [oversized]
    else:
        payload["message"] = oversized
    calls = []
    original = dlp.check_text

    def observed(text, **kwargs):
        calls.append(text)
        return original(text, **kwargs)

    monkeypatch.setattr(dlp, "check_text", observed)
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    with pytest.raises(OcrResultMalformed, match="bounds"):
        load_ocr_result(result)
    assert not calls
    result.write_text(json.dumps({"message": "safe", TOOLKIT_RESULT_KEY: _receipt_v13()}))
    assert load_ocr_result(result)["message"] == "safe"
    assert calls


@pytest.mark.parametrize("slot", ("message", "content", "warning"))
def test_producer_omits_oversize_slots_before_recursive_dlp(monkeypatch, slot):
    oversized = ["safe"] * 200_000
    safe = {"path": "sample", "line": 2, "content": "Keep this finding."}
    payload = {"status": "success", "comments": [safe]}
    if slot == "content":
        payload["comments"] = [{"path": "sample", "line": 1, "content": oversized}, safe]
    elif slot == "warning":
        payload["warnings"] = [oversized, "Keep this warning."]
    else:
        payload["message"] = oversized
    calls = []
    original = review_runner._dlp_reasons

    def observed(value, **kwargs):
        assert value is not oversized
        calls.append(None)
        return original(value, **kwargs)

    monkeypatch.setattr(review_runner, "_dlp_reasons", observed)
    projected, publication, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset()
    )
    assert filtered and publication["reason_counts"]["limit"] > 0
    assert projected["comments"] == [safe]
    if slot == "warning":
        assert projected["warnings"] == ["Keep this warning."]
    assert 0 < len(calls) < 20
