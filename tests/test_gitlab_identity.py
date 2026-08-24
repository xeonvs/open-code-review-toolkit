"""Shared authenticated GitLab identity contracts."""

from __future__ import annotations

import pytest

from ocr_toolkit.providers.gitlab_identity import (
    GitLabIdentityError,
    fetch_current_user_identity,
    parse_current_user_identity,
    valid_discussion_id,
)


def test_current_user_identity_uses_only_validated_live_id_and_username() -> None:
    identity = parse_current_user_identity(
        {
            "id": 91,
            "username": "OCR.Bot-1",
            "name": "Must not become identity authority",
            "email": "must-not-survive@example.invalid",
        }
    )

    assert identity.user_id == 91
    assert identity.username == "OCR.Bot-1"
    assert "must-not-survive" not in repr(identity)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"id": True, "username": "ocr_bot"},
        {"id": 0, "username": "ocr_bot"},
        {"id": 7, "username": "@ocr_bot"},
        {"id": 7, "username": "ocr bot"},
        {"id": 7, "username": "-ocr_bot"},
        {"id": 7, "username": "ocr_bot-"},
        {"id": 7, "username": "a" * 256},
    ],
)
def test_current_user_identity_rejects_ambiguous_fields(payload: object) -> None:
    with pytest.raises(GitLabIdentityError):
        parse_current_user_identity(payload)


def test_current_user_fetch_owns_exact_user_endpoint() -> None:
    calls: list[str] = []

    def read_json(url: str) -> object:
        calls.append(url)
        return {"id": 7, "username": "ocr_bot"}

    identity = fetch_current_user_identity("https://gitlab.example.invalid/api/v4", read_json)

    assert identity.user_id == 7
    assert calls == ["https://gitlab.example.invalid/api/v4/user"]
    with pytest.raises(GitLabIdentityError):
        fetch_current_user_identity("https://gitlab.example.invalid/api/v4/", read_json)


def test_discussion_identity_remains_closed_and_endpoint_safe() -> None:
    assert valid_discussion_id("thread_01-safe")
    for value in ("", "../thread", "thread/1", True, 7, "a" * 256):
        assert not valid_discussion_id(value)
