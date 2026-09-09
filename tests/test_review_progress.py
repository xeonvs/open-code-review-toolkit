"""Progress observes closed phases and never owns review result data."""

import io
import os
import threading

import pytest

from ocr_toolkit import review_progress, review_runner
from ocr_toolkit.review_progress import ReviewProgress, progress_enabled


@pytest.mark.parametrize("value", ["", "false", "FALSE", " false "])
def test_progress_is_off_by_default(value: str) -> None:
    assert progress_enabled(value) is False


@pytest.mark.parametrize("value", ["true", "TRUE", " true "])
def test_progress_accepts_explicit_true(value: str) -> None:
    assert progress_enabled(value) is True


def test_invalid_progress_value_is_not_echoed() -> None:
    with pytest.raises(ValueError) as error:
        progress_enabled("private-invalid-value")
    assert "private-invalid-value" not in str(error.value)


def test_heartbeat_stops_without_late_output() -> None:
    waiting = threading.Event()

    class Sink(io.StringIO):
        def write(self, value: str) -> int:
            result = super().write(value)
            if "waiting" in value:
                waiting.set()
            return result

    sink = Sink()
    progress = ReviewProgress(sink, interval=0.01)
    try:
        progress.start()
        thread = progress._thread
        progress.phase("subprocess")
        assert waiting.wait(2)
    finally:
        progress.close()
    assert thread is not None and not thread.is_alive()
    final = sink.getvalue()
    progress.phase("reporting")
    progress.start()
    progress.close()
    assert sink.getvalue() == final
    assert "phase=subprocess" in final
    assert review_progress.HEARTBEAT_SECONDS == 30


def test_budget_stops_timer_and_caps_all_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_progress, "MAX_PROGRESS_MESSAGES", 3)
    sink = io.StringIO()
    progress = ReviewProgress(sink)
    progress.start()
    thread = progress._thread
    for _ in range(10):
        progress.phase("evidence")
    progress.close()
    assert len(sink.getvalue().splitlines()) == 3
    assert thread is not None and not thread.is_alive()


def test_real_broken_pipe_disables_progress_and_releases_thread() -> None:
    reader, writer = os.pipe()
    os.close(reader)
    with io.TextIOWrapper(io.FileIO(writer, "w"), write_through=True) as sink:
        progress = ReviewProgress(sink, interval=0.01)
        progress.start()
        thread = progress._thread
        progress.phase("subprocess")
        progress.close()
        assert progress._stop.is_set()
        assert thread is None or not thread.is_alive()


def test_thread_start_failure_does_not_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(_thread: threading.Thread) -> None:
        raise RuntimeError("thread limit")

    monkeypatch.setattr(threading.Thread, "start", reject)
    progress = ReviewProgress(io.StringIO())
    progress.start()
    progress.close()
    assert progress._thread is None


def test_nonblocking_descriptor_writes_without_mutating_the_caller_stream() -> None:
    reader, writer = os.pipe()
    try:
        os.set_blocking(writer, False)
        with io.TextIOWrapper(io.FileIO(writer, "w", closefd=False), write_through=True) as sink:
            progress = ReviewProgress(sink)
            progress.start()
            progress.phase("subprocess")
        assert os.get_blocking(writer) is False
        os.set_blocking(reader, False)
        output = os.read(reader, 4096).decode("ascii")
        assert "OCR progress: phase=configuration" in output
        assert "OCR progress: phase=subprocess" in output
        progress.close()
    finally:
        os.close(writer)
        os.close(reader)


def test_terminal_gets_an_independent_nonblocking_progress_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_reader, original, terminal_reader, terminal = *os.pipe(), *os.pipe()
    opened_terminal = -1
    try:
        calls: list[tuple[object, ...]] = []
        os.set_blocking(terminal, False)
        with io.TextIOWrapper(io.FileIO(original, "w", closefd=False), write_through=True) as sink:
            progress = ReviewProgress(sink)
            monkeypatch.setattr(
                review_progress.os, "isatty", lambda descriptor: descriptor == original
            )
            monkeypatch.setattr(review_progress.os, "ttyname", lambda _descriptor: "/synthetic/tty")

            def open_terminal(path: str, flags: int) -> int:
                nonlocal opened_terminal
                calls.append((path, flags))
                assert path == "/synthetic/tty"
                assert flags & os.O_NONBLOCK
                opened_terminal = os.dup(terminal)
                return opened_terminal

            monkeypatch.setattr(review_progress.os, "open", open_terminal)
            progress.start()
            progress.phase("subprocess")
            assert os.get_blocking(original) is True
            os.set_blocking(terminal_reader, False)
            output = os.read(terminal_reader, 4096).decode("ascii")
            assert "OCR progress: phase=configuration" in output
            assert "OCR progress: phase=subprocess" in output
            progress.close()
            with pytest.raises(OSError):
                os.fstat(opened_terminal)
        assert calls
    finally:
        os.close(terminal_reader)
        os.close(terminal)
        os.close(original_reader)
        os.close(original)


def test_blocking_pipe_disables_progress_without_mutating_stream() -> None:
    reader, writer = os.pipe()
    try:
        with io.TextIOWrapper(io.FileIO(writer, "w", closefd=False), write_through=True) as sink:
            progress = ReviewProgress(sink)
            progress.start()
            progress.phase("subprocess")
            assert progress._thread is None
            progress.close()
        assert progress._stop.is_set()
        assert progress._thread is None
        assert os.get_blocking(writer) is True
        os.set_blocking(reader, False)
        with pytest.raises(BlockingIOError):
            os.read(reader, 1)
    finally:
        os.close(writer)
        os.close(reader)


def test_full_pipe_disables_progress_without_blocking() -> None:
    reader, writer = os.pipe()
    try:
        os.set_blocking(writer, False)
        try:
            while True:
                os.write(writer, b"x" * 4096)
        except BlockingIOError:
            pass
        with io.TextIOWrapper(io.FileIO(writer, "w", closefd=False), write_through=True) as sink:
            progress = ReviewProgress(sink)
            progress.start()
            progress.close()
            assert progress._stop.is_set()
            assert progress._thread is None
            assert os.get_blocking(writer) is False
    finally:
        os.close(writer)
        os.close(reader)


def test_progress_stops_when_review_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[ReviewProgress] = []
    original_start = ReviewProgress.start

    def start(self: ReviewProgress) -> None:
        observed.append(self)
        original_start(self)

    monkeypatch.setattr(ReviewProgress, "start", start)
    monkeypatch.setenv("OCR_REVIEW_PROGRESS", "true")
    monkeypatch.setenv("OCR_REVIEW_CONTEXT_MODE", "metadata")
    with pytest.raises(review_runner.ReviewRunnerError, match="change-request context"):
        review_runner.run_evidence_review(tmp_path / "result", tmp_path / "stderr", [], local=True)
    assert len(observed) == 1 and observed[0]._thread is None
    assert observed[0]._stop.is_set()
