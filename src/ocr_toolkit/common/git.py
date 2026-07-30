"""Shared trust-boundary controls for read-only Git plumbing."""

from __future__ import annotations

import os
from pathlib import Path

_PROCESS_OVERRIDE_KEYS = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_WORK_TREE",
    }
)


def isolated_git_environment() -> dict[str, str]:
    """Return an environment isolated from caller-controlled Git state."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in _PROCESS_OVERRIDE_KEYS
        and not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def read_only_git_prefix(root: Path | None = None) -> list[str]:
    """Return Git arguments that bind a root and disable repository hooks."""

    prefix = ["git", "-c", "core.hooksPath=/dev/null"]
    if root is not None:
        prefix.extend(["-C", str(root)])
    return prefix
