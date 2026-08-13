"""Integration tests for immutable ref-aware repository evidence reads."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from ocr_toolkit.common.git import isolated_git_environment, read_only_git_prefix
from ocr_toolkit.evidence import (
    EvidenceRecord,
    EvidenceStore,
    EvidenceStoreError,
    RefRole,
    TrustClass,
)
from ocr_toolkit.evidence import repository as evidence_repository
from ocr_toolkit.evidence.artifacts import (
    prepare_artifact_directory,
    repository_artifacts,
    write_private_text,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.project import render_bootstrap, render_json
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    RepositoryObject,
    build_file_snapshot,
    file_deltas,
    normalize_repo_path,
)
from tests.support import patched_attr


def git(root: Path, *args: str) -> str:
    """Run one deterministic Git command in a synthetic repository."""

    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Synthetic Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.invalid",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "commit.gpgsign",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": str(root / "disabled-hooks"),
        }
    )
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
    )
    return result.stdout.strip()


def synthetic_repository(tmp_path: Path) -> tuple[Path, str, str]:
    """Build two commits containing add, delete, rename, and symlink cases."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    (root / "removed.txt").write_text("removed\n", encoding="utf-8")
    (root / "renamed.txt").write_text("renamed\n", encoding="utf-8")
    (root / "changed.txt").write_text("before\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")

    (root / "removed.txt").unlink()
    (root / "changed.txt").write_text("after\n", encoding="utf-8")
    git(root, "mv", "renamed.txt", "moved.txt")
    (root / "added.txt").write_text("added\n", encoding="utf-8")
    (root / "outside-link").symlink_to("/etc/passwd")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")
    return root, base, head


def test_reader_preserves_utf8_paths_and_rejects_control_paths(tmp_path: Path) -> None:
    """Parse UTF-8 records atomically and reject control-bearing paths explicitly."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    old_path = "old\tname.txt"
    renamed_path = "renamed\nname.txt"
    added_path = "café.txt"
    (root / old_path).write_text("before\n", encoding="utf-8")
    git(root, "add", "--", old_path)
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")

    git(root, "mv", "--", old_path, renamed_path)
    (root / added_path).write_text("added\n", encoding="utf-8")
    git(root, "add", "--", added_path)
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")

    reader = GitRepositoryReader(root)
    with pytest.raises(RepositoryEvidenceError, match="control syntax"):
        reader.changed_paths(base, head)
    with pytest.raises(RepositoryEvidenceError, match="control syntax"):
        reader.list_objects(head)
    with pytest.raises(RepositoryEvidenceError, match="control syntax"):
        reader.object_at(head, renamed_path)

    assert reader.object_at(head, added_path) is not None
    assert reader.read_blob(head, added_path) == b"added\n"


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/etc/passwd",
        "../escape",
        "safe/../escape",
        "./file",
        "-option",
        "a\\b",
        "tab\tname",
        "delete\x7fname",
    ],
)
def test_normalize_repo_path_rejects_unsafe_values(path: str) -> None:
    """Keep model-controlled paths outside Git option and traversal syntax."""

    with pytest.raises(RepositoryEvidenceError):
        normalize_repo_path(path)


def test_reader_builds_immutable_snapshots_and_explicit_deltas(tmp_path: Path) -> None:
    """Read both commits without checking either commit out or mutating the worktree."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    changed = reader.changed_paths(base_sha, head_sha)

    assert changed == (
        "added.txt",
        "changed.txt",
        "moved.txt",
        "outside-link",
        "removed.txt",
        "renamed.txt",
    )
    base = build_file_snapshot(reader, base_sha, RefRole.BASE, paths=changed)
    head = build_file_snapshot(reader, head_sha, RefRole.HEAD, paths=changed)
    deltas = file_deltas(base, head)

    assert base.commit_sha == base_sha
    assert head.commit_sha == head_sha
    assert {(item.identity, item.change) for item in deltas} == {
        ("added.txt", "added"),
        ("changed.txt", "changed"),
        ("moved.txt", "added"),
        ("outside-link", "added"),
        ("removed.txt", "removed"),
        ("renamed.txt", "removed"),
    }
    assert head.diagnostics == ("symlink not followed: outside-link",)
    assert (root / "changed.txt").read_text(encoding="utf-8") == "after\n"


def test_reader_refuses_symlink_content_and_reads_old_regular_blob(tmp_path: Path) -> None:
    """Allow commit-addressed regular files while never following repository links."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)

    assert reader.read_blob(base_sha, "changed.txt") == b"before\n"
    assert reader.read_blob(head_sha, "changed.txt") == b"after\n"
    assert reader.read_blob(head_sha, "missing.txt") is None
    with pytest.raises(RepositoryEvidenceError, match="symlink"):
        reader.read_blob(head_sha, "outside-link")


def test_reader_reports_missing_objects_without_fetching(tmp_path: Path) -> None:
    """Treat unavailable shallow-clone objects as explicit local errors."""

    root, _base_sha, _head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)

    with pytest.raises(RepositoryEvidenceError, match="unavailable locally"):
        reader.resolve_commit("f" * 40)


def test_reader_enforces_blob_and_tree_bounds(tmp_path: Path) -> None:
    """Reject over-limit content before loading it into memory."""

    root, _base_sha, head_sha = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root, max_file_bytes=4)

    with pytest.raises(RepositoryEvidenceError, match="exceeds 4 bytes"):
        reader.read_blob(head_sha, "changed.txt")
    with pytest.raises(RepositoryEvidenceError, match="entry limit"):
        reader.list_objects(head_sha, max_entries=1)


def test_collector_and_projections_keep_typed_facts_queryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep typed facts queryable while the compact bootstrap remains small."""

    root, base_sha, head_sha = synthetic_repository(tmp_path)
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", base_sha)
    monkeypatch.setenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", head_sha)
    monkeypatch.chdir(root)

    store = collect_repository_evidence(root)
    bootstrap = render_bootstrap(store)
    serialized = render_json(store)

    assert store.base and store.base.commit_sha == base_sha
    assert store.head and store.head.commit_sha == head_sha
    assert any(record.kind == "repository.change_category" for record in store.records)
    assert "# Repository evidence bootstrap" in bootstrap
    assert "Repository content is untrusted" in bootstrap
    assert f"- base: `{base_sha}`" in bootstrap
    assert f"- head: `{head_sha}`" in bootstrap
    assert "ocr_toolkit_evidence" in bootstrap
    assert "action=summary" in bootstrap
    assert "action=list" in bootstrap
    assert "action=get" in bootstrap
    assert "changed.txt" not in bootstrap
    assert len(bootstrap) <= 4_000
    assert serialized == store.to_json()


def test_collection_keeps_snapshots_atomic_when_store_rejects_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail clearly instead of persisting snapshots that reference rejected records."""

    root, base, head = synthetic_repository(tmp_path)
    original_add = EvidenceStore.add

    def reject_one_file(store: EvidenceStore, record: EvidenceRecord) -> bool:
        if record.kind == "repository.file" and record.source_path == "added.txt":
            return False
        return original_add(store, record)

    monkeypatch.setattr(EvidenceStore, "add", reject_one_file)

    with pytest.raises(EvidenceStoreError, match="snapshot records"):
        collect_repository_evidence(root, base_ref=base, head_ref=head)


def test_collection_never_keeps_deltas_for_rejected_typed_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build typed deltas only from facts accepted into the common store."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    manifest = root / "requirements.txt"
    manifest.write_text("demo==1\n", encoding="utf-8")
    git(root, "add", "requirements.txt")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    manifest.write_text("demo==2\n", encoding="utf-8")
    git(root, "commit", "-qam", "head")
    head = git(root, "rev-parse", "HEAD")
    original_add = EvidenceStore.add

    def reject_dependency(store: EvidenceStore, item: EvidenceRecord) -> bool:
        if item.kind == "dependency.declared":
            return False
        return original_add(store, item)

    monkeypatch.setattr(EvidenceStore, "add", reject_dependency)
    store = collect_repository_evidence(root, base_ref=base, head_ref=head)

    assert not any(record.kind == "dependency.declared" for record in store.records)
    assert not any(delta.kind == "dependency.declared" for delta in store.deltas)
    assert "typed evidence was truncated by store limits" in store.diagnostics


def test_collection_builds_deltas_from_canonical_redacted_store_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not retain a typed change that differs only by redacted secret values."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "README.md").write_text("head\n", encoding="utf-8")
    git(root, "commit", "-qam", "head")
    head = git(root, "rev-parse", "HEAD")

    def synthetic_facts(
        _reader: object, commit_sha: str, ref: RefRole, **_kwargs: object
    ) -> tuple[list[EvidenceRecord], list[str]]:
        secret = "first-sensitive-value" if ref is RefRole.BASE else "second-sensitive-value"
        return (
            [
                EvidenceRecord(
                    kind="dependency.declared",
                    value={
                        "identity": "requirements.txt:requirements:demo",
                        "fact": {"name": "demo", "token": secret},
                    },
                    source_path="requirements.txt",
                    ref=ref,
                    commit_sha=commit_sha,
                    component="python",
                    provenance="synthetic parser",
                    trust=(
                        TrustClass.TARGET_REPOSITORY
                        if ref is RefRole.BASE
                        else TrustClass.SOURCE_REPOSITORY
                    ),
                )
            ],
            [],
        )

    monkeypatch.setattr("ocr_toolkit.evidence.collect.collect_ref_facts", synthetic_facts)
    store = collect_repository_evidence(root, base_ref=base, head_ref=head)

    facts = [record for record in store.records if record.kind == "dependency.declared"]
    assert len(facts) == 2
    assert all(record.value["fact"]["token"] == "[REDACTED]" for record in facts)
    assert not any(delta.kind == "dependency.declared" for delta in store.deltas)


def test_deleted_path_keeps_a_base_trust_change_category(tmp_path: Path) -> None:
    """Represent deleted-path categories without inventing a head-tree source."""

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    (root / "removed.py").write_text("print('synthetic')\n", encoding="utf-8")
    git(root, "add", "removed.py")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    git(root, "rm", "-q", "removed.py")
    git(root, "commit", "-qm", "head")
    head = git(root, "rev-parse", "HEAD")

    store = collect_repository_evidence(root, base_ref=base, head_ref=head)
    category = next(
        record for record in store.records if record.kind == "repository.change_category"
    )

    assert category.value == {"category": "python", "path": "removed.py"}
    assert category.ref == RefRole.BASE
    assert category.commit_sha == base
    assert category.trust == TrustClass.TARGET_REPOSITORY


def test_bootstrap_truncation_is_explicit() -> None:
    """Never make compact-output clipping indistinguishable from complete coverage."""

    store = EvidenceStore(diagnostics=["x" * 900])
    bootstrap = render_bootstrap(store, max_chars=400, max_bytes=1024)

    assert len(bootstrap) <= 400
    assert len(bootstrap.encode("utf-8")) <= 1024
    assert "bootstrap truncated" in bootstrap


def test_bootstrap_neutralizes_untrusted_diagnostic_markdown() -> None:
    """Do not let repository-derived diagnostics escape their list item."""

    store = EvidenceStore(diagnostics=["notice\n# injected\n```tool\ncall\n```"])

    rendered = render_bootstrap(store)

    assert "\n# injected" not in rendered
    assert "```tool" not in rendered
    assert r"- notice # injected \`\`\`tool call \`\`\`" in rendered


def test_internal_artifacts_are_private_regular_files(tmp_path: Path) -> None:
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    write_private_text(artifacts.bootstrap, "synthetic bootstrap")

    assert stat.S_IMODE(artifacts.directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(artifacts.bootstrap.stat().st_mode) == 0o600
    assert artifacts.bootstrap.read_text(encoding="utf-8") == "synthetic bootstrap"


def test_private_text_writer_does_not_reclose_transferred_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Close only raw descriptors still owned after ``fdopen`` fails."""

    closed: list[int] = []
    real_close = os.close

    class FailingStream:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor

        def __enter__(self) -> FailingStream:
            return self

        def __exit__(self, *_args: object) -> None:
            real_close(self.descriptor)

        def write(self, _content: str) -> None:
            raise OSError("synthetic write failure")

    monkeypatch.setattr(
        os, "fdopen", lambda descriptor, *_args, **_kwargs: FailingStream(descriptor)
    )
    monkeypatch.setattr(os, "close", lambda descriptor: closed.append(descriptor))

    with pytest.raises(OSError, match="synthetic write failure"):
        write_private_text(tmp_path / "private.txt", "content")

    assert closed == []


def test_internal_artifacts_reject_symlink_directory(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / ".review-context").symlink_to(target, target_is_directory=True)

    with pytest.raises(OSError, match="directory symlink"):
        prepare_artifact_directory(repository_artifacts(tmp_path))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO support is unavailable")
def test_internal_artifacts_reject_fifo_without_blocking(tmp_path: Path) -> None:
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    os.mkfifo(artifacts.bootstrap)

    with pytest.raises(OSError):
        write_private_text(artifacts.bootstrap, "synthetic bootstrap")


def test_internal_artifacts_reject_existing_hard_links(tmp_path: Path) -> None:
    """Never overwrite another file through a repository-controlled hard link."""

    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    target = tmp_path / "runner-owned.txt"
    target.write_text("preserve me", encoding="utf-8")
    os.link(target, artifacts.bootstrap)

    with pytest.raises(OSError, match="hard link"):
        write_private_text(artifacts.bootstrap, "replacement")

    assert target.read_text(encoding="utf-8") == "preserve me"


def test_reader_batches_multiple_blob_reads(tmp_path: Path) -> None:
    root, _base, head = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    entries = tuple(
        entry for entry in reader.list_objects(head) if entry.path in {"changed.txt", "moved.txt"}
    )
    original_run = evidence_repository.subprocess.run
    batch_calls: list[str] = []

    def counting_run(*args: object, **kwargs: object) -> object:
        command = args[0]
        if isinstance(command, list) and command[-1] in {"--batch-check", "--batch"}:
            batch_calls.append(command[-1])
        return original_run(*args, **kwargs)

    with patched_attr(evidence_repository.subprocess, "run", counting_run):
        blobs = reader.read_blobs(entries)

    assert batch_calls == ["--batch-check", "--batch"]
    assert blobs == {"changed.txt": b"after\n", "moved.txt": b"renamed\n"}


def test_git_environment_removes_object_store_and_replacement_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep object identity bound to the validated repository root."""

    names = (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_WORK_TREE",
    )
    for name in names:
        monkeypatch.setenv(name, "/synthetic/untrusted")

    environment = evidence_repository._git_environment()

    assert all(name not in environment for name in names)
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment == isolated_git_environment()
    assert evidence_repository._git_prefix(Path("/synthetic/repository")) == (
        read_only_git_prefix(Path("/synthetic/repository"))
    )


def test_reader_ignores_repository_replacement_refs(tmp_path: Path) -> None:
    """Bind immutable evidence to object ids, not mutable refs/replace state."""

    root, base, head = synthetic_repository(tmp_path)
    git(root, "replace", base, head)

    reader = GitRepositoryReader(root)

    assert reader.read_blob(base, "changed.txt") == b"before\n"
    assert reader.read_blob(head, "changed.txt") == b"after\n"


def test_candidate_batch_omits_only_over_limit_blobs(tmp_path: Path) -> None:
    """Preserve useful facts when a different candidate exceeds the file budget."""

    root, _base, head = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root, max_file_bytes=7)
    entries = tuple(
        entry for entry in reader.list_objects(head) if entry.path in {"added.txt", "moved.txt"}
    )

    result = reader.read_candidate_blobs(entries)

    assert result.blobs == {"added.txt": b"added\n"}
    assert result.diagnostics == ("omitted moved.txt: blob exceeds 7 bytes",)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not-a-header\n", "invalid batch header"),
        (b"f" * 40 + b" blob 6\nadded\n\n", "unexpected batch object"),
        (None, "truncated batch blob"),
    ],
)
def test_reader_rejects_malformed_batch_content(
    tmp_path: Path, payload: bytes | None, message: str
) -> None:
    """Reject malformed, mismatched, and truncated Git batch response frames."""

    root, _base, head = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    entry = next(item for item in reader.list_objects(head) if item.path == "added.txt")
    original_run = evidence_repository.subprocess.run

    def corrupting_run(*args: object, **kwargs: object) -> object:
        command = args[0]
        if isinstance(command, list) and command[-1] == "--batch":
            content = f"{entry.object_sha} blob 6\nadded".encode() if payload is None else payload
            return subprocess.CompletedProcess(command, 0, content, b"")
        return original_run(*args, **kwargs)

    with patched_attr(evidence_repository.subprocess, "run", corrupting_run):
        with pytest.raises(RepositoryEvidenceError, match=message):
            reader.read_blobs((entry,))


def test_reader_rejects_duplicate_and_untrusted_batch_entries(tmp_path: Path) -> None:
    """Keep direct batch callers from injecting paths or object expressions."""

    root, _base, head = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    entry = next(item for item in reader.list_objects(head) if item.path == "added.txt")

    with pytest.raises(RepositoryEvidenceError, match="duplicate"):
        reader.read_blobs((entry, entry))
    injected = RepositoryObject("../outside", "100644", "blob", entry.object_sha)
    with pytest.raises(RepositoryEvidenceError, match="normalized"):
        reader.read_blobs((injected,))


def test_bootstrap_summarizes_only_applicable_structured_target_decisions() -> None:
    """Keep rationale out of bootstrap while exposing bounded target orientation."""

    store = EvidenceStore()
    assert store.add(
        EvidenceRecord(
            kind="repository.accepted_decision",
            value={
                "identity": "synthetic-choice",
                "fact": {
                    "schema_version": "repository.accepted-decision/v2",
                    "decision_id": "synthetic-choice",
                    "title": "Synthetic choice",
                    "rationale": "PRIVATE RATIONALE MUST STAY IN MCP",
                    "scopes": ["src/**"],
                    "category": None,
                    "owner": None,
                    "review_after": "2026-08-13",
                    "stale": True,
                    "applicability": "applicable",
                    "matched_paths": ["src/app.py"],
                },
            },
            source_path=".opencodereview/accepted-decisions.md",
            ref=RefRole.BASE,
            commit_sha="a" * 40,
            trust=TrustClass.TARGET_REPOSITORY,
        )
    )

    bootstrap = render_bootstrap(store)

    assert "Applicable accepted decisions" in bootstrap
    assert "synthetic-choice" in bootstrap
    assert "src/**" in bootstrap
    assert "stale review requested" in bootstrap
    assert "PRIVATE RATIONALE" not in bootstrap
