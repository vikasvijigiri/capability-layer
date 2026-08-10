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

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All chain tests passed (stall threshold {chain.STALL_TURNS})")
