"""Framing and real relay backpressure boundaries."""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from ocr_toolkit.federation import FederationError
from ocr_toolkit.federation.transport import parse_frame


@pytest.mark.parametrize(
    "raw",
    [
        b'{"jsonrpc":"2.0","id":1,"id":2,"result":{}}',
        b'{"jsonrpc":"2.0","id":1,"result":{"value":NaN}}',
        b'{"jsonrpc":"2.0","id":1,"result":{"value":"\xff"}}',
        b"[" * 25 + b"0" + b"]" * 25,
    ],
)
def test_noncanonical_or_deep_wire_frame_is_rejected(raw: bytes) -> None:
    with pytest.raises(FederationError):
        parse_frame(raw)


def test_relay_deadline_survives_blocked_ocr_stdout() -> None:
    # macOS Unix socket paths must fit in 104 bytes, independently of pytest's root.
    with tempfile.TemporaryDirectory(prefix="ocr-relay-", dir="/tmp") as directory:
        _exercise_blocked_stdout(str(Path(directory) / "relay.sock"))


def _exercise_blocked_stdout(endpoint: str) -> None:
    stopped = threading.Event()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(endpoint)
        server.listen(1)
        server.settimeout(5)

        def feed() -> None:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(1)
                while not stopped.is_set():
                    try:
                        connection.sendall(b'{"jsonrpc":"2.0","id":1,"result":{}}\n' * 1024)
                    except OSError:
                        return

        thread = threading.Thread(target=feed, daemon=True)
        thread.start()
        # Invoke the production relay with a short run deadline; never consume stdout.
        with subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                "import sys; import ocr_toolkit.federation.relay as r; r.RUN_SECONDS=0.3; sys.exit(r.relay(sys.argv[1]))",
                endpoint,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as process:
            try:
                assert process.wait(timeout=5) == 1
            finally:
                stopped.set()
                if process.poll() is None:
                    process.kill()
                thread.join(3)
        assert not thread.is_alive()
