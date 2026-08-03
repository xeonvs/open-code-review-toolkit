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
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "compatibility" / "ocr-support.json"
PREFLIGHT = ROOT / "src" / "ocr_toolkit" / "preflight.py"
GITLAB_EXAMPLE = ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
README = ROOT / "README.md"
GITLAB_DOC = ROOT / "docs" / "gitlab.md"
SECURITY_DOC = ROOT / "docs" / "security.md"
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
DOWNLOAD_ATTEMPTS = 3
VERSION_RE = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PUBLISHED_AT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SAFE_NOTES_RE = re.compile(
    r"\b(fix|bug|documentation|docs|test|chore|refactor|performance)\b", re.I
)
MATERIAL_NOTES_RE = re.compile(
    r"\b(breaking|remove[ds]?|deprecat|security|vulnerab|protocol|schema|format|cli|flag|config|provider|gitlab)\b",
    re.I,
)
REQUIRED_REVIEW_FLAGS = {
    "--audience",
    "--background-file",
    "--format",
    "--from",
    "--preview",
    "--rule",
    "--to",
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


class CompatibilityError(Exception):
    """OCR compatibility metadata or qualification failed closed."""


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


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


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


def _synthetic_repo(directory: Path) -> tuple[Path, str, str]:
    repo = directory / "synthetic-review"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], cwd=repo)
    _run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo)
    _run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo)
    target = repo / "example.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo)
    _run(["git", "commit", "-m", "baseline"], cwd=repo)
    base = _run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    target.write_text("def value():\n    return 2\n", encoding="utf-8")
    _run(["git", "add", "example.py"], cwd=repo)
    _run(["git", "commit", "-m", "change value"], cwd=repo)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    return repo, base, head


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """Deterministic OpenAI-compatible response sequence for OCR probes."""

    request_count = 0

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
        type(self).request_count += 1
        if type(self).request_count == 1:
            arguments = json.dumps(
                {
                    "comments": [
                        {
                            "content": "Synthetic compatibility finding.",
                            "existing_code": "    return 2",
                            "category": "maintainability",
                            "severity": "low",
                        }
                    ]
                }
            )
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-comment",
                        "type": "function",
                        "function": {"name": "code_comment", "arguments": arguments},
                    }
                ],
            }
            finish_reason = "tool_calls"
        elif type(self).request_count == 2:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-done",
                        "type": "function",
                        "function": {"name": "task_done", "arguments": "{}"},
                    }
                ],
            }
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": "[]"}
            finish_reason = "stop"
        payload = json.dumps(
            {
                "id": f"compat-{type(self).request_count}",
                "object": "chat.completion",
                "model": "synthetic-model",
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
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
def _stub_gateway() -> Iterator[str]:
    _StubHandler.request_count = 0
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_contracts(binary: Path, version: str, directory: Path) -> dict[str, Any]:
    """Run deterministic CLI and JSON-consumer probes against one OCR binary."""

    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    repo, base, head = _synthetic_repo(directory)
    version_output = _run([str(binary), "--version"], cwd=repo)
    if re.search(rf"(?<![0-9.])v?{re.escape(version)}(?![0-9.])", version_output) is None:
        _fail(f"OCR binary did not report candidate version {version}")
    help_output = _run([str(binary), "review", "--help"], cwd=repo)
    missing = sorted(flag for flag in REQUIRED_REVIEW_FLAGS if flag not in help_output)
    if missing:
        _fail(f"candidate review help is missing required flags: {', '.join(missing)}")
    preview = _run([str(binary), "review", "--from", base, "--to", head, "--preview"], cwd=repo)
    if "example.py" not in preview:
        _fail("candidate preview did not select the synthetic changed file")

    env = dict(os.environ)
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
    try:
        sample = json.loads(result_output)
    except json.JSONDecodeError as exc:
        raise CompatibilityError("candidate full review did not emit JSON") from exc
    if not isinstance(sample, dict):
        _fail("candidate full review emitted an unsupported result object")
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

    return {
        "version_probe": "passed",
        "required_review_flags": sorted(REQUIRED_REVIEW_FLAGS),
        "preview_probe": {"path": "example.py", "result": "passed"},
        "result_contract_probe": {
            "additive_fields_allowed": True,
            "comment_fields": sorted(comment),
            "manifest_schema": ("ocr.run-manifest/v1" if outcome.manifest_present else "legacy"),
            "normalized_outcome": outcome.kind,
            "result": "passed",
        },
    }


def classify_candidate(
    *, baseline: str, version: str, release_notes: str, contracts_passed: bool
) -> tuple[str, list[str]]:
    """Classify only unambiguous same-minor patches as automatic-safe."""

    base = _version(baseline)
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


def qualify_release(
    release: dict[str, Any], manifest: dict[str, Any], output: Path
) -> dict[str, Any]:
    """Download, verify, execute, and classify one upstream release."""

    tag = release.get("tag_name")
    if not isinstance(tag, str) or VERSION_RE.fullmatch(tag) is None:
        _fail("candidate tag is not a stable semantic version")
    version = tag.removeprefix("v")
    assets = release_assets(release)
    if os.environ.get("RUNNER_OS") != "Linux":
        _fail("candidate execution requires a Linux runner; checksum validation is cross-platform")
    with tempfile.TemporaryDirectory(prefix="ocr-compat-") as temp_value:
        temp = Path(temp_value)
        downloaded = {asset.name: _download(asset, temp) for asset in assets}
        checksums = parse_checksum_file(downloaded["sha256sum.txt"])
        binaries = {asset.name: asset.sha256 for asset in assets if asset.name != "sha256sum.txt"}
        if checksums != binaries:
            _fail("upstream checksum file and GitHub asset digests disagree")
        contracts = run_contracts(downloaded["opencodereview-linux-amd64"], version, temp)
    raw_notes = release.get("body")
    notes = raw_notes if isinstance(raw_notes, str) else ""
    classification, reasons = classify_candidate(
        baseline=str(manifest["recommended_version"]),
        version=version,
        release_notes=notes,
        contracts_passed=True,
    )
    evidence = {
        "schema_version": 1,
        "upstream_repository": UPSTREAM_REPOSITORY,
        "version": version,
        "tag": tag,
        "published_at": release.get("published_at"),
        "result": "compatible",
        "classification": classification,
        "classification_reasons": reasons,
        "baseline_version": str(manifest["recommended_version"]),
        "assets": [
            {"name": asset.name, "sha256": asset.sha256, "size": asset.size} for asset in assets
        ],
        "contracts": contracts,
        "release_changes": release_changes_excerpt(notes),
        "release_notes_sha256": hashlib.sha256(notes.encode()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(evidence))
    return evidence


def _replace_exact(text: str, old: str, new: str, *, source: str) -> str:
    count = text.count(old)
    if count != 1:
        _fail(f"expected exactly one {source} occurrence of {old!r}, found {count}")
    return text.replace(old, new)


def prepare_update(
    *,
    manifest_path: Path,
    evidence: dict[str, Any],
    fragment_number: int,
    root: Path = ROOT,
) -> list[Path]:
    """Prepare one mechanical compatibility update for an automatic-safe candidate."""

    if evidence.get("classification") != "automatic-safe":
        _fail("only automatic-safe evidence may prepare an update")
    if fragment_number <= 0:
        _fail("fragment_number must be a positive issue number")
    manifest = load_json(manifest_path)
    validate_manifest(manifest, root)
    old_version = str(manifest["recommended_version"])
    version = evidence.get("version")
    if not isinstance(version, str):
        _fail("candidate evidence version must be a string")
    if (
        _version(version)[:2] != _version(old_version)[:2]
        or _version(version)[2] != _version(old_version)[2] + 1
    ):
        _fail("candidate no longer satisfies the same-minor patch invariant")
    evidence_name = f"ocr-{version}.json"
    destination = root / "compatibility" / "evidence" / evidence_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json(evidence))
    assets = evidence.get("assets")
    if not isinstance(assets, list):
        _fail("candidate evidence assets must be a list")
    entry = {
        "assets": assets,
        "evidence": f"compatibility/evidence/{evidence_name}",
        "evidence_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "human_conclusion": (
            "Machine-qualified same-minor maintenance patch; promotion still requires "
            "protected PR review and release gates."
        ),
        "published_at": evidence.get("published_at"),
        "release_url": (f"https://github.com/{UPSTREAM_REPOSITORY}/releases/tag/v{version}"),
        "status": "tested",
        "version": version,
    }
    releases = manifest.get("releases")
    assert isinstance(releases, list)
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
    releases.append(entry)
    releases.sort(
        key=lambda item: _version(str(item["version"])) if isinstance(item, dict) else (0, 0, 0)
    )
    manifest["monitoring_floor"] = version
    manifest["recommended_version"] = version
    manifest_path.write_bytes(canonical_json(manifest))

    preflight_path = root / PREFLIGHT.relative_to(ROOT)
    preflight = preflight_path.read_text(encoding="utf-8")
    preflight = _replace_exact(
        preflight,
        f'EXPECTED_OCR_VERSION = "{old_version}"',
        f'EXPECTED_OCR_VERSION = "{version}"',
        source="preflight version",
    )
    preflight_path.write_text(preflight, encoding="utf-8")

    linux_asset = next(
        (
            asset
            for asset in assets
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
    example_path.write_text(example, encoding="utf-8")

    docs: list[Path] = []
    for source in (README, GITLAB_DOC, SECURITY_DOC):
        path = root / source.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        text = _replace_exact(
            text, old_version, version, source=f"{path.relative_to(root)} version"
        )
        path.write_text(text, encoding="utf-8")
        docs.append(path)
    changelog_dir = root / "changelog.d"
    changelog_dir.mkdir(exist_ok=True)
    fragment = changelog_dir / f"{fragment_number}.feature.md"
    fragment.write_text(f"Target checksum-verified Open Code Review {version}.\n", encoding="utf-8")
    return [manifest_path, destination, preflight_path, example_path, *docs, fragment]


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
    baseline = evidence.get("baseline_version")
    compare_line = ""
    if isinstance(baseline, str) and VERSION_RE.fullmatch(baseline) is not None:
        compare_line = (
            f"- compare: https://github.com/{UPSTREAM_REPOSITORY}/compare/"
            f"v{baseline}...v{version}\n"
        )
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
            "- after successful completion, the workflow artifact contains the exact mechanical compatibility patch\n"
            "- opening a real PR requires the optional OCR update bot credential so protected checks run\n"
        )
    return body


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


def upsert_qualification_issue(*, repository: str, evidence: dict[str, Any], run_url: str) -> int:
    """Create or update the sole issue owned by one OCR version marker."""

    version = evidence.get("version")
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
        "body": render_workflow_issue(evidence, run_url),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    discover = subparsers.add_parser("discover")
    discover.add_argument("--output", type=Path, required=True)
    qualify = subparsers.add_parser("qualify")
    qualify.add_argument("--tag", required=True)
    qualify.add_argument("--output", type=Path, required=True)
    qualify.add_argument("--issue-body", type=Path)
    prepare = subparsers.add_parser("prepare-update")
    prepare.add_argument("--evidence", type=Path, required=True)
    prepare.add_argument("--fragment-number", type=int, required=True)
    upsert_issue = subparsers.add_parser("upsert-issue")
    upsert_issue.add_argument("--evidence", type=Path, required=True)
    upsert_issue.add_argument("--repository", required=True)
    upsert_issue.add_argument("--run-url", required=True)
    upsert_issue.add_argument("--output-number", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
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
        if args.command == "prepare-update":
            evidence = load_json(args.evidence)
            changed = prepare_update(
                manifest_path=args.manifest,
                evidence=evidence,
                fragment_number=args.fragment_number,
            )
            print("prepared OCR compatibility update:")
            for path in changed:
                print(path.relative_to(ROOT))
            return 0
        if args.command == "upsert-issue":
            evidence = load_json(args.evidence)
            issue_number = upsert_qualification_issue(
                repository=args.repository,
                evidence=evidence,
                run_url=args.run_url,
            )
            args.output_number.write_text(f"{issue_number}\n", encoding="utf-8")
            print(f"qualification issue: #{issue_number}")
            return 0
        release = _request_json(f"{UPSTREAM_API}/releases/tags/{args.tag}")
        if not isinstance(release, dict):
            _fail("upstream tag response must be an object")
        evidence = qualify_release(release, manifest, args.output)
        if args.issue_body is not None:
            args.issue_body.write_text(render_issue(evidence), encoding="utf-8")
        print(f"qualified OCR {evidence['version']}: {evidence['classification']}")
        return 0
    except CompatibilityError as exc:
        print(f"OCR compatibility qualification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
