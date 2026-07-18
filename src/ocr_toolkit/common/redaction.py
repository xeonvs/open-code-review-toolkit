"""Redaction helpers for data sent to logs, GitLab, or LLM context."""

from __future__ import annotations

import os
import re
import unicodedata
import urllib.parse
from typing import Any

SENSITIVE_KEY_PATTERN = (
    r"x-api-key|api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"secret[_-]?key|refresh[_-]?token|private[_-]?token|"
    r"client[_-]?secret|aws[_-]?secret[_-]?access[_-]?key|password"
)


SENSITIVE_NAMED_KEY_PATTERN = (
    rf"(?:(?:[A-Za-z0-9]+[_.-])*(?:{SENSITIVE_KEY_PATTERN})|"
    r"(?:[A-Za-z0-9]+[_.-])*token)"
)


SENSITIVE_ENV_NAMES = (
    "OCR_LLM_TOKEN",
    "OCR_LLM_AUTH_TOKEN",
    "OCR_LLM_EXTRA_HEADERS",
    "GITLAB_API_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
)

SECRET_SHAPED_ENV_NAME_RE = re.compile(
    r"(?:^|_)(?:API_?KEY|AUTH_?TOKEN|ACCESS_?TOKEN|BEARER|CREDENTIAL|"
    r"PASSWORD|PRIVATE_?KEY|SECRET|TOKEN)(?:$|_)",
    flags=re.IGNORECASE,
)
MIN_DISCOVERED_SECRET_LENGTH = 16


REDACTION_TOKEN_SEPARATOR = r"[-_\s\u200b-\u200f\u202a-\u202e\u2060-\u206f]*"
REDACTION_TOKEN_ALIASES = {
    "authorization": "authorization",
    "proxyauthorization": "proxy-authorization",
    "bearer": "bearer",
    "xapikey": "x-api-key",
    "apikey": "api_key",
    "accesstoken": "access_token",
    "authtoken": "auth_token",
    "secretkey": "secret_key",
    "refreshtoken": "refresh_token",
    "privatetoken": "private_token",
    "clientsecret": "client_secret",
    "password": "password",
}
REDACTION_TOKEN_PATTERNS = tuple(
    (
        re.compile(
            r"(?i)(?<![A-Za-z0-9])"
            + REDACTION_TOKEN_SEPARATOR.join(re.escape(char) for char in compact)
            + r"(?![A-Za-z0-9])"
        ),
        canonical,
    )
    for compact, canonical in REDACTION_TOKEN_ALIASES.items()
)


def normalize_redaction_tokens(text: str) -> str:
    """Collapse invisible separators only inside sensitive token names.

    Preserving normal line breaks keeps diagnostics readable and prevents an
    ``Authorization`` header sweep from consuming subsequent Markdown lines.
    """

    normalized = text
    for pattern, canonical in REDACTION_TOKEN_PATTERNS:
        normalized = pattern.sub(
            lambda match: (
                canonical
                if any(
                    char.isspace() or unicodedata.category(char) in {"Cf", "Zl", "Zp"}
                    for char in match.group(0)
                )
                else match.group(0)
            ),
            normalized,
        )
    return normalized


def strip_redaction_bypass_controls(text: str) -> str:
    """Remove invisible controls that can split secret keys or values."""

    return "".join(
        char
        for char in text
        if unicodedata.category(char) not in {"Cc", "Cf", "Zl", "Zp"} or char in "\n\r\t"
    )


def strip_path_controls(text: str) -> str:
    """Remove every Unicode control/format separator from a display path."""

    return "".join(
        char for char in text if unicodedata.category(char) not in {"Cc", "Cf", "Cs", "Zl", "Zp"}
    )


def redact_env_secret_values(text: str) -> str:
    """Replace configured secret values without generic key/value sweeps."""

    if not text:
        return text

    redacted = text
    variants: set[str] = set()
    candidate_names = set(SENSITIVE_ENV_NAMES)
    candidate_names.update(
        name
        for name, value in os.environ.items()
        if len(value.strip()) >= MIN_DISCOVERED_SECRET_LENGTH
        and SECRET_SHAPED_ENV_NAME_RE.search(name)
    )
    for name in candidate_names:
        value = os.environ.get(name)
        if not value or len(value) < 4:
            continue
        normalized_value = strip_redaction_bypass_controls(value)
        for variant in (value, normalized_value):
            if not variant:
                continue
            variants.update(
                {
                    variant,
                    urllib.parse.quote(variant, safe=""),
                    urllib.parse.quote_plus(variant),
                }
            )

    for variant in sorted(variants, key=len, reverse=True):
        redacted = redacted.replace(variant, "***")

    return redacted


def redact_sensitive(text: str) -> str:
    """Replace known secret values from the process environment with `***`.

    Used before publishing OCR-controlled text to the merge request, including
    stderr excerpts from `OCR_POST_ERROR_DETAILS=1` and structured OCR JSON
    fields. Performs two passes:

    1. Replace each known env value (length >= 4). This is exact-match
       replacement over a small allowlist of secret-bearing environment
       variables, so short bot/MCP secrets still get redacted without
       broadening arbitrary text rewrites. URL-encoded forms are covered.
    2. Sweep generic patterns: whole Authorization header values regardless
       of auth scheme, `Bearer ...`, `x-api-key: ...`, JSON/key-value secrets,
       JWT-shaped values, and `token=...`. This catches values OCR may have
       logged or copied into structured JSON that did not come straight from
       one of our env vars.
    """

    if not text:
        return text

    redacted = normalize_redaction_tokens(strip_redaction_bypass_controls(text))
    redacted = redact_url_userinfo(redacted)
    redacted = redact_env_secret_values(redacted)

    # Generic high-entropy sweeps. Order matters: stricter patterns
    # first so the looser key/value pass doesn't double-redact.
    # Authorization headers are credentials regardless of auth scheme
    # (`Basic`, `ApiKey`, `Digest`, custom gateway schemes, or bare values),
    # so redact the complete header value rather than trying to parse it.
    redacted = re.sub(
        r'(?i)("(?:proxy-)?authorization"\s*:\s*")(?:[^"\\]|\\.)*(")',
        r"\1***\2",
        redacted,
    )
    redacted = re.sub(
        r"(?i)('(?:proxy-)?authorization'\s*:\s*')(?:[^'\\]|\\.)*(')",
        r"\1***\2",
        redacted,
    )
    redacted = re.sub(
        r"(?im)(\b(?:proxy-)?authorization\s*[:=]\s*)[^\r\n]+",
        r"\1***",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\bbearer\s+[A-Za-z0-9_.\-+/=~]{12,}",
        "Bearer ***",
        redacted,
    )
    # JSON-quoted form: `"token": "value"`, `"api_key": "value"`. OCR or
    # SDK error logs often serialize requests/responses this way. Redact even
    # short values because the key name already identifies the field as secret.
    redacted = re.sub(
        rf'(?i)("{SENSITIVE_NAMED_KEY_PATTERN}"\s*:\s*")' r'(?:[^"\\]|\\.)*(")',
        r"\1***\2",
        redacted,
    )
    # Named key/value form: `password=...`, `client_secret: ...`,
    # `private_token=...`. Do not require high entropy for these keys: the
    # field name itself carries enough signal, and this path is used only for
    # failure diagnostics. Handle quoted values before unquoted values so
    # spaces inside `password="..."` are not leaked.
    redacted = re.sub(
        rf'(?i)\b({SENSITIVE_NAMED_KEY_PATTERN})(\s*[:=]\s*)"(?:[^"\\]|\\.)*"',
        r'\1\2"***"',
        redacted,
    )
    redacted = re.sub(
        rf"(?i)\b({SENSITIVE_NAMED_KEY_PATTERN})(\s*[:=]\s*)'(?:[^'\\]|\\.)*'",
        r"\1\2'***'",
        redacted,
    )
    redacted = re.sub(
        rf"(?i)\b({SENSITIVE_NAMED_KEY_PATTERN})(\s*[:=]\s*)[^\"'\s,;&]+",
        r"\1\2***",
        redacted,
    )
    # Structured logs and URLs often use a bare `token=...` key. Keep it
    # bounded to query/CLI-like contexts so ordinary prose mentioning
    # "token" is not aggressively rewritten.
    redacted = re.sub(
        r"(?i)(^|[?&;\s])(token=)[A-Za-z0-9_.\-+/=~]{8,}",
        r"\1\2***",
        redacted,
    )
    # JWT pattern: three base64url segments separated by dots. The
    # header always starts with `eyJ` (base64 of `{"`); the other two
    # segments are bounded loosely — real-world JWTs always exceed this.
    redacted = re.sub(
        r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\b",
        "***",
        redacted,
    )
    return redacted


def sanitize_ocr_value(value: Any) -> Any:
    """Recursively redact OCR-controlled strings before MR publication.

    OCR JSON is model/provider-controlled output. Treat every string as
    publishable until proven otherwise: comments, warnings, tool metadata,
    and future fields all pass through this sanitizer before any formatting,
    fingerprinting, or GitLab posting logic consumes them.
    """

    if isinstance(value, str):
        return redact_sensitive(value)
    if isinstance(value, list):
        return [sanitize_ocr_value(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            sanitized_key = sanitize_ocr_value(key) if isinstance(key, str) else key
            sanitized[sanitized_key] = sanitize_ocr_value(item)
        return sanitized
    return value


def redact_url_userinfo_only(value: str) -> str:
    """Redact only URL userinfo, leaving path/query text unchanged."""

    def replace(match: re.Match[str]) -> str:
        prefix, userinfo = match.group(1), match.group(2)
        if not _is_url_userinfo_candidate(userinfo):
            return match.group(0)
        return f"{prefix}***@"

    return re.sub(
        r"(?i)([a-z][a-z0-9+.-]*://)([^/?#@]+)@"
        r"(?=[^/?#\s@]+(?:[/?#]|[\s,;.!)]|$))",
        replace,
        value,
    )


def _is_url_userinfo_candidate(userinfo: str) -> bool:
    """Return whether text before `@host` is plausibly URL userinfo."""

    normalized = "".join(
        char for char in userinfo if unicodedata.category(char) not in {"Cc", "Cf", "Zl", "Zp"}
    )
    decoded = urllib.parse.unquote(normalized)
    if not decoded or any(char in decoded for char in "/?#@"):
        return False
    if any(char.isspace() for char in userinfo):
        return ":" in decoded
    return True


def _query_key_is_sensitive(raw_key: str) -> bool:
    """Return whether a URL query key names a credential."""

    decoded = urllib.parse.unquote_plus(raw_key)
    decoded = "".join(
        char for char in decoded if unicodedata.category(char) not in {"Cc", "Cf", "Zl", "Zp"}
    )
    decoded = normalize_redaction_tokens(decoded)
    return re.fullmatch(SENSITIVE_NAMED_KEY_PATTERN, decoded, re.IGNORECASE) is not None


def _redact_sensitive_query_values(value: str) -> str:
    """Redact sensitive query-like key values, including encoded key names."""

    def replace(match: re.Match[str]) -> str:
        prefix, key, suffix = match.group(1), match.group(2), match.group(4) or ""
        if not _query_key_is_sensitive(key):
            return match.group(0)
        return f"{prefix}{key}=***{suffix}"

    return re.sub(r"(?i)(^|[?&;])([^=?#&;]+)=([^&#;\s]+)(#[^&;\s]*)?", replace, value)


def redact_url_userinfo(value: str) -> str:
    """Redact credentials embedded in URL-like manifest values."""

    value = redact_url_userinfo_only(value)
    return _redact_sensitive_query_values(value)
