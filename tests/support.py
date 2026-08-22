"""Shared fixtures for OCR CI regression tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ocr_toolkit.posting import gitlab

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_DIR = PROJECT_ROOT / "examples" / "gitlab"


@contextmanager
def patched_attr(obj: Any, name: str, value: Any) -> Iterator[None]:
    """Temporarily replace one object attribute."""

    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


@contextmanager
def patched_env(**values: str) -> Iterator[None]:
    """Temporarily patch environment variables."""

    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def cleared_env(*names: str) -> Iterator[None]:
    """Temporarily remove environment variables."""

    old = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ.pop(name, None)
    try:
        yield
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def gitlab_config(
    current_user_id: int | None = 7, current_username: str | None = "ocr_bot"
) -> gitlab.GitLabConfig:
    """Return a minimal GitLab config for posting tests."""

    return gitlab.GitLabConfig(
        server_url="https://gitlab.example.com",
        project_id="1",
        merge_request_iid="2",
        api_token="token",
        auth_header="PRIVATE-TOKEN",
        current_user_id=current_user_id,
        current_username=current_username,
    )
