"""Thematic OCR CI regression tests."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from ocr_toolkit.common.markdown import (
    inline_code,
    markdown_code_block,
    neutralize_quick_actions,
    neutralize_suggestion_fences,
)
from ocr_toolkit.common.redaction import (
    redact_sensitive,
    redact_url_userinfo,
    redact_url_userinfo_only,
)
from ocr_toolkit.context import settings as context_settings
from ocr_toolkit.posting import comments as posting_comments
from ocr_toolkit.posting import settings
from tests.support import (
    patched_env,
)


class MarkdownSafetyTests(unittest.TestCase):
    def test_invalid_backtick_fence_does_not_hide_quick_action(self) -> None:
        text = "``` `\n/close"

        self.assertEqual(neutralize_quick_actions(text), "``` `\n\\/close")

    def test_valid_fences_preserve_code_block_quick_actions(self) -> None:
        text = "```text\n/close\n```\n~~~\n/reopen\n~~~\n/label bug"

        neutralized = neutralize_quick_actions(text)

        self.assertIn("```text\n\\/close\n```", neutralized)
        self.assertIn("~~~\n\\/reopen\n~~~", neutralized)
        self.assertTrue(neutralized.endswith("\\/label bug"))

    def test_quick_action_neutralizer_preserves_line_endings(self) -> None:
        text = "first\r\nsecond\r\n"

        self.assertEqual(neutralize_quick_actions(text), text)

    def test_suggestion_fence_neutralizer_handles_long_backtick_fences(self) -> None:
        text = "````suggestion:-0+1\n/change\n````\n"

        neutralized = neutralize_suggestion_fences(text)

        self.assertEqual(neutralized, "````text\n/change\n````\n")

    def test_suggestion_fence_neutralizer_does_not_create_valid_invalid_fence(self) -> None:
        text = "```suggestion```\n/close"

        neutralized = neutralize_suggestion_fences(text)

        self.assertEqual(neutralized, text)

    def test_invalid_fence_closer_does_not_hide_quick_action(self) -> None:
        text = "```text\n/inside\n```not-a-close\n/close"

        neutralized = neutralize_quick_actions(text)

        self.assertIn("\\/inside", neutralized)
        self.assertIn("```not-a-close", neutralized)
        self.assertTrue(neutralized.endswith("\\/close"))

    def test_indented_code_quick_action_is_escaped_at_raw_note_boundary(self) -> None:
        text = "    /example\n/close"

        self.assertEqual(neutralize_quick_actions(text), "    \\/example\n\\/close")

    def test_inline_code_escapes_controls_by_default(self) -> None:
        rendered = inline_code("path\n/close\u202esecret")

        self.assertEqual(rendered, "`path\\n/close\\u202esecret`")

    def test_inline_code_preserves_matching_boundary_spaces(self) -> None:
        self.assertEqual(inline_code(" branch "), "`  branch  `")
        self.assertEqual(inline_code(" branch"), "` branch`")

    def test_code_block_preserves_single_trailing_newline(self) -> None:
        rendered = markdown_code_block("text", "line\n")

        self.assertEqual(rendered, "```text\nline\n```")


class SettingsTests(unittest.TestCase):
    def test_posting_limits_are_clamped(self) -> None:
        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            patched_env(
                OCR_MAX_POST_COMMENTS="999999",
                OCR_MAX_RESULT_BYTES="999999999",
            ),
        ):
            self.assertEqual(settings.max_post_comments(), settings.MAX_POST_COMMENTS_HARD_LIMIT)
            self.assertEqual(settings.max_result_bytes(), settings.MAX_RESULT_BYTES_HARD_LIMIT)

        self.assertIn("hard limit", stderr.getvalue())

    def test_invalid_review_language_does_not_log_raw_value(self) -> None:
        raw = "English\nAuthorization: Bearer test-redaction-value"
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            language = context_settings._safe_language_label(raw)

        self.assertEqual(language, "Russian")
        logged = stderr.getvalue()
        self.assertNotIn("test-redaction-value", logged)
        self.assertNotIn("Authorization", logged)

    def test_invalid_ocr_exit_code_does_not_log_raw_value(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            with patched_env(OCR_EXIT_CODE="not-a-number-with-sensitive-shape"):
                self.assertEqual(settings.ocr_exit_code(), 1)

        self.assertNotIn("not-a-number-with-sensitive-shape", stderr.getvalue())

    def test_invalid_post_mode_does_not_log_raw_value(self) -> None:
        stderr = io.StringIO()
        settings.post_mode.cache_clear()
        try:
            with redirect_stderr(stderr):
                with patched_env(OCR_POST_MODE="private_token=secret-value"):
                    self.assertEqual(settings.post_mode(), "draft")
        finally:
            settings.post_mode.cache_clear()

        self.assertNotIn("secret-value", stderr.getvalue())
        self.assertIn("Invalid OCR_POST_MODE value", stderr.getvalue())

    def test_context_int_settings_can_be_clamped(self) -> None:
        with patched_env(OCR_BACKGROUND_MAX_BYTES="999999999"):
            self.assertEqual(
                context_settings.getenv_int(
                    "OCR_BACKGROUND_MAX_BYTES",
                    1,
                    max_value=context_settings.MAX_BACKGROUND_MAX_BYTES,
                ),
                context_settings.MAX_BACKGROUND_MAX_BYTES,
            )

    def test_env_file_detection_is_case_insensitive(self) -> None:
        self.assertTrue(context_settings.is_env_file(".ENV"))
        self.assertTrue(context_settings.is_env_file(".Env.production"))
        self.assertTrue(context_settings.is_env_file("APP.ENV"))
        self.assertTrue(context_settings.is_env_file("service.env.yaml"))
        self.assertTrue(context_settings.is_env_file("service.env-prod.json"))
        self.assertFalse(context_settings.is_env_file("environment.yml"))
        self.assertTrue(context_settings.is_env_file("service.env.yaml"))
        self.assertTrue(context_settings.is_env_file("service.env-prod.json"))
        self.assertFalse(context_settings.is_env_file("environment.yml"))


class RedactionTests(unittest.TestCase):
    def test_redacts_long_secret_shaped_environment_values(self) -> None:
        secret = "opaque-runtime-secret-value-1234567890"
        with patched_env(OCR_PLUGIN_ACCESS_TOKEN=secret):
            self.assertEqual(redact_sensitive(f"credential={secret}"), "credential=***")
            self.assertNotIn(secret, redact_sensitive(f"credential={secret.replace('-', '%2D')}"))

    def test_does_not_redact_short_or_benign_environment_values(self) -> None:
        text = "short=tiny mode=readonly host=example.com"
        with patched_env(
            OCR_PLUGIN_ACCESS_TOKEN="tiny",
            OCR_TOKENIZER_MODE="readonly",
            OCR_PLUGIN_HOST="example.com",
        ):
            self.assertEqual(redact_sensitive(text), text)

    def test_url_userinfo_is_redacted_when_url_is_embedded_in_prose(self) -> None:
        for delimiter in (" ", ",", ".", ";", ")"):
            with self.subTest(delimiter=delimiter):
                value = f"request https://user:pass@example.com{delimiter}next"
                redacted = redact_sensitive(value)
                self.assertNotIn("user:pass", redacted)
                self.assertIn(delimiter, redacted)

    def test_encoded_query_key_separators_are_normalized_before_matching(self) -> None:
        for key in ("api%20key", "access+token", "client%09secret"):
            with self.subTest(key=key):
                redacted = redact_sensitive(f"https://example.com/?{key}=secret-value")
                self.assertNotIn("secret-value", redacted)
        self.assertIn(
            "public-value",
            redact_sensitive("https://example.com/?api%20keyword=public-value"),
        )

    def test_common_redaction_handles_auth_schemes_and_url_userinfo(self) -> None:
        text = "Authorization: Basic abc client_secret=def private_token: ghi"
        cleaned = redact_sensitive(text)
        self.assertNotIn("abc", cleaned)
        self.assertNotIn("def", cleaned)
        self.assertNotIn("ghi", cleaned)
        self.assertEqual(
            redact_url_userinfo("https://user:pass@example.com/path?token=x&ok=1"),
            "https://***@example.com/path?token=***&ok=1",
        )
        self.assertEqual(
            redact_url_userinfo_only("token=abc/path?auth_token=abc"),
            "token=abc/path?auth_token=abc",
        )
        self.assertEqual(
            redact_url_userinfo_only("make:test@runner1"),
            "make:test@runner1",
        )
        self.assertEqual(
            redact_url_userinfo_only("name:tag@sha256abc"),
            "name:tag@sha256abc",
        )

    def test_generic_redaction_covers_url_userinfo(self) -> None:
        self.assertEqual(
            redact_sensitive("request https://user:pass@example.com/v1 failed"),
            "request https://***@example.com/v1 failed",
        )

    def test_sensitive_query_redaction_preserves_fragment(self) -> None:
        self.assertEqual(
            redact_url_userinfo("https://example.com/path?token=abc#section"),
            "https://example.com/path?token=***#section",
        )

    def test_compact_escaped_text_neutralizes_mentions_and_markdown(self) -> None:
        text = posting_comments.compact_escaped_text("@ops see [link](https://x)", 200)

        self.assertNotIn("@ops", text)
        self.assertIn("&#64;ops", text)
        self.assertIn("\\[link\\]", text)

    def test_env_secret_redaction_covers_short_known_secret_values(self) -> None:
        with patched_env(OCR_LLM_TOKEN="s3cr"):
            cleaned = redact_sensitive("bare secret s3cr")

        self.assertEqual(cleaned, "bare secret ***")

    def test_env_secret_redaction_removes_invisible_value_splits_first(self) -> None:
        with patched_env(OCR_LLM_TOKEN="s3cr"):
            cleaned = redact_sensitive("bare secret s3\u200bcr")

        self.assertEqual(cleaned, "bare secret ***")

    def test_env_secret_redaction_normalizes_secret_value_too(self) -> None:
        with patched_env(OCR_LLM_TOKEN="s3\u200bcr"):
            cleaned = redact_sensitive("bare secret s3cr")

        self.assertEqual(cleaned, "bare secret ***")

    def test_env_secret_redaction_ignores_empty_normalized_secret_value(self) -> None:
        with patched_env(OCR_LLM_TOKEN="\u200b\u200c\u200d\u200e"):
            cleaned = redact_sensitive("ordinary text")

        self.assertEqual(cleaned, "ordinary text")

    def test_named_secret_redaction_removes_invisible_key_splits_first(self) -> None:
        cleaned = redact_sensitive("api\u200b_key=secret-value")

        self.assertEqual(cleaned, "api_key=***")

    def test_named_secret_redaction_removes_line_breaks_inside_tokens(self) -> None:
        self.assertEqual(
            redact_sensitive("Authori\tzation: secret-value"),
            "authorization: ***",
        )
        self.assertEqual(
            redact_sensitive("api_\nkey=secret-value"),
            "api_key=***",
        )

    def test_env_secret_redaction_replaces_longest_values_first(self) -> None:
        with patched_env(
            OCR_LLM_TOKEN="abcdefghijkl",
            OCR_LLM_AUTH_TOKEN="abcdefghijklmnop",
        ):
            cleaned = redact_sensitive("short=abcdefghijkl long=abcdefghijklmnop")

        self.assertNotIn("mnop", cleaned)
        self.assertEqual(cleaned, "short=*** long=***")

    def test_auth_header_name_is_not_treated_as_secret_value(self) -> None:
        with patched_env(OCR_LLM_AUTH_HEADER="authorization"):
            benign = redact_sensitive("configured header is authorization")
            cleaned = redact_sensitive("Authorization: Basic secret-value")

        self.assertEqual(benign, "configured header is authorization")
        self.assertEqual(cleaned, "Authorization: ***")

    def test_env_secret_redaction_covers_quote_plus_values(self) -> None:
        with patched_env(OCR_LLM_TOKEN="secret token value"):
            cleaned = redact_sensitive("token=secret+token+value")

        self.assertEqual(cleaned, "token=***")

    def test_bare_query_style_values_are_redacted(self) -> None:
        self.assertEqual(redact_url_userinfo("token=abc"), "token=***")
        self.assertEqual(redact_url_userinfo("api_key=abc other"), "api_key=*** other")
        self.assertEqual(redact_url_userinfo("auth_token=abc"), "auth_token=***")
        self.assertEqual(redact_url_userinfo("secret_key=abc"), "secret_key=***")
        self.assertEqual(redact_url_userinfo("MY_API_KEY=abc"), "MY_API_KEY=***")
        self.assertEqual(redact_url_userinfo("VAULT_TOKEN=abc"), "VAULT_TOKEN=***")
        self.assertEqual(redact_url_userinfo("session_token=abc"), "session_token=***")
        self.assertEqual(
            redact_sensitive('{"aws_secret_access_key": "abc"}'),
            '{"aws_secret_access_key": "***"}',
        )

    def test_url_redaction_normalizes_invisible_userinfo_controls(self) -> None:
        self.assertEqual(
            redact_url_userinfo("https://user:pa\u200bss@example.com/pkg"),
            "https://***@example.com/pkg",
        )

    def test_url_redaction_handles_encoded_sensitive_query_keys(self) -> None:
        self.assertEqual(
            redact_url_userinfo("https://example.com/?access%5Ftoken=abc&ok=1"),
            "https://example.com/?access%5Ftoken=***&ok=1",
        )
        self.assertEqual(
            redact_sensitive("https://example.com/?access%5Ftoken=abc&ok=1"),
            "https://example.com/?access%5Ftoken=***&ok=1",
        )
        self.assertEqual(
            redact_url_userinfo("client%5Fsecret=abc"),
            "client%5Fsecret=***",
        )
        self.assertEqual(redact_url_userinfo("api%0Akey=abc"), "api%0Akey=***")
        self.assertEqual(redact_url_userinfo("access%09token=abc"), "access%09token=***")
        self.assertEqual(redact_url_userinfo("api\tkey=abc"), "api\tkey=***")
        self.assertEqual(
            redact_url_userinfo("https://user:pa\tss@example.com/pkg"),
            "https://***@example.com/pkg",
        )
        self.assertEqual(
            redact_url_userinfo("https://user:pa\nss@example.com/pkg"),
            "https://***@example.com/pkg",
        )
        self.assertEqual(
            redact_url_userinfo("https://token@example.com/pkg"),
            "https://***@example.com/pkg",
        )
        self.assertEqual(
            redact_url_userinfo("https://user%3Apass@example.com/pkg"),
            "https://***@example.com/pkg",
        )
        self.assertEqual(
            redact_url_userinfo("https://example.com\nname@example.com"),
            "https://example.com\nname@example.com",
        )

    def test_redaction_does_not_match_sensitive_words_inside_benign_keys(self) -> None:
        text = (
            "passwordless_mode=true api_keyword: search secret_keyboard=off access_token_ttl=3600"
        )

        self.assertEqual(redact_sensitive(text), text)
        self.assertEqual(redact_url_userinfo(text), text)

    def test_url_query_at_sign_is_not_treated_as_userinfo(self) -> None:
        self.assertEqual(
            redact_url_userinfo("https://example.com/path?email=a@b.com"),
            "https://example.com/path?email=a@b.com",
        )


class MarkdownTests(unittest.TestCase):
    def test_code_block_language_is_allowlisted(self) -> None:
        block = markdown_code_block("python\n/label bug", "print('x')")

        self.assertTrue(block.startswith("```\n"))
        self.assertNotIn("/label", block.splitlines()[0])

    def test_code_block_escapes_unicode_controls_by_default(self) -> None:
        block = markdown_code_block("text", "safe\u202e-name\x85next\r\nline\tindent")

        self.assertIn("safe\\u202e-name\\x85next\\x0d", block)
        self.assertIn("line\tindent", block)
