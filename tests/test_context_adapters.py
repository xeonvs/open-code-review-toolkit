"""Real subprocess/TLS adapter protocol and broker authorization tests."""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.context.adapters import (
    AdapterConfig,
    AdapterRequest,
    AdapterResponse,
    ContextAdapterError,
    authorize_and_resolve,
    configured_secret_values,
    parse_adapter_config,
)
from ocr_toolkit.context.broker import BrokerResult, CandidateSelection, acquire_external_records
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.context.recognizers import ReferenceCandidate
from tests.test_context_policy import encoded_policy, policy_value

PEER = Path(__file__).with_name("context_adapter_peer.py")
RUN_ID = "synthetic_run_0001"


def stdio_config() -> AdapterConfig:
    raw = json.dumps(
        [
            {
                "name": "tracker",
                "type": "stdio",
                "tenants": ["engineering"],
                "resource_classes": ["issue"],
                "command": sys.executable,
                "args": ["-I", str(PEER)],
                "env_from": ["SYNTHETIC_ADAPTER_MODE"],
            }
        ]
    )
    return parse_adapter_config(raw)[0]


def request(*, deadline_ms: int = 1000) -> AdapterRequest:
    return AdapterRequest(
        request_id="synthetic_request_0001",
        run_id=RUN_ID,
        adapter="tracker",
        tenant="engineering",
        resource_class="issue",
        candidate="DEMO-7",
        requested_fields=("descriptor", "digest", "expiry", "state", "text", "version"),
        max_chars=4000,
        max_bytes=8000,
        max_lines=100,
        max_age_seconds=31_536_000,
        deadline_ms=deadline_ms,
    )


@pytest.mark.parametrize(
    "mode",
    ["mismatch", "version", "schema", "partial", "multiple", "oversize", "stderr"],
)
def test_real_stdio_adapter_rejects_hostile_frames(mode: str) -> None:
    with pytest.raises(ContextAdapterError):
        authorize_and_resolve(
            stdio_config(),
            request(),
            environment={"SYNTHETIC_ADAPTER_MODE": mode},
        )


def test_real_stdio_adapter_isolated_process_and_uniform_unavailable() -> None:
    admitted = authorize_and_resolve(
        stdio_config(), request(), environment={"SYNTHETIC_ADAPTER_MODE": "valid"}
    )
    unavailable = authorize_and_resolve(
        stdio_config(), request(), environment={"SYNTHETIC_ADAPTER_MODE": "unavailable"}
    )

    assert admitted.status == "admitted"
    assert admitted.canonical_object == "tenant-object-7"
    assert unavailable.status == "unavailable"
    assert unavailable.record is None


def test_real_stdio_adapter_timeout_terminates_child() -> None:
    with pytest.raises(ContextAdapterError, match="timed out"):
        authorize_and_resolve(
            stdio_config(),
            request(deadline_ms=100),
            environment={"SYNTHETIC_ADAPTER_MODE": "timeout"},
        )


def test_real_stdio_adapter_deadline_covers_request_delivery() -> None:
    blocked_request = replace(request(deadline_ms=100), candidate="x" * 30_000)
    with pytest.raises(ContextAdapterError, match="timed out"):
        authorize_and_resolve(
            stdio_config(),
            blocked_request,
            environment={"SYNTHETIC_ADAPTER_MODE": "no_read"},
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenants", ["engineering", 7]),
        ("tenants", ["engineering", {}]),
        ("resource_classes", ["issue", []]),
        ("env_from", ["SYNTHETIC_ADAPTER_MODE", 7]),
        ("env_from", ["SYNTHETIC_ADAPTER_MODE", {}]),
    ],
)
def test_adapter_config_rejects_mixed_and_unhashable_list_items(
    field: str, value: list[object]
) -> None:
    config: dict[str, object] = {
        "name": "tracker",
        "type": "stdio",
        "tenants": ["engineering"],
        "resource_classes": ["issue"],
        "command": sys.executable,
        "args": [],
        "env_from": [],
    }
    config[field] = value
    with pytest.raises(ContextAdapterError):
        parse_adapter_config(json.dumps([config]))


@pytest.mark.parametrize(
    "value",
    [
        [
            {
                "name": "bad",
                "type": "stdio",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "command": "relative",
                "args": [],
                "env_from": [],
            }
        ],
        [
            {
                "name": "bad",
                "type": "remote",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "url": "http://example.invalid",
                "headers_from": {},
            }
        ],
        [
            {
                "name": "bad",
                "type": "remote",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "url": "https://example.invalid/context?access_token=synthetic-secret-value",
                "headers_from": {},
            }
        ],
        [
            {
                "name": "bad",
                "type": "remote",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "url": "https://example.invalid/context",
                "headers_from": {"Authorization": "TOKEN_A", "authorization": "TOKEN_B"},
            }
        ],
        [
            {
                "name": "bad",
                "type": "remote",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "url": "https://secret@example.invalid/context",
                "headers_from": {},
            }
        ],
        [
            {
                "name": "bad",
                "type": "stdio",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "command": sys.executable,
                "args": [],
                "env_from": [],
                "setup": "unsafe",
            }
        ],
        [
            {
                "name": "bad",
                "type": "stdio",
                "tenants": ["x"],
                "resource_classes": ["issue"],
                "command": sys.executable,
                "args": ["--token=synthetic-secret-value"],
                "env_from": [],
            }
        ],
    ],
)
def test_adapter_config_rejects_shell_plaintext_and_non_https(value: object) -> None:
    with pytest.raises(ContextAdapterError):
        parse_adapter_config(json.dumps(value))


class RemoteHandler(BaseHTTPRequestHandler):
    mode = "valid"
    requests: list[tuple[str, str | None]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        request_value = json.loads(self.rfile.read(length))
        type(self).requests.append((self.path, self.headers.get("X-Synthetic-Token")))
        if self.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "/redirected")
            self.end_headers()
            return
        payload = {
            "schema_version": "ocr.context-adapter-response/v1",
            "request_id": request_value["request_id"],
            "run_id": request_value["run_id"],
            "status": "admitted",
            "canonical_object": "tenant-object-7",
            "version": "version-1",
            "expiry": 200,
            "record": {
                "descriptor": "issue",
                "digest": "a" * 64,
                "expiry": 200,
                "state": "open",
                "text": "Synthetic issue context.",
                "version": "version-1",
            },
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header(
            "Content-Type", "text/plain" if self.mode == "content_type" else "application/json"
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: Any) -> None:
        return


@contextmanager
def tls_peer(tmp_path: Path, *, mode: str = "valid") -> Iterator[str]:
    tmp_path.mkdir(mode=0o700, parents=True)
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
    server = ThreadingHTTPServer(("127.0.0.1", 0), RemoteHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    RemoteHandler.mode = mode
    RemoteHandler.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    previous = os.environ.get("SSL_CERT_FILE")
    os.environ["SSL_CERT_FILE"] = str(cert)
    try:
        yield f"https://localhost:{server.server_port}/context"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        if previous is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = previous


def remote_config(url: str) -> AdapterConfig:
    return parse_adapter_config(
        json.dumps(
            [
                {
                    "name": "tracker",
                    "type": "remote",
                    "tenants": ["engineering"],
                    "resource_classes": ["issue"],
                    "url": url,
                    "headers_from": {"X-Synthetic-Token": "SYNTHETIC_REMOTE_TOKEN"},
                }
            ]
        )
    )[0]


def test_real_https_adapter_verifies_tls_headers_content_type_and_redirects(tmp_path: Path) -> None:
    with tls_peer(tmp_path / "valid") as url:
        response = authorize_and_resolve(
            remote_config(url),
            request(),
            environment={"SYNTHETIC_REMOTE_TOKEN": "synthetic-value"},
        )
    assert response.status == "admitted"
    assert RemoteHandler.requests == [("/context", "synthetic-value")]

    with tls_peer(tmp_path / "redirect", mode="redirect") as url:
        with pytest.raises(ContextAdapterError, match="unavailable status"):
            authorize_and_resolve(
                remote_config(url),
                request(),
                environment={"SYNTHETIC_REMOTE_TOKEN": "synthetic-value"},
            )

    with tls_peer(tmp_path / "content", mode="content_type") as url:
        with pytest.raises(ContextAdapterError, match="content type"):
            authorize_and_resolve(
                remote_config(url),
                request(),
                environment={"SYNTHETIC_REMOTE_TOKEN": "synthetic-value"},
            )


def test_broker_enforces_operator_tenant_dlp_and_required_degradation() -> None:
    policy = parse_policy(encoded_policy())
    reference = policy.references[0]
    selection = CandidateSelection(
        policy=reference,
        candidate=ReferenceCandidate("issue", "DEMO-7", "issue_key"),
    )
    configs = [stdio_config()]

    admitted = acquire_external_records(
        policy=policy,
        adapters=configs,
        selections=[selection],
        run_id=RUN_ID,
        now=100,
        environment={"SYNTHETIC_ADAPTER_MODE": "valid"},
    )
    assert len(admitted.records) == 1
    assert admitted.records[0].projections["model"]["text"] == "Synthetic issue context."
    assert admitted.required_degraded is False

    pii = acquire_external_records(
        policy=policy,
        adapters=configs,
        selections=[selection],
        run_id=RUN_ID,
        now=100,
        environment={"SYNTHETIC_ADAPTER_MODE": "pii"},
    )
    assert pii.records == ()
    assert pii.required_degraded is True
    assert pii.degradation_counts["invalid"] == 1

    wrong_tenant = acquire_external_records(
        policy=policy,
        adapters=[
            parse_adapter_config(
                json.dumps(
                    [
                        {
                            "name": "tracker",
                            "type": "stdio",
                            "tenants": ["foreign"],
                            "resource_classes": ["issue"],
                            "command": sys.executable,
                            "args": ["-I", str(PEER)],
                            "env_from": [],
                        }
                    ]
                )
            )[0]
        ],
        selections=[selection],
        run_id=RUN_ID,
        now=100,
        environment={},
    )
    assert wrong_tenant.records == ()
    assert wrong_tenant.completeness == {"reference:tracker:engineering:issue": "unavailable"}


def test_broker_blocks_exact_neutrally_named_adapter_secret() -> None:
    policy = parse_policy(encoded_policy())
    reference = policy.references[0]
    config = stdio_config()
    environment = {"SYNTHETIC_ADAPTER_MODE": "valid"}
    secrets = configured_secret_values((config,), environment)

    def invoke(
        _config: AdapterConfig,
        adapter_request: AdapterRequest,
        *,
        environment: object,
    ) -> AdapterResponse:
        del environment
        return AdapterResponse(
            status="admitted",
            canonical_object="tenant-object-secret",
            version="version-1",
            expiry=200,
            record={
                "descriptor": "issue",
                "digest": "a" * 64,
                "expiry": 200,
                "state": "open",
                "text": f"adapter returned {secrets[0]}",
                "version": "version-1",
            },
        )

    result = acquire_external_records(
        policy=policy,
        adapters=[config],
        selections=[
            CandidateSelection(
                policy=reference,
                candidate=ReferenceCandidate("issue", "DEMO-7", "issue_key"),
            )
        ],
        run_id=RUN_ID,
        now=100,
        environment=environment,
        forbidden=secrets,
        invoke=invoke,
    )

    assert secrets == ("valid",)
    assert result.records == ()
    assert result.degradation_counts["invalid"] == 1


def test_optional_adapter_degradation_never_claims_required_failure() -> None:
    value = policy_value()
    value["references"][0]["required"] = False
    policy = parse_policy(encoded_policy(value))
    reference = policy.references[0]
    result = acquire_external_records(
        policy=policy,
        adapters=[stdio_config()],
        selections=[
            CandidateSelection(
                policy=reference,
                candidate=ReferenceCandidate("issue", "DEMO-7", "issue_key"),
            )
        ],
        run_id=RUN_ID,
        now=100,
        environment={"SYNTHETIC_ADAPTER_MODE": "unavailable"},
    )

    assert result.records == ()
    assert result.required_degraded is False
    assert result.completeness == {"reference:tracker:engineering:issue": "unavailable"}


def test_broker_record_budget_counts_admissions_not_failed_requests() -> None:
    value = policy_value()
    value["budgets"]["max_records"] = 1  # type: ignore[index]
    policy = parse_policy(encoded_policy(value))
    reference = policy.references[0]

    def invoke(
        _config: AdapterConfig,
        adapter_request: AdapterRequest,
        *,
        environment: object,
    ) -> AdapterResponse:
        del environment
        if adapter_request.candidate == "DEMO-7":
            return AdapterResponse(status="unavailable")
        return AdapterResponse(
            status="admitted",
            canonical_object="tenant-object-8",
            version="version-1",
            expiry=200,
            record={
                "descriptor": "issue",
                "digest": "a" * 64,
                "expiry": 200,
                "state": "open",
                "text": "Later authorized record.",
                "version": "version-1",
            },
        )

    result = acquire_external_records(
        policy=policy,
        adapters=[stdio_config()],
        selections=[
            CandidateSelection(reference, ReferenceCandidate("issue", key, "issue_key"))
            for key in ("DEMO-7", "DEMO-8")
        ],
        run_id=RUN_ID,
        now=100,
        environment={},
        invoke=invoke,
    )

    assert len(result.records) == 1
    assert result.records[0].canonical_object == "tenant-object-8"


def test_broker_has_separate_hard_request_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = parse_policy(encoded_policy())
    reference = policy.references[0]
    calls = 0

    def invoke(
        _config: AdapterConfig,
        _request: AdapterRequest,
        *,
        environment: object,
    ) -> AdapterResponse:
        nonlocal calls
        del environment
        calls += 1
        return AdapterResponse(status="unavailable")

    monkeypatch.setattr("ocr_toolkit.context.broker.MAX_ADAPTER_REQUESTS", 2)
    result = acquire_external_records(
        policy=policy,
        adapters=[stdio_config()],
        selections=[
            CandidateSelection(reference, ReferenceCandidate("issue", key, "issue_key"))
            for key in ("DEMO-7", "DEMO-8", "DEMO-9")
        ],
        run_id=RUN_ID,
        now=100,
        environment={},
        invoke=invoke,
    )

    assert calls == 2
    assert result.degradation_counts == {"unavailable": 2, "invalid": 0, "limit": 1}
    assert result.completeness == {"reference:tracker:engineering:issue": "partial"}


def test_broker_deduplicates_before_budget_and_rejects_changed_duplicate() -> None:
    value = policy_value()
    value["budgets"]["max_chars"] = 30  # type: ignore[index]
    value["budgets"]["max_bytes"] = 60  # type: ignore[index]
    policy = parse_policy(encoded_policy(value))
    reference = policy.references[0]

    def acquire(second_text: str) -> BrokerResult:
        calls = 0

        def invoke(
            _config: AdapterConfig,
            _request: AdapterRequest,
            *,
            environment: object,
        ) -> AdapterResponse:
            nonlocal calls
            del environment
            calls += 1
            text = "Bounded object." if calls == 1 else second_text
            return AdapterResponse(
                status="admitted",
                canonical_object="same-object",
                version="version-1",
                expiry=200,
                record={
                    "descriptor": "issue",
                    "digest": "a" * 64,
                    "expiry": 200,
                    "state": "open",
                    "text": text,
                    "version": "version-1",
                },
            )

        return acquire_external_records(
            policy=policy,
            adapters=[stdio_config()],
            selections=[
                CandidateSelection(reference, ReferenceCandidate("issue", key, "issue_key"))
                for key in ("DEMO-7", "DEMO-8", "DEMO-9")
            ],
            run_id=RUN_ID,
            now=100,
            environment={},
            invoke=invoke,
        )

    duplicate = acquire("Bounded object.")
    assert len(duplicate.records) == 1
    assert duplicate.degradation_counts["limit"] == 0

    changed = acquire("Changed duplicate object text.")
    assert changed.records == ()
    assert changed.degradation_counts["invalid"] == 2
    assert changed.completeness == {"reference:tracker:engineering:issue": "unavailable"}


def test_broker_applies_one_aggregate_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = parse_policy(encoded_policy())
    reference = policy.references[0]
    deadlines: list[int] = []

    def invoke(
        _config: AdapterConfig,
        adapter_request: AdapterRequest,
        *,
        environment: object,
    ) -> AdapterResponse:
        del environment
        deadlines.append(adapter_request.deadline_ms)
        return AdapterResponse(
            status="admitted",
            canonical_object=f"tenant-object-{adapter_request.candidate}",
            version="version-1",
            expiry=200,
            record={
                "descriptor": "issue",
                "digest": "a" * 64,
                "expiry": 200,
                "state": "open",
                "text": "Synthetic issue context.",
                "version": "version-1",
            },
        )

    ticks = iter((100.0, 100.1, 115.0))
    monkeypatch.setattr("ocr_toolkit.context.broker.time.monotonic", lambda: next(ticks))
    result = acquire_external_records(
        policy=policy,
        adapters=[stdio_config()],
        selections=[
            CandidateSelection(
                policy=reference,
                candidate=ReferenceCandidate("issue", "DEMO-7", "issue_key"),
            ),
            CandidateSelection(
                policy=reference,
                candidate=ReferenceCandidate("issue", "DEMO-8", "issue_key"),
            ),
        ],
        run_id=RUN_ID,
        now=100,
        environment={},
        invoke=invoke,
    )

    assert deadlines == [14900]
    assert len(result.records) == 1
    assert result.completeness == {"reference:tracker:engineering:issue": "partial"}
    assert result.degradation_counts["limit"] == 1
    assert result.required_degraded is True


@pytest.mark.parametrize("name", ["wiki_proxy", "mcp_bridge"])
def test_document_and_read_only_mcp_proxies_share_only_the_fixed_protocol(name: str) -> None:
    config = parse_adapter_config(
        json.dumps(
            [
                {
                    "name": name,
                    "type": "stdio",
                    "tenants": ["documentation"],
                    "resource_classes": ["document"],
                    "command": sys.executable,
                    "args": ["-I", str(PEER)],
                    "env_from": ["SYNTHETIC_ADAPTER_MODE"],
                }
            ]
        )
    )[0]
    protocol_request = AdapterRequest(
        request_id="synthetic_request_0002",
        run_id=RUN_ID,
        adapter=name,
        tenant="documentation",
        resource_class="document",
        candidate="[[context:document:guide-7]]",
        requested_fields=("descriptor", "digest", "expiry", "state", "text", "version"),
        max_chars=4000,
        max_bytes=8000,
        max_lines=100,
        max_age_seconds=31_536_000,
        deadline_ms=1000,
    )

    response = authorize_and_resolve(
        config,
        protocol_request,
        environment={"SYNTHETIC_ADAPTER_MODE": "valid"},
    )

    assert response.status == "admitted"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("compiled_true", "effective allow_failure is true"),
        ("compiled_false", "effective allow_failure is false"),
    ],
)
def test_synthetic_compiled_gitlab_fact_uses_the_bounded_document_adapter(
    mode: str, expected: str
) -> None:
    value = policy_value()
    reference_value = value["references"][0]
    assert isinstance(reference_value, dict)
    reference_value.update(
        {
            "adapter": "compiled_ci",
            "tenant": "synthetic",
            "resource_class": "document",
            "recognizer": {"type": "explicit"},
        }
    )
    policy = parse_policy(encoded_policy(value))
    reference = policy.references[0]
    config = parse_adapter_config(
        json.dumps(
            [
                {
                    "name": "compiled_ci",
                    "type": "stdio",
                    "tenants": ["synthetic"],
                    "resource_classes": ["document"],
                    "command": sys.executable,
                    "args": ["-I", str(PEER)],
                    "env_from": ["SYNTHETIC_ADAPTER_MODE"],
                }
            ]
        )
    )[0]

    result = acquire_external_records(
        policy=policy,
        adapters=[config],
        selections=[
            CandidateSelection(
                policy=reference,
                candidate=ReferenceCandidate(
                    "document", "[[context:document:review-job]]", "explicit"
                ),
            )
        ],
        run_id=RUN_ID,
        now=100,
        environment={"SYNTHETIC_ADAPTER_MODE": mode},
    )

    assert result.required_degraded is False
    assert len(result.records) == 1
    assert result.records[0].resource_class == "document"
    text = result.records[0].projections["model"]["text"]
    assert isinstance(text, str) and expected in text
