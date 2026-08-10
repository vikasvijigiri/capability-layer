#!/usr/bin/env python3
"""Tests for tools/delivery_check.py -- the facts that decide whether a branch
is actually ready to land.

Why this suite exists
---------------------
Two failures on 2026-08-09, hours apart, neither caught by any check:

  1. A PR opened with `--base X` from a branch cut off `Y` showed ten files
     instead of three. A human reading the PR list caught it.
  2. Merge order stranded three merged units: a child merged upward before its
     siblings merged into it, so four PRs read "merged" while the work was
     absent from the branch heading for `main`. Caught by counting files during
     an unrelated question.

Both are `base-alignment`, and it is one command. The point of this file is that
the check now fails before a human has to notice.

`evaluate()` is pure, so every case here is a dict literal -- no repository, no
network, no fixture directories. The IO lives in `gather_facts()` behind an
`offline` escape, the same seam `git_identity.gather(root, offline=)` uses.

Run: python tools/test_delivery_check.py
"""
from __future__ import annotations

import importlib.util
import shutil
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


dc = load("tools/delivery_check.py", "delivery_check_mod")


# A tree where every check passes. Each case below inverts exactly one fact, so
# a finding that appears for the wrong reason is visible.
CLEAN = {
    "head_sha": "aaaaaaa",
    "merge_base": "bbbbbbb",
    "base_tip": "bbbbbbb",
    "ci": {"sha": "aaaaaaa", "conclusion": "success"},
    "stack_depth": 1,
    "merge_methods": ["squash"],
    "ahead": 2,
    "behind": 0,
    "dirty": [],
    "protection": {"required_status_checks": {"contexts": ["conclusion"]}},
}


def codes(facts: dict, severity: str | None = None) -> set[str]:
    found = dc.evaluate(facts)
    return {f["code"] for f in found
            if severity is None or f["severity"] == severity}


def one(facts: dict, code: str) -> dict | None:
    return next((f for f in dc.evaluate(facts) if f["code"] == code), None)


def sev(facts: dict, code: str) -> str:
    """The severity of one finding, or `<absent>`.

    Never raises. `sev(...)` on a missing finding raises TypeError,
    which kills the suite mid-run so that every later check silently never runs
    -- found by mutation, where removing the worktree check produced a crash
    rather than a FAIL and read as "hollow".
    """
    f = one(facts, code)
    return f["severity"] if f else "<absent>"


# --- the clean baseline ------------------------------------------------------

check("a clean tree produces no blocking finding",
      not codes(CLEAN, "blocking"), str(codes(CLEAN, "blocking")))


# --- base-alignment: the check that catches both of today's failures ---------

_misbased = {**CLEAN, "merge_base": "ccccccc"}
check("a PR whose base is not its branch point is blocking",
      sev(_misbased, "base-alignment") == "blocking",
      str(one(_misbased, "base-alignment")))
check("...and it says so in words a reader can act on",
      "base" in str(one(_misbased, "base-alignment")).lower(),
      "a finding nobody can act on is a finding nobody acts on")


# --- ci: green, and green for THIS sha ---------------------------------------

check("a failed CI run is blocking",
      sev({**CLEAN, "ci": {"sha": "aaaaaaa", "conclusion": "failure"}},
          "ci") == "blocking")

# A run against an older SHA proves nothing about this tree. This is the exact
# shape of the second failure -- a signal that looked present and was stale.
_stale = {**CLEAN, "ci": {"sha": "0000000", "conclusion": "success"}}
check("a successful run against a DIFFERENT sha is blocking",
      sev(_stale, "ci") == "blocking",
      "a green run on another commit is not evidence about this one")

# Resolved at Gate 1: pending is blocking, because a required status check
# treats expected-but-not-reported as unsatisfied.
_pending = {**CLEAN, "ci": None}
check("CI that has not run is blocking by default",
      sev(_pending, "ci") == "blocking")
check("...and --allow-pending downgrades it to advisory, not to silence",
      sev({**_pending, "allow_pending": True}, "ci") == "advisory",
      "proceeding must be a thing somebody typed, and still visible")


# --- stack-depth --------------------------------------------------------------

check("a depth of 2 is advisory",
      sev({**CLEAN, "stack_depth": 2}, "stack-depth") == "advisory")
check("a depth of 4 is blocking",
      sev({**CLEAN, "stack_depth": 4}, "stack-depth") == "blocking")


# --- merge-method: squash is the declared intent ------------------------------
#
# Resolved at Gate 1: squash, and never stack. The finding is the incompatible
# COMBINATION, because that is what stranded three merged units -- squashing the
# base gives main a new SHA and the children re-propose their parent's files.
check("squash with a stack open is blocking",
      sev({**CLEAN, "stack_depth": 2}, "merge-method") == "blocking",
      "this is the combination that stranded three units")
check("squash with no stack is fine",
      one(CLEAN, "merge-method") is None)


# --- divergence ---------------------------------------------------------------

_diverged = {**CLEAN, "behind": 3}
check("a branch needing a force-push is reported",
      one(_diverged, "divergence") is not None)
check("...and the report names --force-with-lease, never --force",
      "force-with-lease" in str(one(_diverged, "divergence")),
      "the layer has never mentioned the safe form; this is where it says it")


# --- worktree ------------------------------------------------------------------

check("a dirty worktree is blocking",
      sev({**CLEAN, "dirty": ["a.py"]}, "worktree") == "blocking")


# --- enforcement: the 403 must never read as a pass ---------------------------

_unenforced = {**CLEAN, "protection": None}
check("unavailable branch protection is `unknown`, never a pass",
      sev(_unenforced, "enforcement") == "unknown")
check("...and it says the result is advisory only",
      "advisory" in str(one(_unenforced, "enforcement")).lower(),
      "a green run must not be read as a guarantee it cannot make")


# --- a missing fact is never a pass -------------------------------------------
#
# Article V: a check that could not run is unrun, not passed. Every fact is
# nulled in turn, and none may vanish from the report.
for _fact in ("merge_base", "base_tip", "stack_depth", "merge_methods",
              "ahead", "dirty"):
    _missing = {**CLEAN, _fact: None}
    _sev = {f["severity"] for f in dc.evaluate(_missing)}
    check(f"a missing `{_fact}` yields a finding, not silence",
          "unknown" in _sev or "blocking" in _sev,
          f"severities were {_sev}")


# --- exit codes ----------------------------------------------------------------

check("no blocking finding exits 0", dc.exit_code(dc.evaluate(CLEAN)) == 0)
check("a blocking finding exits 1",
      dc.exit_code(dc.evaluate(_misbased)) == 1)
check("an undetermined fact exits 2, not 0",
      dc.exit_code(dc.evaluate({**CLEAN, "merge_base": None})) == 2,
      "absent and passing are different answers")


# --- the transformations gather_facts used to hide -----------------------------
#
# Every defect `code-review` found was in `gather_facts`, and the suite had
# missed all three because it only ever exercised that function with
# `offline=True` -- the one path where it does nothing. The seam that made
# `evaluate()` testable is exactly what left the collection untested.
#
# The transformations are pure functions now, so the API shapes that caused the
# defects are ordinary dict literals here.

# `conclusion` is null until `status == "completed"`. Reading it unfiltered made
# an in-progress run look like a failure -- and, worse, made `facts["ci"]`
# non-None, so the pending branch never ran and `--allow-pending` could not fire
# in the one situation it exists for.
_RUNS_MIXED = {"check_runs": [{"status": "in_progress", "conclusion": None},
                              {"status": "completed", "conclusion": "success"}]}
check("a run still in progress means not-yet-green, never a failure",
      dc._ci_from_runs(_RUNS_MIXED, "aaaaaaa") is None,
      f"got {dc._ci_from_runs(_RUNS_MIXED, 'aaaaaaa')}")

_RUNS_QUEUED = {"check_runs": [{"status": "queued", "conclusion": None}]}
check("a queued run is not-yet-run either",
      dc._ci_from_runs(_RUNS_QUEUED, "aaaaaaa") is None)

_RUNS_DONE = {"check_runs": [{"status": "completed", "conclusion": "success"},
                             {"status": "completed", "conclusion": "success"}]}
check("all completed and successful is success",
      dc._ci_from_runs(_RUNS_DONE, "aaaaaaa") == {"sha": "aaaaaaa",
                                                  "conclusion": "success"})

_RUNS_FAILED = {"check_runs": [{"status": "completed", "conclusion": "failure"},
                               {"status": "in_progress", "conclusion": None}]}
check("a completed failure beside a running job is still a failure",
      (dc._ci_from_runs(_RUNS_FAILED, "aaaaaaa") or {}).get("conclusion") == "failure",
      "a job that already failed does not become pending because another is running")

# `skipped` and `neutral` are not failures, and this is not theoretical: this
# repository's own checks.yml skips `build · audit · e2e · smoke` on push-only
# runs, so a green commit carries one skipped run. Treating anything-but-success
# as failure reported `[blocking] CI concluded 'failure'` on a green base branch.
for _ok in ("skipped", "neutral"):
    _mixed = {"check_runs": [{"status": "completed", "conclusion": "success"},
                             {"status": "completed", "conclusion": _ok}]}
    check(f"a completed `{_ok}` run does not make CI a failure",
          (dc._ci_from_runs(_mixed, "a") or {}).get("conclusion") == "success",
          f"got {dc._ci_from_runs(_mixed, 'a')} -- a skipped job is not a failed one")

for _bad in ("failure", "cancelled", "timed_out", "action_required"):
    _f = {"check_runs": [{"status": "completed", "conclusion": _bad}]}
    check(f"a completed `{_bad}` run IS a failure",
          (dc._ci_from_runs(_f, "a") or {}).get("conclusion") == "failure",
          f"got {dc._ci_from_runs(_f, 'a')}")

check("no runs at all is not-yet-run", dc._ci_from_runs({"check_runs": []}, "a") is None)
check("an unreadable response is not-yet-run", dc._ci_from_runs(None, "a") is None)


# Depth must describe THIS branch's chain. Counting every stacked PR in the
# repository gave the same number to every branch, so an unrelated stack could
# block a branch based directly on the default branch.
_PRS = [{"baseRefName": "main", "headRefName": "unrelated-a"},
        {"baseRefName": "unrelated-a", "headRefName": "unrelated-b"},
        {"baseRefName": "main", "headRefName": "mine"}]
check("a branch off the default branch is depth 1, whatever else is stacked",
      dc._chain_depth(_PRS, "mine") == 1,
      f"got {dc._chain_depth(_PRS, 'mine')} -- an unrelated stack must not count")
check("...and the unrelated stack still measures its own depth",
      dc._chain_depth(_PRS, "unrelated-b") == 2,
      f"got {dc._chain_depth(_PRS, 'unrelated-b')} -- two PRs in that chain "
      f"(unrelated-b, unrelated-a); `main` is not a PR and adds no depth")
check("a branch with no PR is depth 1",
      dc._chain_depth(_PRS, "no-pr-yet") == 1)
check("an unreadable PR list is unknown, not 1",
      dc._chain_depth(None, "mine") is None)

# A cycle in baseRefName must terminate rather than hang.
_CYCLE = [{"baseRefName": "b", "headRefName": "a"},
          {"baseRefName": "a", "headRefName": "b"}]
check("a cycle in the chain terminates", dc._chain_depth(_CYCLE, "a") is not None)


# `_run` returned "" for both a clean tree and a failed command, so an
# undetermined worktree read as a pass -- the exact Article V violation this
# module's docstring is built around.
check("a failed command is distinguishable from empty output",
      dc._run(["git", "definitely-not-a-subcommand"], ROOT) is None,
      "a failure must not look like success with no output")
check("...while a command that succeeds with no output returns empty, not None",
      dc._run(["git", "log", "-0", "--format="], ROOT) == "",
      "empty and failed are different answers")


# --- the two paths a mutation sweep found uncovered -----------------------------
#
# Both were HOLLOW: mutating them left the suite green. Neither needs a mock --
# a name that is not an executable raises OSError, and a directory that is not a
# repository makes `git status` exit non-zero. Reaching a branch with a real
# input beats asserting it with a patched one.

check("a missing executable is None, not empty output",
      dc._run(["definitely-not-an-executable-xyz"], ROOT) is None,
      "this is the `except OSError` branch; returning '' here made a failed "
      "command look like a command that printed nothing")

# `gather_facts` in a directory with no repository: every git call fails, so
# `dirty` must be None rather than [] -- absent, not clean.
_norepo = Path(tempfile.mkdtemp())
_facts = dc.gather_facts(_norepo, "main", "HEAD", offline=True)
check("gather_facts reports an undetermined worktree as None, not clean",
      _facts["dirty"] is None,
      f"got {_facts['dirty']!r} -- [] would read as 'no uncommitted paths', "
      f"which is a pass this could not have earned")
check("...and evaluate turns that into `unknown`, never silence",
      sev(_facts, "worktree") == "unknown",
      f"findings: {[f['code'] for f in dc.evaluate(_facts)]}")
check("...and the run as a whole cannot exit 0 from there",
      dc.exit_code(dc.evaluate(_facts)) != 0)

shutil.rmtree(_norepo, ignore_errors=True)


# --- gather_facts is inert offline ---------------------------------------------

_offline = dc.gather_facts(ROOT, "main", "HEAD", offline=True)
check("offline gathering returns every network fact as None",
      _offline["ci"] is None and _offline["protection"] is None
      and _offline["stack_depth"] is None,
      str({k: v for k, v in _offline.items() if v is not None}))


print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures[:3])}")
    sys.exit(1)
print("All delivery-check tests passed")
