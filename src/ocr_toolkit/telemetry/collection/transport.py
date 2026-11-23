"""Read bounded, authenticated GitLab API responses through the active glab context."""

from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ..links import INSTANCE_PATH, web_location
from ..state import TelemetryError

MAX_BYTES = 8 * 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 16 * 1024
MAX_CALLS = 50_000
MAX_ROWS = 10_000
REQUEST_SECONDS = 30
GLAB_ENVIRONMENT = frozenset(
    [
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "GLAB_CONFIG_DIR",
        "GLAB_API_PROTOCOL",
        "GLAB_GIT_PROTOCOL",
        "GITLAB_HOST",
        "GITLAB_URI",
        "GITLAB_URL",
        "GL_HOST",
        "GITLAB_REPO",
        "GITLAB_API_HOST",
        "GITLAB_TOKEN",
        "GITLAB_ACCESS_TOKEN",
        "OAUTH_TOKEN",
        "CI_JOB_TOKEN",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "CURL_CA_BUNDLE",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
)
ENDPOINT = re.compile(r"[a-z0-9][A-Za-z0-9_./%~-]{0,1023}")
HTTP_STATUS = re.compile(rb"(?i)\bHTTP(?: status)?[ :]+([45][0-9][0-9])\b")
MR_PROCESS_QUERY = """
query($fullPath: ID!, $iid: String!) {
  project(fullPath: $fullPath) {
    fullPath
    mergeRequest(iid: $iid) {
      iid
      diffStatsSummary { additions deletions fileCount }
      commitCount
      commitsWithoutMergeCommits(first: 100) {
        pageInfo { hasNextPage }
        nodes { author { username } authoredDate committedDate }
      }
    }
  }
}
"""


class CollectionError(TelemetryError):
    """Represent a closed collection diagnostic without provider content."""


class RequestError(CollectionError):
    """Represent a failed request with an optional verified status code."""

    def __init__(self, status: int | None) -> None:
        """Keep only a closed numeric HTTP failure classification."""

        self.status = status
        super().__init__(
            f"GitLab API request failed (HTTP {status})."
            if status
            else "GitLab API request failed."
        )


class ResponseError(CollectionError):
    """Represent a malformed or ambiguous JSON response without retaining its contents."""


class RequestTimeout(CollectionError):
    """Represent an expired deadline for one GitLab API request."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous objects before any provider identities are consumed."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    """Reject non-JSON floating-point extensions."""

    raise ValueError("invalid JSON constant")


def _decode(payload: bytes, *, pages: bool) -> Any:
    """Decode one JSON object or the concatenated lists from glab pagination."""

    try:
        source = payload.decode("utf-8")
        decoder = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_reject_constant)
        if not pages:
            return decoder.decode(source)
        result: list[dict[str, Any]] = []
        cursor = page_count = 0
        while cursor < len(source):
            while cursor < len(source) and source[cursor] in " \t\r\n":
                cursor += 1
            if cursor == len(source):
                break
            page, cursor = decoder.raw_decode(source, cursor)
            page_count += 1
            if (
                not isinstance(page, list)
                or len(result) + len(page) > MAX_ROWS
                or page_count > MAX_ROWS
                or any(not isinstance(row, dict) for row in page)
            ):
                raise ValueError("invalid page")
            result.extend(page)
        if not page_count:
            raise ValueError("no pages")
    except (ValueError, RecursionError):
        raise ResponseError("GitLab returned an invalid or oversized JSON response.") from None
    return result


def _active_instance(user: Any) -> tuple[str, str]:
    """Derive the API instance and web prefix from its authenticated profile response."""

    if not isinstance(user, dict) or type(user.get("id")) is not int or user["id"] <= 0:
        raise CollectionError("GitLab did not return an authenticated profile.")
    username, location = user.get("username"), web_location(user.get("web_url"))
    if (
        not isinstance(username, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", username) is None
        or location is None
    ):
        raise CollectionError("Cannot bind the active glab context to a GitLab host.")
    host, path = location
    prefix, _, profile = path.rpartition("/")
    if profile != username or INSTANCE_PATH.fullmatch(prefix) is None:
        raise CollectionError("Cannot bind the active glab context to a GitLab host.")
    return host, prefix


def _execute(
    command: list[str], environment: dict[str, str], cwd: Path, *, timeout: float
) -> bytes:
    """Stream the subprocess result within byte and time bounds and reap it."""

    deadline = time.monotonic() + timeout
    output, diagnostic = bytearray(), bytearray()
    try:
        with subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as process:
            assert process.stdout is not None and process.stderr is not None
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ, (output, MAX_BYTES))
                    selector.register(
                        process.stderr, selectors.EVENT_READ, (diagnostic, MAX_DIAGNOSTIC_BYTES)
                    )
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise RequestTimeout("GitLab API request timed out.")
                        for key, _events in selector.select(remaining):
                            data = os.read(key.fd, 65_536)
                            if not data:
                                selector.unregister(key.fileobj)
                                continue
                            buffer, maximum = key.data
                            if len(buffer) + len(data) > maximum:
                                raise CollectionError(
                                    "GitLab API response exceeded its byte limit."
                                )
                            buffer.extend(data)
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
            if process.returncode != 0:
                match = HTTP_STATUS.search(diagnostic)
                raise RequestError(int(match[1]) if match is not None else None)
    except subprocess.TimeoutExpired:
        raise RequestTimeout("GitLab API request timed out.") from None
    except OSError:
        raise CollectionError("Cannot execute the authenticated glab command.") from None
    return bytes(output)


class GitLabClient:
    """Use the same local glab context for every read."""

    def __init__(self) -> None:
        """Resolve glab locally and record the instance reported by its active context."""

        executable = shutil.which("glab")
        if executable is None:
            raise CollectionError("The authenticated glab command is required.")
        self.executable = str(Path(executable).absolute())
        self.cwd = Path.cwd()
        self.environment = {
            name: value for name, value in os.environ.items() if name in GLAB_ENVIRONMENT
        }
        self.environment["GLAB_NO_PROMPT"] = "1"
        self.environment["GLAB_SEND_TELEMETRY"] = "false"
        self.calls = 0
        # The profile is display evidence. It must never select a destination
        # for the credentials delegated to glab.
        self.host, self.base_path = _active_instance(self.get("user"))
        for key in ("GITLAB_HOST", "GITLAB_URI", "GL_HOST", "GITLAB_URL"):
            if configured := self.environment.get(key):
                location = web_location(
                    configured if "://" in configured else f"https://{configured}"
                )
                if location is None or location[0] != self.host:
                    raise CollectionError(
                        "The active GitLab profile does not match the configured glab host."
                    )
                break

    def web_url(self, candidate: object, relative: str) -> str:
        """Admit a provider link for the exact bound path, or construct its missing value."""

        full_path = f"{self.base_path}/{relative}"
        if candidate is None or candidate == "":
            return f"https://{self.host}{full_path}"
        if not isinstance(candidate, str) or web_location(candidate) != (self.host, full_path):
            raise CollectionError("GitLab returned a link outside the verified observation scope.")
        return candidate

    def get(
        self,
        endpoint: str,
        *,
        query: dict[str, str] | None = None,
        pages: bool = False,
    ) -> Any:
        """Read a fixed relative REST resource using GET and no command interpolation."""

        if ENDPOINT.fullmatch(endpoint) is None or ".." in endpoint.split("/"):
            raise CollectionError("Invalid GitLab API resource.")
        command = [self.executable, "api", "--method", "GET"]
        if pages:
            command.append("--paginate")
        command.append(f"{endpoint}?{urlencode(query)}" if query else endpoint)
        return self._request(command, pages=pages)

    def process_graphql(self, path: str, iid: int) -> Any:
        """Run the fixed query using literal variables on the active GitLab host."""

        command = [
            self.executable,
            "api",
            "--method",
            "POST",
            "graphql",
            "--raw-field",
            f"query={MR_PROCESS_QUERY}",
            "--raw-field",
            f"fullPath={path}",
            "--raw-field",
            f"iid={iid}",
        ]
        return self._request(command, pages=False)

    def _request(self, command: list[str], *, pages: bool) -> Any:
        """Apply the shared request and retry budget to one fixed API operation."""

        for attempt in range(2):
            self.calls += 1
            if self.calls > MAX_CALLS:
                raise CollectionError("The GitLab API request limit was exceeded.")
            try:
                return _decode(
                    _execute(command, self.environment, self.cwd, timeout=REQUEST_SECONDS),
                    pages=pages,
                )
            except RequestError as exc:
                if attempt or exc.status not in {429, 500, 502, 503, 504}:
                    raise
                time.sleep(1)
        raise AssertionError("unreachable GitLab retry state")

    def pages(self, endpoint: str, *, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """Fetch all pages of an authorized endpoint within the response limits."""

        return self.get(endpoint, query={"per_page": "100", **(query or {})}, pages=True)
