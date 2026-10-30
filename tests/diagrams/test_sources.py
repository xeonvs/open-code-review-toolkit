"""Real immutable Git boundaries for bounded diagram source metadata."""

import json
import subprocess
import sys
from dataclasses import replace

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.diagrams import sources
from ocr_toolkit.diagrams.admission import admit_candidate
from ocr_toolkit.diagrams.contracts import ReferenceSourceInfo, parse_submission
from ocr_toolkit.diagrams.lifecycle import DiagramExecution
from ocr_toolkit.diagrams.persistence import diagram_payload
from ocr_toolkit.evidence import repository as git_reader
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.posting.workflow import publication_range_and_diagram
from ocr_toolkit.review_range import ReviewRange
from tests.diagrams.support import flow_submission
from tests.test_evidence_repository import git
from tests.test_review_range import native_result
from tests.test_review_runner import (
    BUILTIN_EVIDENCE_TOOLS,
    DEFAULT_IDENTITY,
    LOCAL_IDENTITY,
    SUMMARY_ACTION_COUNTS,
)


def repository(tmp_path, content, *, aliases=False):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    (root / "app.py").write_bytes(content)
    if aliases:
        (root / "alias").write_bytes(content)
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "marker").write_text("head")
    git(root, "add", ".")
    git(root, "commit", "-qm", "head")
    return root, ReviewRange(base, git(root, "rev-parse", "HEAD"))


def admitted(root, review_range, *, line=1):
    payload = flow_submission()
    payload.update(base_sha=review_range.base, head_sha=review_range.head)
    payload["diagram"]["nodes"] = payload["diagram"]["nodes"][:1]
    payload["diagram"]["edges"] = []
    payload["diagram"]["nodes"][0]["references"][0].update(start_line=line, end_line=line)
    return admit_candidate(
        "local",
        parse_submission(payload, expected_range=review_range),
        review_range=review_range,
        output_calls=1,
        read_source=sources.DiagramSourceReader(root, review_range.head),
        forbidden_matcher=ForbiddenMatcher.compile(()),
        dlp_enabled=True,
    )


@pytest.mark.parametrize("size", (256_000, 256_001, 301_000, 5_000_000))
def test_large_valid_source_does_not_depend_on_evidence_blob_limit(tmp_path, size):
    root, review_range = repository(tmp_path, b"# safe\n" + b"x" * (size - 7))
    assert admitted(root, review_range, line=2).state == "generated"
    if size > 256_000:
        with pytest.raises(RepositoryEvidenceError):
            GitRepositoryReader(root).read_blob(review_range.head, "app.py")


@pytest.mark.parametrize(
    "content,lines,reason",
    (
        (b"", 0, "none"),
        (b"one", 1, "none"),
        (b"one\n", 1, "none"),
        (b"one\r\ntwo\r\n", 2, "none"),
        ("one\u2028two".encode(), 1, "none"),
        (b"x" * 65_535 + "\u20ac\n".encode(), 1, "none"),
        (b"safe\n" + b"x" * 270_000 + b"\x00", 0, "reference"),
        (b"safe\n" + b"x" * 270_000 + b"\xff", 0, "reference"),
        (b"safe\n" + b"x" * 270_000 + b"\xe2\x82", 0, "reference"),
    ),
)
def test_whole_blob_text_checks_and_line_units(tmp_path, content, lines, reason):
    root, review_range = repository(tmp_path, content)
    assert sources.DiagramSourceReader(root, review_range.head)("app.py") == ReferenceSourceInfo(
        lines, reason
    )


def test_file_and_shared_byte_budgets_are_closed(tmp_path, monkeypatch):
    root, review_range = repository(tmp_path, b"safe\n" * 10, aliases=True)
    monkeypatch.setattr(sources, "MAX_TOTAL_SOURCE_BYTES", 50)
    reader = sources.DiagramSourceReader(root, review_range.head)
    assert reader("app.py").line_count == 10
    assert reader("app.py").line_count == 10
    assert reader("alias").line_count == 10  # Same object is read and charged once.
    assert reader("marker").reason == "budget"
    assert reader._used == 50
    assert not any(isinstance(value, (bytes, str)) for value in reader._objects.values())
    monkeypatch.setattr(sources, "MAX_SOURCE_BYTES", 49)
    assert sources.DiagramSourceReader(root, review_range.head)("app.py").reason == "budget"


def test_invalid_root_and_corrupt_object_alias_are_closed(tmp_path):
    root, review_range = repository(tmp_path, b"safe\n\xff", aliases=True)
    reader = sources.DiagramSourceReader(root, review_range.head)
    assert reader("app.py").reason == reader("alias").reason == "reference"
    assert reader._used == 6
    assert (
        sources.DiagramSourceReader(tmp_path, review_range.head)("app.py").reason == "unavailable"
    )


def test_missing_links_mutable_checkout_and_wrong_lines_do_not_supply_proof(tmp_path):
    root, review_range = repository(tmp_path, b"one\ntwo\n")
    (root / "app.py").write_text("changed checkout\n")
    (root / "link").symlink_to("app.py")
    git(root, "add", "link")
    git(root, "commit", "-qm", "link")
    reader = sources.DiagramSourceReader(root, git(root, "rev-parse", "HEAD"))
    assert reader("link").reason == "reference"
    assert reader("missing").reason == "reference"
    assert admitted(root, review_range, line=2).state == "generated"
    assert admitted(root, review_range, line=3).reason == "reference"
    assert reader("../app.py").reason == "unavailable"


def test_deadline_is_shared_and_initialization_is_lazy(tmp_path, monkeypatch):
    root, review_range = repository(tmp_path, b"one\n")
    reader = sources.DiagramSourceReader(root, review_range.head)
    assert reader._reader is None
    monkeypatch.setattr(sources, "SOURCE_SECONDS", 0)
    assert reader("app.py").reason == "budget"
    assert admitted(root, review_range).reason == "budget"
    assert reader._reader is None


def test_metadata_budget_and_object_arguments_are_validated(tmp_path):
    root, review_range = repository(tmp_path, b"one\n")
    reader = GitRepositoryReader(root)
    entry = reader.object_at(review_range.head, "app.py")
    for limit in (-1, True, 32_000_001):
        with pytest.raises(RepositoryEvidenceError):
            reader.read_text_metadata(entry, max_bytes=limit)
    with pytest.raises(RepositoryEvidenceError):
        reader.read_text_metadata(replace(entry, object_sha="--invalid"), max_bytes=100)
    with pytest.raises(ValueError):
        sources.DiagramSourceReader(root, "main")


def test_over_file_limit_and_gitlink_cannot_supply_reference_metadata(tmp_path):
    root, review_range = repository(tmp_path, b"x" * 5_000_001)
    reader = sources.DiagramSourceReader(root, review_range.head)
    assert reader("app.py").reason == "budget"
    git(root, "update-index", "--add", "--cacheinfo", "160000", review_range.base, "module")
    git(root, "commit", "-qm", "gitlink")
    assert (
        sources.DiagramSourceReader(root, git(root, "rev-parse", "HEAD"))("module").reason
        == "reference"
    )


@pytest.mark.parametrize("fault", ("short", "long", "stderr", "exit", "timeout"))
def test_text_metadata_consumes_real_peer_output_with_limits_and_reaps_it(
    tmp_path, monkeypatch, fault
):
    root, review_range = repository(tmp_path, b"safe\n")
    reader = GitRepositoryReader(root)
    entry = reader.object_at(review_range.head, "app.py")
    program = (
        "import os,sys,time\n"
        "if '-s' in sys.argv: print(5)\n"
        "else:\n"
        + {
            "short": " os.write(1,b'x')\n",
            "long": " os.write(1,b'xxxxxx')\n",
            "stderr": " os.write(2,b'e'*70000)\n",
            "exit": " sys.exit(1)\n",
            "timeout": " time.sleep(10)\n",
        }[fault]
    )
    monkeypatch.setattr(git_reader, "_git_prefix", lambda _root: [sys.executable, "-c", program])
    if fault == "timeout":
        monkeypatch.setattr(reader, "_timeout", lambda _limit: 0.3)
    processes = []
    popen = subprocess.Popen

    def observed(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", observed)
    with pytest.raises((RepositoryEvidenceError, subprocess.TimeoutExpired)):
        reader.read_text_metadata(entry, max_bytes=5)
    assert processes and all(process.poll() is not None for process in processes)


def test_large_source_crosses_final_result_receipt_and_publication_readers(tmp_path, monkeypatch):
    root, review_range = repository(tmp_path, b"# safe\n" * 43_000)
    artifacts = repository_artifacts(root)
    prepare_artifact_directory(artifacts)
    execution = DiagramExecution.prepare(
        "local",
        local=True,
        native_version="1.13.3",
        review_range=review_range,
        path=artifacts.diagram,
    )
    candidate = flow_submission()
    candidate.update(base_sha=review_range.base, head_sha=review_range.head)
    execution.collector.submit(candidate)
    execution.capture()
    payload = native_result(review_range)
    payload["tool_calls"] = {
        "total": 2,
        "by_tool": {"ocr_toolkit_evidence": 1, "ocr_toolkit_review_diagram": 1},
    }
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(payload))
    composition = MCPComposition(
        {},
        (
            MCPCapability(
                "ocr_toolkit_evidence",
                (*BUILTIN_EVIDENCE_TOOLS, "ocr_toolkit_review_diagram"),
                True,
            ),
        ),
        (),
        (),
    )
    monkeypatch.chdir(root)
    reports = []
    _usage, filtered, publication = review_runner._finalize_ocr_result(
        result_path,
        composition,
        replace(LOCAL_IDENTITY, source_sha=review_range.head),
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        expected_range=review_range,
        diagram_execution=execution,
        report_consumer=reports.append,
    )
    assert not filtered and publication["state"] == "passed"
    assert reports[0].diagram.state == "generated" and reports[0].outcome.status == "complete"
    result_path.write_text(json.dumps(payload))
    execution.result = replace(execution.result, mode="on")
    review_runner._finalize_ocr_result(
        result_path,
        composition,
        replace(
            DEFAULT_IDENTITY,
            source_sha=review_range.head,
            policy_sha=review_range.base,
            target_sha=review_range.base,
            diff_base_sha=review_range.base,
            diff_start_sha=review_range.base,
            diff_head_sha=review_range.head,
        ),
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        expected_range=review_range,
        diagram_execution=execution,
    )
    from ocr_toolkit.ocr_result import load_ocr_result

    saved = load_ocr_result(result_path)
    metadata = saved["_ocr_toolkit"]
    assert metadata["diagram"] == diagram_payload(execution.result)
    _range, diagram = publication_range_and_diagram(saved, metadata, "on")
    assert diagram.state == "generated" and _range == review_range
    # The same immutable reference remains valid after mutable checkout changes.
    (root / "app.py").write_text("changed checkout")
    assert publication_range_and_diagram(saved, metadata, "on")[1].state == "generated"
