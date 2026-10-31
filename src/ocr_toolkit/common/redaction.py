"""Redaction helpers for data sent to logs, GitLab, or LLM context."""

from __future__ import annotations

import os
import re
import unicodedata
import urllib.parse
from bisect import bisect_right
from collections.abc import Iterator
from typing import Any

from ocr_toolkit.common.value_boundaries import complete_carrier as _complete_credential_carrier
from ocr_toolkit.common.value_boundaries import complete_value

SENSITIVE_KEY_PATTERN = (
    r"x-api-key|api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"secret[_-]?key|refresh[_-]?token|private[_-]?token|"
    r"client[_-]?secret|aws[_-]?secret[_-]?access[_-]?key|password"
)


SENSITIVE_NAMED_KEY_PATTERN = (
    rf"(?:(?:[A-Za-z0-9]+[_.-])*(?:{SENSITIVE_KEY_PATTERN})|"
    r"(?:[A-Za-z0-9]+[_.-])*token)"
)
_MATERIAL_KEY_HINT = re.compile(rf"(?i)(?:{SENSITIVE_KEY_PATTERN}|token|authorization)")

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
_ASCII_BYPASS_CONTROLS = {code: None for code in (*range(32), 127) if chr(code) not in "\n\r\t"}


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

    if text.isascii():
        return text.translate(_ASCII_BYPASS_CONTROLS)
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


def _complete_credential_value(text: str, end: int, *, start: int | None = None) -> bool:
    """Require a terminal value, not a prefix of concatenation or a call.

    One unambiguous matching outer quote may close its carrier. Arbitrary
    quotes cannot prove an empty prefix is the whole value.
    """

    cursor = end
    while cursor < len(text) and text[cursor] in " \t":
        cursor += 1
    if start is not None and cursor < len(text) and text[cursor] in "\"'":
        quote = text[cursor]
        opening = text.rfind(quote, max(0, start - 1024), start)
        carrier = opening >= 0 and (opening == 0 or text[opening - 1] not in "\\\"'")
        # An unquoted mask can be inside a path or other quoted carrier. Its
        # entire prefix must be unambiguous; quote runs never prove a carrier.
        prefix = text[opening + 1 : cursor] if carrier else ""
        single = opening == start - 1 or (
            text[end - 1] not in "\"'" and not any(c in prefix for c in (quote, "\\", "\r", "\n"))
        )
        if carrier and single and text[end - 1] != quote:
            return _complete_credential_carrier(text, cursor + 1)
    return complete_value(text, end)


def masked_credential_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Locate canonical masks so display interpretation cannot erase them."""

    if "***" not in text:
        return ()
    spans = {
        match.span("value")
        for pattern, _replacement in (*_AUTH_RULES, *_ASSIGNMENT_RULES)
        for match in pattern.finditer(text)
        if match["value"] == "***"
        and _complete_credential_value(text, match.end(), start=match.start())
    }
    # URI carriers have their own proven boundaries. A closing carrier quote
    # must not require granting the same authority to arbitrary quote runs.
    for query, end, empty, qualified in _material_queries(text):
        if empty and qualified:
            start = query.end()
            while start < end and text[start].isspace():
                start += 1
            if text[start:end] == "***":
                spans.add((start, end))
            elif text[start:end] in {"'***'", '"***"'}:
                spans.add((start + 1, end - 1))
    return tuple(sorted(spans))


def _credential_material(text: str) -> bool:
    if (":" not in text and "=" not in text) or not _MATERIAL_KEY_HINT.search(text):
        return False
    # Resolve complete quoted values first. The broader fallback expressions
    # must not reinterpret a closing quote as a new credential. Binary search
    # avoids quadratic work for documents containing many empty/masked fields.
    # A proven empty query qualifies only its key, never a broad regex match
    # spanning a fragment, source wrapper or a subsequent credential field.
    parts = []
    previous = 0
    for query, _end, empty, qualified in _material_queries(text):
        if empty and qualified:
            start, end = query.span(2)
            parts.extend((text[previous:start], "x" * (end - start)))
            previous = end
    if parts:
        parts.append(text[previous:])
        text = "".join(parts)
    safe_fields: set[tuple[int, int]] = set()
    for pattern, _replacement in (*_AUTH_RULES, *_ASSIGNMENT_RULES):
        if "suffix" not in pattern.groupindex:
            continue
        for match in pattern.finditer(text):
            if match["value"] not in {"", "***"} or not _complete_credential_value(
                text, match.end(), start=match.start()
            ):
                return True
            safe_fields.add(match.span())
    ordered_fields = sorted(safe_fields)
    for pattern, _replacement in (*_AUTH_RULES, *_ASSIGNMENT_RULES):
        if "suffix" in pattern.groupindex:
            continue
        for match in pattern.finditer(text):
            index = bisect_right(ordered_fields, (match.start(), len(text) + 1)) - 1
            if index >= 0 and match.end() <= ordered_fields[index][1]:
                continue
            if match["value"] in {"", "***"} and _complete_credential_value(
                text, match.end(), start=match.start()
            ):
                continue
            return True
    return False


_QUERY_VALUE_RE = re.compile(r"(?i)(^|[?&;])([^=?#&;]+)=([^&#;\s]+)(#[^&;\s]*)?")
# Diagnostic replacement and material classification have distinct grammars.
# A key-only iterator cannot consume another credential inside a wrapper tail.
_QUERY_KEY_RE = re.compile(r"(?i)(^|[?&;])([^=?#&;\s]+)=")
_QUERY_END_RE = re.compile(r"[&#\s]")
_EMPTY_QUERY_VALUE_RE = re.compile(r"(?:(?P<quote>['\"])(?:\*\*\*|)(?P=quote)|\*\*\*)")
_URI_CARRIER = re.compile(r"(?P<quote>['\"])[A-Za-z][A-Za-z0-9+.-]{0,31}:[^\s\"'<>]*$")
_URI_SCHEME = re.compile(r"(?<![\w.+-])[A-Za-z][A-Za-z0-9+.-]{0,31}://")
_SOURCE_BREAK = re.compile(r"[\s\"'<>]")


def _material_queries(text: str) -> Iterator[tuple[re.Match[str], int, bool, bool]]:
    """Walk complete sensitive values without granting authority to their tails."""

    cursor = 0
    while (query := _QUERY_KEY_RE.search(text, cursor)) is not None:
        cursor = query.end()
        if not _query_key_is_sensitive(query[2]):
            continue
        start = cursor
        # Assignment detectors allow leading whitespace. A URI-shaped prefix
        # must not turn that same whitespace into proof of an empty value.
        while start < len(text) and text[start].isspace():
            start += 1
        qualified = not query[1] or query.start() == 0
        safe = _EMPTY_QUERY_VALUE_RE.match(text, start)
        if not query[1] and safe is not None and safe["quote"]:
            end = safe.end()
            empty = complete_value(text, end)
        else:
            left = max(0, query.start() - 1024)
            window = text[left : query.start()]
            carrier = _URI_CARRIER.search(window)
            ambiguous_carrier = False
            if carrier is not None:
                opening = left + carrier.start("quote")
                if opening and text[opening - 1] in "\\\"'":
                    carrier = None
                    ambiguous_carrier = True
            token_start = max((part.end() for part in _SOURCE_BREAK.finditer(window)), default=0)
            qualified = (
                qualified
                or carrier is not None
                or _URI_SCHEME.search(window, token_start) is not None
            )
            closing = text.find(carrier["quote"], start) if carrier is not None else -1
            if closing == start and not _complete_credential_carrier(text, closing + 1):
                # An opening query-value quote cannot also prove the carrier's
                # end. Ambiguous nested quoting retains ordinary checks.
                closing = -1
            if closing >= 0 and text[closing - 1 : closing] == "\\":
                closing = -1
            # Bound the delimiter search before a proven source-string end;
            # otherwise adjacent quoted URLs could rescan the entire suffix.
            maximum = closing if closing >= 0 else len(text)
            boundary = _QUERY_END_RE.search(text, start, maximum)
            end = boundary.start() if boundary else maximum
            closed = closing >= 0 and end == closing
            empty = start == end or _EMPTY_QUERY_VALUE_RE.fullmatch(text, start, end) is not None
            empty = empty and not ambiguous_carrier
            if closed and not _complete_credential_carrier(text, end + 1):
                empty = False
            if (
                end < len(text)
                and text[end].isspace()
                and not _complete_credential_value(text, end)
            ):
                empty = False
        yield query, end, empty, qualified
        cursor = max(cursor, end)


def _query_has_material(text: str) -> bool:
    """Classify complete values; diagnostic replacement may consume wrappers."""

    return any(not empty for _query, _end, empty, _qualified in _material_queries(text))


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
        or _query_has_material(credential)
        or _BEARER_RE.search(prepared)
        or _JWT_RE.search(prepared)
        or _credential_material(credential)
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

    return _QUERY_VALUE_RE.sub(replace, value)


def redact_url_userinfo(value: str) -> str:
    """Redact credentials embedded in URL-like manifest values."""

    value = redact_url_userinfo_only(value)
    return _redact_sensitive_query_values(value)
