"""Real TLS acquisition bounds and malformed provider-state branches."""

import ssl
import time
import urllib.error

import pytest

from ocr_toolkit.providers import gitlab_ci
from ocr_toolkit.providers.gitlab import GitLabProviderError
from tests.test_gitlab_provider import _GitLabHandler, _https_gitlab


@pytest.mark.parametrize(
    "mode", ("valid", "duplicate", "utf8", "type", "large", "pagination", "redirect", "http")
)
def test_ci_page_crosses_real_tls_and_enforces_wire_bounds(tmp_path, monkeypatch, mode) -> None:
    requests = []

    def get(peer):
        requests.append((peer.path, peer.headers.get("PRIVATE-TOKEN")))
        body = b'{"value":1}'
        if mode == "duplicate":
            body = b'{"value":1,"value":2}'
        elif mode == "utf8":
            body = b'"\xff"'
        elif mode == "large":
            body = b"x" * (gitlab_ci.MAX_PAGE_BYTES + 1)
        peer.send_response(302 if mode == "redirect" else 503 if mode == "http" else 200)
        peer.send_header("Content-Type", "text/html" if mode == "type" else "application/json")
        peer.send_header("Content-Length", str(len(body)))
        peer.send_header(
            "X-Next-Page", "not-a-page" if mode == "pagination" else "2" if mode == "valid" else ""
        )
        if mode == "redirect":
            peer.send_header("Location", "/must-not-receive-credentials")
        peer.end_headers()
        try:
            peer.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass

    monkeypatch.setattr(_GitLabHandler, "do_GET", get)
    with _https_gitlab(tmp_path) as url:
        if mode == "valid":
            assert gitlab_ci._read_page(url, "synthetic-token", deadline=time.monotonic() + 5) == (
                {"value": 1},
                True,
            )
        else:
            with pytest.raises(GitLabProviderError):
                gitlab_ci._read_page(url, "synthetic-token", deadline=time.monotonic() + 5)
    assert requests == [("/api/v4", "synthetic-token")]


@pytest.mark.parametrize("token", ("", "line\nbreak", "line\rbreak", "x" * 16_385))
def test_malformed_ci_credentials_stop_before_network(monkeypatch, token) -> None:
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid credentials must not create an HTTP opener")

    monkeypatch.setattr(gitlab_ci.urllib.request, "build_opener", forbidden)
    with pytest.raises(GitLabProviderError, match="missing or malformed"):
        gitlab_ci._read_page("https://example.invalid", token, deadline=time.monotonic() + 5)


def test_ci_deadline_stops_before_network_and_network_errors_remain_closed(monkeypatch) -> None:
    with pytest.raises(GitLabProviderError, match="timed out"):
        gitlab_ci._read_page("https://example.invalid", "synthetic-token", deadline=0)

    class Unavailable:
        def open(self, *_args, **_kwargs):
            raise urllib.error.URLError("private provider diagnostic")

    monkeypatch.setattr(gitlab_ci.urllib.request, "build_opener", lambda *_args: Unavailable())
    with pytest.raises(GitLabProviderError, match=r"^GitLab CI outcome request failed$"):
        gitlab_ci._read_page(
            "https://example.invalid", "synthetic-token", deadline=time.monotonic() + 5
        )


@pytest.mark.parametrize("value", (None, True, 0, -1, "1", [], {}))
def test_ci_ids_never_coerce_malformed_provider_values(value) -> None:
    with pytest.raises(GitLabProviderError):
        gitlab_ci._positive_id(value)


@pytest.mark.parametrize("name", (None, "", "x" * 129, "bad\x00name", "bad\x7fname"))
def test_ci_names_reject_empty_oversized_and_control_values(name) -> None:
    with pytest.raises(GitLabProviderError):
        gitlab_ci._bounded_name(name)
