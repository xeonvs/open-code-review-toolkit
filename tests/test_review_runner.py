"""Regression tests for safe local OCR execution diagnostics."""

from __future__ import annotations

import io
import json
import os
import signal
import stat
import subprocess
import sys
from contextlib import redirect_stderr
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.broker import BrokerResult
from ocr_toolkit.context.contracts import RecognizerPolicy
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.context.store import ContextStore
from ocr_toolkit.evidence import EvidenceRecord, EvidenceSnapshot, EvidenceStore, RefRole
from ocr_toolkit.evidence.artifacts import EvidenceArtifacts, repository_artifacts
from ocr_toolkit.evidence.review_context import normalize_merge_request_context
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.posting import approval, settings
from ocr_toolkit.result_contract import parse_result_outcome
from tests.support import patched_attr, patched_env
from tests.test_context_policy import encoded_policy, remediation_policy_value

DEFAULT_IDENTITY = review_runner.ReviewIdentity(
    source_sha="a" * 40,
    policy_sha="b" * 40,
    mr_author_id=None,
    context_mode="off",
    context=None,
)


def enriched_identity() -> review_runner.ReviewIdentity:
    """Return one provider-normalized enriched-review identity."""

    context = normalize_merge_request_context(
        provider="gitlab",
        project_id="7",
        merge_request_iid="9",
        source_sha="a" * 40,
        title="Validate current behavior",
        description="Review the implementation and its tests.",
        labels=["review"],
        source_branch="feature/context",
    )
    return review_runner.ReviewIdentity(
        source_sha="a" * 40,
        policy_sha="b" * 40,
        mr_author_id=41,
        context_mode="enriched",
        context=context,
    )


def configure_enrichment_test(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider_acquire: object,
    external_acquire: object,
) -> EvidenceArtifacts:
    """Install only the composition-edge fakes shared by enrichment tests."""

    policy = parse_policy(encoded_policy(remediation_policy_value()))
    artifacts = repository_artifacts(tmp_path)
    artifacts.directory.mkdir(mode=0o700)
    monkeypatch.setattr(review_runner, "load_protected_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(review_runner, "acquire_gitlab_context", provider_acquire)
    monkeypatch.setattr(review_runner, "acquire_external_records", external_acquire)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)
    return artifacts


def test_default_termination_signal_is_translated_for_cleanup() -> None:
    previous = review_runner._install_termination_handlers()
    try:
        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)
        with pytest.raises(review_runner.ReviewRunnerError, match="interrupted by signal"):
            handler(signal.SIGTERM, None)
    finally:
        review_runner._restore_termination_handlers(previous)


def test_reference_candidate_dedup_preserves_independent_resource_classes() -> None:
    """The same explicit value may select distinct protected issue/document sources."""

    references = tuple(
        SimpleNamespace(
            adapter="knowledge",
            tenant="engineering",
            resource_class=resource_class,
            recognizer=RecognizerPolicy(type="explicit"),
        )
        for resource_class in ("issue", "document")
    )
    policy = SimpleNamespace(references=references)

    selections = review_runner._select_reference_candidates(  # type: ignore[arg-type]
        policy,
        ["[[context:issue:shared]] [[context:document:shared]]"],
    )

    assert [selection.policy.resource_class for selection in selections] == [
        "issue",
        "document",
    ]


def test_enrichment_composes_one_provider_snapshot_without_remediation_reference_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = enriched_identity()
    discussion = SimpleNamespace(
        thread=0,
        reply=0,
        author_class="user",
        author_pseudonym="actor-0123456789abcdef",
        body="Investigate DEMO-7 before merge.",
        created_at=100,
        updated_at=110,
        resolved=False,
        outdated=False,
        anchor={"path": "src/review.py", "line": 8},
        version="110",
        digest="c" * 64,
    )
    remediation_reply = SimpleNamespace(
        order=0,
        author_class="user",
        author_pseudonym="actor-fedcba9876543210",
        body="DEMO-99 is claimed to be fixed; verify the current code.",
        created_at=120,
        updated_at=130,
    )
    remediation = SimpleNamespace(
        root_author_pseudonym="actor-0123456789abcdef",
        root_body="Finding DEMO-99: validate the command before execution.",
        anchor_state="current",
        replies=(remediation_reply,),
        completeness="complete",
        resolved_count=0,
        outdated_count=0,
        version="130",
        digest="d" * 64,
    )
    snapshot = SimpleNamespace(
        discussions=SimpleNamespace(state="complete", records=(discussion,)),
        remediation_threads=SimpleNamespace(state="complete", records=(remediation,)),
    )
    calls = 0
    selected: list[str] = []

    def acquire(*_args: object, **_kwargs: object) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        return snapshot

    def external(**kwargs: object) -> BrokerResult:
        selections = kwargs["selections"]
        assert isinstance(selections, list)
        selected.extend(selection.candidate.value for selection in selections)
        return BrokerResult((), {}, {"invalid": 0, "limit": 0, "unavailable": 0}, False)

    artifacts = configure_enrichment_test(
        tmp_path,
        monkeypatch,
        provider_acquire=acquire,
        external_acquire=external,
    )

    context_config, receipt = review_runner._prepare_enrichment(
        identity,
        artifacts,
        SimpleNamespace(read_blob=lambda *_args: b""),  # type: ignore[arg-type]
    )

    assert calls == 1
    assert selected == ["DEMO-7"]
    assert context_config is not None and receipt is not None
    assert receipt.mutable_admitted is True
    assert receipt.required_degraded is False
    restored = ContextStore.read(
        artifacts.context_store,
        expected_run_id=context_config.run_id,
        expected_policy_digest=context_config.policy_digest,
        now=0,
    )
    assert [record.resource_class for record in restored.records] == [
        "issue",
        "remediation_thread",
    ]
    assert review_runner._remediation_mutable_admitted(restored.records) is True
    assert (
        review_runner._remediation_mutable_admitted(
            tuple(record for record in restored.records if record.resource_class == "issue")
        )
        is False
    )
    serialized = artifacts.context_store.read_text(encoding="utf-8")
    assert "DEMO-7" in serialized
    assert "DEMO-99" in serialized
    assert "gitlab" in serialized
    assert "must-not-survive" not in serialized


def test_enrichment_dlp_rejection_cannot_make_approval_eligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = enriched_identity()
    snapshot = SimpleNamespace(
        discussions=SimpleNamespace(
            state="partial",
            records=(),
            omitted=1,
            dlp_rejected=1,
        ),
        remediation_threads=SimpleNamespace(state="complete", records=()),
    )
    artifacts = configure_enrichment_test(
        tmp_path,
        monkeypatch,
        provider_acquire=lambda *_args, **_kwargs: snapshot,
        external_acquire=lambda **_kwargs: BrokerResult(
            (), {}, {"invalid": 0, "limit": 0, "unavailable": 0}, False
        ),
    )

    _context_config, receipt = review_runner._prepare_enrichment(
        identity,
        artifacts,
        SimpleNamespace(read_blob=lambda *_args: b""),  # type: ignore[arg-type]
    )

    assert receipt is not None
    assert receipt.required_degraded is True
    assert receipt.mutable_admitted is False
    assert receipt.completeness["forge:gitlab_discussions"] == "partial"
    assert receipt.degradation_counts == {"invalid": 1, "limit": 0, "unavailable": 0}


def test_mixed_context_states_produce_exact_closed_degradation_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project mixed source failures into exact closed degradation counts."""

    identity = enriched_identity()
    snapshot = SimpleNamespace(
        discussions=SimpleNamespace(
            state="mutated",
            records=(),
            omitted=0,
            dlp_rejected=0,
        ),
        remediation_threads=SimpleNamespace(
            state="partial",
            records=(),
            omitted=2,
            dlp_rejected=1,
        ),
    )
    external = BrokerResult(
        (),
        {"reference:tracker:engineering:issue": "unavailable"},
        {"invalid": 2, "limit": 3, "unavailable": 1},
        False,
    )
    artifacts = configure_enrichment_test(
        tmp_path,
        monkeypatch,
        provider_acquire=lambda *_args, **_kwargs: snapshot,
        external_acquire=lambda **_kwargs: external,
    )

    context_config, receipt = review_runner._prepare_enrichment(
        identity,
        artifacts,
        SimpleNamespace(read_blob=lambda *_args: b""),  # type: ignore[arg-type]
    )

    assert context_config is not None and receipt is not None
    assert receipt.completeness == {
        "forge:gitlab_discussions": "mutated",
        "forge:gitlab_remediation_threads": "partial",
        "reference:tracker:engineering:issue": "unavailable",
    }
    assert receipt.degradation_counts == {"invalid": 4, "limit": 4, "unavailable": 1}
    assert receipt.required_degraded is True
    assert receipt.mutable_admitted is False
    assert "dlp_rejected" not in artifacts.context_store.read_text(encoding="utf-8")


def test_safe_mr_and_enrichment_data_preserve_auto_approval_but_remediation_does_not() -> None:
    """Keep safe MR context approval-neutral and remediation comment-only."""

    identity = enriched_identity()
    payload: dict[str, object] = {
        "status": "complete",
        "comments": [],
        "warnings": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "item-1"}],
                "completed": [{"item_id": "item-1"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
        "tool_calls": {
            "total": 3,
            "by_tool": {
                "ocr_toolkit_evidence": 1,
                "context_list": 1,
                "context_get": 1,
            },
        },
    }
    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability(
                "ocr_toolkit_evidence",
                ("ocr_toolkit_evidence", "context_list", "context_get"),
                True,
            ),
        ),
        external_servers=(),
        secret_values=(),
    )
    safe_enrichment = review_runner.EnrichmentReceipt(
        policy_digest="c" * 64,
        completeness={
            "forge:gitlab_discussions": "complete",
            "reference:tracker:engineering:issue": "complete",
        },
        degradation_counts={"invalid": 0, "limit": 0, "unavailable": 0},
        required_degraded=False,
        mutable_admitted=False,
        forbidden_publication=(
            "Validate current behavior",
            "Review the implementation and its tests.",
        ),
    )

    metadata = review_runner._review_receipt(
        payload,
        composition,
        identity,
        safe_enrichment,
    )
    metadata["schema_version"] = 5
    eligible = approval.evaluate_approval_policy(
        settings.BooleanSetting(True),
        parse_result_outcome(payload),
        [],
        [],
        0,
        metadata,
    )

    assert eligible.eligible is True
    assert metadata["context"]["per_source"] == safe_enrichment.completeness  # type: ignore[index]
    assert metadata["context"]["tool_usage"] == {  # type: ignore[index]
        "context_get": 1,
        "context_list": 1,
    }
    assert "Validate current behavior" not in repr(metadata)
    assert "Review the implementation and its tests." not in repr(metadata)

    for changed, expected_reason in (
        (replace(safe_enrichment, mutable_admitted=True), "mutable review context was admitted"),
        (
            replace(safe_enrichment, required_degraded=True),
            "the selected review context was degraded",
        ),
    ):
        blocked = review_runner._review_receipt(payload, composition, identity, changed)
        blocked["schema_version"] = 5
        decision = approval.evaluate_approval_policy(
            settings.BooleanSetting(True),
            parse_result_outcome(payload),
            [],
            [],
            0,
            blocked,
        )
        assert decision.eligible is False
        assert decision.result.reason == expected_reason


def test_combined_context_budget_counts_nested_remediation_text() -> None:
    """Charge nested remediation text against the combined context budget."""

    from ocr_toolkit.context.policy import parse_policy
    from tests.test_context_policy import encoded_policy, remediation_policy_value
    from tests.test_context_store import remediation_pending

    policy = parse_policy(encoded_policy(remediation_policy_value()))
    policy = replace(
        policy,
        budgets=replace(policy.budgets, max_chars=32, max_bytes=64, max_lines=10),
    )
    record = remediation_pending()

    admitted, limited = review_runner._bounded_combined_records([record], policy)

    assert admitted == []
    assert limited == {record.source}


def test_evidence_mcp_self_query_exercises_all_read_actions() -> None:
    """Fail preflight unless summary, list, and stable-ID get share one store."""

    sha = "a" * 40
    record = EvidenceRecord(
        kind="repository.manifest",
        value={"path": "pyproject.toml"},
        source_path="pyproject.toml",
        ref=RefRole.HEAD,
        commit_sha=sha,
        component="python",
        provenance="test",
    )
    store = EvidenceStore()
    assert store.add(record)
    store.head = EvidenceSnapshot(RefRole.HEAD, sha, (record,))
    actions: list[str] = []
    real_call = review_runner.call_tool

    def record_call(store: EvidenceStore, arguments: dict[str, object]) -> dict[str, object]:
        actions.append(str(arguments.get("action")))
        return real_call(store, arguments)

    with patched_attr(review_runner, "call_tool", record_call):
        review_runner._verify_evidence_mcp(store)

    assert actions == ["summary", "list", "get"]


def test_evidence_mcp_self_query_rejects_invalid_list_envelope() -> None:
    """Treat malformed internal MCP responses as a preflight failure."""

    store = EvidenceStore()

    def call(_store: EvidenceStore, arguments: object) -> dict[str, object]:
        action = arguments.get("action") if isinstance(arguments, dict) else None
        if action == "summary":
            return {"isError": False}
        return {"isError": False, "content": [{"text": json.dumps({"records": {}})}]}

    with (
        patched_attr(review_runner, "call_tool", call),
        pytest.raises(review_runner.ReviewRunnerError, match="invalid records"),
    ):
        review_runner._verify_evidence_mcp(store)


def test_evidence_mcp_self_query_does_not_satisfy_model_usage(tmp_path: Path) -> None:
    """A successful toolkit preflight query cannot synthesize a model tool call."""

    store = EvidenceStore()
    review_runner._verify_evidence_mcp(store)
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps({"status": "success", "tool_calls": {"total": 0, "by_tool": {}}}),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match="did not call"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


def test_ocr_result_requires_builtin_mcp_usage_for_completed_review(tmp_path: Path) -> None:
    """Accept proven built-in usage and reject a completed review without it."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "tool_calls": {"total": 2, "by_tool": {"ocr_toolkit_evidence": 2}},
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )
    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {
        "ocr_toolkit_evidence": 2
    }
    assert json.loads(result.read_text(encoding="utf-8"))["_ocr_toolkit"] == {
        "schema_version": 5,
        "review": {"source_sha": "a" * 40, "policy_sha": "b" * 40, "mr_author_id": None},
        "context": {
            "mode": "off",
            "state": "disabled",
            "classes": [],
            "policy_digest": None,
            "per_source": {},
            "degradation_counts": {"invalid": 0, "limit": 0, "unavailable": 0},
            "required_degraded": False,
            "mutable_admitted": False,
            "tool_usage": {"context_get": 0, "context_list": 0},
        },
        "mcp": {
            "capabilities": [
                {
                    "server": "ocr_toolkit_evidence",
                    "transport": "builtin",
                    "tools": ["ocr_toolkit_evidence"],
                }
            ],
            "usage": {"ocr_toolkit_evidence": 2},
        },
        "evidence": {
            "mandatory": True,
            "used": True,
            "calls": 2,
            "actions": {"state": "unavailable"},
        },
        "publication": {"state": "passed"},
        "cleanup": {"result": "passed"},
    }

    result.write_text(
        json.dumps({"status": "success", "tool_calls": {"total": 1, "by_tool": {"file_read": 1}}}),
        encoding="utf-8",
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="did not call"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


def test_evidence_action_attribution_is_verified_only_on_exact_reconciliation(
    tmp_path: Path,
) -> None:
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )
    cases = (
        ({"summary": 1, "list": 1, "get": 0}, "verified"),
        ({"summary": 1, "list": 0, "get": 0}, "unavailable"),
        (None, "unavailable"),
    )
    for index, (counts, expected) in enumerate(cases):
        result = tmp_path / f"case-{index}.json"
        result.write_text(
            json.dumps(
                {
                    "status": "success",
                    "tool_calls": {"total": 2, "by_tool": {"ocr_toolkit_evidence": 2}},
                }
            ),
            encoding="utf-8",
        )
        review_runner._record_ocr_result_mcp_usage(
            result,
            composition,
            DEFAULT_IDENTITY,
            evidence_action_counts=counts,
        )
        actions = json.loads(result.read_text(encoding="utf-8"))["_ocr_toolkit"]["evidence"][
            "actions"
        ]
        assert actions["state"] == expected


def test_ocr_result_receipt_blocks_approval_when_mr_context_was_admitted(
    tmp_path: Path,
) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    review_runner._record_ocr_result_mcp_usage(
        result,
        composition,
        review_runner.ReviewIdentity("a" * 40, "b" * 40, 41, "metadata", None),
    )

    assert json.loads(result.read_text(encoding="utf-8"))["_ocr_toolkit"] == {
        "schema_version": 5,
        "review": {"source_sha": "a" * 40, "policy_sha": "b" * 40, "mr_author_id": 41},
        "context": {
            "mode": "metadata",
            "state": "degraded",
            "classes": ["merge_request_metadata"],
            "policy_digest": None,
            "per_source": {},
            "degradation_counts": {"invalid": 0, "limit": 0, "unavailable": 0},
            "required_degraded": False,
            "mutable_admitted": False,
            "tool_usage": {"context_get": 0, "context_list": 0},
        },
        "mcp": {
            "capabilities": [
                {
                    "server": "ocr_toolkit_evidence",
                    "transport": "builtin",
                    "tools": ["ocr_toolkit_evidence"],
                }
            ],
            "usage": {"ocr_toolkit_evidence": 1},
        },
        "evidence": {
            "mandatory": True,
            "used": True,
            "calls": 1,
            "actions": {"state": "unavailable"},
        },
        "publication": {"state": "passed"},
        "cleanup": {"result": "passed"},
    }


def test_publication_projection_blocks_context_copy_secret_pii_and_laundering() -> None:
    forbidden = (
        "prefix private context sentence suffix",
        "ghp_abcdefghijklmnopqrstuvwxyz123456",
        "<!-- private hidden-only context sentence -->",
    )
    safe_payload: dict[str, object] = {
        "status": "success",
        "comments": [{"content": "Safe finding."}],
    }
    projected, publication, blocked = review_runner._publication_projection(
        safe_payload, forbidden=forbidden, allowed_tools=frozenset()
    )
    assert projected is safe_payload
    assert publication == {"state": "passed"}
    assert blocked is False

    excerpt_payload: dict[str, object] = {
        "status": "success",
        "comments": [{"content": "abcdefghijklmnopqrstuvwx"}],
    }
    projected, publication, blocked = review_runner._publication_projection(
        excerpt_payload,
        forbidden=("prefix abcdefghijklmnopqrstuvwx suffix",),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []
    assert publication["state"] == "publication-filtered"
    assert blocked is True

    for text in (
        "Copied private context sentence.",
        "<!-- private hidden-only context sentence -->",
        "private context <!--split-->sentence",
        "private context &#x73;entence",
        "private con&#x200b;text sentence",
        'private con<span data-x="' + "x" * 600 + '">text</span> sentence',
        "Contact synthetic@example.invalid.",
        "Contact synthetic&#64;example.invalid.",
        "+420<span>123</span>456789",
        "ghp_abcdefghij<span>klmnop</span>qrstuvwxyz123456",
        "See [hidden](https://example.invalid/path).",
        "See [hidden](&#x68;ttps://example.invalid/path).",
        "See [hidden][destination].\n[destination]: https://example.invalid/path",
        "See <https://example.invalid/path>.",
        "Unicode control: &#x202e;hidden.",
    ):
        hostile_payload: dict[str, object] = {
            "status": "success",
            "comments": [{"content": text}],
        }
        projected, publication, blocked = review_runner._publication_projection(
            hostile_payload, forbidden=forbidden, allowed_tools=frozenset()
        )
        assert projected["comments"] == []
        assert publication["state"] == "publication-filtered"
        assert blocked is True
        assert text not in json.dumps(projected)

    work_bound_payload: dict[str, object] = {
        "status": "success",
        "comments": [{"content": "safe " * 400}],
    }
    projected, publication, blocked = review_runner._publication_projection(
        work_bound_payload,
        forbidden=("private " * 20_000,),
        allowed_tools=frozenset(),
    )
    assert projected["comments"] == []
    assert publication["state"] == "publication-filtered"
    assert publication["reason_counts"]["limit"] == 1
    assert blocked is True


def test_publication_dlp_retains_only_safe_local_findings_and_closed_receipt(
    tmp_path: Path,
) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "comments": [
                    {
                        "path": "src/safe.py",
                        "line": 7,
                        "content": "Guard the empty collection before indexing it.",
                        "severity": "medium",
                        "category": "bug",
                    },
                    {
                        "path": "src/private.py",
                        "line": 9,
                        "content": "Copied private discussion sentence.",
                    },
                    {
                        "path": "src/optional.py",
                        "line": 11,
                        "content": "Validate the safe branch before returning.",
                        "suggestion_code": "owner = 'synthetic@example.invalid'",
                    },
                ],
                "warnings": [
                    "Safe bounded warning.",
                    "Contact synthetic@example.invalid.",
                ],
                "tool_calls": {
                    "total": 2,
                    "by_tool": {"ocr_toolkit_evidence": 1, "task_done": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    usage, blocked, publication = review_runner._finalize_ocr_result(
        result,
        composition,
        DEFAULT_IDENTITY,
        None,
        forbidden=("private discussion sentence",),
    )

    assert usage == {"ocr_toolkit_evidence": 1}
    assert blocked is True
    assert publication["state"] == "publication-filtered"
    assert publication["reason_counts"] == {
        "forbidden": 1,
        "invalid_text": 0,
        "laundering": 0,
        "limit": 0,
        "pii": 2,
        "secret": 0,
    }
    persisted = json.loads(result.read_text(encoding="utf-8"))
    assert persisted["status"] == "completed_with_errors"
    assert persisted["comments"] == [
        {
            "path": "src/safe.py",
            "line": 7,
            "content": "Guard the empty collection before indexing it.",
            "severity": "medium",
            "category": "bug",
        },
        {
            "path": "src/optional.py",
            "line": 11,
            "content": "Validate the safe branch before returning.",
        },
    ]
    assert persisted["warnings"] == ["Safe bounded warning."]
    assert persisted["tool_calls"] == {
        "total": 2,
        "by_tool": {"ocr_toolkit_evidence": 1},
    }
    assert persisted["_ocr_toolkit"]["publication"] == publication
    assert publication["retained"] == {"comments": 2, "warnings": 1}
    assert publication["omitted"] == {"comments": 1, "warnings": 1, "fields": 2}
    serialized = result.read_text(encoding="utf-8")
    assert "private discussion sentence" not in serialized
    assert "synthetic@example.invalid" not in serialized


def test_publication_dlp_ignores_private_non_rendered_identifiers_but_filters_sinks() -> None:
    payload: dict[str, object] = {
        "status": "complete",
        "message": "Review completed.",
        "comments": [
            {
                "path": "src/safe.py",
                "start_line": 7,
                "end_line": 7,
                "content": "Guard the empty collection before indexing it.",
            }
        ],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "sha-a1234567890abcdef1234567890abcdef1234567"}],
                "completed": [{"item_id": "sha-a1234567890abcdef1234567890abcdef1234567"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
        "locations": [
            {
                "source_sha": "a1234567890abcdef1234567890abcdef1234567",
                "private_diagnostic": "bounded internal diagnostic",
            }
        ],
    }

    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )

    assert projected is payload
    assert publication == {"state": "passed"}
    assert blocked is False

    payload["locations"] = [
        {
            "private_diagnostic": "synthetic@example.invalid",
            "hidden@example.invalid": "must be removed with its hostile key",
        }
    ]
    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )
    assert blocked is False
    assert publication["state"] == "private-sanitized"
    assert publication["sanitized_fields"] == 2
    assert projected["status"] == "complete"
    assert projected["locations"] == [{"private_diagnostic": "ocr-redacted-000001"}]
    assert projected["comments"] == payload["comments"]

    payload["locations"] = []
    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=("ocr.run-manifest/v1",),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )
    assert blocked is True
    assert publication["state"] == "publication-filtered"
    assert projected["status"] == "completed_with_errors"
    assert "manifest" not in projected
    assert projected["comments"] == payload["comments"]

    payload["locations"] = []
    payload["comments"] = [
        {
            "path": "src/safe.py",
            "content": '<span title="synthetic&#64;example.invalid">safe</span>',
        }
    ]
    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )
    assert blocked is True
    assert publication["state"] == "publication-filtered"
    assert publication["omitted"] == {"comments": 1, "warnings": 0, "fields": 1}


def test_private_sanitization_ignores_unknown_usage_keys_but_not_supported_buckets() -> None:
    payload: dict[str, object] = {
        "status": "success",
        "comments": [],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "usage": {
            "input_tokens": 12,
            "output_tokens": 3,
            "provider_private_label": "synthetic@example.invalid",
        },
    }

    projected, publication, blocked = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset({"ocr_toolkit_evidence"})
    )

    assert publication["state"] == "private-sanitized"
    assert blocked is False
    assert projected["usage"] == {
        "input_tokens": 12,
        "output_tokens": 3,
        "provider_private_label": "ocr-redacted-000001",
    }

    payload["usage"] = {
        "input_tokens": 12,
        "output_tokens": 3,
        "cached_tokens": "synthetic@example.invalid",
    }
    projected, publication, blocked = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset({"ocr_toolkit_evidence"})
    )
    assert publication["state"] == "publication-filtered"
    assert blocked is True
    assert "usage" not in projected
    assert projected["comments"] == []


def test_stage_grouped_retry_report_is_private_and_approval_projection_neutral() -> None:
    payload: dict[str, object] = {
        "status": "complete",
        "comments": [{"path": "src/safe.py", "content": "Keep the validated branch."}],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "coverage": {
                "selected": [{"item_id": "safe-a"}],
                "completed": [{"item_id": "safe-a"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }
    baseline = review_runner._canonical_result_projection(payload)
    payload["retry_report"] = {
        "schema_version": "ocr.llm-retry-report/v1",
        "requests": [
            {
                "review_stage": "Core review",
                "file_path": "private@example.invalid",
                "provider_detail": "Authorization: Bearer private-retry-token",
            }
        ],
    }

    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=(),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )

    assert blocked is False
    assert publication["state"] == "private-sanitized"
    assert review_runner._canonical_result_projection(projected) == baseline
    serialized = json.dumps(projected)
    assert "private@example.invalid" not in serialized
    assert "private-retry-token" not in serialized
    assert projected["status"] == "complete"
    assert projected["comments"] == payload["comments"]


def test_warning_objects_are_conservatively_publication_relevant() -> None:
    payload: dict[str, object] = {
        "status": "success",
        "comments": [],
        "warnings": [
            {
                "message": "Safe bounded warning.",
                "provider_private_label": "synthetic@example.invalid",
            }
        ],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
    }

    projected, publication, blocked = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset({"ocr_toolkit_evidence"})
    )

    assert publication["state"] == "publication-filtered"
    assert blocked is True
    assert projected["warnings"] == []
    assert "synthetic@example.invalid" not in json.dumps(projected)

    payload["warnings"] = [
        {
            "message": "Safe bounded warning.",
            "error": {"detail": "Authorization: Bearer synthetic-secret-token"},
        }
    ]
    projected, publication, blocked = review_runner._publication_projection(
        payload, forbidden=(), allowed_tools=frozenset({"ocr_toolkit_evidence"})
    )
    assert publication["state"] == "publication-filtered"
    assert blocked is True
    assert "synthetic-secret-token" not in json.dumps(projected)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("message", "Authorization: Bearer synthetic-secret-token"),
        ("warnings", ["private warning detail"]),
        (
            "tool_calls",
            {"total": 1, "by_tool": {"private-tool-name": 1}},
        ),
    ],
)
def test_unsafe_displayed_result_units_are_partial(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "status": "success",
        "comments": [],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
    }
    payload[field] = value
    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=("private warning detail", "private-tool-name"),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )

    assert publication["state"] == "publication-filtered"
    assert blocked is True
    serialized = json.dumps(projected)
    assert "synthetic-secret-token" not in serialized
    assert "private warning detail" not in serialized
    assert "private-tool-name" not in serialized


def test_unsafe_manifest_failure_detail_is_partial_and_destroyed() -> None:
    payload: dict[str, object] = {
        "status": "partial",
        "comments": [],
        "warnings": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "partial",
            "coverage": {
                "selected": [{"item_id": "safe-a"}, {"item_id": "safe-b"}],
                "completed": [{"item_id": "safe-a"}],
                "reused": [],
                "failed": [
                    {
                        "item_id": "safe-b",
                        "path": "src/private.py",
                        "classification": "provider",
                        "reason": "private failure detail",
                    }
                ],
                "waived": [],
            },
        },
    }
    projected, publication, blocked = review_runner._publication_projection(
        payload,
        forbidden=("private failure detail",),
        allowed_tools=frozenset({"ocr_toolkit_evidence"}),
    )

    assert publication["state"] == "publication-filtered"
    assert blocked is True
    assert "manifest" not in projected
    assert "private failure detail" not in json.dumps(projected)


def test_publication_dlp_atomically_sanitizes_private_fields_without_losing_manifest(
    tmp_path: Path,
) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "complete",
                "comments": [
                    {
                        "path": "src/safe.py",
                        "start_line": 7,
                        "content": "Guard the empty collection before indexing it.",
                    }
                ],
                "warnings": [],
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
                "manifest": {
                    "schema_version": "ocr.run-manifest/v1",
                    "operation": "review",
                    "terminal_state": "complete",
                    "coverage": {
                        "selected": [{"item_id": "synthetic-item"}],
                        "completed": [{"item_id": "synthetic-item"}],
                        "reused": [],
                        "failed": [],
                        "waived": [],
                    },
                },
                "locations": [{"diagnostic": "synthetic@example.invalid"}],
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    usage, blocked, publication = review_runner._finalize_ocr_result(
        result,
        composition,
        DEFAULT_IDENTITY,
        None,
        forbidden=(),
    )

    persisted = json.loads(result.read_text(encoding="utf-8"))
    assert usage == {"ocr_toolkit_evidence": 1}
    assert blocked is False
    assert publication["state"] == "private-sanitized"
    assert publication["sanitized_fields"] == 1
    assert persisted["status"] == "complete"
    assert persisted["manifest"]["terminal_state"] == "complete"
    assert persisted["comments"][0]["content"].startswith("Guard the empty")
    assert persisted["locations"] == [{"diagnostic": "ocr-redacted-000001"}]
    assert "synthetic@example.invalid" not in result.read_text(encoding="utf-8")


def test_resolve_ocr_binary_rejects_relative_and_repository_owned_path_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    local_ocr = repository / "ocr"
    local_ocr.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    local_ocr.chmod(0o700)
    external = tmp_path / "bin"
    external.mkdir()
    external_ocr = external / "ocr"
    external_ocr.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    external_ocr.chmod(0o700)
    monkeypatch.chdir(repository)

    monkeypatch.setenv("PATH", ".")
    with pytest.raises(review_runner.ReviewRunnerError, match="search path"):
        review_runner._resolve_ocr_binary()

    monkeypatch.setenv("PATH", str(repository))
    with pytest.raises(review_runner.ReviewRunnerError, match="executable is unsafe"):
        review_runner._resolve_ocr_binary()

    monkeypatch.setenv("PATH", str(external))
    assert review_runner._resolve_ocr_binary() == str(external_ocr)


def test_context_tool_calls_never_satisfy_mandatory_evidence_summary(tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "tool_calls": {"total": 2, "by_tool": {"context_list": 1, "context_get": 1}},
            }
        )
    )
    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability(
                "ocr_toolkit_evidence",
                ("ocr_toolkit_evidence", "context_list", "context_get"),
                True,
            ),
        ),
        external_servers=(),
        secret_values=(),
    )
    enrichment = review_runner.EnrichmentReceipt(
        policy_digest="c" * 64,
        completeness={},
        degradation_counts={"invalid": 0, "limit": 0, "unavailable": 0},
        required_degraded=False,
        mutable_admitted=False,
        forbidden_publication=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match="mandatory"):
        review_runner._record_ocr_result_mcp_usage(
            result,
            composition,
            review_runner.ReviewIdentity("a" * 40, "b" * 40, 41, "enriched", None),
            enrichment,
        )


def test_ocr_result_allows_manifest_failure_without_tool_calls(tmp_path: Path) -> None:
    """Persist a failed pre-tool result without inventing evidence usage."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "failed",
                "comments": [],
                "manifest": {
                    "schema_version": "ocr.run-manifest/v1",
                    "operation": "review",
                    "terminal_state": "failed",
                    "coverage": {
                        "selected": [],
                        "completed": [],
                        "reused": [],
                        "failed": [],
                        "waived": [],
                    },
                    "run_failure": {"classification": "configuration"},
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {}
    persisted = json.loads(result.read_text(encoding="utf-8"))
    assert persisted["_ocr_toolkit"]["evidence"] == {
        "mandatory": False,
        "used": False,
        "calls": 0,
        "actions": {"state": "unavailable"},
    }
    assert persisted["_ocr_toolkit"]["mcp"]["usage"] == {}


def test_ocr_result_allows_skipped_review_without_tool_calls(tmp_path: Path) -> None:
    """Do not invent an MCP-use requirement when OCR found no supported files."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "skipped",
                "message": "No supported files changed.",
                "comments": [],
                "tool_calls": {"total": 0, "by_tool": {}},
            }
        ),
        encoding="utf-8",
    )

    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )
    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {}


def test_ocr_result_allows_manifest_skipped_message_without_tool_calls(tmp_path: Path) -> None:
    """Use manifest coverage, not a legacy message literal, for versioned skips."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "skipped",
                "message": "Review skipped because no items were selected.",
                "comments": [],
                "tool_calls": {"total": 0, "by_tool": {}},
                "manifest": {
                    "schema_version": "ocr.run-manifest/v1",
                    "operation": "review",
                    "terminal_state": "skipped",
                    "coverage": {
                        "selected": [],
                        "completed": [],
                        "reused": [],
                        "failed": [],
                        "waived": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {}


def test_ocr_result_manifest_complete_requires_builtin_mcp_usage(tmp_path: Path) -> None:
    """Apply the existing evidence requirement to the new complete status."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "complete",
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
                "manifest": {
                    "schema_version": "ocr.run-manifest/v1",
                    "operation": "review",
                    "terminal_state": "complete",
                    "coverage": {
                        "selected": [{"item_id": "synthetic-item"}],
                        "completed": [{"item_id": "synthetic-item"}],
                        "reused": [],
                        "failed": [],
                        "waived": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {
        "ocr_toolkit_evidence": 1
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "status": "skipped",
            "message": "provider skipped",
            "comments": [],
            "tool_calls": {"total": 0, "by_tool": {}},
        },
        {
            "status": "skipped",
            "message": "No supported files changed.",
            "comments": [],
            "tool_calls": {"total": 1, "by_tool": {}},
        },
    ],
)
def test_ocr_result_rejects_unpinned_skipped_contract(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload), encoding="utf-8")
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match="no-supported-files contract"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


def test_ocr_result_rejects_provider_owned_toolkit_receipt(tmp_path: Path) -> None:
    """Do not trust OCR output that impersonates toolkit-authored provenance."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "success",
                "tool_calls": {
                    "total": 1,
                    "by_tool": {"ocr_toolkit_evidence": 1},
                },
                "_ocr_toolkit": {"schema_version": 1, "mcp_usage": {}},
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match="valid bounded JSON"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


def test_ocr_result_receipt_attributes_independent_mcp_servers(tmp_path: Path) -> None:
    """Aggregate only known positive tool calls under their owning servers."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "completed_with_warnings",
                "tool_calls": {
                    "total": 8,
                    "by_tool": {
                        "ocr_toolkit_evidence": 2,
                        "search_docs": 3,
                        "get_docs": 2,
                        "unconfigured_tool": 1,
                        "invalid_bool": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), builtin=True),
            MCPCapability("documentation", ("search_docs", "get_docs")),
        ),
        external_servers=(),
        secret_values=(),
    )

    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {
        "documentation": 5,
        "ocr_toolkit_evidence": 2,
    }


@pytest.mark.parametrize(
    "by_tool,error",
    [
        ({"ocr_toolkit_evidence": True}, "invalid known MCP usage count"),
        ({"ocr_toolkit_evidence": 1_000_000_001}, "invalid known MCP usage count"),
        ({"ocr_toolkit_evidence": 2}, "inconsistent aggregate MCP usage"),
        (
            {"external_a": 600_000_000, "external_b": 600_000_000, "ocr_toolkit_evidence": 1},
            "per-server MCP usage bound",
        ),
    ],
)
def test_ocr_result_rejects_unbounded_known_mcp_usage(
    tmp_path: Path, by_tool: dict[str, object], error: str
) -> None:
    """Do not serialize a receipt that its hostile readback owner must reject."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps({"status": "success", "tool_calls": {"total": 1, "by_tool": by_tool}}),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),
            MCPCapability("external", ("external_a", "external_b")),
        ),
        external_servers=(),
        secret_values=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match=error):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


def test_budget_limited_result_preserves_verified_mcp_usage(tmp_path: Path) -> None:
    """Treat a budget stop as a partial completed review, not unsupported output."""

    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "status": "budget_exceeded",
                "summary": {"budget_exceeded": True, "total_tokens": 321},
                "comments": [{"path": "example.py", "line": 7}],
                "tool_calls": {
                    "total": 2,
                    "by_tool": {"ocr_toolkit_evidence": 2},
                },
            }
        ),
        encoding="utf-8",
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), True),),
        external_servers=(),
        secret_values=(),
    )

    assert review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY) == {
        "ocr_toolkit_evidence": 2
    }
    persisted = json.loads(result.read_text(encoding="utf-8"))
    assert persisted["summary"] == {"budget_exceeded": True, "total_tokens": 321}
    assert persisted["comments"] == [{"path": "example.py", "line": 7}]


def test_ocr_result_receipt_rejects_hard_link_without_rewriting(tmp_path: Path) -> None:
    """Do not replace a result name that aliases another filesystem entry."""

    target = tmp_path / "target.json"
    original = json.dumps(
        {
            "status": "success",
            "tool_calls": {
                "total": 1,
                "by_tool": {"ocr_toolkit_evidence": 1},
            },
        }
    )
    target.write_text(original, encoding="utf-8")
    result = tmp_path / "result.json"
    os.link(target, result)
    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), builtin=True),
        ),
        external_servers=(),
        secret_values=(),
    )

    with pytest.raises(review_runner.ReviewRunnerError, match="valid bounded JSON"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)

    assert target.read_text(encoding="utf-8") == original


def test_run_review_unit_wires_argv_and_artifact_streams_to_subprocess() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert argv == ["ocr", "review", "--from", "base", "--to", "head"]
        kwargs["stdout"].write(b'{"comments": []}\n')  # type: ignore[union-attr]
        kwargs["stderr"].write(b"review complete\n")  # type: ignore[union-attr]
        return subprocess.CompletedProcess(argv, 0)

    with TemporaryDirectory() as tmp, patched_attr(review_runner.subprocess, "run", fake_run):
        result_path = Path(tmp) / "artifacts" / "result.json"
        stderr_path = Path(tmp) / "artifacts" / "stderr.log"
        exit_code = review_runner.run_review(
            result_path, stderr_path, ["--from", "base", "--to", "head"]
        )

        assert exit_code == 0
        assert result_path.read_text(encoding="utf-8") == '{"comments": []}\n'
        assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(stderr_path.stat().st_mode) == 0o600


def test_run_review_unit_redacts_failure_from_mocked_child_output() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        kwargs["stderr"].write(  # type: ignore[union-attr]
            b"Authorization: Bearer synthetic-secret-value\nprovider timeout\n"
        )
        return subprocess.CompletedProcess(argv, 1)

    output = io.StringIO()
    with (
        TemporaryDirectory() as tmp,
        patched_env(OCR_LLM_TOKEN="synthetic-secret-value"),
        patched_attr(review_runner.subprocess, "run", fake_run),
        redirect_stderr(output),
    ):
        exit_code = review_runner.run_review(
            Path(tmp) / "result.json", Path(tmp) / "stderr.log", ["--from", "base"]
        )

    assert exit_code == 1
    assert "provider timeout" in output.getvalue()
    assert "synthetic-secret-value" not in output.getvalue()
    assert "Authorization: ***" in output.getvalue()


@pytest.mark.skipif(os.name == "nt", reason="synthetic executable contract is POSIX-only")
@pytest.mark.parametrize("budget", ["0", "120000"])
def test_run_review_crosses_real_subprocess_boundary_with_private_artifacts(
    tmp_path: Path, budget: str
) -> None:
    """Exercise the production launcher against a child process beyond its boundary."""

    binary_directory = tmp_path / "bin"
    binary_directory.mkdir()
    executable = binary_directory / "ocr"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "if sys.stdin.read() != '': raise SystemExit(90)\n"
        "print(json.dumps({'argv': sys.argv[1:], 'secret_present': "
        "'OCR_LLM_TOKEN' in os.environ}, sort_keys=True))\n"
        "print('synthetic child stderr', file=sys.stderr)\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    result_path = tmp_path / "artifacts" / "result.json"
    stderr_path = tmp_path / "artifacts" / "stderr.log"
    result_path.parent.mkdir()
    result_path.write_text("stale result", encoding="utf-8")
    stderr_path.write_text("stale stderr", encoding="utf-8")
    result_path.chmod(0o644)
    stderr_path.chmod(0o644)

    with patched_env(
        PATH=os.pathsep.join((str(binary_directory), os.environ.get("PATH", ""))),
        OCR_LLM_TOKEN="synthetic-secret-value",
    ):
        exit_code = review_runner.run_review(
            result_path,
            stderr_path,
            [
                "--from",
                "base ref",
                "--to=head-ref",
                "--format",
                "json",
                "--max-tokens-budget",
                budget,
            ],
        )

    assert exit_code == 0
    assert json.loads(result_path.read_text(encoding="utf-8")) == {
        "argv": [
            "review",
            "--from",
            "base ref",
            "--to=head-ref",
            "--format",
            "json",
            "--max-tokens-budget",
            budget,
        ],
        "secret_present": True,
    }
    assert stderr_path.read_text(encoding="utf-8") == "synthetic child stderr\n"
    assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(stderr_path.stat().st_mode) == 0o600


def test_run_review_rejects_symlink_artifact() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        target.write_text("preserve", encoding="utf-8")
        result_path = Path(tmp) / "result.json"
        os.symlink(target, result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="must not be a symlink"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])

        assert target.read_text(encoding="utf-8") == "preserve"


def test_run_review_tightens_existing_artifact_permissions() -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0)

    with TemporaryDirectory() as tmp, patched_attr(review_runner.subprocess, "run", fake_run):
        result_path = Path(tmp) / "result.json"
        stderr_path = Path(tmp) / "stderr.log"
        result_path.write_text("old", encoding="utf-8")
        stderr_path.write_text("old", encoding="utf-8")
        result_path.chmod(0o644)
        stderr_path.chmod(0o644)

        assert review_runner.run_review(result_path, stderr_path, ["--from", "base"]) == 0
        assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(stderr_path.stat().st_mode) == 0o600


def test_run_review_rejects_same_result_and_stderr_path() -> None:
    with TemporaryDirectory() as tmp:
        artifact = Path(tmp) / "artifact"
        with pytest.raises(review_runner.ReviewRunnerError, match="must be different"):
            review_runner.run_review(artifact, artifact, ["--from", "base"])


def test_run_review_rejects_hard_link_artifact_without_truncating() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        target.write_text("preserve", encoding="utf-8")
        result_path = Path(tmp) / "result.json"
        os.link(target, result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="must not have hard links"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])

        assert target.read_text(encoding="utf-8") == "preserve"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO support is unavailable")
def test_run_review_rejects_fifo_artifact_without_blocking() -> None:
    with TemporaryDirectory() as tmp:
        result_path = Path(tmp) / "result.json"
        os.mkfifo(result_path)

        with pytest.raises(review_runner.ReviewRunnerError, match="private result artifact"):
            review_runner.run_review(result_path, Path(tmp) / "stderr.log", ["--from", "base"])


def test_review_refs_require_one_immutable_diff_mode() -> None:
    assert review_runner._review_refs(["--from", "base", "--to=head"]) == (
        review_runner.ReviewRefs("base", "head")
    )
    assert review_runner._review_refs(["-c", "abc123"]) == review_runner.ReviewRefs(
        "abc123^", "abc123"
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="immutable"):
        review_runner._review_refs([])
    with pytest.raises(review_runner.ReviewRunnerError, match="cannot be combined"):
        review_runner._review_refs(["--commit", "abc123", "--from", "base"])


def test_review_refs_are_resolved_before_evidence_and_ocr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bind both consumers to the same commit pair before the review starts."""

    class Reader:
        def __init__(self, root: Path) -> None:
            assert root == tmp_path

        def resolve_commit(self, ref: str) -> str:
            return {"target": "a" * 40, "source": "b" * 40}[ref]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(review_runner, "GitRepositoryReader", Reader)

    assert review_runner._immutable_review_refs(
        review_runner.ReviewRefs("target", "source")
    ) == review_runner.ReviewRefs("a" * 40, "b" * 40)


def test_immutable_ref_rewrite_preserves_non_diff_ocr_options() -> None:
    """Keep caller review settings while replacing only movable diff selectors."""

    assert review_runner._without_diff_options(
        [
            "--from",
            "target",
            "--to=source",
            "--format",
            "json",
            "--max-comments=20",
        ]
    ) == ["--format", "json", "--max-comments=20"]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--background", "inline"],
        ["--background=inline"],
        ["--background-file", "other.md"],
        ["--background-file=other.md"],
    ],
)
def test_review_rejects_caller_owned_background(arguments: list[str]) -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="managed by ocr-ci"):
        review_runner._reject_owned_background(arguments)


@pytest.mark.parametrize("option", ["--background", "--background-file"])
def test_review_rejects_missing_caller_background_value(option: str) -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="requires a value"):
        review_runner._reject_owned_background([option])


def test_evidence_review_prepares_internal_context_before_ocr(tmp_path: Path) -> None:
    events: list[object] = []
    session_homes: list[Path] = []
    original_home = os.environ.get("HOME")
    artifacts = review_runner.repository_artifacts(tmp_path)
    review_runner.prepare_artifact_directory(artifacts)
    artifacts.pre_execution_status.write_text("stale", encoding="utf-8")
    artifacts.pre_execution_status.chmod(0o600)

    class Store:
        head = SimpleNamespace(commit_sha="b" * 40)

        def add(self, record: object) -> bool:
            events.append(("enrich", record))
            return True

        def add_diagnostic(self, diagnostic: str) -> None:
            events.append(("diagnostic", diagnostic))

        def write(self, path: Path) -> None:
            events.append(("write", path))

    composition = MCPComposition(
        payload={},
        capabilities=(
            MCPCapability("ocr_toolkit_evidence", ("ocr_toolkit_evidence",), builtin=True),
        ),
        external_servers=(),
        secret_values=(),
    )

    def collect(**kwargs: str) -> Store:
        events.append(("collect", kwargs))
        return Store()

    def run(result: Path, stderr: Path, args: list[str], **_kwargs: object) -> int:
        session_homes.append(Path(os.environ["HOME"]))
        events.append(("ocr", result, stderr, args))
        return 0

    with (
        patched_attr(
            review_runner,
            "_immutable_review_refs",
            lambda _refs: review_runner.ReviewRefs("a" * 40, "b" * 40),
        ),
        patched_attr(review_runner, "_write_isolated_runtime_config", lambda: None),
        patched_attr(review_runner, "repository_artifacts", lambda: artifacts),
        patched_attr(review_runner, "collect_repository_evidence", collect),
        patched_attr(
            review_runner,
            "collect_invocation_evidence",
            lambda _identifiers, *, head_sha: (f"invocation:{head_sha}",),
        ),
        patched_attr(review_runner, "invocation_identifiers", lambda _environment: ("ci",)),
        patched_attr(
            review_runner.mcp_config,
            "build_mcp_composition",
            lambda **_kwargs: composition,
        ),
        patched_attr(
            review_runner.mcp_config,
            "apply_mcp_composition",
            lambda _composition: events.append("apply"),
        ),
        patched_attr(
            review_runner.mcp_config,
            "verify_mcp_composition",
            lambda _composition: events.append("verify"),
        ),
        patched_attr(review_runner, "render_bootstrap", lambda *_args, **_kwargs: "bootstrap"),
        patched_attr(
            review_runner,
            "write_private_text",
            lambda path, content: events.append(("bootstrap", path, content)),
        ),
        patched_attr(
            review_runner,
            "evidence_summary",
            lambda *_args: {"base": "a" * 40, "head": "b" * 40, "records": 3},
        ),
        patched_attr(
            review_runner, "_verify_evidence_mcp", lambda _store: events.append("self-query")
        ),
        patched_attr(
            review_runner,
            "_finalize_ocr_result",
            lambda *_args, **_kwargs: (
                events.append("ocr-usage") or {"ocr_toolkit_evidence": 1},
                False,
                {"state": "passed"},
            ),
        ),
        patched_attr(review_runner, "_resolve_ocr_binary", lambda: "/synthetic/ocr"),
        patched_attr(review_runner, "run_review", run),
    ):
        result = review_runner.run_evidence_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            ["--from", "base", "--to", "head", "--format", "json"],
        )

    assert result == 0
    assert not artifacts.pre_execution_status.exists()
    assert len(session_homes) == 1 and not session_homes[0].exists()
    assert os.environ.get("HOME") == original_home
    assert events[0] == (
        "collect",
        {
            "base_ref": "a" * 40,
            "head_ref": "b" * 40,
            "policy_ref": "a" * 40,
        },
    )
    assert events[1] == ("enrich", f"invocation:{'b' * 40}")
    assert events[2] == ("write", artifacts.store)
    assert events[3] == ("bootstrap", artifacts.bootstrap, "bootstrap")
    assert events[4] == "apply"
    assert events[5] == "verify"
    assert events[6] == "self-query"
    assert events[7][0] == "ocr"  # type: ignore[index]
    assert events[7][3] == [  # type: ignore[index]
        "--from",
        "a" * 40,
        "--to",
        "b" * 40,
        "--format",
        "json",
        "--background-file",
        str(artifacts.bootstrap),
    ]
    assert events[8] == "ocr-usage"
