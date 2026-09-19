#!/usr/bin/env python3
"""Scan an exact Git index or public working tree before committing or pushing."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

MAX_FILE_BYTES = 20 * 1024 * 1024
PATH_RULES = {
    "user_profile_path": re.compile(r"/(?:Users|home)/[^/\s\"'<>]+/"),
    "windows_profile_path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+[\\/]", re.I),
    "local_file_url": re.compile(r"file://(?:/[^\s\"'{}]|[A-Za-z0-9.-]+/)", re.I),
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def findings(data: bytes, name: str) -> list[dict[str, object]]:
    if b"\0" in data:
        return []
    result = []
    for line, text in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
        for category, pattern in PATH_RULES.items():
            if pattern.search(text):
                result.append({"category": category, "file": name, "line": line})
    return result


def snapshot(staged: bool, destination: Path) -> list[dict[str, object]]:
    entries = git("ls-files", "--stage", "-z").split(b"\0") if staged else []
    issues: list[dict[str, object]] = []
    if staged:
        files = []
        for entry in entries:
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            mode, oid, stage = metadata.split()
            name = os.fsdecode(raw_name)
            if stage != b"0" or mode == b"160000":
                raise ValueError(
                    "unmerged index or submodule requires explicit public-content review"
                )
            size = int(git("cat-file", "-s", oid.decode()))
            if size > MAX_FILE_BYTES:
                raise ValueError("public file exceeds scan bound")
            files.append((name, git("cat-file", "blob", oid.decode())))
    else:
        names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
        files = []
        for name in sorted(set(os.fsdecode(n) for n in names.split(b"\0") if n)):
            source = Path(name)
            if source.is_symlink():
                data = os.fsencode(os.readlink(source))
            elif source.is_file():
                with source.open("rb") as stream:
                    data = stream.read(MAX_FILE_BYTES + 1)
                if len(data) > MAX_FILE_BYTES:
                    raise ValueError("public file exceeds scan bound")
            elif not source.exists():
                continue
            else:
                raise ValueError("unsupported public file type")
            files.append((name, data))
    for name, data in files:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe public path")
        issues.extend(findings(os.fsencode(name), name))
        issues.extend(findings(data, name))
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--privacy-only", action="store_true")
    args = parser.parse_args()
    try:
        root = git("rev-parse", "--show-toplevel").decode().strip()
        os.chdir(root)
        with tempfile.TemporaryDirectory(prefix="ocr-public-content-") as directory:
            issues = snapshot(args.staged, Path(directory))
            if issues:
                print(json.dumps({"success": False, "findings": issues}, indent=2))
                return 1
            if not args.privacy_only:
                result = subprocess.run(
                    [
                        "gitleaks",
                        "detect",
                        "--no-git",
                        "--source",
                        directory,
                        "--redact",
                        "--exit-code=1",
                        "--log-level=warn",
                    ],
                    check=False,
                )
                if result.returncode:
                    return result.returncode
    except (OSError, ValueError, subprocess.CalledProcessError):
        print(json.dumps({"success": False, "error": "public-content scan could not complete"}))
        return 2
    print(json.dumps({"success": True, "scope": "index" if args.staged else "public-tree"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
