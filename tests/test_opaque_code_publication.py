"""Optional opaque code must be source-proven and safely rendered at both sinks."""

from __future__ import annotations

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.opaque_code import prove_opaque_code
from ocr_toolkit.posting.formatting import format_fallback_comment, format_inline_comment
from ocr_toolkit.posting.suggestions import evaluate_suggestion
from ocr_toolkit.providers.local import local_report_parts
from ocr_toolkit.reporting.model import ReviewReport
from ocr_toolkit.reporting.result import normalize_coverage_diagnostics
from ocr_toolkit.result_contract import ReviewOutcome


@pytest.mark.parametrize(
    ("existing", "suggestion"),
    [
        ("List<Entry> value;", "List<Node> value;"),
        ("(?P<entry>[a-z]+)", "(?P<item>[a-z]+)"),
        ("<Widget enabled />", "<Widget disabled />"),
        ("  key: List<Entry>", "  key: List<Node>"),
    ],
)
def test_proven_code_survives_projection_and_both_renderers(existing: str, suggestion: str) -> None:
    comment = {
        "path": "src/example.txt",
        "line": 1,
        "content": "Update the declaration.",
        "existing_code": existing,
        "suggestion_code": suggestion,
    }
    payload = {"status": "success", "warnings": [], "comments": [comment]}

    def proof(item: dict[str, object]):
        return prove_opaque_code(item, "src/example.txt", lambda _path: existing + "\n")

    projected, publication, filtered = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset(), code_proof=proof
    )
    assert not filtered
    assert publication["state"] == "passed"
    assert projected["comments"] == [comment]

    decision = evaluate_suggestion(comment, "src/example.txt", lambda _path: existing + "\n")
    inline = format_inline_comment(comment, suggestion_decision=decision)
    fallback = format_fallback_comment(comment, suggestion_decision=decision)
    assert suggestion in inline and "```suggestion:" in inline
    assert existing in fallback and suggestion in fallback

    outcome = ReviewOutcome(status="success", kind="success", budget_exceeded=False)
    report = ReviewReport(
        outcome=outcome,
        comments=(comment,),
        warnings=(),
        diagnostics=normalize_coverage_diagnostics(outcome, ()),
        publication={"state": "passed"},
    )
    local = "".join(local_report_parts(report))
    assert existing in local and suggestion in local
    assert local.count("#### Existing code") == 1
    assert local.count("#### Suggested code") == 1


def test_unproven_code_is_omitted_but_mandatory_prose_remains() -> None:
    comment = {
        "path": "src/example.txt",
        "line": 1,
        "content": "Update the declaration.",
        "existing_code": "List<Entry>",
        "suggestion_code": "List<Node>",
    }
    payload = {"status": "success", "warnings": [], "comments": [comment]}
    projected, publication, filtered = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(
            item, "src/example.txt", lambda _path: "different source\n"
        ),
    )
    assert filtered
    assert projected["comments"] == [
        {"path": "src/example.txt", "line": 1, "content": "Update the declaration."}
    ]
    assert publication["omitted"]["comments"] == 0
    assert publication["omitted"]["fields"] == 2


def test_proven_code_cannot_mask_mixed_secret_or_unproven_prose() -> None:
    comment = {
        "path": "src/example.txt",
        "line": 1,
        "content": "Update the declaration.",
        "existing_code": "List<Entry>\nlogin_password: 'synthetic-secret-value'",
        "suggestion_code": "List<Node>\nlogin_password: 'synthetic-secret-value'",
    }
    payload = {"status": "success", "warnings": [], "comments": [comment]}
    projected, publication, filtered = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(
            item, "src/example.txt", lambda _path: comment["existing_code"] + "\n"
        ),
    )
    assert filtered
    assert len(projected["comments"]) == 1
    assert "existing_code" not in projected["comments"][0]
    assert publication["reason_counts"]["secret"] >= 1

    comment["content"] = "Check List<Entry>."
    projected, publication, filtered = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(
            item, "src/example.txt", lambda _path: comment["existing_code"] + "\n"
        ),
    )
    assert filtered and not projected["comments"]
    assert publication["omitted"]["comments"] == 1
