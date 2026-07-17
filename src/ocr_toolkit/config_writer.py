"""Write Open Code Review configuration without exposing secrets in argv."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class OCRConfigError(Exception):
    """OCR configuration could not be read or written safely."""


def ocr_config_path() -> Path:
    """Return the OCR config path for the current HOME."""

    return Path.home() / ".opencodereview" / "config.json"


def read_ocr_config(path: Path | None = None) -> dict[str, Any]:
    """Read OCR config JSON, returning an empty config when it is absent."""

    config_path = path or ocr_config_path()
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OCRConfigError(f"OCR config is not valid JSON: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise OCRConfigError(f"OCR config is not valid UTF-8: {exc}") from exc
    except OSError as exc:
        raise OCRConfigError(f"cannot read OCR config: {exc}") from exc
    if not isinstance(data, dict):
        raise OCRConfigError("OCR config top-level value is not an object")
    return data


def write_ocr_config(config: Mapping[str, Any], path: Path | None = None) -> None:
    """Atomically write OCR config with owner-only permissions."""

    config_path = path or ocr_config_path()
    try:
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(config_path.parent, 0o700)
    except OSError as exc:
        raise OCRConfigError(f"cannot prepare OCR config directory: {exc}") from exc

    payload = json.dumps(config, ensure_ascii=False, indent=4, sort_keys=True) + "\n"
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=config_path.parent,
            prefix="config.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_name = tmp_file.name
            os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
            tmp_file.write(payload)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, config_path)
        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise OCRConfigError(f"cannot write OCR config: {exc}") from exc


def set_config_path(config: dict[str, Any], dotted_key: str, value: Any) -> None:
    """Set a dotted OCR config key in-place."""

    parts = [part for part in dotted_key.split(".") if part]
    if not parts:
        raise OCRConfigError("empty OCR config key")
    cursor: dict[str, Any] = config
    for part in parts[:-1]:
        existing = cursor.get(part)
        if existing is None:
            existing = {}
            cursor[part] = existing
        elif not isinstance(existing, dict):
            raise OCRConfigError(
                f"OCR config key {part!r} is not an object; refusing to overwrite it"
            )
        cursor = existing
    cursor[parts[-1]] = value


def update_ocr_config(values: Mapping[str, Any], path: Path | None = None) -> None:
    """Read, update, and write OCR config for dotted keys."""

    config = read_ocr_config(path)
    for key, value in values.items():
        set_config_path(config, key, value)
    write_ocr_config(config, path)
