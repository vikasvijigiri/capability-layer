#!/usr/bin/env python3
"""Run Stop finalizers in a deterministic order.

Claude Code may run multiple matching hooks concurrently.  The finalizers in
this directory intentionally share recovery and git state, so they are exposed
through one Stop hook and sequenced here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STEPS = ("03-checkpoint.py", "06-artifact-autocommit.py", "07-layer-drift.py", "08-chain-continuity.py")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402


def main() -> int:
    payload = sys.stdin.read()
    load_payload()
    env = os.environ.copy()
    env["HOOK_PAYLOAD"] = payload or env.get("HOOK_PAYLOAD", "{}")
    for name in STEPS:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name(name))],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # A finalizer must not wedge the host session.
        raise SystemExit(0) from None
