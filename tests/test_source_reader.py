"""Immutable batch/source proof handoffs through the real Git boundary."""

import json
from dataclasses import replace

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.opaque_code import prove_opaque_code
from ocr_toolkit.evidence.repository import GitRepositoryReader
from ocr_toolkit.evidence.source_reader import SourceReadSession
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.review_range import ReviewRange
from tests.test_evidence_repository import git
from tests.test_review_range import native_result
from tests.test_review_runner import BUILTIN_EVIDENCE_TOOLS, LOCAL_IDENTITY, SUMMARY_ACTION_COUNTS
from tests.test_text_excerpts import repository


def comment(path, line, code, suggestion=None):
    return {
        "path": path,
        "start_line": line,
        "end_line": line,
        "existing_code": code,
        "suggestion_code": suggestion,
        "content": "Update this declaration.",
    }


def test_aliases_coalesce_ranges_before_one_complete_blob_read(tmp_path, monkeypatch):
    source = b"one\ntwo\nthree\n"
    _, _head = repository(tmp_path, source)
    (tmp_path / "alias").write_bytes(source)
    git(tmp_path, "add", "alias")
    git(tmp_path, "commit", "-qm", "alias")
    head = git(tmp_path, "rev-parse", "HEAD")
    calls = []
    original = GitRepositoryReader.read_text_metadata

    def observe(reader, entry, **kwargs):
        calls.append(entry.object_sha)
        return original(reader, entry, **kwargs)

    monkeypatch.setattr(GitRepositoryReader, "read_text_metadata", observe)
    session = SourceReadSession(tmp_path, head, {"source": ((1, 1), (3, 3)), "alias": ((2, 2),)})
    (tmp_path / "source").write_text("unstaged local work")
    for path, line, value in (("source", 1, "one"), ("alias", 2, "two"), ("source", 3, "three")):
        proof = prove_opaque_code(
            comment(path, line, value), path, read_head_excerpt=session.read_excerpt
        )
        assert proof.existing_verified and proof.source_reason == "verified"
    assert len(calls) == 1
    assert session.used_bytes == len(source)
    assert session.read("alias").metadata.line_count == 3
    assert (tmp_path / "source").read_text() == "unstaged local work"


def test_large_source_identity_does_not_confer_fragment_syntax_authority(tmp_path):
    source = b"#" + b"x" * 270_000 + b"\nList<Entry> value;\n"
    _, head = repository(tmp_path, source)
    session = SourceReadSession(tmp_path, head, {"source": ((2, 2),)})
    item = comment("source", 2, "List<Entry> value;", "List<Node> value;")
    proof = prove_opaque_code(item, "source", read_head_excerpt=session.read_excerpt)
    assert proof.existing_verified and proof.suggestion_verified
    assert proof.existing_context is None and proof.suggestion_context is None
    assert proof.syntax_reason == "source-limit"
    projected, publication, filtered = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [item]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    assert projected["comments"][0]["existing_code"] == item["existing_code"]
    assert not filtered and publication["state"] == "passed"


@pytest.mark.parametrize(
    "value", ["person@example.invalid", "+1 202 555 0114", 'api_key="synthetic-material"']
)
def test_proven_large_source_never_exempts_sensitive_material(tmp_path, value):
    source = "#" + "x" * 270_000 + "\n" + value + "\n"
    _, head = repository(tmp_path, source.encode())
    session = SourceReadSession(tmp_path, head, {"source": ((2, 2),)})
    item = comment("source", 2, value)
    proof = prove_opaque_code(item, "source", read_head_excerpt=session.read_excerpt)
    assert proof.existing_verified
    projected, _, filtered = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [item]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda _comment: proof,
    )
    assert filtered
    assert not projected["comments"] or "existing_code" not in projected["comments"][0]


def test_closed_source_limit_missing_invalid_and_session_budget_diagnoses(tmp_path):
    source = b"safe\n"
    _, head = repository(tmp_path, source)
    limited = SourceReadSession(tmp_path, head, {"source": ((1, 1),)}, max_source_bytes=4)
    assert limited.read("source").reason == "source-limit"
    assert limited.used_bytes == 0
    session = SourceReadSession(tmp_path, head, {"source": ((1, 1),)}, max_total_bytes=4)
    assert session.read("source").reason == "budget"
    assert session.read("missing").reason == "missing-source"
    expired = SourceReadSession(tmp_path, head, seconds=0)
    assert expired.read("source").reason == "budget"
    assert expired.read("source").reason == "budget"
    assert expired.used_bytes == 0


def test_syntax_cache_eviction_does_not_remove_captured_identity(tmp_path):
    _, _head = repository(tmp_path, b"initial")
    for index in range(5):
        (tmp_path / f"code{index}").write_text(f"def value_{index}():\n    return 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "sources")
    head = git(tmp_path, "rev-parse", "HEAD")
    session = SourceReadSession(tmp_path, head, {f"code{i}": ((2, 2),) for i in range(5)})
    for index in range(5):
        assert session.read(f"code{index}").syntax_source is not None
    result = session.read_excerpt("code0", 2, 2)
    assert result.syntax_source is None and not result.syntax_limited
    proof = prove_opaque_code(
        comment("code0", 2, "    return 1"), "code0", read_head_excerpt=session.read_excerpt
    )
    assert proof.existing_verified and proof.syntax_reason == "not-retained"


@pytest.mark.parametrize(
    "options",
    [
        {"head": "main"},
        {"head": None},
        {"requests": []},
        {"requests": {"source": 1}},
        {"requests": {"source": ((0, 1),)}},
        {"max_source_bytes": 5_000_001},
        {"max_total_bytes": -1},
        {"seconds": float("nan")},
        {"seconds": 31},
        {"seconds": True},
    ],
)
def test_bad_session_inputs_fail_before_repository_access(tmp_path, options):
    kwargs = {"head": "a" * 40, **options}
    with pytest.raises(ValueError):
        SourceReadSession(tmp_path, **kwargs)


def test_finalizer_batches_many_large_source_fields_before_publication(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    prefix = "#" + "x" * 270_000 + "\n"
    before = (prefix + "\n".join(f"List<Entry> before_{i};" for i in range(115)) + "\n").encode()
    _, base = repository(root, before)
    (root / "source").write_bytes(before.replace(b"before_", b"after_"))
    git(root, "add", ".")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    review_range = ReviewRange(base, head)
    payload = native_result(review_range)
    items = [comment("source", 2 + i, f"List<Entry> after_{i};") for i in range(115)]
    payload.update(comments=items, tool_calls={"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}})
    result = tmp_path / "result.json"
    result.write_text(json.dumps(payload))
    calls = []
    original = GitRepositoryReader.read_text_metadata

    def observe(reader, entry, **kwargs):
        calls.append(entry.object_sha)
        return original(reader, entry, **kwargs)

    monkeypatch.setattr(GitRepositoryReader, "read_text_metadata", observe)
    monkeypatch.chdir(root)
    reports = []
    composition = MCPComposition(
        {}, (MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),), (), ()
    )
    _, filtered, publication = review_runner._finalize_ocr_result(
        result,
        composition,
        replace(LOCAL_IDENTITY, source_sha=head),
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        expected_range=review_range,
        report_consumer=reports.append,
    )
    assert not filtered and publication["state"] == "passed"
    assert len(calls) == 1
    assert len(reports[0].comments) == 115
    assert [item["existing_code"] for item in json.loads(result.read_text())["comments"]] == [
        f"List<Entry> after_{i};" for i in range(115)
    ]


@pytest.mark.parametrize("kind", ["paths", "spans", "total", "bad-path"])
def test_request_population_is_bounded_before_git(tmp_path, monkeypatch, kind):
    from ocr_toolkit.evidence import source_reader

    monkeypatch.setattr(source_reader, "MAX_TEXT_SPANS", 2)
    requests = {
        "paths": {"a": (), "b": (), "c": ()},
        "spans": {"a": ((1, 1), (2, 2), (3, 3))},
        "total": {"a": ((1, 1), (2, 2)), "b": ((3, 3),)},
        "bad-path": {1: ()},
    }[kind]
    with pytest.raises(ValueError):
        SourceReadSession(tmp_path, "a" * 40, requests)


@pytest.mark.parametrize("failure", ["lookup-budget", "metadata-budget", "identity", "initial"])
def test_reader_failures_are_closed_cached_and_never_retried(tmp_path, monkeypatch, failure):
    from ocr_toolkit.evidence import source_reader
    from ocr_toolkit.evidence.repository import RepositoryReadBudget

    _, head = repository(tmp_path, b"original\n")
    calls = []
    if failure == "initial":

        def fail_init(*args, **kwargs):
            calls.append(1)
            raise RepositoryReadBudget("synthetic")

        monkeypatch.setattr(source_reader, "GitRepositoryReader", fail_init)
    elif failure == "lookup-budget":

        def fail_lookup(*args, **kwargs):
            calls.append(1)
            raise RepositoryReadBudget("synthetic")

        monkeypatch.setattr(GitRepositoryReader, "object_at", fail_lookup)
    else:
        original = GitRepositoryReader.read_text_metadata

        def fail_metadata(*args, **kwargs):
            calls.append(1)
            if failure == "metadata-budget":
                raise RepositoryReadBudget("synthetic")
            return replace(original(*args, **kwargs), object_sha="f" * 40)

        monkeypatch.setattr(GitRepositoryReader, "read_text_metadata", fail_metadata)
    session = SourceReadSession(tmp_path, head, {"source": ((1, 1),)})
    expected = "unavailable" if failure == "identity" else "budget"
    assert session.read("source").reason == expected
    assert session.read("source").reason == expected
    assert len(calls) == 1
    assert session.read(None).metadata is None


def test_source_pathless_invalid_and_expired_reads(tmp_path, monkeypatch):
    _, head = repository(tmp_path, b"source\n")
    session = SourceReadSession(tmp_path, head, {"source": ()})
    assert session.read(None).reason == "missing-source"
    assert session.read("source").metadata.line_count == 1
    assert session.read_excerpt("source", 1, 1).metadata.excerpts == ()
    session = SourceReadSession(tmp_path, head)
    session._prepare()
    monkeypatch.setattr(session, "_expired", lambda: True)
    assert session.read("source").reason == "budget"
