#!/usr/bin/env python3
"""A ceiling that escalates rather than running unbounded, and never halts.

Why this suite exists
----------------------
`budget.py` closes a checklist line -- nothing bounded a run before it -- and
the shape most likely to be wrong is exactly the shape `chain.py`'s own suite
warns about for a different reason: a proxy quietly standing in for something
it is not. Here that risk is "tokens" -- unmeasurable from any tool in this
repository -- being reported as a plain number that reads as cost. This suite
therefore asserts the docstring says so, not just that the arithmetic is right.

The second risk is gate rows: `chain.record_gate()` writes to the very same
ledger with no `slug` field, and a naive count would let every approval and
rejection inflate a unit's own spend. Asserted directly, with a ledger that is
mostly gate rows for the one slug under test.

`spent()` and `verdict()` are pure, so most cases here are dict/list literals.
`gather()` is the IO seam and is exercised against a real temporary ledger,
written the same way `chain.record()` / `chain.record_gate()` write it.

Run: python tools/test_budget.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import budget  # noqa: E402
import chain  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def turn(slug: str, ts: str) -> dict:
    return {"kind": "turn", "slug": slug, "state": "BUILD", "ts": ts}


def gate(decision: str = "approve") -> dict:
    # Real gate rows carry no `slug` -- see `chain.record_gate()`.
    return {"kind": "gate", "gate": 1, "decision": decision, "reason": "r",
            "ts": "2026-08-10T00:00:00"}


# --- the module states its own limitation, in its own words -------------------
#
# This is not a nicety. A budget module that does not say plainly it cannot see
# tokens will be read by the next person as a cost figure, which is the exact
# defect this task exists to close.
doc = (budget.__doc__ or "").lower()
check("the docstring states this is NOT a token budget",
      "not a token budget" in doc or "not," in doc and "token" in doc,
      doc[:200])
check("the docstring states token spend is not observable here",
      "not observable" in doc or "cannot" in doc and "token" in doc,
      "expected an explicit statement that no tool here sees token spend")

# --- spent(): gate rows never count -------------------------------------------
#
# A ledger dominated by gate rows for the unit's own gate history, plus a
# handful of real turns. If a gate leaked into the count, this would report
# more turns than were actually recorded.
mixed = [turn("u", "2026-08-10T10:00:00"), gate("approve"), gate("reject"),
         turn("u", "2026-08-10T10:05:00"), gate("approve"),
         turn("u", "2026-08-10T10:12:00")]
got = budget.spent(mixed, "u")
check("gate rows are excluded from the turn count",
      got["turns"] == 3, str(got))
check("elapsed spans only the turn rows' timestamps (12 minutes)",
      got["elapsed_hours"] is not None and abs(got["elapsed_hours"] - 0.2) < 1e-9,
      str(got))

# --- spent(): another unit's turns do not leak into this one's count ----------
two_units = [turn("a", "2026-08-10T09:00:00"), turn("a", "2026-08-10T09:30:00"),
             turn("b", "2026-08-10T09:00:00")]
only_a = budget.spent(two_units, "a")
check("only the named slug's rows are counted",
      only_a["turns"] == 2, str(only_a))

# --- spent(): a real zero vs. an unmeasurable pair are different facts --------
#
# The ledger HAS turn rows -- just none for this slug. That is a genuine "this
# unit has not spent anything yet", not "nothing could be measured".
fresh_unit = budget.spent(two_units, "brand-new-slug")
check("a slug with no rows yet is a real zero, not unknown",
      fresh_unit == {"slug": "brand-new-slug", "turns": 0, "elapsed_hours": 0.0},
      str(fresh_unit))

# An empty ledger cannot answer the question at all.
empty_ledger = budget.spent([], "u")
check("an empty ledger is unmeasurable, not a zero",
      empty_ledger["turns"] is None and empty_ledger["elapsed_hours"] is None,
      str(empty_ledger))

# A ledger of gate rows only, for the SAME reason: no turn ever got recorded.
gates_only = budget.spent([gate(), gate()], "u")
check("a ledger with turn rows removed down to nothing is unmeasurable",
      gates_only["turns"] is None and gates_only["elapsed_hours"] is None,
      str(gates_only))

# No slug to narrow by at all -- "per-unit spend" cannot be answered.
no_slug = budget.spent(mixed, None)
check("no slug means unmeasurable, never a silent cross-unit sum",
      no_slug["turns"] is None and no_slug["elapsed_hours"] is None,
      str(no_slug))

# A single recorded turn spans zero elapsed time, not `None`.
single = budget.spent([turn("u", "2026-08-10T10:00:00")], "u")
check("one recorded turn is 1 turn, 0.0h elapsed -- a real answer",
      single == {"slug": "u", "turns": 1, "elapsed_hours": 0.0}, str(single))

# A corrupt timestamp does not crash the count, but does cost the elapsed span.
corrupt = budget.spent([turn("u", "not-a-timestamp"), turn("u", "also-bad")], "u")
check("turns are still counted when every timestamp is unparseable",
      corrupt["turns"] == 2, str(corrupt))
check("...but elapsed_hours is None rather than a fabricated 0.0",
      corrupt["elapsed_hours"] is None, str(corrupt))

# --- verdict(): the ceiling escalates, it is not a pass/fail gate -------------
#
# "Escalates rather than blocking" is the checklist's own wording: `over` is a
# reported fact, and nothing about calling verdict() stops, denies, or halts
# anything -- it is a pure function returning a dict.
past_turns = budget.verdict({"turns": budget.TURN_CEILING + 1, "elapsed_hours": 0.1})
check("turns past the ceiling reports over",
      past_turns["budget"] == "over", str(past_turns))
check("...and the reason names the ceiling that fired",
      str(budget.TURN_CEILING) in past_turns["reason"], past_turns["reason"])

past_elapsed = budget.verdict(
    {"turns": 1, "elapsed_hours": budget.ELAPSED_CEILING_HOURS + 0.01})
check("elapsed past the ceiling reports over",
      past_elapsed["budget"] == "over", str(past_elapsed))

at_turns = budget.verdict({"turns": budget.TURN_CEILING, "elapsed_hours": 0.0})
check("exactly at the turn ceiling does not fire (a real boundary, not off-by-one)",
      at_turns["budget"] == "within", str(at_turns))

within = budget.verdict({"turns": 1, "elapsed_hours": 0.1})
check("comfortably under both ceilings is within",
      within["budget"] == "within", str(within))

# --- verdict(): unknown is not within budget, ever ----------------------------
#
# The exact case the task names: an empty ledger's facts must report `unknown`,
# never `within` -- Article V, a fact that could not be established is not a
# pass, and reporting `within` here would be silent degradation dressed up as
# good news.
unknown_facts = budget.spent([], "u")
unknown_verdict = budget.verdict(unknown_facts)
check("an empty ledger's facts verdict as unknown, not within budget",
      unknown_verdict["budget"] == "unknown", str(unknown_verdict))

# A verdict must never call an unmeasurable pair "within" even when nothing
# fired -- that is the silent-pass Article V forbids.
half_unknown = budget.verdict({"turns": 1, "elapsed_hours": None})
check("one measurable axis under ceiling + one unmeasurable is unknown, "
      "not within", half_unknown["budget"] == "unknown", str(half_unknown))

# But an axis that DID fire still wins over an unmeasurable partner -- a real
# overrun must not be hidden behind a missing timestamp.
fired_over_unmeasurable = budget.verdict(
    {"turns": budget.TURN_CEILING + 5, "elapsed_hours": None})
check("a fired ceiling outranks an unmeasurable partner axis",
      fired_over_unmeasurable["budget"] == "over", str(fired_over_unmeasurable))

# --- gather(): the real IO seam, against a real temp ledger -------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    led = Path(d) / "chain-ledger.jsonl"

    # Written with chain.py's own functions -- not hand-crafted JSON -- so this
    # proves budget.py reads what chain.py actually produces, via
    # chain.read_ledger(), rather than a second parser of the same file.
    chain.record({"slug": "worktree-unit", "state": "BUILD",
                  "fingerprint": "f1"}, led)
    chain.record({"slug": "worktree-unit", "state": "BUILD",
                  "fingerprint": "f2"}, led)
    chain.record_gate(1, "approve", "looked fine", path=led)
    chain.record({"slug": "worktree-unit", "state": "BUILD",
                  "fingerprint": "f3"}, led)

    io_facts = budget.gather(ROOT, led, slug="worktree-unit")
    check("gather() reads a real ledger via chain.read_ledger() and excludes "
          "the gate row it just wrote",
          io_facts["turns"] == 3, str(io_facts))
    check("gather() reports how many ledger rows it read in total, gates included",
          io_facts["entries_total"] == 4, str(io_facts))

    # A ledger that does not exist yet -- the honest state of a brand-new
    # worktree that has never called `chain.py --record`.
    missing = Path(d) / "never-written.jsonl"
    absent_facts = budget.gather(ROOT, missing, slug="worktree-unit")
    check("a ledger file that does not exist reports unmeasurable, not zero",
          absent_facts["turns"] is None and absent_facts["elapsed_hours"] is None,
          str(absent_facts))

    # --- main(): exit codes, and proof it reports rather than halting --------
    #
    # A ceiling well past what three real rows could ever cross, verified by
    # forging enough turns to trip it, THEN checking main() still just returns
    # an int -- no flag file written, no exception, no call into halt.py.
    over_led = Path(d) / "over-ledger.jsonl"
    for i in range(budget.TURN_CEILING + 3):
        chain.record({"slug": "runaway", "state": "BUILD",
                      "fingerprint": f"f{i}"}, over_led)
    rc_over = budget.main(["--ledger", str(over_led), "--slug", "runaway",
                          "--root", str(ROOT)])
    check("main() exits 1 when a unit is over budget", rc_over == 1, str(rc_over))
    halt_flag = ROOT / ".claude" / "hooks" / "state" / "halt.json"
    check("crossing the ceiling never writes the kill switch's flag file -- "
          "this module reports, it does not halt",
          not halt_flag.exists())

    rc_within = budget.main(["--ledger", str(led), "--slug", "worktree-unit",
                             "--root", str(ROOT)])
    check("main() exits 0 when a unit is within budget", rc_within == 0,
          str(rc_within))

    rc_unknown = budget.main(["--ledger", str(missing), "--slug", "worktree-unit",
                              "--root", str(ROOT)])
    check("main() exits 2 when the ledger cannot answer the question",
          rc_unknown == 2, str(rc_unknown))

    # --json prints something parseable and carries the same verdict.
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_json = budget.main(["--ledger", str(led), "--slug", "worktree-unit",
                               "--root", str(ROOT), "--json"])
    parsed = json.loads(buf.getvalue())
    check("--json emits valid JSON carrying the same verdict as the plain run",
          parsed.get("budget") == "within" and rc_json == 0, buf.getvalue())


print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All budget tests passed (turn ceiling {budget.TURN_CEILING}, "
      f"elapsed ceiling {budget.ELAPSED_CEILING_HOURS}h)")
