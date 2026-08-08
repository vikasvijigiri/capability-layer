#!/usr/bin/env python3
"""Tests for tools/loop.py -- the escalation ladder and its restore point.

The property under test is **termination**. Every path through the ladder must
reach a rung nothing automatic moves past, from any starting class and any
attempt count. A loop that can cycle is the failure mode this whole design
exists to prevent, so it is asserted by exhaustion rather than by example.

The second property is that `restore` actually restores: a tree three bad
repairs deep must come back to the commit that was last verified green, not to
some commit that merely exists.

Run: python tools/test_loop.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lp = load("tools/loop.py", "loop_mod")
hl = load(".claude/hooks/_hooklib.py", "hooklib_tl")

TERMINAL_RUNGS = {"block", "retreat"}


# --- one case per rung -------------------------------------------------------

CASES = [
    # (kind, attempt, restored, has_green, want)
    ("security", 0, False, True, "block"),
    ("security", 0, False, False, "block"),
    ("transient", 0, False, True, "retry"),
    ("transient", 1, False, True, "retry"),
    ("transient", 2, False, True, "block"),
    ("merge", 0, False, True, "rebase"),
    ("merge", 2, False, True, "retreat"),
    ("deterministic", 0, False, True, "repair"),
    ("deterministic", 2, False, True, "repair"),
    ("deterministic", 3, False, True, "restore"),
    ("deterministic", 3, True, True, "retreat"),
    ("deterministic", 3, False, False, "retreat"),
    ("unknown", 0, False, True, "repair"),
]

for kind, attempt, restored, has_green, want in CASES:
    got = lp.rung(kind, attempt, hl.failure_budget(kind), restored, has_green)
    check(f"{kind}/{attempt}{'/restored' if restored else ''}"
          f"{'' if has_green else '/no-green'} -> {want}",
          got == want, f"got {got}")

check("security never gets an attempt, whatever the count",
      all(lp.rung("security", n, 0, False, True) == "block" for n in range(6)))
check("a transient failure that outlives its budget is an outage, not noise",
      lp.rung("transient", 9, 2, False, True) == "block")
check("restore is offered once and only once",
      lp.rung("deterministic", 3, 3, False, True) == "restore"
      and lp.rung("deterministic", 3, 3, True, True) == "retreat")
check("with nothing verified to fall back to, restore is skipped",
      lp.rung("deterministic", 5, 3, False, False) == "retreat")


# --- termination, by exhaustion ---------------------------------------------
#
# Not an example: every class, every attempt count to well past any budget,
# every combination of restored/has_green. If any of these could return a rung
# that leads back to itself forever, the design's central claim is false.

KINDS = ["security", "merge", "transient", "deterministic", "unknown"]
for kind in KINDS:
    budget = hl.failure_budget(kind)
    for attempt in range(0, 12):
        for restored in (False, True):
            for has_green in (False, True):
                got = lp.rung(kind, attempt, budget, restored, has_green)
                if got not in lp.RUNG_NOTE:
                    check(f"unknown rung {got} from {kind}/{attempt}", False)
check("every rung the ladder can produce has a note", True)

for kind in KINDS:
    budget = hl.failure_budget(kind)
    # Past its budget, with restore already spent, every class must be terminal.
    end = lp.rung(kind, budget + 3, budget, restored=True, has_green=True)
    check(f"{kind} terminates once its budget and restore are spent",
          end in TERMINAL_RUNGS, f"got {end}")


# --- the gate ladder ---------------------------------------------------------
#
# A gate is not a failure and gets no retry budget -- there is no budget on a
# person's judgement, and no rung here ever proceeds without the approval. What
# IS bounded is re-asking: presenting the identical artifact again, and drafting
# a fourth version when the objection was never about the draft.

GATE_CASES = [
    (0, True, "present"),
    (1, True, "revise"),
    (2, True, "revise"),
    (3, True, "retreat"),
    (5, True, "retreat"),
    (1, False, "unchanged"),
    (2, False, "unchanged"),
    (3, False, "unchanged"),
]
for n, changed, want in GATE_CASES:
    got = lp.gate_rung(n, changed)
    check(f"gate: {n} rejection(s), {'changed' if changed else 'unchanged'} -> {want}",
          got == want, f"got {got}")

check("an unchanged plan is never re-presented, however few rejections",
      all(lp.gate_rung(n, False) == "unchanged" for n in range(1, 9)),
      "re-asking about an artifact the user already judged wastes the one "
      "resource a gate is spending")
check("every gate rung has a note", set(
    lp.gate_rung(n, c) for n in range(0, 9) for c in (True, False)
) <= set(lp.GATE_RUNG_NOTE))
check("the gate never returns a failure-ladder rung",
      not ({lp.gate_rung(n, c) for n in range(0, 9) for c in (True, False)}
           & {"retry", "repair", "restore", "block"}),
      "a rejection must not be treated as a defect")


# --- the agent-dispatch ladder ----------------------------------------------
#
# A dispatch fails in ways a check cannot: it can report that its own brief was
# incomplete, or die before reporting at all. Same property under test as the
# failure ladder -- termination by exhaustion -- but a separate table, because
# the remedies do not overlap. You cannot rebase a subagent.

AGENT_TERMINAL = {"accept", "note", "diagnose", "block"}

AGENT_CASES = [
    # (status, attempt, serialized, want)
    ("DONE", 0, False, "accept"),
    ("DONE", 5, False, "accept"),
    ("DONE_WITH_CONCERNS", 0, False, "note"),
    ("NEEDS_CONTEXT", 0, False, "supply"),
    ("NEEDS_CONTEXT", 1, False, "supply"),
    ("NEEDS_CONTEXT", 2, False, "serialize"),
    ("NEEDS_CONTEXT", 2, True, "diagnose"),
    ("BLOCKED", 0, False, "escalate"),
    ("BLOCKED", 1, False, "serialize"),
    ("BLOCKED", 1, True, "diagnose"),
    ("DIED", 0, False, "escalate"),
    ("DIED", 1, True, "diagnose"),
    # lowercase and hyphenated forms are the same status, not an unknown one
    ("done_with_concerns", 0, False, "note"),
    ("needs-context", 0, False, "supply"),
]
for status, attempt, serialized, want in AGENT_CASES:
    got = lp.agent_rung(status, attempt, serialized)
    check(f"agent: {status}/{attempt}{'/serialized' if serialized else ''} -> {want}",
          got == want, f"got {got}")

check("a success rung never depends on the attempt count",
      all(lp.agent_rung("DONE", n) == "accept" for n in range(8)))
check("BLOCKED is never retried unchanged -- the first rung escalates",
      lp.agent_rung("BLOCKED", 0) == "escalate",
      "same brief, same model, same weights is the same answer")
check("serialize is offered once and only once",
      lp.agent_rung("BLOCKED", 1, False) == "serialize"
      and lp.agent_rung("BLOCKED", 1, True) == "diagnose",
      "offering it twice is how this ladder would fail to terminate")

_AGENT_STATUSES = ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED",
                   "DIED", "", "WAT", "done", None]
for reported in _AGENT_STATUSES:
    for attempt in range(0, 10):
        for serialized in (False, True):
            got = lp.agent_rung(reported or "", attempt, serialized)
            if got not in lp.AGENT_RUNG_NOTE:
                check(f"unknown agent rung {got} from {reported!r}/{attempt}", False)
check("every agent rung the ladder can produce has a note", True)

for reported in _AGENT_STATUSES:
    end = lp.agent_rung(reported or "", 9, serialized=True)
    check(f"agent ladder terminates for {reported!r} once serialize is spent",
          end in AGENT_TERMINAL, f"got {end}")

check("an unreportable status stops rather than looping",
      lp.agent_rung("WAT", 0) == "supply" and lp.agent_rung("WAT", 1) == "block",
      "a worker that cannot report its own state is not one to keep feeding")
check("the agent ladder never returns a failure-ladder rung",
      not ({lp.agent_rung(s or "", n, z)
            for s in _AGENT_STATUSES for n in range(6) for z in (False, True)}
           & {"retry", "repair", "restore", "rebase", "retreat"}),
      "a subagent result is not a red check and must not borrow its remedies")


# --- restore against a real repository --------------------------------------


def temp_repo() -> Path:
    d = Path(tempfile.mkdtemp())
    for args in (["init", "--quiet"],
                 ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True)
    return d


def commit(d: Path, name: str, body: str) -> str:
    (d / name).write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(d), capture_output=True, text=True)
    subprocess.run(["git", "commit", "--quiet", "-m", name],
                   cwd=str(d), capture_output=True, text=True)
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(d),
                         capture_output=True, text=True)
    return out.stdout.strip()


repo = temp_repo()
good = commit(repo, "app.py", "def f():\n    return 1\n")
subprocess.run(["git", "update-ref", "refs/uaios/green/demo", good],
               cwd=str(repo), capture_output=True, text=True)

check("the green ref is readable", lp.green_sha(repo, "demo") == good)
check("an absent green ref is None, not an error",
      lp.green_sha(repo, "no-such-slug") is None)

# Three bad repairs, each committed. This is what the tree looks like when the
# budget runs out -- worse than where it started, which is why restore exists.
for n in range(3):
    commit(repo, "app.py", f"def f():\n    return {n} +\n")   # deliberately broken
check("the tree has moved away from the verified commit",
      lp.green_sha(repo, "demo") == good
      and subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                         capture_output=True, text=True).stdout.strip() != good)

ok, detail = lp.restore(repo, "demo")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                      capture_output=True, text=True).stdout.strip()
check("restore resets to the last verified-good commit", ok and head == good, detail)
check("...and the working tree is the verified content",
      (repo / "app.py").read_text(encoding="utf-8") == "def f():\n    return 1\n")
check("...and the ledger records that restore has been spent",
      lp._rs.read_ledger(repo, "demo").get("restored") is True)
check("...and the attempt count is cleared, so the re-attempt is not pre-spent",
      lp._rs.read_ledger(repo, "demo").get("attempts") == 0)

# The other half of the restore point: a tree verified and committed by hand
# never passes through the autocommit hook, so without an explicit marker a
# branch can be green all day and still have nothing to fall back to.
fresh = commit(repo, "app.py", "def f():\n    return 2\n")
ok_mark, mark_detail = lp.mark_green(repo, "demo")
check("marking green points the ref at HEAD",
      ok_mark and lp.green_sha(repo, "demo") == fresh, mark_detail)
check("...so a later restore comes back to the newer verified tree",
      lp.restore(repo, "demo")[0]
      and (repo / "app.py").read_text(encoding="utf-8") == "def f():\n    return 2\n")

ok2, detail2 = lp.restore(repo, "no-such-slug")
check("restoring with no green ref fails loudly rather than resetting to anything",
      not ok2 and "nothing verified" in detail2, detail2)


# --- next_step stays small ---------------------------------------------------
#
# The token argument only holds if the step is a step. A step that carried the
# repository would put the cost straight back.

step = lp.next_step(repo, "demo")
check("a step names the state and what is next",
      "state" in step and "next" in step, str(step))
check("a step is small", len(str(step)) < 700, f"{len(str(step))} chars")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All loop tests passed")
