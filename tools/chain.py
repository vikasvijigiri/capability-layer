#!/usr/bin/env python3
"""Did the chain actually advance, or did a handoff go missing?

    python tools/chain.py                 # is this unit moving?
    python tools/chain.py --record        # append this turn's state to the ledger
    python tools/chain.py --json
    python tools/chain.py --ledger        # what has happened to this unit so far

The gap this closes
-------------------
Every skill names its successor in prose, and **nothing makes the handoff
happen**. A hook cannot invoke a skill -- that is settled in
`decisions/2026-08-04-hooks-never-name-a-skill.md` and it is not going to change
-- so the chain between Gate 1 and Gate 2 runs on the model choosing to continue.

When it does not, the failure is *silent*: the turn ends, the tree is green, and
the missing stage looks exactly like a stage that was not needed. That silence is
the whole defect. This module cannot force a transition, and does not pretend to.
It makes the break **loud**:

  * every turn's derived state is appended to an append-only ledger;
  * a unit whose state has not advanced while its tree kept changing is
    `stalled`, and the number of turns is a fact, not an impression;
  * the ledger is the audit trail -- what the system actually did, in order,
    with timestamps, queryable afterwards.

Honest about its own ceiling: `stalled` is a report. Acting on it is the
caller's, and the wording a reader sees comes from `.claude/workflow.md`, never
from here.

One state owner, not two
------------------------
`resume.py` already derives the unit's state from git facts. This imports it
rather than re-deriving, because two answers to "where is this unit" is the
duplicate-owner smell this repository deletes on sight. What is added here is
strictly the *time* dimension: resume answers "where", this answers "is it still
there, and for how long".

Names no skill
--------------
`tools/test_hook_registration.py` fails any hook that names one, and the hook
that calls this obeys the same rule: it reports a state key, and
`.claude/workflow.md` owns what that key means.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".claude" / "hooks" / "state" / "chain-ledger.jsonl"

# Turns of no state change, while the tree keeps changing, before the chain is
# called stalled.
#
# 2 rather than 1: a single stage legitimately spans several turns -- executing a
# nine-task plan sits in BUILD for a dozen. What is NOT legitimate is the tree
# changing repeatedly with the state pinned, which is what a missed handoff looks
# like from outside. 3 was tried and it reported the break two turns after a
# reader would have noticed it themselves, which is worthless.
STALL_TURNS = 2

# States a unit can sit in indefinitely without anything being wrong, because
# something outside the loop is what moves them. Never stalled.
HUMAN_STATES = {"WAITING_PLAN_APPROVAL", "WAITING_SHIP_APPROVAL", "BLOCKED", "QUEUED"}

# Terminal. A unit that reached DONE and stays there is finished, not stuck.
TERMINAL_STATES = {"DONE"}


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _git(args: list[str], root: Path) -> str | None:
    """None on failure. `""` only on a real, empty success."""
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def tree_fingerprint(root: Path) -> str | None:
    """What the tree looks like now, cheaply. None when git cannot answer.

    HEAD plus the porcelain status: a commit OR an uncommitted edit both count
    as the tree changing. Using HEAD alone would call a unit stalled through an
    entire uncommitted stage, and using status alone would miss a stage whose
    only output was a commit.
    """
    head = _git(["rev-parse", "HEAD"], root)
    status = _git(["status", "--porcelain=v1", "-uall"], root)
    if head is None or status is None:
        return None
    return f"{head}:{hash(status) & 0xffffffff:08x}"


def read_ledger(path: Path | None = None) -> list[dict]:
    """Every recorded turn, oldest first. A corrupt line is skipped, not fatal."""
    path = path or LEDGER
    if not path.is_file():
        return []
    entries = []
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    return entries


def assess(entries: list[dict], state: str | None, fingerprint: str | None) -> dict:
    """Pure. Is this unit advancing, stalled, waiting, done, or unknown?

    `entries` is the ledger oldest-first; `state` and `fingerprint` are now.
    """
    if state is None:
        return {"chain": "unknown", "turns_in_state": 0,
                "reason": "the unit's state could not be derived"}

    if state in TERMINAL_STATES:
        return {"chain": "done", "turns_in_state": 0,
                "reason": f"{state} is terminal"}

    if state in HUMAN_STATES:
        return {"chain": "waiting", "turns_in_state": 0,
                "reason": f"{state} waits on someone outside the loop, "
                          f"so time spent here is not a stall"}

    # How many consecutive trailing entries share this state?
    same = 0
    for entry in reversed(entries):
        if entry.get("state") != state:
            break
        same += 1

    # Did the tree move while the state did not? A state pinned across turns
    # with a still tree is just a quiet session; pinned while the tree churns is
    # work happening that no stage is claiming.
    recent = [e for e in entries[-(STALL_TURNS + 1):] if e.get("state") == state]
    prints = {e.get("fingerprint") for e in recent if e.get("fingerprint")}
    if fingerprint:
        prints.add(fingerprint)
    tree_moved = len(prints) > 1

    if same >= STALL_TURNS and tree_moved:
        return {"chain": "stalled", "turns_in_state": same,
                "reason": f"state has been {state} for {same} recorded turn(s) "
                          f"while the tree kept changing -- a stage finished and "
                          f"its successor was never invoked"}

    return {"chain": "advancing", "turns_in_state": same,
            "reason": f"{state}, {same} recorded turn(s) in this state"}


def gather(root: Path | None = None, ledger: Path | None = None) -> dict:
    """The IO seam: derive the state via `resume.py`, read the ledger, fingerprint."""
    root = Path(root or ROOT)
    resume = _load("tools/resume.py", "resume_for_chain")
    state = slug = None
    if resume is not None:
        # `gather_facts` then `derive_state` -- resume's own two-part seam, used
        # exactly as resume's own `main()` uses it. Calling the pair rather than
        # shelling out to `resume.py` keeps one implementation of the state
        # machine; a subprocess would parse resume's printed line and quietly
        # become a second, weaker parser of it.
        try:
            facts = resume.gather_facts(root)
            state = resume.derive_state(facts)
            slug = facts.get("slug")
        except Exception:
            state = None
    return {
        "state": state,
        "slug": slug,
        "fingerprint": tree_fingerprint(root),
        "entries": read_ledger(ledger or (root / ".claude/hooks/state/chain-ledger.jsonl")),
    }


def record(facts: dict, path: Path | None = None, note: str = "") -> bool:
    """Append one turn to the ledger. Append-only: never rewrites, never truncates.

    This is the audit trail. A line is added and nothing is ever edited, so
    "what did the system actually do" is answerable after the fact rather than
    reconstructed from a transcript nobody kept.
    """
    path = path or LEDGER
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "slug": facts.get("slug"),
        "state": facts.get("state"),
        "fingerprint": facts.get("fingerprint"),
    }
    if note:
        entry["note"] = note
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", action="store_true",
                    help="append this turn's state to the ledger")
    ap.add_argument("--note", default="", help="a note to store with --record")
    ap.add_argument("--ledger", action="store_true", help="print the ledger")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    facts = gather(root)

    if args.ledger:
        for entry in facts["entries"]:
            print(f"{entry.get('ts','?'):20} {str(entry.get('state')):24} "
                  f"{entry.get('slug') or '-'}")
        return 0

    verdict = assess(facts["entries"], facts["state"], facts["fingerprint"])

    if args.record:
        record(facts, note=args.note)

    if args.json:
        print(json.dumps({**verdict, "state": facts["state"],
                          "slug": facts["slug"]}, indent=2))
    else:
        print(f"chain: {verdict['chain']}  --  {verdict['reason']}")

    # 0 advancing/done · 1 stalled · 2 could not tell. `waiting` is 0: a gate
    # holding is the system working.
    return {"stalled": 1, "unknown": 2}.get(verdict["chain"], 0)


if __name__ == "__main__":
    sys.exit(main())
