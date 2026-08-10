"""Regression tests for proof-bound GitLab suggestion rendering."""

from __future__ import annotations

import unittest
from typing import Any

from ocr_toolkit.posting import formatting, suggestions

SOURCE = "before\r\nroute:\r\n  destination: 192.0.2.0/24\r\nafter\r\n"


def evaluate(**overrides: Any) -> suggestions.SuggestionDecision:
    """Evaluate a synthetic replacement against one immutable source blob."""

    comment: dict[str, Any] = {
        "line": 2,
        "start_line": 2,
        "end_line": 3,
        "existing_code": "route:\n  destination: 192.0.2.0/24",
        "suggestion_code": "route:\n  destination: 198.51.100.0/24",
    }
    comment.update(overrides)
    return suggestions.evaluate_suggestion(comment, "config/service.yml", lambda _path: SOURCE)


class SuggestionValidationTests(unittest.TestCase):
    """Prove only one exact contiguous replacement becomes actionable."""

    def test_valid_one_line_replacement_is_actionable(self) -> None:
        decision = evaluate(
            start_line=2,
            end_line=2,
            existing_code="route:\n",
            suggestion_code="endpoint:\r\n",
        )

        self.assertEqual(decision.state, suggestions.SuggestionState.ACTIONABLE)
        self.assertEqual(decision.replacement, "endpoint:")
        self.assertEqual(decision.range_suffix, "-0+0")

    def test_valid_multiline_replacement_is_actionable(self) -> None:
        decision = evaluate()

        self.assertEqual(decision.state, suggestions.SuggestionState.ACTIONABLE)
        body = formatting.format_inline_comment(
            {"content": "Use the documentation range."},
            suggestion_decision=decision,
        )
        self.assertIn("```suggestion:-0+1", body)
        self.assertIn("198.51.100.0/24", body)

    def test_missing_existing_code_is_omitted(self) -> None:
        self.assertEqual(
            evaluate(existing_code=None).omission,
            suggestions.SuggestionOmission.MISSING_EXISTING_CODE,
        )

    def test_stale_existing_code_is_omitted(self) -> None:
        self.assertEqual(
            evaluate(existing_code="stale").omission,
            suggestions.SuggestionOmission.EXISTING_CODE_MISMATCH,
        )

    def test_invalid_and_out_of_bounds_ranges_are_omitted(self) -> None:
        self.assertEqual(
            evaluate(start_line=3, end_line=2).omission,
            suggestions.SuggestionOmission.INVALID_RANGE,
        )
        self.assertEqual(
            evaluate(start_line=2, end_line=20).omission,
            suggestions.SuggestionOmission.RANGE_OUT_OF_BOUNDS,
        )

    def test_synthetic_omission_bridge_is_omitted(self) -> None:
        for marker in ("...", "# ...", "// ...", "/* ... */", "<!-- ... -->", "(* ... *)"):
            with self.subTest(marker=marker):
                decision = evaluate(
                    suggestion_code=(
                        "route:\n  destination: 198.51.100.0/24\n\n"
                        f"{marker}\naccess:\n  allowed: true"
                    )
                )

                self.assertEqual(
                    decision.omission,
                    suggestions.SuggestionOmission.SYNTHETIC_OMISSION,
                )

    def test_non_omission_ellipsis_remains_valid_code(self) -> None:
        decision = evaluate(
            suggestion_code=(
                "route:\n  destination: 198.51.100.0/24\ndescription: Continue ... with fallback"
            )
        )

        self.assertEqual(decision.state, suggestions.SuggestionState.ACTIONABLE)

    def test_diff_prefixed_replacement_is_omitted(self) -> None:
        decision = evaluate(suggestion_code="+route:\n+  destination: 198.51.100.0/24")

        self.assertEqual(decision.omission, suggestions.SuggestionOmission.DIFF_PREFIXED)

    def test_exact_noop_is_suppressed_without_existing_code(self) -> None:
        decision = evaluate(
            existing_code=None,
            suggestion_code="route:\r\n  destination: 192.0.2.0/24\r\n",
        )

        self.assertEqual(decision.state, suggestions.SuggestionState.NO_OP)
        self.assertEqual(formatting.format_suggestion_block(decision), "")

    def test_unsafe_path_is_rejected_before_blob_read(self) -> None:
        calls: list[str] = []

        def read_blob(path: str) -> str | None:
            calls.append(path)
            return "same\n"

        decision = suggestions.evaluate_suggestion(
            {"line": 1, "existing_code": "same", "suggestion_code": "changed"},
            "../outside.py",
            read_blob,
        )

        self.assertEqual(decision.omission, suggestions.SuggestionOmission.INVALID_PATH)
        self.assertEqual(calls, [])

    def test_omission_keeps_finding_and_exposes_only_closed_reason(self) -> None:
        decision = evaluate(existing_code="token=private-value")
        body = formatting.format_inline_comment(
            {"content": "The route should use the documentation network."},
            suggestion_decision=decision,
        )

        self.assertIn("The route should use the documentation network.", body)
        self.assertIn("did not match the reviewed range", body)
        self.assertNotIn("```suggestion", body)
        self.assertNotIn("private-value", body)

    def test_impossible_typed_decision_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            suggestions.SuggestionDecision(suggestions.SuggestionState.ACTIONABLE)
        with self.assertRaises(ValueError):
            suggestions.SuggestionDecision(suggestions.SuggestionState.OMITTED)


if __name__ == "__main__":
    unittest.main()
