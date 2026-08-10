"""OCR bot note markers, fingerprints, and ownership checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ocr_toolkit.posting.comments import clean_text, code_text, comment_line, line_number

if TYPE_CHECKING:
    from ocr_toolkit.posting.gitlab import GitLabConfig

MARKER = "<!-- open-code-review-bot -->"


SUMMARY_RUN_MARKER_RE = re.compile(r"<!-- open-code-review-summary run=([0-9a-f]{32}) -->")


MANAGED_APPROVAL_RE = re.compile(
    r"<!-- open-code-review-approval v=1 user=([1-9][0-9]*) "
    r"sha=([0-9a-f]{40}) managed=true -->"
)


MANAGED_APPROVAL_SUMMARY_RE = re.compile(
    r"\A<!-- open-code-review-bot -->\r?\n"
    r"<!-- open-code-review-summary run=[0-9a-f]{32} -->\r?\n"
    r"<!-- open-code-review-approval v=1 user=([1-9][0-9]*) "
    r"sha=([0-9a-f]{40}) managed=true -->\r?\n"
    r"## Open Code Review(?:\r?\n|\Z)"
)


MARKER_WITH_FINGERPRINT_RE = re.compile(
    r"^<!-- open-code-review-bot(?:\s+fp=([0-9a-f]{8,64}))?\s*-->"
)


OCR_REPLY_COMMAND_RE = re.compile(
    r"(?i)\A[ \t]*/ocr[ \t]+(suppress|resolve)[ \t]*(?:\r?\n[ \t]*)*\Z"
)


FINGERPRINT_LEN = 32  # hex characters (= 16 raw bytes from blake2b)


@dataclass(frozen=True, slots=True)
class ManagedApprovalReceipt:
    """Proof that this toolkit user managed approval for one reviewed SHA."""

    user_id: int
    reviewed_sha: str


def build_summary_run_marker(run_id: str) -> str:
    """Render a unique bounded marker used to find the current summary note."""

    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("summary run id must be 32 lowercase hexadecimal characters")
    return f"<!-- open-code-review-summary run={run_id} -->"


def build_managed_approval_receipt(receipt: ManagedApprovalReceipt) -> str:
    """Render a versioned marker proving toolkit-managed approval ownership."""

    if receipt.user_id <= 0 or not re.fullmatch(r"[0-9a-f]{40}", receipt.reviewed_sha):
        raise ValueError("managed approval receipt fields are invalid")
    return (
        "<!-- open-code-review-approval v=1 "
        f"user={receipt.user_id} sha={receipt.reviewed_sha} managed=true -->"
    )


def managed_approval_receipt_from_body(body: str) -> ManagedApprovalReceipt | None:
    """Parse one valid managed-approval receipt from an owned summary body."""

    match = MANAGED_APPROVAL_SUMMARY_RE.match(body)
    if match is None or len(MANAGED_APPROVAL_RE.findall(body)) != 1:
        return None
    raw_user_id, reviewed_sha = match.groups()
    return ManagedApprovalReceipt(int(raw_user_id), reviewed_sha)


def _digest_payload(parts: list[str], digest_size: int = FINGERPRINT_LEN // 2) -> str:
    """Return a blake2b digest for normalized fingerprint fields."""

    return hashlib.blake2b("\n".join(parts).encode("utf-8"), digest_size=digest_size).hexdigest()


def _normalized_payload_parts(
    comment: dict[str, Any], *, line_based: bool = False
) -> list[str] | None:
    """Build shared canonical fingerprint fields, or None for invalid input."""

    path = clean_text(comment.get("path"))
    if not path:
        return None

    content = clean_text(comment.get("content"))
    suggestion = code_text(comment.get("suggestion_code"))
    existing = code_text(comment.get("existing_code"))
    category = clean_text(comment.get("category"))
    rule_id = clean_text(comment.get("rule_id"))
    line = comment_line(comment)
    if line_based:
        start_line = line_number(comment.get("start_line") or comment.get("line"))
        return [
            path.strip(),
            str(start_line),
            rule_id.lower(),
            category.lower(),
            " ".join(content.lower().split()),
            " ".join(suggestion.split()),
        ]

    parts = [
        path.strip(),
        rule_id.lower(),
        category.lower(),
        " ".join(content.lower().split()),
        " ".join(existing.split()),
        " ".join(suggestion.split()),
    ]
    if not existing.strip():
        parts.append(str(line))

    return parts


def _fingerprint_payload(comment: dict[str, Any]) -> bytes | None:
    """Build the canonical payload bytes for a fingerprint, or None."""

    parts = _normalized_payload_parts(comment)
    if parts is None:
        return None
    return "\n".join(parts).encode("utf-8")


def _line_based_fingerprint_payload(comment: dict[str, Any]) -> bytes | None:
    """Build the previous line-based payload for compatibility checks."""

    parts = _normalized_payload_parts(comment, line_based=True)
    if parts is None:
        return None
    return "\n".join(parts).encode("utf-8")


def comment_fingerprint(comment: dict[str, Any]) -> str | None:
    """Return a stable short hash describing one OCR finding.

    The hash combines path, normalized review text, and the commented code
    fragment (`existing_code`) when OCR provides it. It omits the anchor line
    only when that code anchor exists, so resolved findings and `/ocr suppress`
    survive ordinary line shifts without broadening generic no-code comments
    across a whole file. Returns None for comments missing a usable path.

    Uses 16 raw bytes (32 hex chars) to keep birthday-collision risk
    well below MR sizes the bot is likely to see. The marker regex
    accepts 8–64 hex chars, so the wider hash is forward-compatible.
    Older markers used a line-based payload; filter code checks those
    compatibility hashes alongside this value.
    """

    payload = _fingerprint_payload(comment)
    if payload is None:
        return None
    return hashlib.blake2b(payload, digest_size=FINGERPRINT_LEN // 2).hexdigest()


def line_based_comment_fingerprint(comment: dict[str, Any]) -> str | None:
    """Return the previous 32-hex line-based fingerprint for compatibility."""

    payload = _line_based_fingerprint_payload(comment)
    if payload is None:
        return None
    return hashlib.blake2b(payload, digest_size=FINGERPRINT_LEN // 2).hexdigest()


def occurrence_comment_fingerprint(comment: dict[str, Any], occurrence_index: int) -> str | None:
    """Return a fingerprint that separates repeated identical findings."""

    base = comment_fingerprint(comment)
    if base is None or occurrence_index <= 0:
        return base

    return _digest_payload([base, f"occurrence:{occurrence_index}"])


def annotate_comment_fingerprints(
    comments: list[dict[str, Any]], existing_key: str = "_ocr_fingerprint"
) -> None:
    """Attach occurrence-aware fingerprints to OCR comments in posting order."""

    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, comment in enumerate(comments):
        base = comment_fingerprint(comment)
        if base is None:
            comment.pop(existing_key, None)
            continue
        grouped.setdefault(base, []).append((index, comment))

    for base, indexed_comments in grouped.items():
        ordered_comments = sorted(
            indexed_comments,
            key=lambda item: (
                comment_line(item[1]),
                clean_text(item[1].get("path")),
                code_text(item[1].get("existing_code")),
                code_text(item[1].get("suggestion_code")),
                item[0],
            ),
        )
        for occurrence, (_index, comment) in enumerate(ordered_comments):
            comment[existing_key] = occurrence_comment_fingerprint(comment, occurrence)


def legacy_comment_fingerprint(comment: dict[str, Any]) -> str | None:
    """Return the pre-migration 16-hex fingerprint for one OCR finding.

    Why: markers produced before the 8→16 byte digest migration are still
    stored in resolved or suppressed discussions. Without this companion,
    `/ocr suppress` decisions made under the old length would silently stop
    suppressing their findings after the migration. Same line-based
    payload as the previous fingerprint implementation, narrower digest.
    """

    payload = _line_based_fingerprint_payload(comment)
    if payload is None:
        return None
    return hashlib.blake2b(payload, digest_size=8).hexdigest()


def comment_fingerprint_candidates(comment: dict[str, Any]) -> set[str]:
    """Return current and backward-compatible fingerprints for a comment."""

    annotated = comment.get("_ocr_fingerprint")
    if isinstance(annotated, str) and annotated:
        # For duplicate findings, the annotated marker is the current run's
        # identity. Do not also include the base hash: suppressing the first
        # duplicate would suppress every later duplicate in the same file.
        candidates = {annotated}
        if line_number(comment.get("start_line") or comment.get("line")) > 0:
            line_fingerprint = line_based_comment_fingerprint(comment)
            legacy_fingerprint = legacy_comment_fingerprint(comment)
            if line_fingerprint:
                candidates.add(line_fingerprint)
            if legacy_fingerprint:
                candidates.add(legacy_fingerprint)
        return {fingerprint for fingerprint in candidates if fingerprint}

    candidates = set(
        filter(
            None,
            (
                comment_fingerprint(comment),
                line_based_comment_fingerprint(comment),
                legacy_comment_fingerprint(comment),
            ),
        )
    )
    return {fingerprint for fingerprint in candidates if fingerprint}


def build_marker(fingerprint: str | None) -> str:
    """Render the OCR marker, embedding the fingerprint when available."""

    if fingerprint:
        return f"<!-- open-code-review-bot fp={fingerprint} -->"
    return MARKER


def note_starts_with_marker(body: str) -> bool:
    """Return whether a note body is owned by this script format."""

    return bool(MARKER_WITH_FINGERPRINT_RE.match(body))


def fingerprint_from_marker(body: str) -> str | None:
    """Return the fingerprint embedded in a bot marker, if any."""

    match = MARKER_WITH_FINGERPRINT_RE.match(body)
    if not match:
        return None
    return match.group(1)


def author_id_from_note(note: dict[str, Any]) -> int | None:
    """Extract author id from a published note or draft note object."""

    raw_author_id = note.get("author_id")

    if raw_author_id is None:
        author = note.get("author")
        if isinstance(author, dict):
            raw_author_id = author.get("id")

    if isinstance(raw_author_id, (str, int, float)) and not isinstance(raw_author_id, bool):
        try:
            return int(raw_author_id)
        except ValueError:
            pass
    return None


def is_diff_note(note: dict[str, Any]) -> bool:
    """Return True if a note belongs to an inline (diff) discussion.

    Such notes are owned by the /discussions cycle and must NOT be
    deleted via DELETE /notes/{id}, otherwise a reviewer-preserved
    thread (resolved, /ocr suppress, /ocr resolve) gets destroyed despite our
    decision to preserve it.
    """

    if note.get("type") == "DiffNote":
        return True
    if isinstance(note.get("position"), dict):
        return True
    return False


def is_own_bot_note(config: GitLabConfig, note: dict[str, Any], body_field: str) -> bool:
    """Return whether a note belongs to this bot and this script.

    Authorship must be positively verifiable. If `current_user_id` could
    not be resolved (see `print_user_id_failure_banner`) or the note has
    no author id, refuse to claim ownership — otherwise this bot might
    delete notes written by other users whose body happens to start with
    the same MARKER.
    """

    body = str(note.get(body_field) or "")
    if not note_starts_with_marker(body):
        return False

    if config.current_user_id is None:
        return False

    actual_author_id = author_id_from_note(note)
    if actual_author_id is None:
        return False

    return actual_author_id == config.current_user_id
