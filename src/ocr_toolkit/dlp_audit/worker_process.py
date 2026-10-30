"""One isolated serial peer, with bounded frames and a deadline for each file."""

from __future__ import annotations

import math
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path
from typing import BinaryIO

from .state import MAX_DOCUMENT, AuditError

MAX_REQUEST = 8 * 1_048_576


class WorkerFailure(AuditError):
    """Carry an operational diagnosis without subprocess output or source values."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def frame(raw: bytes) -> bytes:
    if not raw or len(raw) > MAX_DOCUMENT:
        raise AuditError("invalid worker frame size")
    return len(raw).to_bytes(4, "big") + raw


def read_request(stream: BinaryIO) -> bytes | None:
    """Read only a bounded request; EOF between requests is normal shutdown."""

    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4 or not 1 <= (size := int.from_bytes(header, "big")) <= MAX_REQUEST:
        raise AuditError("invalid worker request frame")
    raw = stream.read(size)
    if len(raw) != size:
        raise AuditError("truncated worker request")
    return raw


class WorkerSession:
    """Reuse trusted imports while keeping target code unexecuted and unimported."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> WorkerSession:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        """Kill/reap the owned process on cancellation, failure or normal teardown."""

        process, self.process = self.process, None
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait()
            finally:
                for stream in (process.stdin, process.stdout):
                    if stream is not None:
                        stream.close()

    def exchange(self, raw: bytes, timeout: float) -> bytes:
        if not raw or len(raw) + 16 > MAX_REQUEST or not math.isfinite(timeout) or timeout <= 0:
            raise AuditError("invalid worker request budget")
        deadline = time.monotonic() + timeout
        try:
            if self.process is not None and self.process.poll() is not None:
                self.close()
            if self.process is None:
                try:
                    self.process = subprocess.Popen(
                        [sys.executable, "-I", "-m", "ocr_toolkit.dlp_audit", "--worker"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        bufsize=0,
                        cwd=Path(__file__).resolve().parent,
                    )
                except OSError as exc:
                    raise WorkerFailure("worker_launch") from exc
            process = self.process
            assert process.stdin is not None and process.stdout is not None
            os.set_blocking(process.stdin.fileno(), False)
            os.set_blocking(process.stdout.fileno(), False)
            request_id = os.urandom(16)
            outgoing = frame(request_id + raw)
            sent = 0
            incoming = bytearray()
            expected: int | None = None
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdin, selectors.EVENT_WRITE)
                selector.register(process.stdout, selectors.EVENT_READ)
                while expected is None or len(incoming) < expected or sent < len(outgoing):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise WorkerFailure("worker_timeout")
                    for key, _events in selector.select(remaining):
                        if key.fileobj is process.stdin:
                            sent += os.write(key.fd, outgoing[sent : sent + 65536])
                            if sent == len(outgoing):
                                selector.unregister(process.stdin)
                        else:
                            part = os.read(key.fd, 65536)
                            if not part:
                                raise WorkerFailure("worker_failed")
                            if len(incoming) + len(part) > MAX_DOCUMENT + 4:
                                raise AuditError("worker response byte limit")
                            incoming.extend(part)
                            if expected is None and len(incoming) >= 4:
                                size = int.from_bytes(incoming[:4], "big")
                                if not 17 <= size <= MAX_DOCUMENT:
                                    raise AuditError("invalid worker response size")
                                expected = size + 4
                            if expected is not None and len(incoming) > expected:
                                raise AuditError("unexpected worker response bytes")
            if incoming[4:20] != request_id:
                raise AuditError("stale worker response")
            return bytes(incoming[20:])
        except OSError as exc:
            self.close()
            raise WorkerFailure("worker_failed") from exc
        except BaseException:
            self.close()
            raise
