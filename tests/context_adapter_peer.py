"""Standalone synthetic fixed-protocol context adapter used through real stdio."""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    raw = sys.stdin.buffer.readline()
    request = json.loads(raw)
    mode = os.environ.get("SYNTHETIC_ADAPTER_MODE", "valid")
    current = os.path.realpath(os.getcwd())
    if current != os.path.realpath(os.environ.get("HOME", "")) or current != os.path.realpath(
        os.environ.get("TMPDIR", "")
    ):
        return 20
    if os.environ.get("PATH") != "":
        return 21
    if mode == "timeout":
        time.sleep(2)
    if mode == "stderr":
        sys.stderr.write("Authorization: Bearer synthetic-private-value\n")
        return 22
    if mode == "oversize":
        sys.stdout.write("x" * 300_000)
        return 0
    response: dict[str, object] = {
        "schema_version": "ocr.context-adapter-response/v1",
        "request_id": request["request_id"],
        "run_id": request["run_id"],
        "status": "admitted",
        "canonical_object": "tenant-object-7",
        "version": "version-1",
        "expiry": 200,
        "record": {
            "descriptor": "issue",
            "digest": "a" * 64,
            "expiry": 200,
            "state": "open",
            "text": "Synthetic issue context.",
            "version": "version-1",
        },
    }
    if mode == "unavailable":
        response = {
            "schema_version": "ocr.context-adapter-response/v1",
            "request_id": request["request_id"],
            "run_id": request["run_id"],
            "status": "unavailable",
            "reason": "unavailable",
        }
    elif mode == "mismatch":
        response["request_id"] = "different-request-identity"
    elif mode == "version":
        response["record"]["version"] = "replacement"  # type: ignore[index]
    elif mode == "pii":
        response["record"]["text"] = "person@example.invalid"  # type: ignore[index]
    elif mode == "schema":
        response["record"]["provider_tool_schema"] = {"write": True}  # type: ignore[index]
    output = json.dumps(response, sort_keys=True)
    if mode == "partial":
        sys.stdout.write(output[: len(output) // 2])
    elif mode == "multiple":
        sys.stdout.write(output + "\n" + output + "\n")
    else:
        sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
