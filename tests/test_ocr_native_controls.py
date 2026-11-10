"""Exact native controls, using isolated synthetic sessions and a real API peer."""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
from io import BytesIO
from pathlib import Path

import pytest

from ocr_toolkit.config_writer import write_ocr_config
from tests.test_ocr_compat import load_script


@pytest.mark.parametrize("concurrency", (None, 1, 2))
def test_native_concurrency_bounds_coverage_and_read_only_session_lookup(
    tmp_path: Path, qualified_native_ocr, concurrency: int | None
) -> None:
    binary, version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    module = load_script()
    if module.core._version(version) < (1, 13, 7):
        pytest.skip("global session inspection was introduced in OCR 1.13.7")
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
        saturated = False

        def complete_pending(self) -> None:
            if getattr(self, "pending", False):
                with type(self).lock:
                    type(self).active -= 1
                    self.pending = False

        def send_response(self, code: int, message: str | None = None) -> None:
            # Finish accounting before headers/body can release the native caller.
            # A live handler after this boundary is no longer an outstanding request.
            self.complete_pending()
            super().send_response(code, message)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= module.settings.MAX_HTTP_BYTES:
                self.send_error(400)
                return
            raw = self.rfile.read(length)
            request = json.loads(raw)
            self.rfile = BytesIO(raw)
            names = {tool.get("function", {}).get("name") for tool in request.get("tools", [])}
            # Grouping/planning/filtering do not establish review-group saturation.
            self.pending = {"file_read", "code_comment"} <= names
            if self.pending:
                with type(self).lock:
                    type(self).active += 1
                    type(self).peak = max(type(self).peak, type(self).active)
                    if type(self).active >= bound:
                        type(self).saturated = True
                        type(self).filled.set()
            try:
                if self.pending and not type(self).filled.wait(timeout=30):
                    # Release once on an inconclusive saturation probe; avoid
                    # multiplying deadlines across every remaining request.
                    type(self).filled.set()
                super().do_POST()
            finally:
                self.complete_pending()

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
    assert Peer.peak <= bound, "native main requests exceeded the configured bound"
    assert Peer.saturated, "controlled main requests did not saturate before the probe deadline"
    assert Peer.active == 0
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
