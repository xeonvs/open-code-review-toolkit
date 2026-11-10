"""Exact native controls, using isolated synthetic sessions and a real API peer."""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
from pathlib import Path

import pytest

from ocr_toolkit.config_writer import write_ocr_config
from tests.test_ocr_compat import load_script


@pytest.mark.parametrize("concurrency", (None, 1, 2))
def test_native_concurrency_bounds_coverage_and_read_only_session_lookup(
    tmp_path: Path, qualified_native_ocr, concurrency: int | None
) -> None:
    binary, version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    if version != "1.13.7":
        pytest.skip("global session inspection is qualified on OCR 1.13.7")
    load_script()
    from ocr_qualification import execution, peer

    env = execution._isolated_probe_environment(tmp_path / "home")
    repo, base, _head = execution._synthetic_repo(tmp_path, env)
    for index in range(12):
        (repo / f"unit_{index:02}.py").write_text(f"value = {index}\n")
    execution._run(["git", "add", "."], cwd=repo, env=env)
    execution._run(["git", "commit", "-m", "independent files"], cwd=repo, env=env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    bound = 8 if concurrency is None else concurrency

    class Peer(peer._StubHandler):
        active = 0
        peak = 0
        lock = threading.Lock()
        filled = threading.Event()

        def do_POST(self) -> None:
            with type(self).lock:
                type(self).active += 1
                type(self).peak = max(type(self).peak, type(self).active)
                if type(self).active == bound:
                    type(self).filled.set()
            try:
                # A tool-free grouping call may time out this wait. Main groups
                # release it together and demonstrate actual parallel requests.
                type(self).filled.wait(timeout=1)
                super().do_POST()
            finally:
                with type(self).lock:
                    type(self).active -= 1

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Peer)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    write_ocr_config(
        {
            "llm": {
                "auth_token": "synthetic-token",
                "model": "synthetic-model",
                "protocol": "openai",
                "url": f"http://127.0.0.1:{server.server_port}/v1",
            },
            "telemetry": {"enabled": False},
        },
        Path(env["HOME"]) / ".opencodereview" / "config.json",
    )
    args = [
        str(binary),
        "review",
        "--from",
        base,
        "--to",
        head,
        "--format",
        "json",
        "--audience",
        "agent",
        "--effort",
        "low",
        "--max-tokens-budget",
        "0",
    ]
    if concurrency is not None:
        args.extend(("--concurrency", str(concurrency)))
    try:
        raw = execution._run(args, cwd=repo, env=env)
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    result = json.loads(raw)
    assert Peer.peak == bound
    manifest = result["manifest"]
    assert manifest["terminal_state"] == "complete"
    coverage = manifest["coverage"]
    assert coverage["selected"] == coverage["completed"]
    assert len(coverage["selected"]) == 13
    sessions = sorted((Path(env["HOME"]) / ".opencodereview" / "sessions").glob("*/*.jsonl"))
    assert len(sessions) == 1
    saved = sessions[0]
    before = saved.read_bytes()
    session_id = saved.stem
    elsewhere = tmp_path / "outside"
    elsewhere.mkdir()
    shown = json.loads(
        execution._run(
            [str(binary), "session", "show", session_id, "--json"], cwd=elsewhere, env=env
        )
    )
    assert shown["summary"]["session_id"] == session_id
    assert shown["summary"]["repo_dir"] == str(repo)
    restricted = execution._run(
        [str(binary), "session", "show", session_id, "--json", "--repo", str(repo)],
        cwd=elsewhere,
        env=env,
    )
    assert json.loads(restricted) == shown
    for args in (("missing",), (session_id, "--repo", str(elsewhere)), ("../escape",)):
        missing = subprocess.run(
            [str(binary), "session", "show", *args],
            cwd=elsewhere,
            env=env,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert missing.returncode != 0
    duplicate = saved.parent.parent / "synthetic-other-repository"
    duplicate.mkdir(mode=0o700)
    (duplicate / saved.name).write_bytes(
        before.replace(str(repo).encode(), str(elsewhere).encode())
    )
    ambiguous = subprocess.run(
        [str(binary), "session", "show", session_id],
        cwd=repo,
        env=env,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert ambiguous.returncode != 0 and b"--repo" in ambiguous.stderr
    assert saved.read_bytes() == before
    # A restricted lookup does not acquire global ambiguity or mutate saved state.
    assert (
        json.loads(
            execution._run(
                [str(binary), "session", "show", session_id, "--json", "--repo", str(repo)],
                cwd=elsewhere,
                env=env,
            )
        )
        == shown
    )
