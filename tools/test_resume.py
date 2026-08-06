#!/usr/bin/env python3
"""Tests for tools/resume.py -- the derived state that replaces stored state.

Two halves, tested differently on purpose:

  1. `derive_state` is pure, so every state gets a fixture dict and an assertion.
     This is the whole policy, and it is cheap enough to assert exhaustively.
  2. `gather_facts` touches git and the filesystem, so it is exercised once
     against a real throwaway repository. It is not re-tested per state -- that
     is what the split is for.

The invariant that matters most is **totality**: `derive_state` must return a
known state for any dict, including an empty one. A resume that can throw is a
resume you cannot rely on at the exact moment you need it -- after a crash.

Run: python tools/test_resume.py
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
    assert spec is not None, f"no import spec for {rel}"
    assert spec.loader is not None, f"no loader for {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rs = load("tools/resume.py", "resume_mod")


# --- a fully-formed unit of work, which every case below perturbs -----------
#
# Written as a base plus overrides rather than nine literal dicts: when a new
# fact is added, one line changes here instead of nine drifting out of sync.

DONE_FACTS = {
    "slug": "checkout-retry",
    "branch": "feat/checkout-retry",
    "plan_exists": True,
    "plan_approved": True,
    "clarifications": 0,
    "branch_exists": True,
    "checks_green": True,
    "pr_number": 42,
    "pr_labels": [],
    "pr_merged": True,
    "release_pr": None,
    "deploy_healthy": True,
    "attempts": 0,
    "max_attempts": 3,
}


def facts(**overrides) -> dict:
    merged = dict(DONE_FACTS)
    merged.update(overrides)
    return merged


# --- one case per state ------------------------------------------------------

CASES = [
    ("PLANNING", facts(plan_exists=False)),
    ("WAITING_PLAN_APPROVAL", facts(plan_approved=False)),
    ("BUILD", facts(branch_exists=False)),
    ("REPAIR", facts(checks_green=False)),
    ("LAND", facts(pr_number=None)),
    ("QUEUED", facts(pr_merged=False)),
    ("WAITING_SHIP_APPROVAL", facts(release_pr=7)),
    ("ROLLING_BACK", facts(deploy_healthy=False)),
    ("BLOCKED", facts(attempts=3, checks_green=False)),
    ("DONE", facts()),
]

for want, fixture in CASES:
    got = rs.derive_state(fixture)
    check(f"derives {want}", got == want, f"got {got}")

check("every state in the table is reachable from a fixture",
      {want for want, _ in CASES} == set(rs.NEXT_ACTION),
      f"table={sorted(rs.NEXT_ACTION)} covered={sorted({w for w, _ in CASES})}")


# --- totality ----------------------------------------------------------------
#
# The failure this guards against is a resume that raises after a crash, which
# is precisely when nobody can afford to debug the resume itself.

check("an empty dict still derives a state", rs.derive_state({}) == "PLANNING")
check("a partial dict does not raise",
      rs.derive_state({"plan_exists": True}) == "WAITING_PLAN_APPROVAL")
check("every derived state has a next action",
      all(rs.derive_state(f) in rs.NEXT_ACTION for _, f in CASES))
check("every terminal state is a real state",
      rs.TERMINAL <= set(rs.NEXT_ACTION),
      f"unknown: {sorted(rs.TERMINAL - set(rs.NEXT_ACTION))}")


# --- the two ordering rules that are policy, not accident --------------------

check("an unresolved clarification outranks an approved plan",
      rs.derive_state(facts(clarifications=1)) == "WAITING_PLAN_APPROVAL",
      "approving over an open question would bake in a guess")
check("a spent attempt budget outranks a red check",
      rs.derive_state(facts(attempts=3, checks_green=False)) == "BLOCKED",
      "otherwise an exhausted unit is handed back to REPAIR forever")
check("...but an unspent budget still repairs",
      rs.derive_state(facts(attempts=2, checks_green=False)) == "REPAIR")
check("a blocking review label sends a green PR back to repair",
      rs.derive_state(facts(pr_labels=["review:blocked"], pr_merged=False)) == "REPAIR")


# --- three-valued checks_green ----------------------------------------------
#
# "failed" and "nothing has run" are different facts. Conflating them sends the
# loop into REPAIR with nothing to repair, which is how a repair budget gets
# spent before any work is attempted.

check("checks_green=None means build, not repair",
      rs.derive_state(facts(checks_green=None)) == "BUILD")
check("checks_green=False means repair",
      rs.derive_state(facts(checks_green=False)) == "REPAIR")


# --- slug handling -----------------------------------------------------------

check("a prefixed branch yields the slug",
      rs.slug_from_branch("feat/checkout-retry") == "checkout-retry")
check("an unprefixed branch is its own slug",
      rs.slug_from_branch("rebuild-capability-layer") == "rebuild-capability-layer")


# --- the state line stays short ---------------------------------------------
#
# It is injected at every session start, so its length is a per-session tax.

_line = rs.state_line(DONE_FACTS, "DONE")
check("the state line is one line", "\n" not in _line)
check("...and names the slug, state and next action",
      "checkout-retry" in _line and "state=DONE" in _line and "next=" in _line, _line)


# --- gather_facts against a real repository ---------------------------------


def temp_repo() -> Path:
    d = Path(tempfile.mkdtemp())
    for args in (
        ["init", "--quiet"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True)
    (d / "README.md").write_text("# t\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(d), capture_output=True, text=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init"],
                   cwd=str(d), capture_output=True, text=True)
    return d


repo = temp_repo()
f = rs.gather_facts(repo, "checkout-retry")
check("a repo with no plan reports no plan", f["plan_exists"] is False)
check("...and derives PLANNING", rs.derive_state(f) == "PLANNING")
check("...and asks gh nothing when there is no remote", f["pr_number"] is None)

plans = repo / "docs" / "plans"
plans.mkdir(parents=True)
(plans / "2026-08-06-checkout-retry.md").write_text(
    "# Checkout retry\n\n[NEEDS CLARIFICATION: which backoff?]\n", encoding="utf-8")
f = rs.gather_facts(repo, "checkout-retry")
check("a plan file is found by slug", f["plan_exists"] is True)
check("...and its clarification markers are counted", f["clarifications"] == 1)
check("...so the state is the plan gate", rs.derive_state(f) == "WAITING_PLAN_APPROVAL")

(plans / "2026-08-06-checkout-retry.md").write_text(
    "# Checkout retry\n\n## Approved\n", encoding="utf-8")
f = rs.gather_facts(repo, "checkout-retry")
check("an approved plan with no markers passes the gate",
      f["plan_approved"] is True and f["clarifications"] == 0)
check("...and with no branch, the state is BUILD", rs.derive_state(f) == "BUILD")

subprocess.run(["git", "checkout", "--quiet", "-b", "feat/checkout-retry"],
               cwd=str(repo), capture_output=True, text=True)
f = rs.gather_facts(repo, "checkout-retry")
check("the work branch is detected", f["branch_exists"] is True)
check("...and nothing verified yet still means BUILD, not REPAIR",
      f["checks_green"] is None and rs.derive_state(f) == "BUILD")

subprocess.run(["git", "update-ref", "refs/uaios/green/checkout-retry", "HEAD"],
               cwd=str(repo), capture_output=True, text=True)
f = rs.gather_facts(repo, "checkout-retry")
check("a green ref at HEAD means verified", f["checks_green"] is True)
check("...and a verified tree with no PR means LAND", rs.derive_state(f) == "LAND")

# A commit after the green ref means the tree is no longer the verified one.
(repo / "src.py").write_text("x = 1\n", encoding="utf-8")
subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True, text=True)
subprocess.run(["git", "commit", "--quiet", "-m", "work"],
               cwd=str(repo), capture_output=True, text=True)
f = rs.gather_facts(repo, "checkout-retry")
check("work after the green ref makes the tree unverified again",
      f["checks_green"] is None, f"green={f['last_green']}")

# The ledger is the only stored state, and it holds counters, nothing else.
state_dir = repo / ".claude" / "hooks" / "state"
state_dir.mkdir(parents=True)
(state_dir / "resume-checkout-retry.json").write_text(
    '{"attempts": 3, "failure_class": "deterministic"}', encoding="utf-8")
f = rs.gather_facts(repo, "checkout-retry")
check("the ledger supplies the attempt count", f["attempts"] == 3)
check("...and a spent budget derives BLOCKED", rs.derive_state(f) == "BLOCKED")

(state_dir / "resume-checkout-retry.json").write_text("{ not json", encoding="utf-8")
check("a corrupt ledger reads as fresh rather than raising",
      rs.gather_facts(repo, "checkout-retry")["attempts"] == 0)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All resume tests passed")
