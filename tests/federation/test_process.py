"""Production subprocess acquisition and actual descendant cleanup tests."""

import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from ocr_toolkit.federation import FederationError, parse_registry, runtime, start_gateway

PEER = Path(__file__).with_name("hostile_peer.py")


def configured(mode: str, receipt: Path) -> str:
    """Pass only synthetic mode and controlled private PID evidence to the peer."""
    return json.dumps(
        {
            "version": 2,
            "servers": {
                "synthetic": {
                    "transport": {
                        "type": "stdio",
                        "command": sys.executable,
                        "args": ["-I", str(PEER), mode, str(receipt)],
                    },
                    "tools": {"echo": {}},
                }
            },
        }
    )


def exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@pytest.mark.parametrize("mode", ["overflow", "utf8", "stderr", "unsupported"])
def test_hostile_process_fails_before_ready_and_is_reaped(tmp_path: Path, mode: str) -> None:
    pid_file = tmp_path / "pid"
    started = time.monotonic()
    with pytest.raises(FederationError):
        start_gateway(parse_registry(configured(mode, pid_file)), environment={}, run_id="a" * 32)
    assert time.monotonic() - started < 10
    assert not exists(int(pid_file.read_text()))


def test_leader_exit_does_not_skip_descendant_kill(tmp_path: Path) -> None:
    pid_file = tmp_path / "pid"
    gateway = start_gateway(
        parse_registry(configured("descendant", pid_file)), environment={}, run_id="a" * 32
    )
    parent = int(pid_file.read_text())
    child = int(Path(str(pid_file) + ".child").read_text())
    try:
        try:
            receipt = gateway.close()
            assert receipt["cleanup"] == "clean"
        except FederationError as error:
            # A still-visible reparented zombie is uncertainty, never successful cleanup.
            assert error.code == "cleanup_failed"
        deadline = time.monotonic() + 3
        while exists(child) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not exists(parent)
        assert not exists(child)
    finally:
        if exists(child):
            os.kill(child, signal.SIGKILL)


def test_gateway_preparation_uses_registry_wide_deadline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed: list[float | None] = []
    original_wait = runtime.threading.Event.wait

    def recording_wait(event: object, timeout: float | None = None) -> bool:
        observed.append(timeout)
        return original_wait(event, timeout)

    monkeypatch.setattr(runtime.threading.Event, "wait", recording_wait)
    gateway = start_gateway(
        parse_registry(configured("descendant", tmp_path / "pid")),
        environment={},
        run_id="a" * 32,
    )
    try:
        assert runtime.RUN_SECONDS in observed
    finally:
        gateway.close()
