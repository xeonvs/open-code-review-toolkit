"""Validate OCR support metadata and qualify checksum-pinned upstream candidates."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import http.client
import http.server
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, TypeVar

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "compatibility" / "ocr-support.json"
PREFLIGHT = ROOT / "src" / "ocr_toolkit" / "preflight.py"
GITLAB_EXAMPLE = ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
UPSTREAM_REPOSITORY = "alibaba/open-code-review"
UPSTREAM_API = f"https://api.github.com/repos/{UPSTREAM_REPOSITORY}"
USER_AGENT = "open-code-review-toolkit-compatibility/1"
HTTP_TIMEOUT_SECONDS = 30
MAX_HTTP_BYTES = 2_000_000
MAX_ASSET_BYTES = 64 * 1024 * 1024
MAX_ASSETS = 16
MAX_TOTAL_ASSET_BYTES = 384 * 1024 * 1024
MAX_RELEASES_PER_PAGE = 50
MAX_RELEASE_PAGES = 4
MAX_ISSUE_PAGES = 10
MAX_ISSUE_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_RELEASE_CHANGES_CHARS = 4_000
MAX_RELEASE_CHANGES_LINES = 50
MAX_QUALIFICATION_CHAIN = 10
MAX_CLI_PROBE_BYTES = 100_000
DOWNLOAD_ATTEMPTS = 3
VERSION_RE = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PUBLISHED_AT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SAFE_NOTES_RE = re.compile(
    r"\b(fix|bug|documentation|docs|test|chore|refactor|performance)\b", re.I
)
MATERIAL_NOTES_RE = re.compile(
    r"\b(breaking|remove[ds]?|deprecat|security|vulnerab|protocol|schema|format|cli|flag|config|provider|gitlab|features?)\b"
    r"|^[ \t]*-[ \t]*feat(?:\([^\r\n)]{1,80}\))?:",
    re.I | re.M,
)
REQUIRED_REVIEW_FLAGS = {
    "--audience",
    "--background-file",
    "--format",
    "--max-tokens-budget",
    "--max-tools",
    "--from",
    "--preview",
    "--rule",
    "--to",
}
MAX_TOOLS_NORMALIZATION_RE = re.compile(
    r"\[ocr\] --max-tools ([0-9]{1,12}) is below minimum ([0-9]{1,12}), "
    r"using ([0-9]{1,12})\n?\Z"
)
MAX_TOOLS_NEGATIVE_RE = re.compile(
    r"Error: --max-tools must be a non-negative integer "
    r"\(0 means use template default\)\n?\Z"
)
MAX_TOKENS_BUDGET_NEGATIVE_RE = re.compile(
    r"Error: --max-tokens-budget must be a non-negative integer "
    r"\(0 means unlimited\)\n?\Z"
)
CURRENT_NUMERIC_CLI_CONTRACT: dict[str, object] = {
    "max_tokens_budget": {
        "cases": {
            "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
            "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
            "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
            "representative": {"effective": 30_000, "input": 30_000, "outcome": "accepted"},
            "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
        },
        "maximum": None,
        "owner": "ocr-cli",
    },
    "max_tools": {
        "cases": {
            "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
            "minimum": {"effective": 100, "input": 50, "outcome": "accepted"},
            "minimum_minus_one": {
                "effective": 100,
                "input": 49,
                "outcome": "normalized",
                "reported_normalization": 50,
            },
            "omitted": {"effective": 100, "input": None, "outcome": "accepted"},
            "representative": {"effective": 101, "input": 101, "outcome": "accepted"},
            "sentinel": {"effective": 100, "input": 0, "outcome": "accepted"},
        },
        "maximum": None,
        "owner": "ocr-template-or-higher-cli",
        "reported_minimum": 50,
    },
    "result": "passed",
}
REQUIRED_ASSETS = {
    "opencodereview-darwin-amd64",
    "opencodereview-darwin-arm64",
    "opencodereview-linux-amd64",
    "opencodereview-linux-arm64",
    "opencodereview-windows-amd64.exe",
    "opencodereview-windows-arm64.exe",
    "sha256sum.txt",
}
KNOWN_OPTIONAL_CAPABILITIES = {
    "llm_result_identity",
    "per_run_model_override",
    "per_run_provider_override",
    "review_effort",
    "semantic_grouping",
}
QUALIFICATION_STATUS_SCHEMA = "ocr-toolkit.compatibility-status/v1"
QUALIFICATION_PHASES = {"metadata", "artifact", "contracts", "evidence", "complete"}
QUALIFICATION_REASONS = {
    "metadata-invalid",
    "metadata-request-failed",
    "artifact-verification-failed",
    "contract-probe-failed",
    "evidence-write-failed",
    "issue-body-write-failed",
    "status-write-failed",
    "compatible",
}
QUALIFICATION_FAILURE_REASONS = {
    "metadata": frozenset({"metadata-invalid", "metadata-request-failed"}),
    "artifact": frozenset({"artifact-verification-failed"}),
    "contracts": frozenset({"contract-probe-failed"}),
    "evidence": frozenset(
        {"evidence-write-failed", "issue-body-write-failed", "status-write-failed"}
    ),
}
T = TypeVar("T")


class CompatibilityError(Exception):
    """OCR compatibility metadata or qualification failed closed."""


class QualificationStageError(CompatibilityError):
    """Carry one closed public qualification stage alongside private detail."""

    def __init__(self, message: str, *, phase: str, reason: str) -> None:
        super().__init__(message)
        self.phase = phase
        self.reason = reason


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
        raise CompatibilityError("metadata redirects are not allowed")


METADATA_OPENER = urllib.request.build_opener(_NoRedirectHandler)


@dataclass(frozen=True)
class Asset:
    """One bounded upstream release asset."""

    name: str
    size: int
    sha256: str
    url: str


def _fail(message: str) -> NoReturn:
    raise CompatibilityError(message)


def _version(value: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if match is None:
        _fail(f"invalid stable semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _release_transition(
    previous: tuple[int, int, int], candidate: tuple[int, int, int]
) -> str | None:
    """Classify one adjacent SemVer transition accepted for reviewed promotion."""

    if candidate[:2] == previous[:2] and candidate[2] == previous[2] + 1:
        return "patch"
    if candidate[0] == previous[0] and candidate[1] == previous[1] + 1 and candidate[2] == 0:
        return "minor"
    if candidate[0] == previous[0] + 1 and candidate[1:] == (0, 0):
        return "major"
    return None


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def write_atomic_bytes(path: Path, payload: bytes, *, label: str) -> None:
    """Commit one output through a private same-directory temporary file."""

    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as output:
            written = output.write(payload)
            if written != len(payload):
                raise OSError("short output write")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
        if os.name != "nt":
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except OSError as exc:
        raise CompatibilityError(f"cannot write {label}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"cannot load JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"{path} must contain a JSON object")
    return value


def validate_manifest(manifest: dict[str, Any], root: Path = ROOT) -> None:
    """Validate the versioned OCR support contract and evidence linkage."""

    if manifest.get("schema_version") != 1:
        _fail("manifest schema_version must be 1")
    if manifest.get("upstream_repository") != UPSTREAM_REPOSITORY:
        _fail(f"manifest upstream_repository must be {UPSTREAM_REPOSITORY}")
    recommended = manifest.get("recommended_version")
    floor = manifest.get("monitoring_floor")
    if not isinstance(recommended, str) or not isinstance(floor, str):
        _fail("recommended_version and monitoring_floor must be strings")
    _version(recommended)
    if _version(floor) > _version(recommended):
        _fail("monitoring_floor cannot be newer than recommended_version")
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        _fail("manifest releases must be a non-empty list")
    versions: set[str] = set()
    recommended_found = False
    for entry in releases:
        if not isinstance(entry, dict):
            _fail("each release entry must be an object")
        version = entry.get("version")
        status = entry.get("status")
        if not isinstance(version, str):
            _fail("release version must be a string")
        _version(version)
        if version in versions:
            _fail(f"duplicate release version: {version}")
        versions.add(version)
        if status not in {"tested", "observed-candidate"}:
            _fail(f"invalid support status for {version}: {status!r}")
        capabilities = entry.get("capabilities", [])
        if (
            not isinstance(capabilities, list)
            or len(capabilities) > len(KNOWN_OPTIONAL_CAPABILITIES)
            or any(capability not in KNOWN_OPTIONAL_CAPABILITIES for capability in capabilities)
            or capabilities != sorted(set(capabilities))
        ):
            _fail(f"invalid optional capabilities for {version}")
        if version == recommended:
            if status != "tested":
                _fail("recommended_version must have tested status")
            recommended_found = True
        assets = entry.get("assets")
        if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
            _fail(f"{version} assets must be a bounded list")
        asset_names: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict):
                _fail(f"{version} asset must be an object")
            name, size, sha256 = asset.get("name"), asset.get("size"), asset.get("sha256")
            if not isinstance(name, str) or name in asset_names or Path(name).name != name:
                _fail(f"invalid or duplicate asset name for {version}: {name!r}")
            asset_names.add(name)
            if not isinstance(size, int) or size <= 0 or size > MAX_ASSET_BYTES:
                _fail(f"invalid asset size for {version}/{name}")
            if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
                _fail(f"invalid SHA-256 for {version}/{name}")
        if asset_names != REQUIRED_ASSETS:
            _fail(f"{version} asset set does not match the supported upstream matrix")
        evidence_rel = entry.get("evidence")
        evidence_hash = entry.get("evidence_sha256")
        if not isinstance(evidence_rel, str) or not isinstance(evidence_hash, str):
            _fail(f"{version} evidence path and hash are required")
        evidence_path = (root / evidence_rel).resolve()
        compatibility_root = (root / "compatibility").resolve()
        if not evidence_path.is_relative_to(compatibility_root):
            _fail(f"{version} evidence path escapes compatibility/")
        try:
            payload = evidence_path.read_bytes()
        except OSError as exc:
            raise CompatibilityError(f"cannot read evidence for {version}: {exc}") from exc
        if hashlib.sha256(payload).hexdigest() != evidence_hash:
            _fail(f"evidence hash mismatch for {version}")
        evidence = load_json(evidence_path)
        if evidence.get("version") != version or evidence.get("result") != "compatible":
            _fail(f"evidence does not qualify {version} as compatible")
        if _version(version) >= (1, 9, 5):
            contracts = evidence.get("contracts")
            required_flags = (
                contracts.get("required_review_flags") if isinstance(contracts, dict) else None
            )
            budget_probe = (
                contracts.get("review_budget_probe") if isinstance(contracts, dict) else None
            )
            if not isinstance(required_flags, list) or "--max-tokens-budget" not in required_flags:
                _fail(f"evidence does not qualify the review budget flag for {version}")
            if budget_probe != {
                "budget": 30_000,
                "completed": 2,
                "failed_budget": 1,
                "partial_findings_preserved": True,
                "result": "passed",
                "selected": 3,
            }:
                _fail(f"evidence does not qualify partial review budget behavior for {version}")
        if _version(version) >= (1, 10, 0):
            contracts = evidence.get("contracts")
            required_flags = (
                contracts.get("required_review_flags") if isinstance(contracts, dict) else None
            )
            capabilities = (
                contracts.get("optional_capabilities") if isinstance(contracts, dict) else None
            )
            if not isinstance(required_flags, list) or "--effort" not in required_flags:
                _fail(f"evidence does not qualify the review effort flag for {version}")
            if not isinstance(capabilities, list) or not {
                "review_effort",
                "semantic_grouping",
            }.issubset(capabilities):
                _fail(f"evidence does not qualify effort and grouping for {version}")
            expected_grouping_probe = {
                "default_effort": "medium",
                "filter_requests": 1,
                "grouping_requests": 1,
                "main_requests": 3,
                "result": "passed",
                "review_rounds": 2,
            }
            if _version(version) >= (1, 10, 2):
                expected_grouping_probe["grouping_completion_cap"] = 16_384
            if contracts.get("semantic_grouping_probe") != expected_grouping_probe:
                _fail(f"evidence does not qualify semantic grouping behavior for {version}")
            if contracts.get("completion_cap_probe") != {
                "explicit": 4_096,
                "inherited": 16_384,
                "result": "passed",
                "wire_field": "max_completion_tokens",
            }:
                _fail(f"evidence does not qualify the completion cap for {version}")
            if contracts.get("numeric_cli_probe") != CURRENT_NUMERIC_CLI_CONTRACT:
                _fail(f"evidence does not qualify numeric CLI boundaries for {version}")
        evidence_assets = evidence.get("assets")
        if not isinstance(evidence_assets, list):
            _fail(f"evidence assets are missing for {version}")
        manifest_asset_tuples = sorted(
            (asset["name"], asset["size"], asset["sha256"])
            for asset in assets
            if isinstance(asset, dict)
        )
        evidence_asset_tuples = sorted(
            (asset.get("name"), asset.get("size"), asset.get("sha256"))
            for asset in evidence_assets
            if isinstance(asset, dict)
        )
        if manifest_asset_tuples != evidence_asset_tuples:
            _fail(f"manifest and evidence assets disagree for {version}")
    if not recommended_found:
        _fail("recommended_version is missing from releases")


def _request_json(url: str) -> dict[str, Any] | list[Any]:
    """Read bounded GitHub release metadata with origin-scoped authentication."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        _fail(f"metadata URL is outside the allowed GitHub API origin: {url}")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        # Authentication is scoped to this validated API origin. Asset downloads
        # use a separate request path and must remain public and credential-free.
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with METADATA_OPENER.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_HTTP_BYTES:
                _fail(f"metadata response exceeds {MAX_HTTP_BYTES} bytes")
            payload = response.read(MAX_HTTP_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise CompatibilityError(f"metadata request failed for {url}: {exc}") from exc
    if len(payload) > MAX_HTTP_BYTES:
        _fail(f"metadata response exceeds {MAX_HTTP_BYTES} bytes")
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CompatibilityError(f"metadata response from {url} is not JSON") from exc
    if not isinstance(value, (dict, list)):
        _fail(f"metadata response from {url} has unsupported shape")
    return value


def _issue_api_request(
    url: str, *, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any] | list[Any]:
    """Call a bounded GitHub issue endpoint with repository-scoped credentials."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        _fail(f"issue URL is outside the allowed GitHub API origin: {url}")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        _fail("GITHUB_TOKEN is required to update qualification issues")
    data = canonical_json(payload) if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with METADATA_OPENER.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_ISSUE_RESPONSE_BYTES:
                _fail("GitHub issue response exceeds the configured byte limit")
            response_data = response.read(MAX_ISSUE_RESPONSE_BYTES + 1)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise CompatibilityError(f"GitHub issue request failed for {url}: {exc}") from exc
    if len(response_data) > MAX_ISSUE_RESPONSE_BYTES:
        _fail("GitHub issue response exceeds the configured byte limit")
    try:
        value = json.loads(response_data)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("GitHub issue response is not JSON") from exc
    if not isinstance(value, (dict, list)):
        _fail("GitHub issue response has unsupported shape")
    return value


def discover_unseen(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return bounded unseen stable upstream releases above the monitoring floor."""

    floor = _version(str(manifest["monitoring_floor"]))
    known = {str(entry["version"]) for entry in manifest["releases"]}
    unseen: list[dict[str, Any]] = []
    reached_floor = False
    payload: list[Any] = []
    for page in range(1, MAX_RELEASE_PAGES + 1):
        value = _request_json(
            f"{UPSTREAM_API}/releases?per_page={MAX_RELEASES_PER_PAGE}&page={page}"
        )
        if not isinstance(value, list) or len(value) > MAX_RELEASES_PER_PAGE:
            _fail("upstream release list has unsupported shape or size")
        payload = value
        if not payload:
            reached_floor = True
            break
        for release in payload:
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
                continue
            tag = release.get("tag_name")
            if not isinstance(tag, str) or VERSION_RE.fullmatch(tag) is None:
                continue
            version = tag.removeprefix("v")
            parsed = _version(version)
            if parsed <= floor:
                reached_floor = True
            elif version not in known:
                unseen.append(release)
        if reached_floor or len(payload) < MAX_RELEASES_PER_PAGE:
            break
    if not reached_floor and len(payload) == MAX_RELEASES_PER_PAGE:
        _fail("monitoring floor was not reached within the bounded release pages")
    return sorted(unseen, key=lambda item: _version(str(item["tag_name"]).removeprefix("v")))


def qualification_matrix(
    manifest: dict[str, Any], releases: list[dict[str, Any]]
) -> dict[str, list[dict[str, str]]]:
    """Build ordered matrix entries with distinct tested and adjacent baselines."""

    if len(releases) > MAX_QUALIFICATION_CHAIN:
        _fail(f"refusing to qualify more than {MAX_QUALIFICATION_CHAIN} releases per run")
    tested_baseline = str(manifest["recommended_version"])
    comparison = tested_baseline
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for release in sorted(
        releases, key=lambda item: _version(str(item.get("tag_name", "")).removeprefix("v"))
    ):
        tag = release.get("tag_name")
        if not isinstance(tag, str) or VERSION_RE.fullmatch(tag) is None:
            _fail("qualification matrix contains an invalid stable release tag")
        version = tag.removeprefix("v")
        if version in seen:
            _fail(f"qualification matrix contains duplicate version {version}")
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


def _asset_from_api(value: Any) -> Asset:
    if not isinstance(value, dict):
        _fail("upstream asset metadata must be an object")
    name, size, digest, url = (
        value.get("name"),
        value.get("size"),
        value.get("digest"),
        value.get("browser_download_url"),
    )
    if not isinstance(name, str) or Path(name).name != name:
        _fail(f"unsafe asset name: {name!r}")
    if not isinstance(size, int) or size <= 0 or size > MAX_ASSET_BYTES:
        _fail(f"invalid asset size for {name}")
    if not isinstance(digest, str) or (match := SHA256_RE.fullmatch(digest)) is None:
        _fail(f"missing GitHub SHA-256 digest for {name}")
    prefix = f"https://github.com/{UPSTREAM_REPOSITORY}/releases/download/"
    if not isinstance(url, str) or not url.startswith(prefix):
        _fail(f"unsafe asset URL for {name}")
    return Asset(name=name, size=size, sha256=match.group(1), url=url)


def release_assets(release: dict[str, Any]) -> list[Asset]:
    """Validate and return the complete expected upstream asset matrix."""

    values = release.get("assets")
    if not isinstance(values, list) or not values or len(values) > MAX_ASSETS:
        _fail("upstream release assets are missing or exceed the configured bound")
    assets = [_asset_from_api(value) for value in values]
    if {asset.name for asset in assets} != REQUIRED_ASSETS:
        _fail("upstream release asset set differs from the supported matrix")
    if sum(asset.size for asset in assets) > MAX_TOTAL_ASSET_BYTES:
        _fail("upstream release assets exceed the total download budget")
    return sorted(assets, key=lambda asset: asset.name)


def _download(asset: Asset, directory: Path) -> Path:
    """Download one verified asset with bounded retries for transient transport errors."""

    destination = directory / asset.name
    parsed = urllib.parse.urlsplit(asset.url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        _fail(f"asset URL is outside the allowed GitHub release origin: {asset.url}")
    request = urllib.request.Request(asset.url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        digest = hashlib.sha256()
        count = 0
        try:
            # The initial URL is an exact HTTPS github.com release asset; urllib follows
            # GitHub's signed, credential-free release-asset redirect.
            with urllib.request.urlopen(  # nosec B310
                request, timeout=HTTP_TIMEOUT_SECONDS
            ) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != "https" or final.hostname not in {
                    "github.com",
                    "objects.githubusercontent.com",
                    "release-assets.githubusercontent.com",
                }:
                    _fail(f"asset redirect ended at an untrusted origin: {response.geturl()}")
                with destination.open("xb") as output:
                    while chunk := response.read(64 * 1024):
                        count += len(chunk)
                        if count > asset.size or count > MAX_ASSET_BYTES:
                            _fail(f"download for {asset.name} exceeded its declared size")
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
                raise CompatibilityError(f"cannot download {asset.name}: {exc}") from exc
            last_error = exc
            try:
                destination.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                raise CompatibilityError(
                    f"cannot reset partial download for {asset.name}: {cleanup_exc}"
                ) from cleanup_exc
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(attempt)
                continue
            break
        except OSError as exc:
            raise CompatibilityError(f"cannot download {asset.name}: {exc}") from exc
        if count != asset.size or digest.hexdigest() != asset.sha256:
            _fail(f"downloaded bytes do not match metadata for {asset.name}")
        return destination
    assert last_error is not None
    raise CompatibilityError(
        f"cannot download {asset.name} after {DOWNLOAD_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def parse_checksum_file(path: Path) -> dict[str, str]:
    """Parse the bounded upstream sha256sum.txt format."""

    if path.stat().st_size > 16_384:
        _fail("upstream checksum file is too large")
    checksums: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.split(maxsplit=1)
        if len(parts) != 2 or SHA256_RE.fullmatch(parts[0]) is None:
            _fail("upstream checksum file has an invalid line")
        name = parts[1].lstrip("*")
        if Path(name).name != name or name in checksums:
            _fail("upstream checksum file has an unsafe or duplicate name")
        checksums[name] = parts[0]
    return checksums


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()[-2000:]
        raise CompatibilityError(
            f"contract command failed: {' '.join(command)}: exit {exc.returncode}: {stderr}"
        ) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CompatibilityError(f"contract command failed: {' '.join(command)}: {exc}") from exc
    return completed.stdout


def _isolated_probe_environment(home: Path) -> dict[str, str]:
    """Return a private OCR/Git environment independent of operator configuration."""

    home.mkdir(mode=0o700)
    temp = home / "tmp"
    temp.mkdir(mode=0o700)
    git = shutil.which("git")
    if git is None or not Path(git).is_absolute():
        _fail("qualification requires an absolute Git executable")
    return {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "NO_PROXY": "127.0.0.1,localhost",
        "PATH": os.pathsep.join((str(Path(git).parent), os.defpath)),
        "TMPDIR": str(temp),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
    }


def _synthetic_repo(directory: Path, env: dict[str, str]) -> tuple[Path, str, str]:
    """Create an immutable two-commit fixture under isolated Git configuration."""

    repo = directory / "synthetic-review"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo, env=env)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=env)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=env)
    target = repo / "example.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo, env=env)
    _run(["git", "commit", "-m", "baseline"], cwd=repo, env=env)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    target.write_text("def value():\n    return 2\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo, env=env)
    _run(["git", "commit", "-m", "change value"], cwd=repo, env=env)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    return repo, base, head


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """Deterministic OpenAI-compatible response sequence for OCR probes."""

    request_count = 0
    tokens_per_request = 2
    grouping_tokens_per_request = 2
    grouping_mode = "singletons"
    main_mode = "findings"
    completion_caps: list[object] = []
    request_stages: list[str] = []

    @staticmethod
    def _message_contents(messages: list[Any]) -> list[str]:
        """Return only text message content from one bounded probe request."""

        return [
            content
            for message in messages
            if isinstance(message, dict) and isinstance((content := message.get("content")), str)
        ]

    @classmethod
    def _grouping_files(cls, messages: list[Any]) -> list[str]:
        """Extract the public grouping prompt's changed-file inventory."""

        paths: list[str] = []
        for content in cls._message_contents(messages):
            for match in re.finditer(
                r"(?m)^([^\r\n]+) \((?:ADDED|MODIFIED|DELETED|RENAMED), \+[0-9]+/-[0-9]+\)$",
                content,
            ):
                candidate = match.group(1)
                if candidate not in paths:
                    paths.append(candidate)
        return paths

    @classmethod
    def _review_path(cls, messages: list[Any]) -> str | None:
        """Extract the first path from OCR's public review-files XML block."""

        for content in cls._message_contents(messages):
            if match := re.search(r'<file path="([^"\r\n]+)">', content):
                return match.group(1)
        return None

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_HTTP_BYTES:
            self.send_error(400)
            return
        try:
            request = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400)
            return
        if not isinstance(request, dict):
            self.send_error(400)
            return
        type(self).completion_caps.append(request.get("max_completion_tokens"))
        messages = request.get("messages")
        if not isinstance(messages, list):
            self.send_error(400)
            return
        type(self).request_count += 1
        tools = request.get("tools")
        tool_names: set[str] = set()
        if isinstance(tools, list):
            for tool in tools:
                function = tool.get("function") if isinstance(tool, dict) else None
                if isinstance(function, dict) and isinstance(function.get("name"), str):
                    tool_names.add(function["name"])
        message: dict[str, Any]
        if not tool_names:
            paths = type(self)._grouping_files(messages)
            if not paths:
                self.send_error(400)
                return
            groups = (
                [{"label": "compatibility-group", "files": paths}]
                if type(self).grouping_mode == "combined"
                else [{"label": path, "files": [path]} for path in paths]
            )
            message = {"role": "assistant", "content": json.dumps(groups)}
            finish_reason = "stop"
            stage = "grouping"
        elif "approve_all_comments" in tool_names:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-filter",
                        "type": "function",
                        "function": {"name": "approve_all_comments", "arguments": "{}"},
                    }
                ],
            }
            finish_reason = "tool_calls"
            stage = "filter"
        else:
            contents = type(self)._message_contents(messages)
            if type(self).main_mode == "exhaust-tools":
                if "file_read" in tool_names:
                    function = {
                        "name": "file_read",
                        "arguments": json.dumps(
                            {"file_path": "example.py", "start_line": 1, "end_line": 1}
                        ),
                    }
                    call_id = f"call-read-{type(self).request_count}"
                    stage = "main"
                else:
                    function = {"name": "task_done", "arguments": "{}"}
                    call_id = "call-grace-done"
                    stage = "grace"
            else:
                prior_comment = any(
                    isinstance(message, dict)
                    and any(
                        isinstance(call, dict)
                        and isinstance(call.get("function"), dict)
                        and call["function"].get("name") == "code_comment"
                        for call in message.get("tool_calls", [])
                    )
                    for message in messages
                )
                later_round = any("### Previously Confirmed Findings" in item for item in contents)
                if not prior_comment and not later_round:
                    path = type(self)._review_path(messages)
                    if path is None:
                        self.send_error(400)
                        return
                    arguments = json.dumps(
                        {
                            "comments": [
                                {
                                    "content": "Synthetic compatibility finding.",
                                    "existing_code": "    return 2",
                                    "path": path,
                                    "thinking": "Synthetic private compatibility reasoning.",
                                    "category": "maintainability",
                                    "severity": "low",
                                }
                            ]
                        }
                    )
                    function = {"name": "code_comment", "arguments": arguments}
                    call_id = "call-comment"
                else:
                    function = {"name": "task_done", "arguments": "{}"}
                    call_id = "call-done"
                stage = "main"
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": function,
                    }
                ],
            }
            finish_reason = "tool_calls"
        type(self).request_stages.append(stage)
        usage_tokens = (
            type(self).grouping_tokens_per_request
            if stage == "grouping"
            else type(self).tokens_per_request
        )
        payload = json.dumps(
            {
                "id": f"compat-{type(self).request_count}",
                "object": "chat.completion",
                "model": "synthetic-model",
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                "usage": {
                    "prompt_tokens": usage_tokens - 1,
                    "completion_tokens": 1,
                    "total_tokens": usage_tokens,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, _format: str, *_args: Any) -> None:
        return


@contextlib.contextmanager
def _stub_gateway(
    *,
    tokens_per_request: int = 2,
    grouping_tokens_per_request: int = 2,
    grouping_mode: str = "singletons",
    main_mode: str = "findings",
) -> Iterator[str]:
    """Serve deterministic responses with configurable real usage accounting."""

    if tokens_per_request < 2 or grouping_tokens_per_request < 2:
        _fail("stub gateway token usage must be at least two")
    if grouping_mode not in {"singletons", "combined"}:
        _fail("stub gateway grouping mode is invalid")
    if main_mode not in {"findings", "exhaust-tools"}:
        _fail("stub gateway main mode is invalid")
    _StubHandler.request_count = 0
    _StubHandler.tokens_per_request = tokens_per_request
    _StubHandler.grouping_tokens_per_request = grouping_tokens_per_request
    _StubHandler.grouping_mode = grouping_mode
    _StubHandler.main_mode = main_mode
    _StubHandler.completion_caps = []
    _StubHandler.request_stages = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def detect_optional_capabilities(help_output: str, sample: dict[str, Any]) -> list[str]:
    """Validate additive OCR identity fields and return observed optional capabilities."""

    optional_capabilities: set[str] = set()
    if "--effort" in help_output:
        optional_capabilities.add("review_effort")
    if "--model" in help_output:
        optional_capabilities.add("per_run_model_override")
    if "--provider" in help_output:
        optional_capabilities.add("per_run_provider_override")
    llm_identity = sample.get("llm")
    if llm_identity is not None:
        if not isinstance(llm_identity, dict):
            _fail("candidate full review emitted an invalid additive LLM identity")
        model = llm_identity.get("model")
        provider = llm_identity.get("provider")
        if not isinstance(model, str) or not model or len(model) > 500:
            _fail("candidate full review emitted an invalid additive LLM model identity")
        if provider is not None and (
            not isinstance(provider, str) or not provider or len(provider) > 200
        ):
            _fail("candidate full review emitted an invalid additive LLM provider identity")
        optional_capabilities.add("llm_result_identity")
    groups = sample.get("groups")
    if groups is not None:
        _validate_file_groups(groups)
        optional_capabilities.add("semantic_grouping")
    return sorted(optional_capabilities)


def _validate_file_groups(value: Any, expected_paths: set[str] | None = None) -> None:
    """Validate bounded additive group metadata without retaining its labels."""

    if not isinstance(value, list) or not value or len(value) > 100:
        _fail("candidate full review emitted invalid additive file groups")
    observed: list[str] = []
    for group in value:
        if not isinstance(group, dict):
            _fail("candidate full review emitted an invalid file group")
        label = group.get("label")
        files = group.get("files")
        if (
            not isinstance(label, str)
            or not label
            or len(label) > 500
            or any(ord(character) < 32 for character in label)
            or not isinstance(files, list)
            or not files
            or len(files) > 10
        ):
            _fail("candidate full review emitted an invalid file group")
        for path in files:
            if (
                not isinstance(path, str)
                or not path
                or len(path) > 1_000
                or any(ord(character) < 32 for character in path)
                or path in observed
            ):
                _fail("candidate full review emitted an invalid grouped path")
            observed.append(path)
    if expected_paths is not None and set(observed) != expected_paths:
        _fail("candidate semantic grouping did not cover the expected paths")


def _budget_result_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Drive the real OCR review budget gate and validate its partial manifest."""

    git_env = _isolated_probe_environment(directory / "budget-git-home")
    repo = directory / "budget-review"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    for name in ("first.py", "second.py", "third.py"):
        (repo / name).write_text("def value():\n    return 1\n", encoding="utf-8")
    _run(["git", "add", "first.py", "second.py", "third.py"], cwd=repo, env=git_env)
    _run(["git", "commit", "-m", "budget baseline"], cwd=repo, env=git_env)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for name in ("first.py", "second.py", "third.py"):
        (repo / name).write_text("def value():\n    return 2\n", encoding="utf-8")
    _run(["git", "commit", "-am", "budget changes"], cwd=repo, env=git_env)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()

    home = directory / "budget-review-home"
    env = _isolated_probe_environment(home)
    with _stub_gateway(tokens_per_request=20_000) as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        output = _run(
            [
                str(binary),
                "review",
                "--from",
                base,
                "--to",
                head,
                "--format",
                "json",
                "--audience",
                "agent",
                "--concurrency",
                "1",
                "--max-tokens-budget",
                "30000",
            ],
            cwd=repo,
            env=env,
        )
    try:
        sample = json.loads(output)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("budget-limited review did not emit JSON") from exc
    if not isinstance(sample, dict):
        _fail("budget-limited review emitted an unsupported result object")
    summary = sample.get("summary")
    if not isinstance(summary, dict) or summary.get("budget_exceeded") is not True:
        _fail("budget-limited review omitted summary.budget_exceeded")

    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(sample)
    except OcrResultContractError as exc:
        raise CompatibilityError(
            f"budget-limited review emitted an unsupported result object: {exc}"
        ) from exc
    if (
        outcome.kind != "partial"
        or not outcome.budget_exceeded
        or outcome.selected_count != 3
        or outcome.completed_count != 2
        or outcome.failed_count != 1
        or len(outcome.failed_items) != 1
        or outcome.failed_items[0].classification != "budget"
    ):
        _fail("real OCR budget gate did not produce the expected partial coverage contract")
    warnings = sample.get("warnings")
    if not isinstance(warnings, list) or not any(
        isinstance(warning, dict) and warning.get("type") == "token_budget_reached"
        for warning in warnings
    ):
        _fail("budget-limited review omitted the token_budget_reached warning")
    comments = sample.get("comments")
    if not isinstance(comments, list) or len(comments) != 2:
        _fail("budget-limited review did not preserve its completed finding")
    return {
        "budget": 30_000,
        "completed": 2,
        "failed_budget": 1,
        "partial_findings_preserved": True,
        "result": "passed",
        "selected": 3,
    }


def _run_numeric_preview_case(
    binary: Path,
    repo: Path,
    base: str,
    head: str,
    directory: Path,
    *,
    flag: str,
    value: int | None,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded no-model numeric CLI preview and retain diagnostics privately."""

    case_name = "omitted" if value is None else str(value).replace("-", "negative-")
    env = _isolated_probe_environment(directory / f"numeric-{flag.removeprefix('--')}-{case_name}")
    command = [
        str(binary),
        "review",
        "--from",
        base,
        "--to",
        head,
        "--preview",
        "--format",
        "json",
    ]
    if value is not None:
        command.extend([flag, str(value)])
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CompatibilityError(f"numeric CLI preview failed for {flag}") from exc
    if (
        len(completed.stdout.encode()) > MAX_CLI_PROBE_BYTES
        or len(completed.stderr.encode()) > MAX_CLI_PROBE_BYTES
    ):
        _fail(f"numeric CLI preview exceeded its output bound for {flag}")
    return completed


def _accepted_numeric_preview(completed: subprocess.CompletedProcess[str], *, flag: str) -> None:
    """Require one clean accepted numeric preview without trusting help text."""

    if completed.returncode != 0 or completed.stderr:
        _fail(f"candidate {flag} preview did not pass without diagnostics")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CompatibilityError(f"candidate {flag} preview did not emit JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        _fail(f"candidate {flag} preview emitted an invalid file manifest")


def _effective_max_tools_probe(
    binary: Path,
    repo: Path,
    base: str,
    head: str,
    directory: Path,
    *,
    value: int,
    expected_diagnostic: re.Pattern[str] | None,
) -> int:
    """Count real OCR main-loop rounds through a deterministic local protocol peer."""

    env = _isolated_probe_environment(directory / f"effective-max-tools-{value}")
    with _stub_gateway(main_mode="exhaust-tools") as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        try:
            completed = subprocess.run(  # nosec B603
                [
                    str(binary),
                    "review",
                    "--from",
                    base,
                    "--to",
                    head,
                    "--format",
                    "json",
                    "--audience",
                    "agent",
                    "--concurrency",
                    "1",
                    "--effort",
                    "low",
                    "--no-filter",
                    "--max-tools",
                    str(value),
                ],
                cwd=repo,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CompatibilityError("effective max-tools probe failed") from exc
        stages = tuple(_StubHandler.request_stages)
    if (
        len(completed.stdout.encode()) > MAX_CLI_PROBE_BYTES
        or len(completed.stderr.encode()) > MAX_CLI_PROBE_BYTES
    ):
        _fail("effective max-tools probe exceeded its output bound")
    first_diagnostic = completed.stderr.partition("\n")[0]
    if expected_diagnostic is None:
        if first_diagnostic.startswith("[ocr] --max-tools"):
            _fail("effective max-tools probe returned an unexpected normalization")
    elif expected_diagnostic.fullmatch(f"{first_diagnostic}\n") is None:
        _fail("effective max-tools probe did not retain the qualified normalization")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("effective max-tools probe did not emit JSON") from exc
    tool_calls = payload.get("tool_calls") if isinstance(payload, dict) else None
    by_tool = tool_calls.get("by_tool") if isinstance(tool_calls, dict) else None
    observed = stages.count("main")
    if (
        completed.returncode not in {0, 1}
        or observed <= 0
        or stages.count("grace") != 1
        or len(stages) != observed + 1
        or not isinstance(by_tool, dict)
        or by_tool.get("file_read") != observed
        or tool_calls.get("total") != observed
    ):
        _fail("effective max-tools probe returned an inconsistent tool-loop result")
    return observed


def _numeric_cli_probe(
    binary: Path, repo: Path, base: str, head: str, directory: Path
) -> dict[str, object]:
    """Qualify closed numeric CLI boundaries and the resulting effective semantics."""

    max_tools_omitted = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=None
    )
    max_tools_sentinel = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=0
    )
    max_tools_invalid = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=-1
    )
    discovery = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=1
    )
    for completed in (max_tools_omitted, max_tools_sentinel):
        _accepted_numeric_preview(completed, flag="--max-tools")
    if (
        max_tools_invalid.returncode == 0
        or MAX_TOOLS_NEGATIVE_RE.fullmatch(max_tools_invalid.stderr) is None
    ):
        _fail("candidate max-tools negative boundary did not fail closed")
    normalization = MAX_TOOLS_NORMALIZATION_RE.fullmatch(discovery.stderr)
    if discovery.returncode != 0 or normalization is None:
        _fail("candidate max-tools minimum could not be qualified behaviorally")
    requested, minimum, normalized = (int(value) for value in normalization.groups())
    if requested != 1 or minimum <= 1 or normalized != minimum:
        _fail("candidate max-tools minimum diagnostic is inconsistent")
    below = minimum - 1
    below_preview = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=below
    )
    below_match = MAX_TOOLS_NORMALIZATION_RE.fullmatch(below_preview.stderr)
    if (
        below_preview.returncode != 0
        or below_match is None
        or tuple(int(value) for value in below_match.groups()) != (below, minimum, minimum)
    ):
        _fail("candidate max-tools minimum-minus-one boundary is inconsistent")
    minimum_preview = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=minimum
    )
    _accepted_numeric_preview(minimum_preview, flag="--max-tools")
    template_default = _effective_max_tools_probe(
        binary,
        repo,
        base,
        head,
        directory,
        value=below,
        expected_diagnostic=MAX_TOOLS_NORMALIZATION_RE,
    )
    if template_default < minimum:
        _fail("candidate max-tools template default is below the reported minimum")
    representative = template_default + 1
    representative_preview = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=representative
    )
    _accepted_numeric_preview(representative_preview, flag="--max-tools")
    effective_representative = _effective_max_tools_probe(
        binary,
        repo,
        base,
        head,
        directory,
        value=representative,
        expected_diagnostic=None,
    )
    if effective_representative != representative:
        _fail("candidate max-tools representative value was not applied exactly")

    budget_cases: dict[str, subprocess.CompletedProcess[str]] = {
        "omitted": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=None
        ),
        "sentinel": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=0
        ),
        "invalid_below": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=-1
        ),
        "minimum": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=1
        ),
        "representative": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=30_000
        ),
    }
    for name in ("omitted", "sentinel", "minimum", "representative"):
        _accepted_numeric_preview(budget_cases[name], flag="--max-tokens-budget")
    if (
        budget_cases["invalid_below"].returncode == 0
        or MAX_TOKENS_BUDGET_NEGATIVE_RE.fullmatch(budget_cases["invalid_below"].stderr) is None
    ):
        _fail("candidate max-tokens-budget negative boundary did not fail closed")
    return {
        "max_tokens_budget": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
                "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
                "representative": {
                    "effective": 30_000,
                    "input": 30_000,
                    "outcome": "accepted",
                },
                "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
            },
            "maximum": None,
            "owner": "ocr-cli",
        },
        "max_tools": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {
                    "effective": template_default,
                    "input": minimum,
                    "outcome": "accepted",
                },
                "minimum_minus_one": {
                    "effective": template_default,
                    "input": below,
                    "outcome": "normalized",
                    "reported_normalization": minimum,
                },
                "omitted": {
                    "effective": template_default,
                    "input": None,
                    "outcome": "accepted",
                },
                "representative": {
                    "effective": representative,
                    "input": representative,
                    "outcome": "accepted",
                },
                "sentinel": {
                    "effective": template_default,
                    "input": 0,
                    "outcome": "accepted",
                },
            },
            "maximum": None,
            "owner": "ocr-template-or-higher-cli",
            "reported_minimum": minimum,
        },
        "result": "passed",
    }


def _semantic_grouping_probe(binary: Path, version: str, directory: Path) -> dict[str, object]:
    """Drive one real two-file group through grouping and medium review rounds."""

    root = directory / "semantic-grouping-probe"
    root.mkdir()
    git_env = _isolated_probe_environment(root / "git-home")
    repo = root / "review"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    paths = ("first.py", "second.py")
    for path in paths:
        (repo / path).write_text("def value():\n    return 1\n", encoding="utf-8")
    _run(["git", "add", *paths], cwd=repo, env=git_env)
    _run(["git", "commit", "-m", "grouping baseline"], cwd=repo, env=git_env)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for path in paths:
        (repo / path).write_text("def value():\n    return 2\n", encoding="utf-8")
    _run(["git", "commit", "-am", "group related changes"], cwd=repo, env=git_env)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()

    env = _isolated_probe_environment(root / "review-home")
    with _stub_gateway(grouping_mode="combined") as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        output = _run(
            [
                str(binary),
                "review",
                "--from",
                base,
                "--to",
                head,
                "--format",
                "json",
                "--audience",
                "agent",
                "--concurrency",
                "1",
            ],
            cwd=repo,
            env=env,
        )
        stages = list(_StubHandler.request_stages)
        completion_caps = list(_StubHandler.completion_caps)
    try:
        sample = json.loads(output)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("semantic grouping review did not emit JSON") from exc
    if not isinstance(sample, dict):
        _fail("semantic grouping review emitted an unsupported result object")
    _validate_file_groups(sample.get("groups"), set(paths))
    groups = sample["groups"]
    if (
        len(groups) != 1
        or groups[0].get("label") != "compatibility-group"
        or groups[0].get("files") != list(paths)
    ):
        _fail("semantic grouping review did not preserve the accepted group")
    if stages != ["grouping", "main", "main", "filter", "main"]:
        _fail(f"default medium review emitted an unexpected stage sequence: {stages!r}")
    expected_grouping_cap = 16_384 if _version(version) >= (1, 10, 2) else 4_096
    if len(completion_caps) != len(stages) or completion_caps[0] != expected_grouping_cap:
        _fail(
            "semantic grouping review emitted an unexpected grouping completion cap: "
            f"{completion_caps!r}"
        )
    result: dict[str, object] = {
        "default_effort": "medium",
        "filter_requests": 1,
        "grouping_requests": 1,
        "main_requests": 3,
        "result": "passed",
        "review_rounds": 2,
    }
    if _version(version) >= (1, 10, 2):
        result["grouping_completion_cap"] = expected_grouping_cap
    return result


def _completion_cap_probe(binary: Path, version: str, directory: Path) -> dict[str, object]:
    """Observe the real OCR chat-completions output cap with and without an override."""

    probe_root = directory / "completion-cap-probe"
    probe_root.mkdir()
    git_env = _isolated_probe_environment(probe_root / "git-home")
    repo, base, head = _synthetic_repo(probe_root, git_env)
    observed: dict[str, int] = {}
    inherited = 16_384 if _version(version) >= (1, 10, 0) else 58_888
    for label, expected in (("inherited", inherited), ("explicit", 4_096)):
        env = _isolated_probe_environment(probe_root / f"{label}-home")
        with _stub_gateway() as gateway_url:
            env.update(
                {
                    "OCR_LLM_URL": gateway_url,
                    "OCR_LLM_TOKEN": "synthetic-token",
                    "OCR_LLM_MODEL": "synthetic-model",
                    "OCR_LLM_PROTOCOL": "openai",
                    "OCR_TELEMETRY_ENABLED": "false",
                }
            )
            from ocr_toolkit.config_writer import write_ocr_config

            llm_config: dict[str, object] = {
                "auth_token": "synthetic-token",
                "model": "synthetic-model",
                "protocol": "openai",
                "url": gateway_url,
                "use_anthropic": False,
            }
            if label == "explicit":
                llm_config["extra_body"] = {"max_completion_tokens": expected}
            write_ocr_config(
                {"llm": llm_config, "telemetry": {"enabled": False}},
                Path(env["HOME"]) / ".opencodereview" / "config.json",
            )
            _run(
                [
                    str(binary),
                    "review",
                    "--from",
                    base,
                    "--to",
                    head,
                    "--format",
                    "json",
                    "--audience",
                    "agent",
                    "--concurrency",
                    "1",
                ],
                cwd=repo,
                env=env,
            )
        caps = _StubHandler.completion_caps
        if not caps or any(value != expected for value in caps):
            _fail(f"OCR completion-cap {label} probe expected {expected}, observed {caps!r}")
        observed[label] = expected
    return {
        "explicit": observed["explicit"],
        "inherited": observed["inherited"],
        "result": "passed",
        "wire_field": "max_completion_tokens",
    }


def _preview_file_selection(payload: dict[str, Any] | str, path: str) -> tuple[bool, object]:
    """Return one preview file's selected state and closed exclusion reason."""

    if isinstance(payload, str):
        section: str | None = None
        for raw_line in payload.splitlines():
            line = re.sub(r"\x1b\[[0-9;]*m", "", raw_line).strip()
            if line.startswith("Will review ("):
                section = "selected"
                continue
            if line.startswith("Excluded from review ("):
                section = "excluded"
                continue
            if path not in line:
                continue
            exclusion = "unsupported_ext" if "(unsupported_ext)" in line else None
            return section == "selected", exclusion
        return False, None
    files = payload.get("files")
    if not isinstance(files, list):
        _fail("target-rule preview emitted an invalid file manifest")
    records = [item for item in files if isinstance(item, dict) and item.get("path") == path]
    if len(records) != 1:
        _fail("target-rule preview did not report the synthetic changed file exactly once")
    return records[0].get("will_review") is True, records[0].get("exclude_reason")


def _target_rule_selection_probe(binary: Path, version: str, directory: Path) -> dict[str, object]:
    """Prove the real OCR selector consumes target rules without changing its range."""

    git_env = _isolated_probe_environment(directory / "rule-git-home")
    repo = directory / "target-rule-selection"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    target = repo / "synthetic-template.ocrfixture"
    target.write_text("before={{ value }}\n", encoding="utf-8")
    _run(["git", "add", target.name], cwd=repo, env=git_env)
    _run(["git", "commit", "-m", "target rule baseline"], cwd=repo, env=git_env)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    target.write_text("after={{ value }}\n", encoding="utf-8")
    _run(["git", "commit", "-am", "change synthetic template"], cwd=repo, env=git_env)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    rules = directory / "target-policy-rules.json"
    rules.write_bytes(
        canonical_json(
            {
                "exclude": [],
                "include": [f"**/*{target.suffix}"],
                "rules": [
                    {
                        "merge_system_rule": True,
                        "path": f"**/*{target.suffix}",
                        "rule": "Review the synthetic target-policy fixture.",
                    }
                ],
            }
        )
    )

    json_preview = _version(version) >= (1, 9, 0)

    def preview(home_name: str, *extra: str) -> dict[str, Any] | str:
        home = directory / home_name
        env = _isolated_probe_environment(home)
        command = [
            str(binary),
            "review",
            "--from",
            base,
            "--to",
            head,
            "--preview",
            *extra,
        ]
        if json_preview:
            command.extend(["--format", "json"])
        output = _run(command, cwd=repo, env=env)
        if os.path.lexists(home / ".opencodereview" / "sessions"):
            _fail("target-rule preview created a review session store")
        if not json_preview:
            return output
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as exc:
            raise CompatibilityError("target-rule preview did not emit JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
            _fail("target-rule preview emitted an invalid file manifest")
        return payload

    without_rules = preview("rule-source-home")
    with_rules = preview("rule-target-home", "--rule", str(rules))

    source_selected, source_reason = _preview_file_selection(without_rules, target.name)
    target_selected, target_reason = _preview_file_selection(with_rules, target.name)
    expected_source_reason = "unsupported_ext"
    if source_selected or source_reason != expected_source_reason:
        _fail("synthetic file was not excluded before target-rule admission")
    if not target_selected or target_reason not in {None, ""}:
        _fail("real OCR did not select the synthetic file from target rules")
    return {
        "format": "json" if json_preview else "text",
        "from_to_unchanged": True,
        "path": target.name,
        "result": "passed",
        "source_exclusion": "unsupported_ext",
        "target_selected": True,
    }


def run_contracts(binary: Path, version: str, directory: Path) -> dict[str, Any]:
    """Run deterministic CLI and JSON-consumer probes against one OCR binary."""

    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    git_env = _isolated_probe_environment(directory / "git-home")
    repo, base, head = _synthetic_repo(directory, git_env)
    version_output = _run([str(binary), "--version"], cwd=repo)
    if re.search(rf"(?<![0-9.])v?{re.escape(version)}(?![0-9.])", version_output) is None:
        _fail(f"OCR binary did not report candidate version {version}")
    help_output = _run([str(binary), "review", "--help"], cwd=repo)
    required_review_flags = set(REQUIRED_REVIEW_FLAGS)
    if _version(version) >= (1, 10, 0):
        required_review_flags.add("--effort")
    missing = sorted(flag for flag in required_review_flags if flag not in help_output)
    if missing:
        _fail(f"candidate review help is missing required flags: {', '.join(missing)}")
    preview_home = directory / "preview-home"
    preview_env = _isolated_probe_environment(preview_home)
    preview_command = [str(binary), "review", "--from", base, "--to", head, "--preview"]
    json_preview = _version(version) >= (1, 9, 0)
    if json_preview:
        preview_command.extend(["--format", "json"])
    preview = _run(preview_command, cwd=repo, env=preview_env)
    if json_preview:
        try:
            preview_payload = json.loads(preview)
        except json.JSONDecodeError as exc:
            raise CompatibilityError("candidate JSON preview did not emit JSON") from exc
        preview_files = preview_payload.get("files") if isinstance(preview_payload, dict) else None
        if not isinstance(preview_files, list) or not any(
            isinstance(item, dict) and item.get("path") == "example.py" for item in preview_files
        ):
            _fail("candidate JSON preview did not select the synthetic changed file")
    elif "example.py" not in preview:
        _fail("candidate preview did not select the synthetic changed file")
    if os.path.lexists(preview_home / ".opencodereview" / "sessions"):
        _fail("candidate preview created a review session store")

    review_home = directory / "review-home"
    env = _isolated_probe_environment(review_home)
    with _stub_gateway() as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        result_output = _run(
            [
                str(binary),
                "review",
                "--from",
                base,
                "--to",
                head,
                "--format",
                "json",
                "--audience",
                "agent",
                "--concurrency",
                "1",
            ],
            cwd=repo,
            env=env,
        )
        review_stages = list(_StubHandler.request_stages)
    try:
        sample = json.loads(result_output)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("candidate full review did not emit JSON") from exc
    if not isinstance(sample, dict):
        _fail("candidate full review emitted an unsupported result object")
    optional_capabilities = detect_optional_capabilities(help_output, sample)
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(sample)
    except OcrResultContractError as exc:
        raise CompatibilityError(
            f"candidate full review emitted an unsupported result object: {exc}"
        ) from exc
    if outcome.kind != "clean":
        _fail(f"candidate full review did not complete cleanly: {outcome.kind}")
    comments = sample.get("comments")
    if not isinstance(comments, list) or len(comments) != 1 or not isinstance(comments[0], dict):
        _fail("candidate full review did not emit the synthetic comment")
    if _version(version) >= (1, 10, 0):
        _validate_file_groups(sample.get("groups"), {"example.py"})
        if review_stages != ["main", "main", "filter", "main"]:
            _fail(f"default medium review emitted an unexpected stage sequence: {review_stages!r}")
    sample["future_additive_field"] = {"accepted": True}
    from ocr_toolkit.posting.comments import comment_line
    from ocr_toolkit.posting.formatting import (
        format_inline_comment,
        format_token_usage_summary,
        format_tool_calls_summary,
    )

    comment = comments[0]
    assert isinstance(comment, dict)
    rendered = format_inline_comment(comment)
    if comment_line(comment) != 2 or "Synthetic compatibility finding" not in rendered:
        _fail("toolkit posting consumer rejected the candidate result contract")
    token_summary = format_token_usage_summary(sample)
    if not token_summary or "total" not in token_summary:
        _fail("toolkit token summary rejected the candidate result contract")
    if "1 total" not in format_tool_calls_summary(sample.get("tool_calls")):
        _fail("toolkit tool-call summary rejected the candidate result contract")
    thinking_probe: dict[str, Any] | None = None
    if _version(version) >= (1, 9, 0):
        if comment.get("thinking") != "Synthetic private compatibility reasoning.":
            _fail("candidate did not preserve additive comment thinking")
        if "Synthetic private compatibility reasoning." in rendered:
            _fail("toolkit posting consumer exposed private comment thinking")
        thinking_probe = {
            "additive_field_preserved": True,
            "posting_exposes_thinking": False,
            "result": "passed",
        }

    contracts: dict[str, Any] = {
        "numeric_cli_probe": _numeric_cli_probe(binary, repo, base, head, directory),
        "optional_capabilities": optional_capabilities,
        "review_budget_probe": _budget_result_probe(binary, directory),
        "target_rule_selection_probe": _target_rule_selection_probe(binary, version, directory),
        "version_probe": "passed",
        "required_review_flags": sorted(required_review_flags),
        "preview_probe": {
            "format": "json" if json_preview else "text",
            "path": "example.py",
            "result": "passed",
            "session_store_created": False,
        },
        "result_contract_probe": {
            "additive_fields_allowed": True,
            "comment_fields": sorted(comment),
            "manifest_schema": ("ocr.run-manifest/v1" if outcome.manifest_present else "legacy"),
            "normalized_outcome": outcome.kind,
            "result": "passed",
        },
    }
    if _version(version) >= (1, 10, 0):
        contracts["semantic_grouping_probe"] = _semantic_grouping_probe(binary, version, directory)
    if _version(version) >= (1, 9, 10):
        contracts["completion_cap_probe"] = _completion_cap_probe(binary, version, directory)
    if thinking_probe is not None:
        contracts["comment_thinking_probe"] = thinking_probe
    return contracts


def classify_candidate(
    *, comparison_version: str, version: str, release_notes: str, contracts_passed: bool
) -> tuple[str, list[str]]:
    """Classify only unambiguous same-minor patches as automatic-safe."""

    base = _version(comparison_version)
    candidate = _version(version)
    reasons: list[str] = []
    if candidate[:2] != base[:2] or candidate[2] != base[2] + 1:
        reasons.append("candidate is not a newer patch in the tested major/minor line")
    if not contracts_passed:
        reasons.append("one or more deterministic compatibility probes failed")
    if MATERIAL_NOTES_RE.search(release_notes):
        reasons.append("release notes contain a material or ambiguous compatibility signal")
    if not SAFE_NOTES_RE.search(release_notes):
        reasons.append("release notes do not contain an allowlisted maintenance signal")
    if reasons:
        return "human-review-required", reasons
    return "automatic-safe", ["same-minor patch passed all probes with maintenance-only notes"]


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
        remaining = MAX_RELEASE_CHANGES_CHARS - total
        if remaining <= 0 or len(lines) >= MAX_RELEASE_CHANGES_LINES:
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
        _fail(f"field {field!r} must be a bounded string")
    cleaned = "".join(character for character in value if ord(character) >= 32).strip()
    return html.escape(cleaned, quote=False).replace("@", "@\u200b")


def qualification_status(
    *,
    tag: str,
    comparison_version: str,
    tested_baseline_version: str,
    result: str,
    phase: str,
    reason: str,
) -> dict[str, str]:
    """Build the closed public status retained for one qualification attempt."""

    if VERSION_RE.fullmatch(tag) is None:
        _fail("qualification status tag is invalid")
    version = tag.removeprefix("v")
    comparison = comparison_version.removeprefix("v")
    baseline = tested_baseline_version.removeprefix("v")
    _version(comparison)
    _version(baseline)
    if result not in {"compatible", "failed"}:
        _fail("qualification status result is invalid")
    if phase not in QUALIFICATION_PHASES or reason not in QUALIFICATION_REASONS:
        _fail("qualification status phase or reason is invalid")
    if (result == "compatible") != (phase == "complete" and reason == "compatible"):
        _fail("qualification status result is inconsistent")
    if result == "failed" and reason not in QUALIFICATION_FAILURE_REASONS.get(phase, frozenset()):
        _fail("qualification status failure phase and reason are inconsistent")
    return {
        "comparison_version": comparison,
        "phase": phase,
        "reason": reason,
        "result": result,
        "schema": QUALIFICATION_STATUS_SCHEMA,
        "tag": f"v{version}",
        "tested_baseline_version": baseline,
        "version": version,
    }


def validate_qualification_status(value: dict[str, Any]) -> dict[str, str]:
    """Reject any status that contains open-ended or inconsistent public data."""

    expected_keys = {
        "comparison_version",
        "phase",
        "reason",
        "result",
        "schema",
        "tag",
        "tested_baseline_version",
        "version",
    }
    if set(value) != expected_keys or value.get("schema") != QUALIFICATION_STATUS_SCHEMA:
        _fail("qualification status schema is invalid")
    status = qualification_status(
        tag=value.get("tag") if isinstance(value.get("tag"), str) else "",
        comparison_version=(
            value.get("comparison_version")
            if isinstance(value.get("comparison_version"), str)
            else ""
        ),
        tested_baseline_version=(
            value.get("tested_baseline_version")
            if isinstance(value.get("tested_baseline_version"), str)
            else ""
        ),
        result=value.get("result") if isinstance(value.get("result"), str) else "",
        phase=value.get("phase") if isinstance(value.get("phase"), str) else "",
        reason=value.get("reason") if isinstance(value.get("reason"), str) else "",
    )
    if value.get("version") != status["version"]:
        _fail("qualification status version is inconsistent")
    return status


def _qualification_stage(phase: str, reason: str, function: Callable[[], T]) -> T:
    """Run one private qualification stage and expose only its closed identity."""

    try:
        return function()
    except QualificationStageError:
        raise
    except CompatibilityError as exc:
        raise QualificationStageError(str(exc), phase=phase, reason=reason) from exc


def qualify_release(
    release: dict[str, Any],
    manifest: dict[str, Any],
    output: Path,
    *,
    comparison_version: str | None = None,
    tested_baseline_version: str | None = None,
) -> dict[str, Any]:
    """Download, verify, execute, and classify one upstream release."""

    def metadata() -> tuple[str, str, list[Asset]]:
        tag = release.get("tag_name")
        if not isinstance(tag, str) or VERSION_RE.fullmatch(tag) is None:
            _fail("candidate tag is not a stable semantic version")
        if os.environ.get("RUNNER_OS") != "Linux":
            _fail(
                "candidate execution requires a Linux runner; checksum validation is cross-platform"
            )
        return tag, tag.removeprefix("v"), release_assets(release)

    tag, version, assets = _qualification_stage("metadata", "metadata-invalid", metadata)
    with tempfile.TemporaryDirectory(prefix="ocr-compat-") as temp_value:
        temp = Path(temp_value)

        def artifacts() -> dict[str, Path]:
            downloaded = {asset.name: _download(asset, temp) for asset in assets}
            checksums = parse_checksum_file(downloaded["sha256sum.txt"])
            binaries = {
                asset.name: asset.sha256 for asset in assets if asset.name != "sha256sum.txt"
            }
            if checksums != binaries:
                _fail("upstream checksum file and GitHub asset digests disagree")
            return downloaded

        downloaded = _qualification_stage("artifact", "artifact-verification-failed", artifacts)
        contracts = _qualification_stage(
            "contracts",
            "contract-probe-failed",
            lambda: run_contracts(downloaded["opencodereview-linux-amd64"], version, temp),
        )
    raw_notes = release.get("body")
    notes = raw_notes if isinstance(raw_notes, str) else ""
    tested_baseline = tested_baseline_version or str(manifest["recommended_version"])
    comparison = comparison_version or tested_baseline
    _version(tested_baseline)
    _version(comparison)
    if tested_baseline != manifest["recommended_version"]:
        _fail("candidate qualification tested baseline is stale")
    if _version(comparison) < _version(tested_baseline):
        _fail("candidate comparison version predates the tested baseline")
    classification, reasons = classify_candidate(
        comparison_version=comparison,
        version=version,
        release_notes=notes,
        contracts_passed=True,
    )
    evidence = {
        "schema_version": 2,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "version": version,
        "tag": tag,
        "published_at": release.get("published_at"),
        "result": "compatible",
        "classification": classification,
        "classification_reasons": reasons,
        "comparison_version": comparison,
        "tested_baseline_version": tested_baseline,
        "assets": [
            {"name": asset.name, "sha256": asset.sha256, "size": asset.size} for asset in assets
        ],
        "contracts": contracts,
        "release_changes": release_changes_excerpt(notes),
        "release_notes_sha256": hashlib.sha256(notes.encode()).hexdigest(),
    }

    def write_evidence() -> None:
        write_atomic_bytes(output, canonical_json(evidence), label="compatibility evidence")

    _qualification_stage("evidence", "evidence-write-failed", write_evidence)
    return evidence


def _replace_exact(text: str, old: str, new: str, *, source: str) -> str:
    count = text.count(old)
    if count != 1:
        _fail(f"expected exactly one {source} occurrence of {old!r}, found {count}")
    return text.replace(old, new)


def assess_automatic_chain(
    manifest: dict[str, Any], evidences: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate one observed chain and report whether cumulative automation is safe."""

    if not evidences or len(evidences) > MAX_QUALIFICATION_CHAIN:
        _fail("candidate evidence chain must be a non-empty bounded list")
    ordered = sorted(evidences, key=lambda item: _version(str(item.get("version", ""))))
    tested_baseline = str(manifest["recommended_version"])
    comparison = tested_baseline
    versions: list[str] = []
    classifications: list[str] = []
    contiguous = True
    for item in ordered:
        version = item.get("version")
        if not isinstance(version, str) or version in versions:
            _fail("candidate evidence chain contains an invalid or duplicate version")
        candidate = _version(version)
        previous = _version(comparison)
        if candidate[:2] != previous[:2] or candidate[2] != previous[2] + 1:
            contiguous = False
        if (
            item.get("schema_version") != 2
            or item.get("tested_baseline_version") != tested_baseline
            or item.get("comparison_version") != comparison
            or item.get("result") != "compatible"
        ):
            _fail(f"candidate evidence {version} does not match the observed chain contract")
        classification = item.get("classification")
        if classification not in {"automatic-safe", "human-review-required"}:
            _fail(f"candidate evidence {version} has an invalid classification")
        versions.append(version)
        classifications.append(classification)
        comparison = version
    automatic = contiguous and all(value == "automatic-safe" for value in classifications)
    return {
        "automatic_blockers": ([] if contiguous else ["non-contiguous release sequence"]),
        "classification": "automatic-safe" if automatic else "human-review-required",
        "target_version": versions[-1],
        "tested_baseline_version": tested_baseline,
        "versions": versions,
    }


def prepare_update(
    *,
    manifest_path: Path,
    evidence: dict[str, Any] | list[dict[str, Any]],
    fragment_number: int,
    human_conclusions: dict[str, str] | None = None,
    root: Path = ROOT,
) -> list[Path]:
    """Prepare one cumulative promotion from a validated adjacent evidence chain."""

    if fragment_number <= 0:
        _fail("fragment_number must be a positive issue number")
    manifest = load_json(manifest_path)
    validate_manifest(manifest, root)
    old_version = str(manifest["recommended_version"])
    evidences = [evidence] if isinstance(evidence, dict) else list(evidence)
    if not evidences or len(evidences) > MAX_QUALIFICATION_CHAIN:
        _fail("candidate evidence chain must be a non-empty bounded list")
    evidences.sort(key=lambda item: _version(str(item.get("version", ""))))
    conclusions = human_conclusions or {}
    expected_comparison = old_version
    versions: list[str] = []
    for item in evidences:
        version = item.get("version")
        if not isinstance(version, str):
            _fail("candidate evidence version must be a string")
        if version in versions:
            _fail(f"candidate evidence chain contains duplicate version {version}")
        candidate = _version(version)
        comparison = _version(expected_comparison)
        transition = _release_transition(comparison, candidate)
        if transition is None:
            _fail("candidate evidence chain is not a contiguous release sequence")
        if transition != "patch" and item.get("schema_version") != 2:
            _fail("minor and major promotions require chain-aware evidence schema 2")
        if item.get("result") != "compatible":
            _fail(f"candidate evidence does not qualify {version} as compatible")
        schema_version = item.get("schema_version")
        if schema_version == 2:
            if item.get("tested_baseline_version") != old_version:
                _fail(f"candidate evidence {version} has a stale tested baseline")
            if item.get("comparison_version") != expected_comparison:
                _fail(f"candidate evidence {version} has a non-adjacent comparison version")
        elif schema_version != 1 or len(evidences) != 1:
            _fail("multi-release promotion requires chain-aware evidence schema 2")
        classification = item.get("classification")
        conclusion = conclusions.get(version)
        if conclusion is not None and (
            not isinstance(conclusion, str)
            or not conclusion.strip()
            or len(conclusion) > 2_000
            or any(ord(character) < 32 and character not in "\n\t" for character in conclusion)
        ):
            _fail(f"candidate {version} conclusion must be bounded plain text")
        if classification == "human-review-required":
            if conclusion is None:
                _fail(f"human-reviewed candidate {version} requires a bounded conclusion")
        elif classification != "automatic-safe":
            _fail(f"candidate evidence {version} has an invalid classification")
        if transition != "patch" and classification != "human-review-required":
            _fail("minor and major promotions require explicit human review")
        versions.append(version)
        expected_comparison = version
    unknown_conclusions = set(conclusions).difference(versions)
    if unknown_conclusions:
        _fail("human conclusions may reference only evidence versions in this promotion")

    version = versions[-1]
    releases = manifest.get("releases")
    assert isinstance(releases, list)
    existing_versions = {str(item.get("version")) for item in releases if isinstance(item, dict)}
    if any(candidate in existing_versions for candidate in versions):
        _fail("candidate evidence chain overlaps an existing manifest release")
    old_entry = next(
        (
            item
            for item in releases
            if isinstance(item, dict) and item.get("version") == old_version
        ),
        None,
    )
    if old_entry is None:
        _fail("manifest lost its previous recommended release")
    old_assets = old_entry.get("assets")
    if not isinstance(old_assets, list):
        _fail("previous recommended release assets are invalid")
    old_linux_asset = next(
        (
            asset
            for asset in old_assets
            if isinstance(asset, dict) and asset.get("name") == "opencodereview-linux-amd64"
        ),
        None,
    )
    if old_linux_asset is None or not isinstance(old_linux_asset.get("sha256"), str):
        _fail("previous recommended release lacks the Linux amd64 checksum")
    old_linux = old_linux_asset["sha256"]
    destinations: list[Path] = []
    evidence_payloads: list[bytes] = []
    for item in evidences:
        candidate_version = str(item["version"])
        evidence_name = f"ocr-{candidate_version}.json"
        destination = root / "compatibility" / "evidence" / evidence_name
        payload = canonical_json(item)
        destinations.append(destination)
        evidence_payloads.append(payload)
        assets = item.get("assets")
        if not isinstance(assets, list) or len(assets) != len(REQUIRED_ASSETS):
            _fail(f"candidate evidence {candidate_version} assets must be the supported matrix")
        asset_names: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict):
                _fail(f"candidate evidence {candidate_version} asset must be an object")
            name, size, sha256 = asset.get("name"), asset.get("size"), asset.get("sha256")
            if not isinstance(name, str) or name in asset_names or Path(name).name != name:
                _fail(f"candidate evidence {candidate_version} asset name is invalid")
            asset_names.add(name)
            if not isinstance(size, int) or size <= 0 or size > MAX_ASSET_BYTES:
                _fail(f"candidate evidence {candidate_version}/{name} size is invalid")
            if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
                _fail(f"candidate evidence {candidate_version}/{name} digest is invalid")
        if asset_names != REQUIRED_ASSETS:
            _fail(f"candidate evidence {candidate_version} asset set is invalid")
        contracts = item.get("contracts")
        capabilities = (
            contracts.get("optional_capabilities", []) if isinstance(contracts, dict) else []
        )
        if (
            not isinstance(capabilities, list)
            or capabilities != sorted(set(capabilities))
            or any(value not in KNOWN_OPTIONAL_CAPABILITIES for value in capabilities)
        ):
            _fail(f"candidate evidence {candidate_version} capabilities are invalid")
        conclusion = conclusions.get(candidate_version)
        if conclusion is None:
            conclusion = (
                "Machine-qualified same-minor maintenance patch; promotion still requires "
                "protected PR review and release gates."
            )
        releases.append(
            {
                "assets": assets,
                "capabilities": capabilities,
                "evidence": f"compatibility/evidence/{evidence_name}",
                "evidence_sha256": hashlib.sha256(payload).hexdigest(),
                "human_conclusion": conclusion.strip(),
                "published_at": item.get("published_at"),
                "release_url": (
                    f"https://github.com/{UPSTREAM_REPOSITORY}/releases/tag/v{candidate_version}"
                ),
                "status": "tested",
                "version": candidate_version,
            }
        )
    releases.sort(
        key=lambda item: _version(str(item["version"])) if isinstance(item, dict) else (0, 0, 0)
    )
    manifest["monitoring_floor"] = version
    manifest["recommended_version"] = version
    manifest_payload = canonical_json(manifest)

    preflight_path = root / PREFLIGHT.relative_to(ROOT)
    preflight = preflight_path.read_text(encoding="utf-8")
    preflight = _replace_exact(
        preflight,
        f'EXPECTED_OCR_VERSION = "{old_version}"',
        f'EXPECTED_OCR_VERSION = "{version}"',
        source="preflight version",
    )
    final_assets = evidences[-1].get("assets")
    assert isinstance(final_assets, list)
    linux_asset = next(
        (
            asset
            for asset in final_assets
            if isinstance(asset, dict) and asset.get("name") == "opencodereview-linux-amd64"
        ),
        None,
    )
    if linux_asset is None or not isinstance(linux_asset.get("sha256"), str):
        _fail("candidate evidence lacks the Linux amd64 checksum")
    example_path = root / GITLAB_EXAMPLE.relative_to(ROOT)
    example = example_path.read_text(encoding="utf-8")
    example = _replace_exact(
        example,
        f'OCR_VERSION: "v{old_version}"',
        f'OCR_VERSION: "v{version}"',
        source="example version",
    )
    example = _replace_exact(
        example,
        f'OCR_SHA256: "{old_linux}"',
        f'OCR_SHA256: "{linux_asset["sha256"]}"',
        source="example checksum",
    )
    changelog_dir = root / "changelog.d"
    fragment = changelog_dir / f"{fragment_number}.maintenance.md"
    qualified = version if len(versions) == 1 else f"{versions[0]} through {version}"
    fragment_text = (
        f"Target checksum-verified Open Code Review {version} after qualifying {qualified}.\n"
    )

    # Validate every input and transformation before changing the checkout, then
    # write each accepted evidence snapshot together with its linked manifest.
    destinations[0].parent.mkdir(parents=True, exist_ok=True)
    changelog_dir.mkdir(exist_ok=True)
    for destination, payload in zip(destinations, evidence_payloads, strict=True):
        destination.write_bytes(payload)
    manifest_path.write_bytes(manifest_payload)
    preflight_path.write_text(preflight, encoding="utf-8")
    example_path.write_text(example, encoding="utf-8")
    fragment.write_text(fragment_text, encoding="utf-8")
    return [manifest_path, *destinations, preflight_path, example_path, fragment]


def render_issue(evidence: dict[str, Any]) -> str:
    """Render bounded, injection-resistant Markdown for a qualification issue."""

    version = evidence.get("version")
    if not isinstance(version, str) or VERSION_RE.fullmatch(version) is None:
        _fail("qualification evidence version is invalid")
    classification = evidence.get("classification")
    if classification not in {"automatic-safe", "human-review-required"}:
        _fail("qualification evidence classification is invalid")
    if evidence.get("result") != "compatible":
        _fail("qualification evidence result is not compatible")
    reasons = evidence.get("classification_reasons", [])
    if not isinstance(reasons, list) or len(reasons) > 20:
        _fail("qualification evidence classification reasons are invalid")
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
        if isinstance(published_value, str) and PUBLISHED_AT_RE.fullmatch(published_value)
        else "unknown"
    )
    comparison = evidence.get("comparison_version", evidence.get("baseline_version"))
    tested_baseline = evidence.get("tested_baseline_version", evidence.get("baseline_version"))
    compare_line = ""
    if isinstance(comparison, str) and VERSION_RE.fullmatch(comparison) is not None:
        compare_line = (
            f"- compare: https://github.com/{UPSTREAM_REPOSITORY}/compare/"
            f"v{comparison}...v{version}\n"
        )
    tested_line = ""
    if isinstance(tested_baseline, str) and VERSION_RE.fullmatch(tested_baseline) is not None:
        tested_line = f"- current tested baseline: `v{tested_baseline}`\n"
    return (
        f"<!-- ocr-compat-candidate:v{version} -->\n"
        f"## OCR v{version} compatibility evidence\n\n"
        f"- machine result: **{evidence['result']}**\n"
        f"- classification: **{classification}**\n"
        f"- all upstream asset digests and `sha256sum.txt`: verified\n"
        f"- Linux amd64 version/help/preview/result-consumer probes: passed\n\n"
        "### Upstream release changes\n\n"
        f"- release: https://github.com/{UPSTREAM_REPOSITORY}/releases/tag/v{version}\n"
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

    checked = validate_qualification_status(status)
    if checked["result"] != "failed":
        _fail("failure issue requires a failed qualification status")
    version = checked["version"]
    return (
        f"<!-- ocr-compat-candidate:v{version} -->\n"
        f"## OCR v{version} compatibility qualification failed\n\n"
        "- machine result: **failed**\n"
        f"- closed phase: `{checked['phase']}`\n"
        f"- closed reason: `{checked['reason']}`\n"
        f"- current tested baseline: `v{checked['tested_baseline_version']}`\n"
        f"- compare: https://github.com/{UPSTREAM_REPOSITORY}/compare/"
        f"v{checked['comparison_version']}...v{version}\n"
        f"- release: https://github.com/{UPSTREAM_REPOSITORY}/releases/tag/v{version}\n\n"
        "The candidate was not classified as compatible. Raw process diagnostics are "
        "not copied into this issue.\n\n"
        f"### Workflow evidence\n\n- run: {run_url}\n\n"
        "### Resume checklist\n\n"
        "- [ ] Inspect the bounded workflow artifact and private job log.\n"
        "- [ ] Correct or explicitly classify the failed compatibility boundary.\n"
        "- [ ] Rerun the same candidate; update this issue instead of creating a duplicate.\n"
        "- [ ] Promote only after compatible evidence and protected review.\n"
    )


def find_qualification_issue(repository: str, marker: str) -> int | None:
    """Find one exact marker through bounded direct issue listing, without search indexing."""

    if REPOSITORY_RE.fullmatch(repository) is None:
        _fail("repository must use the owner/name form")
    matches: list[int] = []
    for page in range(1, MAX_ISSUE_PAGES + 1):
        url = f"https://api.github.com/repos/{repository}/issues?state=all&per_page=100&page={page}"
        value = _issue_api_request(url)
        if not isinstance(value, list) or len(value) > 100:
            _fail("GitHub issue listing has unsupported shape or size")
        for issue in value:
            if not isinstance(issue, dict) or "pull_request" in issue:
                continue
            number = issue.get("number")
            body = issue.get("body")
            if (
                isinstance(number, int)
                and not isinstance(number, bool)
                and isinstance(body, str)
                and marker in body
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
        _fail(f"issue lookup exceeded {MAX_ISSUE_PAGES} pages")
    matches = sorted(set(matches))
    if len(matches) > 1:
        _fail(
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
        _fail("issue upsert requires exactly one evidence or status input")
    record = evidence if evidence is not None else validate_qualification_status(status or {})
    version = record.get("version")
    if not isinstance(version, str) or VERSION_RE.fullmatch(version) is None:
        _fail("qualification evidence version is invalid")
    expected_run_prefix = f"https://github.com/{repository}/actions/runs/"
    if (
        not run_url.startswith(expected_run_prefix)
        or not run_url.removeprefix(expected_run_prefix).isdigit()
    ):
        _fail("workflow run URL is invalid for the target repository")
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
    if not isinstance(returned_number, int) or isinstance(returned_number, bool):
        _fail("GitHub issue write did not return a valid issue number")
    if issue_number is not None and returned_number != issue_number:
        _fail("GitHub issue update returned a different issue number")
    return returned_number


def parse_human_conclusions(values: list[str]) -> dict[str, str]:
    """Parse repeatable VERSION=CONCLUSION CLI values without losing whitespace."""

    conclusions: dict[str, str] = {}
    for value in values:
        version, separator, conclusion = value.partition("=")
        if not separator or VERSION_RE.fullmatch(version) is None or version in conclusions:
            _fail("human conclusions must be unique VERSION=CONCLUSION values")
        conclusions[version] = conclusion
    return conclusions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    discover = subparsers.add_parser("discover")
    discover.add_argument("--output", type=Path, required=True)
    matrix = subparsers.add_parser("build-matrix")
    matrix.add_argument("--releases", type=Path, required=True)
    matrix.add_argument("--output", type=Path, required=True)
    qualify = subparsers.add_parser("qualify")
    qualify.add_argument("--tag", required=True)
    qualify.add_argument("--comparison-version")
    qualify.add_argument("--tested-baseline-version")
    qualify.add_argument("--output", type=Path, required=True)
    qualify.add_argument("--issue-body", type=Path)
    qualify.add_argument("--status-output", type=Path)
    assess = subparsers.add_parser("assess-chain")
    assess.add_argument("--evidence", type=Path, action="append", required=True)
    assess.add_argument("--output", type=Path, required=True)
    prepare = subparsers.add_parser("prepare-update")
    prepare.add_argument("--evidence", type=Path, action="append", required=True)
    prepare.add_argument("--human-conclusion", action="append", default=[])
    prepare.add_argument("--fragment-number", type=int, required=True)
    probe_local = subparsers.add_parser("probe-local")
    probe_local.add_argument("--binary", type=Path, required=True)
    probe_local.add_argument("--version", required=True)
    probe_local.add_argument("--output", type=Path, required=True)
    upsert_issue = subparsers.add_parser("upsert-issue")
    upsert_input = upsert_issue.add_mutually_exclusive_group(required=True)
    upsert_input.add_argument("--evidence", type=Path)
    upsert_input.add_argument("--status", type=Path)
    upsert_issue.add_argument("--repository", required=True)
    upsert_issue.add_argument("--run-url", required=True)
    upsert_issue.add_argument("--output-number", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest: dict[str, Any] | None = None

    def finish_issue_upsert(
        *, evidence: dict[str, Any] | None = None, status: dict[str, Any] | None = None
    ) -> int:
        issue_number = upsert_qualification_issue(
            repository=args.repository,
            evidence=evidence,
            status=status,
            run_url=args.run_url,
        )
        write_atomic_bytes(
            args.output_number,
            f"{issue_number}\n".encode(),
            label="qualification issue number",
        )
        print(f"qualification issue: #{issue_number}")
        return 0

    try:
        if args.command == "upsert-issue" and args.status is not None:
            return finish_issue_upsert(status=load_json(args.status))
        manifest = load_json(args.manifest)
        validate_manifest(manifest, args.manifest.resolve().parents[1])
        if args.command == "validate":
            print("OCR support manifest validated")
            return 0
        if args.command == "discover":
            unseen = discover_unseen(manifest)
            args.output.write_bytes(canonical_json({"releases": unseen}))
            print(f"discovered {len(unseen)} unseen stable OCR release(s)")
            return 0
        if args.command == "build-matrix":
            release_payload = load_json(args.releases)
            releases = release_payload.get("releases")
            if not isinstance(releases, list):
                _fail("discovery payload must contain a release list")
            result = qualification_matrix(manifest, releases)
            args.output.write_bytes(canonical_json(result))
            print(f"built qualification matrix with {len(result['include'])} release(s)")
            return 0
        if args.command == "assess-chain":
            evidences = [load_json(path) for path in args.evidence]
            result = assess_automatic_chain(manifest, evidences)
            args.output.write_bytes(canonical_json(result))
            print(f"assessed OCR chain: {result['classification']}")
            return 0
        if args.command == "prepare-update":
            evidences = [load_json(path) for path in args.evidence]
            changed = prepare_update(
                manifest_path=args.manifest,
                evidence=evidences,
                fragment_number=args.fragment_number,
                human_conclusions=parse_human_conclusions(args.human_conclusion),
            )
            print("prepared OCR compatibility update:")
            for path in changed:
                print(path.resolve().relative_to(ROOT))
            return 0
        if args.command == "upsert-issue":
            assert args.evidence is not None
            return finish_issue_upsert(evidence=load_json(args.evidence))
        if args.command == "probe-local":
            version = args.version.removeprefix("v")
            _version(version)
            binary = args.binary.resolve(strict=True)
            if not binary.is_file():
                _fail("local OCR binary must be a regular file")
            with tempfile.TemporaryDirectory(prefix="ocr-local-probe-") as temp_value:
                contracts = run_contracts(binary, version, Path(temp_value))
            receipt = {"contracts": contracts, "result": "compatible", "version": version}
            args.output.write_bytes(canonical_json(receipt))
            print(f"local OCR {version} contract probes passed")
            return 0
        try:
            release = _request_json(f"{UPSTREAM_API}/releases/tags/{args.tag}")
        except CompatibilityError as exc:
            raise QualificationStageError(
                str(exc), phase="metadata", reason="metadata-request-failed"
            ) from exc
        if not isinstance(release, dict):
            _fail("upstream tag response must be an object")
        evidence = qualify_release(
            release,
            manifest,
            args.output,
            comparison_version=args.comparison_version,
            tested_baseline_version=args.tested_baseline_version,
        )
        if args.issue_body is not None:
            _qualification_stage(
                "evidence",
                "issue-body-write-failed",
                lambda: write_atomic_bytes(
                    args.issue_body,
                    render_issue(evidence).encode(),
                    label="qualification issue body",
                ),
            )
        if args.status_output is not None:
            status = qualification_status(
                tag=args.tag,
                comparison_version=args.comparison_version or str(manifest["recommended_version"]),
                tested_baseline_version=args.tested_baseline_version
                or str(manifest["recommended_version"]),
                result="compatible",
                phase="complete",
                reason="compatible",
            )
            _qualification_stage(
                "evidence",
                "status-write-failed",
                lambda: write_atomic_bytes(
                    args.status_output,
                    canonical_json(status),
                    label="compatibility status",
                ),
            )
        print(f"qualified OCR {evidence['version']}: {evidence['classification']}")
        return 0
    except CompatibilityError as exc:
        if args.command == "qualify" and args.status_output is not None:
            phase = exc.phase if isinstance(exc, QualificationStageError) else "metadata"
            reason = exc.reason if isinstance(exc, QualificationStageError) else "metadata-invalid"
            manifest_version = (
                str(manifest["recommended_version"])
                if isinstance(manifest, dict) and "recommended_version" in manifest
                else ""
            )
            try:
                status = qualification_status(
                    tag=args.tag,
                    comparison_version=args.comparison_version or manifest_version,
                    tested_baseline_version=args.tested_baseline_version or manifest_version,
                    result="failed",
                    phase=phase,
                    reason=reason,
                )
                write_atomic_bytes(
                    args.status_output,
                    canonical_json(status),
                    label="compatibility status",
                )
            except (CompatibilityError, OSError) as status_exc:
                print(f"OCR compatibility status write failed: {status_exc}", file=sys.stderr)
        print(f"OCR compatibility qualification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
