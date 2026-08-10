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
check("...repeatedly, and on backslashes",
      scope._norm(".\\\\.github\\\\workflows\\\\ci.yml").endswith(".github/workflows/ci.yml"),
      scope._norm(".\\\\.github\\\\workflows\\\\ci.yml"))
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

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All scope tests passed ({len(scope.CLAUSES)} clauses)")
