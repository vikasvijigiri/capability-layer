#!/usr/bin/env python3
"""Run Stop finalizers in a deterministic order.

Claude Code may run multiple matching hooks concurrently.  The finalizers this
dispatches intentionally share recovery and git state, so they are exposed
through one Stop hook and sequenced here -- moved from `post-run/00-dispatch.py`
during the Notion-architecture-family rename (`stop-finalization`), still the
same single-Stop-hook shape for the same concurrency reason. `telemetry/`
carries the 5th step now that Notion names telemetry as its own family, but it
still runs last in this same sequence -- splitting it into a second, separately
registered Stop hook would let it run concurrently with these four, which is
exactly the hazard this file's own docstring has always warned against.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = Path(__file__).resolve().parents[1]
STEPS = (
    Path(__file__).with_name("03-checkpoint.py"),
    Path(__file__).with_name("06-artifact-autocommit.py"),
    Path(__file__).with_name("07-layer-drift.py"),
    Path(__file__).with_name("08-chain-continuity.py"),
    HOOKS_DIR / "telemetry" / "09-telemetry.py",
)
sys.path.insert(0, str(HOOKS_DIR))
from _hooklib import load_payload  # noqa: E402


def main() -> int:
    payload = sys.stdin.read()
    load_payload()
    env = os.environ.copy()
    env["HOOK_PAYLOAD"] = payload or env.get("HOOK_PAYLOAD", "{}")
    for step in STEPS:
        result = subprocess.run(
            [sys.executable, str(step)],
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
