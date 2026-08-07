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
