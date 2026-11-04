"""Suggestion acquisition crosses real immutable Git without whole-blob retention."""

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.source_reader import SourceReadSession
from ocr_toolkit.posting.source_suggestions import SuggestionSourceReader
from ocr_toolkit.posting.suggestions import SuggestionOmission, SuggestionState, evaluate_suggestion
from tests.fuzz.strategies import json_values
from tests.test_text_excerpts import repository


def finding(**changes):
    value = {"path": "source", "line": 2, "existing_code": "original", "suggestion_code": "changed"}
    value.update(changes)
    return value


def test_large_immutable_source_shared_across_distinct_suggestions_and_noop(tmp_path, monkeypatch):
    _, head = repository(tmp_path, b"x" * 270_000 + b"\noriginal\nthird\n")
    items = [
        finding(),
        finding(line=3, existing_code="third"),
        finding(existing_code=None, suggestion_code="original"),
    ]
    calls = []
    original = SourceReadSession._read

    def observe(session, entry):
        calls.append(entry.object_sha)
        return original(session, entry)

    monkeypatch.setattr(SourceReadSession, "_read", observe)
    source = SuggestionSourceReader(tmp_path, head, items)
    (tmp_path / "source").write_text("local edits remain untouched")
    decisions = [source.evaluate(item, "source") for item in items]
    assert [d.state for d in decisions] == [
        SuggestionState.ACTIONABLE,
        SuggestionState.ACTIONABLE,
        SuggestionState.NO_OP,
    ]
    assert len(calls) == 1
    assert source._session.read("source").syntax_source is None
    assert (tmp_path / "source").read_text() == "local edits remain untouched"


@pytest.mark.parametrize(
    "changes,omission",
    [
        ({"existing_code": "stale"}, SuggestionOmission.EXISTING_CODE_MISMATCH),
        ({"existing_code": None}, SuggestionOmission.MISSING_EXISTING_CODE),
        ({"line": 9}, SuggestionOmission.RANGE_OUT_OF_BOUNDS),
        ({"path": "../source"}, SuggestionOmission.INVALID_PATH),
        ({"line": True}, SuggestionOmission.INVALID_RANGE),
    ],
)
def test_invalid_suggestion_cannot_become_actionable(tmp_path, changes, omission):
    _, head = repository(tmp_path, b"header\noriginal\n")
    item = finding(**changes)
    source = SuggestionSourceReader(tmp_path, head, [item])
    assert source.evaluate(item, item["path"]).omission == omission


def test_invalid_head_and_failed_reader_preserve_finding(tmp_path):
    item = finding()
    source = SuggestionSourceReader(tmp_path, "branch", [item])
    assert source.evaluate(item, "source").omission == SuggestionOmission.SOURCE_UNAVAILABLE
    source = SuggestionSourceReader(tmp_path, "a" * 40, [item])
    assert source.evaluate(item, "source").omission == SuggestionOmission.SOURCE_UNAVAILABLE


def test_absent_or_malformed_replacements_never_acquire_source(tmp_path, monkeypatch):
    def unexpected(*args):
        raise AssertionError("no source read is required")

    monkeypatch.setattr(SourceReadSession, "read_excerpt", unexpected)
    source = SuggestionSourceReader(tmp_path, "a" * 40, [])
    assert source.evaluate(finding(suggestion_code=None), "source").state == SuggestionState.ABSENT
    assert (
        source.evaluate(finding(suggestion_code=[]), "source").omission
        == SuggestionOmission.MALFORMED_REPLACEMENT
    )


@given(
    st.sampled_from(("line", "start_line", "end_line")),
    st.one_of(
        st.booleans(),
        st.floats(),
        st.integers(max_value=0),
        st.integers(min_value=1_000_000_001),
        st.text(alphabet="abc+-./", max_size=20),
        st.lists(json_values(), max_size=3),
        st.dictionaries(st.text(max_size=3), json_values(), max_size=3),
    ),
)
def test_invalid_line_json_is_rejected_before_either_reader_route(field, value):
    item = finding(**{field: value})

    def unexpected(*args):
        pytest.fail("invalid range reached source acquisition")

    decision = evaluate_suggestion(item, "source", read_head_blob=unexpected)
    assert decision.omission == SuggestionOmission.INVALID_RANGE
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(SourceReadSession, "read_excerpt", unexpected)
        reader = SuggestionSourceReader(Path("/synthetic-unavailable-source"), "a" * 40, [item])
        assert reader.evaluate(item, "source").omission == SuggestionOmission.INVALID_RANGE


@given(st.integers(1, 12), st.booleans())
def test_valid_numeric_line_reaches_source_and_can_be_actionable(number, as_text):
    calls = []

    def source(path):
        calls.append(path)
        return "original\n" * 12

    item = finding(line=str(number) if as_text else number)
    assert (
        evaluate_suggestion(item, "source", read_head_blob=source).state
        == SuggestionState.ACTIONABLE
    )
    assert calls == ["source"]


@pytest.mark.parametrize("field", ["line", "start_line", "end_line"])
@pytest.mark.parametrize("value", [2, "2", " 2 ", "\u0662"])
def test_valid_line_representations_cross_actual_git_acquisition(tmp_path, field, value):
    _, head = repository(tmp_path, b"header\noriginal\n")
    item = finding(**{field: value})
    reader = SuggestionSourceReader(tmp_path, head, [item])
    assert reader.evaluate(item, "source").state == SuggestionState.ACTIONABLE


def test_real_posting_remap_precedes_batched_source_planning(tmp_path, monkeypatch):
    from ocr_toolkit.posting import gitlab, snapshot, workflow
    from tests.support import gitlab_config

    _, head = repository(tmp_path, b"x" * 270_000 + b"\noriginal\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        workflow, "get_diff_refs", lambda _: {"base_sha": head, "start_sha": head, "head_sha": head}
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda _: snapshot.BotCommentRefs()
    )
    monkeypatch.setattr(
        workflow, "remap_existing_code_location", lambda *args, **kwargs: ("source", 2)
    )
    monkeypatch.setattr(workflow, "post_review_note_bounded", lambda *args: {"id": 1})
    monkeypatch.setattr(workflow, "finalize_posting", lambda *args: True)
    monkeypatch.setattr(workflow, "delete_previous_bot_comments_if_collected", lambda *args: None)
    posted = []

    def post(**kwargs):
        posted.append(kwargs)
        return gitlab.GitLabWriteResult("posted")

    monkeypatch.setattr(workflow, "post_review_discussion", post)
    calls = []
    original = SourceReadSession._read

    def observe(session, entry):
        calls.append(entry.object_sha)
        return original(session, entry)

    monkeypatch.setattr(SourceReadSession, "_read", observe)
    items = [
        finding(content="Update the declaration."),
        finding(path="old", line=0, old_path="old", content="Update the other declaration."),
    ]
    assert workflow.post_results(gitlab_config(), {"comments": items}) == 0
    assert len(calls) == 1 and len(posted) == 2
    assert all("```suggestion:-0+0" in item["body"] for item in posted)
    assert posted[1]["path"] == "source" and posted[1]["old_path"] is None
