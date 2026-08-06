#!/usr/bin/env python3
"""Where is this unit of work, right now, derived from facts rather than memory.

The workflow used to describe its states in prose (`.claude/workflow.md` carried
21 of them) and nothing wrote to or read from that description. A state machine
nothing persists is not a state machine; it is a wish. This file replaces it with
the opposite arrangement: **nothing is stored, everything is re-derived.**

The design that makes it testable is the split:

    gather_facts(root, slug) -> dict     touches git/gh/disk, tested once
    derive_state(facts)      -> str      pure, one test per state

`derive_state` is a total function over a plain dict. Every state in the workflow
is one `if` in one place, in priority order, so "which state am I in" has exactly
one answer and reading the order is reading the policy.

The slug ties everything together and is the only identifier:

    docs/plans/YYYY-MM-DD-<slug>.md      the approved plan
    feat/<slug>                          the branch
    refs/uaios/green/<slug>              the newest verified-good tree
    .claude/hooks/state/resume-<slug>.json   attempt counters, nothing else

Because state is derived, this survives what memory does not: a cleared context,
a crash mid-repair, a week away, a different machine with the same clone.

    python tools/resume.py                 # slug inferred from the branch
    python tools/resume.py --slug checkout-retry
    python tools/resume.py --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAX_ATTEMPTS = 3
BRANCH_PREFIX = "feat/"
PLANS_DIR = "docs/plans"
APPROVAL_MARKER = "## Approved"
CLARIFICATION_MARKER = "[NEEDS CLARIFICATION"
STATE_DIR = Path(".claude") / "hooks" / "state"
GREEN_REF = "refs/uaios/green/"

# A label the diff review applies when it finds something of high severity. The
# queue treats it as blocking, and so does this.
BLOCKING_LABELS = {"review:blocked", "do-not-merge", "do-not-merge/hold"}

# States nothing automatic may move out of. Two are human gates, two are stops.
TERMINAL = {
    "DONE",
    "BLOCKED",
    "WAITING_PLAN_APPROVAL",
    "WAITING_SHIP_APPROVAL",
}

# What the loop does next in each state. Kept beside the states rather than in a
# skill, because a state whose next action lives somewhere else drifts from it.
NEXT_ACTION = {
    "PLANNING": "write the plan and its acceptance tests",
    "WAITING_PLAN_APPROVAL": "human: resolve clarifications, then mark the plan approved",
    "BUILD": "implement against the plan's acceptance tests",
    "REPAIR": "classify the failure and repair it (see the escalation ladder)",
    "LAND": "open the PR and enable auto-merge",
    "QUEUED": "wait -- the merge queue owns it now",
    "WAITING_SHIP_APPROVAL": "human: merge the release PR",
    "ROLLING_BACK": "roll back, verify the rolled-back version is healthy, then diagnose",
    "BLOCKED": "human: the escalation ladder is exhausted; read the failure report",
    "DONE": "record the outcome",
}


# --- fact gathering ---------------------------------------------------------
#
# Everything here degrades to "unknown" rather than raising. A missing `gh`, an
# unauthenticated one, or no network must not turn "I cannot see the PR" into a
# crash -- the derivation treats unknown as not-yet-done, which is the safe way
# to be wrong.


def _git(root: Path, *args: str) -> tuple[int, str]:
    """(returncode, stdout). Never raises; a failed git is (1, '')."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root),
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def _gh_json(root: Path, *args: str):
    """Parsed `gh` JSON output, or None when gh cannot answer for any reason."""
    try:
        proc = subprocess.run(
            ["gh", *args], cwd=str(root),
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "null")
    except ValueError:
        return None


def slug_from_branch(branch: str) -> str:
    """`feat/checkout-retry` -> `checkout-retry`; anything else -> itself.

    A branch that does not carry the prefix is still a valid slug source. The
    prefix is a convention for readability, not a key.
    """
    if branch.startswith(BRANCH_PREFIX):
        return branch[len(BRANCH_PREFIX):]
    return branch


def plan_path(root: Path, slug: str) -> Path | None:
    """The newest plan file for this slug, or None.

    Newest by name, which sorts correctly because the convention is a leading
    ISO date. A replanned unit therefore reads its latest plan, not its first.
    """
    matches = sorted((root / PLANS_DIR).glob(f"*{slug}.md"))
    return matches[-1] if matches else None


def ledger_path(root: Path, slug: str) -> Path:
    return root / STATE_DIR / f"resume-{slug}.json"


def read_ledger(root: Path, slug: str) -> dict:
    """Attempt counters and the last recorded health. Absent means fresh."""
    try:
        return json.loads(ledger_path(root, slug).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gather_facts(root: Path, slug: str | None = None) -> dict:
    """Everything `derive_state` needs, read from git, gh, and one small ledger."""
    _, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if not slug:
        slug = slug_from_branch(branch) if branch else ""

    plan = plan_path(root, slug) if slug else None
    plan_text = ""
    if plan is not None:
        try:
            plan_text = plan.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            plan_text = ""

    work_branch = f"{BRANCH_PREFIX}{slug}"
    branch_rc, _ = _git(root, "rev-parse", "--verify", "--quiet",
                        f"refs/heads/{work_branch}")
    branch_exists = branch_rc == 0 or branch == work_branch

    _, head = _git(root, "rev-parse", "HEAD")
    green_rc, green = _git(root, "rev-parse", "--verify", "--quiet",
                           f"{GREEN_REF}{slug}")
    ledger = read_ledger(root, slug)

    # Three-valued on purpose. False means a run failed; None means nothing has
    # been verified since the last change, which is not the same fact and must
    # not send the loop into REPAIR with nothing to repair.
    if int(ledger.get("attempts", 0)) > 0:
        checks_green: bool | None = False
    elif green_rc == 0 and green and green == head:
        checks_green = True
    else:
        checks_green = None

    pr_number = None
    pr_labels: list[str] = []
    pr_merged = False
    release_pr = None

    # No remote means no PR can exist, so asking `gh` would be both wrong and
    # slow. Checking first keeps a local-only repo (this one, today) off the
    # network path entirely rather than relying on gh to fail quickly.
    _, remotes = _git(root, "remote")
    if remotes.strip():
        prs = _gh_json(root, "pr", "list", "--head", work_branch, "--state", "all",
                       "--json", "number,labels,state", "--limit", "1")
        if isinstance(prs, list) and prs:
            pr = prs[0]
            pr_number = pr.get("number")
            pr_labels = [lbl.get("name", "") for lbl in pr.get("labels") or []]
            pr_merged = pr.get("state") == "MERGED"

        release = _gh_json(root, "pr", "list", "--label", "autorelease: pending",
                           "--json", "number", "--limit", "1")
        if isinstance(release, list) and release:
            release_pr = release[0].get("number")

    return {
        "slug": slug,
        "branch": branch,
        "plan_exists": plan is not None,
        "plan_path": str(plan.relative_to(root)) if plan is not None else None,
        "plan_approved": APPROVAL_MARKER in plan_text,
        "clarifications": plan_text.count(CLARIFICATION_MARKER),
        "branch_exists": branch_exists,
        "checks_green": checks_green,
        "last_green": green if green_rc == 0 else None,
        "pr_number": pr_number,
        "pr_labels": pr_labels,
        "pr_merged": pr_merged,
        "release_pr": release_pr,
        "deploy_healthy": ledger.get("deploy_healthy"),
        "attempts": int(ledger.get("attempts", 0)),
        "max_attempts": int(ledger.get("max_attempts", MAX_ATTEMPTS)),
        "failure_class": ledger.get("failure_class"),
    }


# --- derivation -------------------------------------------------------------


def derive_state(facts: dict) -> str:
    """The one place a state is decided. Pure, total, order-sensitive.

    Read top to bottom: the first true clause wins, so the order *is* the
    policy. Two rules earn their position:

      - clarifications outrank approval. An approved plan that still carries a
        `[NEEDS CLARIFICATION]` marker was approved over an open question, and
        proceeding would bake in a guess.
      - a spent budget outranks everything below it. Otherwise a unit that has
        exhausted its ladder keeps being handed back to REPAIR forever.
    """
    if not facts.get("plan_exists"):
        return "PLANNING"
    if facts.get("clarifications", 0) > 0:
        return "WAITING_PLAN_APPROVAL"
    if not facts.get("plan_approved"):
        return "WAITING_PLAN_APPROVAL"

    if facts.get("attempts", 0) >= facts.get("max_attempts", MAX_ATTEMPTS):
        return "BLOCKED"

    if not facts.get("branch_exists"):
        return "BUILD"

    green = facts.get("checks_green")
    if green is False:
        return "REPAIR"
    if green is None:
        return "BUILD"

    if facts.get("pr_number") is None:
        return "LAND"
    if set(facts.get("pr_labels") or []) & BLOCKING_LABELS:
        return "REPAIR"
    if not facts.get("pr_merged"):
        return "QUEUED"

    if facts.get("release_pr") is not None:
        return "WAITING_SHIP_APPROVAL"
    if facts.get("deploy_healthy") is False:
        return "ROLLING_BACK"
    return "DONE"


def state_line(facts: dict, state: str) -> str:
    """The one line the session-start hook prints. Kept short on purpose -- it is
    injected every session, so it is charged for every session."""
    pr = facts.get("pr_number")
    return (
        f"slug={facts.get('slug') or '-'} "
        f"state={state} "
        f"branch={facts.get('branch') or '-'} "
        f"pr={pr if pr is not None else '-'} "
        f"attempt={facts.get('attempts', 0)}/{facts.get('max_attempts', MAX_ATTEMPTS)} "
        f"next={NEXT_ACTION.get(state, '?')}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="unit of work; inferred from the branch if omitted")
    ap.add_argument("--root", default=str(ROOT), help="repository root")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="print the facts and the state as JSON")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    facts = gather_facts(root, args.slug)
    state = derive_state(facts)

    if args.as_json:
        print(json.dumps({"state": state, "facts": facts}, indent=2))
    else:
        print(state_line(facts, state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
