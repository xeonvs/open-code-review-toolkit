"""Run Open Code Review with private artifacts and safe CI diagnostics."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from io import BufferedWriter
from pathlib import Path

from ocr_toolkit import mcp_config
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.evidence.artifacts import (
    prepare_artifact_directory,
    repository_artifacts,
    write_private_text,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.mcp import TOOL_NAME, evidence_summary
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import RepositoryEvidenceError
from ocr_toolkit.evidence.store import EvidenceStoreError

STDERR_PROBE_BYTES = 64 * 1024
DEFAULT_DIAGNOSTIC_CHARS = 4_000


class ReviewRunnerError(Exception):
    """The local OCR review process could not be started safely."""


@dataclass(frozen=True, slots=True)
class ReviewRefs:
    """Name the immutable base and head refs represented by one OCR review."""

    base: str
    head: str


def _option_values(args: list[str], name: str, short: str | None = None) -> list[str]:
    """Return values for one bounded OCR option form."""

    values: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument == name or (short is not None and argument == short):
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                raise ReviewRunnerError(f"OCR option {argument} requires a value")
            values.append(args[index + 1])
            index += 2
            continue
        prefix = f"{name}="
        if argument.startswith(prefix):
            value = argument[len(prefix) :]
            if not value:
                raise ReviewRunnerError(f"OCR option {name} requires a value")
            values.append(value)
        index += 1
    return values


def _one_option(args: list[str], name: str, short: str | None = None) -> str | None:
    """Return one unique OCR option value or reject ambiguous duplicates."""

    values = _option_values(args, name, short)
    if len(values) > 1:
        raise ReviewRunnerError(f"OCR option {name} must be provided at most once")
    return values[0] if values else None


def _review_refs(args: list[str]) -> ReviewRefs:
    """Derive immutable evidence refs from the exact OCR diff arguments."""

    base = _one_option(args, "--from")
    head = _one_option(args, "--to")
    commit = _one_option(args, "--commit", "-c")
    if commit is not None:
        if base is not None or head is not None:
            raise ReviewRunnerError("OCR --commit cannot be combined with --from or --to")
        return ReviewRefs(f"{commit}^", commit)
    if (base is None) != (head is None):
        raise ReviewRunnerError("OCR evidence review requires both --from and --to")
    if base is None or head is None:
        raise ReviewRunnerError(
            "OCR evidence review requires immutable --from/--to refs or --commit"
        )
    return ReviewRefs(base, head)


def _reject_owned_background(args: list[str]) -> None:
    """Reject caller attempts to replace the toolkit-owned bootstrap file."""

    if _option_values(args, "--background-file"):
        raise ReviewRunnerError(
            "--background-file is managed by ocr-ci review; use --background for extra context"
        )


def run_evidence_review(result_path: Path, stderr_path: Path, ocr_args: list[str]) -> int:
    """Prepare private evidence and run OCR through the composed MCP context."""

    refs = _review_refs(ocr_args)
    _reject_owned_background(ocr_args)
    artifacts = repository_artifacts()
    print("OCR evidence preflight: collecting immutable review refs", file=sys.stderr)
    try:
        prepare_artifact_directory(artifacts)
        store = collect_repository_evidence(base_ref=refs.base, head_ref=refs.head)
        store.write(artifacts.store)
        composition = mcp_config.build_mcp_composition()
        bootstrap = render_bootstrap(store, capabilities=composition.capabilities)
        write_private_text(artifacts.bootstrap, bootstrap)
        mcp_config.apply_mcp_composition(composition)
        summary = evidence_summary(store)
    except (
        EvidenceStoreError,
        OSError,
        RepositoryEvidenceError,
        ValueError,
        mcp_config.MCPConfigError,
    ) as exc:
        raise ReviewRunnerError(
            f"OCR evidence preflight failed: {redact_sensitive(str(exc))}"
        ) from exc
    records = summary.get("records")
    if not isinstance(records, int) or isinstance(records, bool) or records < 0:
        raise ReviewRunnerError("OCR evidence preflight returned an invalid MCP summary")
    print(
        "OCR evidence preflight: ready "
        f"base={summary.get('base')} head={summary.get('head')} records={records} "
        f"mcp_servers={len(composition.capabilities)} "
        f"builtin_tool={TOOL_NAME}",
        file=sys.stderr,
    )
    return run_review(
        result_path,
        stderr_path,
        [*ocr_args, "--background-file", str(artifacts.bootstrap)],
    )


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
