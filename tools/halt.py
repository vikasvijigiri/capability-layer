#!/usr/bin/env python3
"""The kill switch: one command that stops work from any state.

Nothing in this layer could halt an in-flight run before this file. The
checklist asks for exactly one thing: a command that stops work, from any
state, and leaves the tree resumable.

This is the one place a *stored* fact is correct, not derived. Every other
piece of workflow state in this repository is re-derived from git facts
(`decisions/2026-08-07-derived-state-over-stored-state.md`), because a stored
copy of something git already knows just goes stale. A halt is different: it
is an *instruction* -- "stop" -- and there is no git fact that means "a human
told this to stop". So it is the one flag file in the layer, written under
`.claude/hooks/state/`, which is gitignored wholesale and therefore
machine-local: it cannot be committed by accident and does not travel with
the branch.

    python tools/halt.py --halt "reason text"
    python tools/halt.py --status
    python tools/halt.py --resume

Halting takes no destructive action -- it writes one small JSON file and
nothing else. `stop-finalization/03-checkpoint.py` already snapshots every turn, so
there is nothing to recover: resuming is just deleting the flag. The
guarantee this file exists to keep is that the working tree is byte-identical
before halt and after resume.

The guard that reads this flag lives at
`.claude/hooks/pre-tool/01-halt-guard.py` and is UNREGISTERED as of this
change -- wiring it into `.claude/settings.json` and
`.claude/hooks/hooks_registry.json` is a separate task (Task 12 of
`docs/plans/2026-08-10-checklist-completion.md`), assigned to another agent
running concurrently on those files. Firing it for real requires
`tools/run_hook.py pre-tool '<payload>'` until that registration lands.

Per `decisions/2026-08-04-hooks-never-name-a-skill.md`, neither this module
nor the guard names a skill. `.claude/workflow.md` owns what a halted state
means to the chain.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".claude" / "hooks" / "state"
HALT_FLAG = STATE_DIR / "halt.json"


def halt(reason: str) -> dict:
    """Write the halt flag. Idempotent: halting twice keeps the first reason
    stamp's `since` if the flag already exists, so a second halt call cannot
    hide how long work has actually been stopped."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    since = time.time()
    if HALT_FLAG.exists():
        try:
            existing = json.loads(HALT_FLAG.read_text(encoding="utf-8"))
            since = existing.get("since", since)
        except (OSError, ValueError):
            pass
    record = {"reason": reason, "since": since}
    HALT_FLAG.write_text(json.dumps(record), encoding="utf-8")
    return record


def status() -> dict:
    """Whether a halt is currently in effect, and why.

    Never raises: a corrupt or unreadable flag file is treated as "halted, but
    the reason is unknown" rather than crashing the caller -- the guard that
    reads this must fail toward denying, not toward silently allowing.
    """
    if not HALT_FLAG.exists():
        return {"halted": False}
    try:
        record = json.loads(HALT_FLAG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"halted": True, "reason": "unknown (halt flag unreadable)", "since": None}
    return {
        "halted": True,
        "reason": record.get("reason", "unknown"),
        "since": record.get("since"),
    }


def resume() -> bool:
    """Remove the halt flag. Returns True if a halt was actually lifted."""
    if not HALT_FLAG.exists():
        return False
    HALT_FLAG.unlink()
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--halt", metavar="REASON", help="stop work; write the flag")
    group.add_argument("--status", action="store_true", help="report halt state")
    group.add_argument("--resume", action="store_true", help="clear the flag")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.halt is not None:
        record = halt(args.halt)
        if args.json:
            print(json.dumps({"halted": True, **record}))
        else:
            print(f"Halted: {record['reason']}")
            print("Resume with: python tools/halt.py --resume")
        return 0

    if args.status:
        st = status()
        if args.json:
            print(json.dumps(st))
        elif st["halted"]:
            print(f"HALTED: {st['reason']}")
        else:
            print("not halted")
        return 0

    lifted = resume()
    if args.json:
        print(json.dumps({"resumed": lifted}))
    elif lifted:
        print("Resumed.")
    else:
        print("Not halted -- nothing to resume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
