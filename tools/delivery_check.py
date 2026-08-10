#!/usr/bin/env python3
"""Is this branch actually ready to land — checked, not asserted.

    python tools/delivery_check.py                    # current branch vs its base
    python tools/delivery_check.py --base main --head feat/x
    python tools/delivery_check.py --offline          # no network; facts report unknown
    python tools/delivery_check.py --allow-pending    # CI not yet run is advisory

Why this exists
---------------
Two failures on 2026-08-09, hours apart, neither caught by any check:

  1. A PR opened with `--base X` from a branch cut off `Y` showed ten files
     instead of three. A human reading the PR list caught it.
  2. Merge order stranded three merged units -- a child merged upward before its
     siblings merged into it, so four PRs read "merged" while the work was
     absent from the branch heading for `main`.

Both are `base-alignment`, and it is one command:

    git merge-base <base> <head> == git rev-parse <base>

It reports; it never decides
----------------------------
The same shape as `resume.py`, `analyze.py` and `git_identity.py`, which says of
itself that it "ranks; it does not choose". Nothing here merges, pushes,
rebases or configures anything -- `test_process_router.py` fails any file that
acquires `gh pr merge`, and this one is in its scan.

Advisory, and it says so
------------------------
    gh api repos/<owner>/<repo>/branches/main/protection
    -> 403 Upgrade to GitHub Pro or make this repository public

Required checks, branch protection and merge queues are unavailable on a free
private repository, so nothing here can PREVENT a bad merge. The `enforcement`
check reports that as `unknown` and prints "advisory only", because a green run
that reads as a guarantee is worse than no run.

A missing fact is never a pass. Article V of `.claude/constitution.md`: a check
that could not run is unrun. `exit_code` returns 2 for that, and 2 is not 0.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Squash, resolved at Gate 1: squash-merge onto short-lived independent branches
# is the dominant trunk-based convention, and `CLAUDE.md` already assumed it --
# `wip:` checkpoints are deliberate "because squash-merge collapses them". The
# finding is therefore not "squash is enabled" but the incompatible COMBINATION
# of squash with an open stack, which is what stranded three merged units.
DECLARED_MERGE_METHOD = "squash"

# A stack is a scheduling constraint you chose to take on. Two is a warning;
# four is where the ordering cost exceeds what the review granularity buys, and
# the industry answer at that depth is tooling rather than discipline.
STACK_ADVISORY = 2
STACK_BLOCKING = 4


def _run(args: list[str], cwd: Path | None = None, timeout: int = 20) -> str:
    """stdout, or '' when the command is missing, fails or hangs.

    Shape copied from `git_identity._run`: `stdin=DEVNULL` so a subprocess can
    never inherit an open pipe and block forever, and no `shell=True` -- ruff
    selects the `S` set and would reject it.
    """
    try:
        proc = subprocess.run(
            args, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _json(args: list[str], cwd: Path | None = None):
    """Parsed JSON, or None. `gh` absent, unauthenticated or answering 403 is
    not a crash -- the fact becomes None and its check reports `unknown`."""
    raw = _run(args, cwd)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def gather_facts(root: Path, base: str, head: str,
                 offline: bool = False, allow_pending: bool = False) -> dict:
    """Every fact the checks read. `offline=True` nulls the network-derived ones.

    The `offline` escape is `git_identity.gather(root, offline=)`'s, and it is
    what lets the suite run with no remote: the facts become None and every
    dependent check reports `unknown` rather than passing.
    """
    facts: dict = {"allow_pending": allow_pending}

    facts["head_sha"] = _run(["git", "rev-parse", head], root) or None
    facts["base_tip"] = _run(["git", "rev-parse", base], root) or None
    facts["merge_base"] = _run(["git", "merge-base", base, head], root) or None
    facts["dirty"] = [
        ln[3:].strip()
        for ln in _run(["git", "status", "--porcelain"], root).splitlines()
        if ln.strip()
    ]

    ahead_behind = _run(
        ["git", "rev-list", "--left-right", "--count", f"{base}...{head}"], root)
    if ahead_behind and len(ahead_behind.split()) == 2:
        behind, ahead = ahead_behind.split()
        facts["behind"], facts["ahead"] = int(behind), int(ahead)
    else:
        facts["behind"] = facts["ahead"] = None

    if offline:
        facts["ci"] = None
        facts["protection"] = None
        facts["stack_depth"] = None
        facts["merge_methods"] = None
        return facts

    slug = _run(["gh", "repo", "view", "--json", "nameWithOwner",
                 "--jq", ".nameWithOwner"], root)

    facts["ci"] = None
    if slug and facts["head_sha"]:
        runs = _json(["gh", "api",
                      f"repos/{slug}/commits/{facts['head_sha']}/check-runs"], root)
        conclusions = [r.get("conclusion") for r in (runs or {}).get("check_runs", [])]
        if conclusions:
            facts["ci"] = {
                "sha": facts["head_sha"],
                "conclusion": ("success" if all(c == "success" for c in conclusions)
                               else "failure"),
            }

    facts["protection"] = (
        _json(["gh", "api", f"repos/{slug}/branches/{base}/protection"], root)
        if slug else None)

    repo = _json(["gh", "api", f"repos/{slug}"], root) if slug else None
    facts["merge_methods"] = None if repo is None else [
        name for name, key in (("squash", "allow_squash_merge"),
                               ("merge", "allow_merge_commit"),
                               ("rebase", "allow_rebase_merge"))
        if repo.get(key)
    ]

    prs = _json(["gh", "pr", "list", "--state", "open", "--json",
                 "number,baseRefName,headRefName"], root)
    if prs is None:
        facts["stack_depth"] = None
    else:
        heads = {p["headRefName"] for p in prs}
        facts["stack_depth"] = 1 + sum(1 for p in prs if p["baseRefName"] in heads)

    return facts


def evaluate(facts: dict) -> list[dict]:
    """Findings for one branch. Pure: the whole input is the dict.

    Every check resolves to exactly one of `blocking`, `advisory` or `unknown`,
    and a fact of None is `unknown` -- never absent, never a pass.
    """
    out: list[dict] = []

    def add(code: str, severity: str, finding: str) -> None:
        out.append({"code": code, "severity": severity, "finding": finding})

    def unknown(code: str, what: str) -> None:
        add(code, "unknown", f"could not determine {what} -- unrun, not passed")

    # --- base-alignment: the one that caught both of today's failures
    if facts.get("merge_base") is None or facts.get("base_tip") is None:
        unknown("base-alignment", "the merge base")
    elif facts["merge_base"] != facts["base_tip"]:
        add("base-alignment", "blocking",
            f"the base has moved or was never the branch point: "
            f"merge-base {facts['merge_base'][:7]} != base tip "
            f"{facts['base_tip'][:7]}. A PR declared against this base shows "
            f"every file the real branch point does not have.")

    # --- ci: green, for THIS sha, and pending is not green
    ci = facts.get("ci")
    if ci is None:
        sev = "advisory" if facts.get("allow_pending") else "blocking"
        add("ci", sev,
            "no CI run for this commit. A required status check treats "
            "expected-but-not-reported as unsatisfied"
            + (" (--allow-pending given)" if sev == "advisory" else ""))
    elif ci.get("sha") != facts.get("head_sha"):
        add("ci", "blocking",
            f"the latest run is against {str(ci.get('sha'))[:7]}, not "
            f"{str(facts.get('head_sha'))[:7]} -- a green run on another commit "
            f"is not evidence about this one")
    elif ci.get("conclusion") != "success":
        add("ci", "blocking", f"CI concluded {ci.get('conclusion')!r} for this commit")

    # --- stack-depth
    depth = facts.get("stack_depth")
    if depth is None:
        unknown("stack-depth", "how many PRs chain to this one")
    elif depth >= STACK_BLOCKING:
        add("stack-depth", "blocking",
            f"{depth} PRs deep. Past {STACK_ADVISORY} the ordering constraint "
            f"costs more than the review granularity buys; prefer independent "
            f"branches off the default branch.")
    elif depth >= STACK_ADVISORY:
        add("stack-depth", "advisory",
            f"{depth} PRs deep -- merge order becomes load-bearing here")

    # --- merge-method: the incompatible combination, not the setting
    methods = facts.get("merge_methods")
    if methods is None:
        unknown("merge-method", "which merge methods are enabled")
    elif DECLARED_MERGE_METHOD in methods and (depth or 0) >= STACK_ADVISORY:
        add("merge-method", "blocking",
            f"{DECLARED_MERGE_METHOD}-merge is enabled and {depth} PRs are "
            f"stacked. Squashing the base gives the default branch a new SHA, "
            f"and every child then re-proposes its parent's files. This is what "
            f"stranded three merged units on 2026-08-09.")

    # --- divergence
    if facts.get("ahead") is None or facts.get("behind") is None:
        unknown("divergence", "how far this branch has diverged")
    elif facts["behind"]:
        add("divergence", "advisory",
            f"{facts['behind']} commit(s) behind the base; publishing a rebase "
            f"needs --force-with-lease, never --force -- the lease is what "
            f"refuses when the remote moved since you last fetched")

    # --- worktree
    dirty = facts.get("dirty")
    if dirty is None:
        unknown("worktree", "whether the worktree is clean")
    elif dirty:
        add("worktree", "blocking",
            f"{len(dirty)} uncommitted path(s) -- the branch does not match the "
            f"tree these checks just read")

    # --- enforcement: the ceiling, stated so a green run is not over-read
    if facts.get("protection") is None:
        add("enforcement", "unknown",
            "branch protection is unavailable or unreadable (403 on a free "
            "private repository). These results are advisory only: nothing here "
            "prevents a merge.")

    return out


def exit_code(findings: list[dict]) -> int:
    """0 ready · 1 a check failed · 2 a fact could not be determined.

    2 is deliberately not 0. Folding "I could not tell" into "fine" is the
    silent degradation Article V forbids.
    """
    severities = {f["severity"] for f in findings}
    if "blocking" in severities:
        return 1
    if "unknown" in severities:
        return 2
    return 0


def render(findings: list[dict], base: str, head: str) -> str:
    if not findings:
        return f"delivery check: {head} -> {base}\n  ready -- no findings"
    order = {"blocking": 0, "unknown": 1, "advisory": 2}
    lines = [f"delivery check: {head} -> {base}"]
    for f in sorted(findings, key=lambda f: order.get(f["severity"], 9)):
        lines.append(f"  [{f['severity']:<8}] {f['code']}: {f['finding']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=None, help="base ref (default: the tracked upstream)")
    ap.add_argument("--head", default="HEAD", help="head ref (default: HEAD)")
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--offline", action="store_true",
                    help="skip every network fact; they report unknown")
    ap.add_argument("--allow-pending", action="store_true",
                    help="downgrade a not-yet-run CI check to advisory")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    base = args.base or _run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root
    ) or "main"

    facts = gather_facts(root, base, args.head, offline=args.offline,
                         allow_pending=args.allow_pending)
    findings = evaluate(facts)

    if args.as_json:
        print(json.dumps({"base": base, "head": args.head,
                          "findings": findings}, indent=2))
    else:
        print(render(findings, base, args.head))
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main())
