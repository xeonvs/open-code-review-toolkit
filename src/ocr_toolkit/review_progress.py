"""Emit bounded toolkit-only progress independently of OCR output and admission."""

from __future__ import annotations

import io
import os
import select
import threading
from typing import TextIO, get_args

from ocr_toolkit.reporting.model import FailureStage

HEARTBEAT_SECONDS = 30.0
MAX_PROGRESS_MESSAGES = 120


def progress_enabled(value: str) -> bool:
    """Parse the explicit progress switch without printing operator input."""

    normalized = value.strip().lower()
    if normalized not in {"", "false", "true"}:
        raise ValueError("OCR_REVIEW_PROGRESS must be true, false, or empty")
    return normalized == "true"


class ReviewProgress:
    """Own one timer and a bounded stream of closed toolkit phase labels."""

    def __init__(self, stream: TextIO, *, interval: float = HEARTBEAT_SECONDS) -> None:
        if interval <= 0:
            raise ValueError("progress interval must be positive")
        self._stream = stream
        self._interval = interval
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._stage: FailureStage = "configuration"
        self._messages = 0
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start optional observation; resource failures cannot reject a review."""

        if self._thread is not None or self._stop.is_set():
            return
        thread = threading.Thread(target=self._heartbeat, name="ocr-review-progress", daemon=True)
        try:
            thread.start()
        except (RuntimeError, OSError):
            self._stop.set()
            return
        self._thread = thread
        self.phase("configuration")

    def _emit(self, *, waiting: bool) -> None:
        with self._lock:
            if self._stop.is_set() or self._messages >= MAX_PROGRESS_MESSAGES:
                return
            self._messages += 1
            prefix = "waiting " if waiting else ""
            try:
                message = f"OCR progress: {prefix}phase={self._stage}\n"
                try:
                    descriptor = self._stream.fileno()
                except (AttributeError, io.UnsupportedOperation):
                    descriptor = None
                if descriptor is None:
                    self._stream.write(message)
                    self._stream.flush()
                elif select.select([], [descriptor], [], 0)[1]:
                    # One short ASCII record, below PIPE_BUF, with no read or
                    # mutation of the shared stderr descriptor's status flags.
                    encoded = message.encode("ascii")
                    if os.write(descriptor, encoded) != len(encoded):
                        self._stop.set()
                else:
                    self._stop.set()
            except (OSError, ValueError):
                self._stop.set()
            if self._messages >= MAX_PROGRESS_MESSAGES:
                self._stop.set()

    def phase(self, stage: FailureStage) -> None:
        """Accept only a toolkit-owned phase, never a subprocess message."""

        if stage not in get_args(FailureStage):
            return
        with self._lock:
            self._stage = stage
        self._emit(waiting=False)

    def _heartbeat(self) -> None:
        while not self._stop.wait(self._interval):
            self._emit(waiting=True)

    def close(self) -> None:
        """Stop the timer and leave no live heartbeat after returning."""

        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
