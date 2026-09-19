"""Bounded synthetic hostile stdio peer for acquisition and process-group tests."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

mode, receipt = sys.argv[1:]
Path(receipt).write_text(str(os.getpid()))
if mode == "overflow":
    os.write(1, b"x" * (256 * 1024 + 1))
    time.sleep(5)
elif mode == "utf8":
    os.write(1, b'"\xff"\n')
    time.sleep(5)
elif mode == "stderr":
    os.write(2, b"x" * (32 * 1024 + 1))
    time.sleep(5)
elif mode == "descendant":
    child = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-c",
            "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)",
        ]
    )
    Path(receipt + ".child").write_text(str(child.pid))
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request["method"]
        if method == "server/discover":
            response = {"error": {"code": -32601, "message": "unsupported"}}
        elif method == "initialize":
            response = {
                "result": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "synthetic", "version": "1"},
                }
            }
        elif method == "tools/list":
            response = {"result": {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]}}
        else:
            response = {"result": {"content": [{"type": "text", "text": "controlled result"}]}}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], **response}), flush=True)
    # Deliberately exit first, leaving the child in the owned process group.
elif mode == "unsupported":
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"supportedVersions": ["2099-01-01"], "capabilities": {"tools": {}}},
        }
        print(json.dumps(response), flush=True)
