#!/usr/bin/env python3
"""Install one local distribution through a generated hash-locked requirement."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, help="Python interpreter in the target venv")
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--requirements", required=True, type=Path)
    args = parser.parse_args()

    artifact = args.artifact.resolve(strict=True)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    args.requirements.write_text(f"{artifact.as_uri()} --hash=sha256:{digest}\n", encoding="utf-8")
    subprocess.run(
        [
            args.python,
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "--no-deps",
            "--requirement",
            str(args.requirements),
        ],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
