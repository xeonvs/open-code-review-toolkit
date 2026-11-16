"""Prove rejection diagnostics, private retention, and posting admission boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit import ocr_result, review_runner
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.posting import workflow
from tests.support import gitlab_config
from tests.test_review_runner import BUILTIN_EVIDENCE_TOOLS, DEFAULT_IDENTITY, SUMMARY_ACTION_COUNTS


def composition() -> MCPComposition:
    """Build a ready composition without synthesizing any model evidence use."""
    return MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),),
        external_servers=(),
        secret_values=(),
    )


@pytest.mark.parametrize("status", ["success", "completed_with_warnings", "completed_with_errors"])
@pytest.mark.parametrize(
    ("telemetry", "expected"),
    [
        ({"total": 0, "by_tool": {}}, 0),
        ({"total": 0, "by_tool": {"ocr_toolkit_evidence": 0}}, 0),
        ({"total": 1, "by_tool": {"file_read": 1}}, 0),
        ({"total": 1, "by_tool": {"context_get": 1}}, 0),
        ({"total": 1, "by_tool": {"ocr_toolkit_evidence_search": 1}}, 0),
    ],
)
def test_rejected_result_discards_unadmitted_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    status: str,
    telemetry: dict[str, object] | None,
    expected: int | None,
) -> None:
    """Enter real atomic finalization and hostile readback before posting rejection."""
    result = tmp_path / "result.json"
    raw = {"status": status, "comments": [], "message": "private operator content"}
    if telemetry is not None:
        raw["tool_calls"] = telemetry
    result.write_text(json.dumps(raw), encoding="utf-8")
    reports = []
    with pytest.raises(review_runner.ReviewRejected) as caught:
        review_runner._finalize_ocr_result(
            result,
            composition(),
            replace(DEFAULT_IDENTITY, mr_author_id=None),
            None,
            forbidden=(),
            report_consumer=reports.append,
        )
    assert caught.value.reason == "evidence-use-unconfirmed"
    assert caught.value.calls == expected
    assert not reports
    output = capsys.readouterr().err
    assert "Review rejected:" in output
    assert "private operator content" not in output
    assert str(tmp_path) not in output
    assert ("reported calls: unavailable" if expected is None else "reported calls: 0") in output
    assert not result.exists()


def native_payload() -> dict[str, object]:
    """Build the reported coverage shape without private source or identifiers."""
    items = [{"item_id": f"synthetic-{index}"} for index in range(408)]
    return {
        "status": "complete",
        "comments": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": items,
                "completed": items,
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }


@pytest.mark.parametrize(
    "status", ["success", "completed_with_warnings", "completed_with_errors", "complete"]
)
@pytest.mark.parametrize("actions", [None, SUMMARY_ACTION_COUNTS])
def test_missing_telemetry_is_an_unexpected_contract(tmp_path, capsys, status, actions):
    payload = native_payload() if status == "complete" else {"status": status, "comments": []}
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    with pytest.raises(review_runner.UnexpectedResultContract) as caught:
        review_runner._finalize_ocr_result(
            result, composition(), DEFAULT_IDENTITY, None, actions, forbidden=(), ocr_exit_code=0
        )
    assert caught.value.reason == "unexpected-result-contract"
    assert caught.value.detail == "missing-tool-calls"
    output = capsys.readouterr().err
    assert "tool_calls=missing" in output and "ocr_exit_code=0" in output
    assert "reported_evidence_calls=unavailable" in output
    assert f"summary_receipt={'available' if actions is not None else 'unavailable'}" in output
    assert "evidence-use-unconfirmed" not in str(caught.value)
    assert not result.exists()


def test_native_only_calls_are_not_missing_telemetry(tmp_path, capsys):
    payload = native_payload()
    payload["tool_calls"] = {"total": 213, "by_tool": {"file_read": 213}}
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    with pytest.raises(review_runner.ReviewRejected) as caught:
        review_runner._finalize_ocr_result(
            result, composition(), DEFAULT_IDENTITY, None, forbidden=()
        )
    assert caught.value.reason == "evidence-use-unconfirmed"
    assert caught.value.calls == 0
    output = capsys.readouterr().err
    assert "Coverage: selected 408; completed 408" in output
    assert "tool_calls=present" in output
    assert "reported_total=213 reported_evidence_calls=0" in output
    assert not result.exists()


def test_early_manifest_failure_keeps_primary_error_and_closed_facts(tmp_path, capsys):
    from ocr_toolkit.review_range import ReviewRange

    result = tmp_path / "result.json"
    payload = native_payload()
    payload["private-key\nsecret-value"] = "private-value"
    result.write_text(json.dumps(payload))
    with pytest.raises(review_runner.ReviewRunnerError, match="native manifest did not prove"):
        review_runner._finalize_ocr_result(
            result,
            composition(),
            DEFAULT_IDENTITY,
            None,
            forbidden=(),
            expected_range=ReviewRange(DEFAULT_IDENTITY.diff_base_sha, DEFAULT_IDENTITY.source_sha),
        )
    output = capsys.readouterr().err
    assert "status=complete" in output and "manifest=present tool_calls=missing" in output
    assert "unknown_keys=1" in output
    assert "private" not in output and "secret" not in output
    assert not result.exists()


@pytest.mark.parametrize("error_type", [OSError, BrokenPipeError, ValueError])
def test_failed_stderr_cannot_replace_rejection_or_skip_cleanup(tmp_path, monkeypatch, error_type):
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"status": "success", "tool_calls": {"total": 0, "by_tool": {}}}))

    class FailedSink:
        def write(self, _text):
            raise error_type("synthetic diagnostic sink failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(review_runner.sys, "stderr", FailedSink())
        with pytest.raises(review_runner.ReviewRejected) as caught:
            review_runner._finalize_ocr_result(
                result, composition(), DEFAULT_IDENTITY, None, forbidden=()
            )
    assert caught.value.reason == "evidence-use-unconfirmed"
    assert not result.exists()


def test_failed_diagnostic_formatting_keeps_original_rejection(tmp_path, monkeypatch):
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"status": "success"}))

    def fail(_self):
        raise RuntimeError("synthetic formatting failure")

    monkeypatch.setattr(review_runner.ResultDiagnostic, "render", fail)
    with pytest.raises(review_runner.UnexpectedResultContract):
        review_runner._finalize_ocr_result(
            result, composition(), DEFAULT_IDENTITY, None, forbidden=()
        )
    assert not result.exists()


@pytest.mark.parametrize(
    "telemetry",
    [
        None,
        [],
        {"total": 0, "by_tool": []},
        {"total": 0, "by_tool": {"ocr_toolkit_evidence": False}},
        {"total": 0, "by_tool": {"ocr_toolkit_evidence": -1}},
    ],
)
def test_malformed_telemetry_remains_separate(tmp_path: Path, telemetry: object) -> None:
    """Malformed counts are never downgraded to missing or zero evidence."""
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"status": "success", "tool_calls": telemetry}))
    with pytest.raises(review_runner.ReviewRunnerError) as caught:
        review_runner._finalize_ocr_result(
            result, composition(), DEFAULT_IDENTITY, None, forbidden=()
        )
    assert not isinstance(caught.value, review_runner.ReviewRejected)
    assert not result.exists()


@pytest.mark.parametrize("reason", ["evidence-use-unconfirmed", "private-retention"])
@pytest.mark.parametrize("strict", ["0", "1"])
def test_private_diagnostic_marker_blocks_receiptless_posting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reason: str,
    strict: str,
) -> None:
    """A private diagnostic remains job-only under both strictness settings."""
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "comments": [{"comment": "must not publish"}],
                ocr_result.TOOLKIT_PRIVATE_DIAGNOSTIC_KEY: {"reason": reason},
            }
        )
    )
    notes = []
    monkeypatch.setenv("OCR_STRICT_POSTING", strict)
    monkeypatch.setattr(
        workflow, "post_review_note_bounded", lambda *args: notes.append(args) or {"id": 1}
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_args: True)
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda *_args: pytest.fail("must not inspect previous comments"),
    )
    monkeypatch.setattr(
        workflow, "execute_approval", lambda *_args, **_kwargs: pytest.fail("must not approve")
    )
    code = workflow.post_results(gitlab_config(), ocr_result.load_ocr_result(result))
    assert code == 1
    assert notes == []
    assert "not publication-eligible" in capsys.readouterr().err


def test_positive_calls_without_summary_keep_distinct_rejection(tmp_path: Path) -> None:
    """A positive model count never replaces mandatory completed action attribution."""
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
            }
        )
    )
    with pytest.raises(review_runner.ReviewRejected) as caught:
        review_runner._finalize_ocr_result(
            result,
            composition(),
            DEFAULT_IDENTITY,
            None,
            forbidden=(),
        )
    assert caught.value.reason == "evidence-action-attribution-invalid"
    assert caught.value.calls == 1
    assert not result.exists()


@pytest.mark.parametrize("error_type", [OSError, RuntimeError])
def test_atomic_finalization_failure_cannot_leave_adoptable_raw_output(
    tmp_path, monkeypatch, error_type
):
    """Discard unadmitted output and preserve the original atomic/callback failure."""
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"status": "success", "message": "private operator content"}))

    def fail_transform(*_args, **_kwargs):
        """Model an actual finalization owner failing before safe replacement."""
        raise error_type("synthetic finalization failure")

    monkeypatch.setattr(review_runner, "transform_ocr_result", fail_transform)
    with pytest.raises(error_type, match="synthetic finalization failure"):
        review_runner._finalize_ocr_result(
            result, composition(), DEFAULT_IDENTITY, None, forbidden=()
        )
    assert not result.exists()
