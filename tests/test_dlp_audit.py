"""Private audit lifecycle, exact comparisons and real production boundaries."""

from __future__ import annotations

import io
import json
import os
import runpy
import stat
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit import cli as public_cli
from ocr_toolkit.dlp_audit import cli, scanner, worker_process
from ocr_toolkit.dlp_audit import corpus as corpus_module
from ocr_toolkit.dlp_audit import state as state_module

AuditError = state_module.AuditError
State = state_module.State
CLI_COMMAND = [str(Path(sys.executable).parent / "ocr-ci"), "dlp-audit"]
WORKER_COMMAND = [sys.executable, "-I", "-m", "ocr_toolkit.dlp_audit", "--worker"]


@pytest.fixture
def state(tmp_path: Path):
    """Use physical paths and remove synthetic raw copies even after failed tests."""

    directory = tmp_path.resolve() / "state"
    with State(directory, create=True) as owner:
        yield owner
        for path in directory.glob("corpus-*.json"):
            corpus_module.cleanup(owner, path.stem.removeprefix("corpus-"))


def captured(state, text: str) -> str:
    return corpus_module.capture(state, snippet=text.encode(), deadline=time.monotonic() + 30)


def request(state, identity: str) -> dict:
    corpus = corpus_module.manifest(state, identity)
    item = corpus["files"][0]
    raw_fd = state.raw_directory(identity)
    try:
        source = corpus_module.read_source(state, raw_fd, item).decode()
    finally:
        os.close(raw_fd)
    return {
        "key": state.key.hex(),
        "corpus": identity,
        "item": item,
        "source": source,
        "scanner": scanner.scanner_identity(),
    }


def run_in_process(state, identity: str, monkeypatch) -> tuple[str, dict]:
    """Keep lifecycle tests fast; separate tests exercise the real process boundary."""

    monkeypatch.setattr(
        scanner, "supervised", lambda body, _timeout, **_kwargs: scanner.evaluate(body)
    )
    return scanner.scan(state, identity, deadline=time.monotonic() + 30)


def test_private_state_authentication_and_exact_scope(state) -> None:
    identity = captured(state, "safe source\n")
    value = corpus_module.manifest(state, identity)
    assert stat.S_IMODE(state.path.stat().st_mode) == 0o700
    for path in state.path.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)
    document = state.path / f"corpus-{identity}.json"
    original = document.read_bytes()
    data = json.loads(original)
    data["payload"]["files"][0]["path"] = "different.txt"
    document.write_text(json.dumps(data))
    with pytest.raises(AuditError, match="authenticated"):
        corpus_module.manifest(state, identity)
    document.write_bytes(original)
    raw_fd = state.raw_directory(identity)
    try:
        slot = value["files"][0]["slot"]
        (state.path / f"raw-{identity}" / slot).write_text("changed source\n")
        with pytest.raises(AuditError, match="snapshot"):
            corpus_module.read_source(state, raw_fd, value["files"][0])
    finally:
        os.close(raw_fd)


def test_state_refuses_shared_symlink_worktree_and_parent_escape(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    shared = root / "shared"
    shared.mkdir(mode=0o755)
    with pytest.raises(AuditError, match="private"):
        State(shared, create=True)
    link = root / "link"
    link.symlink_to(shared, target_is_directory=True)
    with pytest.raises((AuditError, OSError, ValueError)):
        State(link / "child", create=True)
    worktree = root / "repo"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(AuditError, match="Git"):
        State(worktree / "state", create=True)
    with pytest.raises(AuditError, match="normalized"):
        State(root / "missing" / ".." / "state", create=True)


def test_lock_and_key_are_not_followed(tmp_path: Path) -> None:
    root = tmp_path.resolve() / "state"
    with State(root, create=True):
        with pytest.raises(AuditError, match="busy"):
            State(root)
    key = root / "key"
    key.unlink()
    key.symlink_to(root.parent / "outside")
    with pytest.raises(OSError):
        State(root)


def test_cleanup_is_owned_idempotent_and_preserves_input(state, tmp_path: Path) -> None:
    root = tmp_path.resolve() / "source"
    root.mkdir()
    original = root / "example.py"
    original.write_text("amount = 3\n")
    before = original.stat()
    identity = corpus_module.capture(
        state, root=root, paths=[original.name], deadline=time.monotonic() + 30
    )
    raw = state.path / f"raw-{identity}"
    foreign = raw / "unowned"
    foreign.write_text("unowned")
    with pytest.raises(AuditError, match="unowned"):
        corpus_module.cleanup(state, identity)
    foreign.unlink()
    corpus_module.cleanup(state, identity)
    corpus_module.cleanup(state, identity)
    assert not raw.exists()
    assert corpus_module.manifest(state, identity)["raw_removed"]
    assert original.read_text() == "amount = 3\n"
    assert original.stat().st_mtime_ns == before.st_mtime_ns


def test_interrupted_capture_is_recoverable(state, monkeypatch) -> None:
    original_open = corpus_module.os.open

    def fail_raw_write(path, flags, *args, **kwargs):
        if isinstance(path, str) and state_module.ID.fullmatch(path) and flags & os.O_WRONLY:
            raise OSError("synthetic interruption")
        return original_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(corpus_module.os, "open", fail_raw_write)
        with pytest.raises(OSError):
            captured(state, "source\n")
    documents = list(state.path.glob("corpus-*.json"))
    assert len(documents) == 1
    identity = documents[0].stem.removeprefix("corpus-")
    corpus_module.cleanup(state, identity)
    assert not list(state.path.glob("raw-*"))


def test_source_selection_links_fifo_and_moving_inputs(state, tmp_path: Path, monkeypatch) -> None:
    root = tmp_path.resolve() / "source"
    root.mkdir()
    source = root / "file.py"
    source.write_text("amount = 1\n")
    (root / "link.py").symlink_to(source)
    os.link(source, root / "hard.py")
    os.mkfifo(root / "fifo.py")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for path in ("file.py", "hard.py", "fifo.py", "link.py"):
            with pytest.raises((AuditError, OSError)):
                corpus_module.selected_file(descriptor, path)
    finally:
        os.close(descriptor)
    (root / "hard.py").unlink()
    original = corpus_module.selected_file
    calls = 0

    def moving(fd, path, **kwargs):
        nonlocal calls
        calls += 1
        return original(fd, path, **kwargs) if calls == 1 else b"changed\n"

    monkeypatch.setattr(corpus_module, "selected_file", moving)
    with pytest.raises(AuditError, match="selection changed"):
        corpus_module.capture(state, root=root, paths=["file.py"], deadline=time.monotonic() + 30)
    assert not list(state.path.glob("raw-*"))


@pytest.mark.parametrize("raw", [b"\xff", b"a\x00b"])
def test_unsupported_input_is_accounted_and_cannot_pass(state, raw, monkeypatch) -> None:
    identity = corpus_module.capture(state, snippet=raw, deadline=time.monotonic() + 30)
    _, result = run_in_process(state, identity, monkeypatch)
    assert not result["complete"] and result["units"] == 0
    assert result["errors"] == [
        {
            "slot": corpus_module.manifest(state, identity)["files"][0]["slot"],
            "reason": "unsupported_input",
        }
    ]


def test_real_worker_proof_projection_and_no_source_in_report(state) -> None:
    text = '#include <stdint.h>\ntoken = "".join(parts)\namount = 17\n'
    identity = captured(state, text)
    result = scanner.supervised(request(state, identity), 30)
    assert result["units"] == 4
    assert any(hit["unit"] == 1 and hit["role"] == "text" for hit in result["hits"])
    assert not any(hit["unit"] == 1 and hit["role"] == "existing_code" for hit in result["hits"])
    assert text not in json.dumps(result)
    assert "parts" not in json.dumps(result)


def test_raw_role_matches_prose_while_code_keeps_source_tabs(state) -> None:
    from ocr_toolkit import review_runner
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    text = "\tamount = 3"
    identity = captured(state, text)
    result = scanner.evaluate(request(state, identity))
    assert result["hits"] and all(hit["role"] == "text" for hit in result["hits"])
    assert all(
        (hit["reason"], hit["detector"]) == ("invalid_text", "type_or_control")
        for hit in result["hits"]
    )
    comment = {"path": "snippet.txt", "line": 1, "content": text, "existing_code": text}
    projected, publication, _ = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(item, "snippet.txt", lambda _path: text),
    )
    assert projected["comments"] == [] and publication["omitted"]["comments"] == 1
    comment["content"] = "Inspect the expression."
    projected, publication, _ = review_runner._publication_projection(
        {"status": "success", "warnings": [], "comments": [comment]},
        forbidden=(),
        allowed_tools=frozenset(),
        code_proof=lambda item: prove_opaque_code(item, "snippet.txt", lambda _path: text),
    )
    assert projected["comments"][0]["existing_code"] == text and publication["state"] == "passed"


def test_raw_admission_dominates_actual_projection() -> None:
    from ocr_toolkit import review_runner
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text
    from ocr_toolkit.evidence.opaque_code import prove_opaque_code

    for text in ("amount = 3", "value = table[index]", "", "\treturn data", "version >= 2020.1.10"):
        assert check_text(
            text,
            budgets=TextBudgets(1000, 4000, 100),
            publication=True,
            allow_horizontal_tabs=True,
            enabled=True,
        ).admitted
        item = {
            "path": "example.py",
            "line": 1,
            "content": "Inspect the expression.",
            "existing_code": text,
        }
        output, _, _ = review_runner._publication_projection(
            {"status": "success", "comments": [item], "warnings": []},
            forbidden=(),
            allowed_tools=frozenset(),
            code_proof=lambda value: prove_opaque_code(value, "example.py", lambda _path: text),
        )
        assert output["comments"][0]["existing_code"] == text


def test_worker_shadow_packages_cannot_execute(tmp_path: Path, state) -> None:
    root = tmp_path.resolve()
    marker = root / "executed"
    (root / "ocr_toolkit.py").write_text(f"open({str(marker)!r}, 'w').write('bad')\n")
    (root / "sitecustomize.py").write_text(f"open({str(marker)!r}, 'w').write('bad')\n")
    identity = captured(state, "amount = 3\n")
    result = subprocess.run(
        WORKER_COMMAND,
        input=worker_process.frame(b"0" * 16 + state_module.encode(request(state, identity))),
        capture_output=True,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert (
        state_module.decode(worker_process.read_request(io.BytesIO(result.stdout))[16:])["units"]
        == 2
    )
    assert not marker.exists()


def test_worker_failure_and_deadline_are_incomplete(state, monkeypatch) -> None:
    identity = captured(state, "amount = 1\n")

    def failure(*_args, **_kwargs):
        raise AuditError("worker_timeout")

    monkeypatch.setattr(scanner, "supervised", failure)
    run_id, result = scanner.scan(state, identity, deadline=time.monotonic() + 30)
    assert not result["complete"] and result["errors"]
    assert scanner.load_run(state, run_id) == result
    with pytest.raises(AuditError, match="incomplete"):
        cli.compare(state, run_id, run_id)
    _, expired = scanner.scan(state, identity, deadline=time.monotonic() - 1)
    assert expired["errors"][0]["reason"] == "scan_deadline"


def test_exact_annotations_never_skip_scanning_or_cross_corpora(state, monkeypatch) -> None:
    identity = captured(state, "token = parse_value()\n")
    before_id, before = run_in_process(state, identity, monkeypatch)
    assert before["complete"] and before["hits"]
    hits = [hit["id"] for hit in before["hits"]]
    cli.annotate(state, before_id, hits, "conservative-ambiguity")
    after_id, after = run_in_process(state, identity, monkeypatch)
    assert after["hits"] == before["hits"]
    code, diff = cli.compare(state, before_id, after_id)
    assert code == 0 and not any(diff.values())
    other_id = captured(state, "token = parse_value()\n")
    other_run, other = run_in_process(state, other_id, monkeypatch)
    assert other["hits"][0]["id"] not in hits
    with pytest.raises(AuditError, match="incomparable"):
        cli.compare(state, before_id, other_run)
    with pytest.raises(AuditError, match="rejected unit"):
        cli.annotate(state, other_run, hits, "confirmed-benign")


def test_comparison_flags_new_rejections_and_lost_protection(state, monkeypatch) -> None:
    identity = captured(state, "amount = 1\ntoken = parse_value()\n")
    before_id, before = run_in_process(state, identity, monkeypatch)
    cli.annotate(state, before_id, [hit["id"] for hit in before["hits"]], "expected-protection")
    changed = {**before, "hits": []}
    lost_id = "a" * 32
    state.save("run", lost_id, changed)
    code, diff = cli.compare(state, before_id, lost_id)
    assert code == 1 and diff["protection_lost"] == len(before["hits"])
    # A formerly admitted line must appear as a new rejection, not disappear
    # because the baseline retained only rejected records.
    item = corpus_module.manifest(state, identity)["files"][0]
    hit = {
        "id": scanner._unit_id(state.key, identity, item, 1, "text"),
        "slot": item["slot"],
        "unit": 1,
        "role": "text",
        "reason": "secret",
        "detector": "normalized",
        "proof": True,
    }
    new_id = "b" * 32
    state.save("run", new_id, {**before, "hits": [*before["hits"], hit]})
    code, diff = cli.compare(state, before_id, new_id)
    assert code == 1 and diff["newly_rejected"] == 1 and diff["untriaged"] == 1
    cli.annotate(state, new_id, [hit["id"]], "conservative-ambiguity")
    code, diff = cli.compare(state, before_id, new_id)
    assert code == 0 and diff["newly_rejected"] == 1


def test_reason_change_needs_exact_new_review(state, monkeypatch) -> None:
    identity = captured(state, "token = parse_value()\n")
    before_id, before = run_in_process(state, identity, monkeypatch)
    ids = [hit["id"] for hit in before["hits"]]
    cli.annotate(state, before_id, ids, "conservative-ambiguity")
    after_id = "c" * 32
    state.save(
        "run",
        after_id,
        {**before, "hits": [{**hit, "detector": "decoded"} for hit in before["hits"]]},
    )
    code, diff = cli.compare(state, before_id, after_id)
    assert code == 1 and diff["unreviewed_changes"] == len(ids)
    cli.annotate(state, after_id, ids, "conservative-ambiguity")
    code, diff = cli.compare(state, before_id, after_id)
    assert code == 0 and diff["changed_decisions"] == len(ids)


def test_benign_classification_does_not_allow_other_admissions(state, monkeypatch) -> None:
    identity = captured(state, "token = parse_value()\n")
    before_id, before = run_in_process(state, identity, monkeypatch)
    ids = [hit["id"] for hit in before["hits"]]
    after_id = "d" * 32
    state.save("run", after_id, {**before, "hits": []})
    code, diff = cli.compare(state, before_id, after_id)
    assert code == 1 and diff["unexplained_admissions"] == len(ids)
    cli.annotate(state, before_id, ids, "confirmed-benign")
    code, diff = cli.compare(state, before_id, after_id)
    assert code == 0 and diff["newly_admitted"] == len(ids)


def test_limits_empty_unicode_and_newline_paths_are_accounted(
    state, tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path.resolve() / "inputs"
    root.mkdir()
    filename = "λογική\nsource.py"
    (root / filename).write_text("\n\namount = 17\n")
    identity = corpus_module.capture(
        state, root=root, paths=[filename], deadline=time.monotonic() + 30
    )
    _, result = run_in_process(state, identity, monkeypatch)
    assert result["complete"] and result["units"] == 2
    empty = captured(state, "")
    _, result = run_in_process(state, empty, monkeypatch)
    assert result["complete"] and result["units"] == 1 and result["hits"] == []
    monkeypatch.setattr(corpus_module, "MAX_TOTAL", 2)
    with pytest.raises(AuditError, match="size limit"):
        captured(state, "more than two bytes")


def test_state_cannot_overlap_inputs_in_either_direction(state) -> None:
    for root in (state.path.parent, state.path / "source"):
        with pytest.raises(AuditError, match="outside input roots"):
            corpus_module.private_location(state, root)


def test_metadata_only_replays_complete_inputs_without_copies(state, tmp_path, monkeypatch) -> None:
    root = tmp_path.resolve() / "input"
    root.mkdir()
    original = root / "example.py"
    original.write_text("token = parse_value()\n")
    identity = corpus_module.capture(
        state, root=root, paths=[original.name], metadata_only=True, deadline=time.monotonic() + 30
    )
    assert not list(state.path.glob("raw-*"))
    before_id, before = run_in_process(state, identity, monkeypatch)
    assert before["complete"]
    cli.annotate(state, before_id, [hit["id"] for hit in before["hits"]], "conservative-ambiguity")
    after_id, _ = run_in_process(state, identity, monkeypatch)
    assert cli.compare(state, before_id, after_id)[0] == 0
    original.write_text("amount = 1\n")
    with pytest.raises(AuditError, match="snapshot"):
        run_in_process(state, identity, monkeypatch)
    assert not list(state.path.glob("raw-*"))
    corpus_module.cleanup(state, identity)
    assert original.read_text() == "amount = 1\n"


def test_metadata_only_detects_movement_during_worker(state, tmp_path, monkeypatch) -> None:
    root = tmp_path.resolve() / "input"
    root.mkdir()
    original = root / "example.py"
    original.write_text("amount = 1\n")
    identity = corpus_module.capture(
        state, root=root, paths=[original.name], metadata_only=True, deadline=time.monotonic() + 30
    )

    def moving(body, _timeout, **_kwargs):
        original.write_text("changed original\n")
        return scanner.evaluate(body)

    monkeypatch.setattr(scanner, "supervised", moving)
    with pytest.raises(AuditError, match="snapshot"):
        scanner.scan(state, identity, deadline=time.monotonic() + 30)
    assert not list(state.path.glob("run-*.json"))
    assert not list(state.path.glob("raw-*"))


@pytest.mark.parametrize("extra", [{"snippet": b"x"}, {"git_ref": "HEAD"}, {}])
def test_metadata_only_cannot_select_another_input_mode(state, extra) -> None:
    with pytest.raises(AuditError, match="explicit file selection"):
        corpus_module.capture(state, metadata_only=True, deadline=time.monotonic() + 30, **extra)


def test_worker_output_contract_rejects_spoofed_id_and_incomplete_population(
    state, monkeypatch
) -> None:
    identity = captured(state, "token = parse_value()\n")
    correct = scanner.evaluate(request(state, identity))
    with monkeypatch.context() as patch:
        wrong = {**correct, "units": correct["units"] - 1}
        patch.setattr(scanner, "supervised", lambda *_args, **_kwargs: wrong)
        with pytest.raises(AuditError, match="population"):
            scanner.scan(state, identity, deadline=time.monotonic() + 30)
    spoofed = {**correct, "hits": [{**correct["hits"][0], "id": "f" * 64}]}
    monkeypatch.setattr(scanner, "supervised", lambda *_args, **_kwargs: spoofed)
    with pytest.raises(AuditError, match="unbound"):
        scanner.scan(state, identity, deadline=time.monotonic() + 30)


def test_real_cli_complete_scan_reports_source_free_and_cleans(tmp_path: Path) -> None:
    directory = tmp_path.resolve() / "state"
    result = subprocess.run(
        [*CLI_COMMAND, "--state-dir", str(directory), "scan", "--stdin"],
        input=b"amount = 3\n",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["complete"] and summary["units"] == 2
    assert b"amount" not in result.stdout + result.stderr
    with State(directory) as owner:
        run = scanner.load_run(owner, summary["run"])
        assert run["hits"] == []
        report = (directory / f"run-{summary['run']}.md").read_text()
        assert "amount" not in report and "false-positive rate" in report
        corpus_module.cleanup(owner, summary["corpus"])
    assert not list(directory.glob("raw-*"))


@pytest.mark.parametrize("bad_field,bad_value", [("complete", True), ("units", 1), ("future", {})])
def test_hostile_partial_run_cannot_claim_completeness(
    state, monkeypatch, bad_field, bad_value
) -> None:
    identity = captured(state, "amount = 1\n")

    def failure(*_args, **_kwargs):
        raise AuditError("worker_failed")

    monkeypatch.setattr(scanner, "supervised", failure)
    run_id, result = scanner.scan(state, identity, deadline=time.monotonic() + 30)
    state.save("run", run_id, {**result, bad_field: bad_value})
    with pytest.raises(AuditError):
        scanner.load_run(state, run_id)


def test_stale_secret_set_and_unknown_signed_schema_are_rejected(state, monkeypatch) -> None:
    identity = captured(state, "amount = 1\n")
    run_id, run = run_in_process(state, identity, monkeypatch)
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-credential-for-exact-set")
    with pytest.raises(AuditError, match="incomparable"):
        cli.compare(state, run_id, run_id)
    state.save("run", run_id, {**run, "future": {}})
    with pytest.raises(AuditError, match="fields"):
        scanner.load_run(state, run_id)


def test_console_errors_never_echo_operator_values(tmp_path: Path) -> None:
    value = "synthetic-sensitive-operator-value"
    result = subprocess.run(
        [*CLI_COMMAND, "--unknown", value],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert value.encode() not in result.stdout + result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["--unknown", "synthetic-sensitive-operator-value"],
        ["--state-dir", "/synthetic", "synthetic-sensitive-operator-value"],
        [
            "--state-dir",
            "/synthetic",
            "scan",
            "--stdin",
            "--seconds",
            "synthetic-sensitive-operator-value",
        ],
        [
            "--state-dir",
            "/synthetic",
            "scan",
            "--stdin",
            "--unknown",
            "synthetic-sensitive-operator-value",
        ],
    ],
)
def test_public_parser_errors_are_source_free(arguments, capsys) -> None:
    assert public_cli.main(["dlp-audit", *arguments]) == 2
    output = capsys.readouterr()
    assert "synthetic-sensitive-operator-value" not in output.out + output.err
    assert "Traceback" not in output.err


def test_audit_dispatch_does_not_acquire_review_or_provider_configuration(
    tmp_path, monkeypatch, capsys
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("local audit must not acquire review/provider configuration")

    monkeypatch.setattr(public_cli.preflight, "main", forbidden)
    monkeypatch.setattr(public_cli.configure, "main", forbidden)
    monkeypatch.setattr(public_cli.mcp_config, "configure_mcp_servers", forbidden)
    monkeypatch.setattr(public_cli.review_runner, "run_evidence_review", forbidden)
    monkeypatch.setattr(public_cli, "posting_main", forbidden)
    directory = tmp_path.resolve() / "state"
    with State(directory, create=True) as owner:
        identity = captured(owner, "amount = 1\n")
    monkeypatch.setattr(
        scanner, "supervised", lambda body, _timeout, **_kwargs: scanner.evaluate(body)
    )
    try:
        assert (
            public_cli.main(
                ["dlp-audit", "--state-dir", str(directory), "scan", "--snapshot", identity]
            )
            == 0
        )
        output = capsys.readouterr()
        assert json.loads(output.out)["complete"]
    finally:
        with State(directory) as owner:
            corpus_module.cleanup(owner, identity)


def test_internal_worker_entrypoint_only_accepts_its_fixed_protocol(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(scanner, "worker", lambda: calls.append("worker") or 0)
    for arguments, expected in ((["--worker"], 0), (["scan"], 2), (["--worker", "extra"], 2)):
        monkeypatch.setattr(sys, "argv", ["internal-worker", *arguments])
        with pytest.raises(SystemExit) as result:
            runpy.run_module("ocr_toolkit.dlp_audit", run_name="__main__")
        assert result.value.code == expected
    assert calls == ["worker"]


def test_cli_full_lifecycle_with_exact_file_selection(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path.resolve()
    inputs = root / "input"
    inputs.mkdir()
    (inputs / "example.py").write_text("token = parse_value()\n")
    selection = root / "selection"
    selection.write_bytes(b"example.py\0")
    state_path = root / "state"
    monkeypatch.setattr(
        scanner, "supervised", lambda body, _timeout, **_kwargs: scanner.evaluate(body)
    )

    def invoke(*args):
        monkeypatch.setattr(sys, "argv", [*CLI_COMMAND, "--state-dir", str(state_path), *args])
        code = public_cli.main()
        output = capsys.readouterr()
        assert "token =" not in output.out + output.err
        return code, json.loads(output.out or output.err)

    code, baseline = invoke("scan", "--root", str(inputs), "--files-from0", str(selection))
    assert code == 1 and baseline["complete"]
    with State(state_path) as owner:
        hits = scanner.load_run(owner, baseline["run"])["hits"]
    args = [item for hit in hits for item in ("--hit", hit["id"])]
    code, _ = invoke("annotate", baseline["run"], "--label", "conservative-ambiguity", *args)
    assert code == 0
    code, replay = invoke("scan", "--snapshot", baseline["corpus"])
    assert code == 0 and replay["rejections"] == baseline["rejections"]
    code, diff = invoke("compare", baseline["run"], replay["run"])
    assert code == 0 and not any(diff.values())
    code, result = invoke("cleanup", baseline["corpus"])
    assert code == 0 and result["raw_removed"]
    assert invoke("scan", "--snapshot", baseline["corpus"])[0] == 2


@pytest.mark.parametrize(
    "mode", ["snippet", "binary", "bad-list", "fifo-list", "no-root", "mixed-root"]
)
def test_cli_invalid_and_incomplete_modes(tmp_path: Path, monkeypatch, capsys, mode: str) -> None:
    root = tmp_path.resolve()
    inputs = root / "inputs"
    inputs.mkdir()
    selection = root / "selection"
    selection.write_bytes(b"source.py")
    monkeypatch.setattr(
        scanner, "supervised", lambda body, _timeout, **_kwargs: scanner.evaluate(body)
    )
    arguments = [*CLI_COMMAND, "--state-dir", str(root / "state"), "scan"]
    stdin_file = None
    if mode in {"snippet", "binary", "mixed-root"}:
        raw = b"amount = 1\n" if mode != "binary" else b"\xff\x00"
        stdin_path = root / "stdin.txt"
        stdin_path.write_bytes(raw)
        stdin_file = stdin_path.open("rb")
        monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=stdin_file))
        arguments += ["--stdin"]
        if mode == "mixed-root":
            arguments += ["--root", str(inputs)]
    else:
        if mode == "fifo-list":
            selection.unlink()
            os.mkfifo(selection)
        arguments += ["--files-from0", str(selection)]
        if mode != "no-root":
            arguments += ["--root", str(inputs)]
    monkeypatch.setattr(sys, "argv", arguments)
    try:
        code = public_cli.main()
    finally:
        if stdin_file is not None:
            stdin_file.close()
    assert code == (0 if mode == "snippet" else 2)
    output = capsys.readouterr()
    assert "Traceback" not in output.err
    if mode in {"snippet", "binary"}:
        result = json.loads(output.out)
        with State(root / "state") as owner:
            corpus_module.cleanup(owner, result["corpus"])
    assert not list((root / "state").glob("raw-*"))


def test_immutable_git_capture_and_unsupported_objects(state, tmp_path: Path, monkeypatch) -> None:
    root = tmp_path.resolve() / "git"
    root.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, check=True, timeout=30
        )

    git("init", "--quiet")
    (root / "source.py").write_text("amount = 3\n")
    (root / "source-link").symlink_to("source.py")
    git("add", "source.py", "source-link")
    git(
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "Synthetic source",
    )
    (root / "source.py").write_text("changed working tree\n")
    identity = corpus_module.capture(
        state, root=root, git_ref="HEAD", deadline=time.monotonic() + 30
    )
    corpus = corpus_module.manifest(state, identity)
    item = next(item for item in corpus["files"] if item["path"] == "source.py")
    fd = state.raw_directory(identity)
    try:
        assert corpus_module.read_source(state, fd, item) == b"amount = 3\n"
    finally:
        os.close(fd)
    _, result = run_in_process(state, identity, monkeypatch)
    assert not result["complete"] and len(result["errors"]) == 1


def test_stdin_open_pipe_obeys_deadline_and_releases_state(tmp_path: Path) -> None:
    directory = tmp_path.resolve() / "state"
    process = subprocess.Popen(
        [*CLI_COMMAND, "--state-dir", str(directory), "scan", "--stdin", "--seconds", "1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert (
            process.stdin is not None and process.stdout is not None and process.stderr is not None
        )
        process.stdin.write(b"synthetic-sensitive-open-pipe-value\n")
        process.stdin.flush()
        # Keeping the write end open is essential: communicate() would close it.
        assert process.wait(timeout=10) == 2
        output = process.stdout.read() + process.stderr.read()
        assert b"synthetic-sensitive-open-pipe-value" not in output
        assert b"Traceback" not in output
        with State(directory):
            assert not list(directory.glob("raw-*"))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def test_input_limits_and_nonblocking_flags_restore(tmp_path, monkeypatch) -> None:
    path = tmp_path.resolve() / "input"
    path.write_bytes(b"abc")
    with path.open("rb") as stream:
        descriptor = stream.fileno()
        original = os.get_blocking(descriptor)
        with pytest.raises(AuditError, match="deadline"):
            corpus_module.read_input(descriptor, deadline=time.monotonic() - 1)
        assert os.get_blocking(descriptor) == original
        with monkeypatch.context() as patch:
            patch.setattr(corpus_module, "MAX_FILE", 2)
            with pytest.raises(AuditError, match="size limit"):
                corpus_module.read_input(descriptor, deadline=time.monotonic() + 5)
        assert os.get_blocking(descriptor) == original
        stream.seek(0)
        real_read = os.read
        attempts = 0

        def temporarily_unavailable(fd, length):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise BlockingIOError
            return real_read(fd, length)

        monkeypatch.setattr(corpus_module.os, "read", temporarily_unavailable)
        assert corpus_module.read_input(descriptor, deadline=time.monotonic() + 5) == b"abc"
        assert os.get_blocking(descriptor) == original


def test_git_acquisition_timeout_is_bounded_and_source_free(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path.resolve() / "synthetic-sensitive-root"
    root.mkdir()
    ref = "synthetic-sensitive-ref"
    seen = []

    def timeout(target, arguments, *, timeout=15, text=True):
        seen.append(timeout)
        raise subprocess.TimeoutExpired(["git", "-C", str(target), *arguments, ref], timeout)

    monkeypatch.setattr(corpus_module.GitRepositoryReader, "_run_at", staticmethod(timeout))
    directory = tmp_path.resolve() / "state"
    assert (
        public_cli.main(
            [
                "dlp-audit",
                "--state-dir",
                str(directory),
                "scan",
                "--root",
                str(root),
                "--git-ref",
                ref,
                "--seconds",
                "1",
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert "synthetic-sensitive" not in output.out + output.err
    assert "Traceback" not in output.err and seen and 0 < seen[0] <= 1
    with State(directory):
        assert not list(directory.glob("raw-*"))
    with pytest.raises(ValueError, match="deadline"):
        corpus_module.GitRepositoryReader(root, deadline=time.monotonic() - 1)


def test_reloaded_run_cannot_erase_unsupported_members(state, monkeypatch) -> None:
    identity = corpus_module.capture(state, snippet=b"\xff", deadline=time.monotonic() + 30)
    run_id, result = run_in_process(state, identity, monkeypatch)
    assert not result["complete"] and result["errors"]
    state.save("run", run_id, {**result, "errors": [], "complete": True})
    with pytest.raises(AuditError, match="unsupported inputs"):
        scanner.load_run(state, run_id)
    with pytest.raises(AuditError, match="unsupported inputs"):
        cli.compare(state, run_id, run_id)
    state.save(
        "run",
        run_id,
        {**result, "errors": [{**result["errors"][0], "reason": "worker_unavailable"}]},
    )
    with pytest.raises(AuditError, match="does not match corpus"):
        scanner.load_run(state, run_id)


def test_cleanup_rejects_substituted_link_without_touching_original(state, tmp_path: Path) -> None:
    identity = captured(state, "amount = 3\n")
    item = corpus_module.manifest(state, identity)["files"][0]
    copied = state.path / f"raw-{identity}" / item["slot"]
    original = tmp_path.resolve() / "original"
    original.write_text("original")
    copied.unlink()
    copied.symlink_to(original)
    with pytest.raises(AuditError, match="unsafe raw"):
        corpus_module.cleanup(state, identity)
    assert original.read_text() == "original"
    copied.unlink()


@pytest.mark.parametrize(
    "payload", [b'{"a":1,"a":2}', b'{"v":NaN}', b'{"v":Infinity}', b"\xff", b"{"]
)
def test_json_rejects_noncanonical_documents(payload: bytes) -> None:
    with pytest.raises(AuditError):
        state_module.decode(payload)


def test_supervisor_timeout_nonzero_malformed_and_bounds(state, monkeypatch) -> None:
    body = request(state, captured(state, "amount = 3\n"))

    def timeout(*_args, **_kwargs):
        raise worker_process.WorkerFailure("worker_timeout")

    monkeypatch.setattr(worker_process.WorkerSession, "exchange", timeout)
    with pytest.raises(AuditError, match="timeout"):
        scanner.supervised(body, 1)

    def failed(*_args, **_kwargs):
        raise worker_process.WorkerFailure("worker_failed")

    monkeypatch.setattr(worker_process.WorkerSession, "exchange", failed)
    with pytest.raises(AuditError, match="failed"):
        scanner.supervised(body, 1)
    monkeypatch.setattr(worker_process.WorkerSession, "exchange", lambda *_args: b'{"units":2}')
    with pytest.raises(AuditError, match="fields"):
        scanner.supervised(body, 1)


def test_environment_secret_is_not_retained_in_private_diagnostics(state, monkeypatch) -> None:
    secret = "synthetic-exact-credential-material"
    monkeypatch.setenv("OCR_LLM_TOKEN", secret)
    identity = captured(state, f"value = '{secret}'\n")
    run_id, run = run_in_process(state, identity, monkeypatch)
    assert run["hits"] and all(hit["reason"] == "secret" for hit in run["hits"])
    for path in state.path.iterdir():
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
    assert scanner.load_run(state, run_id) == run


def test_private_file_permissions_size_and_concurrent_change(state, monkeypatch) -> None:
    target = state.path / "probe"
    target.write_bytes(b"old")
    target.chmod(0o644)
    with pytest.raises(AuditError, match="unsafe private file"):
        state_module.read_regular(state.fd, target.name, 10)
    target.chmod(0o600)
    with pytest.raises(AuditError, match="unsafe private file"):
        state_module.read_regular(state.fd, target.name, 2)
    original = os.read

    def moving(fd, length):
        result = original(fd, length)
        if result:
            target.write_bytes(b"new-value")
        return result

    monkeypatch.setattr(state_module.os, "read", moving)
    with pytest.raises(AuditError, match="changed"):
        state_module.read_regular(state.fd, target.name, 10)


def test_state_rejects_invalid_lock_key_and_nonempty_initialization(tmp_path) -> None:
    root = tmp_path.resolve()
    for kind in ("lock", "key", "foreign"):
        directory = root / kind
        directory.mkdir(mode=0o700)
        target = directory / kind
        target.write_bytes(b"invalid")
        target.chmod(0o644 if kind == "lock" else 0o600)
        with pytest.raises(AuditError):
            State(directory, create=True)


def test_state_document_bounds_kinds_and_raw_permissions(state, monkeypatch) -> None:
    with pytest.raises(AuditError, match="identity"):
        state_module.identifier("../escape")
    for operation in (state.load, state.save):
        with pytest.raises(AuditError, match="kind"):
            operation("future", "a" * 32, *([{}] if operation == state.save else []))
    with monkeypatch.context() as patch:
        patch.setattr(state_module, "MAX_DOCUMENT", 8)
        with pytest.raises(AuditError, match="limit"):
            state_module.decode(b" " * 9)
        with pytest.raises(AuditError, match="limit"):
            state.save("run", "d" * 32, {"large": "document"})
    identity = captured(state, "source\n")
    directory = state.path / f"raw-{identity}"
    directory.chmod(0o755)
    with pytest.raises(AuditError, match="unsafe raw"):
        state.raw_directory(identity)
    directory.chmod(0o700)


def test_source_file_bounds_and_change_during_read(state, tmp_path, monkeypatch) -> None:
    root = tmp_path.resolve() / "source"
    (root / "nested").mkdir(parents=True)
    source = root / "nested/file.py"
    source.write_bytes(b"amount = 1\n")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert corpus_module.selected_file(descriptor, "nested/file.py") == source.read_bytes()
        with monkeypatch.context() as patch:
            patch.setattr(corpus_module, "MAX_FILE", 3)
            with pytest.raises(AuditError, match="file size limit"):
                corpus_module.selected_file(descriptor, "nested/file.py")
        original = os.read

        def moving(fd, length):
            value = original(fd, length)
            if value:
                source.write_bytes(b"changed source content\n")
            return value

        with monkeypatch.context() as patch:
            patch.setattr(corpus_module.os, "read", moving)
            with pytest.raises(AuditError, match="changed during capture"):
                corpus_module.selected_file(descriptor, "nested/file.py")
    finally:
        os.close(descriptor)


def test_binary_and_sparse_inputs_use_content_and_metadata_not_extensions(
    state, tmp_path, monkeypatch
) -> None:
    root = tmp_path.resolve() / "input"
    root.mkdir()
    sparse = root / "large.txt"
    with sparse.open("wb") as stream:
        stream.truncate(8 * 1024**3)
    (root / "binary.py").write_bytes(b"\x00\xffbinary-payload")
    (root / "text.png").write_text("amount = 17\n")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:

        def forbidden_read(*_args):
            raise AssertionError("oversize body must not be read")

        with monkeypatch.context() as patch:
            patch.setattr(corpus_module.os, "read", forbidden_read)
            with pytest.raises(corpus_module.InputSkipped, match="size limit"):
                corpus_module.selected_file(descriptor, sparse.name)
    finally:
        os.close(descriptor)
    identity = corpus_module.capture(
        state,
        root=root,
        paths=["large.txt", "binary.py", "text.png"],
        deadline=time.monotonic() + 30,
    )
    value = corpus_module.manifest(state, identity)
    files = {item["path"]: item for item in value["files"]}
    assert files["large.txt"]["error"] == "oversize_input"
    assert files["binary.py"]["error"] == "binary input"
    assert files["text.png"]["error"] is None
    requests = []

    def evaluate_text_only(body, _timeout, **_kwargs):
        requests.append(body["source"])
        return scanner.evaluate(body)

    monkeypatch.setattr(scanner, "supervised", evaluate_text_only)
    _, result = scanner.scan(state, identity, deadline=time.monotonic() + 30)
    assert requests == ["amount = 17\n"]
    assert not result["complete"] and len(result["errors"]) == 2 and result["units"] == 2
    raw_fd = state.raw_directory(identity)
    try:
        assert os.listdir(raw_fd) == [files["text.png"]["slot"]]
    finally:
        os.close(raw_fd)


def test_capture_limits_fail_before_raw_writes(state, tmp_path, monkeypatch) -> None:
    inputs = tmp_path.resolve() / "inputs"
    inputs.mkdir()
    for constant, value, text in (("MAX_FILES", 0, "x"), ("MAX_UNITS", 1, "x\n")):
        with monkeypatch.context() as patch:
            patch.setattr(corpus_module, constant, value)
            with pytest.raises(AuditError, match="limit"):
                captured(state, text)
    with pytest.raises(AuditError, match="time limit"):
        corpus_module.capture(state, snippet=b"x", deadline=time.monotonic() - 1)
    with pytest.raises(AuditError, match="conflicting"):
        corpus_module.capture(
            state, root=tmp_path.resolve(), snippet=b"x", deadline=time.monotonic() + 30
        )
    for paths in ([], ["duplicate", "duplicate"]):
        with pytest.raises(AuditError, match="selection"):
            corpus_module.capture(state, root=inputs, paths=paths, deadline=time.monotonic() + 30)
    assert not list(state.path.glob("raw-*"))


@pytest.mark.parametrize(
    "mutation",
    [
        "storage",
        "source-storage",
        "origin-kind",
        "snippet-root",
        "relative-root",
        "git-revision",
        "non-git-revision",
        "duplicate-file",
        "member-units",
        "population",
    ],
)
def test_authenticated_corpus_is_still_schema_checked(state, mutation) -> None:
    identity = captured(state, "safe source\n")
    original = corpus_module.manifest(state, identity)
    value = deepcopy(original)
    if mutation == "storage":
        value["storage"] = "unknown"
    elif mutation == "source-storage":
        value["storage"] = "original"
    elif mutation == "origin-kind":
        value["origin"]["kind"] = "unknown"
    elif mutation == "snippet-root":
        value["origin"]["root"] = "/unexpected"
    elif mutation == "relative-root":
        value["origin"] = {"kind": "files", "root": "relative", "revision": None}
    elif mutation == "git-revision":
        value["origin"] = {"kind": "git", "root": "/synthetic", "revision": "not-a-commit"}
    elif mutation == "non-git-revision":
        value["origin"] = {"kind": "files", "root": "/synthetic", "revision": "a" * 40}
    elif mutation == "duplicate-file":
        value["files"].append(deepcopy(value["files"][0]))
    elif mutation == "member-units":
        value["files"][0]["units"] = True
    else:
        value["units"] += 1
    state.save("corpus", identity, value)
    try:
        with pytest.raises(AuditError):
            corpus_module.manifest(state, identity)
    finally:
        state.save("corpus", identity, original)


def test_worker_entrypoint_checks_resource_limits_and_suppresses_input(state, monkeypatch) -> None:
    identity = captured(state, "amount = 1\n")
    body = request(state, identity)
    limits = []
    output = io.BytesIO()
    with monkeypatch.context() as patch:
        patch.setattr(
            scanner.resource, "setrlimit", lambda kind, bound: limits.append((kind, bound))
        )
        patch.setattr(
            sys,
            "stdin",
            SimpleNamespace(
                buffer=io.BytesIO(worker_process.frame(b"0" * 16 + state_module.encode(body)))
            ),
        )
        patch.setattr(sys, "stdout", SimpleNamespace(buffer=output))
        assert scanner.worker() == 0
    assert (
        state_module.decode(worker_process.read_request(io.BytesIO(output.getvalue()))[16:])[
            "units"
        ]
        == 2
    )
    assert (scanner.resource.RLIMIT_CORE, (0, 0)) in limits
    assert (
        scanner.resource.RLIMIT_FSIZE,
        (state_module.MAX_DOCUMENT, state_module.MAX_DOCUMENT),
    ) in limits
    for bad in (
        b"malformed-secret-input",
        state_module.encode({**body, "scanner": "stale"}),
        state_module.encode({**body, "item": {**body["item"], "units": 1}}),
    ):
        output = io.BytesIO()
        with monkeypatch.context() as patch:
            patch.setattr(scanner.resource, "setrlimit", lambda *_args: None)
            patch.setattr(
                sys,
                "stdin",
                SimpleNamespace(buffer=io.BytesIO(worker_process.frame(b"0" * 16 + bad))),
            )
            patch.setattr(sys, "stdout", SimpleNamespace(buffer=output))
            assert scanner.worker() == 2
        assert output.getvalue() == b""


def test_loading_many_files_and_hits_has_linear_work_bound(state, monkeypatch) -> None:
    identity = "e" * 32
    files = [
        {
            "slot": f"{number:032x}",
            "path": f"source-{number}.py",
            "digest": f"{number:064x}",
            "units": 1,
            "lines": 1,
            "error": None,
        }
        for number in range(1000)
    ]
    state.save(
        "corpus",
        identity,
        {
            "origin": {"kind": "files", "root": "/synthetic", "revision": None},
            "files": files,
            "units": 1000,
            "bytes": 1000,
            "storage": "snapshot",
            "raw_removed": True,
        },
    )
    hits = [
        {
            "id": scanner._unit_id(state.key, identity, item, 0, role),
            "slot": item["slot"],
            "unit": 0,
            "role": role,
            "reason": "secret",
            "detector": "normalized",
            "proof": False,
        }
        for item in files
        for role in ("text", "existing_code")
    ]
    run_id = "f" * 32
    state.save(
        "run",
        run_id,
        {
            "corpus": identity,
            "scanner": scanner.scanner_identity(),
            "profile": scanner.PROFILE,
            "secret_set": scanner.secret_fingerprint(state),
            "units": 1000,
            "expected_units": 1000,
            "execution": scanner.ExecutionLimits().record(),
            "proven_rejections": 0,
            "complete": True,
            "errors": [],
            "hits": hits,
        },
    )
    visits = 0

    class BoundedFiles(list):
        def __iter__(self):
            nonlocal visits
            for item in super().__iter__():
                visits += 1
                assert visits <= 6 * len(files) + 4 * len(hits), (
                    "file traversal exceeded linear bound"
                )
                yield item

    original = scanner.manifest

    def counted(*args):
        value = original(*args)
        return {**value, "files": BoundedFiles(value["files"])}

    monkeypatch.setattr(scanner, "manifest", counted)
    assert len(scanner.load_run(state, run_id)["hits"]) == 2000


@given(st.text(max_size=200))
def test_duplicate_key_and_keyed_identity_properties(value: str) -> None:
    encoded = json.dumps(value)
    with pytest.raises(AuditError):
        state_module.decode(f'{{"input":{encoded},"input":{encoded}}}'.encode())
    first, second = b"a" * 32, b"b" * 32
    assert scanner.mac(first, value) == scanner.mac(first, value)
    assert scanner.mac(first, value) != scanner.mac(second, value)
    assert scanner.mac(first, value, "text") != scanner.mac(first, value, "existing_code")


@given(st.sampled_from(["../escape", "/absolute", "a//b", "a/./b", "a\\b", "a/../b", "\x00"]))
def test_unsafe_source_locators_never_reach_filesystem(value: str) -> None:
    with pytest.raises(AuditError):
        corpus_module.relative_path(value)


@given(
    seconds=st.integers(1, 86400),
    file_seconds=st.integers(1, 3600),
    git_seconds=st.integers(1, 3600),
)
def test_execution_settings_round_trip_without_changing_detector_identity(
    seconds, file_seconds, git_seconds
) -> None:
    from ocr_toolkit.dlp_audit.limits import ExecutionLimits

    limits = ExecutionLimits(seconds, file_seconds, git_seconds)
    assert ExecutionLimits.parse(limits.record()) == limits
    assert limits.record()["workers"] == 1


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), 86401])
def test_invalid_execution_settings_fail_closed(value) -> None:
    with pytest.raises(AuditError):
        scanner.ExecutionLimits(seconds=value)
    with pytest.raises(AuditError):
        scanner.ExecutionLimits.parse({**scanner.ExecutionLimits().record(), "workers": value})


def test_file_budget_and_lazy_source_acquisition(state, tmp_path, monkeypatch) -> None:
    root = tmp_path.resolve() / "sources"
    root.mkdir()
    for name in ("a.py", "b.py", "c.py"):
        (root / name).write_text("amount = 1\n")
    identity = corpus_module.capture(
        state, root=root, paths=["a.py", "b.py", "c.py"], deadline=time.monotonic() + 30
    )
    events = []
    original = scanner.read_source

    def reading(*args):
        events.append(("read", args[-1]["path"]))
        return original(*args)

    def evaluating(body, timeout, **_kwargs):
        assert 0 < timeout <= 7
        events.append(("evaluate", body["item"]["path"]))
        if body["item"]["path"] == "b.py":
            raise scanner.ScanFailure("worker_timeout")
        return scanner.evaluate(body)

    monkeypatch.setattr(scanner, "read_source", reading)
    monkeypatch.setattr(scanner, "supervised", evaluating)
    run_id, result = scanner.scan(
        state,
        identity,
        deadline=time.monotonic() + 30,
        limits=scanner.ExecutionLimits(file_seconds=7),
    )
    assert events == [
        (operation, name) for name in ("a.py", "b.py", "c.py") for operation in ("read", "evaluate")
    ]
    assert not result["complete"] and result["units"] == 4
    assert result["errors"][0]["reason"] == "worker_timeout"
    assert result["execution"]["file_seconds"] == 7
    assert scanner.load_run(state, run_id) == result


def test_output_budget_discards_entire_file_and_does_not_read_tail(
    state, tmp_path, monkeypatch
) -> None:
    root = tmp_path.resolve() / "sources"
    root.mkdir()
    for name in ("a.py", "b.py", "c.py"):
        (root / name).write_text('token = "synthetic-literal-value"\n')
    identity = corpus_module.capture(
        state, root=root, paths=["a.py", "b.py", "c.py"], deadline=time.monotonic() + 30
    )
    seen = []

    def evaluating(body, _timeout, **_kwargs):
        seen.append(body["item"]["path"])
        return scanner.evaluate(body)

    monkeypatch.setattr(scanner, "supervised", evaluating)
    monkeypatch.setattr(scanner, "MAX_HITS", 5)
    run_id, result = scanner.scan(state, identity, deadline=time.monotonic() + 30)
    assert seen == ["a.py", "b.py"]
    assert result["units"] == 2 and len(result["hits"]) == 4
    assert [error["reason"] for error in result["errors"]] == ["output_budget"] * 2
    assert not result["complete"] and scanner.load_run(state, run_id) == result


def test_generation_and_admission_enforce_record_and_byte_budgets(state, monkeypatch) -> None:
    identity = captured(state, 'token = "synthetic-credential-value"\n')
    body = request(state, identity)
    hits = scanner.evaluate(body)["hits"]
    for cap in ("MAX_HITS", "MAX_HIT_BYTES"):
        with monkeypatch.context() as patch:
            patch.setattr(scanner, cap, 1)
            with pytest.raises(scanner.ScanFailure, match="output_budget"):
                scanner.evaluate(body)
            with pytest.raises(AuditError, match="population"):
                scanner.validate_hits(hits, files=[body["item"]], units=body["item"]["units"])


@pytest.mark.parametrize("failure", [scanner.ScanFailure("output_budget"), MemoryError()])
def test_worker_returns_closed_resource_failure_without_raw_values(
    state, monkeypatch, failure
) -> None:
    body = request(state, captured(state, "amount = 1\n"))

    def failing(_body):
        raise failure

    monkeypatch.setattr(scanner, "evaluate", failing)
    monkeypatch.setattr(scanner.resource, "setrlimit", lambda *_args: None)
    output = io.BytesIO()
    monkeypatch.setattr(
        sys,
        "stdin",
        SimpleNamespace(
            buffer=io.BytesIO(worker_process.frame(b"0" * 16 + state_module.encode(body)))
        ),
    )
    monkeypatch.setattr(sys, "stdout", SimpleNamespace(buffer=output))
    assert scanner.worker() == 0
    assert state_module.decode(worker_process.read_request(io.BytesIO(output.getvalue()))[16:]) == {
        "error": "worker_memory" if isinstance(failure, MemoryError) else "output_budget"
    }


@pytest.mark.parametrize("mode", ["launch", "closed", "invalid"])
def test_supervisor_operational_failures_are_closed(state, monkeypatch, mode) -> None:
    body = request(state, captured(state, "amount = 1\n"))

    def failed(*args, **kwargs):
        if mode == "launch":
            raise worker_process.WorkerFailure("worker_launch")
        return state_module.encode(
            {"error": "worker_memory" if mode == "closed" else "private-source-value"}
        )

    monkeypatch.setattr(worker_process.WorkerSession, "exchange", failed)
    with pytest.raises(AuditError) as caught:
        scanner.supervised(body, 1)
    assert "private-source-value" not in str(caught.value)


def test_actual_supervisor_timeout_reaps_its_process(state, tmp_path, monkeypatch) -> None:
    body = request(state, captured(state, "amount = 1\n"))
    pid_file = tmp_path / "worker-pid"
    native_popen = subprocess.Popen

    def controlled_peer(_command, **kwargs):
        return native_popen(
            [
                sys.executable,
                "-c",
                "import os,sys,time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)",
                str(pid_file),
            ],
            **kwargs,
        )

    monkeypatch.setattr(worker_process.subprocess, "Popen", controlled_peer)
    with pytest.raises(scanner.ScanFailure, match="worker_timeout"):
        scanner.supervised(body, 0.5)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_document_budgets_apply_before_persistence_and_annotations_stay_atomic(
    state, monkeypatch
) -> None:
    identity = captured(state, 'token = "synthetic-test-value"\n')
    run_id, run = run_in_process(state, identity, monkeypatch)
    identities = [hit["id"] for hit in run["hits"]]
    for bound in ("MAX_HITS", "MAX_HIT_BYTES"):
        with monkeypatch.context() as patch:
            patch.setattr(cli, bound, 1)
            with pytest.raises(AuditError, match="limit"):
                cli.annotate(state, run_id, identities, "expected-protection")
        assert not (state.path / f"expectations-{identity}.json").exists()
    cli.annotate(state, run_id, identities, "expected-protection")
    for bound in ("MAX_HITS", "MAX_HIT_BYTES"):
        with monkeypatch.context() as patch:
            patch.setattr(cli, bound, 1)
            with pytest.raises(AuditError):
                cli.expectations(state, identity)
    before = set(state.path.iterdir())
    monkeypatch.setattr(corpus_module, "MAX_DOCUMENT", 65537)
    with pytest.raises(AuditError, match="manifest size"):
        captured(state, "amount = 1\n")
    assert set(state.path.iterdir()) == before


def test_native_cancellation_reaps_owned_worker(tmp_path) -> None:
    pid_file = tmp_path / "child-pid"
    # This controlled peer replaces only the worker executable. Production
    # supervision owns cancellation, temporary output and the process lifecycle.
    peer = """
import subprocess, sys
from ocr_toolkit.dlp_audit.scanner import supervised
native = subprocess.Popen
def sleeping(command, **kwargs):
    return native([sys.executable, "-c", "import os,sys,time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)", sys.argv[1]], **kwargs)
subprocess.Popen = sleeping
try:
    supervised({}, 30)
except KeyboardInterrupt:
    raise SystemExit(130)
"""
    import signal

    process = subprocess.Popen(
        [sys.executable, "-I", "-c", peer, str(pid_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child = None
    try:
        until = time.monotonic() + 10
        while not pid_file.exists() and process.poll() is None and time.monotonic() < until:
            time.sleep(0.01)
        child = int(pid_file.read_text())
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=5) == 130
        with pytest.raises(ProcessLookupError):
            os.kill(child, 0)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        if child is not None:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_admitted_units_do_not_load_review_or_provider_owners(state, monkeypatch) -> None:
    import builtins

    body = request(state, captured(state, "amount = 17\n"))
    native_import = builtins.__import__

    def bounded_import(name, globals=None, locals=None, fromlist=(), level=0):
        assert not (name == "ocr_toolkit" and "review_runner" in (fromlist or ())), (
            "admitted text does not require the review execution owner"
        )
        return native_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", bounded_import)
    assert scanner.evaluate(body) == {"units": 2, "proven_rejections": 0, "hits": []}


def test_reused_native_worker_matches_fresh_workers_and_reaps(state) -> None:
    texts = ["amount = 17\n", 'token = "synthetic-literal-value"\n', "#include <stdint.h>\n"] * 4
    bodies = [request(state, captured(state, text)) for text in texts]
    started = time.monotonic()
    fresh = [scanner.supervised(body, 15) for body in bodies]
    fresh_seconds = time.monotonic() - started
    started = time.monotonic()
    with worker_process.WorkerSession() as owner:
        reused = []
        pids = set()
        for body in bodies:
            reused.append(scanner.supervised(body, 15, worker=owner))
            pids.add(owner.process.pid)
        process = owner.process
    reused_seconds = time.monotonic() - started
    assert reused == fresh and len(pids) == 1
    assert owner.process is None and process.poll() is not None
    print(
        f"12 files: fresh={fresh_seconds:.3f}s reused={reused_seconds:.3f}s speedup={fresh_seconds / reused_seconds:.2f}x"
    )


def test_delayed_duplicate_clean_response_cannot_pass_another_file(state, monkeypatch) -> None:
    safe = request(state, captured(state, "amount = 17\n"))
    rejected = request(state, captured(state, 'token = "synthetic-short-value"\n'))
    assert scanner.evaluate(rejected)["hits"] and safe["item"]["units"] == rejected["item"]["units"]
    peer = """
import json,sys
stream=sys.stdin.buffer
size=int.from_bytes(stream.read(4),'big'); first=stream.read(size)
body=json.dumps({'units':2,'proven_rejections':0,'hits':[]}).encode()
reply=first[:16]+body
sys.stdout.buffer.write(len(reply).to_bytes(4,'big')+reply); sys.stdout.buffer.flush()
size=int.from_bytes(stream.read(4),'big'); stream.read(size)
sys.stdout.buffer.write(len(reply).to_bytes(4,'big')+reply); sys.stdout.buffer.flush()
stream.read()
"""
    native = subprocess.Popen
    monkeypatch.setattr(
        worker_process.subprocess,
        "Popen",
        lambda _args, **kw: native([sys.executable, "-c", peer], **kw),
    )
    with worker_process.WorkerSession() as owner:
        assert scanner.supervised(safe, 5, worker=owner)["hits"] == []
        process = owner.process
        with pytest.raises(AuditError, match="stale"):
            scanner.supervised(rejected, 5, worker=owner)
        assert owner.process is None and process.poll() is not None


def test_worker_timeout_restarts_peer_for_next_file(state, monkeypatch) -> None:
    body = request(state, captured(state, "amount = 17\n"))
    native = subprocess.Popen
    processes = []

    def peer(command, **kwargs):
        process = native(
            [sys.executable, "-c", "import time; time.sleep(60)"] if not processes else command,
            **kwargs,
        )
        processes.append(process)
        return process

    monkeypatch.setattr(worker_process.subprocess, "Popen", peer)
    with worker_process.WorkerSession() as owner:
        with pytest.raises(scanner.ScanFailure, match="worker_timeout"):
            scanner.supervised(body, 0.1, worker=owner)
        assert owner.process is None and processes[0].poll() is not None
        assert scanner.supervised(body, 15, worker=owner)["units"] == 2
    assert len(processes) == 2 and all(process.poll() is not None for process in processes)


@pytest.mark.parametrize(
    "payload",
    [b"", b"\x00", b"\x00" * 4, (8_388_609).to_bytes(4, "big"), (3).to_bytes(4, "big") + b"a"],
)
def test_worker_request_framing_is_closed(payload) -> None:
    if not payload:
        assert worker_process.read_request(io.BytesIO(payload)) is None
    else:
        with pytest.raises(AuditError):
            worker_process.read_request(io.BytesIO(payload))


@pytest.mark.parametrize("mode", ["oversize", "empty", "truncated", "extra", "malformed", "stale"])
def test_real_peer_response_failures_are_bounded_and_reaped(state, monkeypatch, mode) -> None:
    body = request(state, captured(state, "amount = 17\n"))
    response = {
        "oversize": "(32000001).to_bytes(4,'big')",
        "empty": "b'\\0'*4",
        "truncated": "(40).to_bytes(4,'big')+nonce+b'{}'",
        "extra": "(17).to_bytes(4,'big')+nonce+b'{}'",
        "malformed": "(17).to_bytes(4,'big')+nonce+b'{'",
        "stale": "(18).to_bytes(4,'big')+b'wrong-identity!!X'+b'{}'",
    }[mode]
    peer = f"import sys; s=sys.stdin.buffer; n=int.from_bytes(s.read(4),'big'); nonce=s.read(n)[:16]; sys.stdout.buffer.write({response}); sys.stdout.buffer.flush()"
    native = subprocess.Popen
    processes = []

    def launch(_args, **kwargs):
        process = native([sys.executable, "-c", peer], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(worker_process.subprocess, "Popen", launch)
    with worker_process.WorkerSession() as owner:
        with pytest.raises(AuditError):
            scanner.supervised(body, 5, worker=owner)
        assert owner.process is None
    assert processes and all(process.poll() is not None for process in processes)


def test_streaming_transport_does_not_deadlock_full_input_and_output_pipes(monkeypatch) -> None:
    peer = """
import sys
stream=sys.stdin.buffer
size=int.from_bytes(stream.read(4),'big'); nonce=stream.read(16)
reply=nonce+b'x'*1048576
sys.stdout.buffer.write(len(reply).to_bytes(4,'big')+reply); sys.stdout.buffer.flush()
stream.read(size-16)
stream.read()
"""
    native = subprocess.Popen
    monkeypatch.setattr(
        worker_process.subprocess,
        "Popen",
        lambda _args, **kw: native([sys.executable, "-c", peer], **kw),
    )
    with worker_process.WorkerSession() as owner:
        assert owner.exchange(b"y" * 1048576, 5) == b"x" * 1048576


def test_worker_transport_budget_launch_and_dead_peer_paths(state, monkeypatch) -> None:
    with worker_process.WorkerSession() as owner:
        for raw, seconds in ((b"", 1), (b"x", 0), (b"x", float("inf"))):
            with pytest.raises(AuditError):
                owner.exchange(raw, seconds)
        with monkeypatch.context() as patch:
            patch.setattr(worker_process, "MAX_REQUEST", 16)
            with pytest.raises(AuditError):
                owner.exchange(b"x", 1)
        with monkeypatch.context() as patch:
            patch.setattr(worker_process, "MAX_DOCUMENT", 8)
            with pytest.raises(AuditError):
                worker_process.frame(b"x" * 9)

        def fail(*_args, **_kwargs):
            raise OSError("synthetic-sensitive-error")

        with monkeypatch.context() as patch:
            patch.setattr(worker_process.subprocess, "Popen", fail)
            with pytest.raises(worker_process.WorkerFailure, match="worker_launch"):
                owner.exchange(b"{}", 1)
        body = request(state, captured(state, "amount = 17\n"))
        first = scanner.supervised(body, 10, worker=owner)
        process = owner.process
        process.kill()
        process.wait()
        assert scanner.supervised(body, 10, worker=owner) == first
        assert owner.process.pid != process.pid


def test_audit_does_not_infer_code_pass_from_prose_pass(state, monkeypatch) -> None:
    from ocr_toolkit.context.code_text import TextSink
    from ocr_toolkit.context.contracts import TextBudgets
    from ocr_toolkit.context.dlp import check_text

    value = "x*ｐａｓｓｗｏｒｄ=syntheticShortCredential"  # noqa: RUF001 - distinct sink decisions
    budgets = TextBudgets(20000, 80000, 300)
    assert check_text(value, budgets=budgets, publication=True).admitted
    assert not check_text(
        value, budgets=budgets, publication=True, sink=TextSink.LITERAL_CODE
    ).admitted
    identity = captured(state, value)
    _, result = run_in_process(state, identity, monkeypatch)
    assert result["complete"]
    assert result["hits"] and {hit["role"] for hit in result["hits"]} == {"existing_code"}
