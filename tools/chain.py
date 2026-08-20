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
import hashlib
import importlib.util
import json
import re
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
HUMAN_STATES = {"WAITING_PLAN_APPROVAL", "WAITING_SHIP_APPROVAL", "BLOCKED",
                "QUEUED", "WAITING_DELIVERY"}

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


# A `## Progress` box, ticked or not, requiring `Task <n>` after it: the
# constitution gate uses the same `- [x]` syntax with roman numerals, and
# counting those as progress would report every plan as advancing seven steps
# the moment it was written. `_hooklib.PROGRESS_TASK_BOX`, imported rather
# than retyped -- four sites (this one, analyze.py, git_ops.py, resume.py)
# had drifted into disagreement by defining it independently. Matches BOTH
# ticked and unticked boxes, unlike the old ticked-only pattern this replaces
# -- `plan_progress()` below does the ticked-only filtering explicitly now.
_hooklib_for_chain = _load(".claude/hooks/_hooklib.py", "hooklib_for_chain")
PROGRESS_TICK = (
    _hooklib_for_chain.PROGRESS_TASK_BOX if _hooklib_for_chain is not None
    else re.compile(r"(?m)^- \[( |x|X)\]\s+Task\s+(\d+)\b")
)


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
    return fingerprint_of(head, status)


def fingerprint_of(head: str, status: str) -> str:
    """Pure, and **deterministic across processes** -- which is the whole point.

    This was `hash(status)`, and Python's builtin `hash()` on a `str` is SipHash
    with a per-process random seed. Every hook run is a new process, so the
    fingerprint changed on every turn even when the tree was byte-identical, and
    the "did the tree move?" limb was therefore ALWAYS true.

    That is not a cosmetic bug. `.claude/workflow.md` records that a two-limb
    stall detector "reported `stalled` through four turns of a healthy twelve-task
    execution -- a detector nobody believes is worse than none", and that the
    third limb was added to fix it. With a random fingerprint the third limb
    contributed nothing and the detector was two-limbed the entire time: the
    documented fix was never in effect.

    Measured on an unchanged tree, three separate processes:

        0eb45474...:b30ad4dc
        0eb45474...:1bf90e40
        0eb45474...:e519ed51

    Same process twice, or with `PYTHONHASHSEED` pinned: identical. That is the
    signature of the defect, and it is why `test_chain.py` asserts a hard-coded
    digest -- any per-process randomness fails that assertion immediately,
    whereas comparing two calls inside ONE process passes happily.
    """
    digest = hashlib.sha256(status.encode("utf-8", "replace")).hexdigest()[:8]
    return f"{head}:{digest}"


def plan_progress(root: Path) -> int | None:
    """Ticked `## Progress` boxes in the active plan, or None if unaskable.

    Reuses `_hooklib.active_plans` so this counts THIS unit's plan rather than
    every plan ever written -- the same narrowing the minimal-diff gate needed,
    and for the same reason: a closed unit's ticks are not this one's progress.

    None, never 0, when there is no active plan. Zero ticked boxes is a real
    measurement; no plan to read is not, and collapsing them would make every
    plan-less repository look permanently stalled.
    """
    mod = _load(".claude/hooks/_hooklib.py", "hooklib_for_chain")
    if mod is None or not hasattr(mod, "active_plans"):
        return None
    try:
        plans = mod.active_plans(root)
    except Exception:
        return None
    if not plans:
        return None
    ticked = 0
    for plan in plans:
        try:
            text = Path(plan).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        ticked += sum(1 for m in PROGRESS_TICK.finditer(text)
                      if m.group(1).lower() == "x")
    return ticked


def record_gate(gate: int, decision: str, reason: str, plan_hash: str = "",
                path: Path | None = None) -> bool:
    """Append a GATE decision to the same append-only ledger.

    Both gates take a decision and neither recorded it as data -- the plan file
    carried Gate 1's approval as prose and Gate 2's was only ever in a
    transcript. One shape for both, so "what was decided, when, and why" is one
    query rather than an archaeology exercise.

    `reason` is stored **verbatim**. `tools/loop.py` refuses to re-present a plan
    body whose hash has not changed, so a summarised rejection produces a second
    submission that looks new and is not.
    """
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": "gate",
        "gate": int(gate),
        "decision": decision,
        "reason": reason,
        "plan_hash": plan_hash,
    }
    path = path or LEDGER
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        return False
    return True


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


def assess(entries: list[dict], state: str | None, fingerprint: str | None,
           progress: int | None = None) -> dict:
    """Pure. Is this unit advancing, stalled, waiting, done, or unknown?

    `entries` is the ledger oldest-first; `state`, `fingerprint` and `progress`
    are now. `progress` is the count of ticked `## Progress` boxes in the active
    plan.

    **Three limbs, not two, and the third was learned the hard way.** The first
    version asked only *has the state changed?* and *has the tree changed?* — and
    then reported `stalled` on four consecutive turns of a healthy twelve-task
    execution, because a long plan legitimately sits in `BUILD` for many turns
    while files change constantly. It was crying wolf on the very run that built
    it, which is the failure `test_chain.py`'s own docstring warns about: a
    detector nobody believes is worse than no detector.

    The missing signal was already on disk. A plan ticks a checkbox as each task
    lands, so a rising count is proof the unit is advancing whatever the state
    machine says. A stall now needs all three: the state pinned, the tree
    churning, **and** the plan's progress not moving.
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

    # Has the plan's own progress moved? Compared against the OLDEST entry in
    # the same window, so a single tick anywhere across it counts as advancing.
    # `None` on either side means the question could not be asked -- an absent
    # plan is not evidence of a stall, so it falls back to the two-limb rule.
    prior = [p for p in (e.get("progress") for e in recent)
             if isinstance(p, int)]
    progress_moved = bool(progress is not None and prior and progress > min(prior))

    if same >= STALL_TURNS and tree_moved and not progress_moved:
        # Two ways to reach here and they are not the same finding. With a plan,
        # flat ticks across a churning tree is the missed handoff this detector
        # was built for. WITHOUT a plan the third limb was never evaluated, and
        # saying "the plan's progress did not [move]" asserts a fact about a
        # file that does not exist -- which is what this notice did for 64
        # consecutive turns on 2026-08-12 while its stated cause was benign.
        #
        # Whether a plan-less unit should report `stalled` AT ALL is a genuine
        # design question, left open deliberately: `test_chain.py` says "an
        # absent plan must not read as a stall", but going silent would blind
        # the detector to exactly the units `workflow.md`'s small-work path is
        # about to make routine. Silence is the worse failure. So the verdict is
        # unchanged and only the reason is made true.
        if progress is None:
            return {"chain": "stalled", "turns_in_state": same,
                    # The caller renders this key from workflow.md. Returned
                    # rather than string-matched on the reason, because a body
                    # chosen by grepping a sentence breaks the moment the
                    # sentence is reworded -- and the reason above is prose.
                    "block": "chain-stalled-no-plan",
                    "reason": f"state has been {state} for {same} recorded "
                              f"turn(s) while the tree kept changing, and this "
                              f"unit has NO active plan -- so progress could not "
                              f"be measured and this rests on two limbs, not "
                              f"three. Either the work never had a plan to tick, "
                              f"or the state is being derived from a finished "
                              f"unit's slug"}
        return {"chain": "stalled", "turns_in_state": same,
                "block": "chain-stalled",
                "reason": f"state has been {state} for {same} recorded turn(s) "
                          f"while the tree kept changing and the plan's progress "
                          f"did not -- a stage finished and its successor was "
                          f"never invoked"}

    if progress_moved:
        # `progress_moved` is only true when both are real ints, but the type
        # checker cannot see that through the guard, and a bare `# type: ignore`
        # would hide a genuine None slipping in later.
        landed = int(progress or 0) - min(prior)
        return {"chain": "advancing", "turns_in_state": same,
                "reason": f"{state}, and the plan ticked {landed} "
                          f"more task(s) across the last {len(recent)} turn(s)"}

    return {"chain": "advancing", "turns_in_state": same,
            "reason": f"{state}, {same} recorded turn(s) in this state"}


def gather(root: Path | None = None, ledger: Path | None = None,
           offline: bool = True) -> dict:
    """The IO seam: derive the state via `resume.py`, read the ledger, fingerprint.

    **`offline=True` by default, and that default is the whole point.**
    `resume.gather_facts` makes two `gh pr list` calls, which measured 4.8s of a
    5.2s run. This is called by a hook on *every turn*, and a five-second tax on
    every turn is how a reporting mechanism gets switched off -- the same
    argument `CLAUDE.md` makes for splitting the checks into two tiers.

    Stubbing `gh` costs nothing for this module's purpose: the derived state was
    identical (`BUILD`) with and without it, because stall detection turns on
    whether the state MOVED, not on which state it is. The states that genuinely
    need PR data -- `LAND`, `QUEUED` -- are ones a stall would not be claimed in
    anyway, and a caller that needs them passes `offline=False`.
    """
    root = Path(root or ROOT)
    resume = _load("tools/resume.py", "resume_for_chain")
    state = slug = None
    if resume is not None:
        if offline:
            # Explicit, and narrow: only the network probe is stubbed. Every
            # git-derived fact is still read for real.
            resume._gh_json = lambda *a, **k: None
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
        "progress": plan_progress(root),
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
        "progress": facts.get("progress"),
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
    ap.add_argument("--gate", type=int, choices=(1, 2),
                    help="record a gate decision: 1 plan approval, 2 shipment")
    ap.add_argument("--decision", default="",
                    help="approve|revise|reject, or ship|hold|reject for gate 2")
    ap.add_argument("--reason", default="",
                    help="the user's own words, stored verbatim")
    ap.add_argument("--plan-hash", default="",
                    help="the plan body hash, so a rejection is traceable")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()

    if args.gate:
        # A decision with no reason is not a record -- "approve" alone tells a
        # later reader nothing they could not have guessed from the fact that
        # work continued.
        if not args.decision:
            print("a gate decision needs --decision", file=sys.stderr)
            return 2
        ok = record_gate(args.gate, args.decision, args.reason, args.plan_hash)
        print(f"gate {args.gate}: {args.decision}"
              + (f" -- {args.reason}" if args.reason else "")
              + ("" if ok else "  (NOT RECORDED: the ledger could not be written)"))
        return 0 if ok else 1

    facts = gather(root)

    if args.ledger:
        # Gate rows and turn rows are different shapes and must render
        # differently. The first version printed both through the turn format,
        # so every gate decision -- the rows a reader actually opens this file
        # for -- came out as `None  -`, and the audit trail was unreadable at
        # precisely the point it was worth having.
        for entry in facts["entries"]:
            ts = entry.get("ts", "?")
            if entry.get("kind") == "gate":
                reason = entry.get("reason") or ""
                print(f"{ts:20} GATE {entry.get('gate')}  "
                      f"{entry.get('decision', '?'):10}"
                      + (f"  {reason[:60]}" if reason else ""))
            else:
                ticked = entry.get("progress")
                print(f"{ts:20} {str(entry.get('state')):24} "
                      f"{entry.get('slug') or '-':22}"
                      + (f"  {ticked} task(s) done" if ticked is not None else ""))
        return 0

    verdict = assess(facts["entries"], facts["state"], facts["fingerprint"],
                     facts.get("progress"))

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
