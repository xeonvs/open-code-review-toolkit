"""One build-file grammar for classification, acquisition and FROM parsing."""

from pathlib import PurePosixPath


def is_container_build_file(path: str) -> bool:
    """Recognize base, base.variant and name.base, case-insensitively."""

    name = PurePosixPath(path).name.casefold()
    return any(
        name == base
        or (name.startswith(base + ".") and len(name) > len(base) + 1)
        or (name.endswith("." + base) and len(name) > len(base) + 1)
        for base in ("dockerfile", "containerfile")
    )
