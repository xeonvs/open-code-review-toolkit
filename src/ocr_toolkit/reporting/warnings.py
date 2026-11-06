"""Pure legacy warning text projection; metadata and admission stay separate."""

from __future__ import annotations

from typing import Any

from ocr_toolkit.reporting.text import clean_text


def ocr_warning_text(warning: Any, *, _seen: set[int] | None = None) -> str:
    """Return warning text relevant for provider failure classification."""

    if _seen is None:
        _seen = set()
    if isinstance(warning, (dict, list)):
        marker = id(warning)
        if marker in _seen:
            return ""
        _seen.add(marker)
    if isinstance(warning, dict):
        parts: list[str] = []
        for key in ("type", "message", "code", "status", "status_code", "detail"):
            text = clean_text(warning.get(key))
            if text:
                parts.append(f"{key}: {text}" if key in {"code", "status", "status_code"} else text)
        for key in ("error", "details"):
            nested = warning.get(key)
            if isinstance(nested, dict):
                text = ocr_warning_text(nested, _seen=_seen)
                if text:
                    parts.append(text)
            else:
                text = clean_text(nested)
                if text:
                    parts.append(text)
        return "\n".join(parts)[:4000]
    if isinstance(warning, list):
        return "\n".join(
            text for value in warning[:40] if (text := ocr_warning_text(value, _seen=_seen))
        )[:4000]
    return clean_text(warning)
