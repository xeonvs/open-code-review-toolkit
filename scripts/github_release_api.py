#!/usr/bin/env python3
"""Perform bounded numeric-ID GitHub Release creation, upload, and publication."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_ORIGIN = "https://api.github.com"
UPLOAD_ORIGIN = "https://uploads.github.com"
API_VERSION = "2026-03-10"
MAX_JSON_BYTES = 1_048_576
MAX_ASSET_BYTES = 10_485_760
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_RE = re.compile(r"^v[0-9]+(?:\.[0-9]+)+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")


class GitHubReleaseError(ValueError):
    """A GitHub Release response or requested mutation is unsafe or inconsistent."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Reject redirects so authorization never crosses an endpoint boundary."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        """Return no redirected request for every redirect response."""

        return None


def _read_bounded(response: Any, max_bytes: int) -> bytes:
    """Read a response under a hard byte ceiling before parsing it."""

    payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise GitHubReleaseError("GitHub Release response exceeds its byte limit")
    return payload


def _request(
    *,
    origin: str,
    endpoint: str,
    token: str,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str = "application/vnd.github+json",
    expected: tuple[int, ...] = (200,),
    max_bytes: int = MAX_JSON_BYTES,
) -> tuple[int, Any]:
    """Call one closed GitHub endpoint without redirects and parse bounded JSON."""

    if origin not in {API_ORIGIN, UPLOAD_ORIGIN} or not endpoint.startswith("/repos/"):
        raise GitHubReleaseError("unsupported GitHub Release endpoint")
    if not token:
        raise GitHubReleaseError("GH_TOKEN is required")
    request = urllib.request.Request(
        origin + endpoint,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
            "User-Agent": "open-code-review-toolkit-release",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=60) as response:
            status = response.status
            raw = _read_bounded(response, max_bytes)
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = _read_bounded(exc, max_bytes)
    except (OSError, urllib.error.URLError) as exc:
        raise GitHubReleaseError("bounded GitHub Release request failed") from exc
    if status not in expected:
        raise GitHubReleaseError(f"unexpected GitHub Release status {status}")
    if status == 404 and not raw:
        return status, None
    try:
        return status, json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GitHubReleaseError("GitHub Release response is not valid bounded JSON") from exc


def _metadata(notes_path: Path) -> str:
    """Read exact release notes under the shared response-size ceiling."""

    if not notes_path.is_file() or notes_path.stat().st_size > MAX_JSON_BYTES:
        raise GitHubReleaseError("release notes are missing or oversized")
    return notes_path.read_text(encoding="utf-8")


def _validate_inputs(repository: str, tag: str, target: str, title: str) -> None:
    """Validate the closed release identity supplied by protected workflow data."""

    if (
        not REPOSITORY_RE.fullmatch(repository)
        or not TAG_RE.fullmatch(tag)
        or not SHA_RE.fullmatch(target)
        or title != tag
    ):
        raise GitHubReleaseError("GitHub Release identity is invalid")


def validate_release(
    payload: object,
    *,
    repository: str,
    tag: str,
    target: str,
    title: str,
    notes: str,
    require_draft: bool | None = None,
) -> dict[str, Any]:
    """Return one exact release response with a stable numeric identity."""

    _validate_inputs(repository, tag, target, title)
    if not isinstance(payload, dict):
        raise GitHubReleaseError("GitHub Release response must be an object")
    release_id = payload.get("id")
    assets = payload.get("assets")
    if (
        isinstance(release_id, bool)
        or not isinstance(release_id, int)
        or release_id <= 0
        or payload.get("tag_name") != tag
        or payload.get("target_commitish") != target
        or payload.get("name") != title
        or payload.get("body") != notes
        or not isinstance(payload.get("draft"), bool)
        or payload.get("prerelease") is not False
        or not isinstance(assets, list)
    ):
        raise GitHubReleaseError("GitHub Release metadata does not match")
    if require_draft is not None and payload["draft"] is not require_draft:
        raise GitHubReleaseError("GitHub Release draft state does not match")
    for asset in assets:
        if (
            not isinstance(asset, dict)
            or isinstance(asset.get("id"), bool)
            or not isinstance(asset.get("id"), int)
            or asset["id"] <= 0
            or not isinstance(asset.get("name"), str)
            or not ASSET_RE.fullmatch(asset["name"])
        ):
            raise GitHubReleaseError("GitHub Release asset metadata is invalid")
    names = [asset["name"] for asset in assets]
    if len(names) != len(set(names)):
        raise GitHubReleaseError("GitHub Release contains duplicate asset names")
    return payload


def _write_json(path: Path, payload: object) -> None:
    """Atomically write one owner-only canonical JSON response."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def ensure_release(
    *, repository: str, tag: str, target: str, title: str, notes: str, token: str
) -> dict[str, Any]:
    """Discover one release by tag or numeric draft listing, creating it if absent."""

    encoded_tag = urllib.parse.quote(tag, safe="")
    status, payload = _request(
        origin=API_ORIGIN,
        endpoint=f"/repos/{repository}/releases/tags/{encoded_tag}",
        token=token,
        expected=(200, 404),
    )
    if status == 200:
        return validate_release(
            payload,
            repository=repository,
            tag=tag,
            target=target,
            title=title,
            notes=notes,
        )

    releases: list[object] = []
    for page in range(1, 6):
        _status, page_payload = _request(
            origin=API_ORIGIN,
            endpoint=f"/repos/{repository}/releases?per_page=100&page={page}",
            token=token,
        )
        if not isinstance(page_payload, list) or len(page_payload) > 100:
            raise GitHubReleaseError("GitHub Release listing is malformed")
        releases.extend(page_payload)
        if len(page_payload) < 100:
            break
    else:
        _status, overflow = _request(
            origin=API_ORIGIN,
            endpoint=f"/repos/{repository}/releases?per_page=1&page=501",
            token=token,
        )
        if not isinstance(overflow, list) or overflow:
            raise GitHubReleaseError("GitHub Release listing exceeds its page bound")

    matches = [item for item in releases if isinstance(item, dict) and item.get("tag_name") == tag]
    if len(matches) > 1:
        raise GitHubReleaseError("GitHub Release tag is not unique")
    if matches:
        return validate_release(
            matches[0],
            repository=repository,
            tag=tag,
            target=target,
            title=title,
            notes=notes,
        )

    create_body = json.dumps(
        {
            "tag_name": tag,
            "target_commitish": target,
            "name": title,
            "body": notes,
            "draft": True,
            "prerelease": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    _status, created = _request(
        origin=API_ORIGIN,
        endpoint=f"/repos/{repository}/releases",
        token=token,
        method="POST",
        body=create_body,
        expected=(201,),
    )
    return validate_release(
        created,
        repository=repository,
        tag=tag,
        target=target,
        title=title,
        notes=notes,
        require_draft=True,
    )


def _read_release(
    *, repository: str, release_id: int, tag: str, target: str, title: str, notes: str, token: str
) -> dict[str, Any]:
    """Read and validate one release through its retained numeric identity."""

    _status, payload = _request(
        origin=API_ORIGIN,
        endpoint=f"/repos/{repository}/releases/{release_id}",
        token=token,
    )
    return validate_release(
        payload,
        repository=repository,
        tag=tag,
        target=target,
        title=title,
        notes=notes,
    )


def upload_asset(
    *,
    repository: str,
    release_id: int,
    tag: str,
    target: str,
    title: str,
    notes: str,
    asset: Path,
    token: str,
) -> dict[str, Any]:
    """Upload one bounded asset to an exact draft numeric release identity."""

    release = _read_release(
        repository=repository,
        release_id=release_id,
        tag=tag,
        target=target,
        title=title,
        notes=notes,
        token=token,
    )
    if release["draft"] is not True:
        raise GitHubReleaseError("cannot upload an asset to a published Release")
    name = asset.name
    metadata = asset.stat(follow_symlinks=False)
    if (
        not ASSET_RE.fullmatch(name)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > MAX_ASSET_BYTES
    ):
        raise GitHubReleaseError("GitHub Release asset is unsafe or oversized")
    if any(item["name"] == name for item in release["assets"]):
        raise GitHubReleaseError("GitHub Release asset already exists")
    body = asset.read_bytes()
    endpoint = f"/repos/{repository}/releases/{release_id}/assets?" + urllib.parse.urlencode(
        {"name": name}
    )
    _status, uploaded = _request(
        origin=UPLOAD_ORIGIN,
        endpoint=endpoint,
        token=token,
        method="POST",
        body=body,
        content_type="application/octet-stream",
        expected=(201,),
    )
    if (
        not isinstance(uploaded, dict)
        or uploaded.get("name") != name
        or uploaded.get("size") != metadata.st_size
        or isinstance(uploaded.get("id"), bool)
        or not isinstance(uploaded.get("id"), int)
        or uploaded["id"] <= 0
    ):
        raise GitHubReleaseError("uploaded GitHub Release asset metadata does not match")
    return uploaded


def publish_release(
    *,
    repository: str,
    release_id: int,
    tag: str,
    target: str,
    title: str,
    notes: str,
    expected_assets: list[str],
    token: str,
) -> dict[str, Any]:
    """Publish an exact draft after validating its complete unique asset set."""

    release = _read_release(
        repository=repository,
        release_id=release_id,
        tag=tag,
        target=target,
        title=title,
        notes=notes,
        token=token,
    )
    if sorted(expected_assets) != sorted(set(expected_assets)) or not all(
        ASSET_RE.fullmatch(name) for name in expected_assets
    ):
        raise GitHubReleaseError("expected GitHub Release asset set is invalid")
    actual_assets = sorted(item["name"] for item in release["assets"])
    if actual_assets != sorted(expected_assets):
        raise GitHubReleaseError("GitHub Release asset set does not match")
    if release["draft"] is False:
        return release
    patch = json.dumps({"draft": False}, separators=(",", ":")).encode("utf-8")
    _status, published = _request(
        origin=API_ORIGIN,
        endpoint=f"/repos/{repository}/releases/{release_id}",
        token=token,
        method="PATCH",
        body=patch,
    )
    return validate_release(
        published,
        repository=repository,
        tag=tag,
        target=target,
        title=title,
        notes=notes,
        require_draft=False,
    )


def main() -> int:
    """Dispatch one protected-workflow Release operation."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("ensure", "upload", "publish"):
        command = subparsers.add_parser(action)
        command.add_argument("--repository", required=True)
        command.add_argument("--tag", required=True)
        command.add_argument("--target", required=True)
        command.add_argument("--title", required=True)
        command.add_argument("--notes-file", type=Path, required=True)
        if action != "ensure":
            command.add_argument("--release-id", type=int, required=True)
        if action == "ensure":
            command.add_argument("--output", type=Path, required=True)
        elif action == "upload":
            command.add_argument("--asset", type=Path, required=True)
        else:
            command.add_argument("--asset-name", action="append", required=True)
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    notes = _metadata(args.notes_file)
    common = {
        "repository": args.repository,
        "tag": args.tag,
        "target": args.target,
        "title": args.title,
        "notes": notes,
        "token": token,
    }
    if args.action == "ensure":
        payload = ensure_release(**common)
        _write_json(args.output, payload)
    elif args.action == "upload":
        upload_asset(release_id=args.release_id, asset=args.asset, **common)
    else:
        payload = publish_release(
            release_id=args.release_id,
            expected_assets=args.asset_name,
            **common,
        )
        _write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
