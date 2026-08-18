"""Regression tests for safe local OCR execution diagnostics."""

from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence import EvidenceRecord, EvidenceSnapshot, EvidenceStore, RefRole
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from tests.support import patched_attr, patched_env

DEFAULT_IDENTITY = review_runner.ReviewIdentity(
    source_sha="a" * 40,
    policy_sha="b" * 40,
    mr_author_id=None,
    context_mode="off",
    context=None,
)


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
        "schema_version": 3,
        "review": {"source_sha": "a" * 40, "policy_sha": "b" * 40, "mr_author_id": None},
        "context": {"mode": "off", "state": "disabled", "classes": []},
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
        "evidence": {"mandatory": True, "used": True},
    }

    result.write_text(
        json.dumps({"status": "success", "tool_calls": {"total": 1, "by_tool": {"file_read": 1}}}),
        encoding="utf-8",
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="did not call"):
        review_runner._record_ocr_result_mcp_usage(result, composition, DEFAULT_IDENTITY)


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
        "schema_version": 3,
        "review": {"source_sha": "a" * 40, "policy_sha": "b" * 40, "mr_author_id": 41},
        "context": {
            "mode": "metadata",
            "state": "degraded",
            "classes": ["merge_request_metadata"],
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
        "evidence": {"mandatory": True, "used": True},
    }


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


def test_review_rejects_caller_owned_background_file() -> None:
    with pytest.raises(review_runner.ReviewRunnerError, match="managed by ocr-ci"):
        review_runner._reject_owned_background(["--background-file", "other.md"])


def test_evidence_review_prepares_internal_context_before_ocr(tmp_path: Path) -> None:
    events: list[object] = []
    artifacts = review_runner.repository_artifacts(tmp_path)

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

    def run(result: Path, stderr: Path, args: list[str]) -> int:
        events.append(("ocr", result, stderr, args))
        return 0

    with (
        patched_attr(
            review_runner,
            "_immutable_review_refs",
            lambda _refs: review_runner.ReviewRefs("a" * 40, "b" * 40),
        ),
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
            "_record_ocr_result_mcp_usage",
            lambda _result, _registry, _identity: (
                events.append("ocr-usage") or {"ocr_toolkit_evidence": 1}
            ),
        ),
        patched_attr(review_runner, "run_review", run),
    ):
        result = review_runner.run_evidence_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            ["--from", "base", "--to", "head", "--format", "json"],
        )

    assert result == 0
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
