"""Real-TLS stable GitLab discussion acquisition and identity projection tests."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.context.broker import prepare_discussion_records
from ocr_toolkit.context.contracts import DiscussionPolicy
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.providers.gitlab import GitLabProviderError
from ocr_toolkit.providers.gitlab_discussions import DiscussionSnapshot, acquire_discussions
from tests.test_context_policy import encoded_policy, policy_value

SOURCE_SHA = "a" * 40


def note(
    identifier: int,
    body: str,
    *,
    author: dict[str, object] | None = None,
    system: bool = False,
    resolved: bool = False,
    position: object = None,
) -> dict[str, object]:
    return {
        "id": identifier,
        "body": body,
        "author": author
        or {
            "id": 41,
            "state": "active",
            "username": "must-not-survive",
            "name": "Must Not Survive",
            "email": "must-not-survive@example.invalid",
            "avatar_url": "https://private.example.invalid/avatar",
        },
        "system": system,
        "created_at": "2026-08-19T08:00:00Z",
        "updated_at": "2026-08-19T09:00:00Z",
        "resolved": resolved,
        "position": position,
    }


class DiscussionHandler(BaseHTTPRequestHandler):
    mode = "stable"
    requests: list[str] = []

    def do_GET(self) -> None:
        type(self).requests.append(self.path)
        if not self.path.startswith("/api/v4/projects/7/merge_requests/9/discussions?"):
            self.send_error(404)
            return
        page = "2" if "page=2" in self.path else "1"
        cycle = (
            (len(type(self).requests) - 1) // 2
            if self.mode == "pagination"
            else len(type(self).requests) - 1
        )
        suffix = " changed" if self.mode == "mutated" and cycle > 0 else ""
        if self.mode == "unknown":
            payload = [
                {
                    "id": "thread-1",
                    "notes": [
                        note(
                            1,
                            "Unknown actor",
                            author={"id": 41, "state": "mystery", "bot": "unknown"},
                        )
                    ],
                }
            ]
        elif page == "1":
            payload = [
                {
                    "id": "thread-1",
                    "notes": [
                        note(1, "First synthetic reply" + suffix),
                        note(
                            2,
                            "Automation reply",
                            author={"id": 42, "state": "active", "bot": True},
                            position={
                                "position_type": "text",
                                "new_path": "src/example.py",
                                "new_line": 12,
                            },
                        ),
                    ],
                }
            ]
        else:
            payload = [
                {
                    "id": "thread-2",
                    "notes": [note(3, "Second page system note", system=True)],
                }
            ]
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if self.mode == "pagination" and page == "1":
            self.send_header("X-Next-Page", "2")
        else:
            self.send_header("X-Next-Page", "")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: Any) -> None:
        return


@contextmanager
def gitlab_peer(tmp_path: Path, *, mode: str = "stable") -> Iterator[str]:
    tmp_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), DiscussionHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    DiscussionHandler.mode = mode
    DiscussionHandler.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    previous = os.environ.get("SSL_CERT_FILE")
    os.environ["SSL_CERT_FILE"] = str(cert)
    try:
        yield f"https://localhost:{server.server_port}/api/v4"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        if previous is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = previous


def environment(api_root: str) -> dict[str, str]:
    return {
        "CI_API_V4_URL": api_root,
        "CI_PROJECT_ID": "7",
        "CI_MERGE_REQUEST_IID": "9",
        "GITLAB_API_TOKEN": "synthetic-token",
    }


def discussion_policy() -> DiscussionPolicy:
    value = policy_value()
    value["forge_discussions"]["account_classes"] = ["automation", "system", "user"]
    parsed = parse_policy(encoded_policy(value))
    assert parsed.forge_discussions is not None
    return parsed.forge_discussions


def test_discussions_cross_real_tls_twice_preserve_order_and_hide_display_identity(
    tmp_path: Path,
) -> None:
    with gitlab_peer(tmp_path, mode="pagination") as api_root:
        snapshot = acquire_discussions(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            policy=discussion_policy(),
            now=1_787_209_200,
        )

    assert snapshot.state == "complete"
    assert [(record.thread, record.reply) for record in snapshot.records] == [
        (0, 0),
        (0, 1),
        (1, 0),
    ]
    assert [record.author_class for record in snapshot.records] == ["user", "automation", "system"]
    assert snapshot.records[1].anchor == {"path": "src/example.py", "line": 12}
    serialized = repr(snapshot)
    assert "must-not-survive" not in serialized
    assert "private.example.invalid" not in serialized
    assert len({record.author_pseudonym for record in snapshot.records}) == 3
    assert len(DiscussionHandler.requests) == 4
    pending = prepare_discussion_records(
        snapshot.records,
        policy=discussion_policy(),
        expiry=1_777_003_600,
    )
    assert len(pending) == 3
    assert pending[0].mutable is True
    assert pending[0].canonical_object != "thread-1"
    assert pending[0].projections["model"]["text"] == "First synthetic reply"
    assert "must-not-survive" not in repr(pending)


def test_discussions_reject_mutated_pagination_and_unknown_actor(tmp_path: Path) -> None:
    with gitlab_peer(tmp_path / "mutated", mode="mutated") as api_root:
        mutated = acquire_discussions(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            policy=discussion_policy(),
            now=1_787_209_200,
        )
    assert mutated.state == "mutated"
    assert mutated.records == ()

    with gitlab_peer(tmp_path / "unknown", mode="unknown") as api_root:
        unknown = acquire_discussions(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            policy=discussion_policy(),
            now=1_787_209_200,
        )
    assert unknown.state == "partial"
    assert unknown.records == ()
    assert unknown.omitted == 1


def test_discussions_apply_exact_configured_secret_dlp(tmp_path: Path) -> None:
    with gitlab_peer(tmp_path) as api_root:
        snapshot = acquire_discussions(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            policy=discussion_policy(),
            now=1_787_209_200,
            forbidden=("First synthetic reply",),
        )

    assert snapshot.state == "partial"
    assert [record.body for record in snapshot.records] == ["Automation reply"]
    assert snapshot.omitted == 1


def test_discussions_bind_validated_project_mr_and_source_identity(tmp_path: Path) -> None:
    with gitlab_peer(tmp_path) as api_root:
        with pytest.raises(GitLabProviderError, match="identity"):
            acquire_discussions(
                environment(api_root),
                project_id="8",
                merge_request_iid="9",
                source_sha=SOURCE_SHA,
                run_id="synthetic_run_0001",
                policy=discussion_policy(),
                now=1_787_209_200,
            )
        with pytest.raises(GitLabProviderError, match="identity"):
            acquire_discussions(
                environment(api_root),
                project_id="7",
                merge_request_iid="9",
                source_sha="invalid",
                run_id="synthetic_run_0001",
                policy=discussion_policy(),
                now=1_787_209_200,
            )


def test_discussions_reuse_one_caller_owned_deadline_for_both_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deadlines: list[float] = []

    def snapshot_once(*_args: object, deadline: float, **_kwargs: object) -> DiscussionSnapshot:
        deadlines.append(deadline)
        return DiscussionSnapshot(state="complete", records=(), digest="a" * 64, omitted=0)

    monkeypatch.setattr(
        "ocr_toolkit.providers.gitlab_discussions._snapshot_once",
        snapshot_once,
    )
    snapshot = acquire_discussions(
        environment("https://gitlab.example.invalid/api/v4"),
        project_id="7",
        merge_request_iid="9",
        source_sha=SOURCE_SHA,
        run_id="synthetic_run_0001",
        policy=discussion_policy(),
        now=1_787_209_200,
        deadline=123.5,
    )

    assert snapshot.state == "complete"
    assert deadlines == [123.5, 123.5]
