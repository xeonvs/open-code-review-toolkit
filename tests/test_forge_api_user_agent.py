"""Forge request identity crosses real TLS and rejects unsafe operator input."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

import pytest

from ocr_toolkit import preflight
from ocr_toolkit.common.provider_http import (
    DEFAULT_FORGE_API_USER_AGENT,
    resolve_forge_api_user_agent,
)
from ocr_toolkit.posting import gitlab as posting
from ocr_toolkit.posting import workflow
from ocr_toolkit.providers import gitlab as provider
from ocr_toolkit.providers import gitlab_ci, gitlab_discussions
from tests.test_gitlab_provider import SOURCE_SHA, _environment, _GitLabHandler, _https_gitlab


@pytest.mark.parametrize(
    "value",
    ("", " \t", "line\nfeed", "line\rfeed", "nul\x00", "del\x7f", "café", "x" * 257),
)
def test_invalid_forge_user_agent_is_rejected_without_echo(value: str) -> None:
    with pytest.raises(ValueError, match="OCR_FORGE_API_USER_AGENT") as error:
        resolve_forge_api_user_agent({"OCR_FORGE_API_USER_AGENT": value})
    assert value not in str(error.value) if value else True


def test_forge_user_agent_default_and_exact_boundary() -> None:
    assert resolve_forge_api_user_agent({}) == DEFAULT_FORGE_API_USER_AGENT
    assert resolve_forge_api_user_agent({"OCR_FORGE_API_USER_AGENT": "x" * 256}) == "x" * 256


def test_snapshot_uses_injected_override_for_every_request(tmp_path, monkeypatch) -> None:
    seen: list[str | None] = []
    original = _GitLabHandler.do_GET

    def capture(peer: BaseHTTPRequestHandler) -> None:
        seen.append(peer.headers.get("User-Agent"))
        original(peer)

    monkeypatch.setattr(_GitLabHandler, "do_GET", capture)
    monkeypatch.setenv("OCR_FORGE_API_USER_AGENT", "wrong-global-agent/1")
    with _https_gitlab(tmp_path) as root:
        environment = _environment(root)
        environment["OCR_FORGE_API_USER_AGENT"] = "injected-agent/2"
        provider.acquire_review_snapshot(environment, expected_head=SOURCE_SHA)
    assert len(seen) >= 3
    assert set(seen) == {"injected-agent/2"}


def test_user_403_remains_publication_blocking_over_tls(tmp_path, monkeypatch) -> None:
    seen: list[tuple[str, str]] = []

    def reject(peer: BaseHTTPRequestHandler) -> None:
        seen.append((peer.command, peer.path))
        peer.send_error(403, "code 1010")

    monkeypatch.setattr(_GitLabHandler, "do_GET", reject)
    monkeypatch.setattr(_GitLabHandler, "do_POST", reject, raising=False)
    with _https_gitlab(tmp_path) as root:
        monkeypatch.setenv("CI_SERVER_URL", root.removesuffix("/api/v4"))
        monkeypatch.setenv("CI_PROJECT_ID", "7")
        monkeypatch.setenv("CI_MERGE_REQUEST_IID", "9")
        monkeypatch.setenv("GITLAB_API_TOKEN", "synthetic-token")
        config = posting.load_gitlab_config()
        assert config is not None and config.current_user_id is None
        assert workflow.post_results(config, {"comments": []}) == 1
    assert seen == [("GET", "/api/v4/user")]


@pytest.mark.parametrize("override", (None, "synthetic-forge-agent/2"))
def test_all_forge_callers_send_same_serialized_agent_over_tls(
    tmp_path, monkeypatch, override: str | None
) -> None:
    seen: list[tuple[str, str | None]] = []

    def respond(peer: BaseHTTPRequestHandler) -> None:
        agent = peer.headers.get("User-Agent")
        seen.append((peer.command, agent))
        if agent is None or agent.startswith("Python-urllib/"):
            peer.send_error(403, "code 1010")
            return
        body = b"[]" if "pipelines" in peer.path or "discussions" in peer.path else b"{}"
        peer.send_response(200)
        peer.send_header("Content-Type", "application/json")
        peer.send_header("Content-Length", str(len(body)))
        peer.end_headers()
        peer.wfile.write(body)

    monkeypatch.setattr(_GitLabHandler, "do_GET", respond)
    monkeypatch.setattr(_GitLabHandler, "do_POST", respond, raising=False)
    monkeypatch.setattr(_GitLabHandler, "do_PUT", respond, raising=False)
    monkeypatch.setattr(_GitLabHandler, "do_DELETE", respond, raising=False)
    with _https_gitlab(tmp_path) as root:
        monkeypatch.setattr(
            preflight,
            "URL_OPENER",
            urllib.request.build_opener(preflight._NoRedirectHandler),
        )
        url = f"{root}/user"
        with pytest.raises(urllib.error.HTTPError) as rejected:
            urllib.request.build_opener().open(url, timeout=5)
        assert rejected.value.code == 403

        environment = {} if override is None else {"OCR_FORGE_API_USER_AGENT": override}
        agent = resolve_forge_api_user_agent(environment)
        provider._read_json(url, "synthetic-token", deadline=time.monotonic() + 5, user_agent=agent)
        gitlab_discussions._read_page(
            url, "synthetic-token", deadline=time.monotonic() + 5, user_agent=agent
        )
        gitlab_ci._read_page(
            url, "synthetic-token", deadline=time.monotonic() + 5, user_agent=agent
        )
        preflight._request_json(url, {"PRIVATE-TOKEN": "synthetic-token", "User-Agent": agent})
        assert (
            posting.api_request_url(url, "synthetic-token", "PRIVATE-TOKEN", user_agent=agent) == {}
        )
        assert posting.api_write_url_detailed(
            url, "synthetic-token", "PRIVATE-TOKEN", {"body": "synthetic"}, user_agent=agent
        ).posted
        for method in ("PUT", "DELETE"):
            assert (
                posting.api_request_url(
                    url, "synthetic-token", "PRIVATE-TOKEN", method=method, user_agent=agent
                )
                == {}
            )

    assert seen[0][0] == "GET" and seen[0][1] is not None
    assert seen[0][1].startswith("Python-urllib/")
    assert seen[1:] == [("GET", agent)] * 5 + [("POST", agent), ("PUT", agent), ("DELETE", agent)]


def test_loaded_posting_config_keeps_its_operator_agent_for_all_operations(tmp_path, monkeypatch):
    seen = []

    def respond(peer):
        seen.append((peer.command, peer.headers.get("User-Agent")))
        body = b'{"id":7,"username":"synthetic-bot"}' if peer.path.endswith("/user") else b"{}"
        peer.send_response(200)
        peer.send_header("Content-Length", str(len(body)))
        peer.end_headers()
        peer.wfile.write(body)

    for method in ("GET", "POST", "PUT", "DELETE"):
        monkeypatch.setattr(_GitLabHandler, "do_" + method, respond, raising=False)
    with _https_gitlab(tmp_path) as root:
        monkeypatch.setenv("CI_SERVER_URL", root.removesuffix("/api/v4"))
        monkeypatch.setenv("CI_PROJECT_ID", "7")
        monkeypatch.setenv("CI_MERGE_REQUEST_IID", "9")
        monkeypatch.setenv("GITLAB_API_TOKEN", "synthetic-token")
        monkeypatch.setenv("OCR_FORGE_API_USER_AGENT", "configured-agent/2")
        config = posting.load_gitlab_config()
        assert config is not None and config.current_user_id == 7
        monkeypatch.setenv("OCR_FORGE_API_USER_AGENT", "unrelated-later-value/3")
        assert posting.api_request(config, "notes/1", method="DELETE") == {}
        assert posting.update_plain_note(config, 1, "synthetic note").posted
        assert posting.approve_merge_request(config, SOURCE_SHA).posted
    assert seen == [(method, "configured-agent/2") for method in ("GET", "DELETE", "PUT", "POST")]


@pytest.mark.parametrize("module", (provider, gitlab_discussions, gitlab_ci))
def test_invalid_mapping_stops_before_forge_request(module, monkeypatch) -> None:
    monkeypatch.setenv("OCR_FORGE_API_USER_AGENT", "global-agent/1")

    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid injected environment must stop before the request")

    monkeypatch.setattr(module.urllib.request, "build_opener", forbidden)
    environment = {
        "GITLAB_API_TOKEN": "synthetic-token",
        "CI_API_V4_URL": "https://example.invalid/api/v4",
        "CI_PROJECT_ID": "7",
        "CI_MERGE_REQUEST_IID": "9",
        "CI_PIPELINE_ID": "1",
        "OCR_FORGE_API_USER_AGENT": "bad\nagent",
    }
    if module is provider:
        with pytest.raises(provider.GitLabProviderError, match="OCR_FORGE_API_USER_AGENT"):
            provider.acquire_review_snapshot(environment, expected_head="a" * 40)
    elif module is gitlab_discussions:
        with pytest.raises(provider.GitLabProviderError, match="OCR_FORGE_API_USER_AGENT"):
            gitlab_discussions._read_raw_snapshot(
                environment,
                project_id="7",
                merge_request_iid="9",
                max_threads=1,
                deadline=time.monotonic() + 5,
            )
    else:
        with pytest.raises(provider.GitLabProviderError, match="OCR_FORGE_API_USER_AGENT"):
            gitlab_ci._raw_snapshot(
                environment,
                project_id="7",
                source_sha="a" * 40,
                policy=None,
                now=0,
                deadline=time.monotonic() + 5,
            )


def test_invalid_agent_blocks_preflight_and_posting_before_user_lookup(monkeypatch) -> None:
    monkeypatch.setenv("OCR_FORGE_API_USER_AGENT", "bad\nagent")
    monkeypatch.setenv("GITLAB_API_TOKEN", "synthetic-token")
    monkeypatch.setenv("CI_PROJECT_ID", "7")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "9")
    monkeypatch.setenv("CI_SERVER_URL", "https://example.invalid")

    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid agent must stop before /user")

    monkeypatch.setattr(preflight, "_request_json", forbidden)
    monkeypatch.setattr(posting, "fetch_posting_identity", forbidden)
    with pytest.raises(preflight.PreflightError, match="OCR_FORGE_API_USER_AGENT"):
        preflight.validate_gitlab_access()
    assert posting.load_gitlab_config() is None


@pytest.mark.parametrize("write", (False, True))
def test_posting_helpers_reject_invalid_explicit_agent_before_transport(monkeypatch, write) -> None:
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid explicit agent must stop before transport")

    monkeypatch.setattr(posting, "_open_gitlab_request", forbidden)
    if write:
        with pytest.raises(ValueError, match="OCR_FORGE_API_USER_AGENT"):
            posting.api_write_url_detailed(
                "https://example.invalid/user",
                "synthetic-token",
                "PRIVATE-TOKEN",
                {"body": "synthetic"},
                user_agent="bad\ragent",
            )
    else:
        with pytest.raises(ValueError, match="OCR_FORGE_API_USER_AGENT"):
            posting.api_request_url(
                "https://example.invalid/user",
                "synthetic-token",
                "PRIVATE-TOKEN",
                user_agent="bad\ragent",
            )
