"""GitLab API access for OCR MR posting."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.posting.payloads import (
    build_marked_note_body,
    note_body_budget,
    truncate_note_body,
    truncate_plain_text,
)
from ocr_toolkit.posting.settings import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    MAX_API_ERROR_BODY_BYTES,
    MAX_API_RESPONSE_BODY_BYTES,
    MAX_INLINE_NOTE_CHARS,
    MAX_NOTE_CHARS,
    getenv,
    post_mode,
)


@dataclass(frozen=True)
class GitLabConfig:
    """GitLab API configuration derived from CI environment variables."""

    server_url: str
    project_id: str
    merge_request_iid: str
    api_token: str
    auth_header: str
    current_user_id: int | None

    @property
    def api_base(self) -> str:
        """Return the GitLab Merge Request API base URL."""

        encoded_project = urllib.parse.quote_plus(self.project_id)
        return (
            f"{self.server_url}/api/v4/projects/{encoded_project}"
            f"/merge_requests/{self.merge_request_iid}"
        )


@dataclass(frozen=True)
class GitLabWriteResult:
    """Detailed result for non-idempotent GitLab write calls."""

    status: str
    response: Any | None = None
    http_status: int | None = None

    @property
    def posted(self) -> bool:
        return self.status == "posted"

    @property
    def invalid_position(self) -> bool:
        return self.status == "invalid_position"

    @property
    def write_failed(self) -> bool:
        return self.status == "write_failed"


class GitLabResponseTooLarge(Exception):
    """GitLab response exceeded the bounded read budget."""


class _SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow HTTPS redirects only within the configured GitLab origin."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        if request.get_method() not in {"GET", "HEAD"}:
            return None
        redirected = super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )
        if redirected is None:
            return None
        try:
            original = urllib.parse.urlsplit(request.full_url)
            destination = urllib.parse.urlsplit(redirected.full_url)
            original_port = original.port or 443
            destination_port = destination.port or 443
        except ValueError:
            return None
        if (
            original.scheme.lower() != "https"
            or destination.scheme.lower() != "https"
            or original.hostname != destination.hostname
            or destination.username is not None
            or destination.password is not None
            or original_port != destination_port
        ):
            return None
        return redirected


def _open_gitlab_request(request: urllib.request.Request) -> Any:
    """Open one GitLab request with redirect handling disabled."""

    return urllib.request.build_opener(_SameOriginRedirectHandler()).open(
        request, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS
    )


def _read_limited_response(response: Any) -> bytes:
    """Read a GitLab response body and fail when it exceeds the success budget."""

    body: bytes = response.read(MAX_API_RESPONSE_BODY_BYTES)
    if len(body) >= MAX_API_RESPONSE_BODY_BYTES and response.read(1):
        raise GitLabResponseTooLarge(f"GitLab response exceeds {MAX_API_RESPONSE_BODY_BYTES} bytes")
    return body


def _retry_after_seconds(header_value: str | None) -> float | None:
    """Parse a `Retry-After` header: integer seconds or an HTTP-date."""

    if not header_value:
        return None
    header_value = header_value.strip()
    if not header_value:
        return None
    try:
        return max(0.0, float(header_value))
    except ValueError:
        pass
    try:
        # email.utils handles RFC 7231 IMF-fixdate without depending on
        # locale or pulling in third-party libraries.
        from datetime import datetime, timezone
        from email.utils import parsedate_to_datetime

        when = parsedate_to_datetime(header_value)
        delta = (when - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delta)
    except (TypeError, ValueError):
        return None


def api_request_url(
    url: str,
    api_token: str,
    auth_header: str,
    data: dict[str, Any] | None = None,
    method: str = "GET",
) -> Any | None:
    """Call a GitLab API URL and return parsed JSON, `{}` for empty success, or None."""

    headers = {
        auth_header: api_token,
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)

    retryable_statuses = {429, 500, 502, 503, 504}
    # Only GET is retried. GitLab note writes do not expose an idempotency
    # key here: retrying create, publish, update/resolve, or delete after a
    # lost response can duplicate notes or treat an already-completed write
    # as a failure and trigger destructive cleanup.
    max_attempts = 3 if method.upper() == "GET" else 1
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        retry_after: float | None = None
        try:
            with _open_gitlab_request(request) as response:
                raw = _read_limited_response(response).decode("utf-8", errors="replace")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            message = truncate_plain_text(
                redact_sensitive(
                    exc.read(MAX_API_ERROR_BODY_BYTES).decode("utf-8", errors="replace")
                ),
                2000,
            )
            if exc.code not in retryable_statuses or attempt == max_attempts - 1:
                print(
                    f"GitLab API error {exc.code} for {method} {url}: {message}",
                    file=sys.stderr,
                )
                return None
            retry_after = _retry_after_seconds(
                exc.headers.get("Retry-After") if exc.headers is not None else None
            )
            last_error = exc
        except GitLabResponseTooLarge as exc:
            print(f"GitLab API response too large for {method} {url}: {exc}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == max_attempts - 1:
                print(
                    f"GitLab API request failed for {method} {url}: {redact_sensitive(str(exc))}",
                    file=sys.stderr,
                )
                return None
            last_error = exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"GitLab API returned invalid JSON for {method} {url}: {exc}", file=sys.stderr)
            return None

        if retry_after is not None:
            time.sleep(min(max(retry_after, 0.0), 60.0))
        else:
            time.sleep(min(1.0 + attempt, 5.0))

    if last_error is not None:
        print(
            f"GitLab API request failed for {method} {url}: {redact_sensitive(str(last_error))}",
            file=sys.stderr,
        )
    return None


def _parse_response_body(response: bytes) -> Any:
    """Parse a GitLab response body as JSON or return `{}` for empty success."""

    if not response:
        return {}
    return json.loads(response.decode("utf-8"))


def _is_invalid_position_error(status: int, body: str) -> bool:
    """Return whether GitLab rejected an inline position without creating a note."""

    if status not in {400, 422}:
        return False
    field_pattern = r"\b(position|line_code|new_line|old_line|new_path|old_path|base_sha|head_sha|start_sha|diff|line|path)\b"
    reason_pattern = (
        r"\b(invalid|missing|not found|does not exist|can't be blank|"
        r"is required|must be a valid)\b"
    )
    return bool(re.search(rf"(?i){field_pattern}.*{reason_pattern}", body))


def api_write_url_detailed(
    url: str,
    api_token: str,
    auth_header: str,
    data: dict[str, Any],
    method: str = "POST",
) -> GitLabWriteResult:
    """Call a non-idempotent GitLab write API without retrying it."""

    headers = {
        auth_header: api_token,
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with _open_gitlab_request(request) as response:
            return GitLabWriteResult(
                "posted", _parse_response_body(_read_limited_response(response))
            )
    except urllib.error.HTTPError as exc:
        raw_body = exc.read(MAX_API_ERROR_BODY_BYTES).decode("utf-8", errors="replace")
        safe_body = truncate_plain_text(redact_sensitive(raw_body), 2_000)
        print(f"GitLab API error {exc.code} for {method} {url}: {safe_body}", file=sys.stderr)
        if _is_invalid_position_error(exc.code, raw_body):
            return GitLabWriteResult("invalid_position")
        return GitLabWriteResult("write_failed", http_status=exc.code)
    except GitLabResponseTooLarge as exc:
        print(f"GitLab API response too large for {method} {url}: {exc}", file=sys.stderr)
        return GitLabWriteResult("write_failed")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            f"GitLab API request failed for {method} {url}: {redact_sensitive(str(exc))}",
            file=sys.stderr,
        )
        return GitLabWriteResult("write_failed")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"GitLab API returned invalid JSON for {method} {url}: {exc}", file=sys.stderr)
        return GitLabWriteResult("write_failed")


def print_user_id_failure_banner(reason: str) -> None:
    """Surface a missing GitLab /user response as a posting precondition failure."""

    banner = (
        "==================================================================\n"
        "  OCR POSTING FAILED: could not resolve the current GitLab user.\n"
        f"  Reason: {reason}\n"
        "  The script cannot safely identify previous bot notes, so normal\n"
        "  review publishing is disabled before creating any GitLab notes.\n"
        "  Verify the GitLab API token has /user read access and re-run.\n"
        "=================================================================="
    )
    print(banner, file=sys.stderr)


def fetch_current_user_id(server_url: str, api_token: str, auth_header: str) -> int | None:
    """Return authenticated GitLab user id, or None if it cannot be resolved."""

    url = f"{server_url}/api/v4/user"
    result = api_request_url(url, api_token, auth_header, method="GET")

    if not isinstance(result, dict):
        print_user_id_failure_banner("GET /user returned no JSON object")
        return None

    raw_user_id = result.get("id")
    if isinstance(raw_user_id, (str, int, float)) and not isinstance(raw_user_id, bool):
        try:
            return int(raw_user_id)
        except ValueError:
            pass
    print_user_id_failure_banner("GET /user response has no valid id field")
    return None


def load_gitlab_config() -> GitLabConfig | None:
    """Load GitLab configuration and choose the correct authentication header."""

    server_url = getenv("CI_SERVER_URL", "https://gitlab.com").rstrip("/")
    project_id = getenv("CI_PROJECT_ID")
    merge_request_iid = getenv("CI_MERGE_REQUEST_IID")

    api_token = getenv("GITLAB_API_TOKEN")

    if not project_id or not merge_request_iid:
        print(
            "Not a merge request pipeline or missing GitLab CI variables.",
            file=sys.stderr,
        )
        return None

    if not api_token:
        print(
            "Missing GITLAB_API_TOKEN; a dedicated GitLab API token is required for OCR posting.",
            file=sys.stderr,
        )
        return None

    try:
        parsed_server = urllib.parse.urlsplit(server_url)
        parsed_server_port = parsed_server.port
        parsed_server_hostname = parsed_server.hostname
        parsed_server_username = parsed_server.username
        parsed_server_password = parsed_server.password
    except ValueError:
        print("CI_SERVER_URL must be an absolute HTTPS URL.", file=sys.stderr)
        return None
    if (
        parsed_server.scheme.lower() != "https"
        or not parsed_server_hostname
        or (parsed_server_port is None and parsed_server.netloc.endswith(":"))
        or parsed_server_username is not None
        or parsed_server_password is not None
        or parsed_server.query
        or parsed_server.fragment
    ):
        print("CI_SERVER_URL must be an absolute HTTPS URL.", file=sys.stderr)
        return None

    auth_header = "PRIVATE-TOKEN"
    current_user_id = fetch_current_user_id(server_url, api_token, auth_header)

    return GitLabConfig(
        server_url=server_url,
        project_id=project_id,
        merge_request_iid=merge_request_iid,
        api_token=api_token,
        auth_header=auth_header,
        current_user_id=current_user_id,
    )


def api_request(
    config: GitLabConfig,
    endpoint: str,
    data: dict[str, Any] | None = None,
    method: str = "POST",
) -> Any | None:
    """Call the GitLab MR API and return parsed JSON, `{}` for empty success, or None."""

    return api_request_url(
        url=f"{config.api_base}{endpoint}",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data=data,
        method=method,
    )


def api_get_paginated(
    config: GitLabConfig,
    endpoint: str,
    per_page: int = 100,
    max_pages: int = 10,
) -> list[Any] | None:
    """Fetch a bounded number of paginated GitLab API results."""

    items: list[Any] = []
    last_page_size = 0

    for page in range(1, max_pages + 1):
        separator = "&" if "?" in endpoint else "?"
        page_endpoint = f"{endpoint}{separator}per_page={per_page}&page={page}"
        result = api_request(config, page_endpoint, method="GET")

        if result is None:
            return None

        if not isinstance(result, list):
            print(
                f"GitLab API returned an unexpected payload for {page_endpoint}.",
                file=sys.stderr,
            )
            return None

        if not result:
            return items

        items.extend(result)
        last_page_size = len(result)

        if last_page_size < per_page:
            return items

    separator = "&" if "?" in endpoint else "?"
    sentinel_endpoint = f"{endpoint}{separator}per_page={per_page}&page={max_pages + 1}"
    sentinel = api_request(config, sentinel_endpoint, method="GET")
    if sentinel is None:
        return None
    if not isinstance(sentinel, list):
        print(
            f"GitLab API returned an unexpected payload for {sentinel_endpoint}.",
            file=sys.stderr,
        )
        return None
    if not sentinel:
        return items

    # Reached max_pages and confirmed at least one extra page. Operators need
    # to see this because un-fetched old bot notes will linger across runs.
    print(
        f"GitLab API pagination hit max_pages={max_pages} for {endpoint} "
        "with additional results; refusing to use an incomplete snapshot.",
        file=sys.stderr,
    )
    return None


@dataclass(frozen=True)
class DraftNoteCreation:
    """Validated draft note creation response."""

    response: dict[str, Any]
    note_id: int


def draft_note_id(value: Any) -> int | None:
    """Extract draft note id from a GitLab Draft Notes API object."""

    if not isinstance(value, dict):
        return None

    raw_id = value.get("id")
    if isinstance(raw_id, bool):
        return None

    if isinstance(raw_id, (str, int, float)) and not isinstance(raw_id, bool):
        try:
            return int(raw_id)
        except ValueError:
            pass
    return None


def created_draft_note(response: Any, context: str) -> DraftNoteCreation | None:
    """Validate that a create-draft API response contains a publishable id."""

    if response is None:
        return None

    note_id = draft_note_id(response)
    if note_id is None:
        print(
            f"GitLab Draft Notes API response for {context} did not contain a usable id.",
            file=sys.stderr,
        )
        return None

    return DraftNoteCreation(response=response, note_id=note_id)


def delete_plain_note(config: GitLabConfig, note_id: int) -> bool:
    """Delete a top-level merge request note by note id."""

    response = api_request(config, f"/notes/{note_id}", method="DELETE")
    return response is not None


def update_plain_note(config: GitLabConfig, note_id: int, body: str) -> GitLabWriteResult:
    """Update one known toolkit-owned summary without retrying the write."""

    return api_write_url_detailed(
        url=f"{config.api_base}/notes/{note_id}",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data={"body": build_marked_note_body(body)},
        method="PUT",
    )


def approve_merge_request(config: GitLabConfig, sha: str) -> GitLabWriteResult:
    """Approve exactly one merge-request head without retrying the write."""

    return api_write_url_detailed(
        url=f"{config.api_base}/approve",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data={"sha": sha},
    )


def unapprove_merge_request(config: GitLabConfig) -> GitLabWriteResult:
    """Remove only the authenticated user's approval without retrying."""

    return api_write_url_detailed(
        url=f"{config.api_base}/unapprove",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data={},
    )


def delete_discussion_note(config: GitLabConfig, discussion_id: str, note_id: int) -> bool:
    """Delete a note inside a merge request discussion thread."""

    response = api_request(config, f"/discussions/{discussion_id}/notes/{note_id}", method="DELETE")
    return response is not None


def delete_draft_note(config: GitLabConfig, draft_note_id_value: int) -> bool:
    """Delete a pending draft note owned by the authenticated user."""

    response = api_request(config, f"/draft_notes/{draft_note_id_value}", method="DELETE")
    return response is not None


def resolve_discussion(config: GitLabConfig, discussion_id: str) -> bool:
    """Mark a merge request discussion as resolved."""

    response = api_request(
        config,
        f"/discussions/{discussion_id}?resolved=true",
        method="PUT",
    )
    return response is not None


def post_note(config: GitLabConfig, body: str, fingerprint: str | None = None) -> Any | None:
    """Post a normal Merge Request note directly."""

    return api_request(
        config,
        "/notes",
        {"body": build_marked_note_body(body, fingerprint=fingerprint)},
    )


def post_draft_note(
    config: GitLabConfig,
    body: str,
    position: dict[str, Any] | None = None,
    fingerprint: str | None = None,
) -> Any | None:
    """Create a GitLab draft note.

    If position is provided, the draft note becomes an inline diff draft.
    If position is omitted, it becomes a regular MR draft note.
    """

    payload: dict[str, Any] = {
        "note": build_marked_note_body(
            body,
            fingerprint=fingerprint,
            max_chars=MAX_INLINE_NOTE_CHARS if position is not None else MAX_NOTE_CHARS,
            inline=position is not None,
        )
    }
    if position is not None:
        payload["position"] = position

    return api_request(config, "/draft_notes", payload)


def post_inline_note_detailed(
    config: GitLabConfig,
    path: str,
    line: int,
    body: str,
    refs: dict[str, str],
    fingerprint: str | None = None,
    old_path: str | None = None,
) -> GitLabWriteResult:
    """Post a direct inline note and distinguish invalid positions from write failures."""

    return api_write_url_detailed(
        url=f"{config.api_base}/discussions",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data={
            "body": build_marked_note_body(
                body,
                fingerprint=fingerprint,
                max_chars=MAX_INLINE_NOTE_CHARS,
                inline=True,
            ),
            "position": build_text_position(path, line, refs, old_path=old_path),
        },
    )


def post_inline_draft_note_detailed(
    config: GitLabConfig,
    path: str,
    line: int,
    body: str,
    refs: dict[str, str],
    fingerprint: str | None = None,
    old_path: str | None = None,
) -> GitLabWriteResult:
    """Create an inline draft note and distinguish invalid positions from write failures."""

    marked_body = build_marked_note_body(
        body,
        fingerprint=fingerprint,
        max_chars=MAX_INLINE_NOTE_CHARS,
        inline=True,
    )
    return api_write_url_detailed(
        url=f"{config.api_base}/draft_notes",
        api_token=config.api_token,
        auth_header=config.auth_header,
        data={
            "note": marked_body,
            "position": build_text_position(path, line, refs, old_path=old_path),
        },
    )


def publish_draft_note(config: GitLabConfig, draft_note_id_value: int) -> bool:
    """Publish one draft note created by this script run."""

    response = api_request(
        config,
        f"/draft_notes/{draft_note_id_value}/publish",
        method="PUT",
    )
    return response is not None


def publish_created_draft_notes(config: GitLabConfig, draft_note_ids: list[int]) -> bool:
    """Publish only draft notes created by this script run."""

    if post_mode() != "draft":
        return True

    for note_id in draft_note_ids:
        if not publish_draft_note(config, note_id):
            print(f"Failed to publish OCR draft note id={note_id}.", file=sys.stderr)
            return False

    return True


def post_review_note(
    config: GitLabConfig,
    body: str,
    draft_note_ids: list[int],
    fingerprint: str | None = None,
) -> Any | None:
    """Post a regular MR note using the configured posting mode."""

    if post_mode() == "draft":
        response = post_draft_note(config, body, fingerprint=fingerprint)
        created = created_draft_note(response, "MR note draft")
        if created is None:
            return None
        draft_note_ids.append(created.note_id)
        return created.response

    return post_note(config, body, fingerprint=fingerprint)


def post_review_note_bounded(
    config: GitLabConfig,
    title: str,
    body: str,
    draft_note_ids: list[int],
    fingerprint: str | None = None,
) -> Any | None:
    """Post a bounded regular MR note using the configured posting mode."""

    body_budget = note_body_budget(MAX_NOTE_CHARS, fingerprint)
    full_body = f"{title}\n\n{body}" if title else body
    if len(full_body) <= body_budget and len(full_body.encode("utf-8")) <= body_budget:
        return post_review_note(config, full_body, draft_note_ids, fingerprint=fingerprint)

    title_overhead = len(title.encode("utf-8")) + 2 if title else 0
    content_budget = max(0, body_budget - title_overhead)
    bounded_body = truncate_note_body(body, max_chars=content_budget)
    final_body = f"{title}\n\n{bounded_body}" if title else bounded_body
    if len(final_body) > body_budget or len(final_body.encode("utf-8")) > body_budget:
        final_body = truncate_note_body(final_body, max_chars=body_budget)

    return post_review_note(
        config,
        final_body,
        draft_note_ids,
        fingerprint=fingerprint,
    )


def get_diff_refs(config: GitLabConfig) -> dict[str, str] | None:
    """Fetch GitLab MR diff refs for the commit reviewed by this CI job."""

    versions = api_get_paginated(config, "/versions", max_pages=20)
    if not isinstance(versions, list) or not versions:
        print(
            "GitLab MR versions are unavailable; inline comments will fall back to notes.",
            file=sys.stderr,
        )
        return None

    candidate_head_shas: list[str] = []
    for sha in (
        getenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA").strip(),
        getenv("CI_COMMIT_SHA").strip(),
    ):
        if sha and sha not in candidate_head_shas and not re.fullmatch(r"0+", sha):
            candidate_head_shas.append(sha)
    if not candidate_head_shas:
        print(
            "CI MR source/head commit SHA is unavailable; inline comments will fall back to notes.",
            file=sys.stderr,
        )
        return None

    matching_version = None
    for candidate_sha in candidate_head_shas:
        for version in versions:
            if not isinstance(version, dict):
                continue
            if str(version.get("head_commit_sha") or "") == candidate_sha:
                matching_version = version
                break
        if matching_version is not None:
            break

    if matching_version is None:
        print(
            "GitLab MR versions do not include CI head SHA candidate(s) "
            f"{', '.join(candidate_head_shas)}; "
            "inline comments will fall back to notes.",
            file=sys.stderr,
        )
        return None

    refs = {
        "base_sha": str(matching_version.get("base_commit_sha", "")),
        "start_sha": str(matching_version.get("start_commit_sha", "")),
        "head_sha": str(matching_version.get("head_commit_sha", "")),
    }

    if not all(refs.values()):
        print(
            "GitLab MR version for CI head SHA lacks complete diff refs.",
            file=sys.stderr,
        )
        return None

    return refs


def build_text_position(
    path: str,
    line: int,
    refs: dict[str, str],
    old_path: str | None = None,
) -> dict[str, Any]:
    """Build a GitLab text diff position for an added/new line."""

    return {
        "position_type": "text",
        "new_path": path,
        "old_path": old_path or path,
        "new_line": line,
        "base_sha": refs["base_sha"],
        "start_sha": refs["start_sha"],
        "head_sha": refs["head_sha"],
    }


def post_discussion(
    config: GitLabConfig,
    path: str,
    line: int,
    body: str,
    refs: dict[str, str],
    fingerprint: str | None = None,
    old_path: str | None = None,
) -> Any | None:
    """Post an inline discussion directly on a specific new-line position."""

    return api_request(
        config,
        "/discussions",
        {
            "body": build_marked_note_body(
                body,
                fingerprint=fingerprint,
                max_chars=MAX_INLINE_NOTE_CHARS,
                inline=True,
            ),
            "position": build_text_position(path, line, refs, old_path=old_path),
        },
    )


def post_draft_discussion(
    config: GitLabConfig,
    path: str,
    line: int,
    body: str,
    refs: dict[str, str],
    fingerprint: str | None = None,
    old_path: str | None = None,
) -> Any | None:
    """Create an inline draft discussion on a specific new-line position."""

    return post_draft_note(
        config,
        body,
        position=build_text_position(path, line, refs, old_path=old_path),
        fingerprint=fingerprint,
    )


def post_review_discussion(
    config: GitLabConfig,
    path: str,
    line: int,
    body: str,
    refs: dict[str, str],
    draft_note_ids: list[int],
    fingerprint: str | None = None,
    old_path: str | None = None,
) -> GitLabWriteResult:
    """Post an inline discussion using the configured posting mode."""

    if post_mode() == "draft":
        result = post_inline_draft_note_detailed(
            config, path, line, body, refs, fingerprint=fingerprint, old_path=old_path
        )
        if not result.posted:
            return result
        created = created_draft_note(result.response, "inline discussion draft")
        if created is None:
            return GitLabWriteResult("write_failed")
        draft_note_ids.append(created.note_id)
        return GitLabWriteResult("posted", created.response)

    return post_inline_note_detailed(
        config, path, line, body, refs, fingerprint=fingerprint, old_path=old_path
    )
