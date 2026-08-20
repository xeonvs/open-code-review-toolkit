"""Deterministic toolkit-authored reference candidate grammars."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from ocr_toolkit.context.contracts import RecognizerPolicy

MAX_CANDIDATE_CHARS = 512
MAX_CANDIDATES_PER_TEXT = 64
EXPLICIT_RE = re.compile(r"\[\[context:(issue|document):([A-Za-z0-9][A-Za-z0-9._/-]{0,255})\]\]")
HTTPS_TOKEN_RE = re.compile(r"https://[^\s<>\]\[(){}\"']{1,1024}")


@dataclass(frozen=True, slots=True)
class ReferenceCandidate:
    """Represent syntax only, never adapter authorization."""

    resource_class: str
    value: str
    recognizer: str


def _normalized_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "".join(
        character
        for character in normalized
        if character == "\n" or unicodedata.category(character) not in {"Cc", "Cf", "Cs"}
    )


def recognize(
    text: str,
    *,
    resource_class: str,
    policy: RecognizerPolicy,
) -> tuple[ReferenceCandidate, ...]:
    """Return a stable collision-free candidate list from one admitted text field."""

    normalized = _normalized_text(text)
    values: list[str] = []
    if policy.type == "issue_key" and policy.prefix is not None:
        pattern = re.compile(
            rf"(?<![A-Z0-9]){re.escape(policy.prefix)}-[1-9][0-9]{{0,11}}(?![A-Z0-9])"
        )
        values = [match.group(0) for match in pattern.finditer(normalized)]
    elif (
        policy.type == "https_url" and policy.origin is not None and policy.path_prefix is not None
    ):
        expected = urlsplit(policy.origin)
        for match in HTTPS_TOKEN_RE.finditer(normalized):
            candidate = match.group(0).rstrip(".,;:!?")
            parsed = urlsplit(candidate)
            if (
                parsed.scheme == "https"
                and parsed.username is None
                and parsed.password is None
                and parsed.hostname == expected.hostname
                and parsed.port == expected.port
                and parsed.path.startswith(policy.path_prefix)
                and ".." not in parsed.path.split("/")
                and not parsed.fragment
            ):
                values.append(
                    urlunsplit(("https", parsed.netloc.lower(), parsed.path, parsed.query, ""))
                )
    elif policy.type == "explicit":
        values = [
            match.group(2)
            for match in EXPLICIT_RE.finditer(normalized)
            if match.group(1) == resource_class
        ]
    seen: set[str] = set()
    result: list[ReferenceCandidate] = []
    for value in values:
        if not value or len(value) > MAX_CANDIDATE_CHARS or len(value.encode("utf-8")) > 2_048:
            continue
        identity = value.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        result.append(
            ReferenceCandidate(
                resource_class=resource_class,
                value=value,
                recognizer=policy.type,
            )
        )
        if len(result) >= MAX_CANDIDATES_PER_TEXT:
            break
    return tuple(result)
