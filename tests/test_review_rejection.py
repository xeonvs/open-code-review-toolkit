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
from tests.test_review_runner import BUILTIN_EVIDENCE_TOOLS, DEFAULT_IDENTITY


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
        (None, None),
        ({"total": 0, "by_tool": {}}, 0),
        ({"total": 0, "by_tool": {"ocr_toolkit_evidence": 0}}, 0),
        ({"total": 1, "by_tool": {"read_file": 1}}, None),
    ],
)
@pytest.mark.parametrize("retain", [False, True])
def test_rejected_result_preserves_only_authorized_private_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    status: str,
    telemetry: dict[str, object] | None,
    expected: int | None,
    retain: bool,
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
            private_diagnostics=retain,
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
    assert result.exists() is retain
    if retain:
        assert result.stat().st_mode & 0o777 == 0o600
        retained = ocr_result.load_ocr_result(result)
        assert (
            retained[ocr_result.TOOLKIT_PRIVATE_DIAGNOSTIC_KEY]["reason"]
            == "evidence-use-unconfirmed"
        )
        assert ocr_result.TOOLKIT_RESULT_KEY not in retained
        assert retained["result"]["message"] == "private operator content"


@pytest.mark.parametrize(
    "telemetry",
    [
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


def test_retention_failure_preserves_original_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed atomic replacement must neither mask rejection nor leave adoptable raw data."""
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"status": "success", "tool_calls": {"total": 0, "by_tool": {}}}))
    transform = review_runner.transform_ocr_result
    attempts = 0

    def fail_retention(path: Path, callback: object) -> object:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise ocr_result.OcrResultMissing("private failure details")
        return transform(path, callback)

    monkeypatch.setattr(review_runner, "transform_ocr_result", fail_retention)
    with pytest.raises(review_runner.ReviewRejected, match="evidence-use-unconfirmed"):
        review_runner._finalize_ocr_result(
            result,
            composition(),
            DEFAULT_IDENTITY,
            None,
            forbidden=(),
            private_diagnostics=True,
        )
    output = capsys.readouterr().err
    assert "retention failed" in output
    assert "private failure details" not in output
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
    """Cross real loader and posting owner; replace only external failure-note delivery."""
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
    assert code == int(strict)
    assert len(notes) == 1
    assert "not publication-eligible" in notes[0][2]
    assert "must not publish" not in notes[0][2]
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
            private_diagnostics=True,
        )
    assert caught.value.reason == "evidence-action-attribution-invalid"
    assert caught.value.calls == 1
    assert (
        ocr_result.load_ocr_result(result)[ocr_result.TOOLKIT_PRIVATE_DIAGNOSTIC_KEY]["reason"]
        == caught.value.reason
    )


def test_no_work_private_retention_still_has_no_publication_authority(tmp_path: Path) -> None:
    """Legitimate skipped work is accepted for diagnosis without a provider receipt."""
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "skipped",
                "message": "No supported files changed.",
                "comments": [],
                "tool_calls": {"total": 0, "by_tool": {}},
            }
        )
    )
    reports = []
    review_runner._finalize_ocr_result(
        result,
        composition(),
        DEFAULT_IDENTITY,
        None,
        forbidden=(),
        private_diagnostics=True,
        report_consumer=reports.append,
    )
    assert not reports
    retained = ocr_result.load_ocr_result(result)
    assert retained["status"] == "skipped"
    assert retained[ocr_result.TOOLKIT_PRIVATE_DIAGNOSTIC_KEY]["reason"] == "private-retention"
    assert ocr_result.TOOLKIT_RESULT_KEY not in retained


def test_valid_summary_receipt_allows_private_review_without_admitting_report(
    tmp_path: Path,
) -> None:
    """Real private action attribution satisfies validation but grants no publication authority."""
    from ocr_toolkit.evidence.actions import read_action_receipt, record_action

    receipt = tmp_path / "actions.json"
    record_action(receipt, "summary")
    record_action(receipt, "summary", completed=True)
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "comments": [],
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
            }
        )
    )
    reports = []
    review_runner._finalize_ocr_result(
        result,
        composition(),
        DEFAULT_IDENTITY,
        None,
        read_action_receipt(receipt),
        forbidden=(),
        private_diagnostics=True,
        report_consumer=reports.append,
    )
    retained = ocr_result.load_ocr_result(result)
    assert retained["status"] == "success"
    assert retained[ocr_result.TOOLKIT_PRIVATE_DIAGNOSTIC_KEY]["reason"] == "private-retention"
    assert ocr_result.TOOLKIT_RESULT_KEY not in retained
    assert not reports
