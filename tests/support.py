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


def review_receipt_v7(
    *,
    usage: dict[str, int] | None = None,
    attempted: dict[str, int] | None = None,
    completed: dict[str, int] | None = None,
    context_tool_usage: dict[str, int] | None = None,
    mandatory: bool = True,
) -> dict[str, Any]:
    """Return one exact synthetic receipt v7 for posting-boundary tests."""

    attempted = (
        attempted
        if attempted is not None
        else {
            "summary": 1,
            "list": 0,
            "get": 0,
            "search": 0,
            "coverage": 0,
            "unattributed": 0,
        }
    )
    completed = (
        completed
        if completed is not None
        else {
            "summary": 1,
            "list": 0,
            "get": 0,
            "search": 0,
            "coverage": 0,
        }
    )
    context_tool_usage = (
        context_tool_usage
        if context_tool_usage is not None
        else {"context_get": 0, "context_list": 0}
    )
    evidence_calls = sum(attempted.values())
    builtin_calls = evidence_calls + sum(context_tool_usage.values())
    usage = usage if usage is not None else {"ocr_toolkit_evidence": builtin_calls}
    enriched = any(context_tool_usage.values())
    builtin_tools = [
        "ocr_toolkit_evidence",
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
    ]
    if enriched:
        builtin_tools.extend(("context_list", "context_get"))
    capabilities = [
        {
            "server": "ocr_toolkit_evidence",
            "transport": "builtin",
            "tools": builtin_tools,
        }
    ]
    capabilities.extend(
        {
            "server": server,
            "transport": "remote",
            "tools": [f"{server}_read"],
        }
        for server in usage
        if server != "ocr_toolkit_evidence"
    )
    return {
        "schema_version": 7,
        "review": {
            "source_sha": "a" * 40,
            "policy_sha": "b" * 40,
            "target_sha": "b" * 40,
            "target_protection": "protected",
            "mr_author_id": 41,
        },
        "context": {
            "mode": "enriched" if enriched else "off",
            "state": "complete" if enriched else "disabled",
            "classes": (
                ["merge_request_metadata", "forge_discussions", "external_records"]
                if enriched
                else []
            ),
            "policy_digest": "c" * 64 if enriched else None,
            "per_source": {},
            "degradation_counts": {"invalid": 0, "limit": 0, "unavailable": 0},
            "required_degraded": False,
            "mutable_admitted": False,
            "tool_usage": context_tool_usage,
        },
        "mcp": {"capabilities": capabilities, "usage": usage},
        "evidence": {
            "mandatory": mandatory,
            "used": sum(completed.values()) > 0,
            "calls": evidence_calls,
            "actions": {
                "state": "verified",
                "attempted": attempted,
                "completed": completed,
            },
        },
        "publication": {"state": "passed"},
        "cleanup": {"result": "passed"},
    }
