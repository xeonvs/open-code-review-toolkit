"""Private native traces are bounded projections, never replay or review authority."""

from __future__ import annotations

import json
import os
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit import review_trace
from ocr_toolkit.review_debug import DebugBundle
from ocr_toolkit.review_range import ReviewRange
from ocr_toolkit.review_trace import NativeTraceError, NativeTraceSource

RANGE = ReviewRange("a" * 40, "b" * 40)
SESSION = "00000000-0000-4000-8000-000000000001"
SENTINEL = "synthetic-private-replay-sentinel"


def records(repository: Path) -> list[dict[str, Any]]:
    """Use OCR 1.13.3's distinct response/message call and completion shapes."""

    call = {"id": "call", "name": "file_read_diff", "arguments": '{"paths":["b.py"]}'}
    rows = [
        {
            "type": "session_start",
            "reviewMode": "range",
            "diffFrom": RANGE.base,
            "diffTo": RANGE.head,
            "model": "synthetic-model",
            "cwd": str(repository.resolve()),
            "config": SENTINEL,
        },
        {
            "type": "llm_request",
            "filePath": "a.py",
            "taskType": "main_task",
            "request_no": 1,
            "messages": [
                {"role": "user", "content": "Review frozen diffs", "native_payload": SENTINEL},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call",
                            "type": "function",
                            "function": {"name": call["name"], "arguments": call["arguments"]},
                            "extra_content": SENTINEL,
                        }
                    ],
                    "reasoning_content": SENTINEL,
                },
                {"role": "tool", "tool_call_id": "call", "content": "Frozen cross-group diff"},
            ],
        },
        {
            "type": "llm_response",
            "filePath": "a.py",
            "taskType": "main_task",
            "content": "",
            "tool_calls": [{**call, "extra_content": SENTINEL}],
            "native_payload": SENTINEL,
            "reasoning_content": SENTINEL,
        },
        {
            "type": "tool_call",
            "filePath": "a.py",
            "taskType": "main_task",
            "tool_name": "file_read_diff",
            "arguments": call["arguments"],
            "result": "Error: diff not found",
            "ok": True,
        },
        {
            "type": "llm_error",
            "filePath": "a.py",
            "taskType": "main_task",
            "request_no": 2,
            "error": "Synthetic provider failure",
        },
        {"type": "review_item_failed", "filePath": "a.py", "error": "Synthetic failure"},
        {"type": "session_end", "files_reviewed": ["a.py"], "llm_failures": 1},
    ]
    for index, row in enumerate(rows):
        row.update(
            sessionId=SESSION,
            uuid=f"10000000-0000-4000-8000-{index:012x}",
            parentUuid=rows[index - 1]["uuid"] if index else None,
            timestamp="2026-10-29T12:00:00Z",
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write synthetic upstream JSONL with private permissions."""

    path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))
    path.chmod(0o600)


@pytest.fixture
def native(tmp_path: Path) -> tuple[Path, Path, Path, list[dict[str, Any]]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    home = tmp_path / "session-home"
    home.mkdir(mode=0o700)
    parent = home
    for name in (
        ".opencodereview",
        "sessions",
        str(repository.resolve()).lstrip("/").replace("/", "-"),
    ):
        parent = parent / name
        parent.mkdir(mode=0o700)
    path = parent / f"{SESSION}.jsonl"
    rows = records(repository)
    write_rows(path, rows)
    return home, repository, path, rows


def test_projection_retains_actual_context_without_replay_or_auth(native) -> None:
    home, repository, path, rows = native
    # The source owner has no reason to open native authentication/config files.
    (home / ".opencodereview" / "credentials.json").write_text(SENTINEL)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture()
    assert capture.facts["status"] == "passed"
    assert capture.facts["session_complete"] is True
    assert capture.facts["records_retained"] == len(rows)
    assert SENTINEL.encode() not in capture.content
    projected = [json.loads(line) for line in capture.content.splitlines()]
    assert projected[0]["schema_version"] == review_trace.TRACE_SCHEMA
    assert projected[2]["tool_calls"] == projected[1]["messages"][1]["tool_calls"]
    assert projected[3]["result"] == "Error: diff not found" and projected[3]["ok"] is True
    assert projected[4]["error"] == "Synthetic provider failure"
    assert projected[-1]["files_reviewed"] == ["a.py"]
    assert capture.facts["source_bytes_observed"] == path.stat().st_size
    assert capture.facts["source_changed"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("diffFrom", "c" * 40),
        ("diffTo", "c" * 40),
        ("cwd", "/other"),
        ("reviewMode", "workspace"),
        ("type", "llm_request"),
        ("sessionId", "00000000-0000-4000-8000-000000000002"),
        ("uuid", "invalid"),
        ("parentUuid", SESSION),
        ("model", {}),
    ],
)
def test_unproven_native_identity_rejected(native, field, value) -> None:
    home, repository, path, rows = native
    rows[0][field] = value
    write_rows(path, rows)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        with pytest.raises(NativeTraceError):
            source.capture()


@pytest.mark.parametrize("kind", ["foreign", "chain", "duplicate", "restart", "after-end"])
def test_session_chain_and_order_rejected(native, kind) -> None:
    home, repository, path, rows = native
    if kind == "foreign":
        rows[1]["sessionId"] = "other"
    elif kind == "chain":
        rows[1]["parentUuid"] = None
    elif kind == "duplicate":
        rows[1]["uuid"] = rows[0]["uuid"]
    elif kind == "restart":
        rows[1]["type"] = "session_start"
    else:
        rows[-2]["type"] = "session_end"
    write_rows(path, rows)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        with pytest.raises(NativeTraceError):
            source.capture()


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory", "public"])
def test_hostile_native_files_rejected_without_blocking(native, kind) -> None:
    home, repository, path, _ = native
    original = path.with_suffix(".saved")
    path.rename(original)
    if kind == "symlink":
        path.symlink_to(original)
    elif kind == "hardlink":
        path.hardlink_to(original)
    elif kind == "fifo":
        os.mkfifo(path, mode=0o600)
    elif kind == "directory":
        path.mkdir(mode=0o700)
    else:
        path.write_text("public")
        path.chmod(0o644)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        with pytest.raises((OSError, NativeTraceError)):
            source.capture()


@pytest.mark.parametrize("level", [0, 1, 2])
def test_symlink_source_ancestors_rejected(native, level) -> None:
    home, repository, path, _ = native
    ancestor = path.parents[level]
    moved = ancestor.with_name(ancestor.name + "-moved")
    ancestor.rename(moved)
    ancestor.symlink_to(moved, target_is_directory=True)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        with pytest.raises(OSError):
            source.capture()


@pytest.mark.parametrize("kind", ["missing", "ambiguous", "inventory"])
def test_native_inventory_must_be_bounded_and_unambiguous(native, kind) -> None:
    home, repository, path, _ = native
    if kind == "missing":
        path.unlink()
    elif kind == "ambiguous":
        (path.parent / "00000000-0000-4000-8000-000000000002.jsonl").write_text("")
    else:
        for index in range(review_trace.MAX_DIRECTORY_ENTRIES):
            (path.parent / f"other-{index}").touch()
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        with pytest.raises((FileNotFoundError, NativeTraceError)):
            source.capture()


@pytest.mark.parametrize(
    "tail",
    [b'{"duplicate":1,"duplicate":2}\n', b'{"value":NaN}\n', b"\xff\n", b"{broken\n"],
)
def test_malformed_tail_retains_only_valid_prefix(native, tail) -> None:
    home, repository, path, rows = native
    write_rows(path, rows[:1])
    with path.open("ab") as stream:
        stream.write(tail)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture()
    assert capture.facts["status"] == "degraded"
    assert capture.facts["session_complete"] is False
    assert len(capture.content.splitlines()) == 1


@pytest.mark.parametrize("kind", ["unknown", "type", "surrogate", "end", "no-newline"])
def test_unsupported_records_and_incomplete_session_are_explicit(native, kind) -> None:
    home, repository, path, rows = native
    if kind == "unknown":
        rows[1]["type"] = "future-event"
    elif kind == "type":
        rows[1]["messages"][0]["role"] = []
    elif kind == "surrogate":
        rows[1]["messages"][0]["content"] = "\ud800"
    elif kind == "end":
        rows[-1]["files_reviewed"] = 1
    write_rows(path, rows)
    if kind == "no-newline":
        path.write_bytes(path.read_bytes()[:-1])
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture()
    assert capture.facts["status"] == "degraded"
    assert all(isinstance(json.loads(line), dict) for line in capture.content.splitlines())
    if kind == "end":
        assert capture.facts["session_complete"] is False
    else:
        assert capture.facts["session_complete"] is True


@pytest.mark.parametrize("bound", ["output", "source", "record", "count"])
def test_streaming_limits_retain_complete_json_records(native, monkeypatch, bound) -> None:
    home, repository, path, _rows = native
    header_size = len(path.read_bytes().splitlines(keepends=True)[0])
    if bound == "source":
        monkeypatch.setattr(review_trace, "MAX_SOURCE_BYTES", header_size + 1)
    elif bound == "record":
        monkeypatch.setattr(review_trace, "MAX_RECORD_BYTES", header_size + 1)
    elif bound == "count":
        monkeypatch.setattr(review_trace, "MAX_RECORDS", 1)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture(max_output_bytes=header_size if bound == "output" else 20_000_000)
    assert capture.facts["status"] == "degraded"
    assert capture.facts["truncated"] is True
    assert capture.facts["session_complete"] is False
    assert len(capture.content.splitlines()) == 1


def test_pinned_session_home_survives_path_replacement_and_closes(native) -> None:
    home, repository, _, _ = native
    source = NativeTraceSource(home, repository, RANGE)
    home.rename(home.with_name("original-home"))
    home.mkdir(mode=0o700)
    try:
        assert source.capture().facts["status"] == "passed"
        assert list(home.iterdir()) == []
    finally:
        source.close()
        source.close()
    with pytest.raises(NativeTraceError, match="closed"):
        source.capture()


def test_debug_capture_failure_is_advisory(native, tmp_path) -> None:
    home, repository, path, _ = native
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        bundle.bind_native_session(home, repository, RANGE)
        path.chmod(0o644)
        bundle.capture_native_trace()
        bundle.flush(complete=True)
        journal = json.loads((bundle.directory / "journal.json").read_bytes())
        assert journal["complete"] is True
        assert journal["artifacts"]["native-trace.jsonl"]["status"] == "unavailable"
        assert not (bundle.directory / "native-trace.jsonl").exists()
    finally:
        bundle.close()


@pytest.mark.parametrize("bind", [False, True])
def test_failed_or_absent_binding_keeps_its_diagnostic_state(native, tmp_path, bind) -> None:
    home, repository, _, _ = native
    bundle = DebugBundle(tmp_path / "debug", other_outputs=())
    try:
        if bind:
            home.chmod(0o755)
            bundle.bind_native_session(home, repository, RANGE)
        bundle.capture_native_trace()
        assert bundle.artifacts["native-trace.jsonl"]["status"] == (
            "unavailable" if bind else "not-run"
        )
    finally:
        bundle.close()


@pytest.mark.parametrize("change", ["append", "replace"])
def test_source_changes_cannot_be_reported_as_complete_capture(native, monkeypatch, change) -> None:
    home, repository, path, _ = native
    project = NativeTraceSource._project

    def change_after_read(self, stream, session_id, max_output_bytes):
        result = project(self, stream, session_id, max_output_bytes)
        if change == "replace":
            path.rename(path.with_suffix(".original"))
            path.write_text(SENTINEL)
            path.chmod(0o600)
        else:
            with path.open("ab") as output:
                output.write(SENTINEL.encode())
        return result

    monkeypatch.setattr(NativeTraceSource, "_project", change_after_read)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture()
    assert capture.facts["source_changed"] is True
    assert capture.facts["status"] == "degraded"
    assert SENTINEL.encode() not in capture.content


@pytest.mark.parametrize(
    ("message_field", "value"),
    [
        ("content", {"image_url": "https://example.invalid/private"}),
        ("tool_call_id", 1),
        ("tool_calls", {}),
        ("tool_calls", [None]),
        ("tool_calls", [{"id": "call", "function": {}}]),
        (
            "tool_calls",
            [{"id": "call", "type": "unknown", "function": {"name": "tool", "arguments": "{}"}}],
        ),
    ],
)
def test_message_shape_does_not_copy_unknown_provider_payloads(
    native, message_field, value
) -> None:
    home, repository, path, rows = native
    rows[1]["messages"][0][message_field] = value
    write_rows(path, rows)
    with closing(NativeTraceSource(home, repository, RANGE)) as source:
        capture = source.capture()
    assert capture.facts["status"] == "degraded"
    assert capture.facts["records_omitted"] == 1
    assert b"image_url" not in capture.content
