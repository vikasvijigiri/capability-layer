#!/usr/bin/env python3
"""Tests for tools/parallel_groups.py -- the licence to run agents concurrently.

Two properties, and the second is the one that matters.

**Safety.** No round may contain two tasks that write the same file. This
replaced a flat "never two implementers at once", so if it is wrong the failure
mode is worse than the rule it replaced: silent mutual corruption instead of
slowness. Asserted over every group of every fixture, not by example.

**Usefulness.** A scheduler that answers "one per round" for everything is
safe and pointless. Genuinely independent tasks must actually be grouped.

Run: python tools/test_parallel_groups.py
"""

from __future__ import annotations

import importlib.util
import sys
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


pg = load("tools/parallel_groups.py", "parallel_groups_mod")


# --- the block form this repository actually writes --------------------------
#
# `writing-plans` emits `**Files:**` followed by `- Create: \`path\` — why`
# bullets. The first version of the parser matched only the inline form, read
# zero files from every plan here, and called them all unschedulable. A checker
# that rejects the format it checks gets deleted rather than adopted, so the
# block form is the first fixture.

BLOCK = """
### Task 1: Parser

**Purpose:** read the thing

**Files:**
- Create: `src/parse.py` — the parser
- Test: `tests/test_parse.py` — coverage

**Dependencies:** none

### Task 2: Renderer

**Files:**
- Create: `src/render.py` — output
- Test: `tests/test_render.py` — coverage

**Dependencies:** none

### Task 3: Wire them together

**Files:**
- Modify: `src/cli.py:main` — call both

**Dependencies:** Task 1, Task 2
"""

result = pg.schedule(BLOCK)
check("the block form parses", result["tasks"] == 3, str(result["problems"])[:200])
check("...with no problems", result["valid"], str(result["problems"])[:200])
check("two independent tasks share a round",
      result["groups"][0]["tasks"] == [1, 2], str(result["groups"][0]["tasks"]))
check("...and the dependent task waits for its own round",
      result["groups"][1]["tasks"] == [3], str(result["groups"][1]["tasks"]))
check("rounds are fewer than tasks, which is the whole point",
      result["rounds"] == 2 and result["max_concurrency"] == 2,
      f"rounds={result['rounds']} max={result['max_concurrency']}")

# `Modify: \`src/cli.py:main\`` is one file, not a file called "src/cli.py:main".
check("a path:symbol reference resolves to the path",
      result["groups"][1]["files"] == ["src/cli.py"],
      str(result["groups"][1]["files"]))


# --- the inline form --------------------------------------------------------

INLINE = """
### Task 1: A
- Files: `a.py`, `b.py`
- Depends on: none

### Task 2: B
- Files: `c.py`
- Depends on: none
"""
inline = pg.schedule(INLINE)
check("the inline form parses too", inline["valid"] and inline["tasks"] == 2,
      str(inline["problems"])[:200])
check("...and groups both tasks into one round",
      inline["max_concurrency"] == 2, str(inline["groups"]))


# --- safety: overlap always separates ---------------------------------------

OVERLAP = """
### Task 1: A
**Files:**
- Modify: `shared.py:one`
**Dependencies:** none

### Task 2: B
**Files:**
- Modify: `shared.py:two`
**Dependencies:** none

### Task 3: C
**Files:**
- Create: `other.py`
**Dependencies:** none
"""
overlap = pg.schedule(OVERLAP)
check("two tasks editing different symbols in ONE file are never grouped",
      all(not ({1, 2} <= set(g["tasks"])) for g in overlap["groups"]),
      str([g["tasks"] for g in overlap["groups"]]))
check("...and the independent third task still gets to run beside one of them",
      overlap["max_concurrency"] == 2, str([g["tasks"] for g in overlap["groups"]]))


# --- safety, by exhaustion over every fixture -------------------------------
#
# The invariant is not "the examples above came out right". It is that no group
# this module can produce ever contains a file collision.

FIXTURES = {"block": BLOCK, "inline": INLINE, "overlap": OVERLAP}
for label, text in FIXTURES.items():
    sched = pg.schedule(text)
    tasks, _ = pg.parse_plan(text)
    files_of = {t["number"]: set(t["files"]) for t in tasks}
    for group in sched["groups"]:
        members = group["tasks"]
        for i, left in enumerate(members):
            for right in members[i + 1:]:
                clash = files_of[left] & files_of[right]
                if clash:
                    check(f"{label}: tasks {left} and {right} collide on "
                          f"{sorted(clash)} yet share a round", False)
check("no round in any fixture contains a file collision", True)

for label, text in FIXTURES.items():
    tasks, _ = pg.parse_plan(text)
    task_of = {t["number"]: t for t in tasks}
    seen: set[int] = set()
    for group in pg.schedule(text)["groups"]:
        for number in group["tasks"]:
            unmet = [d for d in task_of[number]["depends_on"]
                     if d in task_of and d not in seen]
            if unmet:
                check(f"{label}: task {number} scheduled before {unmet}", False)
        seen.update(group["tasks"])
check("no task is ever scheduled before something it depends on", True)


# --- shared surfaces run alone ----------------------------------------------

SHARED = """
### Task 1: Add a dependency
**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
**Dependencies:** none

### Task 2: Unrelated feature
**Files:**
- Create: `src/feature.py`
**Dependencies:** none

### Task 3: Also unrelated
**Files:**
- Create: `src/other.py`
**Dependencies:** none
"""
shared = pg.schedule(SHARED)
lock_group = [g for g in shared["groups"] if 1 in g["tasks"]][0]
check("a lockfile task runs alone even with disjoint files",
      lock_group["tasks"] == [1] and lock_group["serialized"],
      str(lock_group))
check("...and says which surface forced it",
      "package-lock.json" in lock_group["reason"], lock_group["reason"])
check("...while the two genuinely independent tasks still share a round",
      any(set(g["tasks"]) == {2, 3} for g in shared["groups"]),
      str([g["tasks"] for g in shared["groups"]]))

MIGRATION = """
### Task 1: Schema change
**Files:**
- Create: `migrations/0004_add_column.sql`
**Dependencies:** none

### Task 2: Feature
**Files:**
- Create: `src/x.py`
**Dependencies:** none
"""
mig = pg.schedule(MIGRATION)
check("a migration is a shared surface too, from _hooklib's table",
      [g for g in mig["groups"] if 1 in g["tasks"]][0]["serialized"],
      "the migration pattern list is reused, not re-listed")


# --- a plan that cannot be scheduled says why -------------------------------

NO_FILES = """
### Task 1: Do the thing
**Purpose:** unclear
**Dependencies:** none
"""
bad = pg.schedule(NO_FILES)
check("a task with no Files field is refused, not guessed at",
      not bad["valid"] and "declares no `Files:` field" in bad["problems"][0],
      str(bad["problems"]))

EMPTY_FILES = """
### Task 1: Do the thing
**Files:** none
**Dependencies:** none
"""
empty = pg.schedule(EMPTY_FILES)
check("an empty Files list is a different problem from a missing one",
      not empty["valid"] and "empty `Files:` list" in empty["problems"][0],
      str(empty["problems"]))

CYCLE = """
### Task 1: A
**Files:** `a.py`
**Depends on:** 2

### Task 2: B
**Files:** `b.py`
**Depends on:** 1
"""
cycle = pg.schedule(CYCLE)
check("a dependency cycle is reported rather than worked around",
      not cycle["valid"] and any("cycle" in p for p in cycle["problems"]),
      str(cycle["problems"]))

UNKNOWN_DEP = """
### Task 1: A
**Files:** `a.py`
**Depends on:** 9
"""
unknown = pg.schedule(UNKNOWN_DEP)
check("a dependency on a task that does not exist is reported",
      not unknown["valid"] and any("no task" in p for p in unknown["problems"]),
      str(unknown["problems"]))

DUPES = """
### Task 1: A
**Files:** `a.py`
**Dependencies:** none

### Task 1: Also A
**Files:** `b.py`
**Dependencies:** none
"""
dupes = pg.schedule(DUPES)
check("two tasks numbered the same is ambiguous and refused",
      not dupes["valid"] and any("duplicate" in p for p in dupes["problems"]),
      str(dupes["problems"]))

check("a document with no tasks is not silently 'schedulable'",
      not pg.schedule("# Just prose\n\nNothing here.\n")["valid"])

# The dangerous direction. A task that never states its dependencies must not be
# read as independent -- that reading turns a sequential plan into a concurrent
# dispatch, which is the corruption the old flat ban was protecting against.
NO_DEPS = """
### Task 1: Store
**Files:** `store.py`

### Task 2: Executor that uses the store
**Files:** `executor.py`
"""
no_deps = pg.schedule(NO_DEPS)
check("a task with no dependency field is refused, not assumed independent",
      not no_deps["valid"]
      and any("declares no `Depends on:`" in p for p in no_deps["problems"]),
      str(no_deps["problems"])[:200])
check("...and it is refused for BOTH tasks, not just the first",
      len([p for p in no_deps["problems"] if "Depends on:" in p]) == 2,
      str(no_deps["problems"]))

PROSE_DEP = """
### Task 1: Store
**Files:** `store.py`
**Dependencies:** none

### Task 2: Executor
**Files:** `executor.py`
**Dependencies:** the store's read API
"""
prose = pg.schedule(PROSE_DEP)
check("a dependency named in prose rather than by number is refused",
      not prose["valid"] and any("cannot resolve" in p for p in prose["problems"]),
      str(prose["problems"])[:200])
check("...because reading it as independence is the unsafe guess",
      not any(set(g["tasks"]) == {1, 2} for g in prose["groups"]),
      "an unresolved dependency must never end up in a concurrent round")


# --- determinism ------------------------------------------------------------
#
# The whole argument for computing this is that the answer is re-derivable. If
# two runs disagreed, a reviewer could not check the schedule they were handed.

for label, text in FIXTURES.items():
    first, second = pg.schedule(text), pg.schedule(text)
    check(f"{label}: the schedule is identical across runs", first == second)


# --- it works on a real plan in this repository -----------------------------

real = sorted((ROOT / "docs" / "plans").glob("*.md"))
real = [p for p in real if p.name != "README.md"]
#
# The live fixture's value is not that it passes -- it is that it exercises the
# real format. `2026-08-03-physrun-run-substrate.md` predates this contract and
# expresses its ordering through `**Interfaces:**` prose rather than
# `**Dependencies:**`, so the correct verdict on it is *unschedulable*, and the
# problems must name the tasks. An earlier version of this module reported it as
# seven fully-parallel tasks, which is why the assertion is written this way
# round: a plan being refused is evidence the refusal works.
if real:
    text = real[-1].read_text(encoding="utf-8", errors="replace")
    live = pg.schedule(text)
    headers = len(pg.TASK_HEADER.findall(text))
    check(f"a real plan ({real[-1].name}) has its task headers found",
          headers > 0, f"{headers} header(s)")
    check("...and every task's declared files are read from the block form",
          all(t["files"] for t in pg.parse_plan(text)[0]) or not pg.parse_plan(text)[0],
          "a task parsed with an empty file set means the block reader regressed")
    if not live["valid"]:
        check("...and an undeclared dependency is reported per task, with its number",
              all(any(f"Task {n} " in p for p in live["problems"])
                  for n in range(1, headers + 1)),
              str(live["problems"])[:300])
        check("...and nothing was scheduled concurrently on an unschedulable plan",
              live["max_concurrency"] <= 1,
              f"max concurrency {live['max_concurrency']} over a plan whose "
              f"ordering this module could not read")
    else:
        check("...and its rounds respect its declared dependencies",
              live["rounds"] >= 1, str(live)[:200])
else:
    # Advisory, not a failure. A freshly installed target has no plans yet, and
    # failing there would make a correct install look broken -- the live fixture
    # is extra confidence in the repo that has one, never the property under test.
    print("NOTE: docs/plans/ has no plan file, so the live-format fixture was "
          "skipped. The synthetic fixtures above cover both plan forms.")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All parallel-group tests passed")
