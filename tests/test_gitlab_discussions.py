"""Real-TLS stable GitLab discussion acquisition and identity projection tests."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.context.broker import ContextOrigin, prepare_discussion_records
from ocr_toolkit.context.contracts import DiscussionPolicy, RemediationThreadPolicy
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.posting.markers import build_marker
from ocr_toolkit.providers.gitlab import GitLabProviderError
from ocr_toolkit.providers.gitlab_context import RawGitLabSnapshot
from ocr_toolkit.providers.gitlab_discussions import (
    _project_discussions,
    acquire_discussions,
    acquire_gitlab_context,
)
from ocr_toolkit.providers.gitlab_identity import GitLabUserIdentity
from ocr_toolkit.providers.gitlab_remediation import project_remediation_threads
from tests.test_context_policy import encoded_policy, policy_value, remediation_policy_value

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
        if self.path == "/api/v4/user":
            identity_cycle = sum(path == "/api/v4/user" for path in type(self).requests)
            username = (
                "changed_bot"
                if self.mode == "identity_mutated" and identity_cycle > 1
                else "OCR_Bot"
            )
            body = json.dumps({"id": 99, "username": username}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not self.path.startswith("/api/v4/projects/7/merge_requests/9/discussions?"):
            self.send_error(404)
            return
        page = "2" if "page=2" in self.path else "1"
        discussion_requests = [path for path in type(self).requests if "/discussions?" in path]
        cycle = (
            (len(discussion_requests) - 1) // 2
            if self.mode == "pagination"
            else len(discussion_requests) - 1
        )
        suffix = " changed" if self.mode == "mutated" and cycle > 0 else ""
        if self.mode in {"remediation", "forged_root"}:
            root_author = {
                "id": 99 if self.mode == "remediation" else 41,
                "state": "active",
                "username": "must-not-survive",
            }
            payload = [
                {
                    "id": "raw-thread-must-not-survive",
                    "notes": [
                        note(
                            1,
                            build_marker("a" * 32)
                            + "\nFinding: validate the command argument before execution.",
                            author=root_author,
                            position={
                                "position_type": "text",
                                "new_path": "src/private.py",
                                "new_line": 8,
                                "head_sha": SOURCE_SHA,
                            },
                        ),
                        note(2, "The branch now validates the argument before execution."),
                        note(3, "@OCR_Bot resolve"),
                    ],
                }
            ]
        elif self.mode == "unknown":
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
        if cycle > 0 and self.mode == "reordered":
            payload[0]["notes"] = list(reversed(payload[0]["notes"]))
        if cycle > 0 and self.mode == "deleted":
            payload[0]["notes"] = payload[0]["notes"][:-1]
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if (
            self.mode == "pagination" or (self.mode == "pagination_drift" and cycle > 0)
        ) and page == "1":
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


def remediation_policy() -> RemediationThreadPolicy:
    parsed = parse_policy(encoded_policy(remediation_policy_value()))
    assert parsed.remediation_threads is not None
    return parsed.remediation_threads


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
    assert len(DiscussionHandler.requests) == 6
    pending = prepare_discussion_records(
        snapshot.records,
        policy=discussion_policy(),
        origin=ContextOrigin(
            source="forge:gitlab_discussions",
            adapter="gitlab",
            tenant="project",
        ),
        expiry=1_777_003_600,
    )
    assert len(pending) == 3
    assert pending[0].mutable is True
    assert pending[0].canonical_object != "thread-1"
    assert pending[0].projections["model"]["text"] == "First synthetic reply"
    assert "must-not-survive" not in repr(pending)


def test_discussions_stop_at_policy_thread_bound_without_fetching_extra_pages(
    tmp_path: Path,
) -> None:
    policy = replace(discussion_policy(), max_threads=1)
    with gitlab_peer(tmp_path, mode="pagination") as api_root:
        snapshot = acquire_discussions(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            policy=policy,
            now=1_787_209_200,
        )

    assert snapshot.state == "partial"
    assert snapshot.omitted == 1
    assert [(record.thread, record.reply) for record in snapshot.records] == [(0, 0), (0, 1)]
    assert len(DiscussionHandler.requests) == 4


@pytest.mark.parametrize("mode", ["mutated", "reordered", "deleted", "pagination_drift"])
def test_discussions_reject_mutated_provider_snapshot(tmp_path: Path, mode: str) -> None:
    with gitlab_peer(tmp_path / mode, mode=mode) as api_root:
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


def test_discussions_degrade_unknown_actor(tmp_path: Path) -> None:
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
    assert snapshot.dlp_rejected == 1


def test_generic_thread_bound_ignores_exclusive_remediation_roots() -> None:
    """Count only non-exclusive discussions against the generic thread bound."""

    raw = RawGitLabSnapshot(
        identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
        threads=(
            {
                "notes": [
                    note(
                        1,
                        build_marker("a" * 32) + "\nFinding reserved for remediation context.",
                        author={"id": 99, "state": "active"},
                    ),
                    note(2, "The branch contains a candidate correction."),
                ]
            },
            {"notes": [note(3, "Independent generic discussion.")]},
        ),
        pagination_omitted=0,
        digest="f" * 64,
    )

    snapshot = _project_discussions(
        raw,
        source_sha=SOURCE_SHA,
        run_id="bounded_run_0001",
        policy=replace(discussion_policy(), max_threads=1),
        now=1_787_209_200,
        forbidden=(),
        excluded_threads=frozenset({0}),
    )

    assert snapshot.state == "complete"
    assert snapshot.omitted == 0
    assert [record.body for record in snapshot.records] == ["Independent generic discussion."]


def test_one_snapshot_builds_exclusive_verified_remediation_bundle(tmp_path: Path) -> None:
    with gitlab_peer(tmp_path, mode="remediation") as api_root:
        snapshot = acquire_gitlab_context(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            discussion_policy=discussion_policy(),
            remediation_policy=remediation_policy(),
            now=1_787_209_200,
        )

    assert snapshot.discussions is not None
    assert snapshot.remediation_threads is not None
    assert snapshot.discussions.records == ()
    assert snapshot.remediation_threads.state == "complete"
    assert len(snapshot.remediation_threads.records) == 1
    record = snapshot.remediation_threads.records[0]
    assert record.root_body == "Finding: validate the command argument before execution."
    assert [reply.body for reply in record.replies] == [
        "The branch now validates the argument before execution."
    ]
    assert record.anchor_state == "current"
    assert record.resolved_count == 0
    serialized = repr(snapshot)
    for forbidden_value in (
        "raw-thread-must-not-survive",
        "must-not-survive",
        "src/private.py",
        "@OCR_Bot resolve",
    ):
        assert forbidden_value not in serialized
    assert len(DiscussionHandler.requests) == 4


def test_remediation_thread_bound_counts_only_verified_roots() -> None:
    """Apply the remediation thread bound after root verification."""

    root = note(
        2,
        build_marker("a" * 32) + "\nFinding: retain the verified remediation bundle.",
        author={"id": 99, "state": "active"},
    )
    raw = RawGitLabSnapshot(
        identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
        threads=(
            {"notes": [note(1, "Ordinary generic discussion.")]},
            {"notes": [root, note(3, "The branch now has the regression test.")]},
        ),
        pagination_omitted=0,
        digest="1" * 64,
    )

    snapshot, verified = project_remediation_threads(
        raw,
        source_sha=SOURCE_SHA,
        run_id="bounded_run_0001",
        policy=replace(remediation_policy(), max_threads=1),
        now=1_787_209_200,
        forbidden=(),
    )

    assert verified == frozenset({1})
    assert snapshot.state == "complete"
    assert snapshot.omitted == 0
    assert len(snapshot.records) == 1


def test_remediation_item_bound_counts_the_unprocessed_reply_tail() -> None:
    """Report every reply omitted after the aggregate item budget is exhausted."""

    root = note(
        1,
        build_marker("a" * 32) + "\nFinding: bound the complete reply tail.",
        author={"id": 99, "state": "active"},
    )
    raw = RawGitLabSnapshot(
        identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
        threads=(
            {
                "notes": [
                    root,
                    note(2, "First admissible reply."),
                    note(3, "Second reply beyond the item bound."),
                    note(4, "Third reply beyond the item bound."),
                ]
            },
        ),
        pagination_omitted=0,
        digest="2" * 64,
    )

    snapshot, _verified = project_remediation_threads(
        raw,
        source_sha=SOURCE_SHA,
        run_id="bounded_run_0001",
        policy=replace(remediation_policy(), max_items=2),
        now=1_787_209_200,
        forbidden=(),
    )

    assert snapshot.state == "partial"
    assert snapshot.omitted == 2
    assert [reply.body for reply in snapshot.records[0].replies] == ["First admissible reply."]


def test_remediation_rejects_forged_root_and_identity_drift(tmp_path: Path) -> None:
    with gitlab_peer(tmp_path / "forged", mode="forged_root") as api_root:
        forged = acquire_gitlab_context(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            discussion_policy=discussion_policy(),
            remediation_policy=remediation_policy(),
            now=1_787_209_200,
        )
    assert forged.remediation_threads is not None
    assert forged.remediation_threads.records == ()
    assert forged.discussions is not None and len(forged.discussions.records) == 3

    with gitlab_peer(tmp_path / "identity", mode="identity_mutated") as api_root:
        mutated = acquire_gitlab_context(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            discussion_policy=discussion_policy(),
            remediation_policy=remediation_policy(),
            now=1_787_209_200,
        )
    assert mutated.discussions is not None and mutated.discussions.state == "mutated"
    assert mutated.remediation_threads is not None
    assert mutated.remediation_threads.state == "mutated"
    assert mutated.remediation_threads.records == ()


def test_remediation_dlp_rejection_retains_no_reply_value(tmp_path: Path) -> None:
    blocked = "The branch now validates the argument before execution."
    with gitlab_peer(tmp_path, mode="remediation") as api_root:
        snapshot = acquire_gitlab_context(
            environment(api_root),
            project_id="7",
            merge_request_iid="9",
            source_sha=SOURCE_SHA,
            run_id="synthetic_run_0001",
            discussion_policy=None,
            remediation_policy=remediation_policy(),
            now=1_787_209_200,
            forbidden=(blocked,),
        )

    assert snapshot.remediation_threads is not None
    assert snapshot.remediation_threads.state == "partial"
    assert snapshot.remediation_threads.records == ()
    assert snapshot.remediation_threads.dlp_rejected == 1
    assert blocked not in repr(snapshot)


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

    def snapshot_once(*_args: object, deadline: float, **_kwargs: object) -> RawGitLabSnapshot:
        deadlines.append(deadline)
        return RawGitLabSnapshot(
            identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
            threads=(),
            pagination_omitted=0,
            digest="a" * 64,
        )

    monkeypatch.setattr(
        "ocr_toolkit.providers.gitlab_discussions._read_raw_snapshot",
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


def test_generic_projection_rejects_hostile_shapes_before_store_admission() -> None:
    """Reject malformed, stale, or sensitive discussion notes before admission."""

    invalid_timestamp = note(4, "Invalid timestamp")
    invalid_timestamp["updated_at"] = "not-a-timestamp"
    future_timestamp = note(5, "Future timestamp")
    future_timestamp["updated_at"] = "2099-01-01T00:00:00Z"
    raw = RawGitLabSnapshot(
        identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
        threads=(
            "not-a-thread",
            {"notes": "not-a-list"},
            {
                "notes": [
                    42,
                    {**note(1, "Unsupported note"), "type": "CommitNote"},
                    {**note(2, "Missing author"), "author": None},
                    invalid_timestamp,
                    future_timestamp,
                    note(6, "Already resolved", resolved=True),
                    note(
                        7,
                        "Outdated anchor",
                        position={
                            "position_type": "text",
                            "new_path": "src/review.py",
                            "new_line": 7,
                            "head_sha": "b" * 40,
                        },
                    ),
                    note(8, "Contact reviewer@example.invalid"),
                    note(9, "blocked-adapter-secret"),
                    note(10, "Safe current discussion"),
                ]
            },
        ),
        pagination_omitted=1,
        digest="d" * 64,
    )

    snapshot = _project_discussions(
        raw,
        source_sha=SOURCE_SHA,
        run_id="bounded_run_0001",
        policy=discussion_policy(),
        now=1_787_209_200,
        forbidden=("blocked-adapter-secret",),
    )

    assert snapshot.state == "partial"
    assert [record.body for record in snapshot.records] == ["Safe current discussion"]
    assert snapshot.dlp_rejected == 2
    assert snapshot.omitted == 12
    serialized = repr(snapshot)
    assert "reviewer@example.invalid" not in serialized
    assert "blocked-adapter-secret" not in serialized


def test_remediation_projection_keeps_only_valid_noncommand_replies() -> None:
    """Admit safe remediation replies while excluding lifecycle commands."""

    invalid_timestamp = note(7, "Invalid timestamp")
    invalid_timestamp["updated_at"] = "not-a-timestamp"
    root = note(
        1,
        build_marker("a" * 32) + "\nFinding: validate the command argument before execution.",
        author={"id": 99, "state": "active", "username": "OCR_Bot"},
    )
    raw = RawGitLabSnapshot(
        identity=GitLabUserIdentity(user_id=99, username="OCR_Bot"),
        threads=(
            {
                "id": "raw-thread-private",
                "notes": [
                    root,
                    42,
                    {**note(2, "Unsupported note"), "type": "CommitNote"},
                    {
                        **note(3, "Unknown actor"),
                        "author": {"id": 41, "state": "unknown"},
                    },
                    note(4, "@OCR_Bot resolve"),
                    note(5, "Contact reviewer@example.invalid"),
                    invalid_timestamp,
                    note(8, "The current code still needs verification."),
                ],
            },
            {
                "notes": [
                    note(
                        9,
                        build_marker("b" * 32) + "\nFinding with only a lifecycle command.",
                        author={"id": 99, "state": "active"},
                    ),
                    note(10, "@OCR_Bot suppress"),
                ]
            },
            {
                "notes": [
                    note(
                        11,
                        build_marker("c" * 32) + "\nForged human root.",
                        author={"id": 41, "state": "active"},
                    ),
                    note(12, "Human reply"),
                ]
            },
        ),
        pagination_omitted=0,
        digest="e" * 64,
    )

    snapshot, verified = project_remediation_threads(
        raw,
        source_sha=SOURCE_SHA,
        run_id="bounded_run_0001",
        policy=remediation_policy(),
        now=1_787_209_200,
        forbidden=(),
    )

    assert verified == frozenset({0, 1})
    assert snapshot.state == "partial"
    assert snapshot.dlp_rejected == 1
    assert len(snapshot.records) == 1
    record = snapshot.records[0]
    assert record.completeness == "partial"
    assert [reply.body for reply in record.replies] == [
        "The current code still needs verification."
    ]
    serialized = repr((snapshot, verified))
    for rejected in (
        "raw-thread-private",
        "reviewer@example.invalid",
        "@OCR_Bot resolve",
        "@OCR_Bot suppress",
        "Forged human root",
    ):
        assert rejected not in serialized
