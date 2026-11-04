"""Http boundary failures preserve bounded delivery and prior reviewer state."""

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ocr_toolkit.posting import gitlab
from tests.support import gitlab_config


@contextmanager
def peer(status, payload, headers=None, *, disconnect=False):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            requests.append(self.command)
            if disconnect:
                self.close_connection = True
                return
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)

        do_GET = handle_request
        do_POST = handle_request

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api", requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        assert not thread.is_alive()


@pytest.mark.parametrize(
    "status,headers,attempts,sleeps",
    [
        (404, {}, 1, []),
        (429, {}, 3, [1, 2]),
        (503, {"Retry-After": "malformed"}, 3, [1, 2]),
        (503, {"Retry-After": "120"}, 3, [60, 60]),
    ],
)
def test_terminal_http_errors_have_bounded_retries_and_redacted_diagnostics(
    monkeypatch, capsys, status, headers, attempts, sleeps
):
    observed_sleeps = []
    monkeypatch.setattr(gitlab.time, "sleep", observed_sleeps.append)
    with peer(status, b'api_key="synthetic-sensitive-material"', headers) as (url, requests):
        assert gitlab.api_request_url(url, "synthetic-auth", "PRIVATE-TOKEN") is None
    assert requests == ["GET"] * attempts
    assert observed_sleeps == sleeps
    assert "synthetic-sensitive-material" not in capsys.readouterr().err


@pytest.mark.parametrize("method,attempts,sleeps", [("GET", 3, [1, 2]), ("POST", 1, [])])
def test_connection_lost_before_response_retries_reads_only(monkeypatch, method, attempts, sleeps):
    observed_sleeps = []
    monkeypatch.setattr(gitlab.time, "sleep", observed_sleeps.append)
    with peer(200, b"", disconnect=True) as (url, requests):
        assert gitlab.api_request_url(url, "synthetic-auth", "PRIVATE-TOKEN", method=method) is None
    assert requests == [method] * attempts and observed_sleeps == sleeps


@pytest.mark.parametrize("payload,limit", [(b"{malformed", 100), (b'{"too-long":true}', 8)])
def test_invalid_or_oversized_success_response_does_not_return_partial_json(
    monkeypatch, payload, limit
):
    monkeypatch.setattr(gitlab, "MAX_API_RESPONSE_BODY_BYTES", limit)
    with peer(200, payload) as (url, requests):
        assert gitlab.api_request_url(url, "synthetic-auth", "PRIVATE-TOKEN") is None
    assert requests == ["GET"]


@pytest.mark.parametrize("bad_page", [None, {}, "bad", [1]])
def test_pagination_cannot_turn_unknown_or_remaining_sentinel_into_complete_snapshot(
    monkeypatch, bad_page
):
    pages = iter(([{"id": 1}], [{"id": 2}], bad_page))
    calls = []

    def request(config, endpoint, method):
        calls.append(endpoint)
        return next(pages)

    monkeypatch.setattr(gitlab, "api_request", request)
    assert (
        gitlab.api_get_paginated(gitlab_config(), "/notes?sort=desc", per_page=1, max_pages=2)
        is None
    )
    assert calls == [f"/notes?sort=desc&per_page=1&page={p}" for p in (1, 2, 3)]


@pytest.mark.parametrize("page", [None, {}, "bad"])
def test_unavailable_early_page_discards_partial_snapshot(monkeypatch, page):
    pages = iter(([1], page))
    monkeypatch.setattr(gitlab, "api_request", lambda *args, **kwargs: next(pages))
    assert gitlab.api_get_paginated(gitlab_config(), "/notes", per_page=1, max_pages=3) is None
