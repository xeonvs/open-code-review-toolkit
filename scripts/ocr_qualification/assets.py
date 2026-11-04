"""Bounded release discovery and checksum-verified asset acquisition."""

from __future__ import annotations

import hashlib
import http.client
import http.server
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from . import core, settings


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject metadata redirects so the reviewed API origin cannot change."""

    def redirect_request(
        self,
        _request: urllib.request.Request,
        _file_pointer: Any,
        _code: int,
        _message: str,
        _headers: Any,
        _new_url: str,
    ) -> None:
        raise core.CompatibilityError("metadata redirects are not allowed")


METADATA_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _request_json(url: str) -> dict[str, Any] | list[Any]:
    """Read bounded GitHub release metadata with origin-scoped authentication."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        core._fail(f"metadata URL is outside the allowed GitHub API origin: {url}")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": settings.USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        # Authentication is scoped to this validated API origin. Asset downloads
        # use a separate request path and must remain public and credential-free.
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with METADATA_OPENER.open(request, timeout=settings.HTTP_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > settings.MAX_HTTP_BYTES:
                core._fail(f"metadata response exceeds {settings.MAX_HTTP_BYTES} bytes")
            payload = response.read(settings.MAX_HTTP_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise core.CompatibilityError(f"metadata request failed for {url}: {exc}") from exc
    if len(payload) > settings.MAX_HTTP_BYTES:
        core._fail(f"metadata response exceeds {settings.MAX_HTTP_BYTES} bytes")
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError(f"metadata response from {url} is not JSON") from exc
    if not isinstance(value, (dict, list)):
        core._fail(f"metadata response from {url} has unsupported shape")
    return value


def discover_unseen(
    manifest: dict[str, Any], *, through_tag: str | None = None
) -> list[dict[str, Any]]:
    """Return bounded unseen stable upstream releases above the monitoring floor."""

    floor = core._version(str(manifest["monitoring_floor"]))
    ceiling: tuple[int, int, int] | None = None
    ceiling_version: str | None = None
    if through_tag is not None:
        if settings.VERSION_RE.fullmatch(through_tag) is None:
            core._fail("qualification ceiling must be a stable semantic version tag")
        ceiling_version = through_tag.removeprefix("v")
        ceiling = core._version(ceiling_version)
        if ceiling <= floor:
            core._fail("qualification ceiling must be newer than the monitoring floor")
    known = {str(entry["version"]) for entry in manifest["releases"]}
    unseen: list[dict[str, Any]] = []
    reached_floor = False
    payload: list[Any] = []
    for page in range(1, settings.MAX_RELEASE_PAGES + 1):
        value = _request_json(
            f"{settings.UPSTREAM_API}/releases?per_page={settings.MAX_RELEASES_PER_PAGE}&page={page}"
        )
        if not isinstance(value, list) or len(value) > settings.MAX_RELEASES_PER_PAGE:
            core._fail("upstream release list has unsupported shape or size")
        payload = value
        if not payload:
            reached_floor = True
            break
        for release in payload:
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
                continue
            tag = release.get("tag_name")
            if not isinstance(tag, str) or settings.VERSION_RE.fullmatch(tag) is None:
                continue
            version = tag.removeprefix("v")
            parsed = core._version(version)
            if parsed <= floor:
                reached_floor = True
            elif version not in known and (ceiling is None or parsed <= ceiling):
                unseen.append(release)
        if reached_floor or len(payload) < settings.MAX_RELEASES_PER_PAGE:
            break
    if not reached_floor and len(payload) == settings.MAX_RELEASES_PER_PAGE:
        core._fail("monitoring floor was not reached within the bounded release pages")
    if ceiling_version is not None and not any(
        str(item.get("tag_name", "")).removeprefix("v") == ceiling_version for item in unseen
    ):
        core._fail("qualification ceiling was not found among unseen stable releases")
    return sorted(unseen, key=lambda item: core._version(str(item["tag_name"]).removeprefix("v")))


def qualification_matrix(
    manifest: dict[str, Any], releases: list[dict[str, Any]]
) -> dict[str, list[dict[str, str]]]:
    """Build ordered matrix entries with distinct tested and adjacent baselines."""

    if len(releases) > settings.MAX_QUALIFICATION_CHAIN:
        core._fail(
            f"refusing to qualify more than {settings.MAX_QUALIFICATION_CHAIN} releases per run"
        )
    tested_baseline = str(manifest["recommended_version"])
    comparison = tested_baseline
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for release in sorted(
        releases, key=lambda item: core._version(str(item.get("tag_name", "")).removeprefix("v"))
    ):
        tag = release.get("tag_name")
        if not isinstance(tag, str) or settings.VERSION_RE.fullmatch(tag) is None:
            core._fail("qualification matrix contains an invalid stable release tag")
        version = tag.removeprefix("v")
        if version in seen:
            core._fail(f"qualification matrix contains duplicate version {version}")
        seen.add(version)
        entries.append(
            {
                "comparison_version": comparison,
                "tag": f"v{version}",
                "tested_baseline_version": tested_baseline,
            }
        )
        comparison = version
    return {"include": entries}


def _asset_from_api(value: Any) -> core.Asset:
    if not isinstance(value, dict):
        core._fail("upstream asset metadata must be an object")
    name, size, digest, url = (
        value.get("name"),
        value.get("size"),
        value.get("digest"),
        value.get("browser_download_url"),
    )
    if not isinstance(name, str) or Path(name).name != name:
        core._fail(f"unsafe asset name: {name!r}")
    if not isinstance(size, int) or size <= 0 or size > settings.MAX_ASSET_BYTES:
        core._fail(f"invalid asset size for {name}")
    if not isinstance(digest, str) or (match := settings.SHA256_RE.fullmatch(digest)) is None:
        core._fail(f"missing GitHub SHA-256 digest for {name}")
    prefix = f"https://github.com/{settings.UPSTREAM_REPOSITORY}/releases/download/"
    if not isinstance(url, str) or not url.startswith(prefix):
        core._fail(f"unsafe asset URL for {name}")
    return core.Asset(name=name, size=size, sha256=match.group(1), url=url)


def release_assets(release: dict[str, Any]) -> list[core.Asset]:
    """Validate and return the complete expected upstream asset matrix."""

    values = release.get("assets")
    if not isinstance(values, list) or not values or len(values) > settings.MAX_ASSETS:
        core._fail("upstream release assets are missing or exceed the configured bound")
    assets = [_asset_from_api(value) for value in values]
    if {asset.name for asset in assets} != settings.REQUIRED_ASSETS:
        core._fail("upstream release asset set differs from the supported matrix")
    if sum(asset.size for asset in assets) > settings.MAX_TOTAL_ASSET_BYTES:
        core._fail("upstream release assets exceed the total download budget")
    return sorted(assets, key=lambda asset: asset.name)


def _download(asset: core.Asset, directory: Path) -> Path:
    """Download one verified asset with bounded retries for transient transport errors."""

    destination = directory / asset.name
    parsed = urllib.parse.urlsplit(asset.url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        core._fail(f"asset URL is outside the allowed GitHub release origin: {asset.url}")
    request = urllib.request.Request(asset.url, headers={"User-Agent": settings.USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(1, settings.DOWNLOAD_ATTEMPTS + 1):
        digest = hashlib.sha256()
        count = 0
        try:
            # The initial URL is an exact HTTPS github.com release asset; urllib follows
            # GitHub's signed, credential-free release-asset redirect.
            with urllib.request.urlopen(  # nosec B310
                request, timeout=settings.HTTP_TIMEOUT_SECONDS
            ) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != "https" or final.hostname not in {
                    "github.com",
                    "objects.githubusercontent.com",
                    "release-assets.githubusercontent.com",
                }:
                    core._fail(f"asset redirect ended at an untrusted origin: {response.geturl()}")
                with destination.open("xb") as output:
                    while chunk := response.read(64 * 1024):
                        count += len(chunk)
                        if count > asset.size or count > settings.MAX_ASSET_BYTES:
                            core._fail(f"download for {asset.name} exceeded its declared size")
                        digest.update(chunk)
                        output.write(chunk)
        except (
            TimeoutError,
            ConnectionError,
            http.client.IncompleteRead,
            urllib.error.URLError,
        ) as exc:
            retryable = not isinstance(exc, urllib.error.HTTPError) or exc.code in {
                408,
                429,
                500,
                502,
                503,
                504,
            }
            if not retryable:
                raise core.CompatibilityError(f"cannot download {asset.name}: {exc}") from exc
            last_error = exc
            try:
                destination.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                raise core.CompatibilityError(
                    f"cannot reset partial download for {asset.name}: {cleanup_exc}"
                ) from cleanup_exc
            if attempt < settings.DOWNLOAD_ATTEMPTS:
                time.sleep(attempt)
                continue
            break
        except OSError as exc:
            raise core.CompatibilityError(f"cannot download {asset.name}: {exc}") from exc
        if count != asset.size or digest.hexdigest() != asset.sha256:
            core._fail(f"downloaded bytes do not match metadata for {asset.name}")
        return destination
    assert last_error is not None
    raise core.CompatibilityError(
        f"cannot download {asset.name} after {settings.DOWNLOAD_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def parse_checksum_file(path: Path) -> dict[str, str]:
    """Parse the bounded upstream sha256sum.txt format."""

    if path.stat().st_size > 16_384:
        core._fail("upstream checksum file is too large")
    checksums: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.split(maxsplit=1)
        if len(parts) != 2 or settings.SHA256_RE.fullmatch(parts[0]) is None:
            core._fail("upstream checksum file has an invalid line")
        name = parts[1].lstrip("*")
        if Path(name).name != name or name in checksums:
            core._fail("upstream checksum file has an unsafe or duplicate name")
        checksums[name] = parts[0]
    return checksums
