"""Private path creation and durability behavior without changing shared parents."""

import errno
import os
import stat
from pathlib import Path

import pytest

from ocr_toolkit.common import filesystem


@pytest.mark.parametrize("error", (errno.EINVAL, errno.ENOTSUP, errno.EBADF, errno.EIO))
def test_directory_fsync_ignores_only_unsupported_filesystem_errors(
    monkeypatch: pytest.MonkeyPatch, error: int
) -> None:
    def fail(_descriptor: int) -> None:
        raise OSError(error, "synthetic fsync failure")

    monkeypatch.setattr(filesystem.os, "fsync", fail)
    if error == errno.EIO:
        with pytest.raises(OSError) as exc:
            filesystem.fsync_directory(-1)
        assert exc.value.errno == errno.EIO
    else:
        filesystem.fsync_directory(-1)


def test_private_parent_creation_preserves_shared_ancestor_mode(tmp_path: Path) -> None:
    tmp_path.chmod(0o755)
    parent = tmp_path / "private" / "nested"
    descriptor, name = filesystem.open_private_parent_directory(parent / "output.json")
    try:
        assert name == "output.json"
        assert filesystem.same_file_identity(os.fstat(descriptor), parent.stat())
        filesystem.fsync_directory(descriptor)
    finally:
        os.close(descriptor)
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o755
    assert stat.S_IMODE(parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(parent.parent.stat().st_mode) == 0o700
    assert not (parent / name).exists()


def test_existing_state_read_forbids_missing_parent_creation(tmp_path: Path) -> None:
    absent = tmp_path / "absent"
    with pytest.raises(ValueError, match="unavailable"):
        filesystem.open_private_parent_directory(absent / "file", create=False)
    assert not absent.exists()


@pytest.mark.parametrize("kind", ("symlink", "file"))
def test_private_parent_cannot_cross_non_directory_or_symlink(tmp_path: Path, kind: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    unsafe = tmp_path / "unsafe"
    if kind == "symlink":
        unsafe.symlink_to(outside)
    else:
        unsafe.write_text("caller content")
    with pytest.raises(ValueError):
        filesystem.open_private_parent_directory(unsafe / "output")
    assert not list(outside.iterdir())


def test_root_is_not_a_private_file_name() -> None:
    with pytest.raises(ValueError, match="name a file"):
        filesystem.open_private_parent_directory(Path("/"))


def test_concurrent_parent_creation_retains_the_opened_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = filesystem.os.mkdir
    parent = tmp_path / "concurrent"

    def raced_mkdir(path, *args, **kwargs):
        original(path, *args, **kwargs)
        raise FileExistsError("another creator won")

    monkeypatch.setattr(filesystem.os, "mkdir", raced_mkdir)
    descriptor, _name = filesystem.open_private_parent_directory(parent / "output")
    try:
        assert filesystem.same_file_identity(os.fstat(descriptor), parent.stat())
    finally:
        os.close(descriptor)
