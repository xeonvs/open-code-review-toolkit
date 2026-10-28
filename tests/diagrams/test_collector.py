"""Real private filesystem and cross-process aggregation of optional output."""

from __future__ import annotations

import json
import multiprocessing
import os
import stat
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit.diagrams import collector as collector_module
from ocr_toolkit.diagrams.collector import MAX_COLLECTOR_BYTES, DiagramCollector
from ocr_toolkit.diagrams.contracts import MAX_SUBMISSION_BYTES, DiagramError
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission


@pytest.fixture
def collector(tmp_path: Path) -> DiagramCollector:
    tmp_path.chmod(0o700)
    value = DiagramCollector(tmp_path / "diagram.json", "c" * 32, REVIEW_RANGE)
    value.initialize()
    return value


def _submit_from_peer(collector: DiagramCollector) -> int:
    return collector.submit(flow_submission()).submissions


def test_identical_normalized_submissions_are_idempotent_until_global_budget(
    collector: DiagramCollector,
) -> None:
    assert collector.read().submissions == 0
    candidate = flow_submission()
    first = collector.submit(candidate)
    candidate["diagram"]["nodes"].reverse()
    for count in range(2, 9):
        snapshot = collector.submit(candidate)
        assert snapshot.submissions == count
        assert snapshot.candidate == first.candidate and snapshot.reason == "none"
    snapshot = collector.submit(candidate)
    assert snapshot.reason == "budget" and snapshot.candidate is None
    assert collector.read() == snapshot
    assert stat.S_IMODE(collector.path.stat().st_mode) == 0o600
    assert {path.name for path in collector.path.parent.glob(".diagram.json.*")} == {
        ".diagram.json.lock"
    }


def test_concurrent_collector_processes_cannot_lose_submission_counts(
    collector: DiagramCollector,
) -> None:
    with ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        counts = list(executor.map(_submit_from_peer, [collector] * 8, timeout=15))
    assert sorted(counts) == list(range(1, 9))
    snapshot = collector.read()
    assert (
        snapshot.submissions == 8 and snapshot.reason == "none" and snapshot.candidate is not None
    )


@pytest.mark.parametrize(
    "first,second", ((flow_submission, sequence_submission), (sequence_submission, flow_submission))
)
def test_conflicting_candidates_omit_in_both_arrival_orders(
    collector: DiagramCollector, first, second
) -> None:
    collector.submit(first())
    snapshot = collector.submit(second())
    assert snapshot.reason == "conflict" and snapshot.candidate is None
    # No later valid submission can repair a conflict by winning arrival order.
    assert collector.submit(first()).reason == "conflict"


def test_invalid_input_is_sticky_and_all_input_bytes_still_count(
    collector: DiagramCollector,
) -> None:
    assert collector.submit({"state": "bad"}).reason == "invalid"
    assert collector.submit(flow_submission()).reason == "invalid"
    for _attempt in range(3):
        snapshot = collector.submit("x" * 64000)
    assert snapshot.reason == "budget" and snapshot.input_bytes == MAX_SUBMISSION_BYTES + 1
    assert snapshot.candidate is None


def test_unserializable_input_exhausts_the_bound_without_retaining_data(
    collector: DiagramCollector,
) -> None:
    snapshot = collector.submit(object())
    assert snapshot.reason == "budget" and snapshot.candidate is None


def test_original_wire_whitespace_cannot_shrink_away_the_run_input_budget(
    collector: DiagramCollector,
) -> None:
    for _attempt in range(3):
        snapshot = collector.submit(flow_submission(), input_bytes=64000)
    assert snapshot.reason == "budget"
    assert snapshot.input_bytes == MAX_SUBMISSION_BYTES + 1
    assert snapshot.candidate is None


@pytest.mark.parametrize("size", (False, -1, 0))
def test_internal_wire_metrics_cannot_undercount_input(
    collector: DiagramCollector, size: int
) -> None:
    with pytest.raises(DiagramError, match="byte count"):
        collector.submit(flow_submission(), input_bytes=size)


def test_not_applicable_repeats_and_conflicts_follow_the_same_rules(
    collector: DiagramCollector,
) -> None:
    value = {
        "state": "not-applicable",
        "base_sha": REVIEW_RANGE.base,
        "head_sha": REVIEW_RANGE.head,
    }
    first = collector.submit(value)
    assert first.candidate is not None and first.candidate.diagram is None
    assert collector.submit(value).candidate == first.candidate
    assert collector.submit(flow_submission()).reason == "conflict"


@pytest.mark.parametrize(
    "field,value",
    (
        ("schema", "future"),
        ("run_id", "d" * 32),
        ("base_sha", "e" * 40),
        ("head_sha", "e" * 40),
        ("submissions", True),
        ("submissions", -1),
        ("submissions", 10),
        ("input_bytes", True),
        ("input_bytes", -1),
        ("input_bytes", MAX_SUBMISSION_BYTES + 2),
        ("reason", "model reason"),
        ("reason", "invalid"),
        ("reason", "budget"),
        ("candidate", flow_submission()),
    ),
)
def test_hostile_persistence_revalidates_exact_run_shape_and_counters(
    collector: DiagramCollector, field: str, value: object
) -> None:
    raw = json.loads(collector.path.read_text())
    raw[field] = value
    collector.path.write_text(json.dumps(raw))
    with pytest.raises(DiagramError):
        collector.read()


@pytest.mark.parametrize(
    "raw",
    (b"[]", b"{}", b"{", b"\xff", b'{"run_id":1,"run_id":2}', b"x" * (MAX_COLLECTOR_BYTES + 1)),
)
def test_malformed_json_and_oversized_persistence(collector: DiagramCollector, raw: bytes) -> None:
    collector.path.write_bytes(raw)
    with pytest.raises(DiagramError):
        collector.read()


@pytest.mark.parametrize("kind", ("symlink", "hardlink", "fifo", "directory", "public"))
def test_unsafe_file_cannot_be_read_or_replaced(
    collector: DiagramCollector, kind: str, tmp_path: Path
) -> None:
    other = tmp_path / "other"
    original = collector.path.read_bytes()
    other.write_bytes(original)
    other.chmod(0o600)
    collector.path.unlink()
    if kind == "symlink":
        collector.path.symlink_to(other)
    elif kind == "hardlink":
        os.link(other, collector.path)
    elif kind == "fifo":
        os.mkfifo(collector.path)
    elif kind == "directory":
        collector.path.mkdir()
    else:
        collector.path.write_bytes(original)
        collector.path.chmod(0o644)
    with pytest.raises((OSError, DiagramError)):
        collector.submit(flow_submission())
    assert other.read_bytes() == original


def test_run_binding_reinitialization_and_parent_safety(
    collector: DiagramCollector, tmp_path: Path
) -> None:
    with pytest.raises(DiagramError, match="already exists"):
        collector.initialize()
    with pytest.raises(DiagramError, match="different run"):
        replace(collector, run_id="d" * 32).read()
    with pytest.raises(DiagramError, match="binding"):
        DiagramCollector(Path("relative.json"), "c" * 32, REVIEW_RANGE)
    with pytest.raises(DiagramError, match="binding"):
        replace(collector, run_id="invalid")
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="unavailable"):
        replace(collector, path=missing / "diagram.json").read()
    assert not missing.exists()
    tmp_path.chmod(0o755)
    with pytest.raises(DiagramError, match="parent is not private"):
        collector.read()


def test_replaced_or_public_lock_is_rejected(collector: DiagramCollector) -> None:
    lock = collector.path.with_name(".diagram.json.lock")
    lock.chmod(0o644)
    with pytest.raises(DiagramError, match="unsafe"):
        collector.read()


def test_lock_contention_is_bounded_and_preserves_the_snapshot(collector: DiagramCollector) -> None:
    lock = collector.path.with_name(".diagram.json.lock")
    descriptor = os.open(lock, os.O_RDWR)
    original = collector.path.read_bytes()
    try:
        collector_module.flock(descriptor, collector_module.LOCK_EX)
        with pytest.raises(DiagramError, match="lock is unavailable"):
            collector.submit(flow_submission())
        assert collector.path.read_bytes() == original
    finally:
        os.close(descriptor)


def test_lock_replacement_between_open_and_acquisition_is_rejected(
    collector: DiagramCollector, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = collector_module.flock

    def replace_lock(descriptor: int, flags: int) -> None:
        original(descriptor, flags)
        lock = collector.path.with_name(".diagram.json.lock")
        lock.unlink()
        lock.touch(mode=0o600)

    monkeypatch.setattr(collector_module, "flock", replace_lock)
    with pytest.raises(DiagramError, match="lock changed"):
        collector.read()


def test_short_read_is_not_adopted_as_a_valid_snapshot(
    collector: DiagramCollector, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = collector_module.os.read
    monkeypatch.setattr(collector_module.os, "read", lambda *args: original(*args)[:-1])
    with pytest.raises(DiagramError, match="size changed"):
        collector.read()


def test_atomic_replace_failure_leaves_no_fragment_and_preserves_prior_state(
    collector: DiagramCollector, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = collector.path.read_bytes()

    def fail(*_args, **_kwargs):
        raise OSError("synthetic replacement failure")

    monkeypatch.setattr(collector_module.os, "replace", fail)
    with pytest.raises(OSError, match="replacement failure"):
        collector.submit(flow_submission())
    assert collector.path.read_bytes() == original
    assert {path.name for path in collector.path.parent.iterdir()} == {
        "diagram.json",
        ".diagram.json.lock",
    }
