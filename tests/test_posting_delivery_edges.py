"""Delivery boundary failures preserve bounded delivery and prior reviewer state."""

import pytest

from ocr_toolkit.posting import gitlab, snapshot
from ocr_toolkit.posting.transaction import PostingTransaction
from tests.support import gitlab_config


@pytest.mark.parametrize("mode", ["direct", "draft"])
@pytest.mark.parametrize("response", [None, {}, {"id": True}, {"id": -1}])
def test_unproven_note_creation_never_enters_a_transaction(monkeypatch, mode, response):
    monkeypatch.setattr(gitlab, "post_mode", lambda: mode)
    monkeypatch.setattr(gitlab, "post_note", lambda *args, **kwargs: response)
    monkeypatch.setattr(gitlab, "post_draft_note", lambda *args, **kwargs: response)
    transaction = PostingTransaction()
    assert gitlab.post_review_note(gitlab_config(), "Review finding", transaction) is None
    assert transaction.plain_note_ids == transaction.draft_note_ids == ()


def test_failed_draft_publication_is_not_retried_or_rolled_back_as_a_visible_note(monkeypatch):
    monkeypatch.setattr(gitlab, "post_mode", lambda: "draft")
    transaction = PostingTransaction()
    for note_id in (1, 2, 3):
        assert transaction.record_draft(note_id)
    attempted = []

    def publish(config, note_id):
        attempted.append(note_id)
        return note_id != 2

    monkeypatch.setattr(gitlab, "publish_draft_note", publish)
    assert not gitlab.publish_created_draft_notes(gitlab_config(), transaction)
    assert attempted == [1, 2]
    assert transaction.consume_drafts_for_publication() == ()


def test_failed_terminal_note_collection_is_not_an_empty_cleanup_snapshot(monkeypatch):
    monkeypatch.setattr(snapshot, "api_get_paginated", lambda *args, **kwargs: None)
    assert snapshot.collect_terminal_status_note_ids(gitlab_config()) is None


@pytest.mark.parametrize(
    "method,endpoint",
    [
        (gitlab.delete_discussion_note, "/discussions/thread/notes/3"),
        (gitlab.delete_draft_note, "/draft_notes/3"),
        (gitlab.resolve_discussion, "/discussions/thread?resolved=true"),
        (gitlab.publish_draft_note, "/draft_notes/3/publish"),
    ],
)
def test_unconfirmed_remote_mutation_is_never_treated_as_success(monkeypatch, method, endpoint):
    calls = []

    def request(config, actual, data=None, method="POST"):
        calls.append((actual, method))
        return None

    monkeypatch.setattr(gitlab, "api_request", request)
    args = (
        ("thread", 3)
        if method is gitlab.delete_discussion_note
        else ("thread",)
        if method is gitlab.resolve_discussion
        else (3,)
    )
    assert method(gitlab_config(), *args) is False
    assert calls[0][0] == endpoint and len(calls) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://host:",
        "https://host:broken",
        "https://[invalid",
        "https://user:credential@host",
        "http://host",
        "https://host?query=1",
        "https://host/#fragment",
    ],
)
def test_invalid_operator_origin_never_sends_the_authentication_header(monkeypatch, capsys, url):
    for key, value in {
        "CI_PROJECT_ID": "1",
        "CI_MERGE_REQUEST_IID": "2",
        "GITLAB_API_TOKEN": "synthetic-auth",
        "CI_SERVER_URL": url,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        gitlab,
        "fetch_posting_identity",
        lambda *args: pytest.fail("invalid origin reached authentication"),
    )
    assert gitlab.load_gitlab_config() is None
    assert "synthetic-auth" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "version",
    [
        None,
        [],
        {"id": 1, "head_commit_sha": "a" * 40},
        {"head_commit_sha": "a" * 40, "base_commit_sha": "b" * 40, "start_commit_sha": ""},
    ],
)
def test_legacy_inline_refs_require_complete_reviewed_head_metadata(monkeypatch, version):
    monkeypatch.setenv("CI_COMMIT_SHA", "a" * 40)
    monkeypatch.delenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", raising=False)
    monkeypatch.delenv("CI_MERGE_REQUEST_EVENT_TYPE", raising=False)
    monkeypatch.setattr(gitlab, "api_get_paginated", lambda *args, **kwargs: [version])
    assert gitlab.get_diff_refs(gitlab_config()) is None


@pytest.mark.parametrize("kind", ["summary", "setup", "terminal"])
def test_scoped_status_cleanup_does_not_select_findings_or_other_statuses(monkeypatch, kind):
    refs = snapshot.BotCommentRefs(
        plain_note_ids=[10],
        discussion_note_refs=[("thread", 11)],
        draft_note_ids=[12],
        summary_plain_note_ids=[20],
        summary_draft_note_ids=[21],
        setup_plain_note_ids=[30],
        setup_draft_note_ids=[31],
        terminal_plain_note_ids=[40],
    )
    deleted = []
    monkeypatch.setattr(
        snapshot, "delete_plain_note", lambda config, note_id: deleted.append(note_id) or False
    )
    monkeypatch.setattr(
        snapshot, "delete_draft_note", lambda config, note_id: deleted.append(note_id) or False
    )
    method = {
        "summary": snapshot.delete_previous_summary_notes,
        "setup": snapshot.delete_previous_setup_notes,
        "terminal": snapshot.delete_previous_terminal_notes,
    }[kind]
    method(gitlab_config(), refs)
    assert deleted == {"summary": [20, 21], "setup": [30, 31], "terminal": [40]}[kind]


@pytest.mark.parametrize("mode", ["direct", "draft"])
def test_duplicate_provider_create_identity_is_not_recorded_twice(monkeypatch, mode):
    transaction = PostingTransaction()
    monkeypatch.setattr(gitlab, "post_mode", lambda: mode)
    monkeypatch.setattr(gitlab, "post_note", lambda *args, **kwargs: {"id": 17})
    monkeypatch.setattr(gitlab, "post_draft_note", lambda *args, **kwargs: {"id": 17})
    assert gitlab.post_review_note(gitlab_config(), "First", transaction) == {"id": 17}
    assert gitlab.post_review_note(gitlab_config(), "Second", transaction) is None
    assert (transaction.draft_note_ids if mode == "draft" else transaction.plain_note_ids) == (17,)


@pytest.mark.parametrize("note_id", [None, True, -1, 0, "17"])
def test_unusable_discussion_create_identity_cannot_authorize_rollback(note_id):
    assert gitlab.created_discussion_note({"id": "thread", "notes": [{"id": note_id}]}) is None


@pytest.mark.parametrize("failed_page", ["notes", "discussions", "draft_notes"])
def test_collection_requires_every_mode_specific_provider_page(monkeypatch, failed_page):
    monkeypatch.setattr(snapshot, "post_mode", lambda: "draft")

    def page(config, endpoint, **kwargs):
        return None if endpoint.split("?", 1)[0] == "/" + failed_page else []

    monkeypatch.setattr(snapshot, "api_get_paginated", page)
    assert snapshot.collect_previous_bot_comment_refs(gitlab_config()) is None


def test_malformed_snapshot_records_cannot_acquire_owned_cleanup_identities(monkeypatch):
    notes = [
        None,
        {"id": True},
        {"id": 0},
        {"id": -1},
        {"id": 7, "author": {"id": 8}, "body": "Human message"},
    ]
    discussions = [
        None,
        {"id": "invalid/endpoint", "notes": []},
        {"id": "thread", "notes": None},
        {
            "id": "thread",
            "notes": [None, {"id": True}, {"id": 8, "author": {"id": 8}, "body": "Human reply"}],
        },
    ]
    drafts = [None, {}, {"id": True}, {"id": 9, "author": {"id": 8}, "note": "Human draft"}]

    def page(config, endpoint, **kwargs):
        return (
            discussions
            if endpoint == "/discussions"
            else drafts
            if endpoint == "/draft_notes"
            else notes
        )

    monkeypatch.setattr(snapshot, "post_mode", lambda: "draft")
    monkeypatch.setattr(snapshot, "api_get_paginated", page)
    refs = snapshot.collect_previous_bot_comment_refs(gitlab_config())
    assert refs is not None
    assert refs.plain_note_ids == refs.draft_note_ids == refs.discussion_note_refs == []
    assert (
        refs.all_plain_note_ids == [7]
        and refs.all_discussion_note_refs == [("thread", 8)]
        and refs.all_draft_note_ids == [9]
    )


@pytest.mark.parametrize("title", ["", "Simple heading", "界" * 500])
def test_status_body_budget_bounds_both_unicode_bytes_and_characters(monkeypatch, title):
    monkeypatch.setattr(gitlab, "MAX_NOTE_CHARS", 256)
    observed = []
    monkeypatch.setattr(
        gitlab,
        "post_review_note",
        lambda config, body, *args, **kwargs: observed.append(body) or {"id": 1},
    )
    assert gitlab.post_review_note_bounded(
        gitlab_config(), title, "界" * 500, PostingTransaction()
    ) == {"id": 1}
    budget = gitlab.note_body_budget(256)
    assert len(observed) == 1 and len(observed[0]) <= budget and len(observed[0].encode()) <= budget


@pytest.mark.parametrize("count", [0, 1])
def test_resolution_reports_only_confirmed_provider_mutations(monkeypatch, capsys, count):
    from ocr_toolkit.posting import workflow

    refs = snapshot.BotCommentRefs(discussions_to_resolve=["first", "second"])
    calls = []
    monkeypatch.setattr(
        workflow,
        "resolve_discussion",
        lambda config, discussion: (
            calls.append(discussion) or (discussion == "first" and count == 1)
        ),
    )
    workflow.resolve_requested_discussions(gitlab_config(), refs)
    assert calls == ["first", "second"]
    assert ("Resolved 1" in capsys.readouterr().out) == bool(count)


def test_missing_delivery_credentials_stop_before_identity_acquisition(monkeypatch):
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.delenv("GITLAB_API_TOKEN", raising=False)
    monkeypatch.setattr(
        gitlab,
        "fetch_posting_identity",
        lambda *args: pytest.fail("missing credential reached provider"),
    )
    assert gitlab.load_gitlab_config() is None
