"""Select local native ChatGPT auth without reading or copying OCR credentials."""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ocr_toolkit.provider_config import ProviderConfigError, request_controls_from_environment

CHATGPT_OCR_VERSIONS = frozenset({"1.13.2"})
_CONFLICTING_SETTINGS = (
    "OCR_LLM_URL",
    "OCR_LLM_TOKEN",
    "OCR_LLM_PROTOCOL",
    "OCR_LLM_AUTH_HEADER",
    "OCR_LLM_EXTRA_HEADERS",
    "OCR_LLM_MODELS_URL",
    "OCR_LLM_ALLOWED_MODELS",
    "OCR_LLM_MAX_COMPLETION_TOKENS",
    "OCR_ANTHROPIC_DISABLE_THINKING",
)
_BODY_FIELDS = frozenset({"reasoning", "text", "prompt_cache_key"})


class LocalChatGPTError(ValueError):
    """Report a closed local-auth configuration or metadata failure."""


def auth_mode(environment: Mapping[str, str], *, local: bool = False) -> str:
    """Reject unsupported auth channels before credential or filesystem access."""

    mode = environment.get("OCR_LLM_AUTH_MODE", "api-key").strip()
    if mode not in {"api-key", "chatgpt"}:
        raise LocalChatGPTError("OCR_LLM_AUTH_MODE must be api-key or chatgpt")
    if mode == "chatgpt" and not local:
        raise LocalChatGPTError("ChatGPT authentication requires explicit --local mode")
    return mode


def provider_entry(environment: Mapping[str, str]) -> dict[str, Any]:
    """Project only native provider fields supported by qualified OCR."""

    if any(environment.get(name, "").strip() for name in _CONFLICTING_SETTINGS):
        raise LocalChatGPTError(
            "ChatGPT authentication conflicts with API URL, credentials, protocol, headers, "
            "model validation, or completion-cap settings; unset API-only settings"
        )
    if "OCR_USE_ANTHROPIC" in environment or environment.get(
        "OCR_LLM_VALIDATE_MODEL", "false"
    ).strip().lower() not in {"", "false"}:
        raise LocalChatGPTError("ChatGPT authentication does not support API model validation")
    controls_environment = {
        "OCR_LLM_PROTOCOL": "openai-responses",
        "OCR_LLM_EXTRA_BODY": environment.get("OCR_LLM_EXTRA_BODY", ""),
        "OCR_LLM_REASONING_EFFORT": environment.get("OCR_LLM_REASONING_EFFORT", ""),
    }
    try:
        controls = request_controls_from_environment(controls_environment)
    except ProviderConfigError as exc:
        raise LocalChatGPTError(str(exc)) from exc
    entry: dict[str, Any] = {}
    model = environment.get("OCR_LLM_MODEL", "").strip()
    if model:
        if len(model) > 512 or any(ord(character) < 32 for character in model):
            raise LocalChatGPTError("ChatGPT model must be a bounded single-line identifier")
        entry["model"] = model
    if controls.extra_body is not None:
        if set(controls.extra_body) - _BODY_FIELDS:
            raise LocalChatGPTError(
                "ChatGPT extra body supports only reasoning, text, and prompt_cache_key"
            )
        entry["extra_body"] = controls.extra_body
    return entry


def require_supported_version(version: str) -> None:
    """Keep native auth limited to the separately qualified OCR release."""

    if version not in CHATGPT_OCR_VERSIONS:
        raise LocalChatGPTError("ChatGPT authentication requires qualified OCR 1.13.2")


def _directory(path: Path, *, private: bool = False, owned: bool = False) -> None:
    """Check a directory without following symlinks or trusting writable ancestors."""

    metadata = path.lstat()
    uid = os.getuid()
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in {0, uid}:
        raise LocalChatGPTError("native ChatGPT auth directory is unsafe")
    if owned and metadata.st_uid != uid:
        raise LocalChatGPTError("native ChatGPT auth directory is not operator-owned")
    # A root-owned sticky ancestor (for example /tmp) cannot replace an existing
    # operator-owned child. Other group/world-writable ancestors are unsafe.
    sticky_root = metadata.st_uid == 0 and bool(mode & stat.S_ISVTX)
    if (mode & 0o022 and not sticky_root) or (private and mode != 0o700):
        raise LocalChatGPTError("native ChatGPT auth directory permissions are unsafe")


def _native_file(path: Path, *, limit: int, required: bool = True) -> None:
    """Inspect bounded native file metadata only; OCR alone reads credential bytes."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if not required:
            return
        raise LocalChatGPTError(
            "native ChatGPT registration is unavailable; run ocr auth login --provider chatgpt"
        ) from None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_size > limit
        or (required and metadata.st_size == 0)
    ):
        raise LocalChatGPTError("native ChatGPT auth file metadata is unsafe")


def native_store(environment: Mapping[str, str]) -> Path:
    """Validate the original HOME's native store without inspecting account contents."""

    if not hasattr(os, "getuid"):
        raise LocalChatGPTError("local ChatGPT authentication requires POSIX ownership checks")
    raw_home = environment.get("HOME", "")
    home = Path(raw_home)
    if (
        not raw_home
        or not home.is_absolute()
        or str(home) != raw_home
        or ".." in home.parts
        or any(ord(character) < 32 for character in raw_home)
    ):
        raise LocalChatGPTError("native ChatGPT HOME must be an absolute lexical path")
    store = home / ".opencodereview" / "auth" / "chatgpt"
    try:
        for ancestor in (*reversed(home.parents), home):
            _directory(ancestor, owned=ancestor == home)
        _directory(home / ".opencodereview", owned=True)
        _directory(home / ".opencodereview" / "auth", owned=True)
        _directory(store, private=True, owned=True)
        _native_file(store / "accounts.json", limit=1_000_000)
        _native_file(store / "host.json", limit=16_384)
        _native_file(store / "session.lock", limit=0, required=False)
    except OSError as exc:
        raise LocalChatGPTError(
            "native ChatGPT registration is unavailable; run ocr auth login --provider chatgpt"
        ) from exc
    return store


def link_native_store(store: Path, session_home: Path) -> None:
    """Share the native directory so OCR retains one lock and refresh/host lifecycle."""

    checked = native_store({"HOME": str(store.parents[2])})
    if checked != store:
        raise LocalChatGPTError("native ChatGPT auth store binding changed")
    try:
        _directory(session_home, private=True, owned=True)
        config_directory = session_home / ".opencodereview"
        _directory(config_directory, private=True, owned=True)
        parent = config_directory / "auth"
        parent.mkdir(mode=0o700)
        _directory(parent, private=True, owned=True)
        (parent / "chatgpt").symlink_to(store, target_is_directory=True)
    except OSError as exc:
        raise LocalChatGPTError("native ChatGPT store could not be linked privately") from exc
