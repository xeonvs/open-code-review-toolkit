"""Private debug storage crosses real filesystem bounds and hostile targets."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from ocr_toolkit import cli, review_debug, review_runner
from ocr_toolkit.ocr_result import PUBLIC_REVIEW_TOOL_CALL_NAMES
from ocr_toolkit.review_debug import DebugBundle


def test_fresh_private_bundle_and_explicit_not_run(tmp_path: Path) -> None:
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        bundle.phase("configuration", "passed", facts={"provider": "local"})
        bundle.flush()
        document = json.loads((bundle.directory / "journal.json").read_bytes())
        assert document["schema_version"] == review_debug.DEBUG_SCHEMA
        assert document["complete"] is False
        assert document["phases"]["configuration"] == {
            "status": "passed",
            "facts": {"provider": "local"},
        }
        assert document["phases"]["mcp-use"] == {"status": "not-run"}
        assert document["artifacts"]["raw-result.json"]["status"] == "not-run"
        assert bundle.directory.stat().st_mode & 0o777 == 0o700
        assert (bundle.directory / "journal.json").stat().st_mode & 0o777 == 0o600
    finally:
        bundle.close()
        bundle.close()


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_bundle_rejects_existing_target(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "debug"
    if kind == "directory":
        destination.mkdir()
    elif kind == "file":
        destination.write_text("caller data")
    else:
        destination.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises((ValueError, FileExistsError)):
        DebugBundle(destination, other_outputs=())
    assert destination.exists()


def test_bundle_rejects_overlapping_outputs(tmp_path: Path) -> None:
    destination = tmp_path / "debug"
    with pytest.raises(ValueError, match="outside"):
        DebugBundle(destination, other_outputs=(destination / "raw-result.json",))
    assert not destination.exists()


def test_bounded_raw_capture_records_prefix_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(review_debug.ARTIFACT_LIMITS, "raw-result.json", 9)
    source = tmp_path / "raw.json"
    raw = "界".encode() * 4
    source.write_bytes(raw)
    bundle = DebugBundle(tmp_path / "debug", other_outputs=(source,))
    try:
        bundle.capture("raw-result.json", source)
        assert (bundle.directory / "raw-result.json").read_bytes() == raw[:9]
        assert bundle.artifacts["raw-result.json"] == {
            "status": "degraded",
            "limit_bytes": 9,
            "captured_bytes": 9,
            "source_bytes_observed": 12,
            "sha256_captured": hashlib.sha256(raw[:9]).hexdigest(),
            "truncated": True,
            "source_changed": False,
        }
    finally:
        bundle.close()


@pytest.mark.parametrize("kind", ["missing", "symlink", "hardlink", "fifo", "directory"])
def test_unavailable_capture_is_explicit(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    original = tmp_path / "original"
    original.write_text("private content")
    if kind == "symlink":
        source.symlink_to(original)
    elif kind == "hardlink":
        source.hardlink_to(original)
    elif kind == "fifo":
        os.mkfifo(source)
    elif kind == "directory":
        source.mkdir()
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        bundle.capture("raw-result.json", source)
        expected = "missing" if kind == "missing" else "unavailable"
        assert bundle.artifacts["raw-result.json"]["status"] == expected
        assert not (bundle.directory / "raw-result.json").exists()
    finally:
        bundle.close()


def test_directory_swap_never_writes_to_replacement(tmp_path: Path) -> None:
    destination = tmp_path / "debug"
    bundle = DebugBundle(destination, other_outputs=())
    destination.rename(tmp_path / "moved")
    destination.mkdir()
    try:
        with pytest.raises(OSError, match="identity"):
            bundle.flush()
        assert list(destination.iterdir()) == []
    finally:
        bundle.close()


def test_value_free_decisions_and_event_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(review_debug, "MAX_DEBUG_DECISIONS", 1)
    monkeypatch.setattr(review_debug, "MAX_DEBUG_TRANSITIONS", 1)
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        for _ in range(3):
            bundle.phase("dlp", "degraded")
            bundle.decision(
                path=("comments", 0, "private-key@example.invalid"),
                action="omit-field",
                reason="pii",
                detector="email",
                value="private-value@example.invalid",
            )
        bundle.flush()
        text = (bundle.directory / "journal.json").read_text()
        assert "private-key" not in text and "private-value" not in text
        document = json.loads(text)
        assert document["omitted_decisions"] == document["omitted_transitions"] == 2
        assert len(document["dlp_decisions"]) == len(document["transitions"]) == 1
    finally:
        bundle.close()


def test_journal_rejects_open_or_oversized_fact_values(tmp_path: Path) -> None:
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        for facts in ({"token": "private"}, {"provider": "x" * 65}, {"provider": ["local"]}):
            with pytest.raises(ValueError, match="closed"):
                bundle.phase("configuration", "passed", facts=facts)
        assert bundle.phases["configuration"] == {"status": "not-run"}
    finally:
        bundle.close()


@pytest.mark.parametrize("private_field", [False, True])
def test_debug_observes_actual_dlp_without_extra_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, private_field: bool
) -> None:
    payload: dict[str, object] = {
        "status": "success",
        "comments": [{"path": "app.py", "line": 1, "content": "Check the boundary."}],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
    }
    if private_field:
        payload["private_detail"] = "synthetic@example.invalid"
    else:
        payload["warnings"] = ["Contact synthetic@example.invalid"]
    calls = 0
    original = review_runner.check_text

    def counted(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(review_runner, "check_text", counted)
    normal = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=PUBLIC_REVIEW_TOOL_CALL_NAMES
    )
    normal_calls = calls
    calls = 0
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        debug = review_runner._publication_projection(
            payload, forbidden=(), allowed_tools=PUBLIC_REVIEW_TOOL_CALL_NAMES, debug=bundle
        )
        assert debug == normal and calls == normal_calls
        assert bundle.decisions
        assert any(
            item["action"] == ("redact-value" if private_field else "omit-warning")
            for item in bundle.decisions
        )
        bundle.flush()
        assert "synthetic@example.invalid" not in (bundle.directory / "journal.json").read_text()
    finally:
        bundle.close()


def test_early_configuration_failure_records_not_run_and_no_source_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OCR_REVIEW_CONTEXT_MODE", "metadata")
    result = tmp_path / "result.json"
    result.write_text("caller-owned old result")
    directory = tmp_path / "debug"
    assert (
        cli.main(
            [
                "review",
                "--local",
                "--result",
                str(result),
                "--stderr",
                str(tmp_path / "stderr"),
                "--debug-dir",
                str(directory),
            ]
        )
        == 2
    )
    document = json.loads((directory / "journal.json").read_text())
    assert document["complete"] is True
    assert document["phases"]["configuration"]["status"] == "failed"
    assert document["phases"]["subprocess"]["status"] == "not-run"
    assert document["phases"]["reporting"] == {
        "status": "passed",
        "facts": {"report_artifact": False, "console": True},
    }
    assert document["artifacts"]["raw-result.json"]["status"] == "not-run"
    assert result.read_text() == "caller-owned old result"
    console = capsys.readouterr().out
    assert "caller-owned" not in console
    assert (directory / "summary.md").read_text() == console


@pytest.mark.parametrize("local", [False, True])
def test_debug_rejects_nonlocal_or_legacy_retention_before_io(tmp_path: Path, local: bool) -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="without legacy retention"):
        review_runner.run_evidence_review(
            tmp_path / "result",
            tmp_path / "stderr",
            [],
            local=local,
            preserve_private_artifacts=local,
            debug_dir=tmp_path / "debug",
        )
    assert list(tmp_path.iterdir()) == []


def test_summary_capture_stops_at_byte_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(review_debug.ARTIFACT_LIMITS, "summary.md", 4)
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())

    def parts():
        yield "界界"
        pytest.fail("rendering continued beyond capture bound")

    try:
        bundle.capture_parts("summary.md", parts())
        assert (bundle.directory / "summary.md").read_bytes() == "界界".encode()[:4]
        assert bundle.artifacts["summary.md"]["truncated"] is True
        assert bundle.artifacts["summary.md"]["source_bytes_observed"] is None
    finally:
        bundle.close()


def test_journal_limit_preserves_incomplete_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        bundle.flush()
        original = (bundle.directory / "journal.json").read_bytes()
        monkeypatch.setattr(review_debug, "MAX_DEBUG_JOURNAL_BYTES", 1)
        with pytest.raises(ValueError, match="byte limit"):
            bundle.flush(complete=True)
        assert (bundle.directory / "journal.json").read_bytes() == original
        assert json.loads(original)["complete"] is False
    finally:
        bundle.close()


def test_late_debug_write_failure_preserves_original_review_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original_write = DebugBundle._write
    writes = 0

    def fail_after_initial(self: DebugBundle, name: str, content: bytes) -> None:
        nonlocal writes
        writes += 1
        if writes > 1:
            raise OSError("private diagnostic path")
        original_write(self, name, content)

    monkeypatch.setattr(DebugBundle, "_write", fail_after_initial)
    monkeypatch.setenv("OCR_REVIEW_CONTEXT_MODE", "metadata")
    directory = tmp_path / "debug"
    with pytest.raises(review_runner.ReviewRunnerError, match="change-request context"):
        review_runner.run_evidence_review(
            tmp_path / "result", tmp_path / "stderr", [], local=True, debug_dir=directory
        )
    output = capsys.readouterr()
    assert "Local debug journal output failed" in output.err
    assert "private diagnostic path" not in output.err + output.out
    assert json.loads((directory / "journal.json").read_text())["complete"] is False


def test_empty_finding_projection_is_not_reported_as_unsafe_content(tmp_path: Path) -> None:
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        review_runner._publication_projection(
            {
                "status": "success",
                "comments": [{}],
                "warnings": ["Contact synthetic@example.invalid"],
            },
            forbidden=(),
            allowed_tools=PUBLIC_REVIEW_TOOL_CALL_NAMES,
            debug=bundle,
        )
        removed = [item for item in bundle.decisions if item["action"] == "omit-finding"]
        assert len(removed) == 1 and removed[0]["reason"] == "empty_projection"
    finally:
        bundle.close()
