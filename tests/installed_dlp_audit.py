"""Exercise the actual installed local audit CLI outside the source checkout."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Smoke-test installed command/worker delivery and remove its synthetic input."""

    if len(sys.argv) != 3:
        raise SystemExit("usage: installed_dlp_audit.py CLI PRIVATE_TEST_ROOT")
    executable = Path(sys.argv[1]).resolve(strict=True)
    root = Path(sys.argv[2]).resolve()
    root.mkdir(mode=0o700)
    state = root / "state"
    environment = {"HOME": str(root), "PATH": ""}
    completed = subprocess.run(
        [str(executable), "dlp-audit", "--state-dir", str(state), "scan", "--stdin"],
        input="amount = 17\n",
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    baseline = json.loads(completed.stdout)
    assert baseline["complete"] is True and baseline["units"] == 2
    assert baseline["rejections"] == 0 and "amount" not in completed.stdout
    assert stat.S_IMODE(state.stat().st_mode) == 0o700
    assert stat.S_IMODE((state / f"run-{baseline['run']}.json").stat().st_mode) == 0o600
    cleanup = subprocess.run(
        [str(executable), "dlp-audit", "--state-dir", str(state), "cleanup", baseline["corpus"]],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert cleanup.returncode == 0, cleanup.stderr
    assert json.loads(cleanup.stdout)["raw_removed"] is True
    assert not list(state.glob("raw-*"))
    print(json.dumps({"installed_audit": True, "private": True, "raw_removed": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
