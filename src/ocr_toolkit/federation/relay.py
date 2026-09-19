"""Fixed stdio relay to the parent-owned, private Unix-socket federation gateway."""

from __future__ import annotations

import argparse
import os
import select
import socket
import sys
import time

from .contracts import RESPONSE_BYTES, RUN_SECONDS, WIRE_BYTES


def relay(endpoint: str) -> int:
    """Copy bounded raw frames with backpressure; never resolve services or credentials."""
    started = time.monotonic()
    total = 0
    partial = {0: 0, 1: 0}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(endpoint)
        connection.setblocking(False)
        stdin, stdout = sys.stdin.fileno(), sys.stdout.fileno()
        os.set_blocking(stdin, False)
        os.set_blocking(stdout, False)
        pending = {connection.fileno(): bytearray(), stdout: bytearray()}
        sources = {stdin: connection.fileno(), connection.fileno(): stdout}
        ended: set[int] = set()
        while time.monotonic() - started < RUN_SECONDS:
            if any(source in ended and not pending[target] for source, target in sources.items()):
                return 0
            readable = [
                source
                for source, target in sources.items()
                if source not in ended and len(pending[target]) < 16 * 1024
            ]
            writable = [target for target, data in pending.items() if data]
            ready, writes, _ = select.select(
                readable, writable, [], min(1, max(0, RUN_SECONDS - (time.monotonic() - started)))
            )
            for source in ready:
                remote = source == connection.fileno()
                try:
                    chunk = os.read(source, 16 * 1024 - len(pending[sources[source]]))
                except BlockingIOError:
                    continue
                if not chunk:
                    ended.add(source)
                    continue
                total += len(chunk)
                if total > WIRE_BYTES:
                    return 1
                for piece in chunk.splitlines(keepends=True):
                    partial[int(remote)] += len(piece)
                    if partial[int(remote)] > RESPONSE_BYTES:
                        return 1
                    if piece.endswith(b"\n"):
                        partial[int(remote)] = 0
                pending[sources[source]].extend(chunk)
            for target in writes:
                try:
                    written = os.write(target, pending[target][:4096])
                except BlockingIOError:
                    continue
                del pending[target][:written]
    return 1


def main() -> int:
    """Accept only the fixed runtime endpoint argument and emit no raw diagnostics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()
    try:
        return relay(args.socket)
    except (OSError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
