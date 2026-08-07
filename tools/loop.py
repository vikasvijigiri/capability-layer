#!/usr/bin/env python3
"""The escalation ladder: what to do about a failure, and when to stop.

`resume.py` answers *where am I*. This answers *what now*, and its whole job is
to make sure the answer is bounded. A loop with no termination criterion does not
terminate; it burns turns producing confident variations of the same wrong fix.

Five rungs, each with a different remedy, because they are different problems:

    retry     rerun the exact command. Product code is not touched.
    repair    a real defect. Smallest change that addresses the root cause.
    restore   undo the loop's own damage: reset to the last verified-good tree.
    rebase    a merge conflict. Fixed against the current target, not by editing.
    retreat   the plan is wrong. Back to Gate 1, which is a human.
    block     the ladder is spent. Stop, with the evidence.

`restore` is the rung that is usually missing, and its absence is why repair
loops feel divergent. Three failed attempts leave the tree worse than they found
it, so attempt four debugs damage the loop did rather than the original defect.
The autocommit hook records `refs/uaios/green/<slug>` on every green fast tier,
which gives this a verified tree to fall back to.

    python tools/loop.py                    # what to do next, one line
    python tools/loop.py --json
    python tools/loop.py --restore          # perform the reset (destructive)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_hl = _load(".claude/hooks/_hooklib.py", "hooklib_loop")
_rs = _load("tools/resume.py", "resume_for_loop")

classify_failure = _hl.classify_failure
failure_budget = _hl.failure_budget
GREEN_REF_PREFIX = "refs/uaios/green/"

RUNG_NOTE = {
    "retry": "Rerun the exact command. Change nothing. If the output is not "
             "byte-identical, it was never transient -- reclassify.",
    "repair": "Reproduce, find the root cause, make the smallest change that "
              "addresses it, rerun the focused check, then the tier.",
    "restore": "Reset to the last verified-good tree and re-attempt once from a "
               "different angle. Three repairs have made this worse, not better.",
    "rebase": "Fetch the current target and rebase. Resolve mechanical conflicts "
              "only; API, migrations, auth or business logic go back to Gate 1.",
    "retreat": "The plan no longer covers this. Write the conflict and return to "
               "plan approval.",
    "block": "Stop. Record the class, the failing command, the last green sha, "
             "and what was tried. A human decides.",
}


def rung(kind: str, attempt: int, budget: int,
         restored: bool = False, has_green: bool = False) -> str:
    """Which rung applies. Pure, and the ordering is the policy.

    security never gets an attempt: a credential in a diff is not something to
    have another go at. transient that outlives its budget is not noise any more
    -- it is an outage, which is a human's problem rather than a repair loop's.
    """
    if kind == "security":
        return "block"
    if kind == "merge":
        return "rebase" if attempt < budget else "retreat"
    if kind == "transient":
        return "retry" if attempt < budget else "block"

    # deterministic and unknown share a ladder: repair on budget, then undo the
    # damage once, then admit the plan is the problem.
    if attempt < budget:
        return "repair"
    if has_green and not restored:
        return "restore"
    return "retreat"


def green_sha(root: Path, slug: str) -> str | None:
    """The last verified-good commit for this unit, or None."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{GREEN_REF_PREFIX}{slug}"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def next_step(root: Path, slug: str | None = None) -> dict:
    """State, class, rung and the reason -- everything the next turn needs.

    Deliberately small. The point of the artifact-passing design is that a
    repair attempt receives the failure and the file it names, not the
    repository and the conversation; a step that carried more would undo that.
    """
    facts = _rs.gather_facts(root, slug)
    state = _rs.derive_state(facts)
    ledger = _rs.read_ledger(root, facts["slug"])

    detail = ledger.get("detail", "") or ""
    kind = ledger.get("failure_class") or classify_failure(detail)[0]
    attempt = int(facts.get("attempts", 0))
    budget = failure_budget(kind)
    sha = green_sha(root, facts["slug"])

    step = {
        "slug": facts["slug"],
        "state": state,
        "next": _rs.NEXT_ACTION.get(state, "?"),
        "last_green": sha,
    }
    if state in ("REPAIR", "BLOCKED"):
        which = rung(kind, attempt, budget,
                     restored=bool(ledger.get("restored")), has_green=bool(sha))
        step.update({
            "failure_class": kind,
            "attempt": attempt,
            "budget": budget,
            "rung": which,
            "note": RUNG_NOTE[which],
        })
    return step


def mark_green(root: Path, slug: str) -> tuple[bool, str]:
    """Point this unit's green ref at HEAD.

    `06-artifact-autocommit.py` does this itself after every checkpoint it makes,
    which covers the automatic path. This covers the other one: a tree verified
    and committed by hand never passes through that hook, so without it a branch
    can be green for a day and still have nothing to fall back to. Only call it
    when the tier actually passed -- the ref's whole value is that it names a
    tree that was verified, not merely one that exists.
    """
    if not slug or slug == "HEAD":
        return False, "no slug -- detached HEAD has no unit of work"
    try:
        proc = subprocess.run(
            ["git", "update-ref", f"{GREEN_REF_PREFIX}{slug}", "HEAD"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, proc.stderr.strip()
    return True, f"{GREEN_REF_PREFIX}{slug} -> {(green_sha(root, slug) or '')[:12]}"


def restore(root: Path, slug: str) -> tuple[bool, str]:
    """Reset hard to the last verified-good tree. Destructive, so it is never
    reached without an explicit flag: it discards work the loop produced, which
    is the point, but not something to do as a side effect."""
    sha = green_sha(root, slug)
    if not sha:
        return False, f"no {GREEN_REF_PREFIX}{slug} -- nothing verified to fall back to"
    try:
        proc = subprocess.run(
            ["git", "reset", "--hard", sha],
            cwd=str(root), capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, proc.stderr.strip()

    ledger = _rs.ledger_path(root, slug)
    try:
        data = _rs.read_ledger(root, slug)
        data["restored"] = True
        data["attempts"] = 0
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
    return True, f"reset to {sha[:12]} and cleared the attempt count"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--restore", action="store_true",
                    help="perform the reset to the last green tree (destructive)")
    ap.add_argument("--mark-green", action="store_true", dest="mark",
                    help="record HEAD as verified-good; only after a green tier")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    slug = args.slug or _rs.gather_facts(root)["slug"]

    if args.mark:
        ok, detail = mark_green(root, slug)
        print(detail)
        return 0 if ok else 1

    if args.restore:
        ok, detail = restore(root, slug)
        print(detail)
        return 0 if ok else 1

    step = next_step(root, slug)
    if args.as_json:
        print(json.dumps(step, indent=2))
    else:
        line = f"{step['slug']}: {step['state']} -> {step['next']}"
        if "rung" in step:
            line += (f" | {step['failure_class']} {step['attempt']}/{step['budget']}"
                     f" -> {step['rung']}")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
