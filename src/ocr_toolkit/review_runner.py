"""Run Open Code Review with private artifacts and safe CI diagnostics."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from contextlib import ExitStack
from io import BufferedWriter
from pathlib import Path

from ocr_toolkit.common.redaction import redact_sensitive

STDERR_PROBE_BYTES = 64 * 1024
DEFAULT_DIAGNOSTIC_CHARS = 4_000


class ReviewRunnerError(Exception):
    """The local OCR review process could not be started safely."""


def _open_private_artifact(path: Path, label: str) -> BufferedWriter:
    """Open one regular artifact without following a final-component symlink."""

    flags = os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        # The pre-check gives a clear error; O_NOFOLLOW closes the replacement race
        # between that check and open on platforms that expose the flag.
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        # Opening a pre-created FIFO for writing could otherwise block the CI job
        # before the descriptor can be rejected as a non-artifact sink.
        flags |= os.O_NONBLOCK
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ReviewRunnerError(f"private {label} artifact must be a regular file: {path}")
        if file_stat.st_nlink > 1:
            raise ReviewRunnerError(f"private {label} artifact must not have hard links: {path}")
        os.fchmod(descriptor, 0o600)
        # Delay truncation until the descriptor has passed type and link checks.
        os.ftruncate(descriptor, 0)
    except ReviewRunnerError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ReviewRunnerError(f"could not open private {label} artifact: {exc}") from exc
    return open(descriptor, "wb", closefd=True)


def read_stderr_excerpt(stderr_path: Path, max_chars: int = DEFAULT_DIAGNOSTIC_CHARS) -> str:
    """Read a bounded, redacted excerpt of an OCR stderr artifact."""

    if not stderr_path.exists():
        return ""
    try:
        with stderr_path.open("rb") as handle:
            chunk = handle.read(STDERR_PROBE_BYTES)
    except OSError:
        return ""

    text = chunk.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    # Redact before truncation so a secret crossing the display boundary is
    # matched against its complete environment value or credential pattern.
    return redact_sensitive(text)[:max_chars]


def run_review(result_path: Path, stderr_path: Path, ocr_args: list[str]) -> int:
    """Execute `ocr review`, retain private artifacts, and report safe failures."""

    if not ocr_args:
        raise ReviewRunnerError("at least one OCR review argument is required after --")
    if result_path.absolute() == stderr_path.absolute():
        raise ReviewRunnerError("result and stderr paths must be different")
    for path, label in ((result_path, "result"), (stderr_path, "stderr")):
        if path.is_symlink():
            raise ReviewRunnerError(f"{label} path must not be a symlink: {path}")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Use explicit argv and file descriptors: OCR-controlled output never crosses
    # a shell, while umask 077 keeps both artifacts private on shared runners.
    previous_umask = os.umask(0o077)
    try:
        with ExitStack() as stack:
            result_file = stack.enter_context(_open_private_artifact(result_path, "result"))
            stderr_file = stack.enter_context(_open_private_artifact(stderr_path, "stderr"))
            if os.path.samestat(os.fstat(result_file.fileno()), os.fstat(stderr_file.fileno())):
                raise ReviewRunnerError("result and stderr paths must be different")
            completed = subprocess.run(
                ["ocr", "review", *ocr_args],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=result_file,
                stderr=stderr_file,
            )
    except OSError as exc:
        raise ReviewRunnerError(f"could not execute OCR: {exc}") from exc
    finally:
        os.umask(previous_umask)

    if completed.returncode != 0:
        print(f"Open Code Review exited with code {completed.returncode}.", file=sys.stderr)
        excerpt = read_stderr_excerpt(stderr_path)
        if excerpt:
            print("Safe OCR stderr excerpt:", file=sys.stderr)
            print(excerpt, file=sys.stderr)
        else:
            print("OCR did not provide a readable stderr diagnostic.", file=sys.stderr)
    return completed.returncode
