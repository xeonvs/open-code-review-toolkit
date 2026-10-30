"""Consume bounded immutable Git text without retaining its source payload."""

from __future__ import annotations

import codecs
import os
import selectors
import subprocess
import time
from dataclasses import dataclass


class TextMetadataError(ValueError):
    """A complete bounded peer response could not be established."""


class TextMetadataInvalid(TextMetadataError):
    """The complete blob contains invalid source text."""


@dataclass(frozen=True, slots=True)
class RepositoryTextMetadata:
    object_sha: str
    byte_count: int
    line_count: int


def consume_text_metadata(
    command: list[str], *, environment: dict[str, str], object_sha: str, size: int, timeout: float
) -> RepositoryTextMetadata:
    """Consume one caller-authorized, size-preflighted object and reap its peer."""

    deadline = time.monotonic() + timeout
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    received = newline_count = error_bytes = 0
    last_byte = None
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment
    ) as process:
        assert process.stdout is not None and process.stderr is not None
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, "source")
                selector.register(process.stderr, selectors.EVENT_READ, "error")
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired("Git text metadata", timeout)
                    for key, _events in selector.select(remaining):
                        chunk = os.read(key.fd, 65_536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        if key.data == "error":
                            error_bytes += len(chunk)
                            if error_bytes > 65_536:
                                raise TextMetadataError("Git text diagnostic limit")
                            continue
                        received += len(chunk)
                        if received > size:
                            raise TextMetadataError("Git text size changed")
                        if b"\x00" in chunk:
                            raise TextMetadataInvalid("repository blob is not text")
                        decoder.decode(chunk)
                        newline_count += chunk.count(b"\n")
                        last_byte = chunk[-1]
            decoder.decode(b"", final=True)
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
            if process.returncode != 0 or received != size:
                raise TextMetadataError("incomplete Git text metadata read")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
    return RepositoryTextMetadata(
        object_sha, received, newline_count + int(last_byte is not None and last_byte != 10)
    )
