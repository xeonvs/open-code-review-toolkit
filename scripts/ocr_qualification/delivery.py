"""Bounded qualification issue rendering and idempotent GitHub delivery."""

from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from . import assets, contracts, core, settings


def _issue_api_request(
    url: str, *, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any] | list[Any]:
    """Call a bounded GitHub issue endpoint with repository-scoped credentials."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        core._fail(f"issue URL is outside the allowed GitHub API origin: {url}")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        core._fail("GITHUB_TOKEN is required to update qualification issues")
    data = core.canonical_json(payload) if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": settings.USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with assets.METADATA_OPENER.open(
            request, timeout=settings.HTTP_TIMEOUT_SECONDS
        ) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > settings.MAX_ISSUE_RESPONSE_BYTES:
                core._fail("GitHub issue response exceeds the configured byte limit")
            response_data = response.read(settings.MAX_ISSUE_RESPONSE_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise core.CompatibilityError(f"GitHub issue request failed for {url}: {exc}") from exc
    if len(response_data) > settings.MAX_ISSUE_RESPONSE_BYTES:
        core._fail("GitHub issue response exceeds the configured byte limit")
    try:
        value = json.loads(response_data)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("GitHub issue response is not JSON") from exc
    if not isinstance(value, (dict, list)):
        core._fail("GitHub issue response has unsupported shape")
    return value


def release_changes_excerpt(release_notes: str) -> str:
    """Return a bounded control-free excerpt without Markdown fence delimiters."""

    lines: list[str] = []
    total = 0
    truncated = False
    for raw_line in release_notes.splitlines():
        # The release body is untrusted Markdown. Render it as escaped plain text
        # and break fence delimiters before placing it inside our own code fence.
        line = "".join(character for character in raw_line if character >= " " or character == "\t")
        line = line.replace("```", "'''").strip()
        if not line and (not lines or not lines[-1]):
            continue
        remaining = settings.MAX_RELEASE_CHANGES_CHARS - total
        if remaining <= 0 or len(lines) >= settings.MAX_RELEASE_CHANGES_LINES:
            truncated = True
            break
        if len(line) > remaining:
            line = line[:remaining].rstrip()
            truncated = True
        lines.append(line)
        total += len(line) + 1
        if truncated:
            break
    excerpt = "\n".join(lines).strip()
    if truncated:
        excerpt = f"{excerpt}\n[release notes excerpt truncated]".strip()
    return excerpt


def issue_plain_text(value: Any, field: str, max_chars: int = 500) -> str:
    """Return one bounded single-line value safe for public issue Markdown."""

    if not isinstance(value, str) or len(value) > max_chars:
        core._fail(f"field {field!r} must be a bounded string")
    cleaned = "".join(character for character in value if ord(character) >= 32).strip()
    return html.escape(cleaned, quote=False).replace("@", "@\u200b")


def render_issue(evidence: dict[str, Any]) -> str:
    """Render bounded, injection-resistant Markdown for a qualification issue."""

    version = evidence.get("version")
    if not isinstance(version, str) or settings.VERSION_RE.fullmatch(version) is None:
        core._fail("qualification evidence version is invalid")
    classification = evidence.get("classification")
    if classification not in {"automatic-safe", "human-review-required"}:
        core._fail("qualification evidence classification is invalid")
    if evidence.get("result") != "compatible":
        core._fail("qualification evidence result is not compatible")
    reasons = evidence.get("classification_reasons", [])
    if not isinstance(reasons, list) or len(reasons) > 20:
        core._fail("qualification evidence classification reasons are invalid")
    reason_lines = "\n".join(
        f"- {issue_plain_text(reason, 'classification reason')}" for reason in reasons
    )
    release_changes = evidence.get("release_changes")
    if not isinstance(release_changes, str) or not release_changes:
        release_changes = "No upstream release notes were provided."
    release_changes = html.escape(release_changes_excerpt(release_changes), quote=False)
    published_value = evidence.get("published_at")
    published_at = (
        published_value
        if isinstance(published_value, str) and settings.PUBLISHED_AT_RE.fullmatch(published_value)
        else "unknown"
    )
    comparison = evidence.get("comparison_version", evidence.get("baseline_version"))
    tested_baseline = evidence.get("tested_baseline_version", evidence.get("baseline_version"))
    compare_line = ""
    if isinstance(comparison, str) and settings.VERSION_RE.fullmatch(comparison) is not None:
        compare_line = (
            f"- compare: https://github.com/{settings.UPSTREAM_REPOSITORY}/compare/"
            f"v{comparison}...v{version}\n"
        )
    tested_line = ""
    if (
        isinstance(tested_baseline, str)
        and settings.VERSION_RE.fullmatch(tested_baseline) is not None
    ):
        tested_line = f"- current tested baseline: `v{tested_baseline}`\n"
    return (
        f"<!-- ocr-compat-candidate:v{version} -->\n"
        f"## OCR v{version} compatibility evidence\n\n"
        f"- machine result: **{evidence['result']}**\n"
        f"- classification: **{classification}**\n"
        f"- all upstream asset digests and `sha256sum.txt`: verified\n"
        f"- Linux amd64 version/help/preview/result-consumer probes: passed\n\n"
        "### Upstream release changes\n\n"
        f"- release: https://github.com/{settings.UPSTREAM_REPOSITORY}/releases/tag/v{version}\n"
        f"{compare_line}"
        f"{tested_line}"
        f"- published: `{published_at}`\n\n"
        f"```text\n{release_changes}\n```\n\n"
        f"### Classification reasons\n\n{reason_lines}\n\n"
        "### Human checklist\n\n"
        "- [ ] Review upstream release notes and relevant commits.\n"
        "- [ ] Confirm compatible or incompatible.\n"
        "- [ ] Confirm tested support and recommended-version promotion.\n"
        "- [ ] Route any compatibility change through protected PR and stable release gates.\n"
    )


def render_workflow_issue(evidence: dict[str, Any], run_url: str) -> str:
    """Add deterministic workflow provenance to a qualification issue body."""

    classification = str(evidence["classification"])
    body = render_issue(evidence)
    body += f"\n### Workflow evidence\n\n- run: {run_url}\n- classification: `{classification}`\n"
    if classification == "automatic-safe":
        body += (
            "- the aggregation job prepares one exact patch only if the complete observed chain is automatic-safe\n"
            "- opening a real PR requires the optional OCR update bot credential so protected checks run\n"
        )
    return body


def render_workflow_failure_issue(status: dict[str, Any], run_url: str) -> str:
    """Render a failed attempt from closed status values, never private detail."""

    checked = contracts.validate_qualification_status(status)
    if checked["result"] != "failed":
        core._fail("failure issue requires a failed qualification status")
    version = checked["version"]
    return (
        f"<!-- ocr-compat-candidate:v{version} -->\n"
        f"## OCR v{version} compatibility qualification failed\n\n"
        "- machine result: **failed**\n"
        f"- closed phase: `{checked['phase']}`\n"
        f"- closed reason: `{checked['reason']}`\n"
        f"- current tested baseline: `v{checked['tested_baseline_version']}`\n"
        f"- compare: https://github.com/{settings.UPSTREAM_REPOSITORY}/compare/"
        f"v{checked['comparison_version']}...v{version}\n"
        f"- release: https://github.com/{settings.UPSTREAM_REPOSITORY}/releases/tag/v{version}\n\n"
        "The candidate was not classified as compatible. Raw process diagnostics are "
        "not copied into this issue.\n\n"
        f"### Workflow evidence\n\n- run: {run_url}\n\n"
        "### Resume checklist\n\n"
        "- [ ] Inspect the bounded workflow artifact and private job log.\n"
        "- [ ] Correct or explicitly classify the failed compatibility boundary.\n"
        "- [ ] Rerun the same candidate; update this issue instead of creating a duplicate.\n"
        "- [ ] Promote only after compatible evidence and protected review.\n"
    )


def _owns_qualification_issue(author: Any, owner: str) -> bool:
    """Use GitHub-controlled identity, never body text or membership association."""

    if (
        not isinstance(author, dict)
        or not isinstance(author.get("login"), str)
        or type(author.get("id")) is not int
        or author["id"] <= 0
    ):
        return False
    return (author.get("type") == "User" and author["login"].casefold() == owner.casefold()) or (
        author.get("type") == "Bot"
        and author["login"] == settings.GITHUB_ACTIONS_LOGIN
        and author["id"] == settings.GITHUB_ACTIONS_USER_ID
    )


def find_qualification_issue(repository: str, marker: str) -> int | None:
    """Find one owner/Actions-authored header through bounded direct listing."""

    if settings.REPOSITORY_RE.fullmatch(repository) is None:
        core._fail("repository must use the owner/name form")
    matches: list[int] = []
    for page in range(1, settings.MAX_ISSUE_PAGES + 1):
        url = f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100&page={page}"
        value = _issue_api_request(url)
        if not isinstance(value, list) or len(value) > 100:
            core._fail("GitHub issue listing has unsupported shape or size")
        for issue in value:
            if not isinstance(issue, dict) or "pull_request" in issue:
                continue
            number = issue.get("number")
            body = issue.get("body")
            if (
                isinstance(number, int)
                and not isinstance(number, bool)
                and number > 0
                and isinstance(body, str)
                and body.split("\n", 1)[0].removesuffix("\r") == marker
                and _owns_qualification_issue(issue.get("user"), repository.split("/", 1)[0])
            ):
                labels = issue.get("labels")
                label_names = (
                    {
                        label.get("name")
                        for label in labels
                        if isinstance(label, dict) and isinstance(label.get("name"), str)
                    }
                    if isinstance(labels, list)
                    else set()
                )
                # Closed issues explicitly archived as duplicates retain their
                # incident evidence, but no longer compete for canonical identity.
                if issue.get("state") == "closed" and "duplicate" in label_names:
                    continue
                matches.append(number)
        if len(value) < 100:
            break
    else:
        core._fail(f"issue lookup exceeded {settings.MAX_ISSUE_PAGES} pages")
    matches = sorted(set(matches))
    if len(matches) > 1:
        core._fail(
            "multiple qualification issues contain the exact version marker: "
            + ", ".join(f"#{number}" for number in matches)
        )
    return matches[0] if matches else None


def upsert_qualification_issue(
    *,
    repository: str,
    run_url: str,
    evidence: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
) -> int:
    """Create or update the sole issue owned by one OCR version marker."""

    if (evidence is None) == (status is None):
        core._fail("issue upsert requires exactly one evidence or status input")
    record = (
        evidence if evidence is not None else contracts.validate_qualification_status(status or {})
    )
    version = record.get("version")
    if not isinstance(version, str) or settings.VERSION_RE.fullmatch(version) is None:
        core._fail("qualification evidence version is invalid")
    expected_run_prefix = f"https://github.com/{repository}/actions/runs/"
    if (
        not run_url.startswith(expected_run_prefix)
        or not run_url.removeprefix(expected_run_prefix).isdigit()
    ):
        core._fail("workflow run URL is invalid for the target repository")
    marker = f"<!-- ocr-compat-candidate:v{version} -->"
    issue_number = find_qualification_issue(repository, marker)
    payload: dict[str, Any] = {
        "title": f"[OCR compatibility] Qualify v{version}",
        "body": (
            render_workflow_issue(evidence, run_url)
            if evidence is not None
            else render_workflow_failure_issue(status or {}, run_url)
        ),
    }
    if issue_number is None:
        payload["labels"] = ["dependencies"]
        response = _issue_api_request(
            f"https://api.github.com/repos/{repository}/issues",
            method="POST",
            payload=payload,
        )
    else:
        payload["state"] = "open"
        response = _issue_api_request(
            f"https://api.github.com/repos/{repository}/issues/{issue_number}",
            method="PATCH",
            payload=payload,
        )
    returned_number = response.get("number") if isinstance(response, dict) else None
    if type(returned_number) is not int or returned_number <= 0:
        core._fail("GitHub issue write did not return a valid issue number")
    if issue_number is not None and returned_number != issue_number:
        core._fail("GitHub issue update returned a different issue number")
    return returned_number
