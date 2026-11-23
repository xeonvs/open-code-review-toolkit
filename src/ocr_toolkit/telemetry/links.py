"""Validate credential-free HTTPS locations shared by telemetry boundaries."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
AUTHORITY = re.compile(rf"{HOST_LABEL}(?:\.{HOST_LABEL})*(?::[0-9]+)?", re.IGNORECASE | re.ASCII)
INSTANCE_PATH = re.compile(r"(?:/[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}){0,8}")
SLUG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,254}")


def project_path(value: object) -> str | None:
    """Accept one bounded, repository-relative GitLab namespace and project slug."""

    if not isinstance(value, str) or len(value) > 512:
        return None
    parts = value.split("/")
    return value if len(parts) >= 2 and all(SLUG.fullmatch(part) for part in parts) else None


def web_location(link: object) -> tuple[str, str] | None:
    """Return the authority and path of one bounded credential-free HTTPS URL."""

    if (
        not isinstance(link, str)
        or len(link) > 1024
        or any(
            character.isspace() or ord(character) < 32 or character in "\x7f?#\\"
            for character in link
        )
    ):
        return None
    try:
        url = urlsplit(link)
        port = url.port
    except ValueError:
        return None
    if (
        url.scheme != "https"
        or not url.hostname
        or len(url.hostname) > 253
        or AUTHORITY.fullmatch(url.netloc) is None
        or port == 0
    ):
        return None
    authority = f"{url.hostname}:{port}" if port and port != 443 else url.hostname
    return authority, url.path
