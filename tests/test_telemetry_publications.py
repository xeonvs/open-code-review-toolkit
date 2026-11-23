"""Verify telemetry at the current GitLab Markdown producer boundary."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.ocr_result import OcrToolkitAdvisory
from ocr_toolkit.posting.approval import ApprovalResult, ApprovalStatus
from ocr_toolkit.posting.formatting import (
    format_ocr_core_advisory,
    format_publication_dlp_details,
    format_token_usage_summary,
    format_tool_calls_summary,
    publication_dlp_signal,
    summarize_result,
)
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.posting.workflow import summary_with_run_marker
from ocr_toolkit.reporting.federation import format_federation, reconcile
from ocr_toolkit.reporting.usage import format_verified_mcp_usage
from ocr_toolkit.result_contract import parse_result_outcome
from ocr_toolkit.telemetry.metrics.cost import observe_cost
from ocr_toolkit.telemetry.publications import parse_publication
from tests.reporting.test_federation import _receipt
from tests.test_dlp_v2_producer import _payload
from tests.test_result_contract import manifest_result


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("success", "complete"),
        ("warning", "complete_with_warnings"),
        ("partial", "incomplete"),
        ("budget_exceeded", "budget_exceeded"),
        ("skipped", "skipped"),
        ("failed", "failed"),
        ("admission-filtered", "incomplete"),
    ],
)
def test_reads_current_producer_outcomes(status, expected):
    rendered = summarize_result(0, 0, 0, 0, outcome_status=status, emoji=True)
    result = parse_publication(build_marked_note_body(rendered))
    assert result is not None and result["recognized"]
    assert result["outcome"] == expected


def test_reads_current_posting_facts_and_keeps_only_closed_data():
    private_label = "synthetic-private-project-alias"
    receipt = _receipt()
    receipt["schema"] = "ocr.federation/v2"
    alias = f"{private_label}__reader"
    entry = receipt["tools"].pop("docs__read")
    receipt["tools"][alias] = entry | {
        "server": private_label,
        "attempted": 2,
        "completed": 1,
        "denied": 1,
        "dlp_rejected": 1,
        "dlp_gates": {
            "arguments": dict.fromkeys(("forbidden", "invalid_text", "limit", "pii", "secret"), 0),
            "result": dict.fromkeys(("forbidden", "invalid_text", "limit", "pii", "secret"), 0)
            | {"pii": 1},
        },
    }
    federation = reconcile(receipt, {alias: 2}, {alias})
    outcome = parse_result_outcome(
        manifest_result(
            "partial", selected=["one", "two"], completed=["one"], failed=[("two", "timeout")]
        )
    )
    rendered = summarize_result(
        2,
        1,
        1,
        1,
        comments=[
            {"severity": "high", "category": "bug"},
            {"severity": "low", "category": "style"},
        ],
        warnings=["Synthetic warning prose is not a telemetry field."],
        omitted_count=3,
        suppressed_count=4,
        outcome_status="partial",
        coverage_summary=outcome.coverage_summary,
        fallback_reasons={"invalid_position": 1},
        merge_request_lifecycle="closed",
        approval_result=ApprovalResult(
            ApprovalStatus.NOT_ELIGIBLE, "publication has partial coverage"
        ),
        tool_calls_summary=format_tool_calls_summary(
            {"total": 9, "by_tool": {"file_read": 2, "code_comment": 2}}
        ),
        token_usage_summary=format_token_usage_summary(
            {
                "usage": {
                    "total_tokens": 100,
                    "input_tokens": 80,
                    "output_tokens": 15,
                    "cached_tokens": 30,
                }
            }
        ),
        mcp_usage_summary=format_verified_mcp_usage(
            mcp_usage={"ocr_toolkit_evidence": 2, private_label: 3},
            evidence={
                "calls": 2,
                "mandatory": True,
                "used": True,
                "actions": {
                    "state": "verified",
                    "attempted": {
                        "summary": 1,
                        "list": 1,
                        "get": 0,
                        "search": 0,
                        "coverage": 0,
                        "unattributed": 0,
                    },
                    "completed": {"summary": 1, "list": 1, "get": 0, "search": 0, "coverage": 0},
                },
            },
            federation=federation,
            legacy_policy=True,
        ),
        ocr_core_advisory_summary=format_ocr_core_advisory(OcrToolkitAdvisory(1000, 100)),
        emoji=False,
    )
    parsed = parse_publication(build_marked_note_body(rendered))
    assert parsed is not None and parsed["recognized"]
    assert parsed["outcome"] == "incomplete"
    assert parsed["findings"] == 2
    assert parsed["severity"] == {"high": 1, "low": 1}
    assert parsed["categories"] == {"bug": 1, "style": 1}
    assert parsed["posting"] == {"inline": 1, "fallback": 1, "omitted": 3}
    assert parsed["coverage"] == {
        "selected": 2,
        "completed": 1,
        "reused": 0,
        "failed": 1,
        "waived": 0,
    }
    assert parsed["tool_calls"] == 9 and parsed["tool_calls_by_name"] == {
        "code_comment": 2,
        "file_read": 2,
    }
    assert parsed["tokens"] == {"total": 100, "input": 80, "output": 15, "cached": 30, "other": 5}
    assert parsed["mcp"]["calls_by_name"] == {"ocr_toolkit_evidence": 2, "other": 3}
    assert parsed["completed_evidence_actions"] == {"state": "available", "summary": 1, "list": 1}
    assert parsed["federation"]["dlp_gates"]["result"] == {"pii": 1}
    assert parsed["legacy_context_policy"]
    assert parsed["ocr_core_advisory"] == {"actual": 1000, "recommended": 100}
    assert parsed["reviewer_suppressed_findings"] == 4
    assert parsed["warning_count"] == 1
    assert parsed["fallback_reasons"] == {"invalid_position": 1}
    assert parsed["approval_state"] == "not eligible"
    assert parsed["terminal_lifecycle"] == "closed"
    assert private_label not in json.dumps(parsed)
    assert "Synthetic warning prose" not in json.dumps(parsed)


def test_reads_current_publication_dlp_producer_and_separates_cleanup():
    _, receipt, _ = review_runner._publication_projection(
        _payload(public_fields=2), forbidden=(), allowed_tools=frozenset()
    )
    details = format_publication_dlp_details(publication_dlp_signal(receipt))
    rendered = summarize_result(
        2,
        2,
        0,
        0,
        outcome_status="publication-filtered",
        publication_dlp_details=details,
    )
    result = parse_publication(rendered)
    assert result is not None and result["recognized"]
    assert result["outcome"] == "complete_publication_filtered"
    assert result["publication_filter"]["public_output"]["fields"] == 2
    assert result["publication_filter"]["private_sanitization"]["fields"] == 2


@pytest.mark.parametrize(
    ("original_changes", "recognized"),
    [
        ({"operational_partial": True}, True),
        ({"operational_partial": False}, False),
        ({"operational_partial": 1}, False),
        ({"operational_partial": True, "failed": 0, "completed": 2}, False),
        ({"operational_partial": True, "outcome": "failed"}, False),
        ({"operational_partial": True, "unknown": 1}, False),
    ],
)
def test_reads_only_valid_legacy_operational_partial_markers(original_changes, recognized):
    _, receipt, _ = review_runner._publication_projection(
        _payload(public_fields=2), forbidden=(), allowed_tools=frozenset()
    )
    signal = publication_dlp_signal(receipt)
    assert signal is not None and signal["schema_version"] == "ocr.publication-dlp-signal/v4"
    outcome = parse_result_outcome(
        manifest_result(
            "partial", selected=["one", "two"], completed=["one"], failed=[("two", "timeout")]
        )
    )
    signal["original"] = {
        "outcome": "partial",
        "selected": 2,
        "completed": 1,
        "reused": 0,
        "failed": 1,
        "waived": 0,
        **original_changes,
    }
    parsed = parse_publication(
        summarize_result(
            1,
            1,
            0,
            0,
            outcome_status=outcome.kind,
            coverage_summary=outcome.coverage_summary,
            publication_dlp_details=format_publication_dlp_details(signal),
        )
    )
    assert parsed is not None and parsed["recognized"] is recognized
    assert "operational_partial" not in json.dumps(parsed)
    if recognized:
        assert parsed["outcome"] == "incomplete"
        assert parsed["findings"] == 1 and parsed["coverage"]["failed"] == 1
        assert parsed["publication_filter"]["public_output"]["fields"] == 2


def test_current_federation_formatter_orders_prefix_related_tools_by_alias():
    receipt = _receipt()
    first, second = "docs__read", "docs__read2"
    receipt["tools"][first].update(attempted=1, completed=1)
    receipt["tools"][second] = receipt["tools"][first].copy()
    rendered_signal = format_federation(reconcile(receipt, {first: 1, second: 1}, {first, second}))
    prefix, details = rendered_signal.split("; ", 1)
    rendered_tools = details.split("; ")
    assert rendered_tools[0].startswith(f"{first}[")
    assert rendered_tools[1].startswith(f"{second}[")

    publication = summarize_result(0, 0, 0, 0, mcp_usage_summary=rendered_signal)
    parsed = parse_publication(publication)
    assert parsed is not None and parsed["recognized"]
    assert parsed["federation"]["tools"] == 2
    assert parsed["federation"]["completed"] == 2
    assert first not in json.dumps(parsed)

    reversed_signal = "; ".join([prefix, *reversed(rendered_tools)])
    bad = parse_publication(summarize_result(0, 0, 0, 0, mcp_usage_summary=reversed_signal))
    assert bad is not None and not bad["recognized"]


def _legacy_dlp_receipt(state: str) -> dict:
    reasons = dict.fromkeys(
        ("forbidden", "invalid_text", "laundering", "limit", "pii", "secret"), 0
    )
    reasons.update(forbidden=1, laundering=1)
    if state == "private-sanitized":
        return {"state": state, "reason_counts": reasons, "sanitized_fields": 2}
    return {
        "state": state,
        "reason_counts": reasons,
        "retained": {"comments": 2, "warnings": 0},
        "omitted": {"comments": 1, "warnings": 0, "fields": 1},
        "original": {
            "outcome": "clean",
            "selected": 2,
            "completed": 2,
            "reused": 0,
            "failed": 0,
            "waived": 0,
        },
    }


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_legacy_filtering_reasons_keep_their_historical_domain(version):
    receipt = _legacy_dlp_receipt("publication-filtered")
    signal = publication_dlp_signal(receipt)
    assert signal is not None
    signal["schema_version"] = f"ocr.publication-dlp-signal/{version}"
    if version == "v1":
        signal["state"] = "filtered"
    details = format_publication_dlp_details(signal)
    parsed = parse_publication(
        summarize_result(
            2, 2, 0, 0, outcome_status="publication-filtered", publication_dlp_details=details
        )
    )
    assert parsed is not None and parsed["recognized"]
    filtering = parsed["publication_filter"]
    assert filtering["historical_reason_counts"] == receipt["reason_counts"]
    assert "public_output" not in filtering
    assert "private_sanitization" not in filtering


@pytest.mark.parametrize("version", ["v2", "v3"])
def test_legacy_private_sanitization_reasons_keep_their_private_domain(version):
    receipt = _legacy_dlp_receipt("private-sanitized")
    signal = publication_dlp_signal(receipt)
    assert signal is not None
    signal["schema_version"] = f"ocr.publication-dlp-signal/{version}"
    parsed = parse_publication(
        summarize_result(0, 0, 0, 0, publication_dlp_details=format_publication_dlp_details(signal))
    )
    assert parsed is not None and parsed["recognized"]
    assert parsed["publication_filter"] == {
        "state": "private-sanitized",
        "private_sanitization": {"fields": 2, "reason_counts": receipt["reason_counts"]},
    }


@pytest.mark.parametrize("state", ["private-sanitized", "publication-filtered"])
def test_legacy_dlp_source_counts_must_be_bounded_per_source(state):
    receipt = _legacy_dlp_receipt(state)
    receipt["source_attribution"] = {
        "schema": "ocr.forbidden-sources/v1",
        "counts": {
            "forge_discussions": 1,
            "remediation_threads": 1,
            "ci_outcomes": 0,
            "external_context": 0,
            "operator_secret": 0,
            "other": 0,
        },
    }
    signal = publication_dlp_signal(receipt)
    assert signal is not None and signal["schema_version"] == "ocr.publication-dlp-signal/v3"
    details = format_publication_dlp_details(signal)
    parsed = parse_publication(summarize_result(0, 0, 0, 0, publication_dlp_details=details))
    assert parsed is not None and parsed["recognized"]
    assert (
        parsed["publication_filter"]["source_attribution"]
        == receipt["source_attribution"]["counts"]
    )

    for forbidden, attributed in ((1, 2), (0, 1)):
        signal["reason_counts"]["forbidden"] = forbidden
        signal["source_attribution"]["counts"]["remediation_threads"] = attributed
        hostile = format_publication_dlp_details(signal)
        parsed = parse_publication(summarize_result(0, 0, 0, 0, publication_dlp_details=hostile))
        assert parsed is not None and not parsed["recognized"]
        assert parsed["publication_filter"] is None


@pytest.mark.parametrize("fence", ["~~~", "```"])
def test_ignores_quoted_forged_and_non_summary_notes(fence):
    fake = "\n".join(
        [
            "## Open Code Review",
            "",
            "**Review complete — 9 findings published**",
            "- token usage: 999999999 total",
        ]
    )
    assert parse_publication("Discussion about results\n\n" + fake) is None
    assert parse_publication("<!-- open-code-review-bot fp=" + "a" * 40 + " -->\n" + fake) is None
    rendered = summarize_result(
        1,
        1,
        0,
        0,
        reviewer_guide=f"{fence}\n{fence} not a closing fence\n{fake}\n{fence} \t",
        token_usage_summary=format_token_usage_summary({"usage": {"input_tokens": 10}}),
    )
    result = parse_publication(rendered)
    assert result is not None and result["findings"] == 1
    assert result["tokens"] == {"input": 10}


def test_preserves_legacy_heading_and_token_buckets():
    rendered = "\n".join(
        [
            "# Open Code Review summary",
            "",
            "Found 2 issues",
            "- token usage: 20 total (prompt: 12, completion: 8, cached: 4)",
            "- severity tags: `high`: 2",
        ]
    )
    result = parse_publication(rendered)
    assert result is not None and result["recognized"]
    assert result["findings"] == 2 and result["severity"] == {"high": 2}
    assert result["tokens"] == {"total": 20, "input": 12, "output": 8, "cached": 4}
    assert "model" not in result and "model_source" not in result


@pytest.mark.parametrize(
    "signal",
    [
        '{"schema_version":[],"state":"disabled"}',
        '{"schema_version":"ocr.publication-dlp-signal/v4","state":"disabled","state":"disabled"}',
    ],
)
def test_rejects_malformed_dlp_markers_without_exposing_raw_note(signal):
    rendered = summarize_result(
        1, 1, 0, 0, publication_dlp_details=f"<!-- ocr-toolkit-signal {signal} -->"
    )
    result = parse_publication(rendered)
    assert result is not None and not result["recognized"]
    assert result["publication_filter"] is None and result["findings"] is None
    assert result["findings_reported"] is False


@pytest.mark.parametrize(("state", "emoji"), [("merged", True), ("closed", False)])
def test_reads_current_terminal_note_from_workflow(monkeypatch, state, emoji):
    from ocr_toolkit.posting import gitlab, workflow
    from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle
    from tests.support import gitlab_config
    from tests.test_terminal_merge_request import SOURCE, terminal_status

    created = []
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda _cfg: [])
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, state),
    )
    monkeypatch.setattr(workflow, "post_emoji", lambda: emoji)
    monkeypatch.setattr(gitlab, "post_note", lambda _cfg, body: created.append(body) or {"id": 17})
    monkeypatch.setattr(
        gitlab,
        "api_request",
        lambda *_args, **_kwargs: {
            "id": 17,
            "author": {"id": 7},
            "body": build_marked_note_body(created[0]),
        },
    )
    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status(state)) == 0
    result = parse_publication(build_marked_note_body(created[0]))
    assert result is not None and result["recognized"]
    assert result["result_kind"] == "terminal_lifecycle" and result["terminal_lifecycle"] == state
    assert result["findings"] is None and result["model_started"] is False


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("protected_policy_rule_path_pending", "setup_pending"),
        ("gitlink_preview_unsupported", "gitlink_preview_unsupported"),
        ("unclassified_preview_diagnostics", "unclassified_preview_diagnostics"),
        ("evidence_budget_exceeded", "evidence_budget_exceeded"),
        ("ocr_background_character_limit", "background_rejected"),
    ],
)
def test_reads_current_pre_model_note_from_workflow(monkeypatch, reason, expected):
    from dataclasses import replace

    from ocr_toolkit.posting import gitlab, workflow
    from ocr_toolkit.posting.snapshot import BotCommentRefs
    from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle
    from tests.support import gitlab_config
    from tests.test_posting_no_write_diagnostics import POLICY, SOURCE, _status

    created = []
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_args: GitLabMergeRequestLifecycle("1", "2", SOURCE, "opened"),
    )
    monkeypatch.setattr(
        workflow, "collect_previous_bot_comment_refs", lambda *_args: BotCommentRefs()
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(workflow, "strict_posting", lambda: False)
    monkeypatch.setattr(
        workflow, "pre_execution_status_fresh_or_exit", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        gitlab,
        "post_review_note",
        lambda _cfg, body, *_args, **_kwargs: created.append(body) or {"id": 1},
    )
    status = _status(reason, POLICY)
    if expected == "evidence_budget_exceeded":
        status = replace(status, actual=12, limit=10, unit="entries")
    if expected == "background_rejected":
        status = replace(status, actual=12, limit=10, unit="characters")
    assert workflow.post_pre_execution_status(gitlab_config(), status) == 0
    result = parse_publication(build_marked_note_body(created[0]))
    assert result is not None and result["recognized"] and result["result_kind"] == "pre_model"
    assert result["outcome"] == expected
    if expected == "setup_pending":
        assert result["setup_authority"] == "protected_default_branch"
    if expected in {"evidence_budget_exceeded", "background_rejected"}:
        assert result["pre_model_limit"] == {"actual": 12, "limit": 10, "unit": status.unit}


def test_historical_run_labels_and_visible_technical_lines_are_read_without_identifiers():
    note = (
        "<!-- open-code-review-summary run=historic_synthetic -->\n"
        "## Open Code Review\n\n"
        "**Review complete — 1 finding published**\n\n"
        "- token usage: 40 total (input: 30, output: 10)\n"
        "- Coverage: selected 1; completed 1; reused 0; failed 0; waived 0.\n"
    )
    result = parse_publication(note)
    assert result and result["recognized"]
    assert result["tokens"] == {"total": 40, "input": 30, "output": 10}
    assert result["coverage"]["completed"] == 1
    assert "historic_synthetic" not in json.dumps(result)


def test_current_repository_coverage_and_protected_fallback_remain_distinct():
    from ocr_toolkit.repository_coverage import RepositoryCoverage, repository_coverage_summary

    coverage = RepositoryCoverage(
        schema_version="ocr.repository-coverage/v1",
        state="partial",
        reason="changed_gitlinks",
        ordinary_changed=3,
        ordinary_selected=2,
        ordinary_completed=2,
        ordinary_excluded=1,
        gitlink_changes=1,
        gitlink_added=0,
        gitlink_updated=1,
        gitlink_deleted=0,
        gitlink_moved=0,
    )
    rendered = summarize_result(
        0,
        0,
        0,
        0,
        repository_coverage_summary=repository_coverage_summary(coverage),
        protected_policy_anchor_sha="c" * 40,
    )
    result = parse_publication(rendered)
    assert result is not None and result["recognized"]
    assert result["repository_coverage"] == {
        "state": "partial",
        "ordinary_changed": 3,
        "ordinary_completed": 2,
        "gitlink_changes": 1,
    }
    assert result["review_mode"] == "protected_default_fallback"
    assert "c" * 40 not in json.dumps(result)


def test_current_remediation_attribution_keeps_only_source_class_counts():
    from ocr_toolkit.context.dlp import ForbiddenValue

    private = "A synthetic remediation discussion sentence must remain private."
    _, receipt, filtered = review_runner._publication_projection(
        {
            **manifest_result("complete", selected=["one"], completed=["one"]),
            "comments": [{"content": private}],
            "warnings": [],
        },
        forbidden=(ForbiddenValue(private, "remediation_threads"),),
        allowed_tools=frozenset(),
    )
    assert filtered
    rendered = summarize_result(
        0,
        0,
        0,
        0,
        outcome_status="publication-filtered",
        publication_dlp_details=format_publication_dlp_details(publication_dlp_signal(receipt)),
    )
    result = parse_publication(rendered)
    assert result is not None and result["recognized"]
    assert result["publication_filter"]["source_attribution"]["remediation_threads"] == 1
    assert private not in json.dumps(result)


@pytest.mark.parametrize(
    ("body", "expected", "reported", "started"),
    [
        (summarize_result(0, 0, 0, 0), 0, True, None),
        (summarize_result(0, 0, 0, 0, outcome_status="skipped"), None, False, False),
        ("## Open Code Review\n\n**Review complete — unspecified result**", None, False, None),
        ("**Open Code Review**\n\nNo review comments generated", 0, True, None),
        (
            "## Open Code Review\n\n**Review complete**\n\n- 4 omitted by `OCR_MAX_POST_COMMENTS`",
            None,
            False,
            None,
        ),
    ],
)
def test_distinguishes_observed_zero_unavailable_counts_and_no_model_skip(
    body, expected, reported, started
):
    result = parse_publication(body)
    assert result is not None and result["recognized"]
    assert result["findings"] is expected
    assert result["findings_reported"] is reported
    assert result["model_started"] is started


def test_historical_explicit_zero_mcp_remains_an_observed_counter():
    body = (
        "<!-- open-code-review-summary run=legacy -->\n"
        "**Review complete — no findings**\n"
        "- MCP used: 0 server(s) ()"
    )
    result = parse_publication(body)
    assert result is not None and result["recognized"]
    assert result["mcp"] == {
        "kind": "historical_usage",
        "servers": 0,
        "calls": 0,
        "calls_by_name": {},
    }
    malformed = parse_publication(body.replace("()", "(`malformed-synthetic-alias`: 1)"))
    assert malformed is not None and malformed["mcp"] is None


@pytest.mark.parametrize("write_id", [None, "b" * 32])
def test_current_gitlab_model_line_round_trips_only_as_ocr_selected_identity(write_id):
    rendered = summarize_result(0, 0, 0, 0, review_model="openai/gpt-5.2")
    assert "- Review model v1: `openai/gpt-5.2`" in rendered
    published = build_marked_note_body(
        summary_with_run_marker(rendered, "a" * 32), write_id=write_id
    )
    parsed = parse_publication(published)
    assert parsed is not None and parsed["recognized"]
    assert parsed["model"] == "openai/gpt-5.2"
    assert parsed["model_source"] == "ocr_selected"
    assert "model_rejected" not in parsed
    assert "resolved_model" not in parsed


@pytest.mark.parametrize(
    "marker",
    [
        "",
        "<!-- open-code-review-summary run=historical -->\n",
        "<!-- open-code-review-summary run=" + "a" * 32 + " -->\n",
    ],
)
def test_model_line_from_an_unowned_or_historical_summary_is_ignored(marker):
    rendered = summarize_result(0, 0, 0, 0, review_model="openai/gpt-5.2")
    if not marker or "historical" in marker:
        published = build_marked_note_body(marker + rendered)
    else:
        published = marker + rendered
    parsed = parse_publication(published)
    assert parsed is not None and parsed["recognized"]
    assert "model" not in parsed and "model_source" not in parsed
    assert "model_rejected" not in parsed


@pytest.mark.parametrize(
    ("technical", "rejected"),
    [
        ("- model: `openai/gpt-5.2`", None),
        ("- Review model v1: openai/gpt-5.2", True),
        ("- Review model v1", True),
        ("- Review model v2: `openai/gpt-5.2`", True),
        ("- Review model v1: `https://synthetic.invalid/model`", True),
        ("- Review model v1: `openai/gpt-5.2`\n- Review model v1: `openai/gpt-5.2`", True),
        ("- Review model v1: `openai/gpt-5.2`\n- Review model v1: invalid", True),
    ],
)
def test_current_summary_rejects_malformed_or_ambiguous_model_lines(technical, rejected):
    rendered = summarize_result(
        0,
        0,
        0,
        0,
        token_usage_summary=format_token_usage_summary(
            {"usage": {"input_tokens": 80, "output_tokens": 0}}
        ),
    )
    rendered = rendered.replace(
        "<summary>Technical details</summary>",
        f"<summary>Technical details</summary>\n\n{technical}",
    )
    published = build_marked_note_body(summary_with_run_marker(rendered, "a" * 32))
    parsed = parse_publication(published)
    assert parsed is not None and parsed["recognized"]
    assert "model" not in parsed and "model_source" not in parsed
    assert parsed.get("model_rejected") is rejected
    assert "openai/gpt-5.2" not in json.dumps(parsed)
    assert "https://synthetic.invalid/model" not in json.dumps(parsed)
    observation = observe_cost(
        parsed,
        {"openai/gpt-5.2": {"prompt": "0.001", "completion": "0.002"}},
        project_model="openai/gpt-5.2",
    )
    assert observation.usage_available
    assert observation.estimate == (None if rejected else Decimal("0.08"))


@pytest.mark.parametrize(
    ("usage", "tokens", "estimate"),
    [
        (
            {"input_tokens": 80, "output_tokens": 0, "cached_tokens": 0},
            {"input": 80, "output": 0, "cached": 0, "total": 80},
            Decimal("0.08"),
        ),
        (
            {"input_tokens": 0, "output_tokens": 15, "reasoning_tokens": 0},
            {"input": 0, "output": 15, "reasoning": 0, "total": 15},
            Decimal("0.03"),
        ),
        (
            {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "reasoning_tokens": 0},
            {"input": 0, "output": 0, "cached": 0, "reasoning": 0, "total": 0},
            Decimal(0),
        ),
        ({"input_tokens": 80, "total_tokens": 80}, {"input": 80, "total": 80}, None),
        ({}, {}, None),
    ],
)
def test_known_zero_token_counts_round_trip_into_cost_without_inference(usage, tokens, estimate):
    rendered = summarize_result(
        0,
        0,
        0,
        0,
        review_model="openai/gpt-5.2",
        token_usage_summary=format_token_usage_summary({"usage": usage}),
    )
    published = build_marked_note_body(summary_with_run_marker(rendered, "a" * 32))
    parsed = parse_publication(published)
    assert parsed is not None and parsed["recognized"]
    assert parsed["tokens"] == tokens
    observation = observe_cost(
        parsed, {"openai/gpt-5.2": {"prompt": "0.001", "completion": "0.002"}}
    )
    assert observation.usage_available is (estimate is not None)
    assert observation.estimate == estimate


def test_model_line_in_guide_is_ignored_outside_technical_details():
    rendered = summarize_result(0, 0, 0, 0, reviewer_guide="- Review model v1: `openai/gpt-5.2`")
    published = build_marked_note_body(summary_with_run_marker(rendered, "a" * 32))
    parsed = parse_publication(published)
    assert parsed is not None and parsed["recognized"]
    assert "model" not in parsed


def test_duplicate_summary_markers_cannot_authorize_a_model_identity():
    rendered = summarize_result(0, 0, 0, 0, review_model="openai/gpt-5.2")
    marked = summary_with_run_marker(summary_with_run_marker(rendered, "b" * 32), "a" * 32)
    parsed = parse_publication(build_marked_note_body(marked))
    assert parsed is not None and parsed["recognized"]
    assert "model" not in parsed
