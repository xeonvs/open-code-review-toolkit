"""Own the private repository-local artifacts used by evidence-backed reviews."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvidenceArtifacts:
    """Name the fixed private artifacts for one analyzed repository."""

    directory: Path
    store: Path
    bootstrap: Path
    policy_rules: Path
    context_store: Path
    pre_execution_status: Path
    review_run_lock: Path
    action_receipt: Path
    action_receipt_lock: Path
    dlp_decisions: Path


def repository_artifacts(root: Path | None = None) -> EvidenceArtifacts:
    """Return toolkit-owned paths below the analyzed repository root."""

    repository_root = (root or Path.cwd()).resolve(strict=True)
    directory = repository_root / ".review-context"
    return EvidenceArtifacts(
        directory=directory,
        store=directory / "evidence.json",
        bootstrap=directory / "bootstrap.md",
        policy_rules=directory / "policy-rules.json",
        context_store=directory / "context.json",
        pre_execution_status=directory / "pre-execution-status.json",
        review_run_lock=directory / ".review-run.lock",
        action_receipt=directory / "evidence-actions.json",
        action_receipt_lock=directory / ".evidence-actions.json.lock",
        dlp_decisions=directory / "private-dlp-decisions.json",
    )


def prepare_artifact_directory(artifacts: EvidenceArtifacts) -> None:
    """Create and validate the toolkit-owned private artifact directory."""

    directory = artifacts.directory
    if directory.is_symlink():
        raise OSError(f"refusing private artifact directory symlink: {directory}")
    directory.mkdir(mode=0o700, parents=False, exist_ok=True)
    descriptor = os.open(
        directory,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        named = directory.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or (metadata.st_dev, metadata.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise OSError(f"private artifact path is not a safe directory: {directory}")
        os.fchmod(descriptor, 0o700)
        named = directory.stat(follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (named.st_dev, named.st_ino):
            raise OSError(f"private artifact directory changed during setup: {directory}")
    finally:
        os.close(descriptor)


class ReviewRunBusy(OSError):
    """Another review owns the fixed private artifacts for this repository."""


@contextmanager
def locked_review_run(artifacts: EvidenceArtifacts) -> Iterator[None]:
    """Hold one stable private lock across a review's entire artifact lifetime."""

    prepare_artifact_directory(artifacts)
    directory = -1
    descriptor = -1
    try:
        directory = os.open(
            artifacts.directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        directory_stat = os.fstat(directory)
        named_directory = artifacts.directory.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(directory_stat.st_mode)
            or directory_stat.st_uid != os.getuid()
            or (directory_stat.st_dev, directory_stat.st_ino)
            != (named_directory.st_dev, named_directory.st_ino)
            or stat.S_IMODE(directory_stat.st_mode) & 0o077
        ):
            raise OSError("private review lock directory is unsafe")
        descriptor = os.open(
            artifacts.review_run_lock.name,
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            0o600,
            dir_fd=directory,
        )
        opened = os.fstat(descriptor)
        named = os.stat(
            artifacts.review_run_lock.name,
            dir_fd=directory,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) & 0o077
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise OSError("private review lock file is unsafe")
        try:
            flock(descriptor, LOCK_EX | LOCK_NB)
        except BlockingIOError as exc:
            raise ReviewRunBusy("another review is already running in this repository") from exc
        named = os.stat(
            artifacts.review_run_lock.name,
            dir_fd=directory,
            follow_symlinks=False,
        )
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            raise OSError("private review lock file changed during acquisition")
        # Keep the named inode across runs; unlinking it would let a second
        # review lock a replacement while this review still holds the old one.
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory >= 0:
            os.close(directory)


def write_private_bytes(path: Path, content: bytes) -> None:
    """Write one private byte artifact without following the final symlink."""

    if path.parent.is_symlink() or not path.parent.is_dir():
        raise OSError(f"private artifact parent is not a safe directory: {path.parent}")
    if path.is_symlink():
        raise OSError(f"refusing to replace private artifact symlink: {path}")
    flags = os.O_WRONLY | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"private artifact is not a regular file: {path}")
        if metadata.st_nlink != 1:
            raise OSError(f"private artifact is an existing hard link: {path}")
        os.fchmod(descriptor, 0o600)
        os.ftruncate(descriptor, 0)
        stream = os.fdopen(descriptor, "wb")
        descriptor = -1
        with stream:
            stream.write(content)
    except BaseException:
        # fdopen owns the descriptor once constructed. Never close a recycled fd.
        if descriptor >= 0:
            os.close(descriptor)
        raise


def write_private_text(path: Path, content: str) -> None:
    """Write one internal UTF-8 artifact through the private byte boundary."""

    write_private_bytes(path, content.encode("utf-8"))


def remove_private_artifact(path: Path) -> None:
    """Remove one toolkit-owned artifact name without following its target."""

    if path.parent.is_symlink() or not path.parent.is_dir():
        raise OSError(f"private artifact parent is not a safe directory: {path.parent}")
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except IsADirectoryError as exc:
        raise OSError(f"private artifact path is not a file: {path}") from exc
