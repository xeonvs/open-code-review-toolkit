"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import json
import os
import random
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from ocr_toolkit.common.git import isolated_git_environment, read_only_git_prefix
from ocr_toolkit.posting import comments as posting_comments
from ocr_toolkit.posting import formatting as posting_formatting
from ocr_toolkit.posting import gitlab, markers, payloads, result, settings, snapshot, workflow
from ocr_toolkit.posting.markers import FINGERPRINT_LEN, build_marker
from ocr_toolkit.result_contract import CoverageFailure, ReviewOutcome
from tests.support import (
    gitlab_config,
    patched_attr,
    patched_env,
)


class PostingIdentityTests(unittest.TestCase):
    def test_post_results_fails_closed_without_current_user(self) -> None:
        calls: list[str] = []

        def fake_api_request(*args: Any, **kwargs: Any) -> dict[str, int]:
            calls.append("called")
            return {"id": 1}

        result_data = {"comments": [{"path": "file.py", "line": 1, "content": "x"}]}
        with redirect_stderr(io.StringIO()):
            with patched_attr(gitlab, "api_request", fake_api_request):
                exit_code = workflow.post_results(gitlab_config(current_user_id=None), result_data)

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, [])

    def test_line_number_rejects_bool_and_non_decimal_values(self) -> None:
        self.assertEqual(posting_comments.line_number(True), 0)
        self.assertEqual(posting_comments.line_number("1.5"), 0)
        self.assertEqual(posting_comments.line_number(" 12 "), 12)

    def test_clean_text_preserves_valid_falsy_values(self) -> None:
        self.assertEqual(posting_comments.clean_text(0), "0")
        self.assertEqual(posting_comments.clean_text(False), "False")
        self.assertEqual(posting_comments.clean_text(None), "")

    def test_fingerprint_survives_line_shifts(self) -> None:
        base = {
            "path": "file.py",
            "content": "same issue",
            "existing_code": "same_code()",
            "suggestion_code": "same_code_fixed()",
        }

        first = markers.comment_fingerprint({**base, "line": 10})
        second = markers.comment_fingerprint({**base, "line": 20})

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first, second)
        self.assertNotEqual(
            markers.line_based_comment_fingerprint({**base, "line": 10}),
            markers.line_based_comment_fingerprint({**base, "line": 20}),
        )
        self.assertIn(
            markers.line_based_comment_fingerprint({**base, "line": 10}),
            markers.comment_fingerprint_candidates({**base, "line": 10}),
        )

    def test_no_code_fingerprint_keeps_line_tiebreaker(self) -> None:
        base = {
            "path": "file.py",
            "content": "same issue",
            "suggestion_code": "",
        }

        self.assertNotEqual(
            markers.comment_fingerprint({**base, "line": 10}),
            markers.comment_fingerprint({**base, "line": 20}),
        )

    def test_duplicate_comment_fingerprints_get_occurrence_tiebreaker(self) -> None:
        comments = [
            {
                "path": "file.py",
                "line": 10,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
            {
                "path": "file.py",
                "line": 40,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
        ]

        self.assertEqual(
            markers.comment_fingerprint(comments[0]),
            markers.comment_fingerprint(comments[1]),
        )
        markers.annotate_comment_fingerprints(comments)

        self.assertNotEqual(comments[0]["_ocr_fingerprint"], comments[1]["_ocr_fingerprint"])
        self.assertIn(
            comments[1]["_ocr_fingerprint"],
            markers.comment_fingerprint_candidates(comments[1]),
        )
        self.assertNotIn(
            markers.comment_fingerprint(comments[1]),
            markers.comment_fingerprint_candidates(comments[1]),
        )

    def test_annotated_fingerprint_candidates_keep_line_compatibility_only_with_line(self) -> None:
        comment = {
            "path": "file.py",
            "line": 40,
            "content": "same issue",
            "existing_code": "same_code()",
            "suggestion_code": "same_code_fixed()",
            "_ocr_fingerprint": "abc123",
        }

        line_less = {key: value for key, value in comment.items() if key != "line"}
        self.assertEqual(markers.comment_fingerprint_candidates(line_less), {"abc123"})
        self.assertEqual(
            markers.comment_fingerprint_candidates({**line_less, "end_line": 40}),
            {"abc123"},
        )
        self.assertIn(
            markers.line_based_comment_fingerprint(comment),
            markers.comment_fingerprint_candidates({**comment, "line": 40}),
        )

    def test_occurrence_suppression_does_not_suppress_later_duplicate(self) -> None:
        comments = [
            {
                "path": "file.py",
                "line": 10,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
            {
                "path": "file.py",
                "line": 40,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
        ]
        markers.annotate_comment_fingerprints(comments)
        previous = snapshot.BotCommentRefs(
            suppressed_fingerprints={comments[0]["_ocr_fingerprint"]}
        )

        kept, dropped = snapshot.filter_suppressed_comments(comments, previous)

        self.assertEqual(kept, [comments[1]])
        self.assertEqual(dropped, 1)

    def test_base_fingerprint_suppression_only_suppresses_one_duplicate(self) -> None:
        comments = [
            {
                "path": "file.py",
                "line": 10,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
            {
                "path": "file.py",
                "line": 40,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            },
        ]
        base = markers.comment_fingerprint(comments[0])
        self.assertIsNotNone(base)
        markers.annotate_comment_fingerprints(comments)
        previous = snapshot.BotCommentRefs(suppressed_fingerprints={base or ""})

        kept, dropped = snapshot.filter_suppressed_comments(comments, previous)

        self.assertEqual(kept, [comments[1]])
        self.assertEqual(dropped, 1)

    def test_three_identical_same_line_findings_get_distinct_occurrence_fingerprints(self) -> None:
        comments = [
            {
                "path": "file.py",
                "line": 10,
                "content": "same issue",
                "existing_code": "same_code()",
                "suggestion_code": "same_code_fixed()",
            }
            for _ in range(3)
        ]

        markers.annotate_comment_fingerprints(comments)

        self.assertEqual(len({comment["_ocr_fingerprint"] for comment in comments}), 3)

    def test_occurrence_fingerprint_survives_line_shifts(self) -> None:
        base = {
            "path": "file.py",
            "content": "same issue",
            "existing_code": "same_code()",
            "suggestion_code": "same_code_fixed()",
        }

        self.assertEqual(
            markers.occurrence_comment_fingerprint({**base, "line": 10}, 2),
            markers.occurrence_comment_fingerprint({**base, "line": 45}, 2),
        )

    def test_ocr_reply_command_must_be_whole_body(self) -> None:
        self.assertIsNotNone(markers.OCR_REPLY_COMMAND_RE.search("/ocr suppress"))
        self.assertIsNotNone(markers.OCR_REPLY_COMMAND_RE.search("/OCR RESOLVE\n\n  \r\n"))
        self.assertIsNone(
            markers.OCR_REPLY_COMMAND_RE.search("Please run this example:\n```\n/ocr suppress\n```")
        )
        self.assertIsNone(markers.OCR_REPLY_COMMAND_RE.search("/ocr suppress please"))
        self.assertIsNone(markers.OCR_REPLY_COMMAND_RE.search("/ocr skip"))
        self.assertIsNone(markers.OCR_REPLY_COMMAND_RE.search("/ocr keep"))

    def test_suppress_command_preserves_open_discussion_and_suppresses_finding(self) -> None:
        refs = snapshot.BotCommentRefs()
        fingerprint = "a" * FINGERPRINT_LEN
        snapshot.process_discussion_for_refs(
            gitlab_config(),
            refs,
            "discussion-id",
            [
                {
                    "id": 10,
                    "body": build_marker(fingerprint) + "\nbody",
                    "author": {"id": 7},
                    "position": {"new_path": "file.py", "new_line": 7},
                },
                {"id": 11, "body": "/ocr suppress", "author": {"id": 8}},
            ],
        )

        self.assertEqual(refs.suppressed_inline_keys, {("file.py", 7)})
        self.assertEqual(refs.suppressed_fingerprints, {fingerprint})
        self.assertEqual(refs.discussions_to_resolve, [])
        self.assertEqual(refs.discussion_note_refs, [])

    def test_resolve_command_suppresses_and_schedules_discussion_resolution(self) -> None:
        refs = snapshot.BotCommentRefs()
        fingerprint = "b" * FINGERPRINT_LEN
        snapshot.process_discussion_for_refs(
            gitlab_config(),
            refs,
            "discussion-id",
            [
                {
                    "id": 10,
                    "body": build_marker(fingerprint) + "\nbody",
                    "author": {"id": 7},
                    "position": {"new_path": "file.py", "new_line": 9},
                },
                {"id": 11, "body": "/ocr resolve", "author": {"id": 8}},
            ],
        )

        self.assertEqual(refs.suppressed_inline_keys, {("file.py", 9)})
        self.assertEqual(refs.suppressed_fingerprints, {fingerprint})
        self.assertEqual(refs.discussions_to_resolve, ["discussion-id"])

    def test_latest_human_lifecycle_command_wins(self) -> None:
        notes = [
            {"body": "/ocr resolve", "author": {"id": 8}},
            {"body": "/ocr suppress", "author": {"id": 9}},
            {"body": "/ocr resolve", "author": {"id": 7}},
        ]

        self.assertEqual(snapshot.reviewer_command_in_thread(gitlab_config(), notes), "suppress")

    def test_legacy_command_is_an_ordinary_human_reply(self) -> None:
        refs = snapshot.BotCommentRefs()
        fingerprint = "c" * FINGERPRINT_LEN
        snapshot.process_discussion_for_refs(
            gitlab_config(),
            refs,
            "discussion-id",
            [
                {
                    "id": 10,
                    "body": build_marker(fingerprint) + "\nbody",
                    "author": {"id": 7},
                    "position": {"new_path": "file.py", "new_line": 11},
                },
                {"id": 11, "body": "/ocr keep", "author": {"id": 8}},
            ],
        )

        self.assertEqual(refs.suppressed_fingerprints, {fingerprint})
        self.assertEqual(refs.discussions_to_resolve, [])
        self.assertEqual(refs.discussion_note_refs, [])

    def test_resolved_discussion_remains_suppressed_without_resolve_request(self) -> None:
        refs = snapshot.BotCommentRefs()
        fingerprint = "d" * FINGERPRINT_LEN
        snapshot.process_discussion_for_refs(
            gitlab_config(),
            refs,
            "discussion-id",
            [
                {
                    "id": 10,
                    "body": build_marker(fingerprint) + "\nbody",
                    "author": {"id": 7},
                    "resolved": True,
                    "position": {"new_path": "file.py", "new_line": 13},
                }
            ],
        )

        self.assertEqual(refs.suppressed_fingerprints, {fingerprint})
        self.assertEqual(refs.discussions_to_resolve, [])
        self.assertEqual(refs.discussion_note_refs, [])

    def test_filter_suppressed_comments_uses_posting_anchor_line(self) -> None:
        previous = snapshot.BotCommentRefs(
            suppressed_inline_keys={("file.py", 7)},
        )
        comments = [{"path": " file.py ", "start_line": 7, "line": 9, "content": "x"}]

        kept, dropped = snapshot.filter_suppressed_comments(comments, previous)

        self.assertEqual(kept, [])
        self.assertEqual(dropped, 1)

    def test_main_fails_closed_before_error_notes_without_current_user(self) -> None:
        calls: list[str] = []

        with (
            redirect_stderr(io.StringIO()),
            patched_attr(workflow, "load_gitlab_config", lambda: gitlab_config(None)),
            patched_attr(
                workflow,
                "post_ocr_failure",
                lambda *args: calls.append("failure") or 0,
            ),
            patched_attr(workflow, "ocr_exit_code", lambda: 1),
        ):
            exit_code = workflow.main([])

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, [])

    def test_inline_write_failure_does_not_fallback_or_cleanup_old_notes(self) -> None:
        calls: list[str] = []

        def fake_post_review_discussion(*args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
            calls.append("inline")
            return gitlab.GitLabWriteResult("write_failed")

        def fake_fallback(*args: Any, **kwargs: Any) -> dict[str, int]:
            calls.append("fallback")
            return {"id": 1}

        with (
            redirect_stderr(io.StringIO()),
            patched_attr(
                workflow,
                "get_diff_refs",
                lambda _config: {"base_sha": "a", "start_sha": "b", "head_sha": "c"},
            ),
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: snapshot.BotCommentRefs(),
            ),
            patched_attr(
                workflow,
                "filter_suppressed_comments",
                lambda comments, _previous: (comments, 0),
            ),
            patched_attr(
                workflow,
                "post_review_discussion",
                fake_post_review_discussion,
            ),
            patched_attr(workflow, "post_review_note_bounded", fake_fallback),
            patched_attr(
                workflow,
                "rollback_current_run_comments",
                lambda *args: calls.append("rollback-current"),
            ),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *args: calls.append("delete-old"),
            ),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {"comments": [{"path": "file.py", "line": 7, "content": "x"}]},
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("inline", calls)
        self.assertIn("rollback-current", calls)
        self.assertNotIn("fallback", calls)
        self.assertNotIn("delete-old", calls)

    def test_invalid_inline_position_falls_back_without_rollback(self) -> None:
        calls: list[str] = []

        def fake_post_review_discussion(*args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
            calls.append("inline")
            return gitlab.GitLabWriteResult("invalid_position")

        def fake_note(*args: Any, **kwargs: Any) -> dict[str, int]:
            calls.append("note")
            return {"id": 1}

        with redirect_stderr(io.StringIO()):
            with redirect_stdout(io.StringIO()):
                with patched_attr(
                    workflow,
                    "get_diff_refs",
                    lambda _config: {"base_sha": "a", "start_sha": "b", "head_sha": "c"},
                ):
                    with patched_attr(
                        workflow,
                        "collect_previous_bot_comment_refs",
                        lambda _config: snapshot.BotCommentRefs(),
                    ):
                        with patched_attr(
                            workflow,
                            "filter_suppressed_comments",
                            lambda comments, _previous: (comments, 0),
                        ):
                            with patched_attr(
                                workflow, "post_review_discussion", fake_post_review_discussion
                            ):
                                with patched_attr(workflow, "post_review_note_bounded", fake_note):
                                    with patched_attr(workflow, "post_review_note", fake_note):
                                        with patched_attr(
                                            workflow, "finalize_posting", lambda *args: True
                                        ):
                                            with patched_attr(
                                                workflow,
                                                "delete_previous_bot_comments_if_collected",
                                                lambda *args: calls.append("delete-old"),
                                            ):
                                                with patched_attr(
                                                    workflow,
                                                    "rollback_current_run_comments",
                                                    lambda *args: calls.append("rollback"),
                                                ):
                                                    exit_code = workflow.post_results(
                                                        gitlab_config(),
                                                        {
                                                            "comments": [
                                                                {
                                                                    "path": "missing.py",
                                                                    "line": 7,
                                                                    "content": "x",
                                                                }
                                                            ]
                                                        },
                                                    )

        self.assertEqual(exit_code, 0)
        self.assertIn("inline", calls)
        self.assertIn("note", calls)
        self.assertIn("delete-old", calls)
        self.assertNotIn("rollback", calls)

    def test_no_comments_note_redacts_message_warnings_and_suppressed_count(self) -> None:
        notes: list[tuple[str, str]] = []

        def fake_post_review_note_bounded(
            _config: gitlab.GitLabConfig,
            title: str,
            body: str,
            _draft_note_ids: list[int],
        ) -> dict[str, int]:
            notes.append((title, body))
            return {"id": 1}

        with patched_attr(
            workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
        ):
            with patched_attr(
                workflow,
                "filter_suppressed_comments",
                lambda comments, _previous: ([], len(comments)),
            ):
                with patched_attr(
                    workflow, "post_review_note_bounded", fake_post_review_note_bounded
                ):
                    with patched_attr(workflow, "finalize_posting", lambda _config, _drafts: True):
                        with patched_attr(
                            workflow,
                            "delete_previous_bot_comments_if_collected",
                            lambda *_args: None,
                        ):
                            with patched_attr(
                                workflow, "resolve_requested_discussions", lambda *_args: None
                            ):
                                exit_code = workflow.post_results(
                                    gitlab_config(),
                                    {
                                        "message": "No comments, token=secret-value",
                                        "warnings": ["Authorization: Bearer secret-token"],
                                        "comments": [
                                            {"path": "a.py", "line": 1, "content": "skip"}
                                        ],
                                    },
                                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        body = notes[0][1]
        self.assertNotIn("secret-value", body)
        self.assertNotIn("secret-token", body)
        self.assertIn(r"Authorization: \*\*\*", body)
        self.assertIn("Reviewer suppression: 1", body)
        self.assertNotIn("Incomplete coverage", body)

    def test_perfect_ocr_review_posts_no_comments_note(self) -> None:
        notes: list[tuple[str, str]] = []

        def fake_post_review_note_bounded(
            _config: gitlab.GitLabConfig,
            title: str,
            body: str,
            _draft_note_ids: list[int],
        ) -> dict[str, int]:
            notes.append((title, body))
            return {"id": 1}

        with patched_attr(
            workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
        ):
            with patched_attr(
                workflow,
                "filter_suppressed_comments",
                lambda comments, _previous: (comments, 0),
            ):
                with patched_attr(
                    workflow, "post_review_note_bounded", fake_post_review_note_bounded
                ):
                    with patched_attr(workflow, "finalize_posting", lambda _config, _drafts: True):
                        with patched_attr(
                            workflow,
                            "delete_previous_bot_comments_if_collected",
                            lambda *_args: None,
                        ):
                            with patched_attr(
                                workflow, "resolve_requested_discussions", lambda *_args: None
                            ):
                                exit_code = workflow.post_results(
                                    gitlab_config(),
                                    {
                                        "comments": [],
                                        "warnings": [],
                                        "_ocr_toolkit": {
                                            "schema_version": 1,
                                            "mcp_usage": {"ocr_toolkit_evidence": 2},
                                        },
                                    },
                                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0][0], "")
        self.assertEqual(notes[0][1].count("## Open Code Review"), 1)
        self.assertIn("✅ **Review complete**", notes[0][1])
        self.assertIn("No findings", notes[0][1])
        self.assertIn("MCP used: 1 server(s)", notes[0][1])
        self.assertFalse(notes[0][1].startswith("**Open Code Review**"))

    def test_skipped_review_without_message_posts_neutral_outcome(self) -> None:
        """Do not describe a supported no-files skip as a failed review."""

        notes: list[str] = []

        def capture_note(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _drafts: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with (
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: snapshot.BotCommentRefs(),
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow, "delete_previous_bot_comments_if_collected", lambda *_args: None
            ),
            patched_attr(workflow, "resolve_requested_discussions", lambda *_args: None),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {"status": "skipped", "comments": [], "warnings": []},
            )

        assert exit_code == 0
        assert "No supported files changed" in notes[0]
        assert "did not complete cleanly" not in notes[0]

    def test_budget_exceeded_without_comments_posts_partial_outcome(self) -> None:
        notes: list[str] = []
        cleanup_calls: list[str] = []

        def capture_note(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _drafts: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with (
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: snapshot.BotCommentRefs(),
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: cleanup_calls.append("delete"),
            ),
            patched_attr(workflow, "resolve_requested_discussions", lambda *_args: None),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "budget_exceeded",
                    "summary": {"budget_exceeded": True, "total_tokens": 321},
                    "comments": [],
                    "warnings": [
                        {
                            "type": "token_budget_reached",
                            "message": "Token budget reached; partial results returned.",
                        }
                    ],
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        self.assertIn("partial result", notes[0])
        self.assertIn("Token budget reached", notes[0])
        self.assertIn("321 total", notes[0])
        self.assertNotIn("No issues found", notes[0])
        self.assertEqual(cleanup_calls, [])

    def test_budget_status_and_summary_must_agree(self) -> None:
        calls: list[str] = []

        with patched_attr(
            workflow,
            "invalid_ocr_schema_exit",
            lambda _config, message, **_kwargs: calls.append(message) or 1,
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "budget_exceeded",
                    "summary": {"budget_exceeded": False},
                    "comments": [],
                    "warnings": [],
                },
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, ["fields 'status' and 'summary.budget_exceeded' disagree"])

    def test_manifest_partial_preserves_previous_review_and_reports_coverage(self) -> None:
        notes: list[str] = []
        cleanup_calls: list[str] = []

        def capture_note(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _drafts: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        result_data = {
            "status": "partial",
            "comments": [],
            "warnings": [],
            "manifest": {
                "schema_version": "ocr.run-manifest/v1",
                "operation": "review",
                "terminal_state": "partial",
                "coverage": {
                    "selected": [{"item_id": "a"}, {"item_id": "b"}],
                    "completed": [{"item_id": "a"}],
                    "reused": [],
                    "failed": [{"item_id": "b", "classification": "provider"}],
                    "waived": [],
                },
            },
        }
        with (
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: snapshot.BotCommentRefs(),
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: cleanup_calls.append("delete"),
            ),
            patched_attr(workflow, "resolve_requested_discussions", lambda *_args: None),
        ):
            exit_code = workflow.post_results(gitlab_config(), result_data)

        self.assertEqual(exit_code, 0)
        self.assertEqual(cleanup_calls, [])
        self.assertIn("Coverage: selected 2; completed 1", notes[0])
        self.assertNotIn("No issues found", notes[0])

    def test_manifest_failed_posts_failure_without_collecting_or_replacing_previous(self) -> None:
        notes: list[str] = []
        collect_calls: list[str] = []

        def capture_note(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _drafts: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        result_data = {
            "status": "failed",
            "message": "Review failed safely.",
            "comments": [],
            "warnings": [],
            "manifest": {
                "schema_version": "ocr.run-manifest/v1",
                "operation": "review",
                "terminal_state": "failed",
                "coverage": {
                    "selected": [{"item_id": "a"}],
                    "completed": [],
                    "reused": [],
                    "failed": [{"item_id": "a", "classification": "provider"}],
                    "waived": [],
                },
            },
        }
        with (
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: collect_calls.append("collect") or snapshot.BotCommentRefs(),
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_env(OCR_STRICT_POSTING="true"),
        ):
            exit_code = workflow.post_results(gitlab_config(), result_data)

        self.assertEqual(exit_code, 1)
        self.assertEqual(collect_calls, [])
        self.assertIn("Previous OCR review comments were preserved", notes[0])
        self.assertIn("Coverage: selected 1", notes[0])

    def test_no_comments_note_uses_bounded_publishing(self) -> None:
        called: list[str] = []

        def fake_post_review_note_bounded(*_args: Any, **_kwargs: Any) -> dict[str, int]:
            called.append("bounded")
            return {"id": 1}

        with patched_attr(
            workflow, "collect_previous_bot_comment_refs", lambda _config: snapshot.BotCommentRefs()
        ):
            with patched_attr(workflow, "post_review_note_bounded", fake_post_review_note_bounded):
                with patched_attr(workflow, "finalize_posting", lambda _config, _drafts: True):
                    with patched_attr(
                        workflow, "delete_previous_bot_comments_if_collected", lambda *_args: None
                    ):
                        with patched_attr(
                            workflow, "resolve_requested_discussions", lambda *_args: None
                        ):
                            exit_code = workflow.post_results(
                                gitlab_config(),
                                {
                                    "message": "x" * (settings.MAX_NOTE_CHARS * 2),
                                    "comments": [],
                                },
                            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(called, ["bounded"])

    def test_inline_comment_neutralizes_model_controlled_suggestion_fences(self) -> None:
        body = posting_formatting.format_inline_comment(
            {
                "content": "Prose\n```suggestion\nmalicious\n```",
                "suggestion_code": "safe()",
                "line": 10,
            }
        )

        self.assertIn("```text\nmalicious", body)
        self.assertIn("```suggestion:-0+0", body)


class PostingPayloadBudgetTests(unittest.TestCase):
    def capture_api_calls(
        self,
    ) -> tuple[list[tuple[str, dict[str, Any] | None, str]], Any]:
        calls: list[tuple[str, dict[str, Any] | None, str]] = []

        def fake_api_request(
            config: Any,
            endpoint: str,
            data: dict[str, Any] | None = None,
            method: str = "POST",
        ) -> dict[str, int]:
            calls.append((endpoint, data, method))
            return {"id": len(calls)}

        return calls, fake_api_request

    def test_all_create_paths_include_marker_inside_size_budget(self) -> None:
        config = gitlab_config()
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}
        fingerprint = "a" * FINGERPRINT_LEN
        huge = "x" * (settings.MAX_NOTE_CHARS + 10_000)
        huge_inline = (
            "intro\n\n"
            + settings.SUGGESTION_HEADER
            + "\n```suggestion\n"
            + "y" * (settings.MAX_INLINE_NOTE_CHARS + 10_000)
            + "\n```"
        )
        calls, fake_api_request = self.capture_api_calls()

        with patched_attr(gitlab, "api_request", fake_api_request):
            gitlab.post_note(config, huge, fingerprint=fingerprint)
            gitlab.post_draft_note(config, huge, fingerprint=fingerprint)
            gitlab.post_discussion(config, "file.py", 12, huge_inline, refs, fingerprint)
            gitlab.post_draft_note(
                config,
                huge_inline,
                fingerprint=fingerprint,
                position=gitlab.build_text_position("file.py", 12, refs),
            )

        self.assertEqual(len(calls), 4)
        marker = build_marker(fingerprint)
        for endpoint, data, _method in calls:
            payload_key = "note" if endpoint == "/draft_notes" else "body"
            body = str((data or {}).get(payload_key, ""))
            self.assertTrue(body.startswith(f"{marker}\n"), endpoint)
            self.assertLessEqual(len(body), settings.MAX_NOTE_CHARS)
            self.assertLessEqual(len(body.encode("utf-8")), settings.MAX_NOTE_CHARS)
            if "/discussions" in endpoint or "position" in (data or {}):
                self.assertLessEqual(len(body), settings.MAX_INLINE_NOTE_CHARS)
                self.assertLessEqual(len(body.encode("utf-8")), settings.MAX_INLINE_NOTE_CHARS)

    def test_create_paths_bound_multibyte_payload_bytes(self) -> None:
        config = gitlab_config()
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}
        fingerprint = "a" * FINGERPRINT_LEN
        huge = "ж" * (settings.MAX_NOTE_CHARS + 10_000)
        huge_inline = "intro\n" + ("ж" * (settings.MAX_INLINE_NOTE_CHARS + 10_000))
        calls, fake_api_request = self.capture_api_calls()

        with patched_attr(gitlab, "api_request", fake_api_request):
            gitlab.post_note(config, huge, fingerprint=fingerprint)
            gitlab.post_draft_note(config, huge, fingerprint=fingerprint)
            gitlab.post_discussion(config, "file.py", 12, huge_inline, refs, fingerprint)
            gitlab.post_draft_note(
                config,
                huge_inline,
                fingerprint=fingerprint,
                position=gitlab.build_text_position("file.py", 12, refs),
            )

        for endpoint, data, _method in calls:
            payload_key = "note" if endpoint == "/draft_notes" else "body"
            body = str((data or {}).get(payload_key, ""))
            self.assertLessEqual(len(body), settings.MAX_NOTE_CHARS)
            self.assertLessEqual(len(body.encode("utf-8")), settings.MAX_NOTE_CHARS)
            if "/discussions" in endpoint or "position" in (data or {}):
                self.assertLessEqual(len(body), settings.MAX_INLINE_NOTE_CHARS)
                self.assertLessEqual(len(body.encode("utf-8")), settings.MAX_INLINE_NOTE_CHARS)

    def test_build_text_position_preserves_rename_old_path(self) -> None:
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}

        position = gitlab.build_text_position("new/file.py", 12, refs, old_path="old/file.py")

        self.assertEqual(position["new_path"], "new/file.py")
        self.assertEqual(position["old_path"], "old/file.py")

    def test_build_marked_note_body_fuzz_stays_within_budget(self) -> None:
        rng = random.Random(42)
        alphabet = "abc`\n/close\n~~~\n"
        for _ in range(400):
            fingerprint = "b" * FINGERPRINT_LEN if rng.choice([True, False]) else None
            max_chars = rng.randint(len(build_marker(fingerprint)) + 2, 6000)
            body = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 800)))
            if rng.choice([True, False]):
                body += "\n\n" + settings.SUGGESTION_HEADER + "\n```suggestion\n"
                body += "z" * rng.randint(0, 2400) + "\n```"

            built = payloads.build_marked_note_body(
                body,
                fingerprint=fingerprint,
                max_chars=max_chars,
                inline=rng.choice([True, False]),
            )

            self.assertLessEqual(len(built), max_chars)
            self.assertTrue(built.startswith(f"{build_marker(fingerprint)}\n"))

    def test_small_text_budgets_stay_within_budget(self) -> None:
        for budget in range(0, 6):
            self.assertLessEqual(len(posting_comments.compact_text("abcdef", budget)), budget)
            self.assertLessEqual(len(payloads.truncate_code_text("abcdef", budget)), budget)


class PostingWorkflowTests(unittest.TestCase):
    def test_missing_gitlab_configuration_fails_closed(self) -> None:
        with patched_attr(workflow, "load_gitlab_config", lambda: None):
            exit_code = workflow.main([])

        self.assertEqual(exit_code, 1)

    def test_changed_new_lines_parses_successful_diff_hunks(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: Any) -> Any:
            calls.append(args)

            class Result:
                returncode = 0
                stdout = "@@ -1 +3,2 @@\n+one\n+two\n@@ -10,0 +20 @@\n+three\n"

            return Result()

        cache: workflow.DiffLineCache = {}
        with patched_attr(workflow.subprocess, "run", fake_run):
            lines = workflow.changed_new_lines(
                {"base_sha": "base", "head_sha": "head"}, "file.py", cache
            )
            cached_lines = workflow.changed_new_lines(
                {"base_sha": "base", "head_sha": "head"}, "file.py", cache
            )

        self.assertEqual(lines, {3, 4, 20})
        self.assertEqual(cached_lines, {3, 4, 20})
        self.assertEqual(len(calls), 1)

    def test_changed_new_paths_decodes_nul_delimited_utf8(self) -> None:
        class Result:
            returncode = 0
            stdout = "src/naïve.py\0src/other.py\0".encode()

        with patched_attr(workflow.subprocess, "run", lambda *_args, **_kwargs: Result()):
            paths = workflow.changed_new_paths({"base_sha": "base", "head_sha": "head"})

        self.assertEqual(paths, ["src/naïve.py", "src/other.py"])

    def test_changed_new_paths_rejects_oversized_output(self) -> None:
        class Result:
            returncode = 0
            stdout = b"x" * (workflow.MAX_REMAP_DIFF_BYTES + 1)

        with patched_attr(workflow.subprocess, "run", lambda *_args, **_kwargs: Result()):
            paths = workflow.changed_new_paths({"base_sha": "base", "head_sha": "head"})

        self.assertEqual(paths, [])

    def test_posting_git_reads_ignore_replacements_and_caller_overrides(self) -> None:
        with patched_env(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="core.hooksPath",
            GIT_CONFIG_VALUE_0="/synthetic/hooks",
            GIT_OBJECT_DIRECTORY="/synthetic/objects",
            GIT_REPLACE_REF_BASE="refs/replace/custom/",
        ):
            environment = workflow._git_read_environment()

        self.assertEqual(environment["GIT_NO_REPLACE_OBJECTS"], "1")
        self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(environment["GIT_CONFIG_SYSTEM"], os.devnull)
        self.assertNotIn("GIT_OBJECT_DIRECTORY", environment)
        self.assertNotIn("GIT_REPLACE_REF_BASE", environment)
        self.assertFalse(
            any(
                name == "GIT_CONFIG_COUNT"
                or name == "GIT_CONFIG_PARAMETERS"
                or name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
                for name in environment
            )
        )
        self.assertEqual(environment, isolated_git_environment())
        self.assertEqual(workflow._git_read_prefix(), read_only_git_prefix())

    def test_existing_code_remap_ignores_blank_lines_with_line_mapping(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"existing_code": "foo()\n\nbar()"}

        with patched_attr(workflow, "changed_new_lines", lambda *_args: {11, 13}):
            with patched_attr(
                workflow,
                "head_file_lines",
                lambda *_args: [(10, "before()"), (11, "foo()"), (13, "bar()")],
            ):
                line = workflow.unique_existing_code_line(refs, "file.py", comment)

        self.assertEqual(line, 11)

    def test_head_file_lines_skips_oversized_blob_before_git_show(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: Any) -> Any:
            calls.append(args)

            class Result:
                returncode = 0
                stdout = str(workflow.MAX_REMAP_FILE_BYTES + 1)

            return Result()

        cache: workflow.FileLineCache = {}
        with patched_attr(workflow.subprocess, "run", fake_run):
            lines = workflow.head_file_lines({"head_sha": "head"}, "large.generated", cache)
            cached = workflow.head_file_lines({"head_sha": "head"}, "large.generated", cache)

        self.assertEqual(lines, [])
        self.assertEqual(cached, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][:5],
            ["git", "-c", "core.hooksPath=/dev/null", "cat-file", "-s"],
        )

    def test_noop_suggestion_matches_only_the_exact_bounded_head_range(self) -> None:
        """Suppress transport-equivalent replacements without hiding the finding."""

        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: Any) -> Any:
            calls.append(args)

            class Result:
                returncode = 0
                stdout = "17" if "-s" in args else b"before\r\ntarget\r\nafter\r\n"

            return Result()

        refs = {"head_sha": "a" * 40}
        cache: workflow.FileTextCache = {}
        with patched_attr(workflow.subprocess, "run", fake_run):
            identical = workflow.suggestion_matches_head_range(
                refs,
                "src/example.py",
                {"start_line": 2, "end_line": 2, "suggestion_code": "target\n"},
                cache,
            )
            changed = workflow.suggestion_matches_head_range(
                refs,
                "src/example.py",
                {"start_line": 2, "end_line": 2, "suggestion_code": "replacement"},
                cache,
            )

        self.assertTrue(identical)
        self.assertFalse(changed)
        self.assertEqual(len(calls), 2)

    def test_noop_suggestion_rejects_unsafe_paths_before_git(self) -> None:
        """Do not turn an OCR-controlled path into Git revision syntax."""

        calls: list[list[str]] = []
        with patched_attr(
            workflow.subprocess,
            "run",
            lambda args, **_kwargs: calls.append(args),
        ):
            matches = workflow.suggestion_matches_head_range(
                {"head_sha": "a" * 40},
                "../outside.py",
                {"line": 1, "suggestion_code": "same"},
            )

        self.assertFalse(matches)
        self.assertEqual(calls, [])

    def test_coverage_diagnostics_are_deduplicated_redacted_and_fail_closed(self) -> None:
        """Count unique files while keeping malformed failure paths out of public notes."""

        outcome = ReviewOutcome(
            status="partial",
            kind="partial",
            budget_exceeded=False,
            manifest_present=True,
            failed_items=(
                CoverageFailure("one", "src/a.py", "timeout", "token=secret-value\n/merge"),
                CoverageFailure("two", "src/a.py", "provider", "request failed"),
                CoverageFailure("three", "/tmp/private.py", "provider", "unsafe"),
            ),
        )

        diagnostics = result.normalize_coverage_diagnostics(outcome, ())
        summary = posting_formatting.summarize_result(
            total=1,
            inline_count=1,
            fallback_count=0,
            warning_count=0,
            outcome_status="partial",
            coverage_diagnostics=diagnostics,
            emoji=False,
        )

        self.assertEqual(len(diagnostics.records), 2)
        self.assertEqual(diagnostics.unique_file_count, 1)
        self.assertIsNone(diagnostics.file_count)
        self.assertNotIn("secret-value", summary)
        self.assertNotIn("/tmp/private.py", summary)
        self.assertNotIn("\n/merge", summary)
        self.assertIn("1 failed item(s) had no safe repository-relative path", summary)

    def test_existing_code_remap_anchors_changed_line_inside_window(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"existing_code": "before()\nchanged()"}

        with (
            patched_attr(workflow, "changed_new_lines", lambda *_args: {22}),
            patched_attr(
                workflow,
                "head_file_lines",
                lambda *_args: [(21, "before()"), (22, "changed()")],
            ),
        ):
            line = workflow.unique_existing_code_line(refs, "file.py", comment)

        self.assertEqual(line, 22)

    def test_anchorless_comment_can_remap_to_unambiguous_changed_path(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"path": "", "existing_code": "set -- review"}

        def fake_unique_existing_code_line(
            _refs: dict[str, str],
            path: str,
            _comment: dict[str, Any],
            **_kwargs: Any,
        ) -> int:
            return 12 if path == ".gitlab-ci.yml" else 0

        with patched_attr(workflow, "changed_new_paths", lambda *_args: [".gitlab-ci.yml"]):
            with patched_attr(
                workflow, "unique_existing_code_line", fake_unique_existing_code_line
            ):
                path, line = workflow.remap_existing_code_location(
                    refs,
                    "",
                    comment,
                    diff_line_cache={},
                    file_line_cache={},
                    changed_path_cache={},
                )

        self.assertEqual((path, line), (".gitlab-ci.yml", 12))

    def test_known_path_does_not_remap_to_different_file(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"path": "known.py", "existing_code": "same()"}

        def fake_unique_existing_code_line(
            _refs: dict[str, str],
            path: str,
            _comment: dict[str, Any],
            **_kwargs: Any,
        ) -> int:
            return 12 if path == "other.py" else 0

        def fail_if_changed_paths_are_loaded(*_args: Any) -> list[str]:
            self.fail("known paths must not trigger cross-file remapping")

        with patched_attr(workflow, "changed_new_paths", fail_if_changed_paths_are_loaded):
            with patched_attr(
                workflow, "unique_existing_code_line", fake_unique_existing_code_line
            ):
                path, line = workflow.remap_existing_code_location(
                    refs,
                    "known.py",
                    comment,
                    diff_line_cache={},
                    file_line_cache={},
                    changed_path_cache={},
                )

        self.assertEqual((path, line), ("known.py", 0))

    def test_anchorless_comment_stays_fallback_when_changed_path_match_is_ambiguous(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"path": "", "existing_code": "same()"}

        def fake_unique_existing_code_line(
            _refs: dict[str, str],
            path: str,
            _comment: dict[str, Any],
            **_kwargs: Any,
        ) -> int:
            return 7 if path in {"a.py", "b.py"} else 0

        with patched_attr(workflow, "changed_new_paths", lambda *_args: ["a.py", "b.py"]):
            with patched_attr(
                workflow, "unique_existing_code_line", fake_unique_existing_code_line
            ):
                path, line = workflow.remap_existing_code_location(
                    refs,
                    "",
                    comment,
                    diff_line_cache={},
                    file_line_cache={},
                    changed_path_cache={},
                )

        self.assertEqual((path, line), ("", 0))

    def test_anchorless_comment_skips_cross_file_remap_when_diff_is_too_large(self) -> None:
        refs = {"base_sha": "base", "head_sha": "head"}
        comment = {"path": "", "existing_code": "same()"}
        calls = 0

        def fake_unique_existing_code_line(*_args: Any, **_kwargs: Any) -> int:
            nonlocal calls
            calls += 1
            return 0

        with (
            patched_attr(
                workflow,
                "changed_new_paths",
                lambda *_args: [f"file-{index}.py" for index in range(250)],
            ),
            patched_attr(workflow, "unique_existing_code_line", fake_unique_existing_code_line),
        ):
            path, line = workflow.remap_existing_code_location(
                refs,
                "",
                comment,
                diff_line_cache={},
                file_line_cache={},
                changed_path_cache={},
            )

        self.assertEqual((path, line), ("", 0))
        self.assertEqual(calls, 0)

    def test_ocr_failure_details_neutralize_quick_actions(self) -> None:
        notes: list[str] = []

        def fake_post_review_note_bounded(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _draft_note_ids: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with tempfile.TemporaryDirectory() as tmp:
            stderr_path = Path(tmp) / "stderr.log"
            stderr_path.write_text("/merge\n", encoding="utf-8")
            with (
                patched_env(OCR_POST_ERROR_DETAILS="1"),
                patched_attr(workflow, "post_review_note_bounded", fake_post_review_note_bounded),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
            ):
                exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, 1)

        self.assertEqual(exit_code, 0)
        self.assertIn("\\/merge", notes[0])
        self.assertNotIn("\n/merge", notes[0])


class PostingSummaryTests(unittest.TestCase):
    def tearDown(self) -> None:
        settings.post_emoji.cache_clear()
        settings.post_mode.cache_clear()

    def test_post_emoji_defaults_on_and_accepts_explicit_false(self) -> None:
        settings.post_emoji.cache_clear()
        with patched_env(OCR_POST_EMOJI=""):
            self.assertTrue(settings.post_emoji())
        settings.post_emoji.cache_clear()
        with patched_env(OCR_POST_EMOJI="false"):
            self.assertFalse(settings.post_emoji())

    def test_tool_calls_prefers_calls_when_by_tool_is_empty(self) -> None:
        summary = posting_formatting.format_tool_calls_summary(
            {"by_tool": {}, "calls": [{"name": "file_read"}, {"tool": "code_search"}]}
        )

        self.assertIn("2 total", summary)
        self.assertIn("`file_read`: 1", summary)
        self.assertIn("`code_search`: 1", summary)

    def test_root_total_is_not_treated_as_token_usage(self) -> None:
        self.assertEqual(posting_formatting.format_token_usage_summary({"total": 17}), "")
        self.assertIn(
            "token usage: 30 total",
            posting_formatting.format_token_usage_summary(
                {"usage": {"prompt": 10, "completion": 20}}
            ),
        )

    def test_cached_only_usage_is_still_reported(self) -> None:
        summary = posting_formatting.format_token_usage_summary({"usage": {"cached_tokens": 40}})

        self.assertIn("token usage: 40 total", summary)
        self.assertIn("cached: 40", summary)
        self.assertIn(
            "token usage: 55 total",
            posting_formatting.format_token_usage_summary({"usage": {"total": 55}}),
        )

    def test_token_usage_summary_reads_root_explicit_fields(self) -> None:
        summary = posting_formatting.format_token_usage_summary(
            {"total_tokens": 10, "prompt_tokens": 7, "completion_tokens": 3}
        )

        self.assertIn("token usage: 10 total", summary)
        self.assertIn("prompt: 7", summary)

    def test_suggestion_block_omits_quick_action_lines(self) -> None:
        body = posting_formatting.format_inline_comment(
            {"content": "Fix this", "line": 1, "suggestion_code": "/close\nvalue"}
        )

        self.assertNotIn("```suggestion", body)
        self.assertNotIn("/close", body)

    def test_summary_includes_fallback_reasons_and_sha_mismatch(self) -> None:
        summary = posting_formatting.summarize_result(
            total=3,
            inline_count=1,
            fallback_count=2,
            warning_count=0,
            comments=[
                {"severity": "high", "category": "security"},
                {"severity": "low", "category": "bug"},
            ],
            fallback_reasons={"missing_line": 1, "invalid_position": 1},
            reviewed_sha="abc123",
            mr_head_sha="def456",
        )

        self.assertIn("Fallback reasons", summary)
        self.assertIn("🚨 `high`: 1", summary)
        self.assertIn("ℹ️ `low`: 1", summary)  # noqa: RUF001
        self.assertIn("🔒 `security`: 1", summary)
        self.assertIn("🐛 `bug`: 1", summary)
        self.assertIn("`missing_line`: 1", summary)
        self.assertIn("Reviewed commit: `abc123`", summary)
        self.assertIn("MR head commit: `def456`", summary)
        self.assertTrue(summary.startswith("## Open Code Review\n"))
        self.assertIn("🔎 **3 findings published**", summary)

    def test_summary_omits_zero_counts_and_can_disable_emoji(self) -> None:
        summary = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=0,
            outcome_status="skipped",
            outcome_message="No supported files changed.",
            emoji=False,
        )

        self.assertIn("No supported files changed", summary)
        self.assertNotIn("0 posted", summary)
        self.assertNotIn(posting_formatting.SEVERITY_EMOJI["low"], summary)

    def test_clean_summary_is_positive_and_has_no_zero_tool_counter(self) -> None:
        summary = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=0,
            outcome_status="success",
            outcome_message="No comments generated. Looks good to me.",
            tool_calls_summary=posting_formatting.format_tool_calls_summary(
                {"total": 0, "by_tool": {}}
            ),
            emoji=True,
        )

        self.assertIn("✅ **Review complete**", summary)
        self.assertIn("No findings", summary)
        self.assertNotIn("tool calls", summary)

    def test_budget_summary_and_guide_mark_findings_as_partial(self) -> None:
        guide = posting_formatting.format_reviewer_guide(
            [{"path": "example.py", "line": 7, "content": "Validate input."}],
            0,
            outcome_status="budget_exceeded",
        )
        summary = posting_formatting.summarize_result(
            total=1,
            inline_count=1,
            fallback_count=0,
            warning_count=1,
            outcome_status="budget_exceeded",
            reviewer_guide=guide,
            token_usage_summary="- token usage: 321 total",
            emoji=True,
        )

        self.assertIn("⚠️ **Review stopped at token budget**", summary)
        self.assertIn("Partial result · 🔎 **1 finding published**", summary)
        self.assertIn("Review scope:", summary)
        self.assertIn("partial review", summary)
        self.assertIn("321 total", summary)

    def test_mcp_usage_summary_reports_only_servers_actually_called(self) -> None:
        summary = posting_formatting.format_mcp_usage_summary(
            {
                "schema_version": 1,
                "mcp_usage": {
                    "ocr_toolkit_evidence": 2,
                    "documentation": 1,
                    "unused_optional": 0,
                },
            }
        )

        self.assertEqual(
            summary,
            "- MCP used: 2 server(s) (`documentation`: 1, `ocr_toolkit_evidence`: 2)",
        )
        self.assertNotIn("unused_optional", summary)
        self.assertNotIn("file_read", summary)

    def test_mcp_usage_summary_omits_zero_usage(self) -> None:
        self.assertEqual(
            posting_formatting.format_mcp_usage_summary(
                {"schema_version": 1, "mcp_usage": {}},
            ),
            "",
        )

    def test_warning_and_error_outcomes_never_look_clean(self) -> None:
        warning = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=1,
            outcome_status="completed_with_warnings",
            outcome_message="Some files were reviewed with warnings.",
            emoji=True,
        )
        error = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=1,
            outcome_status="completed_with_errors",
            outcome_message="Some files could not be reviewed due to errors.",
            emoji=True,
        )

        self.assertIn("⚠️ **Review complete with warnings**", warning)
        self.assertIn("⚠️ **Review incomplete**", error)
        self.assertIn("No findings in reviewed files", error)
        self.assertNotIn("✅", error)

    def test_outcome_message_is_redacted_compacted_and_not_a_quick_action(self) -> None:
        summary = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=1,
            outcome_status="completed_with_warnings",
            outcome_message="provider token=super-secret\n/merge now",
            emoji=False,
        )

        self.assertNotIn("super-secret", summary)
        self.assertNotIn("\n/merge", summary)
        self.assertNotIn("/merge", summary)

    def test_inline_finding_tags_are_quiet_for_every_supported_value(self) -> None:
        for value, marker in posting_formatting.SEVERITY_EMOJI.items():
            with self.subTest(severity=value):
                tagged = posting_formatting.format_finding_tags({"severity": value}, emoji=True)
                plain = posting_formatting.format_finding_tags({"severity": value}, emoji=False)
                self.assertEqual(tagged, plain)
                self.assertNotIn(marker, plain)
        for value, marker in posting_formatting.CATEGORY_EMOJI.items():
            with self.subTest(category=value):
                tagged = posting_formatting.format_finding_tags({"category": value}, emoji=True)
                plain = posting_formatting.format_finding_tags({"category": value}, emoji=False)
                self.assertEqual(tagged, plain)
                self.assertNotIn(marker, plain)

    def test_security_signal_is_promoted_when_present(self) -> None:
        guide = posting_formatting.format_reviewer_guide(
            [{"path": "x", "line": 1, "content": "Possible token leak"}], 0
        )

        self.assertIn("## Security review focus", guide)
        self.assertIn("**Security signal:**", guide)

    def test_reviewer_guide_snippet_is_markdown_neutral(self) -> None:
        guide = posting_formatting.format_reviewer_guide(
            [
                {
                    "path": "file.py\n/close",
                    "line": 1,
                    "content": "**bold**\n/merge @all",
                }
            ],
            0,
        )

        self.assertIn("`file.py\\n/close:L1`", guide)
        self.assertIn(r"\*\*bold\*\*\n\/merge &#64;all", guide)
        self.assertNotIn("**bold**", guide)
        self.assertNotIn("\n/merge", guide)

    def test_reviewer_guide_snippet_escapes_html_and_autolinks(self) -> None:
        guide = posting_formatting.format_reviewer_guide(
            [
                {
                    "path": "file.py",
                    "line": 1,
                    "content": "See <https://user:token@example.com> & <b>x</b>",
                }
            ],
            0,
        )

        self.assertIn("&lt;https://", guide)
        self.assertIn("&amp;", guide)
        self.assertNotIn("<b>", guide)

    def test_fallback_location_rejects_reversed_ranges(self) -> None:
        body = posting_formatting.format_fallback_comment(
            {
                "path": "file.py",
                "start_line": 20,
                "end_line": 10,
                "content": "x",
            }
        )

        self.assertIn("### `file.py` L10", body)
        self.assertNotIn("L20-L10", body)

    def test_fallback_location_uses_line_as_start_fallback(self) -> None:
        body = posting_formatting.format_fallback_comment(
            {"path": "file.py", "line": 5, "end_line": 12, "content": "x"}
        )

        self.assertIn("### `file.py` L5-L12", body)

    def test_fallback_code_details_neutralize_quick_actions(self) -> None:
        body = posting_formatting.format_fallback_comment(
            {
                "path": "file.py",
                "content": "issue",
                "existing_code": "/close",
                "suggestion_code": "/label review",
            }
        )

        self.assertIn(r"\/close", body)
        self.assertIn(r"\/label review", body)
        self.assertNotIn("\n/close", body)
        self.assertNotIn("\n/label review", body)

    def test_fallback_code_details_keep_fences_after_quick_action_neutralization(self) -> None:
        """Do not let neutralization escape or corrupt the surrounding code fence."""

        body = posting_formatting.format_fallback_comment(
            {
                "path": "synthetic.py",
                "content": "Explain the replacement",
                "existing_code": "old\n/close",
                "suggestion_code": "new\n/label review",
            },
            emoji=False,
        )

        assert body.count("```text") == 2
        assert body.count("```") == 4
        assert "\n/close" not in body
        assert "\n/label review" not in body

    def test_inline_comment_formats_structured_ocr_metadata_as_tags(self) -> None:
        body = posting_formatting.format_inline_comment(
            {
                "content": "Needs attention",
                "severity": "HIGH",
                "category": "security",
            }
        )

        self.assertNotIn("🚨", body)
        self.assertNotIn("🔒", body)
        self.assertIn("**Severity:** `high`", body)
        self.assertIn("**Category:** `security`", body)
        self.assertIn("Needs attention", body)

    def test_inline_comment_ignores_invalid_metadata_tags(self) -> None:
        body = posting_formatting.format_inline_comment(
            {
                "content": "Needs attention",
                "severity": "high\n/merge",
                "category": "security",
            }
        )

        self.assertNotIn("/merge", body)
        self.assertIn("**Category:** `security`", body)


class GitLabSnapshotTests(unittest.TestCase):
    def test_gitlab_api_success_reads_are_bounded(self) -> None:
        read_limits: list[int] = []

        class FakeResponse:
            headers = {"Content-Length": "2"}

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, limit: int) -> bytes:
                read_limits.append(limit)
                return b'{"ok": true}'

        def fake_urlopen(_request: Any, **_kwargs: Any) -> FakeResponse:
            return FakeResponse()

        with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
            response = gitlab.api_request(gitlab_config(), "/notes", method="GET")
            write_response = gitlab.api_write_url_detailed(
                "https://gitlab.example/api/v4/projects/1/merge_requests/2/notes",
                "token",
                "PRIVATE-TOKEN",
                {"body": "x"},
            )

        self.assertEqual(response, {"ok": True})
        self.assertEqual(write_response.response, {"ok": True})
        self.assertEqual(
            read_limits,
            [gitlab.MAX_API_RESPONSE_BODY_BYTES, gitlab.MAX_API_RESPONSE_BODY_BYTES],
        )

    def test_gitlab_api_success_rejects_oversized_body(self) -> None:
        class FakeResponse:
            def __init__(self) -> None:
                self.calls = 0

            def __enter__(self) -> FakeResponse:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, limit: int) -> bytes:
                self.calls += 1
                if self.calls == 1:
                    return b"{}" + (b" " * max(0, limit - 2))
                return b"x"

        def fake_urlopen(_request: Any, **_kwargs: Any) -> FakeResponse:
            return FakeResponse()

        with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
            with redirect_stderr(io.StringIO()):
                response = gitlab.api_request(gitlab_config(), "/notes", method="GET")
                write_response = gitlab.api_write_url_detailed(
                    "https://gitlab.example/api/v4/projects/1/merge_requests/2/notes",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                )

        self.assertIsNone(response)
        self.assertTrue(write_response.write_failed)

    def test_gitlab_write_transport_error_is_redacted(self) -> None:
        def fake_urlopen(_request: Any, **_kwargs: Any) -> Any:
            raise OSError("post failed token=super-secret-value")

        stderr = io.StringIO()
        with patched_env(OCR_LLM_TOKEN="super-secret-value"), redirect_stderr(stderr):
            with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
                write_response = gitlab.api_write_url_detailed(
                    "https://gitlab.example/api/v4/projects/1/merge_requests/2/notes",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                )

        self.assertTrue(write_response.write_failed)
        self.assertNotIn("super-secret-value", stderr.getvalue())
        self.assertIn("token=***", stderr.getvalue())

    def test_gitlab_write_http_error_body_is_redacted_and_bounded(self) -> None:
        read_limits: list[int] = []

        class FakeResponse:
            def read(self, limit: int = -1) -> bytes:
                read_limits.append(limit)
                return b'{"message":"token=super-secret-value"}'

            def close(self) -> None:
                return None

        def fake_urlopen(_request: Any, **_kwargs: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://gitlab.example/api/v4/projects/1/merge_requests/2/notes",
                500,
                "boom",
                hdrs=None,
                fp=FakeResponse(),
            )

        stderr = io.StringIO()
        with patched_env(OCR_LLM_TOKEN="super-secret-value"), redirect_stderr(stderr):
            with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
                write_response = gitlab.api_write_url_detailed(
                    "https://gitlab.example/api/v4/projects/1/merge_requests/2/notes",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                )

        self.assertTrue(write_response.write_failed)
        self.assertEqual(read_limits, [gitlab.MAX_API_ERROR_BODY_BYTES])
        self.assertNotIn("super-secret-value", stderr.getvalue())
        self.assertIn("token=***", stderr.getvalue())

    def test_full_last_page_at_pagination_limit_checks_sentinel_page(
        self,
    ) -> None:
        calls: list[str] = []

        def fake_api_request(
            config: Any,
            endpoint: str,
            data: dict[str, Any] | None = None,
            method: str = "POST",
        ) -> list[dict[str, int]]:
            calls.append(endpoint)
            if endpoint.endswith("page=3"):
                return []
            return [{"id": 1}, {"id": 2}]

        with redirect_stderr(io.StringIO()):
            with patched_attr(gitlab, "api_request", fake_api_request):
                loaded = gitlab.api_get_paginated(
                    gitlab_config(), "/notes", per_page=2, max_pages=2
                )

        self.assertEqual(loaded, [{"id": 1}, {"id": 2}, {"id": 1}, {"id": 2}])
        self.assertEqual(
            calls,
            [
                "/notes?per_page=2&page=1",
                "/notes?per_page=2&page=2",
                "/notes?per_page=2&page=3",
            ],
        )

    def test_pagination_refuses_confirmed_extra_page(self) -> None:
        def fake_api_request(
            _config: Any,
            _endpoint: str,
            data: dict[str, Any] | None = None,
            method: str = "POST",
        ) -> list[dict[str, int]]:
            return [{"id": 1}, {"id": 2}]

        with redirect_stderr(io.StringIO()):
            with patched_attr(gitlab, "api_request", fake_api_request):
                loaded = gitlab.api_get_paginated(
                    gitlab_config(), "/notes", per_page=2, max_pages=2
                )

        self.assertIsNone(loaded)

    def test_rollback_collection_keeps_current_run_bot_notes_with_human_reply(self) -> None:
        refs = snapshot.BotCommentRefs()
        notes = [
            {
                "id": 10,
                "body": build_marker("a" * FINGERPRINT_LEN) + "\nbody",
                "author": {"id": 7},
                "position": {"new_path": "file.py", "new_line": 1},
            },
            {"id": 11, "body": "human reply", "author": {"id": 8}},
        ]

        snapshot.process_discussion_for_refs(
            gitlab_config(),
            refs,
            "discussion-id",
            notes,
            preserve_human_touched=False,
        )

        self.assertEqual(refs.discussion_note_refs, [("discussion-id", 10)])

    def test_rollback_does_not_delete_preexisting_human_touched_threads(self) -> None:
        previous_refs = snapshot.BotCommentRefs()
        previous_refs.all_discussion_note_refs.append(("old-discussion", 10))
        current_refs = snapshot.BotCommentRefs()
        current_refs.discussion_note_refs.extend([("old-discussion", 10), ("new-discussion", 20)])
        deleted: list[tuple[str, int]] = []

        def fake_collect(
            _config: gitlab.GitLabConfig, preserve_human_touched: bool = True
        ) -> snapshot.BotCommentRefs:
            self.assertFalse(preserve_human_touched)
            return current_refs

        def fake_delete(_config: gitlab.GitLabConfig, refs: snapshot.BotCommentRefs) -> None:
            deleted.extend(refs.discussion_note_refs)

        with patched_attr(snapshot, "collect_previous_bot_comment_refs", fake_collect):
            with patched_attr(snapshot, "delete_collected_bot_comments", fake_delete):
                with patched_attr(
                    snapshot, "cleanup_drafts_created_by_this_run", lambda *_args: None
                ):
                    snapshot.rollback_current_run_comments(gitlab_config(), previous_refs, [])

        self.assertEqual(deleted, [("new-discussion", 20)])


class ApiErrorRedactionTests(unittest.TestCase):
    def test_gitlab_redirect_handler_refuses_credential_forwarding(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request(
            "https://gitlab.example.com/api",
            headers={"PRIVATE-TOKEN": "gitlab-secret-value"},
        )

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://other.example.com/capture"
        )

        self.assertIsNone(redirected)

    def test_gitlab_redirect_handler_allows_same_origin_https_redirect(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request(
            "https://gitlab.example.com/api",
            headers={"PRIVATE-TOKEN": "gitlab-secret-value"},
        )

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://gitlab.example.com/api/"
        )

        self.assertIsNotNone(redirected)
        assert redirected is not None
        self.assertEqual(redirected.full_url, "https://gitlab.example.com/api/")
        self.assertEqual(redirected.get_header("Private-token"), "gitlab-secret-value")

    def test_gitlab_redirect_handler_rejects_https_downgrade(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request(
            "https://gitlab.example.com/api",
            headers={"PRIVATE-TOKEN": "gitlab-secret-value"},
        )

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "http://gitlab.example.com/api/"
        )

        self.assertIsNone(redirected)

    def test_gitlab_redirect_handler_rejects_redirect_userinfo(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request("https://gitlab.example.com/api")

        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://user:password@gitlab.example.com/api/",
        )

        self.assertIsNone(redirected)

    def test_gitlab_redirect_handler_treats_default_https_port_as_same_origin(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request("https://gitlab.example.com/api")

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://gitlab.example.com:443/api/"
        )

        self.assertIsNotNone(redirected)

    def test_gitlab_redirect_handler_rejects_write_redirect(self) -> None:
        handler = gitlab._SameOriginRedirectHandler()
        request = urllib.request.Request(
            "https://gitlab.example.com/api", data=b"{}", method="POST"
        )

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://gitlab.example.com/api/"
        )

        self.assertIsNone(redirected)

    def test_gitlab_config_rejects_non_https_server_before_token_lookup(self) -> None:
        with patched_env(
            CI_SERVER_URL="http://gitlab.example.com",
            CI_PROJECT_ID="1",
            CI_MERGE_REQUEST_IID="2",
            GITLAB_API_TOKEN="gitlab-secret-value",
        ):
            with patched_attr(
                gitlab,
                "fetch_current_user_id",
                lambda *_args: self.fail("token must not be sent to HTTP"),
            ):
                config = gitlab.load_gitlab_config()

        self.assertIsNone(config)

    def test_gitlab_config_rejects_server_url_with_embedded_credentials(self) -> None:
        with patched_env(
            CI_SERVER_URL="https://user:password@gitlab.example.com",
            CI_PROJECT_ID="1",
            CI_MERGE_REQUEST_IID="2",
            GITLAB_API_TOKEN="gitlab-secret-value",
        ):
            with patched_attr(
                gitlab,
                "fetch_current_user_id",
                lambda *_args: self.fail("invalid origin must not receive the token"),
            ):
                config = gitlab.load_gitlab_config()

        self.assertIsNone(config)

    def test_api_error_body_is_redacted_before_logging(self) -> None:
        class FakeResponse:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def read(self, _limit: int = -1) -> bytes:
                return self._body

            def close(self) -> None:
                return None

        body = (
            b'{"message":"Authorization: Basic abc123","private_token":"secret", "password":"pw"}'
        )

        def fake_urlopen(_request: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://gitlab.example.com/api",
                500,
                "boom",
                hdrs=None,
                fp=FakeResponse(body),
            )

        stderr = io.StringIO()
        with redirect_stderr(stderr), patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
            response = gitlab.api_request_url(
                "https://gitlab.example.com/api",
                "token",
                "PRIVATE-TOKEN",
                method="GET",
            )

        self.assertIsNone(response)
        logged = stderr.getvalue()
        self.assertNotIn("abc123", logged)
        self.assertNotIn("secret", logged)
        self.assertNotIn("pw", logged)

    def test_invalid_position_http_error_is_typed_for_fallback(self) -> None:
        class FakeResponse:
            def read(self, _limit: int = -1) -> bytes:
                return b'{"message":"position line is invalid"}'

            def close(self) -> None:
                return None

        def fake_urlopen(_request: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://gitlab.example.com/api",
                400,
                "bad request",
                hdrs=None,
                fp=FakeResponse(),
            )

        with redirect_stderr(io.StringIO()):
            with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
                write_result = gitlab.api_write_url_detailed(
                    "https://gitlab.example.com/api",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                )

        self.assertTrue(write_result.invalid_position)

    def test_line_code_must_be_valid_is_typed_for_fallback(self) -> None:
        class FakeResponse:
            def read(self, _limit: int = -1) -> bytes:
                return b'{"message":"line_code must be a valid line code"}'

            def close(self) -> None:
                return None

        error = urllib.error.HTTPError(
            "https://gitlab.example.com/api", 422, "invalid", None, FakeResponse()
        )

        with patched_attr(
            gitlab,
            "_open_gitlab_request",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
        ):
            write_result = gitlab.api_write_url_detailed(
                "https://gitlab.example.com/api",
                "token",
                "PRIVATE-TOKEN",
                {"body": "x"},
            )

        self.assertTrue(write_result.invalid_position)

    def test_generic_path_error_is_not_typed_as_invalid_position(self) -> None:
        class FakeResponse:
            def read(self, _limit: int = -1) -> bytes:
                return b'{"message":"path text appears in validation error"}'

            def close(self) -> None:
                return None

        def fake_urlopen(_request: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://gitlab.example.com/api",
                400,
                "bad request",
                hdrs=None,
                fp=FakeResponse(),
            )

        with redirect_stderr(io.StringIO()):
            with patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
                write_result = gitlab.api_write_url_detailed(
                    "https://gitlab.example.com/api",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                )

        self.assertFalse(write_result.invalid_position)
        self.assertTrue(write_result.write_failed)

    def test_gitlab_api_error_body_is_bounded_after_redaction(self) -> None:
        class FakeResponse:
            def read(self, _limit: int = -1) -> bytes:
                return b'{"message":"token=abc123 ' + (b"x" * 5000) + b'"}'

            def close(self) -> None:
                return None

        def fake_urlopen(_request: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://gitlab.example.com/api",
                500,
                "boom",
                hdrs=None,
                fp=FakeResponse(),
            )

        stderr = io.StringIO()
        with redirect_stderr(stderr), patched_attr(gitlab, "_open_gitlab_request", fake_urlopen):
            response = gitlab.api_request_url(
                "https://gitlab.example.com/api",
                "token",
                "PRIVATE-TOKEN",
                method="GET",
            )

        self.assertIsNone(response)
        logged = stderr.getvalue()
        self.assertNotIn("abc123", logged)
        self.assertLess(len(logged), 2500)


class OcrResultLoadingTests(unittest.TestCase):
    def test_result_reader_retries_short_descriptor_reads(self) -> None:
        """Accumulate valid JSON when the operating system returns short reads."""

        original_read = os.read

        def short_read(descriptor: int, count: int) -> bytes:
            return original_read(descriptor, min(count, 3))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text('{"comments": []}', encoding="utf-8")
            with patched_attr(os, "read", short_read):
                loaded = result.load_ocr_result(path)

        self.assertEqual(loaded, {"comments": []})

    def test_result_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.json"
            target.write_text("{}", encoding="utf-8")
            result_path = Path(tmp) / "result.json"
            result_path.symlink_to(target)

            with self.assertRaises(result.OcrResultMissing):
                result.load_ocr_result(result_path)

    def test_oversized_result_is_rejected_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr.json"
            path.write_text("{}", encoding="utf-8")

            with patched_env(OCR_MAX_RESULT_BYTES="1"):
                with self.assertRaises(result.OcrResultTooLarge):
                    result.load_ocr_result(path)

    def test_non_utf8_result_is_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr.json"
            path.write_bytes(b"\xff")

            with self.assertRaises(result.OcrResultMalformed):
                result.load_ocr_result(path)

    def test_deep_result_json_is_controlled_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr.json"
            path.write_text("[" * 1200 + "]" * 1200, encoding="utf-8")

            with self.assertRaises(result.OcrResultMalformed):
                result.load_ocr_result(path)

    def test_sensitive_ocr_values_are_redacted_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr.json"
            path.write_text(
                json.dumps(
                    {
                        "comments": [
                            {
                                "path": "file.py",
                                "line": 1,
                                "content": "Authorization: ApiKey abc123",
                            }
                        ],
                        "message": "password=secret",
                    }
                ),
                encoding="utf-8",
            )

            loaded = result.load_ocr_result(path)

        text = json.dumps(loaded)
        self.assertNotIn("abc123", text)
        self.assertNotIn("secret", text)

    def test_billing_classifier_ignores_file_name(self) -> None:
        warnings = [
            {"file": "billing.py", "type": "subtask_error", "message": "lint failed"},
            {"file": "x.py", "type": "subtask_error", "message": "402 Payment Required"},
        ]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 1)
        self.assertIn("402 Payment Required", matches[0])

    def test_billing_classifier_ignores_generic_billing_text(self) -> None:
        warnings = [
            {"file": "x.py", "type": "subtask_error", "message": "billing module failed tests"}
        ]

        self.assertEqual(result.llm_billing_failure_warnings(warnings), [])

    def test_billing_classifier_tolerates_cyclic_warning_objects(self) -> None:
        """Do not recurse forever if an in-memory caller supplies a cycle."""

        warning: dict[str, Any] = {"message": "ordinary warning"}
        warning["error"] = warning

        self.assertEqual(result.llm_billing_failure_warnings([warning]), [])

    def test_billing_classifier_reads_nested_provider_error_fields(self) -> None:
        warnings = [
            {
                "file": "x.py",
                "error": {"code": 402, "message": "insufficient_quota"},
            }
        ]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 1)
        self.assertIn("insufficient_quota", matches[0])

    def test_billing_classifier_matches_numeric_status_without_message(self) -> None:
        warnings = [{"file": "x.py", "status": 402, "type": "subtask_error"}]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 1)
        self.assertIn("status: 402", matches[0])

    def test_billing_classifier_matches_nested_numeric_code_without_message(self) -> None:
        warnings = [{"file": "x.py", "error": {"code": 402}}]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 1)
        self.assertIn("code: 402", matches[0])

    def test_billing_classifier_reads_embedded_provider_json_message(self) -> None:
        warnings = [
            {
                "file": "x.py",
                "message": '{"error":{"code":"insufficient_funds","message":"Insufficient user balance","extra":{}}}',
                "type": "subtask_error",
            }
        ]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 1)
        self.assertIn("insufficient_funds", matches[0])
        self.assertIn("Insufficient user balance", matches[0])

    def test_billing_classifier_matches_status_code_shapes(self) -> None:
        warnings = [
            {"status_code": 402, "message": "provider rejected request"},
            {"error": {"details": {"status_code": "402"}}},
            '{"status_code": 402, "message": "provider rejected request"}',
            "status_code: 402",
        ]

        matches = result.llm_billing_failure_warnings(warnings)

        self.assertEqual(len(matches), 4)

    def test_billing_classifier_ignores_non_billing_status_code(self) -> None:
        warnings = [
            {"status_code": 200, "message": "billing report generated"},
            '{"status_code": 200, "message": "billing report generated"}',
        ]

        self.assertEqual(result.llm_billing_failure_warnings(warnings), [])

    def test_token_usage_mapping_is_depth_bounded(self) -> None:
        value: dict[str, Any] = {"total_tokens": 123}
        for _ in range(20):
            value = {"usage": value}

        self.assertIsNone(posting_formatting.token_usage_mapping(value))
        self.assertEqual(
            posting_formatting.token_usage_mapping(value, max_depth=25),
            {"total_tokens": 123},
        )
