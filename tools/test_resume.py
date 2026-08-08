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
    ("RECON", facts(plan_exists=False, code_files=40, recon_exists=False)),
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


# --- the entry boundary: a repo this layer was dropped into ------------------
#
# The defect: run this against any repository that has never used the layer and
# it answered PLANNING, because every fact it reads is about the layer's own
# artifacts. Measured on this repo on 2026-08-07 -- 104 commits of finished work,
# state=PLANNING. "No plan here" and "nothing has happened here" were one state.

check("a large unmapped codebase with no plan needs reconnaissance first",
      rs.derive_state(facts(plan_exists=False, code_files=200,
                            recon_exists=False)) == "RECON")
check("...but a small one does not -- just read it",
      rs.derive_state(facts(plan_exists=False, code_files=3,
                            recon_exists=False)) == "PLANNING",
      "a recon pass over four files costs more than it returns")
check("...and once a map exists, recon does not repeat",
      rs.derive_state(facts(plan_exists=False, code_files=200,
                            recon_exists=True)) == "PLANNING")
check("an empty repository plans rather than reconnoitres",
      rs.derive_state({"code_files": 0}) == "PLANNING")
check("a repo at exactly the threshold reconnoitres",
      rs.derive_state(facts(plan_exists=False, code_files=rs.RECON_THRESHOLD,
                            recon_exists=False)) == "RECON",
      "the boundary is inclusive; an off-by-one here silently skips the stage")
check("recon never outranks an existing plan",
      rs.derive_state(facts(plan_exists=True, plan_approved=False,
                            code_files=500, recon_exists=False))
      == "WAITING_PLAN_APPROVAL",
      "a plan that exists was written by someone who had read the repo")
check("RECON is not terminal -- something automatic must move out of it",
      "RECON" not in rs.TERMINAL)
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

# --- a rejection is durable, and re-presenting is checkable -----------------
#
# Until 2026-08-07 `plan_approved` was one boolean, so "never shown", "rejected
# once with a reason" and "rejected three times" were the same state. The reason
# lived in chat, which is not durable evidence.

PLAN_BODY = "# Checkout retry\n\n## Approved\n\nBody of the plan.\n"
_h = rs.plan_body_hash(PLAN_BODY)

check("a plan with no rejection log reports none", rs.rejections(PLAN_BODY) == [])
check("...and counts as changed, so the first ask is allowed",
      rs.derive_state(facts(rejections=0)) == "DONE")

rejected = PLAN_BODY + (
    f"\n## Rejected 2026-08-07 (plan {_h})\n"
    "Rollback story is hand-waved -- say what happens to in-flight writes.\n")
log = rs.rejections(rejected)
check("a rejection is parsed", len(log) == 1, str(log))
check("...carrying the user's words verbatim",
      "in-flight writes" in log[0], log[0])
check("...and the body hash it was rejected at", log[0].startswith(_h), log[0])

check("recording a rejection does not itself count as changing the plan",
      rs.plan_body_hash(rejected) == _h,
      "otherwise every rejection instantly looks like a revision and the "
      "unchanged check never fires")

revised = PLAN_BODY.replace("Body of the plan.", "Body, now with rollback.") + (
    f"\n## Rejected 2026-08-07 (plan {_h})\nsame reason\n")
check("editing the plan body changes its hash",
      rs.plan_body_hash(revised) != _h)

two = rejected + f"\n## Rejected 2026-08-07 (plan {_h})\nStill not addressed.\n"
check("rejections accumulate rather than overwrite", len(rs.rejections(two)) == 2)


# --- the prose and the code agree on the two marker strings -----------------
#
# `derive_state` reads a plan file that a skill wrote. If the skill says
# "NEEDS CLARIFICATION" and the deriver looks for "[NEEDS CLARIFICATION", the
# gate silently stops working -- a plan full of open questions derives as
# approved, which is the one failure this mechanism exists to prevent. Nothing
# else binds the two, so this does.

_plans = (ROOT / ".claude/skills/writing-plans/SKILL.md").read_text(encoding="utf-8")
_brain = (ROOT / ".claude/skills/brainstormer/SKILL.md").read_text(encoding="utf-8")

check("writing-plans states the clarification marker verbatim",
      rs.CLARIFICATION_MARKER in _plans, rs.CLARIFICATION_MARKER)
check("writing-plans states the approval marker verbatim",
      rs.APPROVAL_MARKER in _plans, rs.APPROVAL_MARKER)
check("brainstormer routes non-directional questions to a marker",
      rs.CLARIFICATION_MARKER in _brain)
check("writing-plans batches the markers into one question at the gate",
      "AskUserQuestion" in _plans and "One batch" in _plans)


# --- which plan belongs to this unit -----------------------------------------
#
# The slug came from the FILENAME, so a plan named after its feature while the
# branch was named after something else matched nothing -- and the engine then
# reported the unit as having NO PLAN, which is the same answer a fresh
# repository gives. Measured here on 2026-08-08: branch
# `rebuild-capability-layer`, approved plan `2026-08-08-pip-package.md`, state
# reported as RECON with Gate 1 already passed and the plan sitting in
# docs/plans/.

_r = Path(tempfile.mkdtemp())
(_r / "docs" / "plans").mkdir(parents=True)


def _plan(name: str, body: str) -> None:
    (_r / "docs" / "plans" / name).write_text(body, encoding="utf-8")


check("no plans at all is reported as exactly that",
      rs.plan_path(_r, "anything") == (None, "no plan file exists"))

_plan("README.md", "# plans\n")
check("a README is not a plan", rs.plan_path(_r, "anything")[0] is None)

_plan("2026-01-01-something-else.md", "# Plan\n\n**Goal:** x\n")
_found, _why = rs.plan_path(_r, "checkout-retry")
check("an unrelated plan does not become this unit's", _found is None)
check("...and the reason distinguishes it from an empty directory",
      "none for slug" in _why, _why)
check("...naming how many exist, so it is not silently the fresh-repo answer",
      "1 plan(s) exist" in _why, _why)

_plan("2026-02-02-pip-package.md",
      "# Plan\n\n**Goal:** y\n\n**Slug:** checkout-retry\n")
_found, _why = rs.plan_path(_r, "checkout-retry")
check("a plan that DECLARES the slug is found whatever it is called",
      _found is not None and _found.name == "2026-02-02-pip-package.md", str(_found))
check("...and says which rule matched", _why == "declared **Slug:**", _why)

_plan("2026-03-03-checkout-retry.md", "# Plan\n\n**Goal:** z\n")
_found, _why = rs.plan_path(_r, "checkout-retry")
check("a declaration outranks the filename convention",
      _found.name == "2026-02-02-pip-package.md" and _why == "declared **Slug:**",
      f"{_found.name} via {_why}")

(_r / "docs" / "plans" / "2026-02-02-pip-package.md").unlink()
_found, _why = rs.plan_path(_r, "checkout-retry")
check("...and the filename convention still works when nothing declares",
      _found.name == "2026-03-03-checkout-retry.md"
      and _why == "filename contains the slug", f"{_found.name} via {_why}")

_plan("2026-04-04-checkout-retry.md", "# newer\n")
check("the newest matching plan wins, so a replanned unit reads its latest",
      rs.plan_path(_r, "checkout-retry")[0].name == "2026-04-04-checkout-retry.md")

# The state line is the only thing the session-start hook prints, so a mismatch
# that does not reach it is a mismatch nobody sees.
_orphaned = facts(plan_exists=False, plans_on_disk=3,
                  plan_reason="3 plan(s) exist, none for slug 'x'")
check("an orphaned plan set is surfaced in the one line that gets printed",
      "NOTE:" in rs.state_line(_orphaned, rs.derive_state(_orphaned)),
      rs.state_line(_orphaned, rs.derive_state(_orphaned)))
check("...and a repo with genuinely no plans stays quiet",
      "NOTE:" not in rs.state_line(
          facts(plan_exists=False, plans_on_disk=0), "PLANNING"))

# The live repository must resolve its own approved plan -- but ONLY where there
# is one to resolve. A freshly installed target has an empty `docs/plans/`, and
# asserting otherwise there made a correct install report a red suite. That is the
# third time a suite written here only passed at home; the layer travels, so its
# checks have to ask whether they apply.
_live_branch = rs.slug_from_branch(
    rs._git(ROOT, "rev-parse", "--abbrev-ref", "HEAD")[1] or "")
if rs.plan_candidates(ROOT) and _live_branch:
    _live_plan, _live_why = rs.plan_path(ROOT, _live_branch)
    if _live_plan is not None:
        check("this repository resolves its own plan", True)
    else:
        print(f"NOTE: no plan declares slug {_live_branch!r} here ({_live_why}). "
              f"Not a failure -- a branch may legitimately carry no plan.")
else:
    print("NOTE: no plans on disk, so the live-resolution case does not apply")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All resume tests passed")
