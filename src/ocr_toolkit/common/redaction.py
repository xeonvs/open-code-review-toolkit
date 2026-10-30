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

_SECRET_ASSIGNMENT_KEY_PATTERN = (
    rf'(?:"{SENSITIVE_NAMED_KEY_PATTERN}"|'
    rf"'{SENSITIVE_NAMED_KEY_PATTERN}'|\b{SENSITIVE_NAMED_KEY_PATTERN})"
)
_UNTERMINATED_SECRET_RE = re.compile(
    rf"(?im)(?P<prefix>{_SECRET_ASSIGNMENT_KEY_PATTERN}[ \t]*[:=][ \t]*(?P<quote>[\"']))"
    r"(?P<value>(?:\\[^\r\n]|(?!(?P=quote))[^\\\r\n])+(?:\\)?)(?=\r?$)"
)

# The value capture is shared by semantic admission and diagnostic replacement.
# Admission never infers a credential from normalization or formatting changes.
_AUTH_RULES = (
    (
        re.compile(
            r'(?i)(?P<prefix>"(?:proxy-)?authorization"\s*:\s*")(?P<value>(?:[^"\\]|\\.)*)(?P<suffix>")'
        ),
        r"\g<prefix>***\g<suffix>",
    ),
    (
        re.compile(
            r"(?i)(?P<prefix>'(?:proxy-)?authorization'\s*:\s*')(?P<value>(?:[^'\\]|\\.)*)(?P<suffix>')"
        ),
        r"\g<prefix>***\g<suffix>",
    ),
    (
        re.compile(r"(?im)(?P<prefix>\b(?:proxy-)?authorization\s*[:=]\s*)(?P<value>[^\r\n]+)"),
        r"\g<prefix>***",
    ),
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_.\-+/=~]{12,}")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\b")
_ASSIGNMENT_RULES = (
    (
        re.compile(
            rf'(?i)(?P<prefix>"{SENSITIVE_NAMED_KEY_PATTERN}"\s*:\s*")(?P<value>(?:[^"\\]|\\.)*)(?P<suffix>")'
        ),
        r"\g<prefix>***\g<suffix>",
    ),
    (
        re.compile(
            rf'(?i)(?P<prefix>{_SECRET_ASSIGNMENT_KEY_PATTERN}\s*[:=]\s*")(?P<value>(?:[^"\\]|\\.)*)(?P<suffix>")'
        ),
        r"\g<prefix>***\g<suffix>",
    ),
    (
        re.compile(
            rf"(?i)(?P<prefix>{_SECRET_ASSIGNMENT_KEY_PATTERN}\s*[:=]\s*')(?P<value>(?:[^'\\]|\\.)*)(?P<suffix>')"
        ),
        r"\g<prefix>***\g<suffix>",
    ),
    (_UNTERMINATED_SECRET_RE, r"\g<prefix>***"),
    (
        re.compile(
            rf"(?i)(?P<prefix>\b{SENSITIVE_NAMED_KEY_PATTERN}\s*[:=]\s*)(?P<value>[^\"'\s,;&]+)"
        ),
        r"\g<prefix>***",
    ),
    (
        re.compile(r"(?i)(?P<prefix>(?:^|[?&;\s])token=)(?P<value>[A-Za-z0-9_.\-+/=~]{8,})"),
        r"\g<prefix>***",
    ),
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


def environment_secret_values() -> tuple[str, ...]:
    """Snapshot effective exact/encoded values for one admission, without a global cache."""

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
        for variant in (
            value,
            normalized_value,
            unicodedata.normalize("NFC", value),
            unicodedata.normalize("NFC", normalized_value),
        ):
            if not variant:
                continue
            variants.update(
                {
                    variant,
                    urllib.parse.quote(variant, safe=""),
                    urllib.parse.quote_plus(variant),
                }
            )

    return tuple(sorted(variants, key=len, reverse=True))


def redact_env_secret_values(text: str, *, values: tuple[str, ...] | None = None) -> str:
    """Replace configured values; a caller may reuse one immutable admission snapshot."""

    if not text:
        return text
    redacted = text
    for variant in environment_secret_values() if values is None else values:
        redacted = redacted.replace(variant, "***")
    return redacted


def has_sensitive_material(
    text: str,
    *,
    credential_view: str | None = None,
    values: tuple[str, ...] | None = None,
) -> bool:
    """Classify publication material using shared rules, not diagnostic rewrites."""

    values = environment_secret_values() if values is None else values
    # A decoded passphrase may itself contain words rewritten by token-name
    # canonicalization. Its incoming representation is independently sensitive.
    if redact_env_secret_values(text, values=values) != text:
        return True
    prepared = normalize_redaction_tokens(strip_redaction_bypass_controls(text))
    view = text if credential_view is None else credential_view
    credential = (
        prepared
        if view == text
        else normalize_redaction_tokens(strip_redaction_bypass_controls(view))
    )
    return bool(
        redact_env_secret_values(prepared, values=values) != prepared
        or redact_url_userinfo_only(prepared) != prepared
        or _redact_sensitive_query_values(credential) != credential
        or _BEARER_RE.search(prepared)
        or _JWT_RE.search(prepared)
        or any(
            # A canonical already-masked candidate contains no credential left.
            # Token normalization alone is not evidence of a secret.
            match["value"] != "***"
            for pattern, _replacement in (*_AUTH_RULES, *_ASSIGNMENT_RULES)
            for match in pattern.finditer(credential)
        )
    )


def redact_sensitive(text: str) -> str:
    """Replace known secret values from the process environment with `***`.

    Used before publishing OCR-controlled text to the merge request and when
    rendering bounded local diagnostics from structured OCR JSON fields.
    Performs two passes:

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
    for pattern, replacement in _AUTH_RULES:
        redacted = pattern.sub(replacement, redacted)
    redacted = _BEARER_RE.sub("Bearer ***", redacted)
    for pattern, replacement in _ASSIGNMENT_RULES:
        redacted = pattern.sub(replacement, redacted)
    return _JWT_RE.sub("***", redacted)


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
