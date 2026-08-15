"""Own the private repository-local artifacts used by evidence-backed reviews."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvidenceArtifacts:
    """Name the fixed private artifacts for one analyzed repository."""

    directory: Path
    store: Path
    bootstrap: Path
    policy_rules: Path


def repository_artifacts(root: Path | None = None) -> EvidenceArtifacts:
    """Return toolkit-owned paths below the analyzed repository root."""

    repository_root = (root or Path.cwd()).resolve(strict=True)
    directory = repository_root / ".review-context"
    return EvidenceArtifacts(
        directory=directory,
        store=directory / "evidence.json",
        bootstrap=directory / "bootstrap.md",
        policy_rules=directory / "policy-rules.json",
    )


def prepare_artifact_directory(artifacts: EvidenceArtifacts) -> None:
    """Create and validate the toolkit-owned private artifact directory."""

    directory = artifacts.directory
    if directory.is_symlink():
        raise OSError(f"refusing private artifact directory symlink: {directory}")
    directory.mkdir(mode=0o700, parents=False, exist_ok=True)
    metadata = directory.stat(follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        raise OSError(f"private artifact path is not a directory: {directory}")
    directory.chmod(0o700)


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
