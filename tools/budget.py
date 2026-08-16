#!/usr/bin/env python3
"""Is this unit of work running past a sane length -- reported, never enforced.

    python tools/budget.py                  # the active unit's spend vs ceiling
    python tools/budget.py --slug NAME      # a named unit instead of the active one
    python tools/budget.py --ledger PATH    # read a specific ledger file
    python tools/budget.py --json

This is NOT a token budget
---------------------------
No tool available in this repository can see how many tokens a turn spent --
that number lives inside the model host, not on this machine, and nothing here
calls out to ask for it. A "budget" that quietly meant tokens while reporting a
plain integer would be read as a cost figure by the next person who sees it,
and it would be wrong: **this module counts TURNS and ELAPSED WALL TIME, and
only those.** Anyone who wants a cost number has to get it from the model
host's own usage reporting; it is not, and cannot be, derived from anything
`tools/chain.py`'s ledger recorded.

The unit is the slug
---------------------
"A unit" here is exactly what `resume.py` and `chain.py` already call one: the
work tracked under one `slug` -- one plan, one branch, one ledger's worth of
recorded turns. Not the whole repository's history and not "since forever".
`spent()` narrows to the ledger rows whose `slug` matches the unit being asked
about, the same narrowing `chain.plan_progress()` does for THIS unit's plan
rather than every plan ever written.

Gate rows are not turns
------------------------
`chain.record_gate()` appends a `kind: "gate"` row for every Gate 1 / Gate 2
decision, on the very same ledger, and it carries no `slug` of its own.
Counting a gate row as spend would mean the more scrutiny a unit gets --
a rejection, a re-submission, a second approval -- the closer to its own
ceiling it looks, which is backwards: a gate decision is a human spending
THEIR time reviewing, not the unit spending its own. Gate rows are excluded
outright, before anything else runs.

Default ceilings -- how they were measured
--------------------------------------------
Measured 2026-08-10 against this repository's own ledger
(`.claude/hooks/state/chain-ledger.jsonl`) -- the only two units it has ever
recorded, and both partial: ledger-recording itself (Task 2 of this plan)
landed mid-session today, so neither sample runs from a unit's first turn to
its last.

  * `target-workflow`      -- 6 recorded turns, 16:39:43 to 17:13:16 (0.56h)
  * `checklist-completion` -- 3 recorded turns, 21:27:49 to 21:50:07 (0.37h),
    8 of 12 plan tasks ticked at the last one -- this very unit, still in BUILD
    as this file is written

Both samples are thin and both are left-censored, so the ceiling is not fit
tightly around them. It sits at roughly 5x the larger sample on each axis,
rounded to a number a person reads at a glance.

Re-measured 2026-08-16, and the elapsed limb did not survive it
--------------------------------------------------------------
The ledger now holds 147 rows over four slugs:

  * `target-workflow`       --   6 turns,   0.56h  (left-censored)
  * `checklist-completion`  --  19 turns,  24.42h  (complete: 12/12 tasks)
  * `close-remaining-gaps`  --   2 turns,   0.43h  (approved, never started)
  * `security-gate`         -- 118 turns, 118.59h  (NOT one unit -- see below)

`checklist-completion` is the only unit that ran start to finish, and it came
in at **24.42h against a 3.0h ceiling, 8x over**, while its 19 turns sat
comfortably under 30. So the two axes disagreed about the same healthy unit,
and the turn axis was right.

That is not a calibration error, it is the wrong quantity. Wall-clock span
measures how long a person left a session open -- 19 turns of work spread
across two calendar days -- not what the unit cost. **The elapsed limb is
dropped.** It is still measured and still printed, because it is useful
context; nothing is judged against it. A limb that reports `escalate` on every
healthy unit is one people learn to ignore, and then it is worse than absent:
the same failure the three-limb stall detector was rebuilt to avoid.

The turn ceiling stays at 30 and is NOT refit from `security-gate`'s 118. That
number is an artefact of the stale-slug defect -- `resume.py` keys the unit to
the branch name, so four units' turns accumulated under one finished plan's
slug. Refitting a ceiling to a measurement error would bake the error into the
policy. Re-measure turns once two or three more units have run start to finish
under slugs that are their own.

It reports; it never halts
----------------------------
`tools/halt.py` is the kill switch (Task 3 of this plan) -- one command that
stops work from any state and leaves the tree resumable. A budget that halted
its own run on crossing a number would strand whatever edit was in flight at
the moment it crossed, exactly the failure `halt.py`'s own docstring exists to
prevent. `verdict()` returns a string, `main()` returns an exit code; neither
writes a flag file, denies a tool call, or does anything a caller must react to
beyond reading the answer.

Unknown is not within budget
------------------------------
Article V of `.claude/constitution.md`. An empty or unreadable ledger has no
turns to count and no timestamps to span -- that is not evidence the unit is
small, it is the absence of evidence, and `verdict()` reports `unknown`, never
`within`. `main()` exits 2 for that, and 2 is not 0.

It reports; it never decides
------------------------------
The same shape as `tools/scope.py` and `tools/delivery_check.py`: `spent()`
turns raw ledger rows into facts, `verdict()` is a pure function from facts to
an answer, and `gather()` is the only IO seam. Nothing here escalates, halts,
or narrows a suite; a caller reads `over` and owns what happens next.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".claude" / "hooks" / "state" / "chain-ledger.jsonl"

# `chain.record()` writes this exact format via `time.strftime`. Parsed with
# the same literal here rather than a generic ISO parser, because a ledger row
# this module cannot parse must become `None` (unmeasurable), never raise.
TS_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Turns recorded for one unit (one `slug`, gate rows excluded) before this
# reports `over` rather than `within`. See the module docstring for the
# measurement behind this number and when to re-measure it.
TURN_CEILING = 30

# Wall-clock hours between a unit's first and last recorded turn. MEASURED AND
# REPORTED, NOT JUDGED: `verdict()` does not compare against this and no caller
# should. It is kept as a named number only because the docstring above explains
# why it was retired, and a reader arriving at that section needs the value it
# is talking about. Dropped as a ceiling 2026-08-16 -- the one complete unit
# measured 24.42h against it while its turns stayed under their ceiling.
ELAPSED_CEILING_HOURS_RETIRED = 3.0


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
    """None on failure. `""` only on a real, empty success -- never conflated.

    Same shape as `chain._git` and `delivery_check._run`: a subprocess helper
    in this repository never returns `""` to mean "it did not work", because a
    caller that treats empty-string-on-failure as empty-string-on-success
    reports a clean answer for a question that was never actually asked.
    """
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _parse_ts(raw) -> datetime | None:
    """A ledger timestamp -> a `datetime`, or `None` for anything unparseable.

    Never raises. A corrupt or missing `ts` on one row must not crash the
    whole measurement -- it just cannot contribute a timestamp, the same way
    `chain.read_ledger` skips a corrupt line rather than failing the read.
    """
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw, TS_FORMAT)
    except ValueError:
        return None


def spent(entries: list[dict], slug: str | None = None) -> dict:
    """Pure. Ledger rows (as `chain.read_ledger()` returns them) -> facts.

    `entries` is the whole ledger, oldest first, gate rows and all. `slug` is
    the ONE unit being asked about -- without it, "per-unit spend" is not a
    question this can answer, so both counts come back `None` rather than
    silently summing every unit's turns into one number that describes no
    single unit at all.

    Three distinct outcomes, and they are deliberately not collapsed into two:

      * no turn rows at all (empty ledger, or a ledger of gate rows only), OR
        no slug to narrow by -> `{"turns": None, "elapsed_hours": None}`,
        because nothing could be measured;
      * turn rows exist, but none carry this slug -> `{"turns": 0,
        "elapsed_hours": 0.0}`, a REAL zero: the unit is simply new;
      * turn rows exist for this slug -> counted and spanned for real.

    The first and second look similar but are not the same fact, and
    `verdict()` treats them differently: a real zero is within budget, an
    unmeasurable pair is `unknown`.
    """
    turn_rows = [e for e in entries if e.get("kind") != "gate"]
    if not turn_rows or slug is None:
        return {"slug": slug, "turns": None, "elapsed_hours": None}

    matching = [e for e in turn_rows if e.get("slug") == slug]
    if not matching:
        return {"slug": slug, "turns": 0, "elapsed_hours": 0.0}

    turns = len(matching)
    stamps = sorted(t for t in (_parse_ts(e.get("ts")) for e in matching)
                    if t is not None)
    elapsed_hours = ((stamps[-1] - stamps[0]).total_seconds() / 3600.0
                     if stamps else None)
    return {"slug": slug, "turns": turns, "elapsed_hours": elapsed_hours}


def verdict(facts: dict) -> dict:
    """Pure. `spent()`'s facts -> `{budget, turns, elapsed_hours, reason}`.

    One axis, turns. `elapsed_hours` is still measured and still reported --
    it is useful context -- but it is no longer a ceiling anything is judged
    against. See the module docstring for the measurement that removed it.

    Article V still applies to the axis that remains: turns that could not be
    counted give `unknown`, never `within`. A ceiling that could not be checked
    is not evidence of staying under it.
    """
    turns = facts.get("turns")
    elapsed = facts.get("elapsed_hours")
    span = "unmeasured" if elapsed is None else f"{elapsed:.2f}h"

    if turns is None:
        return {"budget": "unknown", "turns": turns, "elapsed_hours": elapsed,
                "reason": "could not measure turns for this unit -- unrun, "
                          "not passed"}

    if turns > TURN_CEILING:
        return {"budget": "over", "turns": turns, "elapsed_hours": elapsed,
                "reason": f"escalate -- {turns} turn(s) past the "
                          f"{TURN_CEILING}-turn ceiling ({span} elapsed)"}

    return {"budget": "within", "turns": turns, "elapsed_hours": elapsed,
            "reason": f"{turns} turn(s) under the {TURN_CEILING}-turn ceiling "
                      f"({span} elapsed, not judged)"}


def gather(root: Path | None = None, ledger: Path | None = None,
           slug: str | None = None) -> dict:
    """The IO seam. Reads the real ledger via `chain.read_ledger()` -- never
    parses the file itself, so there are not two readers of one append-only
    log -- and resolves the active unit's slug the same way `chain.gather()`
    and `resume.py` already do, unless one was given explicitly.

    `slug` resolution, in order, stopping at the first that answers:
      1. the `slug` argument, if given;
      2. `chain.gather(root)["slug"]` -- `resume.gather_facts` run offline,
         the same derivation every other consumer of "which unit is this" uses;
      3. `resume.slug_from_branch()` on the current branch name, for the case
         where `chain.py` cannot be loaded at all but git still can answer.

    Any step that fails leaves `slug` as `None`, and `spent()` then reports
    `turns`/`elapsed_hours` as unmeasurable rather than guessing.
    """
    root = Path(root or ROOT)
    ledger_path = ledger or LEDGER

    chain_mod = _load("tools/chain.py", "chain_for_budget")
    entries = chain_mod.read_ledger(ledger_path) if chain_mod is not None else []

    if slug is None and chain_mod is not None:
        try:
            slug = chain_mod.gather(root).get("slug")
        except Exception:
            slug = None

    if slug is None:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
        if branch:
            resume_mod = _load("tools/resume.py", "resume_for_budget")
            if resume_mod is not None and hasattr(resume_mod, "slug_from_branch"):
                try:
                    slug = resume_mod.slug_from_branch(branch) or None
                except Exception:
                    slug = None

    facts = spent(entries, slug)
    facts["entries_total"] = len(entries)
    return facts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--ledger", default=None, help="a specific ledger file")
    ap.add_argument("--slug", default=None,
                    help="a named unit; inferred from the branch if omitted")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    ledger_path = Path(args.ledger).resolve() if args.ledger else None

    facts = gather(root, ledger_path, args.slug)
    result = verdict(facts)

    if args.json:
        print(json.dumps({**result, "slug": facts.get("slug"),
                          "entries_total": facts.get("entries_total")},
                         indent=2))
    else:
        print(f"budget: {result['budget']}  --  {result['reason']}")
        print(f"  unit: {facts.get('slug') or '(no slug could be established)'}")
        print(f"  {facts.get('entries_total', 0)} ledger row(s) read in total "
              f"(gate rows excluded from spend)")

    # 0 within · 1 over -- escalate, this reports, it does not halt · 2 unknown.
    # `unknown` is deliberately not 0: Article V, a fact that could not be
    # established is not a pass.
    return {"within": 0, "over": 1}.get(result["budget"], 2)


if __name__ == "__main__":
    sys.exit(main())
