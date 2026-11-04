"""Complete Git text peers and bounded excerpts across actual process I/O."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zlib
from types import SimpleNamespace

import pytest

from ocr_toolkit.evidence import text_metadata
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryTextInvalid,
)
from ocr_toolkit.evidence.text_contracts import (
    RepositoryTextExcerpt,
    RepositoryTextMetadata,
    normalize_fragment,
)
from ocr_toolkit.evidence.text_excerpts import TextExcerptCapture
from ocr_toolkit.evidence.text_metadata import TextMetadataError, consume_text_metadata
from tests.test_evidence_repository import git


def repository(tmp_path, content):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "source").write_bytes(content)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return GitRepositoryReader(tmp_path, max_file_bytes=5_000_000), git(
        tmp_path, "rev-parse", "HEAD"
    )


@pytest.mark.parametrize(
    "source,lines",
    [
        (b"", 0),
        (b"one", 1),
        (b"one\n", 1),
        (b"one\n\n", 2),
        (b"one\r\ntwo\r\n", 2),
        ("one\u2028two".encode(), 1),
        (b"one\rtwo", 1),
    ],
)
def test_real_git_excerpts_use_exact_lf_addresses(tmp_path, source, lines):
    reader, head = repository(tmp_path, source)
    entry = reader.object_at(head, "source")
    assert entry is not None
    result = reader.read_text_metadata(
        entry,
        max_bytes=len(source),
        spans=((1, 1), (2, 2), (1, 2)),
        max_source_chars=100,
    )
    assert result.object_sha == entry.object_sha
    assert (result.byte_count, result.line_count) == (len(source), lines)
    assert result.source == source.decode()
    expected = source.decode().split("\n")
    for excerpt in result.excerpts:
        if excerpt.end_line > lines:
            assert excerpt.text is None and excerpt.reason == "range"
        else:
            assert excerpt.text == "\n".join(expected[excerpt.start_line - 1 : excerpt.end_line])
            assert excerpt.reason == "none"


def test_metadata_representation_excludes_retained_source_and_excerpts():
    marker = "synthetic-private-source-marker"
    excerpt = RepositoryTextExcerpt(1, 1, marker)
    metadata = RepositoryTextMetadata("a" * 40, len(marker), 1, (excerpt,), marker)
    assert marker not in repr(excerpt)
    assert marker not in repr(metadata)


def test_large_git_source_retains_short_ranges_without_full_source(tmp_path):
    source = b"one\n" + b"x" * 270_000 + b"\nlast\n"
    reader, head = repository(tmp_path, source)
    entry = reader.object_at(head, "source")
    result = reader.read_text_metadata(
        entry,
        max_bytes=len(source),
        spans=((1, 1), (2, 2), (3, 3)),
        max_source_chars=256_000,
    )
    assert result.source is None and result.line_count == 3
    assert [(item.text, item.reason) for item in result.excerpts] == [
        ("one", "none"),
        (None, "limit"),
        ("last", "none"),
    ]


@pytest.mark.parametrize("tail", [b"\x00", b"\xff", b"\xe2\x82"])
def test_late_invalid_text_discards_earlier_excerpts(tmp_path, tail):
    source = b"safe\n" + b"x" * 270_000 + tail
    reader, head = repository(tmp_path, source)
    entry = reader.object_at(head, "source")
    with pytest.raises((UnicodeError, RepositoryTextInvalid)):
        reader.read_text_metadata(entry, max_bytes=len(source), spans=((1, 1),))


@pytest.mark.parametrize(
    "options",
    [
        {"spans": []},
        {"spans": ((True, 2),)},
        {"spans": ((0, 1),)},
        {"spans": ((2, 1),)},
        {"spans": ((1, 202),)},
        {"spans": ((1, 1),) * 10_001},
        {"spans": ((1, 1_000_000_001),)},
        {"max_excerpt_bytes": -1},
        {"max_excerpt_bytes": 32_000_001},
        {"max_excerpt_bytes": True},
        {"max_source_chars": -1},
        {"max_source_chars": 256_001},
        {"max_source_chars": False},
    ],
)
def test_malformed_capture_arguments_fail_before_git_io(tmp_path, monkeypatch, options):
    reader, head = repository(tmp_path, b"safe\n")
    entry = reader.object_at(head, "source")
    monkeypatch.setattr(reader, "_run", lambda *_a, **_k: pytest.fail("unexpected Git I/O"))
    with pytest.raises(RepositoryEvidenceError):
        reader.read_text_metadata(entry, max_bytes=5, **options)


def test_capture_limits_reclaim_discarded_storage_without_reopening_the_range():
    capture = TextExcerptCapture(((1, 1), (1, 2), (3, 3)), max_bytes=7, max_source_chars=3)
    capture.feed("abc", 1)
    capture.feed("d\nef\nz", 1)
    result = capture.finish(3)
    assert [(item.text, item.reason) for item in result] == [
        ("abcd", "none"),
        (None, "limit"),
        ("z", "none"),
    ]
    assert capture.source is None and capture.used_bytes <= 7


@pytest.mark.parametrize("pieces", [("abcd\nx",), ("abc", "d\nx"), tuple("abcd\nx")])
def test_overlapping_range_budget_allocation_is_independent_of_pipe_chunks(pieces):
    capture = TextExcerptCapture(((1, 1), (1, 2)), max_bytes=6, max_source_chars=0)
    line = 1
    for piece in pieces:
        capture.feed(piece, line)
        line += piece.count("\n")
    assert [(item.text, item.reason) for item in capture.finish(2)] == [
        ("abcd", "none"),
        (None, "limit"),
    ]
    assert capture.used_bytes == 4


@pytest.mark.parametrize("count,reason", [(12_000, "none"), (12_001, "limit")])
def test_multibyte_excerpt_limits_apply_to_retained_text(count, reason):
    capture = TextExcerptCapture(((1, 1),), max_bytes=48_000, max_source_chars=0)
    capture.feed("\U0001f600" * count, 1)
    (item,) = capture.finish(1)
    assert item.reason == reason
    assert item.text == ("\U0001f600" * count if reason == "none" else None)
    assert capture.used_bytes <= 48_000


def test_no_excerpt_requests_preserve_metadata_only_retention():
    capture = TextExcerptCapture((), max_bytes=0, max_source_chars=0)
    capture.feed("source\n", 1)
    assert capture.finish(1) == () and capture.source is None


def test_duplicate_spans_are_idempotent_and_exact_source_char_limit_is_inclusive():
    capture = TextExcerptCapture(((1, 1), (1, 1)), max_bytes=3, max_source_chars=3)
    capture.feed("abc", 1)
    (item,) = capture.finish(1)
    assert item.text == "abc" and capture.source == "abc" and capture.used_bytes == 3


def test_crlf_transport_overhead_does_not_reduce_the_existing_fragment_limit():
    lines = ["a" * 60, *(["a" * 59] * 199)]
    source = "\r\n".join(lines) + "\r\n"
    assert len("\n".join(lines)) == 12_000
    capture = TextExcerptCapture(((1, 200),), max_bytes=32_000_000, max_source_chars=0)
    capture.feed(source, 1)
    (excerpt,) = capture.finish(200)
    assert excerpt.reason == "none"
    assert normalize_fragment(excerpt.text) == "\n".join(lines)


def test_final_normalized_limit_is_checked_after_allowing_transport_overhead():
    capture = TextExcerptCapture(((1, 1),), max_bytes=32_000_000, max_source_chars=0)
    capture.feed("a" * 12_001, 1)
    (excerpt,) = capture.finish(1)
    assert excerpt.text is None and excerpt.reason == "limit"


@pytest.mark.parametrize("behavior", ["short", "long", "failed", "stderr", "timeout", "identity"])
def test_incomplete_or_hostile_process_never_returns_partial_excerpts(behavior):
    code = {
        "short": "import os; os.write(1,b'x')",
        "long": "import os; os.write(1,b'long')",
        "failed": "import os; os.write(1,b'ok'); raise SystemExit(1)",
        "stderr": "import os; os.write(1,b'ok'); os.write(2,b'x'*70000)",
        "timeout": "import time; time.sleep(5)",
        "identity": "import os; os.write(1,b'no')",
    }[behavior]
    messages = {
        "short": "incomplete Git text metadata read",
        "long": "Git text size changed",
        "failed": "incomplete Git text metadata read",
        "stderr": "Git text diagnostic limit",
        "identity": "Git text object identity mismatch",
        "timeout": "timed out",
    }
    error = subprocess.TimeoutExpired if behavior == "timeout" else TextMetadataError
    digest = hashlib.sha1(b"blob 2\0ok", usedforsecurity=False).hexdigest()
    with pytest.raises(error, match=messages[behavior]):
        consume_text_metadata(
            [sys.executable, "-I", "-c", code],
            environment=os.environ.copy(),
            object_sha=digest,
            size=2,
            timeout=0.1 if behavior == "timeout" else 5,
            spans=((1, 1),),
        )


def test_forged_loose_object_cannot_supply_source_identity(tmp_path):
    reader, head = repository(tmp_path, b"safe\n")
    entry = reader.object_at(head, "source")
    object_path = tmp_path / ".git" / "objects" / entry.object_sha[:2] / entry.object_sha[2:]
    object_path.chmod(0o600)
    object_path.write_bytes(zlib.compress(b"blob 5\0evil\n"))
    with pytest.raises(RepositoryEvidenceError, match="identity mismatch"):
        reader.read_text_metadata(entry, max_bytes=5, spans=((1, 1),))


@pytest.mark.parametrize("phase", ["peer-exit", "capture-finish"])
def test_completed_peer_or_capture_cannot_publish_after_overall_deadline(monkeypatch, phase):
    clock = [100.0]
    monkeypatch.setattr(text_metadata, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    if phase == "peer-exit":
        original = subprocess.Popen.wait

        def wait(process, *args, **kwargs):
            result = original(process, *args, **kwargs)
            clock[0] += 2
            return result

        monkeypatch.setattr(subprocess.Popen, "wait", wait)
    else:
        finish = TextExcerptCapture.finish

        def late_finish(capture, *args, **kwargs):
            result = finish(capture, *args, **kwargs)
            clock[0] += 2
            return result

        monkeypatch.setattr(TextExcerptCapture, "finish", late_finish)
    with pytest.raises(subprocess.TimeoutExpired):
        consume_text_metadata(
            [sys.executable, "-I", "-c", "import os; os.write(1,b'ok')"],
            environment=os.environ.copy(),
            object_sha=hashlib.sha1(b"blob 2\0ok", usedforsecurity=False).hexdigest(),
            size=2,
            timeout=1,
            spans=((1, 1),),
        )
