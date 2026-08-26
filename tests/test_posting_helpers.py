"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import json
import os
import random
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ocr_toolkit import ocr_result
from ocr_toolkit.common.git import isolated_git_environment, read_only_git_prefix
from ocr_toolkit.posting import comments as posting_comments
from ocr_toolkit.posting import formatting as posting_formatting
from ocr_toolkit.posting import (
    gitlab,
    markers,
    payloads,
    reconciliation,
    result,
    settings,
    snapshot,
    workflow,
)
from ocr_toolkit.posting.markers import FINGERPRINT_LEN, build_marker
from ocr_toolkit.posting.suggestions import SuggestionDecision, SuggestionState
from ocr_toolkit.posting.transaction import PostingTransaction
from ocr_toolkit.pre_execution import (
    BACKGROUND_CHARACTER_LIMIT_REASON,
    BACKGROUND_FILE_SIZE_LIMIT_REASON,
    PROTECTED_TARGET_RULE_PATH_PENDING,
    STATUS_SCHEMA,
    PreExecutionStatus,
    write_pre_execution_status,
)
from ocr_toolkit.provider_failure import ProviderFailureReason
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

    def test_invalid_v5_publication_state_never_reaches_normal_result_flow(self) -> None:
        notes: list[str] = []
        result_data = {
            "status": "failed",
            "comments": [{"content": "locally retained safe finding"}],
            "_ocr_toolkit": {
                "schema_version": 5,
                "publication": {"dlp": "blocked"},
            },
        }

        with (
            patched_attr(
                workflow,
                "post_review_note_bounded",
                lambda _config, title, *_args: notes.append(title) or {"id": 1},
            ),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            redirect_stderr(io.StringIO()),
        ):
            exit_code = workflow.post_results(gitlab_config(), result_data)

        self.assertEqual(exit_code, 0)
        self.assertEqual(notes, ["**Open Code Review publication policy error**"])

    def test_advisory_without_exact_receipt_v5_never_reaches_normal_result_flow(self) -> None:
        """Treat a correctly shaped but unbound advisory as an invalid result."""

        notes: list[str] = []
        advisory = ocr_result.toolkit_advisory_payload(
            ocr_result.background_recommended_advisory(actual=2_100, recommended=2_000)
        )
        with (
            patched_attr(
                workflow,
                "post_review_note_bounded",
                lambda _config, title, *_args: notes.append(title) or {"id": 1},
            ),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            redirect_stderr(io.StringIO()),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "complete",
                    "comments": [],
                    "warnings": [],
                    ocr_result.TOOLKIT_ADVISORY_KEY: advisory,
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(notes, ["**Open Code Review result schema error**"])

    def test_advisory_parser_rejects_unknown_extended_and_malformed_values(self) -> None:
        """Accept no provider text, schema extension, boolean, or impossible threshold."""

        valid = ocr_result.toolkit_advisory_payload(
            ocr_result.background_recommended_advisory(actual=2_100, recommended=2_000)
        )
        cases = (
            {},
            {**valid, "provider": "untrusted"},
            {**valid, "kind": "unknown"},
            {**valid, "actual": True},
            {**valid, "actual": 2_000},
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ocr_result.OcrResultMalformed):
                    ocr_result.parse_toolkit_advisory(value)

    def test_advisory_renders_only_inside_technical_details(self) -> None:
        """Keep the complete status ordinary and render only fixed labels plus numbers."""

        advisory = ocr_result.background_recommended_advisory(actual=2_100, recommended=2_000)
        line = posting_formatting.format_ocr_core_advisory(advisory)
        summary = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=0,
            outcome_status="success",
            ocr_core_advisory_summary=line,
            emoji=True,
        )
        visible, technical = summary.split("<details>", 1)

        self.assertIn("✅ **Review complete — no findings**", visible)
        self.assertNotIn("OCR core advisory", visible)
        self.assertIn(
            "- OCR core advisory: background 2100 characters; recommended 2000 characters; "
            "accepted by OCR core",
            technical,
        )

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

    def test_partial_publication_reuses_previous_fingerprint_without_duplicate(self) -> None:
        previous = snapshot.BotCommentRefs()
        comments = [
            {"path": "src/a.py", "line": 7, "content": "same finding"},
            {"path": "src/b.py", "line": 9, "content": "new finding"},
        ]
        markers.annotate_comment_fingerprints(comments)
        previous.published_fingerprints.add(comments[0]["_ocr_fingerprint"])

        kept, carried = snapshot.filter_previously_published_comments(comments, previous)

        self.assertEqual(carried, 1)
        self.assertEqual(kept, [comments[1]])

    def test_markers_are_parsed_only_from_owned_preamble(self) -> None:
        first = "a" * FINGERPRINT_LEN
        second = "b" * FINGERPRINT_LEN
        body = f"{markers.build_marker(first)}\nfinding text\n{markers.build_marker(second)}\nother"

        self.assertEqual(
            markers.finding_fingerprints_from_marked_body(body),
            {first},
        )
        self.assertTrue(
            markers.has_summary_run_marker(
                f"{markers.build_marker(None)}\n{markers.build_summary_run_marker('c' * 32)}"
            )
        )
        self.assertFalse(
            markers.has_summary_run_marker(
                f"{markers.build_marker(None)}\nvisible text\n"
                f"{markers.build_summary_run_marker('c' * 32)}"
            )
        )
        self.assertTrue(
            markers.has_setup_pending_marker(
                f"{markers.build_marker(None)}\n{markers.SETUP_PENDING_MARKER}"
            )
        )
        self.assertFalse(
            markers.has_setup_pending_marker(
                f"{markers.build_marker(None)}\nvisible\n{markers.SETUP_PENDING_MARKER}"
            )
        )

    def test_partial_publication_consumes_one_legacy_marker_per_duplicate(self) -> None:
        comments = [
            {"path": "src/a.py", "line": 7, "content": "same finding"},
            {"path": "src/a.py", "line": 7, "content": "same finding"},
        ]
        markers.annotate_comment_fingerprints(comments)
        legacy = markers.line_based_comment_fingerprint(comments[0])
        self.assertIsNotNone(legacy)
        previous = snapshot.BotCommentRefs(published_fingerprints={legacy or ""})

        kept, carried = snapshot.filter_previously_published_comments(comments, previous)

        self.assertEqual(carried, 1)
        self.assertEqual(kept, [comments[1]])

    def test_write_result_rejects_unknown_outcomes_and_malformed_write_ids(self) -> None:
        with self.assertRaises(ValueError):
            gitlab.GitLabWriteResult("retry")
        with self.assertRaises(ValueError):
            gitlab.GitLabWriteResult("ambiguous_create", write_id="A" * 32)
        with self.assertRaises(ValueError):
            gitlab.GitLabWriteResult("ambiguous_create", write_id="a" * 32)

    def test_provider_author_id_parsers_require_exact_positive_integers(self) -> None:
        valid = {"author": {"id": 7}}
        self.assertEqual(markers.author_id_from_note(valid), 7)
        for value in (True, 0, -1, "7", 7.0, None):
            with self.subTest(value=value):
                self.assertIsNone(markers.author_id_from_note({"author": {"id": value}}))

        identity_calls: list[tuple[str, str]] = []

        def identity_request(url: str, _token: str, _header: str, **kwargs: Any) -> Any:
            identity_calls.append((url, kwargs.get("method", "GET")))
            return {"id": 7, "username": "ocr_bot"}

        with patched_attr(gitlab, "api_request_url", identity_request):
            self.assertEqual(
                gitlab.fetch_posting_identity("https://gitlab.example", "token", "PRIVATE-TOKEN"),
                (7, "ocr_bot"),
            )
        self.assertEqual(identity_calls, [("https://gitlab.example/api/v4/user", "GET")])
        for value in (True, 0, -1, "7", 7.0, None):
            with (
                self.subTest(value=value),
                patched_attr(
                    gitlab, "api_request_url", lambda *_args, item=value, **_kwargs: {"id": item}
                ),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(
                    gitlab.fetch_posting_identity(
                        "https://gitlab.example", "token", "PRIVATE-TOKEN"
                    ),
                    (None, None),
                )

    def test_posting_identity_consumers_reject_bool_and_nonpositive_ids(self) -> None:
        refs = snapshot.BotCommentRefs()
        notes = [
            {
                "id": value,
                "body": build_marker(None) + "\nbot",
                "author": {"id": 7},
            }
            for value in (True, 0, -1)
        ]
        snapshot.process_discussion_for_refs(
            gitlab_config(), refs, "discussion-id", notes, preserve_human_touched=False
        )
        self.assertEqual(refs.discussion_note_refs, [])

        transaction = PostingTransaction()
        self.assertFalse(transaction.record_discussion("../unsafe", 7))
        self.assertFalse(transaction.record_discussion("discussion-id", True))
        self.assertEqual(transaction.discussion_note_refs, ())

    def test_write_marker_has_closed_independent_identity_grammar(self) -> None:
        write_id = "1" * 32
        body = f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n{markers.build_write_marker(write_id)}\nbody"

        self.assertEqual(markers.write_id_from_body(body), write_id)
        self.assertNotEqual(write_id, "a" * FINGERPRINT_LEN)
        quoted = f"{body}\nquoted marker text: <!-- open-code-review-write id={'2' * 32} -->"
        self.assertEqual(markers.write_id_from_body(quoted), write_id)
        for malformed in (
            "<!-- open-code-review-write id=ABC -->",
            f"{markers.build_marker(None)}\n{markers.build_write_marker(write_id)} extra",
            f"{markers.build_marker(None)}\n<!-- open-code-review-write id=ABC -->",
        ):
            with self.subTest(body=malformed):
                self.assertIsNone(markers.write_id_from_body(malformed))
        with self.assertRaises(ValueError):
            markers.build_write_marker("A" * 32)

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

    def test_live_bot_mention_command_supports_gitlab_username_punctuation(self) -> None:
        cases = {
            "@mr.bot resolve": "resolve",
            "  @MR.BOT   SUPPRESS\n \t": "suppress",
            "/ocr resolve": "resolve",
        }
        for body, expected in cases.items():
            with self.subTest(body=body):
                self.assertEqual(
                    markers.reviewer_command_from_body(body, bot_username="mr.bot"),
                    expected,
                )

    def test_live_bot_mention_command_rejects_non_exact_replies(self) -> None:
        rejected = (
            "@mr.bot supress",
            "@mr.bot resolve please",
            "Please @mr.bot resolve",
            "```\n@mr.bot resolve\n```",
            "@other.bot resolve",
            "@mrXbot resolve",
            "@mr.bot retest",
        )
        for body in rejected:
            with self.subTest(body=body):
                self.assertIsNone(markers.reviewer_command_from_body(body, bot_username="mr.bot"))
        self.assertIsNone(markers.reviewer_command_from_body("@mr.bot resolve", bot_username=None))

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
            {"body": "@mr.bot resolve", "author": {"id": 8}},
            {"body": "/ocr suppress", "author": {"id": 9}},
            {"body": "@mr.bot resolve", "author": {"id": 7}},
            {"body": "@mr.bot resolve", "author": {"id": 10}, "system": True},
        ]

        self.assertEqual(
            snapshot.reviewer_command_in_thread(gitlab_config(current_username="mr.bot"), notes),
            "suppress",
        )

    def test_mention_commands_require_a_toolkit_owned_discussion(self) -> None:
        fingerprint = "e" * FINGERPRINT_LEN
        config = gitlab_config(current_username="mr.bot")
        for action in ("suppress", "resolve"):
            with self.subTest(action=action):
                owned = snapshot.BotCommentRefs()
                discussion_id = f"owned-{action}"
                snapshot.process_discussion_for_refs(
                    config,
                    owned,
                    discussion_id,
                    [
                        {
                            "id": 10,
                            "body": build_marker(fingerprint) + "\nbody",
                            "author": {"id": 7},
                            "position": {"new_path": "file.py", "new_line": 10},
                        },
                        {"id": 11, "body": f"@mr.bot {action}", "author": {"id": 8}},
                    ],
                )

                self.assertEqual(
                    owned.discussions_to_resolve,
                    [discussion_id] if action == "resolve" else [],
                )
                self.assertEqual(owned.suppressed_fingerprints, {fingerprint})

        foreign = snapshot.BotCommentRefs()
        snapshot.process_discussion_for_refs(
            config,
            foreign,
            "foreign-discussion",
            [
                {"id": 20, "body": "ordinary root", "author": {"id": 8}},
                {"id": 21, "body": "@mr.bot resolve", "author": {"id": 9}},
            ],
        )

        self.assertEqual(foreign, snapshot.BotCommentRefs())

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

    def test_post_results_retains_finding_but_omits_unproven_suggestion(self) -> None:
        inline_bodies: list[str] = []

        def capture_discussion(*args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
            inline_bodies.append(kwargs["body"])
            return gitlab.GitLabWriteResult("posted")

        with (
            patched_attr(
                workflow,
                "get_diff_refs",
                lambda _config: {"base_sha": "a", "start_sha": "b", "head_sha": "c"},
            ),
            patched_attr(
                workflow,
                "head_file_text",
                lambda *_args: "route:\n  destination: 192.0.2.0/24\n",
            ),
            patched_attr(
                workflow,
                "collect_previous_bot_comment_refs",
                lambda _config: snapshot.BotCommentRefs(),
            ),
            patched_attr(workflow, "post_review_discussion", capture_discussion),
            patched_attr(
                workflow,
                "post_review_note_bounded",
                lambda *_args: {"id": 1},
            ),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: None,
            ),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "comments": [
                        {
                            "path": "config/service.yml",
                            "start_line": 1,
                            "end_line": 2,
                            "content": "Use the documentation network.",
                            "existing_code": "stale content",
                            "suggestion_code": "route:\n  destination: 198.51.100.0/24",
                        }
                    ]
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(inline_bodies), 1)
        self.assertIn("Use the documentation network.", inline_bodies[0])
        self.assertIn("did not match the reviewed range", inline_bodies[0])
        self.assertNotIn("```suggestion", inline_bodies[0])

    def test_post_results_applies_opt_in_badges_to_inline_findings_only(self) -> None:
        inline_bodies: list[str] = []
        notes: list[str] = []

        def capture_discussion(*_args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
            inline_bodies.append(kwargs["body"])
            return gitlab.GitLabWriteResult("posted")

        def capture_note(
            _config: gitlab.GitLabConfig,
            _title: str,
            body: str,
            _drafts: list[int],
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": len(notes)}

        settings.post_badges.cache_clear()
        try:
            with (
                patched_env(OCR_POST_BADGES="shields"),
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
                patched_attr(workflow, "post_review_discussion", capture_discussion),
                patched_attr(workflow, "post_review_note_bounded", capture_note),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
                patched_attr(
                    workflow,
                    "delete_previous_bot_comments_if_collected",
                    lambda *_args: None,
                ),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = workflow.post_results(
                    gitlab_config(),
                    {
                        "comments": [
                            {
                                "path": "src/example.py",
                                "line": 7,
                                "content": "Guard this branch.",
                                "category": "bug",
                                "severity": "high",
                            }
                        ]
                    },
                )
        finally:
            settings.post_badges.cache_clear()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(inline_bodies), 1)
        self.assertIn(
            "![bug · high](https://img.shields.io/badge/bug-high-red)",
            inline_bodies[0],
        )
        summary = next(note for note in notes if "## Open Code Review" in note)
        self.assertNotIn("img.shields.io", summary)

    def test_retry_report_remains_private_from_gitlab_notes(self) -> None:
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
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: None,
            ),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "comments": [],
                    "retry_report": {
                        "schema_version": "ocr.llm-retry-report/v1",
                        "review_stage": "Core review",
                        "provider": "private-provider",
                        "file_path": "private/example.py",
                    },
                },
            )

        self.assertEqual(exit_code, 0)
        published = "\n".join(notes)
        self.assertNotIn("retry_report", published)
        self.assertNotIn("Core review", published)
        self.assertNotIn("private-provider", published)
        self.assertNotIn("private/example.py", published)

    def test_invalid_inline_position_falls_back_without_rollback(self) -> None:
        calls: list[str] = []

        def fake_post_review_discussion(*args: Any, **kwargs: Any) -> gitlab.GitLabWriteResult:
            calls.append("inline")
            return gitlab.GitLabWriteResult("invalid_position", create_kind="discussion")

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
                                    {"comments": [], "warnings": []},
                                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0][0], "")
        self.assertEqual(notes[0][1].count("## Open Code Review"), 1)
        self.assertIn("✅ **Review complete — no findings**", notes[0][1])
        self.assertNotIn("\nNo findings", notes[0][1])
        self.assertNotIn("verified MCP calls", notes[0][1])
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
        assert "no supported files changed" in notes[0]
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
        summary_cleanup_calls: list[str] = []
        previous = snapshot.BotCommentRefs(summary_plain_note_ids=[91])

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
                lambda _config: previous,
            ),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: cleanup_calls.append("delete"),
            ),
            patched_attr(
                workflow,
                "delete_previous_summary_notes",
                lambda _config, refs: summary_cleanup_calls.append(
                    "summary" if refs is previous else "wrong"
                ),
            ),
            patched_attr(workflow, "resolve_requested_discussions", lambda *_args: None),
        ):
            exit_code = workflow.post_results(gitlab_config(), result_data)

        self.assertEqual(exit_code, 0)
        self.assertEqual(cleanup_calls, [])
        self.assertEqual(summary_cleanup_calls, ["summary"])
        self.assertIn("Coverage: selected 2; completed 1", notes[0])
        self.assertNotIn("No issues found", notes[0])

    def test_filtered_publication_posts_safe_new_findings_and_preserves_previous(self) -> None:
        notes: list[str] = []
        cleanup_calls: list[str] = []
        previous = snapshot.BotCommentRefs()
        old = {"path": "src/old.py", "line": 7, "content": "Existing safe finding."}
        new = {"path": "src/new.py", "line": 9, "content": "New safe finding."}
        old_fingerprint = markers.comment_fingerprint(old)
        self.assertIsNotNone(old_fingerprint)
        previous.published_fingerprints.add(old_fingerprint or "")
        publication = {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 1,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 0,
                "secret": 0,
            },
            "retained": {"comments": 2, "warnings": 0},
            "omitted": {"comments": 1, "warnings": 0, "fields": 0},
            "original": {
                "outcome": "clean",
                "selected": 3,
                "completed": 3,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }

        def capture_note(_config: Any, *args: Any) -> dict[str, int]:
            notes.append("\n".join(value for value in args if isinstance(value, str)))
            return {"id": len(notes)}

        with (
            patched_attr(workflow, "collect_previous_bot_comment_refs", lambda _config: previous),
            patched_attr(workflow, "get_diff_refs", lambda _config: None),
            patched_attr(workflow, "post_review_note_bounded", capture_note),
            patched_attr(workflow, "finalize_posting", lambda *_args: True),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: cleanup_calls.append("delete"),
            ),
            patched_attr(workflow, "resolve_requested_discussions", lambda *_args: None),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "status": "completed_with_errors",
                    "comments": [old, new],
                    "warnings": [],
                    "_ocr_toolkit": {"schema_version": 5, "publication": publication},
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(cleanup_calls, [])
        rendered = "\n".join(notes)
        self.assertIn("New safe finding.", rendered)
        self.assertNotIn("Existing safe finding.", rendered)
        self.assertIn("<summary>Publication filtering signal</summary>", rendered)
        self.assertIn('"carried_forward_comments":1', rendered)

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
            },
            suggestion_decision=SuggestionDecision(
                SuggestionState.ACTIONABLE,
                replacement="safe()",
                range_suffix="-0+0",
            ),
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

    def test_inline_payload_reserves_write_and_finding_markers_before_utf8_truncation(self) -> None:
        fingerprint = "a" * FINGERPRINT_LEN
        write_id = "b" * 32
        built = payloads.build_marked_note_body(
            "ж" * (settings.MAX_INLINE_NOTE_CHARS * 2),
            fingerprint=fingerprint,
            write_id=write_id,
            max_chars=settings.MAX_INLINE_NOTE_CHARS,
            inline=True,
        )

        self.assertTrue(
            built.startswith(
                f"{markers.build_marker(fingerprint)}\n{markers.build_write_marker(write_id)}\n"
            )
        )
        self.assertEqual(markers.write_id_from_body(built), write_id)
        self.assertLessEqual(len(built), settings.MAX_INLINE_NOTE_CHARS)
        self.assertLessEqual(len(built.encode("utf-8")), settings.MAX_INLINE_NOTE_CHARS)

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
    def test_nonzero_ocr_projects_retry_report_to_static_provider_note(self) -> None:
        """Publish only a closed 429 reason and keep raw result and stderr data private."""

        notes: list[str] = []
        private_values = (
            "private-provider",
            "private-model",
            "/private/repository/file.py",
            "private-request-id",
            "private-response-body",
            "private-finding",
            "private-stderr",
        )
        payload = {
            "comments": [{"content": "private-finding"}],
            "retry_report": {
                "schema_version": "ocr.llm-retry-report/v1",
                "total_requests": 1,
                "retried_requests": 0,
                "total_retries": 0,
                "recovered_requests": 0,
                "failed_requests": 1,
                "cancelled_requests": 0,
                "requests": [
                    {
                        "logical_request_id": "private-logical-id",
                        "provider": "private-provider",
                        "model": "private-model",
                        "file_path": "/private/repository/file.py",
                        "task_type": "main_task",
                        "request_no": 1,
                        "outcome": "failed",
                        "attempts": [
                            {
                                "attempt": 1,
                                "outcome": "error",
                                "error_class": "rate_limited",
                                "failure_phase": "http",
                                "status_code": 429,
                                "request_id": "private-request-id",
                                "provider_body": "private-response-body",
                            }
                        ],
                    }
                ],
            },
        }

        def capture(
            _config: Any, _title: str, body: str, _transaction: PostingTransaction
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "result.json"
            stderr_path = Path(tmp) / "stderr.log"
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            stderr_path.write_text("private-stderr\n/merge", encoding="utf-8")
            stderr = io.StringIO()
            with (
                patched_env(
                    OCR_EXIT_CODE="1",
                    OCR_POST_ERROR_DETAILS="1",
                    OCR_STRICT_POSTING="false",
                ),
                patched_attr(workflow, "load_gitlab_config", lambda: gitlab_config()),
                patched_attr(
                    workflow,
                    "repository_artifacts",
                    lambda: (_ for _ in ()).throw(RuntimeError("unavailable")),
                ),
                patched_attr(workflow, "post_review_note_bounded", capture),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
                patched_attr(
                    workflow,
                    "read_stderr_excerpt",
                    lambda *_args: self.fail("classified failure read stderr"),
                ),
                patched_attr(
                    workflow,
                    "execute_approval",
                    lambda *_args: self.fail("provider failure reached approval"),
                ),
                redirect_stderr(stderr),
            ):
                exit_code = workflow.main([str(result_path), str(stderr_path)])

        self.assertEqual(exit_code, 0)
        published = "\n".join(notes)
        controlled_log = stderr.getvalue()
        self.assertIn("rate-or-spending-limit", published)
        self.assertIn("Previous OCR review comments were preserved", published)
        self.assertIn("Automatic approval was not attempted", published)
        for private in private_values:
            self.assertNotIn(private, published)
            self.assertNotIn(private, controlled_log)

    def test_malformed_retry_report_retains_generic_failure_details_path(self) -> None:
        """Fall back to the existing generic note when private diagnostics contradict v1."""

        notes: list[str] = []
        payload = {
            "retry_report": {
                "schema_version": "ocr.llm-retry-report/v1",
                "total_requests": 1,
                "retried_requests": 0,
                "total_retries": 0,
                "recovered_requests": 0,
                "failed_requests": 2,
                "cancelled_requests": 0,
                "requests": [],
            }
        }

        def capture(
            _config: Any, title: str, body: str, _transaction: PostingTransaction
        ) -> dict[str, int]:
            notes.append(f"{title}\n{body}")
            return {"id": 1}

        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "result.json"
            stderr_path = Path(tmp) / "stderr.log"
            result_path.write_text(json.dumps(payload), encoding="utf-8")
            stderr_path.write_text("safe bounded diagnostic", encoding="utf-8")
            with (
                patched_env(OCR_POST_ERROR_DETAILS="1", OCR_STRICT_POSTING="false"),
                patched_attr(
                    workflow,
                    "repository_artifacts",
                    lambda: (_ for _ in ()).throw(RuntimeError("unavailable")),
                ),
                patched_attr(workflow, "post_review_note_bounded", capture),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
            ):
                exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, 1, result_path)

        self.assertEqual(exit_code, 0)
        self.assertIn("Open Code Review failure", notes[0])
        self.assertIn("safe bounded diagnostic", notes[0])
        self.assertNotIn("provider failure", notes[0].lower())

    def test_legacy_billing_warning_uses_shared_provider_renderer(self) -> None:
        """Route the pre-v1 warning shape to the same closed reason and renderer."""

        reasons: list[ProviderFailureReason] = []
        with patched_attr(
            workflow,
            "post_llm_provider_failure",
            lambda _config, reason: reasons.append(reason) or 0,
        ):
            exit_code = workflow.post_results(
                gitlab_config(),
                {
                    "comments": [{"content": "must not publish"}],
                    "warnings": [
                        {
                            "message": "private provider response: 402 Payment Required",
                            "provider_body": "private-response-body",
                        }
                    ],
                },
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(reasons, [ProviderFailureReason.RATE_OR_SPENDING_LIMIT])

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

    def test_changed_new_lines_failures_are_empty_and_negatively_cached(self) -> None:
        """Fail closed once when the bounded diff cannot be read safely."""

        cases = (
            OSError("git unavailable"),
            type("Result", (), {"returncode": 2, "stdout": ""})(),
            type(
                "Result",
                (),
                {"returncode": 0, "stdout": "x" * (workflow.MAX_REMAP_DIFF_BYTES + 1)},
            )(),
        )
        for result_or_error in cases:
            calls = 0

            def run(*_args: Any, **_kwargs: Any) -> Any:
                nonlocal calls
                calls += 1
                if isinstance(result_or_error, Exception):
                    raise result_or_error
                return result_or_error

            cache: workflow.DiffLineCache = {}
            with (
                self.subTest(case=type(result_or_error).__name__),
                patched_attr(workflow.subprocess, "run", run),
            ):
                self.assertEqual(
                    workflow.changed_new_lines(
                        {"base_sha": "base", "head_sha": "head"}, "file.py", cache
                    ),
                    set(),
                )
                self.assertEqual(
                    workflow.changed_new_lines(
                        {"base_sha": "base", "head_sha": "head"}, "file.py", cache
                    ),
                    set(),
                )
            self.assertEqual(calls, 1)

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

    def test_changed_new_paths_failures_are_empty_and_negatively_cached(self) -> None:
        """Fail closed once when changed-path discovery is unavailable or malformed."""

        cases = (
            OSError("git unavailable"),
            type("Result", (), {"returncode": 2, "stdout": b""})(),
            type("Result", (), {"returncode": 0, "stdout": b"\xff\0"})(),
        )
        for result_or_error in cases:
            calls = 0

            def run(*_args: Any, **_kwargs: Any) -> Any:
                nonlocal calls
                calls += 1
                if isinstance(result_or_error, Exception):
                    raise result_or_error
                return result_or_error

            cache: workflow.ChangedPathCache = {}
            with (
                self.subTest(case=type(result_or_error).__name__),
                patched_attr(workflow.subprocess, "run", run),
            ):
                self.assertEqual(
                    workflow.changed_new_paths({"base_sha": "base", "head_sha": "head"}, cache),
                    [],
                )
                self.assertEqual(
                    workflow.changed_new_paths({"base_sha": "base", "head_sha": "head"}, cache),
                    [],
                )
            self.assertEqual(calls, 1)

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

    def test_head_file_lines_handles_git_failures_and_preserves_line_numbers(self) -> None:
        """Reject unreadable blobs while preserving safe source line identities."""

        refs = {"head_sha": "head"}
        cases = (
            [OSError("git unavailable")],
            [
                type("Result", (), {"returncode": 0, "stdout": "20"})(),
                type("Result", (), {"returncode": 2, "stdout": b""})(),
            ],
        )
        for responses in cases:
            values = iter(responses)

            def run(*_args: Any, **_kwargs: Any) -> Any:
                value = next(values)
                if isinstance(value, Exception):
                    raise value
                return value

            with (
                self.subTest(responses=len(responses)),
                patched_attr(workflow.subprocess, "run", run),
            ):
                self.assertEqual(workflow.head_file_lines(refs, "file.py"), [])

        responses = iter(
            (
                type("Result", (), {"returncode": 0, "stdout": "40"})(),
                type(
                    "Result",
                    (),
                    {"returncode": 0, "stdout": b"first()\n\n  second()  \n"},
                )(),
            )
        )
        cache: workflow.FileLineCache = {}
        with patched_attr(workflow.subprocess, "run", lambda *_args, **_kwargs: next(responses)):
            self.assertEqual(
                workflow.head_file_lines(refs, "file.py", cache),
                [(1, "first()"), (3, "  second()")],
            )
            self.assertEqual(
                workflow.head_file_lines(refs, "file.py", cache),
                [(1, "first()"), (3, "  second()")],
            )

    def test_head_file_text_uses_only_safe_bounded_git_blobs(self) -> None:
        """Read only safe repository paths through the bounded Git blob contract."""

        refs = {"head_sha": "head"}
        cache: workflow.FileTextCache = {}
        self.assertIsNone(workflow.head_file_text(refs, "../private", cache))
        self.assertIsNone(workflow.head_file_text(refs, "../private", cache))

        with patched_attr(
            workflow.subprocess,
            "run",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid size")),
        ):
            self.assertIsNone(workflow.head_file_text(refs, "broken.py"))

        responses = iter(
            (
                type("Result", (), {"returncode": 0, "stdout": "8"})(),
                type("Result", (), {"returncode": 0, "stdout": b"value=1\n"})(),
            )
        )
        cache = {}
        with patched_attr(workflow.subprocess, "run", lambda *_args, **_kwargs: next(responses)):
            self.assertEqual(workflow.head_file_text(refs, "safe.py", cache), "value=1\n")
            self.assertEqual(workflow.head_file_text(refs, "safe.py", cache), "value=1\n")

    def test_workflow_identity_helpers_fail_closed_on_ambiguous_values(self) -> None:
        """Keep inline, approval, and reviewed-SHA identities unambiguous."""

        self.assertEqual(workflow.inline_skip_reason(None, "file.py", 1), "missing_diff_refs")
        self.assertEqual(workflow.inline_skip_reason({}, "", 1), "missing_path")
        self.assertEqual(workflow.inline_skip_reason({}, "file.py", 0), "missing_line")
        self.assertEqual(workflow.inline_skip_reason({}, "file.py", 1), "unknown")

        for metadata in (
            None,
            {"schema_version": 4},
            {"schema_version": 5, "review": []},
            {
                "schema_version": 5,
                "review": {"source_sha": "invalid", "mr_author_id": True},
            },
        ):
            with self.subTest(metadata=metadata):
                self.assertEqual(workflow.approval_receipt_identity(metadata), ("", None))
        self.assertEqual(
            workflow.approval_receipt_identity(
                {
                    "schema_version": 5,
                    "review": {"source_sha": "a" * 40, "mr_author_id": 41},
                }
            ),
            ("a" * 40, 41),
        )

        with patched_env(
            CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="0" * 40,
            CI_COMMIT_SHA="b" * 40,
        ):
            self.assertEqual(workflow.reviewed_sha(), "b" * 40)

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

    def test_parse_error_preserves_previous_review_and_respects_strict_mode(self) -> None:
        """Preserve prior review state and apply strictness after result parse failure."""

        stderr_path = Path("unused-stderr.log")
        read_paths: list[Path] = []

        def safe_excerpt(path: Path) -> str:
            read_paths.append(path)
            return "token=***\n/merge"

        for details, strict, expected in (("0", "false", 0), ("1", "true", 1)):
            notes: list[str] = []

            def capture(
                _config: Any, _title: str, body: str, _transaction: PostingTransaction
            ) -> dict[str, int]:
                notes.append(body)
                return {"id": 1}

            with (
                self.subTest(details=details, strict=strict),
                patched_env(OCR_POST_ERROR_DETAILS=details, OCR_STRICT_POSTING=strict),
                patched_attr(workflow, "read_stderr_excerpt", safe_excerpt),
                patched_attr(workflow, "post_review_note_bounded", capture),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
            ):
                exit_code = workflow.post_parse_error(gitlab_config(), stderr_path)

            self.assertEqual(exit_code, expected)
            self.assertNotIn("\n/merge", notes[0])
            self.assertEqual("token=***" in notes[0], details == "1")

        self.assertEqual(read_paths, [stderr_path])

    def test_missing_result_failure_is_distinct_and_preserves_previous_review(self) -> None:
        """Report a missing result distinctly without deleting the prior review."""

        notes: list[str] = []

        def capture(
            _config: Any, _title: str, body: str, _transaction: PostingTransaction
        ) -> dict[str, int]:
            notes.append(body)
            return {"id": 1}

        with tempfile.TemporaryDirectory() as tmp:
            stderr_path = Path(tmp) / "stderr.log"
            with (
                patched_env(OCR_POST_ERROR_DETAILS="0"),
                patched_attr(
                    workflow,
                    "repository_artifacts",
                    lambda: (_ for _ in ()).throw(RuntimeError("unavailable")),
                ),
                patched_attr(workflow, "post_review_note_bounded", capture),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
            ):
                exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, -1)

        self.assertEqual(exit_code, 0)
        self.assertIn("result file was missing", notes[0])
        self.assertNotIn("exit code", notes[0])
        self.assertIn("Previous OCR review comments were preserved", notes[0])

    def test_provider_failure_renderer_is_static_and_respects_strict_mode(self) -> None:
        """Render only closed guidance while retaining advisory versus strict behavior."""

        for strict, expected in (("false", 0), ("true", 1)):
            notes: list[str] = []

            def capture(
                _config: Any, _title: str, body: str, _transaction: PostingTransaction
            ) -> dict[str, int]:
                notes.append(body)
                return {"id": 1}

            with (
                self.subTest(strict=strict),
                patched_env(OCR_STRICT_POSTING=strict),
                patched_attr(workflow, "post_review_note_bounded", capture),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = workflow.post_llm_provider_failure(
                    gitlab_config(), ProviderFailureReason.RATE_OR_SPENDING_LIMIT
                )

            self.assertEqual(exit_code, expected)
            self.assertIn("rate-or-spending-limit", notes[0])
            self.assertIn("cost reservation", notes[0])
            self.assertIn("OCR_LLM_MAX_COMPLETION_TOKENS", notes[0])
            self.assertIn("4096", notes[0])

    def test_previous_review_cleanup_depends_only_on_coverage_completeness(self) -> None:
        """Clean prior review state only after complete replacement coverage."""

        previous = snapshot.BotCommentRefs(discussions_to_resolve=["discussion-17"])
        calls: list[str] = []
        partial = ReviewOutcome(status="partial", kind="partial", budget_exceeded=False)
        complete = ReviewOutcome(status="success", kind="clean", budget_exceeded=False)

        with (
            patched_attr(
                workflow,
                "delete_previous_summary_notes",
                lambda *_args: calls.append("summary"),
            ),
            patched_attr(
                workflow,
                "delete_previous_bot_comments_if_collected",
                lambda *_args: calls.append("complete"),
            ),
            patched_attr(
                workflow,
                "resolve_requested_discussions",
                lambda *_args: calls.append("resolve"),
            ),
        ):
            workflow.finalize_previous_review_state(gitlab_config(), previous, partial)
            workflow.finalize_previous_review_state(gitlab_config(), previous, complete)

        self.assertEqual(calls, ["summary", "resolve", "complete", "resolve"])

    def test_setup_pending_status_selects_only_static_text_and_preserves_exit_modes(self) -> None:
        for emoji, strict, expected_exit in (("true", "false", 0), ("false", "true", 1)):
            with self.subTest(emoji=emoji, strict=strict), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / ".review-context"
                directory.mkdir(mode=0o700)
                status_path = directory / "pre-execution-status.json"
                write_pre_execution_status(
                    status_path,
                    PreExecutionStatus(
                        schema_version=STATUS_SCHEMA,
                        reason=PROTECTED_TARGET_RULE_PATH_PENDING,
                        diff_base_sha="a" * 40,
                        source_sha="b" * 40,
                        policy_sha="c" * 40,
                    ),
                )
                stderr_path = root / "stderr.log"
                stderr_path.write_text("/merge repository-controlled details\n", encoding="utf-8")
                notes: list[tuple[str, str]] = []
                setup_cleanup: list[list[int]] = []
                previous = snapshot.BotCommentRefs(
                    summary_plain_note_ids=[8], setup_plain_note_ids=[9]
                )

                def capture_note(
                    _config: gitlab.GitLabConfig,
                    title: str,
                    body: str,
                    _transaction: PostingTransaction,
                ) -> dict[str, int]:
                    notes.append((title, body))
                    return {"id": 1}

                settings.post_emoji.cache_clear()
                with (
                    patched_env(
                        CI_MERGE_REQUEST_DIFF_BASE_SHA="a" * 40,
                        CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="b" * 40,
                        OCR_POST_EMOJI=emoji,
                        OCR_POST_ERROR_DETAILS="1",
                        OCR_STRICT_POSTING=strict,
                    ),
                    patched_attr(
                        workflow,
                        "repository_artifacts",
                        lambda: type("Artifacts", (), {"pre_execution_status": status_path})(),
                    ),
                    patched_attr(workflow, "post_review_note_bounded", capture_note),
                    patched_attr(workflow, "finalize_posting", lambda *_args: True),
                    patched_attr(
                        workflow,
                        "collect_previous_bot_comment_refs",
                        lambda *_args: previous,
                    ),
                    patched_attr(
                        workflow,
                        "delete_previous_setup_notes",
                        lambda _config, refs: setup_cleanup.append(refs.setup_plain_note_ids),
                    ),
                ):
                    exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, 2)

                self.assertEqual(exit_code, expected_exit)
                self.assertEqual(len(notes), 1)
                self.assertEqual("⏳" in notes[0][0], emoji == "true")
                self.assertIn("did not run", notes[0][1])
                self.assertIn("Previous Open Code Review comments were preserved", notes[0][1])
                self.assertIn(markers.SETUP_PENDING_MARKER, notes[0][1])
                self.assertNotIn("/merge", notes[0][1])
                self.assertNotIn("rules.json", notes[0][1])
                self.assertEqual(setup_cleanup, [[9]])

    def test_stale_setup_status_falls_back_to_generic_failure(self) -> None:
        notes: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / ".review-context"
            directory.mkdir(mode=0o700)
            status_path = directory / "pre-execution-status.json"
            write_pre_execution_status(
                status_path,
                PreExecutionStatus(
                    schema_version=STATUS_SCHEMA,
                    reason=PROTECTED_TARGET_RULE_PATH_PENDING,
                    diff_base_sha="a" * 40,
                    source_sha="b" * 40,
                    policy_sha="c" * 40,
                ),
            )
            stderr_path = root / "stderr.log"
            stderr_path.write_text("generic details\n", encoding="utf-8")

            def capture_note(
                _config: gitlab.GitLabConfig,
                _title: str,
                body: str,
                _transaction: PostingTransaction,
            ) -> dict[str, int]:
                notes.append(body)
                return {"id": 1}

            with (
                patched_env(
                    CI_MERGE_REQUEST_DIFF_BASE_SHA="a" * 40,
                    CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="d" * 40,
                    OCR_POST_ERROR_DETAILS="1",
                ),
                patched_attr(
                    workflow,
                    "repository_artifacts",
                    lambda: type("Artifacts", (), {"pre_execution_status": status_path})(),
                ),
                patched_attr(workflow, "post_review_note_bounded", capture_note),
                patched_attr(workflow, "finalize_posting", lambda *_args: True),
            ):
                exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, 2)

        self.assertEqual(exit_code, 0)
        self.assertIn("result may be partial", notes[0])
        self.assertIn("generic details", notes[0])

    def test_background_rejection_status_uses_only_static_numeric_summary(self) -> None:
        """Publish installed-OCR limits without its private path or raw stderr."""

        for reason, actual, limit, unit in (
            (BACKGROUND_CHARACTER_LIMIT_REASON, 8_001, 8_000, "characters"),
            (BACKGROUND_FILE_SIZE_LIMIT_REASON, 1_048_577, 1_048_576, "bytes"),
        ):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / ".review-context"
                directory.mkdir(mode=0o700)
                status_path = directory / "pre-execution-status.json"
                write_pre_execution_status(
                    status_path,
                    PreExecutionStatus(
                        schema_version=STATUS_SCHEMA,
                        reason=reason,
                        diff_base_sha="a" * 40,
                        source_sha="b" * 40,
                        policy_sha="c" * 40,
                        actual=actual,
                        limit=limit,
                        unit=unit,
                    ),
                )
                stderr_path = root / "stderr.log"
                stderr_path.write_text(
                    'Error: background file "/private/provider/background.md" secret-value\n',
                    encoding="utf-8",
                )
                notes: list[tuple[str, str]] = []

                def capture_note(
                    _config: gitlab.GitLabConfig,
                    title: str,
                    body: str,
                    _transaction: PostingTransaction,
                ) -> dict[str, int]:
                    notes.append((title, body))
                    return {"id": 1}

                with (
                    patched_env(
                        CI_MERGE_REQUEST_DIFF_BASE_SHA="a" * 40,
                        CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="b" * 40,
                        OCR_POST_ERROR_DETAILS="1",
                    ),
                    patched_attr(
                        workflow,
                        "repository_artifacts",
                        lambda: type("Artifacts", (), {"pre_execution_status": status_path})(),
                    ),
                    patched_attr(workflow, "post_review_note_bounded", capture_note),
                    patched_attr(workflow, "finalize_posting", lambda *_args: True),
                ):
                    exit_code = workflow.post_ocr_failure(gitlab_config(), stderr_path, 2)

                self.assertEqual(exit_code, 0)
                self.assertIn("background was rejected", notes[0][0])
                self.assertIn(f"`{actual}` {unit}", notes[0][1])
                self.assertIn(f"`{limit}` {unit}", notes[0][1])
                self.assertIn("model review", notes[0][1])
                self.assertIn("Previous Open Code Review comments were preserved", notes[0][1])
                self.assertNotIn("private", notes[0][1])
                self.assertNotIn("secret-value", notes[0][1])
                self.assertNotIn("background.md", notes[0][1])


class PostingSummaryTests(unittest.TestCase):
    def tearDown(self) -> None:
        settings.post_badges.cache_clear()
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
        """Keep the bounded legacy list fallback for admitted tool names."""

        summary = posting_formatting.format_tool_calls_summary(
            {"by_tool": {}, "calls": [{"name": "file_read"}, {"tool": "code_search"}]}
        )

        self.assertIn("2 total", summary)
        self.assertIn("`file_read`: 1", summary)
        self.assertIn("`code_search`: 1", summary)

    def test_tool_calls_reports_every_useful_nonzero_counter_inline(self) -> None:
        """Expose the complete useful activity breakdown without changing its format."""

        summary = posting_formatting.format_tool_calls_summary(
            {
                "total": 36,
                "by_tool": {
                    "task_done": 1,
                    "file_find": 1,
                    "context_list": 1,
                    "file_read_diff": 2,
                    "context_get": 3,
                    "code_comment": 4,
                    "ocr_toolkit_evidence": 5,
                    "code_search": 7,
                    "file_read": 12,
                },
            }
        )

        self.assertEqual(
            summary,
            "- all OCR tool calls: 36 total "
            "(`file_read`: 12, `code_search`: 7, `ocr_toolkit_evidence`: 5, "
            "`code_comment`: 4, `context_get`: 3, `file_read_diff`: 2, "
            "`context_list`: 1, `file_find`: 1, `task_done`: 1)",
        )
        self.assertNotIn("more", summary)

    def test_tool_calls_omits_empty_zero_or_unknown_breakdowns(self) -> None:
        """Do not emit a technical line without a positive admitted counter list."""

        cases = (
            None,
            7,
            [],
            {"total": 0, "by_tool": {}},
            {"total": 5, "by_tool": {}},
            {"total": 5, "by_tool": {"file_read": 0}},
            {"total": 5, "by_tool": {"dynamic_external_tool": 5}},
            [{"name": "dynamic_external_tool"}],
        )

        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(posting_formatting.format_tool_calls_summary(value), "")

    def test_tool_calls_ignores_invalid_counts_and_rejects_invalid_totals(self) -> None:
        """Admit only bounded integer counters under a consistent positive total."""

        summary = posting_formatting.format_tool_calls_summary(
            {
                "total": 2,
                "by_tool": {
                    "file_read": 2,
                    "code_search": True,
                    "file_find": -1,
                    "task_done": "1",
                    "context_get": 1.0,
                    "context_list": ocr_result.MAX_TOOLKIT_MCP_USAGE_COUNT + 1,
                },
            }
        )

        self.assertEqual(summary, "- all OCR tool calls: 2 total (`file_read`: 2)")
        invalid_totals = (False, 0, -1, "2", 2.0, ocr_result.MAX_TOOLKIT_MCP_USAGE_COUNT + 1)
        for total in invalid_totals:
            with self.subTest(total=total):
                self.assertEqual(
                    posting_formatting.format_tool_calls_summary(
                        {"total": total, "by_tool": {"file_read": 1}}
                    ),
                    "",
                )
        self.assertEqual(
            posting_formatting.format_tool_calls_summary({"total": 1, "by_tool": {"file_read": 2}}),
            "",
        )

    def test_tool_and_token_activity_remain_separate_technical_lines(self) -> None:
        """Do not imply that aggregate token usage is attributable to tool counters."""

        summary = posting_formatting.summarize_result(
            total=0,
            inline_count=0,
            fallback_count=0,
            warning_count=0,
            outcome_status="success",
            outcome_message="No comments generated. Looks good to me.",
            tool_calls_summary=posting_formatting.format_tool_calls_summary(
                {"total": 2, "by_tool": {"file_read": 2}}
            ),
            token_usage_summary="- token usage: 48 total (input: 40, output: 8)",
            emoji=True,
        )

        self.assertIn("- all OCR tool calls: 2 total (`file_read`: 2)", summary)
        self.assertIn("- token usage: 48 total (input: 40, output: 8)", summary)
        self.assertNotIn("per-tool", summary)

    def test_root_total_is_not_treated_as_token_usage(self) -> None:
        self.assertEqual(posting_formatting.format_token_usage_summary({"total": 17}), "")
        self.assertIn(
            "token usage: 30 total",
            posting_formatting.format_token_usage_summary(
                {"usage": {"prompt": 10, "completion": 20}}
            ),
        )

    def test_cached_usage_requires_validated_input_parent(self) -> None:
        summary = posting_formatting.format_token_usage_summary({"usage": {"cached_tokens": 40}})

        self.assertEqual(summary, "")
        self.assertIn(
            "cached: 40",
            posting_formatting.format_token_usage_summary(
                {"usage": {"input_tokens": 50, "output_tokens": 5, "cached_tokens": 40}}
            ),
        )
        self.assertIn(
            "token usage: 55 total",
            posting_formatting.format_token_usage_summary({"usage": {"total": 55}}),
        )

    def test_token_usage_summary_reads_root_explicit_fields(self) -> None:
        summary = posting_formatting.format_token_usage_summary(
            {"total_tokens": 10, "prompt_tokens": 7, "completion_tokens": 3}
        )

        self.assertIn("token usage: 10 total", summary)
        self.assertIn("input: 7", summary)
        self.assertIn("output: 3", summary)

    def test_token_usage_summary_renders_available_bucket_without_inventing_total(self) -> None:
        self.assertEqual(
            posting_formatting.format_token_usage_summary({"usage": {"input_tokens": 7}}),
            "- token usage: input: 7",
        )

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
        self.assertIn("🔎 **Review complete — 3 findings published**", summary)

    def test_publication_filtering_signal_is_visible_and_machine_readable(self) -> None:
        publication = {
            "state": "publication-filtered",
            "reason_counts": {
                "forbidden": 1,
                "invalid_text": 0,
                "laundering": 1,
                "limit": 0,
                "pii": 0,
                "secret": 0,
            },
            "retained": {"comments": 2, "warnings": 1},
            "omitted": {"comments": 1, "warnings": 0, "fields": 1},
            "original": {
                "outcome": "clean",
                "selected": 3,
                "completed": 3,
                "reused": 0,
                "failed": 0,
                "waived": 0,
            },
        }
        signal = posting_formatting.publication_dlp_signal(publication, carried_forward_comments=1)
        details = posting_formatting.format_publication_dlp_details(signal)
        summary = posting_formatting.summarize_result(
            total=2,
            inline_count=2,
            fallback_count=0,
            warning_count=0,
            outcome_status="partial",
            publication_dlp_details=details,
            emoji=False,
        )

        self.assertIn("<summary>Publication filtering signal</summary>", summary)
        self.assertIn("Published safe subset: 2 finding(s)", summary)
        marker = summary.split("<!-- ocr-toolkit-signal ", 1)[1].split(" -->", 1)[0]
        self.assertEqual(json.loads(marker), signal)
        self.assertEqual(signal["schema_version"], "ocr.publication-dlp-signal/v2")

        private_only = {
            "state": "private-sanitized",
            "reason_counts": {
                "forbidden": 0,
                "invalid_text": 0,
                "laundering": 0,
                "limit": 0,
                "pii": 2,
                "secret": 0,
            },
            "sanitized_fields": 2,
        }
        private_details = posting_formatting.format_publication_dlp_details(
            posting_formatting.publication_dlp_signal(private_only)
        )
        self.assertIn("Private result sanitization signal", private_details)
        self.assertIn("approval-relevant review is unchanged", private_details)

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

        self.assertIn("no supported files changed", summary)
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

        self.assertIn("✅ **Review complete — no findings**", summary)
        self.assertNotIn("\nNo findings", summary)
        self.assertNotIn("tool calls", summary)

    def test_summary_uses_one_canonical_line_for_every_outcome_state(self) -> None:
        """Keep review health and finding publication inseparable at a glance."""

        cases = (
            (
                "clean findings",
                "success",
                2,
                0,
                0,
                0,
                "🔎 **Review complete — 2 findings published**",
            ),
            (
                "warnings",
                "completed_with_warnings",
                1,
                0,
                0,
                1,
                "⚠️ **Review complete with warnings — 1 finding published**",
            ),
            (
                "partial",
                "partial",
                0,
                0,
                0,
                0,
                "⚠️ **Review incomplete — no findings in reviewed files**",
            ),
            (
                "budget",
                "budget_exceeded",
                0,
                0,
                0,
                1,
                "⚠️ **Review stopped at token budget — no findings in reviewed files**",
            ),
            (
                "skipped",
                "skipped",
                0,
                0,
                0,
                0,
                "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} "
                "**Review skipped — no supported files changed**",
            ),
            (
                "failed",
                "failed",
                0,
                0,
                0,
                0,
                "❌ **Review failed — no reliable review result was produced**",
            ),
            (
                "suppressed",
                "success",
                0,
                0,
                2,
                0,
                "🔎 **Review complete — no new findings published; 2 findings matched prior reviewer decisions**",
            ),
            (
                "all omitted",
                "success",
                0,
                3,
                0,
                0,
                "🔎 **Review complete — no findings published; 3 findings omitted by posting limit**",
            ),
        )
        for label, status, total, omitted, suppressed, warnings, expected in cases:
            with self.subTest(label=label):
                summary = posting_formatting.summarize_result(
                    total=total,
                    inline_count=0,
                    fallback_count=0,
                    warning_count=warnings,
                    omitted_count=omitted,
                    suppressed_count=suppressed,
                    outcome_status=status,
                    emoji=True,
                )
                visible = summary.split("<details>", 1)[0]
                self.assertIn(expected, visible)
                self.assertEqual(sum("Review " in line for line in visible.splitlines()), 1)

    def test_partial_summary_appends_known_unreviewed_files_once(self) -> None:
        diagnostics = result.CoverageDiagnostics(
            (result.CoverageDiagnostic("src/a.py", "review timed out"),),
            0,
            0,
            1,
            1,
        )

        summary = posting_formatting.summarize_result(
            total=1,
            inline_count=1,
            fallback_count=0,
            warning_count=0,
            outcome_status="partial",
            coverage_diagnostics=diagnostics,
            emoji=False,
        )

        self.assertIn(
            "**Review incomplete — 1 finding published from reviewed files; 1 file not reviewed**",
            summary,
        )
        self.assertEqual(summary.count("1 file not reviewed"), 1)

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

        self.assertIn(
            "⚠️ **Review stopped at token budget — 1 finding published from reviewed files**",
            summary,
        )
        self.assertNotIn("Partial result", summary)
        self.assertIn("Review scope:", summary)
        self.assertIn("partial review", summary)
        self.assertIn("321 total", summary)

    def test_mcp_usage_summary_reports_only_servers_actually_called(self) -> None:
        summary = posting_formatting.format_mcp_usage_summary(
            {
                "schema_version": 5,
                "mcp": {
                    "usage": {
                        "ocr_toolkit_evidence": 2,
                        "documentation": 1,
                    }
                },
                "evidence": {"actions": {"state": "unavailable"}},
            }
        )

        self.assertEqual(
            summary,
            "- verified MCP calls: 2 server(s) (`documentation`: 1, `ocr_toolkit_evidence`: 2)\n"
            "- built-in evidence actions: unavailable",
        )
        self.assertNotIn("file_read", summary)

    def test_mcp_usage_summary_reads_receipt_v5_inventory(self) -> None:
        summary = posting_formatting.format_mcp_usage_summary(
            {
                "schema_version": 5,
                "mcp": {
                    "capabilities": [],
                    "usage": {"ocr_toolkit_evidence": 3},
                },
                "evidence": {"actions": {"state": "unavailable"}},
            }
        )

        self.assertEqual(
            summary,
            "- verified MCP calls: 1 server(s) (`ocr_toolkit_evidence`: 3)\n"
            "- built-in evidence actions: unavailable",
        )

    def test_mcp_usage_summary_renders_verified_action_breakdown(self) -> None:
        summary = posting_formatting.format_mcp_usage_summary(
            {
                "schema_version": 5,
                "mcp": {"usage": {"ocr_toolkit_evidence": 4}},
                "evidence": {
                    "calls": 4,
                    "actions": {
                        "state": "verified",
                        "summary": 1,
                        "list": 2,
                        "get": 1,
                    },
                },
            }
        )

        self.assertEqual(
            summary,
            "- verified MCP calls: 1 server(s) (`ocr_toolkit_evidence`: 4)\n"
            "- built-in evidence actions: summary: 1, list: 2, get: 1",
        )

    def test_mcp_usage_summary_omits_hostile_or_unreconciled_action_breakdown(self) -> None:
        for actions in (
            {"state": "verified", "summary": "1\n/approve", "list": 2, "get": 1},
            {"state": "verified", "summary": True, "list": 2, "get": 1},
            {"state": "verified", "summary": 1, "list": 2, "get": 2},
            {"state": "verified", "summary": 1, "list": 2, "get": 1, "extra": 0},
        ):
            with self.subTest(actions=actions):
                summary = posting_formatting.format_mcp_usage_summary(
                    {
                        "schema_version": 5,
                        "mcp": {"usage": {"ocr_toolkit_evidence": 4}},
                        "evidence": {"calls": 4, "actions": actions},
                    }
                )

                self.assertEqual(
                    summary,
                    "- verified MCP calls: 1 server(s) (`ocr_toolkit_evidence`: 4)",
                )
                self.assertNotIn("/approve", summary)

    def test_mcp_usage_summary_reconciles_actions_after_context_calls(self) -> None:
        summary = posting_formatting.format_mcp_usage_summary(
            {
                "schema_version": 5,
                "context": {"tool_usage": {"context_get": 1, "context_list": 2}},
                "mcp": {"usage": {"ocr_toolkit_evidence": 7}},
                "evidence": {
                    "calls": 4,
                    "actions": {
                        "state": "verified",
                        "summary": 1,
                        "list": 2,
                        "get": 1,
                    },
                },
            }
        )

        self.assertEqual(
            summary,
            "- verified MCP calls: 1 server(s) (`ocr_toolkit_evidence`: 7)\n"
            "- built-in evidence actions: summary: 1, list: 2, get: 1",
        )

    def test_mcp_usage_summary_rejects_malformed_usage_before_rendering(self) -> None:
        for usage in (
            {"ocr_toolkit_evidence": 1, 7: 1},
            {"ocr_toolkit_evidence\n/approve": 1},
            {"ocr_toolkit_evidence": True},
            {"ocr_toolkit_evidence": 0},
        ):
            with self.subTest(usage=usage):
                self.assertEqual(
                    posting_formatting.format_mcp_usage_summary(
                        {
                            "schema_version": 5,
                            "mcp": {"usage": usage},
                            "evidence": {"actions": {"state": "unavailable"}},
                        }
                    ),
                    "",
                )

    def test_mcp_usage_summary_rejects_pre_v5_receipt(self) -> None:
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

        self.assertIn("⚠️ **Review complete with warnings — no findings**", warning)
        self.assertIn("⚠️ **Review incomplete — no findings in reviewed files**", error)
        self.assertNotIn("\nNo findings in reviewed files", error)
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

    def test_shields_badges_project_only_normalized_finding_metadata(self) -> None:
        cases = (
            (
                {"category": "security", "severity": "CRITICAL"},
                "![security · critical](https://img.shields.io/badge/security-critical-darkred)",
            ),
            (
                {"category": "bug", "severity": "high"},
                "![bug · high](https://img.shields.io/badge/bug-high-red)",
            ),
            (
                {"category": "performance", "severity": "medium"},
                "![performance · medium](https://img.shields.io/badge/performance-medium-orange)",
            ),
            (
                {"category": "style", "severity": "low"},
                "![style · low](https://img.shields.io/badge/style-low-green)",
            ),
            (
                {"category": "documentation"},
                "![documentation](https://img.shields.io/badge/category-documentation-blue)",
            ),
            (
                {"priority": "high"},
                "![high](https://img.shields.io/badge/severity-high-red)",
            ),
        )
        for finding, expected in cases:
            with self.subTest(finding=finding):
                self.assertEqual(
                    posting_formatting.format_finding_tags(
                        finding,
                        badge_mode="shields",
                    ),
                    expected,
                )

        self.assertEqual(
            set(posting_formatting.SHIELDS_SEVERITY_COLORS),
            posting_formatting.OCR_FINDING_SEVERITIES,
        )

    def test_shields_badges_drop_untrusted_metadata_and_keep_text_fallback(self) -> None:
        hostile = {
            "category": "bug](https://attacker.invalid/x)",
            "severity": "high\n/merge",
            "content": "Finding body",
        }

        self.assertEqual(
            posting_formatting.format_finding_tags(hostile, badge_mode="shields"),
            "",
        )
        self.assertEqual(
            posting_formatting.format_finding_tags(hostile, badge_mode="text"),
            "",
        )
        rendered = posting_formatting.format_inline_comment(hostile, badge_mode="shields")
        self.assertNotIn("attacker.invalid", rendered)
        self.assertNotIn("/merge", rendered)
        self.assertEqual(rendered, "Finding body")

    def test_badge_mode_changes_finding_presentation_not_summary_or_suggestion(self) -> None:
        finding = {
            "content": "Use the guarded value.",
            "category": "bug",
            "severity": "high",
        }
        decision = SuggestionDecision(
            SuggestionState.ACTIONABLE,
            replacement="new_value",
            range_suffix="-0+1",
        )

        with patched_env(OCR_POST_BADGES="shields"):
            settings.post_badges.cache_clear()
            inline = posting_formatting.format_inline_comment(
                finding,
                suggestion_decision=decision,
            )
            fallback = posting_formatting.format_fallback_comment(finding)
            summary = posting_formatting.summarize_result(
                total=1,
                inline_count=1,
                fallback_count=0,
                warning_count=0,
                emoji=False,
            )

        self.assertTrue(inline.startswith("![bug · high](https://img.shields.io/badge/"))
        self.assertIn("```suggestion:-0+1\nnew_value\n```", inline)
        self.assertIn("![bug · high](https://img.shields.io/badge/", fallback)
        self.assertNotIn("img.shields.io", summary)
        self.assertIn("**Review complete — 1 finding published**", summary)

    def test_security_signal_is_promoted_when_present(self) -> None:
        guide = posting_formatting.format_reviewer_guide(
            [{"path": "x", "line": 1, "content": "Possible token leak"}], 0
        )

        self.assertIn("## Security review focus", guide)
        self.assertIn("**Security signal:**", guide)

    def test_reviewer_guide_ranks_only_its_published_copy(self) -> None:
        comments = [
            {
                "severity": "medium",
                "category": "test",
                "path": "z.py",
                "line": 3,
                "content": "medium test",
            },
            {
                "severity": "high",
                "category": "bug",
                "path": "b.py",
                "line": 2,
                "content": "high bug",
            },
            {
                "severity": "high",
                "category": "security",
                "path": "a.py",
                "line": 1,
                "content": "high security",
            },
            {
                "severity": "low",
                "category": "maintainability",
                "path": "c.py",
                "line": 4,
                "content": "low maintenance",
            },
        ]
        original = [dict(comment) for comment in comments]

        guide = posting_formatting.format_reviewer_guide(comments, 0)

        self.assertEqual(comments, original)
        self.assertLess(guide.index("high security"), guide.index("high bug"))
        self.assertLess(guide.index("high bug"), guide.index("medium test"))
        self.assertLess(guide.index("medium test"), guide.index("low maintenance"))

    def test_reviewer_guide_sorts_malformed_metadata_after_known_location(self) -> None:
        comments = [
            {
                "severity": "high",
                "category": "security",
                "path": "../bad",
                "line": -1,
                "content": "malformed",
            },
            {
                "severity": "high",
                "category": "security",
                "path": "A.py",
                "start_line": 4,
                "content": "known first",
                "_ocr_fingerprint": "b" * 32,
            },
            {
                "severity": "HIGH",
                "category": "SECURITY",
                "path": "a.py",
                "line": 4,
                "content": "lowercase path",
                "_ocr_fingerprint": "a" * 32,
            },
        ]

        guide = posting_formatting.format_reviewer_guide(comments, 0)

        self.assertLess(guide.index("known first"), guide.index("lowercase path"))
        self.assertLess(guide.index("lowercase path"), guide.index("malformed"))

    def test_reviewer_guide_uses_occurrence_fingerprint_as_stable_tiebreaker(self) -> None:
        comments = [
            {
                "severity": "high",
                "category": "bug",
                "path": "same.py",
                "line": 7,
                "content": "fingerprint b",
                "_ocr_fingerprint": "b" * 32,
            },
            {
                "severity": "high",
                "category": "bug",
                "path": "same.py",
                "line": 7,
                "content": "fingerprint a",
                "_ocr_fingerprint": "a" * 32,
            },
        ]

        guide = posting_formatting.format_reviewer_guide(comments, 0)

        self.assertLess(guide.index("fingerprint a"), guide.index("fingerprint b"))

    def test_reviewer_guide_applies_cap_after_stable_ranking(self) -> None:
        comments = [
            {
                "severity": "low",
                "category": "style",
                "path": f"z{index}.py",
                "line": 1,
                "content": f"low-{index}",
            }
            for index in range(posting_formatting.MAX_REVIEWER_GUIDE_COMMENTS)
        ]
        comments.append(
            {
                "severity": "critical",
                "category": "security",
                "path": "critical.py",
                "line": 1,
                "content": "must appear",
            }
        )

        first = posting_formatting.format_reviewer_guide(comments, 0)
        second = posting_formatting.format_reviewer_guide(comments, 0)

        self.assertEqual(first, second)
        self.assertIn("must appear", first)
        self.assertNotIn(f"low-{posting_formatting.MAX_REVIEWER_GUIDE_COMMENTS - 1}", first)
        self.assertIn("... and 1 more published finding(s).", first)

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


class GitLabReconciliationTests(unittest.TestCase):
    WRITE_ID = "c" * 32

    @staticmethod
    def draft(
        note_id: object = 17, author_id: object = 7, body: str | None = None
    ) -> dict[str, Any]:
        return {
            "id": note_id,
            "author_id": author_id,
            "note": body
            or (
                f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                f"{markers.build_write_marker(GitLabReconciliationTests.WRITE_ID)}\nbody"
            ),
        }

    @staticmethod
    def discussion(
        discussion_id: object = "discussion-17",
        note_id: object = 19,
        author_id: object = 7,
        body: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": discussion_id,
            "notes": [
                {
                    "id": note_id,
                    "author": {"id": author_id},
                    "body": body
                    or (
                        f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                        f"{markers.build_write_marker(GitLabReconciliationTests.WRITE_ID)}\nbody"
                    ),
                }
            ],
        }

    def ambiguous(self, kind: str) -> gitlab.GitLabWriteResult:
        return gitlab.GitLabWriteResult(
            "ambiguous_create", write_id=self.WRITE_ID, create_kind=kind
        )

    def test_draft_reconciliation_requires_exactly_one_author_bound_match(self) -> None:
        cases = (
            ([], False),
            ([self.draft()], True),
            ([self.draft(), self.draft(18)], False),
            ([self.draft(author_id=8)], False),
            ([self.draft(note_id="17")], False),
            (
                [self.draft(body=f"{markers.build_write_marker(self.WRITE_ID)}\nbody")],
                False,
            ),
            (
                [
                    self.draft(
                        body=(
                            f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                            f"{markers.build_write_marker(self.WRITE_ID)}\n"
                            "quoted <!-- open-code-review-write text"
                        )
                    )
                ],
                True,
            ),
        )
        for items, recovered in cases:
            with (
                self.subTest(items=items),
                redirect_stderr(io.StringIO()),
                patched_attr(
                    gitlab, "api_get_paginated", lambda *_args, value=items, **_kwargs: value
                ),
            ):
                result = reconciliation.reconcile_ambiguous_inline_create(
                    gitlab_config(), self.ambiguous("draft")
                )
            self.assertEqual(result.posted, recovered)
            self.assertEqual(result.draft_note_id, 17 if recovered else None)

    def test_direct_reconciliation_requires_owned_exact_author_bound_match(self) -> None:
        no_owner = self.discussion(body=f"{markers.build_write_marker(self.WRITE_ID)}\nbody")
        cases = (
            ([], False),
            ([self.discussion()], True),
            ([self.discussion(), self.discussion("discussion-18", 20)], False),
            ([self.discussion(author_id=8)], False),
            ([self.discussion(note_id="19")], False),
            ([no_owner], False),
            (
                [
                    self.discussion(
                        body=(
                            f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                            f"{markers.build_write_marker(self.WRITE_ID)}\n"
                            "quoted <!-- open-code-review-write text"
                        )
                    )
                ],
                True,
            ),
        )
        for items, recovered in cases:
            with (
                self.subTest(items=items),
                redirect_stderr(io.StringIO()),
                patched_attr(
                    gitlab, "api_get_paginated", lambda *_args, value=items, **_kwargs: value
                ),
            ):
                result = reconciliation.reconcile_ambiguous_inline_create(
                    gitlab_config(), self.ambiguous("discussion")
                )
            self.assertEqual(result.posted, recovered)
            self.assertEqual(
                (result.discussion_id, result.discussion_note_id),
                ("discussion-17", 19) if recovered else (None, None),
            )

    def test_reconciliation_ignores_non_ambiguous_results_and_missing_user(self) -> None:
        calls: list[str] = []
        with patched_attr(
            gitlab,
            "api_get_paginated",
            lambda *_args, **_kwargs: calls.append("read") or [],
        ):
            posted = reconciliation.reconcile_ambiguous_inline_create(
                gitlab_config(), gitlab.GitLabWriteResult("posted")
            )
            missing_user = reconciliation.reconcile_ambiguous_inline_create(
                gitlab_config(None), self.ambiguous("draft")
            )

        self.assertTrue(posted.posted)
        self.assertTrue(missing_user.ambiguous_create)
        self.assertEqual(calls, [])

    def test_unavailable_or_incomplete_readback_stays_ambiguous_without_create(self) -> None:
        calls: list[str] = []
        with patched_attr(
            gitlab,
            "api_get_paginated",
            lambda *_args, **_kwargs: calls.append("read") or None,
        ):
            result = reconciliation.reconcile_ambiguous_inline_create(
                gitlab_config(), self.ambiguous("draft")
            )

        self.assertTrue(result.ambiguous_create)
        self.assertEqual(calls, ["read"])

    def test_post_review_recovers_draft_once_without_retry_and_records_transaction(self) -> None:
        creates: list[str] = []
        reads: list[str] = []
        transaction = PostingTransaction()
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}

        def create(*_args: Any, write_id: str, **_kwargs: Any) -> gitlab.GitLabWriteResult:
            creates.append(write_id)
            return gitlab.GitLabWriteResult(
                "ambiguous_create", write_id=write_id, create_kind="draft"
            )

        def read(_config: Any, endpoint: str, **_kwargs: Any) -> list[Any]:
            reads.append(endpoint)
            body = (
                f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                f"{markers.build_write_marker(creates[0])}\nbody"
            )
            return [self.draft(body=body)]

        settings.post_mode.cache_clear()
        try:
            with (
                patched_env(OCR_POST_MODE="draft"),
                patched_attr(gitlab, "post_inline_draft_note_detailed", create),
                patched_attr(gitlab, "api_get_paginated", read),
            ):
                result = gitlab.post_review_discussion(
                    gitlab_config(), "file.py", 7, "body", refs, transaction
                )
        finally:
            settings.post_mode.cache_clear()

        self.assertTrue(result.posted)
        self.assertEqual(len(creates), 1)
        self.assertEqual(reads, ["/draft_notes"])
        self.assertEqual(transaction.draft_note_ids, (17,))

    def test_post_review_recovers_direct_identity_for_explicit_rollback(self) -> None:
        creates: list[str] = []
        transaction = PostingTransaction()
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}

        def create(*_args: Any, write_id: str, **_kwargs: Any) -> gitlab.GitLabWriteResult:
            creates.append(write_id)
            return gitlab.GitLabWriteResult(
                "ambiguous_create", write_id=write_id, create_kind="discussion"
            )

        def read(*_args: Any, **_kwargs: Any) -> list[Any]:
            body = (
                f"{markers.build_marker('a' * FINGERPRINT_LEN)}\n"
                f"{markers.build_write_marker(creates[0])}\nbody"
            )
            return [self.discussion(body=body)]

        settings.post_mode.cache_clear()
        try:
            with (
                patched_env(OCR_POST_MODE="direct"),
                patched_attr(gitlab, "post_inline_note_detailed", create),
                patched_attr(gitlab, "api_get_paginated", read),
            ):
                result = gitlab.post_review_discussion(
                    gitlab_config(), "file.py", 7, "body", refs, transaction
                )
        finally:
            settings.post_mode.cache_clear()

        self.assertTrue(result.posted)
        self.assertEqual(len(creates), 1)
        self.assertEqual(transaction.discussion_note_refs, (("discussion-17", 19),))

    def test_reconciliation_crosses_real_paginated_http_read_boundary(self) -> None:
        requests: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                requests.append(self.path)
                payload = json.dumps(
                    [GitLabReconciliationTests.draft()]
                    if "page=1" in self.path and "per_page=100" in self.path
                    else []
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        root = f"http://127.0.0.1:{server.server_port}"
        config = gitlab_config()
        try:
            with patched_attr(
                type(config),
                "api_base",
                property(lambda _self: f"{root}/api/v4/projects/7/merge_requests/9"),
            ):
                result = reconciliation.reconcile_ambiguous_inline_create(
                    config, self.ambiguous("draft")
                )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertTrue(result.posted)
        self.assertEqual(result.draft_note_id, 17)
        self.assertEqual(len(requests), 1)


class PostingTransactionTests(unittest.TestCase):
    def test_drafts_publish_exactly_once_and_duplicate_identity_fails_closed(self) -> None:
        transaction = PostingTransaction()
        published: list[int] = []
        self.assertTrue(transaction.record_draft(17))
        self.assertFalse(transaction.record_draft(17))
        self.assertFalse(transaction.record_draft(True))
        settings.post_mode.cache_clear()
        try:
            with (
                patched_env(OCR_POST_MODE="draft"),
                patched_attr(
                    gitlab,
                    "publish_draft_note",
                    lambda _config, note_id: published.append(note_id) or True,
                ),
            ):
                self.assertTrue(gitlab.publish_created_draft_notes(gitlab_config(), transaction))
                self.assertTrue(gitlab.publish_created_draft_notes(gitlab_config(), transaction))
        finally:
            settings.post_mode.cache_clear()
        self.assertEqual(published, [17])
        self.assertTrue(transaction.record_plain(18))
        self.assertFalse(transaction.record_plain(18))
        self.assertTrue(transaction.record_discussion("discussion-19", 19))
        self.assertFalse(transaction.record_discussion("discussion-19", 19))
        self.assertEqual(transaction.plain_note_ids, (18,))
        self.assertEqual(transaction.discussion_note_refs, (("discussion-19", 19),))

    def test_partial_draft_publication_stops_at_exact_failed_identity(self) -> None:
        """Stop draft publication at the exact identity that failed to publish."""

        transaction = PostingTransaction()
        self.assertTrue(transaction.record_draft(17))
        self.assertTrue(transaction.record_draft(18))
        self.assertTrue(transaction.record_draft(19))
        published: list[int] = []

        def publish(_config: Any, note_id: int) -> bool:
            published.append(note_id)
            return note_id != 18

        settings.post_mode.cache_clear()
        try:
            with (
                patched_env(OCR_POST_MODE="draft"),
                patched_attr(gitlab, "publish_draft_note", publish),
                redirect_stderr(io.StringIO()),
            ):
                self.assertFalse(gitlab.publish_created_draft_notes(gitlab_config(), transaction))
        finally:
            settings.post_mode.cache_clear()

        self.assertEqual(published, [17, 18])
        self.assertEqual(transaction.draft_note_ids, (17, 18, 19))
        self.assertEqual(transaction.consume_drafts_for_publication(), ())

    def test_regular_review_note_records_only_exact_mode_specific_identity(self) -> None:
        """Record a successful review note in only its active publication mode."""

        settings.post_mode.cache_clear()
        try:
            draft_transaction = PostingTransaction()
            with (
                patched_env(OCR_POST_MODE="draft"),
                patched_attr(gitlab, "post_draft_note", lambda *_args, **_kwargs: {"id": 17}),
            ):
                draft = gitlab.post_review_note(gitlab_config(), "draft body", draft_transaction)
            self.assertEqual(draft, {"id": 17})
            self.assertEqual(draft_transaction.draft_note_ids, (17,))

            settings.post_mode.cache_clear()
            direct_transaction = PostingTransaction()
            with (
                patched_env(OCR_POST_MODE="direct"),
                patched_attr(gitlab, "post_note", lambda *_args, **_kwargs: {"id": 18}),
            ):
                direct = gitlab.post_review_note(gitlab_config(), "direct body", direct_transaction)
            self.assertEqual(direct, {"id": 18})
            self.assertEqual(direct_transaction.plain_note_ids, (18,))
        finally:
            settings.post_mode.cache_clear()

    def test_regular_review_note_rejects_missing_malformed_and_duplicate_identity(self) -> None:
        """Reject writes without one new exact provider-owned note identity."""

        settings.post_mode.cache_clear()
        try:
            for mode, response in (
                ("draft", None),
                ("draft", {"id": "17"}),
                ("direct", None),
                ("direct", {"id": True}),
            ):
                transaction = PostingTransaction()
                target = "post_draft_note" if mode == "draft" else "post_note"
                with (
                    self.subTest(mode=mode, response=response),
                    patched_env(OCR_POST_MODE=mode),
                    patched_attr(gitlab, target, lambda *_args, value=response, **_kwargs: value),
                    redirect_stderr(io.StringIO()),
                ):
                    settings.post_mode.cache_clear()
                    self.assertIsNone(gitlab.post_review_note(gitlab_config(), "body", transaction))

            settings.post_mode.cache_clear()
            transaction = PostingTransaction()
            self.assertTrue(transaction.record_plain(18))
            with (
                patched_env(OCR_POST_MODE="direct"),
                patched_attr(gitlab, "post_note", lambda *_args, **_kwargs: {"id": 18}),
            ):
                self.assertIsNone(gitlab.post_review_note(gitlab_config(), "body", transaction))
        finally:
            settings.post_mode.cache_clear()

    def test_bounded_review_note_truncates_multibyte_body_before_posting(self) -> None:
        """Apply the provider byte budget before posting a multibyte review note."""

        bodies: list[str] = []

        def capture(
            _config: Any,
            body: str,
            _transaction: PostingTransaction,
            fingerprint: str | None = None,
        ) -> dict[str, int]:
            self.assertEqual(fingerprint, "a" * FINGERPRINT_LEN)
            bodies.append(body)
            return {"id": 1}

        with patched_attr(gitlab, "post_review_note", capture):
            response = gitlab.post_review_note_bounded(
                gitlab_config(),
                "Review summary",
                "ж" * (settings.MAX_NOTE_CHARS + 100),
                PostingTransaction(),
                fingerprint="a" * FINGERPRINT_LEN,
            )

        self.assertEqual(response, {"id": 1})
        self.assertEqual(len(bodies), 1)
        self.assertLessEqual(
            len(bodies[0].encode("utf-8")),
            payloads.note_body_budget(settings.MAX_NOTE_CHARS, "a" * FINGERPRINT_LEN),
        )


class GitLabSnapshotTests(unittest.TestCase):
    def test_inline_review_mints_one_write_identity_before_each_create(self) -> None:
        minted: list[str] = []
        captured: list[tuple[str, str]] = []

        def token_hex(size: int) -> str:
            self.assertEqual(size, 16)
            value = f"{len(minted) + 1:032x}"
            minted.append(value)
            return value

        def create_draft(*_args: Any, write_id: str, **_kwargs: Any) -> gitlab.GitLabWriteResult:
            captured.append(("draft", write_id))
            return gitlab.GitLabWriteResult("posted", write_id=write_id, draft_note_id=17)

        def create_direct(*_args: Any, write_id: str, **_kwargs: Any) -> gitlab.GitLabWriteResult:
            captured.append(("direct", write_id))
            return gitlab.GitLabWriteResult(
                "posted",
                write_id=write_id,
                discussion_id="discussion-19",
                discussion_note_id=19,
            )

        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}
        transaction = PostingTransaction()
        settings.post_mode.cache_clear()
        try:
            with (
                patched_attr(gitlab.secrets, "token_hex", token_hex),
                patched_attr(gitlab, "post_inline_draft_note_detailed", create_draft),
                patched_env(OCR_POST_MODE="draft"),
            ):
                draft = gitlab.post_review_discussion(
                    gitlab_config(), "file.py", 7, "body", refs, transaction
                )
            settings.post_mode.cache_clear()
            with (
                patched_attr(gitlab.secrets, "token_hex", token_hex),
                patched_attr(gitlab, "post_inline_note_detailed", create_direct),
                patched_env(OCR_POST_MODE="direct"),
            ):
                direct = gitlab.post_review_discussion(
                    gitlab_config(), "file.py", 7, "body", refs, transaction
                )
        finally:
            settings.post_mode.cache_clear()

        self.assertEqual([draft.status, direct.status], ["posted", "posted"])
        self.assertEqual(transaction.draft_note_ids, (17,))
        self.assertEqual(captured, [("draft", minted[0]), ("direct", minted[1])])
        self.assertEqual(len(set(minted)), 2)

    def test_endpoint_create_identity_parsers_reject_type_confused_ids(self) -> None:
        for draft in ({"id": 0}, {"id": True}, {"id": "17"}, {"id": 17.0}):
            with self.subTest(draft=draft), redirect_stderr(io.StringIO()):
                self.assertIsNone(gitlab.created_draft_note(draft, "synthetic draft"))

        for discussion in (
            {"id": "discussion-1", "notes": [{"id": 0}]},
            {"id": "discussion-1", "notes": [{"id": "19"}]},
            {"id": "../unsafe", "notes": [{"id": 19}]},
            {"id": "discussion-1", "notes": [{"id": 19}, {"id": 20}]},
        ):
            with self.subTest(discussion=discussion), redirect_stderr(io.StringIO()):
                self.assertIsNone(gitlab.created_discussion_note(discussion))

    def test_diff_refs_bind_only_the_current_ci_head_and_complete_version(self) -> None:
        """Accept diff refs only when the complete version binds to the CI head."""

        versions = [
            "invalid",
            {
                "head_commit_sha": "b" * 40,
                "base_commit_sha": "base",
                "start_commit_sha": "start",
            },
        ]
        with (
            patched_env(
                CI_MERGE_REQUEST_SOURCE_BRANCH_SHA="b" * 40,
                CI_COMMIT_SHA="c" * 40,
            ),
            patched_attr(gitlab, "api_get_paginated", lambda *_args, **_kwargs: versions),
        ):
            self.assertEqual(
                gitlab.get_diff_refs(gitlab_config()),
                {"base_sha": "base", "start_sha": "start", "head_sha": "b" * 40},
            )

        for values, response in (
            (
                {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "", "CI_COMMIT_SHA": ""},
                versions,
            ),
            (
                {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "d" * 40, "CI_COMMIT_SHA": ""},
                versions,
            ),
            (
                {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "b" * 40, "CI_COMMIT_SHA": ""},
                [{"head_commit_sha": "b" * 40, "base_commit_sha": ""}],
            ),
            (
                {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "b" * 40, "CI_COMMIT_SHA": ""},
                [],
            ),
        ):
            with (
                self.subTest(values=values, response=response),
                patched_env(**values),
                patched_attr(
                    gitlab,
                    "api_get_paginated",
                    lambda *_args, value=response, **_kwargs: value,
                ),
                redirect_stderr(io.StringIO()),
            ):
                self.assertIsNone(gitlab.get_diff_refs(gitlab_config()))

    def test_snapshot_cleanup_uses_only_collected_typed_identities(self) -> None:
        """Delete only typed identities from a safely collected snapshot."""

        refs = snapshot.BotCommentRefs(
            plain_note_ids=[11, 12],
            discussion_note_refs=[("discussion-13", 13)],
            draft_note_ids=[14],
            summary_plain_note_ids=[21],
            summary_draft_note_ids=[22],
            setup_plain_note_ids=[31],
            setup_draft_note_ids=[32],
        )
        deleted: list[tuple[str, object]] = []

        with (
            patched_attr(
                snapshot,
                "delete_plain_note",
                lambda _config, note_id: deleted.append(("plain", note_id)) or note_id != 12,
            ),
            patched_attr(
                snapshot,
                "delete_discussion_note",
                lambda _config, discussion_id, note_id: (
                    deleted.append(("discussion", (discussion_id, note_id))) or True
                ),
            ),
            patched_attr(
                snapshot,
                "delete_draft_note",
                lambda _config, note_id: deleted.append(("draft", note_id)) or True,
            ),
            redirect_stdout(io.StringIO()),
        ):
            snapshot.delete_collected_bot_comments(gitlab_config(), refs)
            snapshot.delete_previous_summary_notes(gitlab_config(), refs)
            snapshot.delete_previous_setup_notes(gitlab_config(), refs)

        self.assertEqual(
            deleted,
            [
                ("plain", 11),
                ("plain", 12),
                ("discussion", ("discussion-13", 13)),
                ("draft", 14),
                ("plain", 21),
                ("draft", 22),
                ("plain", 31),
                ("draft", 32),
            ],
        )

        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            patched_attr(
                snapshot,
                "delete_collected_bot_comments",
                lambda *_args: self.fail("unsafe snapshot reached deletion"),
            ),
        ):
            snapshot.delete_previous_bot_comments_if_collected(gitlab_config(), None)
        self.assertIn("not collected safely", stderr.getvalue())

    def test_create_transport_serializes_write_marker_and_validates_endpoint_identity(self) -> None:
        requests: list[tuple[str, dict[str, Any]]] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                request_body = json.loads(self.rfile.read(length))
                requests.append((self.path, request_body))
                write_id = markers.write_id_from_body(
                    str(request_body.get("note") or request_body.get("body") or "")
                )
                if self.path.endswith("/draft_notes"):
                    response = {"id": 17}
                else:
                    response = {"id": "discussion-17", "notes": [{"id": 19}]}
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                payload = json.dumps(response).encode()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                self.server.write_ids.append(write_id)  # type: ignore[attr-defined]

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.write_ids = []  # type: ignore[attr-defined]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        root = f"http://127.0.0.1:{server.server_port}"
        refs = {"base_sha": "a", "start_sha": "b", "head_sha": "c"}
        config = gitlab_config()
        try:
            with patched_attr(
                type(config),
                "api_base",
                property(lambda _self: f"{root}/api/v4/projects/7/merge_requests/9"),
            ):
                draft = gitlab.post_inline_draft_note_detailed(
                    config, "file.py", 7, "draft", refs, write_id="1" * 32
                )
                direct = gitlab.post_inline_note_detailed(
                    config, "file.py", 7, "direct", refs, write_id="2" * 32
                )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(draft.status, "posted")
        self.assertEqual(draft.draft_note_id, 17)
        self.assertEqual(direct.status, "posted")
        self.assertEqual((direct.discussion_id, direct.discussion_note_id), ("discussion-17", 19))
        self.assertEqual(server.write_ids, ["1" * 32, "2" * 32])  # type: ignore[attr-defined]
        self.assertEqual(len(requests), 2)

    def test_create_transport_classifies_unusable_success_and_http_outcomes(self) -> None:
        class Response:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def __enter__(self) -> Response:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, limit: int) -> bytes:
                return self.payload[:limit]

        for payload in (b"{}", b"not-json"):
            with (
                self.subTest(payload=payload),
                redirect_stderr(io.StringIO()),
                patched_attr(
                    gitlab, "_open_gitlab_request", lambda _request, p=payload: Response(p)
                ),
            ):
                result = gitlab.api_write_url_detailed(
                    "https://gitlab.example/api",
                    "token",
                    "PRIVATE-TOKEN",
                    {"note": "x"},
                    create_kind="draft",
                    write_id="1" * 32,
                )
            self.assertTrue(result.ambiguous_create)

        class ErrorBody:
            def __init__(self, body: bytes) -> None:
                self.body = body

            def read(self, _limit: int = -1) -> bytes:
                return self.body

            def close(self) -> None:
                return None

        for status, expected in (
            (400, "definite_failure"),
            (408, "ambiguous_create"),
            (503, "ambiguous_create"),
        ):
            error = urllib.error.HTTPError(
                "https://gitlab.example/api", status, "synthetic", None, ErrorBody(b"rejected")
            )
            with (
                self.subTest(status=status),
                redirect_stderr(io.StringIO()),
                patched_attr(
                    gitlab,
                    "_open_gitlab_request",
                    lambda _request, exc=error: (_ for _ in ()).throw(exc),
                ),
            ):
                result = gitlab.api_write_url_detailed(
                    "https://gitlab.example/api",
                    "token",
                    "PRIVATE-TOKEN",
                    {"body": "x"},
                    create_kind="discussion",
                    write_id="2" * 32,
                )
            self.assertEqual(result.status, expected)

    def test_gitlab_transport_crosses_local_peer_for_get_and_nonretrying_write(self) -> None:
        requests: list[tuple[str, str, str | None, object]] = []

        class Handler(BaseHTTPRequestHandler):
            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length else b""
                requests.append(
                    (
                        self.command,
                        self.path,
                        self.headers.get("PRIVATE-TOKEN"),
                        json.loads(body) if body else None,
                    )
                )
                payload = json.dumps({"method": self.command}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = _handle
            do_POST = _handle

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        root = f"http://127.0.0.1:{server.server_port}"
        try:
            read = gitlab.api_request_url(
                f"{root}/api/v4/projects/7/merge_requests/9",
                "synthetic-token",
                "PRIVATE-TOKEN",
                method="GET",
            )
            write = gitlab.api_write_url_detailed(
                f"{root}/api/v4/projects/7/merge_requests/9/notes",
                "synthetic-token",
                "PRIVATE-TOKEN",
                {"body": "Synthetic review note"},
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(read, {"method": "GET"})
        self.assertTrue(write.posted)
        self.assertEqual(write.response, {"method": "POST"})
        self.assertEqual(
            requests,
            [
                (
                    "GET",
                    "/api/v4/projects/7/merge_requests/9",
                    "synthetic-token",
                    None,
                ),
                (
                    "POST",
                    "/api/v4/projects/7/merge_requests/9/notes",
                    "synthetic-token",
                    {"body": "Synthetic review note"},
                ),
            ],
        )

    def test_gitlab_get_honors_bounded_retry_after_but_write_is_not_retried(self) -> None:
        """Retry bounded reads while keeping provider writes single-attempt."""

        attempts: list[str] = []
        sleeps: list[float] = []

        class Response:
            def __init__(self) -> None:
                self.sent = False

            def __enter__(self) -> Response:
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def read(self, _limit: int = -1) -> bytes:
                if self.sent:
                    return b""
                self.sent = True
                return b'{"ok":true}'

        def open_request(request: urllib.request.Request) -> Any:
            attempts.append(request.method)
            if request.method == "GET" and attempts.count("GET") == 2:
                return Response()
            raise urllib.error.HTTPError(
                request.full_url,
                503,
                "Unavailable",
                hdrs={"Retry-After": "120"},
                fp=io.BytesIO(b"temporary"),
            )

        with (
            patched_attr(gitlab, "_open_gitlab_request", open_request),
            patched_attr(gitlab.time, "sleep", sleeps.append),
            redirect_stderr(io.StringIO()),
        ):
            read = gitlab.api_request_url(
                "https://gitlab.example/api", "token", "PRIVATE-TOKEN", method="GET"
            )
            write = gitlab.api_request_url(
                "https://gitlab.example/api",
                "token",
                "PRIVATE-TOKEN",
                data={"body": "review"},
                method="POST",
            )

        self.assertEqual(read, {"ok": True})
        self.assertIsNone(write)
        self.assertEqual(attempts, ["GET", "GET", "POST"])
        self.assertEqual(sleeps, [60.0])

    def test_retry_after_parser_accepts_seconds_dates_and_rejects_garbage(self) -> None:
        """Bound Retry-After seconds and dates while rejecting malformed input."""

        self.assertEqual(gitlab._retry_after_seconds("2.5"), 2.5)
        self.assertEqual(gitlab._retry_after_seconds("-1"), 0.0)
        future = gitlab._retry_after_seconds("Fri, 31 Dec 9999 23:59:59 GMT")
        self.assertIsNotNone(future)
        assert future is not None
        self.assertGreater(future, 60.0)
        self.assertIsNone(gitlab._retry_after_seconds("not-a-date"))

    def test_gitlab_api_unit_bounds_mocked_success_responses(self) -> None:
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

    def test_gitlab_api_unit_rejects_mocked_oversized_success_body(self) -> None:
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

    def test_pre_run_snapshot_baseline_contains_all_valid_endpoint_identities(self) -> None:
        plain_notes = [
            {"id": 10, "body": "human", "author": {"id": 8}},
            {"id": 11, "body": build_marker(None) + "\nbot", "author": {"id": 7}},
            {"id": True, "body": "invalid", "author": {"id": 8}},
        ]
        discussions = [
            {
                "id": "discussion-id",
                "notes": [
                    {
                        "id": 21,
                        "body": build_marker(None) + "\nbot",
                        "author": {"id": 7},
                    },
                    {"id": 20, "body": "human", "author": {"id": 8}},
                ],
            },
            {"id": "../unsafe", "notes": [{"id": 22, "body": "ignored"}]},
        ]
        drafts = [
            {"id": 30, "note": "human", "author_id": 8},
            {"id": 31, "note": build_marker(None) + "\nbot", "author_id": 7},
        ]

        def page(_config: Any, endpoint: str, **_kwargs: Any) -> list[Any]:
            if endpoint.startswith("/notes"):
                return plain_notes
            if endpoint == "/discussions":
                return discussions
            if endpoint == "/draft_notes":
                return drafts
            self.fail(endpoint)

        settings.post_mode.cache_clear()
        try:
            with (
                patched_env(OCR_POST_MODE="draft"),
                patched_attr(snapshot, "api_get_paginated", page),
            ):
                refs = snapshot.collect_previous_bot_comment_refs(gitlab_config())
        finally:
            settings.post_mode.cache_clear()

        self.assertIsNotNone(refs)
        assert refs is not None
        self.assertEqual(refs.all_plain_note_ids, [10, 11])
        self.assertEqual(refs.plain_note_ids, [11])
        self.assertEqual(
            refs.all_discussion_note_refs,
            [("discussion-id", 21), ("discussion-id", 20)],
        )
        # The human reply preserves the existing bot thread from ordinary cleanup;
        # the complete baseline still records both identities for rollback guards.
        self.assertEqual(refs.discussion_note_refs, [])
        self.assertEqual(refs.all_draft_note_ids, [30, 31])
        self.assertEqual(refs.draft_note_ids, [31])

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

    def test_rollback_uses_explicit_current_run_ids_and_preserves_baseline(self) -> None:
        previous_refs = snapshot.BotCommentRefs(
            all_plain_note_ids=[10],
            all_discussion_note_refs=[("old-discussion", 20)],
            all_draft_note_ids=[30],
        )
        transaction = PostingTransaction()
        for note_id in (10, 11):
            self.assertTrue(transaction.record_plain(note_id))
        for discussion_id, note_id in (
            ("old-discussion", 20),
            ("new-discussion", 21),
        ):
            self.assertTrue(transaction.record_discussion(discussion_id, note_id))
        for note_id in (30, 31):
            self.assertTrue(transaction.record_draft(note_id))
        deleted: list[tuple[str, object]] = []

        with (
            patched_attr(
                snapshot,
                "delete_plain_note",
                lambda _config, note_id: deleted.append(("plain", note_id)) or True,
            ),
            patched_attr(
                snapshot,
                "delete_discussion_note",
                lambda _config, discussion_id, note_id: (
                    deleted.append(("discussion", (discussion_id, note_id))) or True
                ),
            ),
            patched_attr(
                snapshot,
                "delete_draft_note",
                lambda _config, note_id: deleted.append(("draft", note_id)) or True,
            ),
            redirect_stderr(io.StringIO()),
        ):
            snapshot.rollback_current_run_comments(gitlab_config(), previous_refs, transaction)

        self.assertEqual(
            deleted,
            [
                ("draft", 31),
                ("plain", 11),
                ("discussion", ("new-discussion", 21)),
            ],
        )

    def test_rollback_without_baseline_deletes_only_explicit_pending_drafts(self) -> None:
        transaction = PostingTransaction()
        self.assertTrue(transaction.record_draft(31))
        self.assertTrue(transaction.record_plain(41))
        self.assertTrue(transaction.record_discussion("new-discussion", 51))
        deleted: list[tuple[str, object]] = []

        with (
            patched_attr(
                snapshot,
                "delete_draft_note",
                lambda _config, note_id: deleted.append(("draft", note_id)) or True,
            ),
            patched_attr(
                snapshot,
                "delete_plain_note",
                lambda _config, note_id: deleted.append(("plain", note_id)) or True,
            ),
            patched_attr(
                snapshot,
                "delete_discussion_note",
                lambda _config, discussion_id, note_id: (
                    deleted.append(("discussion", (discussion_id, note_id))) or True
                ),
            ),
            redirect_stderr(io.StringIO()),
        ):
            snapshot.rollback_current_run_comments(gitlab_config(), None, transaction)

        self.assertEqual(deleted, [("draft", 31)])


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
                "fetch_posting_identity",
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
                "fetch_posting_identity",
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
                    create_kind="discussion",
                    write_id="1" * 32,
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
                create_kind="discussion",
                write_id="2" * 32,
            )

        self.assertTrue(write_result.invalid_position)

    def test_generic_non_create_write_never_uses_create_only_invalid_position(self) -> None:
        class FakeResponse:
            def read(self, _limit: int = -1) -> bytes:
                return b'{"message":"position line is invalid"}'

            def close(self) -> None:
                return None

        error = urllib.error.HTTPError(
            "https://gitlab.example/api", 400, "Bad Request", None, FakeResponse()
        )
        with (
            patched_attr(
                gitlab, "_open_gitlab_request", lambda _request: (_ for _ in ()).throw(error)
            ),
            redirect_stderr(io.StringIO()),
        ):
            write_result = gitlab.api_write_url_detailed(
                "https://gitlab.example/api",
                "token",
                "PRIVATE-TOKEN",
                {"body": "x"},
            )

        self.assertTrue(write_result.write_failed)
        self.assertFalse(write_result.invalid_position)

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

    def test_result_transform_retries_short_writes_and_replaces_atomically(self) -> None:
        """Complete short writes before atomically replacing the result artifact."""

        original_write = os.write

        def short_write(descriptor: int, payload: bytes) -> int:
            return original_write(descriptor, payload[:3])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "result.json"
            path.write_text('{"comments": []}', encoding="utf-8")
            with patched_attr(os, "write", short_write):
                transformed = ocr_result.transform_ocr_result(
                    path, lambda payload: {**payload, "status": "success"}
                )

            self.assertEqual(transformed["status"], "success")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), transformed)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(root.glob(".result.json.*.tmp")), [])

    def test_result_transform_short_write_failure_preserves_original_and_cleans_temp(self) -> None:
        """Preserve the original and clean temporary data after short-write failure."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "result.json"
            original = b'{"comments": []}'
            path.write_bytes(original)

            with (
                patched_attr(os, "write", lambda _descriptor, _payload: 0),
                self.assertRaisesRegex(ocr_result.OcrResultMissing, "short write"),
            ):
                ocr_result.transform_ocr_result(path, lambda payload: payload)

            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.glob(".result.json.*.tmp")), [])

    def test_result_transform_detects_inode_replacement_and_keeps_replacement(self) -> None:
        """Reject inode drift without overwriting the independently replaced result."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "result.json"
            path.write_text('{"comments": []}', encoding="utf-8")

            def replace_entry(payload: dict[str, Any]) -> dict[str, Any]:
                path.unlink()
                path.write_text('{"owner":"foreign"}', encoding="utf-8")
                return payload

            with self.assertRaisesRegex(ocr_result.OcrResultMissing, "changed while"):
                ocr_result.transform_ocr_result(path, replace_entry)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"owner": "foreign"})
            self.assertEqual(list(root.glob(".result.json.*.tmp")), [])

    def test_result_transform_rejects_nonobject_recursion_and_growth(self) -> None:
        """Reject malformed transforms and output that exceeds the result budget."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ocr_result.OcrResultMalformed, "must be an object"):
                ocr_result.transform_ocr_result(path, lambda payload: payload)

            path.write_text("{}", encoding="utf-8")

            def recurse(_payload: dict[str, Any]) -> dict[str, Any]:
                raise RecursionError("nested result")

            with self.assertRaises(ocr_result.OcrResultMalformed):
                ocr_result.transform_ocr_result(path, recurse)

            with (
                patched_env(OCR_MAX_RESULT_BYTES="32"),
                self.assertRaises(ocr_result.OcrResultTooLarge),
            ):
                ocr_result.transform_ocr_result(path, lambda _payload: {"value": "x" * 40})

    def test_result_replace_failure_preserves_original_and_cleans_temporary(self) -> None:
        """Preserve the prior result and remove temporary data after replace failure."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "result.json"
            original = b'{"comments":[]}'
            path.write_bytes(original)

            def fail_replace(*_args: Any, **_kwargs: Any) -> None:
                raise OSError("replace unavailable")

            with (
                patched_attr(os, "replace", fail_replace),
                self.assertRaisesRegex(ocr_result.OcrResultMissing, "could not replace"),
            ):
                ocr_result.transform_ocr_result(path, lambda payload: payload)

            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.glob(".result.json.*.tmp")), [])

    def test_toolkit_metadata_is_reserved_and_schema_owned(self) -> None:
        """Keep toolkit metadata reserved and pin its schema at attachment time."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text('{"status":"success"}', encoding="utf-8")
            transformed, metadata = ocr_result.attach_toolkit_metadata(
                path,
                lambda _payload: {"schema_version": 999, "publication": {"state": "passed"}},
            )

            self.assertEqual(metadata["schema_version"], 5)
            self.assertEqual(transformed["_ocr_toolkit"], metadata)

            with self.assertRaisesRegex(ocr_result.OcrResultMalformed, "reserved field"):
                ocr_result.attach_toolkit_metadata(path, lambda _payload: {})

    def test_result_size_configuration_is_bounded_without_echoing_input(self) -> None:
        """Bound result-size configuration without reflecting hostile input."""

        for configured, expected in (
            ("not-an-integer", ocr_result.DEFAULT_MAX_RESULT_BYTES),
            ("0", ocr_result.DEFAULT_MAX_RESULT_BYTES),
            (
                str(ocr_result.MAX_RESULT_BYTES_HARD_LIMIT + 1),
                ocr_result.MAX_RESULT_BYTES_HARD_LIMIT,
            ),
        ):
            with self.subTest(configured=configured), patched_env(OCR_MAX_RESULT_BYTES=configured):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(ocr_result.max_result_bytes(), expected)
                self.assertNotIn("not-an-integer", stderr.getvalue())

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

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_ignores_generic_billing_text(self) -> None:
        warnings = [
            {"file": "x.py", "type": "subtask_error", "message": "billing module failed tests"}
        ]

        self.assertIsNone(result.llm_billing_failure_reason(warnings))

    def test_billing_classifier_tolerates_cyclic_warning_objects(self) -> None:
        """Do not recurse forever if an in-memory caller supplies a cycle."""

        warning: dict[str, Any] = {"message": "ordinary warning"}
        warning["error"] = warning

        self.assertIsNone(result.llm_billing_failure_reason([warning]))

    def test_billing_classifier_reads_nested_provider_error_fields(self) -> None:
        warnings = [
            {
                "file": "x.py",
                "error": {"code": 402, "message": "insufficient_quota"},
            }
        ]

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_matches_numeric_status_without_message(self) -> None:
        warnings = [{"file": "x.py", "status": 402, "type": "subtask_error"}]

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_matches_nested_numeric_code_without_message(self) -> None:
        warnings = [{"file": "x.py", "error": {"code": 402}}]

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_reads_embedded_provider_json_message(self) -> None:
        warnings = [
            {
                "file": "x.py",
                "message": '{"error":{"code":"insufficient_funds","message":"Insufficient user balance","extra":{}}}',
                "type": "subtask_error",
            }
        ]

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_matches_status_code_shapes(self) -> None:
        warnings = [
            {"status_code": 402, "message": "provider rejected request"},
            {"error": {"details": {"status_code": "402"}}},
            '{"status_code": 402, "message": "provider rejected request"}',
            "status_code: 402",
        ]

        reason = result.llm_billing_failure_reason(warnings)

        self.assertEqual(reason, ProviderFailureReason.RATE_OR_SPENDING_LIMIT)

    def test_billing_classifier_ignores_non_billing_status_code(self) -> None:
        warnings = [
            {"status_code": 200, "message": "billing report generated"},
            '{"status_code": 200, "message": "billing report generated"}',
        ]

        self.assertIsNone(result.llm_billing_failure_reason(warnings))

    def test_token_usage_mapping_is_depth_bounded(self) -> None:
        from ocr_toolkit.result_usage import token_usage_mapping

        value: dict[str, Any] = {"total_tokens": 123}
        for _ in range(20):
            value = {"usage": value}

        self.assertIsNone(token_usage_mapping(value))
        self.assertEqual(
            token_usage_mapping(value, max_depth=25),
            {"total_tokens": 123},
        )
