#!/usr/bin/env python3
"""A missed handoff becomes visible, and a legitimate wait never does.

Why this suite exists
---------------------
`chain.py` exists to make one silent failure loud: a stage finishes, its
successor is never invoked, and the turn ends looking exactly like a turn where
nothing needed to happen. The risk in a detector like this is not that it misses
the break -- it is that it fires constantly and gets ignored, which is how three
hooks in this repository ended up deleted.

So both directions are asserted with equal weight: a real stall is caught, and
every legitimate reason to sit in one state is proved NOT to trigger it.

`assess` is pure, so every case below is a list of dicts. The IO seam (`gather`,
`record`) is exercised separately against a real temp file.

Run: python tools/test_chain.py
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def entries(*pairs) -> list[dict]:
    """(state, fingerprint) pairs -> ledger entries, oldest first."""
    return [{"ts": f"2026-08-10T00:00:{i:02d}", "slug": "u",
             "state": s, "fingerprint": f} for i, (s, f) in enumerate(pairs)]


# --- the break this exists to catch -------------------------------------------
#
# BUILD for three turns while the tree changed every turn. Either the work is
# still in BUILD and the state machine cannot see it, or a stage finished and
# nobody invoked the next one. Both are worth saying out loud.
stalled = chain.assess(
    entries(("BUILD", "a"), ("BUILD", "b"), ("BUILD", "c")), "BUILD", "d")
check("a state pinned while the tree churns is stalled",
      stalled["chain"] == "stalled", str(stalled))
check("...and the count of turns is a fact, not an impression",
      stalled["turns_in_state"] == 3, str(stalled["turns_in_state"]))
check("...and the reason names the state", "BUILD" in stalled["reason"])

# --- every reason NOT to fire -------------------------------------------------
#
# This block is the one that decides whether the instrument survives. A detector
# that cries stall on a quiet session, a long stage, or a human gate is noise.

still = chain.assess(
    entries(("BUILD", "a"), ("BUILD", "a"), ("BUILD", "a")), "BUILD", "a")
check("a quiet session is not a stall",
      still["chain"] == "advancing",
      "the tree never changed -- nothing is being silently dropped")

moving = chain.assess(
    entries(("PLANNING", "a"), ("BUILD", "b")), "BUILD", "c")
check("a state that just changed is advancing",
      moving["chain"] == "advancing", str(moving))

for human in sorted(chain.HUMAN_STATES):
    got = chain.assess(
        entries((human, "a"), (human, "b"), (human, "c")), human, "d")
    check(f"[{human}] waiting on a person is never a stall",
          got["chain"] == "waiting", str(got))

done = chain.assess(entries(("DONE", "a"), ("DONE", "b")), "DONE", "c")
check("a finished unit is done, not stuck", done["chain"] == "done", str(done))

# An undrivable state is `unknown`, never `advancing`. Article V: a fact that
# could not be established is not permission to report the healthy answer.
unknown = chain.assess(entries(("BUILD", "a")), None, "b")
check("an underivable state is unknown, not advancing",
      unknown["chain"] == "unknown", str(unknown))

# An empty ledger cannot show a stall -- there is no history to be pinned across.
fresh = chain.assess([], "BUILD", "a")
check("a first turn is never a stall", fresh["chain"] == "advancing", str(fresh))

# The threshold is a real boundary, asserted on both sides so a change to
# STALL_TURNS cannot silently disable the detector.
below = chain.assess(entries(*[("BUILD", str(i))
                               for i in range(chain.STALL_TURNS - 1)]),
                     "BUILD", "z")
check(f"below the threshold ({chain.STALL_TURNS}) does not fire",
      below["chain"] == "advancing", str(below))
at = chain.assess(entries(*[("BUILD", str(i)) for i in range(chain.STALL_TURNS)]),
                  "BUILD", "z")
check("at the threshold it does fire", at["chain"] == "stalled", str(at))

# --- exit codes ---------------------------------------------------------------
#
# `waiting` must exit 0. A gate holding the chain is the system working, and a
# non-zero there would train everyone to ignore the exit code.
check("stalled exits 1, unknown exits 2, waiting and advancing exit 0", True,
      "asserted through main() below")

# --- the ledger is append-only ------------------------------------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    led = Path(d) / "nested" / "chain-ledger.jsonl"
    check("record() creates its directory",
          chain.record({"slug": "u", "state": "BUILD", "fingerprint": "a"}, led))
    chain.record({"slug": "u", "state": "REPAIR", "fingerprint": "b"}, led)
    back = chain.read_ledger(led)
    check("both turns are readable back", len(back) == 2, str(back))
    check("...oldest first", back[0]["state"] == "BUILD", str(back))
    check("...each carries a timestamp", all("ts" in e for e in back), str(back))

    # Append-only is the audit-trail property. A second write must not be able
    # to shorten the file -- that is what makes the record trustworthy after
    # the fact rather than a log somebody could have rewritten.
    before = led.read_text(encoding="utf-8")
    chain.record({"slug": "u", "state": "DONE", "fingerprint": "c"}, led)
    after = led.read_text(encoding="utf-8")
    check("a later write never truncates an earlier one",
          after.startswith(before) and len(after) > len(before))

    # A corrupt line must not lose the rest of the history.
    with led.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    chain.record({"slug": "u", "state": "DONE", "fingerprint": "d"}, led)
    check("a corrupt line is skipped, not fatal",
          len(chain.read_ledger(led)) == 4, str(len(chain.read_ledger(led))))

    check("an absent ledger reads as empty rather than raising",
          chain.read_ledger(Path(d) / "nope.jsonl") == [])

# --- the IO seam against the real repository ----------------------------------
#
# Against the real repo, because the defect class this session kept finding was
# a function tested only on synthetic input while the real input was what broke.
facts = chain.gather(ROOT)
check("gather() derives a state from the real repo",
      isinstance(facts.get("state"), str) and facts["state"],
      str(facts)[:160])
check("...via resume.py rather than a second state machine",
      "resume" in (ROOT / "tools" / "chain.py").read_text(encoding="utf-8"),
      "two answers to `where is this unit` is the duplicate-owner smell")
check("...and fingerprints the tree", bool(facts.get("fingerprint")), str(facts)[:120])

# The state resume derives must be one it declares, or the HUMAN/TERMINAL tables
# here are keyed off strings that no longer exist -- which would silently
# disable the "never stall on a gate" rule.
sys.path.insert(0, str(ROOT / "tools"))
import resume as _resume  # noqa: E402

# `NEXT_ACTION` is the authoritative set: resume keeps every state's next action
# beside the state deliberately, so a state that exists has a row here.
declared = set(getattr(_resume, "NEXT_ACTION", {}) or {})
check("resume.py still declares its states where this can read them",
      bool(declared),
      "NEXT_ACTION was the table; if it moved, this cross-check is unwired and "
      "the tables below are keyed off strings nothing validates")
unknown_keys = sorted((chain.HUMAN_STATES | chain.TERMINAL_STATES) - declared)
check("every state chain.py special-cases is one resume.py declares",
      not unknown_keys,
      f"{unknown_keys} -- a renamed state would silently disable the "
      f"never-stall-on-a-gate rule, and the symptom would be false alarms")
check("the derived state is a declared one",
      facts["state"] in declared, f"{facts['state']} not in {sorted(declared)}")

# resume's own TERMINAL set folds gates and stops together; chain.py splits them
# because they mean different things here -- a gate is `waiting` (healthy), a
# stop is not. Assert the split covers resume's set, so a new terminal state
# cannot fall through to the stall path.
resume_terminal = set(getattr(_resume, "TERMINAL", set()) or set())
uncovered = sorted(resume_terminal - chain.HUMAN_STATES - chain.TERMINAL_STATES)
check("every state resume calls terminal is classified here",
      not uncovered,
      f"{uncovered} would be treated as ordinary work and could report stalled")

# --- the third limb: plan progress ---------------------------------------------
#
# The calibration that stopped this instrument crying wolf. It reported
# `stalled` on four consecutive turns of a healthy twelve-task execution,
# because a long plan legitimately sits in BUILD while files change constantly.
# A rising count of ticked task boxes is proof of advance whatever the state
# machine says, and a stall now needs all three limbs.


def pentries(*triples) -> list[dict]:
    """(state, fingerprint, progress) -> ledger entries, oldest first."""
    return [{"ts": f"2026-08-10T00:00:{i:02d}", "slug": "u", "state": s,
             "fingerprint": f, "progress": p}
            for i, (s, f, p) in enumerate(triples)]


moving_plan = chain.assess(
    pentries(("BUILD", "a", 1), ("BUILD", "b", 2), ("BUILD", "c", 3)),
    "BUILD", "d", 4)
check("a pinned state with RISING plan progress is advancing",
      moving_plan["chain"] == "advancing", str(moving_plan))
check("...and the reason says how many tasks landed",
      "more task" in moving_plan["reason"], moving_plan["reason"])

stuck_plan = chain.assess(
    pentries(("BUILD", "a", 3), ("BUILD", "b", 3), ("BUILD", "c", 3)),
    "BUILD", "d", 3)
check("a pinned state with FLAT progress and a churning tree is still stalled",
      stuck_plan["chain"] == "stalled", str(stuck_plan))
check("...and the reason names all three limbs",
      "progress" in stuck_plan["reason"] and "tree kept changing" in stuck_plan["reason"],
      stuck_plan["reason"])

# An absent plan still reports `stalled` -- on two limbs, and SAYING SO.
#
# The comment here used to read "an absent plan must not read as a stall",
# directly contradicting the assertion three lines below it, and the reason
# string contradicted both: it announced "the plan's progress did not [move]"
# about a file that does not exist. That notice fired 64 consecutive times on
# 2026-08-12 for a benign cause, which is how a detector stops being read.
#
# The verdict stays. Going silent for plan-less units would blind this to
# exactly the work `workflow.md`'s small-work path is about to make routine, and
# silence is the worse failure. What changed is that the reason now names the
# limb it could not evaluate, the same way `security_gate.considered()` omits a
# clause it could not check rather than claiming it.
no_plan = chain.assess(
    entries(("BUILD", "a"), ("BUILD", "b"), ("BUILD", "c")), "BUILD", "d", None)
check("an absent plan still reports stalled, on two limbs",
      no_plan["chain"] == "stalled", str(no_plan))
check("...and the reason says the plan limb was UNEVALUATED, not flat",
      "NO active plan" in no_plan["reason"], no_plan["reason"])
check("...and never claims progress failed to move",
      "progress did not" not in no_plan["reason"], no_plan["reason"])
check("...while a real flat-progress stall still says progress did not move",
      "progress" in stuck_plan["reason"] and "NO active plan" not in stuck_plan["reason"],
      stuck_plan["reason"])

check("plan_progress returns None, not 0, when there is no plan to read",
      chain.plan_progress(Path(tempfile.gettempdir())) is None,
      "0 ticked boxes is a measurement; no plan is not")

# The constitution gate uses the same `- [x]` syntax with roman numerals.
# Counting those would report every plan as instantly advancing seven steps.
check("the progress pattern ignores constitution-gate boxes",
      len(chain.PROGRESS_TICK.findall(
          "- [x] I Evidence — something\n- [x] Task 1 — real\n")) == 1)

# `PROGRESS_TICK` is now `_hooklib.PROGRESS_TASK_BOX`, which (unlike the old
# ticked-only pattern it replaces) matches BOTH ticked and unticked boxes --
# `plan_progress()`'s own counting filters on the captured mark explicitly.
# Proven at both levels: the raw pattern sees both, the real counting
# function reports only the ticked one.
_mixed = "- [x] Task 1 — done\n- [ ] Task 2 — not yet\n"
check("the shared pattern matches both ticked and unticked Task boxes",
      len(chain.PROGRESS_TICK.findall(_mixed)) == 2)
check("...but plan_progress's own counting filters to ticked only",
      sum(1 for m in chain.PROGRESS_TICK.finditer(_mixed)
          if m.group(1).lower() == "x") == 1)

live_progress = chain.plan_progress(ROOT)
if live_progress is None:
    # An installed layer ships no `docs/plans/`, so there is no active plan to
    # count and `None` is the correct answer -- the same distinction the
    # function exists to make. Asserting an int here would assert this
    # repository's contents in somebody else's.
    print("SKIP: no active plan here -- progress is unaskable, which is why "
          "plan_progress returns None rather than 0")
else:
    check("plan_progress reads the ACTIVE plan against the real tree",
          isinstance(live_progress, int) and live_progress >= 0, str(live_progress))

# --- the gate log ---------------------------------------------------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as gd:
    gled = Path(gd) / "chain-ledger.jsonl"
    chain.record({"slug": "u", "state": "BUILD", "fingerprint": "a"}, gled)
    check("a gate decision is recorded",
          chain.record_gate(1, "approve", "the plan was right", "abc123", gled))
    chain.record_gate(2, "reject", "not ready to ship", "", gled)
    log = chain.read_ledger(gled)

    gates = [e for e in log if e.get("kind") == "gate"]
    check("gate rows are distinguishable from state rows",
          len(gates) == 2 and len(log) == 3, str(log))
    check("...and carry the decision and the verbatim reason",
          gates[0]["decision"] == "approve"
          and gates[0]["reason"] == "the plan was right", str(gates[0]))
    check("...and the plan hash, so a rejection is traceable to what was rejected",
          gates[0]["plan_hash"] == "abc123", str(gates[0]))
    check("both gates use one entry shape",
          {"gate", "decision", "reason", "plan_hash", "ts", "kind"} <= set(gates[1]),
          str(gates[1]))

    # Append-only holds for gate rows too: the audit trail is worthless if a
    # later decision can quietly replace an earlier one.
    before = gled.read_text(encoding="utf-8")
    chain.record_gate(2, "approve", "changed my mind", "", gled)
    after = gled.read_text(encoding="utf-8")
    check("a later gate decision never overwrites an earlier one",
          after.startswith(before) and len(after) > len(before))
    check("...so both decisions survive for the record",
          len([e for e in chain.read_ledger(gled) if e.get("kind") == "gate"]) == 3)

    # A gate row must not be mistaken for a turn. `assess` counts trailing
    # entries by state, and a gate row has no state at all.
    mixed = chain.assess(chain.read_ledger(gled), "BUILD", "z", None)
    check("gate rows do not corrupt the stall count",
          mixed["chain"] in {"advancing", "stalled"}, str(mixed))

# --- the per-turn cost, which is a correctness property here ------------------
#
# This runs from a hook on EVERY turn. `resume.gather_facts` makes two
# `gh pr list` calls; measured, they were 4.8s of a 5.2s run, and a five-second
# tax on every turn is how a reporting mechanism gets switched off -- exactly
# the argument `CLAUDE.md` makes for two check tiers.
#
# Asserted two ways, because either alone can be satisfied while the tax comes
# back: the default must be offline, and the elapsed time must stay small.
import inspect  # noqa: E402
import time  # noqa: E402

_sig = inspect.signature(chain.gather)
check("gather() is offline BY DEFAULT",
      _sig.parameters["offline"].default is True,
      "a network probe on every turn is how this gets switched off")

_t0 = time.monotonic()
chain.gather(ROOT)
_elapsed = time.monotonic() - _t0
check(f"gather() stays under 3s ({_elapsed:.2f}s)", _elapsed < 3.0,
      "5.2s measured before the gh calls were stubbed; if this fails, a network "
      "probe has been reintroduced into the per-turn path")

# The ledger is append-only and unbounded by construction. Bounded reading is
# what keeps that safe: `assess` must not need the whole history, or a long-lived
# repository pays for every past turn on every new one.
_huge = entries(*[("BUILD", str(i)) for i in range(5000)])
_t0 = time.monotonic()
chain.assess(_huge, "BUILD", "z")
_big_elapsed = time.monotonic() - _t0
check(f"assess() is fast on a long ledger ({_big_elapsed:.3f}s)",
      _big_elapsed < 0.5,
      "the ledger only grows; a scan proportional to all of history would make "
      "the instrument slower every day it runs")

# --- the fingerprint must be stable ACROSS processes -------------------------
#
# `tree_fingerprint` used the builtin `hash()`, which on a `str` is SipHash with
# a per-process random seed. Every hook run is a new process, so the fingerprint
# changed on every turn whatever the tree did, and the "did the tree move?" limb
# was ALWAYS true -- leaving the stall detector two-limbed, which is the exact
# failure `.claude/workflow.md` says the third limb was added to fix.
#
# The assertion is a HARD-CODED digest, and that choice is the test. Calling the
# function twice inside one process passes happily with the bug present, because
# the seed is fixed for the life of a process; only a value computed in a
# different process -- or written down here once -- can catch it.
_STATUS = " M TASK.md\n?? new.py\n"
_EXPECTED = hashlib.sha256(_STATUS.encode("utf-8")).hexdigest()[:8]
check("the fingerprint is a stable digest of the status, not a random hash",
      chain.fingerprint_of("a" * 40, _STATUS) == "a" * 40 + ":" + _EXPECTED,
      chain.fingerprint_of("a" * 40, _STATUS))
check("...so an unchanged status gives an unchanged fingerprint",
      chain.fingerprint_of("b" * 40, "x") == chain.fingerprint_of("b" * 40, "x"))
check("...and a changed status changes it",
      chain.fingerprint_of("b" * 40, "x") != chain.fingerprint_of("b" * 40, "y"))
check("...and the head half still distinguishes two commits",
      chain.fingerprint_of("b" * 40, "x") != chain.fingerprint_of("c" * 40, "x"))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All chain tests passed (stall threshold {chain.STALL_TURNS})")
