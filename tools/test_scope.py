#!/usr/bin/env python3
"""Every veto clause is independently provable, and inverting one flips the verdict.

Why this suite exists
---------------------
"Small" and "major" decide how much checking a change gets, so under pressure the
judged answer is always "small". `scope.py` computes it from a veto list instead,
and the property that makes a veto list auditable is exactly what is asserted
here: **one clause firing is enough**, and the verdict names every clause that
fired.

The shape of each case is the same: a facts dict that fires nothing, then the
same dict with one clause's fact inverted. If the second is not `major`, that
clause is decoration. A weighted score could not be tested this way, which is
part of why it was rejected.

Run: python tools/test_scope.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


# A change that fires nothing: two code files, one container, no shared or
# control surface, both mapped.
QUIET = {
    "paths": ["tools/a.py", "tools/b.py"],
    "test_map": {"tools/*.py": "python tools/test_a.py"},
}


quiet = scope.classify(QUIET)
check("a quiet change is small", quiet["scope"] == "small", str(quiet))
check("...and names the clauses it considered",
      len(quiet["considered"]) == len(scope.CLAUSES), str(quiet["considered"]))
check("...with nothing fired", quiet["fired"] == [], str(quiet["fired"]))

# --- one case per clause, each the quiet change with one fact inverted -------
#
# The path chosen for each is a real one from this repository, so a clause that
# stops matching the layer it guards goes red here rather than silently.
INVERSIONS = {
    "shared-surface": ["tools/a.py", ".claude/project-checks.json"],
    "control-surface": ["tools/a.py", ".claude/hooks/_hooklib.py"],
    "volume": [f"tools/f{i}.py" for i in range(scope.VOLUME_LIMIT + 1)],
    "spread": ["tools/a.py", "docs/b.py"],
    "unmapped": ["src/unmapped.py"],
}

for clause, paths in INVERSIONS.items():
    facts = dict(QUIET, paths=paths)
    got = scope.classify(facts)
    check(f"[{clause}] inverting it alone flips the verdict to major",
          got["scope"] == "major", f"{got['scope']} -- fired {got['fired']}")
    check(f"[{clause}] ...and the verdict names that clause",
          clause in got["fired"], str(got["fired"]))

# Every clause must be reachable by exactly this method, or a clause exists that
# nothing above proves. This is the check that catches a clause added later
# without a case.
check("every clause has an inversion case",
      set(INVERSIONS) == set(scope.CLAUSES),
      f"untested: {sorted(set(scope.CLAUSES) - set(INVERSIONS))}; "
      f"invented: {sorted(set(INVERSIONS) - set(scope.CLAUSES))}")

# --- a veto list, not a score ------------------------------------------------
#
# Two clauses firing must not be needed, and two firing must both be named. A
# score would let one cheap signal be outvoted; this asserts it cannot.
both = scope.classify(dict(QUIET, paths=[".claude/hooks/_hooklib.py",
                                         ".claude/project-checks.json"]))
check("two clauses firing names both",
      {"shared-surface", "control-surface"} <= set(both["fired"]),
      str(both["fired"]))

# --- an absent map is named, never treated as mapped -------------------------
#
# Article V. `test_map` arrives with Task 5; before it exists the `unmapped`
# clause cannot be evaluated, and the honest report is that it did not run --
# not that everything is mapped (silently small) and not that nothing is
# (everything major, which would make the tool useless before its map lands).
no_map = scope.classify({"paths": ["tools/a.py"], "test_map": None})
check("an absent test_map does not fire unmapped",
      "unmapped" not in no_map["fired"], str(no_map["fired"]))
check("...and says the clause could not be evaluated",
      "unmapped" in no_map["skipped"], str(no_map))
check("...and the verdict is not silently small",
      no_map["scope"] == "undetermined", no_map["scope"])

# An empty change is not a small change; it is nothing to classify, and
# reporting `small` would license skipping checks on a diff nobody looked at.
empty = scope.classify({"paths": [], "test_map": {}})
check("an empty change is undetermined, not small",
      empty["scope"] == "undetermined", str(empty))

# --- the clause sources are imported, not copied -----------------------------
#
# The whole reason `shared-surface` works is that it reuses the two tables that
# already exist. A copy would drift the moment either changed -- the same defect
# as the three disagreeing commit tokenisers.
# `lstrip` takes a character SET, so `lstrip("./")` ate the leading dot and
# `./.claude/settings.json` became `claude/settings.json`, matching nothing.
# The identical defect this plan's Task 1 removed from
# `parallel_groups.normalise`, shipped again in the new file -- so both limbs
# are pinned: the prefix goes, the dot stays.
check("_norm strips a ./ prefix without eating the dot",
      scope._norm("./.claude/settings.json") == ".claude/settings.json",
      scope._norm("./.claude/settings.json"))
# Two source backslashes, which is ONE real separator. Four were written first
# and that is a doubled separator no Windows path ever produces -- the assertion
# failed against an input that cannot occur, which is a test defect wearing a
# code defect's clothes.
check("...and on backslashes",
      scope._norm(".\\.github\\workflows\\ci.yml") == ".github/workflows/ci.yml",
      scope._norm(".\\.github\\workflows\\ci.yml"))
check("a ./-prefixed control surface still fires its clause",
      scope.classify({"paths": ["./.claude/hooks/_hooklib.py"], "test_map": {}})["fired"]
      == scope.classify({"paths": [".claude/hooks/_hooklib.py"], "test_map": {}})["fired"],
      "the prefix changed the verdict, so a control surface was invisible")

check("shared-surface reuses _hooklib's migration table",
      "migrations/*" in scope._migration_patterns(),
      str(scope._migration_patterns())[:120])
check("shared-surface reuses parallel_groups' shared table",
      ".claude/project-checks.json" in scope._shared_patterns(),
      str(scope._shared_patterns())[:120])

# --- gather() is the IO seam and offline nulls it ----------------------------
root = Path(__file__).resolve().parents[1]
off = scope.gather(root, "HEAD", offline=True)
check("gather(offline=True) reports paths as unknown rather than guessing",
      off["paths"] is None, str(off)[:160])
check("...which classifies undetermined",
      scope.classify(off)["scope"] == "undetermined", str(scope.classify(off)))

live = scope.gather(root, "HEAD")
check("gather() against a real repo returns a list of paths",
      isinstance(live["paths"], list), str(live)[:160])

# --- risk tier ----------------------------------------------------------------
#
# A different question from small/major: not "how much of the repo does this
# deserve" but "how much of the pipeline may trust automation with it". Four
# things read it, and one of them decides whether a human is skipped at Gate 2 --
# so the same veto discipline applies, and `undetermined` must never be `low`.

low = scope.tier(scope.classify(QUIET), QUIET["paths"])
check("a change firing nothing is low risk", low["tier"] == "low", str(low))
check("...and nothing forced it", low["forced_by"] == [], str(low))

# One case per clause that forces a tier, each inverted alone.
for clause, expect in scope.CLAUSE_TIER.items():
    facts = dict(QUIET, paths=INVERSIONS[clause])
    got = scope.tier(scope.classify(facts), INVERSIONS[clause])
    check(f"[{clause}] alone forces {expect}", got["tier"] == expect,
          f"got {got['tier']} -- {got['reason']}")
    check(f"[{clause}] ...and is named as the reason",
          clause in got["forced_by"], str(got["forced_by"]))

# `unmapped` is deliberately NOT a tier-forcing clause: it is a gap in the test
# map, not a fact about danger. Asserted so that adding it later is a decision
# rather than a drift.
check("unmapped does not force a tier on its own",
      "unmapped" not in scope.CLAUSE_TIER,
      "an unmapped path is a coverage gap, not a risk signal")

# The highest forced tier wins, and every clause at that level is named -- an
# average would let a `medium` dilute a `high`, which is the failure a veto list
# exists to prevent.
mixed = dict(QUIET, paths=[".claude/hooks/_hooklib.py", "tools/a.py", "docs/b.py"])
got = scope.tier(scope.classify(mixed), mixed["paths"])
check("the highest forced tier wins over a lower one",
      got["tier"] == "high", str(got))
check("...and only the winning clauses are named",
      "spread" not in got["forced_by"], str(got["forced_by"]))

# Sensitive surfaces force high on their own, even when no veto clause fires.
# The installer is the one defect this project can ship into other repositories.
sens = {"paths": [".claude/install.py"], "test_map": {".claude/*.py": "x"}}
got = scope.tier(scope.classify(sens), sens["paths"])
check("a sensitive surface forces high by itself",
      got["tier"] == "high" and "sensitive-surface" in got["forced_by"], str(got))
check("...and names the path that did it",
      ".claude/install.py" in (got.get("sensitive") or []), str(got))

# Article V, at the point it matters most.
und = scope.tier({"scope": "undetermined", "fired": []}, None)
check("an undetermined change is high risk, never low",
      und["tier"] == "high", str(und))
check("...and says why", "never low-risk" in und["reason"], und["reason"])

# --- tiering a plan, before any diff exists -----------------------------------
#
# The whole point: work is tiered at planning time, so the tier can decide what
# the rest of the pipeline does. Sourced from the plan's own declaration lines
# via `_hooklib.declared_paths`' parser -- reused, not re-implemented, or the
# minimal-diff gate and the tier could disagree about what a plan declares.
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as _d:
    _plan = Path(_d) / "p.md"
    _plan.write_text(
        "# Plan\n\n### Task 1\n"
        "- Modify: `tools/quiet_one.py` — a reason mentioning `.claude/hooks/x.py`\n"
        "- Create: `tools/quiet_two.py`\n", encoding="utf-8")
    declared = scope.plan_paths(_plan)
    check("plan_paths reads the declaration lines",
          declared == ["tools/quiet_one.py", "tools/quiet_two.py"], str(declared))
    check("...and does not harvest the reason clause",
          ".claude/hooks/x.py" not in (declared or []),
          "a path named in a REASON is not declared, or every plan tiers high")

    _plan.write_text("# Plan\n\n### Task 1\n"
                     "- Modify: `.claude/hooks/_hooklib.py` — the gate\n",
                     encoding="utf-8")
    declared2 = scope.plan_paths(_plan)
    got = scope.tier(scope.classify({"paths": declared2, "test_map": {}}), declared2)
    check("a plan touching a control surface tiers high",
          got["tier"] == "high", str(got))

    check("an unreadable plan yields None, which tiers high",
          scope.plan_paths(Path(_d) / "absent.md") is None)

# Exit codes are ordered so a caller can threshold on them.
check("the tier order is low < medium < high",
      scope.TIERS == ("low", "medium", "high"), str(scope.TIERS))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All scope tests passed ({len(scope.CLAUSES)} clauses, "
      f"{len(scope.TIERS)} risk tiers)")
