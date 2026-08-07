#!/usr/bin/env python3
"""The merge-queue CI shape holds: one required check, and it depends on all.

Two failures this prevents, both silent:

  1. **A new job not in `conclusion.needs`.** Branch protection requires only
     `conclusion`, so a job nobody depends on can fail while the merge stays
     green. rust-analyzer's own workflow shouts this in a comment for a reason.
  2. **A missing `merge_group` trigger.** The queue waits for checks on that
     event. Without it there are none to wait for, and the queue merges
     combinations no run ever tested -- which is the entire thing a queue exists
     to prevent.

Parsed as text rather than with PyYAML: nothing else in `tools/` needs a
dependency, and CI installs only ruff and mypy. The shapes asserted are simple
enough that a real parser buys nothing.

Run: python tools/test_ci_shape.py
"""

from __future__ import annotations

import re
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


WF = ROOT / ".github" / "workflows" / "checks.yml"
OWNERS = ROOT / "CODEOWNERS"

check("the checks workflow exists", WF.is_file(), str(WF))
if failures:
    sys.exit(1)

wf = WF.read_text(encoding="utf-8")

# --- triggers ---------------------------------------------------------------

trigger_block = wf.split("\njobs:", 1)[0]
for event in ("pull_request:", "merge_group:"):
    check(f"the workflow triggers on {event.rstrip(':')}",
          re.search(rf"(?m)^\s{{2}}{re.escape(event)}", trigger_block) is not None)

# --- the required check depends on everything -------------------------------

jobs_block = wf.split("\njobs:", 1)[1] if "\njobs:" in wf else ""
jobs = re.findall(r"(?m)^  ([a-z][a-z0-9_-]*):\s*$", jobs_block)
check("jobs are declared", len(jobs) >= 2, str(jobs))
check("there is a job named `conclusion`", "conclusion" in jobs, str(jobs))

needs_m = re.search(r"(?m)^    needs:\s*\[([^\]]*)\]", jobs_block)
needs = {n.strip() for n in needs_m.group(1).split(",") if n.strip()} if needs_m else set()
others = {j for j in jobs if j != "conclusion"}

check("conclusion declares its dependencies", bool(needs), "no `needs:` found")
check("conclusion depends on EVERY other job",
      others <= needs,
      f"missing from needs: {sorted(others - needs)} -- these can fail while the "
      f"merge stays green")
check("conclusion depends on nothing that does not exist",
      needs <= set(jobs), f"phantom: {sorted(needs - set(jobs))}")

# --- a skipped job counts as success to GitHub ------------------------------
#
# So `if: !cancelled()` is not defensive style; without it the required check is
# skipped when its dependencies fail, and a skipped required check merges.

check("conclusion runs even when a dependency failed",
      "!cancelled()" in jobs_block,
      "without `if: ${{ !cancelled() }}` the required check is skipped, and a "
      "skipped check is a passing check")
check("...and it inspects each dependency's result rather than trusting `needs`",
      "toJson(needs)" in jobs_block and "--exit-status" in jobs_block)
check("...treating only success or skipped as acceptable",
      '.result == "success"' in jobs_block and '.result == "skipped"' in jobs_block)

# --- CODEOWNERS -------------------------------------------------------------

check("CODEOWNERS exists", OWNERS.is_file(), str(OWNERS))
if OWNERS.is_file():
    owners = OWNERS.read_text(encoding="utf-8")
    rules = [ln for ln in owners.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    check("CODEOWNERS has rules", len(rules) >= 2, str(len(rules)))
    check("every rule names at least one owner",
          all("@" in ln for ln in rules),
          str([ln for ln in rules if "@" not in ln]))
    check("every owner handle is well formed",
          all(re.fullmatch(r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:/[\w-]+)?", tok)
              for ln in rules for tok in ln.split()[1:]),
          "a malformed handle makes the whole file inert, with no error at merge time")

    # GitHub applies the LAST matching pattern, so a catch-all placed after a
    # specific rule silently overrides it -- the file reads as protecting a path
    # that it does not.
    first = rules[0].split()[0] if rules else ""
    check("the catch-all is first, so specific rules win", first == "*", f"first rule: {first}")

    # The paths that run unattended must be owned. Everything else is a judgement
    # call; these are not.
    for must in ("/.claude/hooks/", "/.claude/settings.json",
                 "/.claude/project-checks.json", "/.github/workflows/"):
        check(f"{must} is owned", any(ln.split()[0] == must for ln in rules))

# --- every workflow, not just this one ---------------------------------------
#
# `ci.yml` sat beside `checks.yml` for months referencing requirements.txt,
# docs/diagrams/ and tools/test_resolver.py -- none of which exist. It failed on
# every push and nothing here looked at it, because this suite only ever read
# `checks.yml`. A second workflow running its own tests also defeats the
# single-required-check design: branch protection names `conclusion`, so whatever
# that other workflow decides is invisible to the merge.

WORKFLOWS = ROOT / ".github" / "workflows"
_files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
check("there is at least one workflow", bool(_files))
for _wf in _files:
    _text = _wf.read_text(encoding="utf-8")
    for _ref in set(re.findall(r"(?:python |-r )([A-Za-z0-9_./-]+\.(?:py|txt))", _text)):
        check(f"{_wf.name} references a file that exists: {_ref}",
              (ROOT / _ref).is_file(),
              "a workflow step pointing at a deleted path fails every run, and "
              "a red job nobody reads is worse than no job")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All CI shape tests passed ({len(jobs)} jobs, conclusion needs {sorted(needs)})")
