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

A second, separate ladder covers one subagent dispatch, because a dispatch fails
in ways a check does not: it can report that its brief was incomplete, or die
before reporting anything. Its rungs are supply, escalate, serialize, diagnose --
and `serialize`, pulling the task back into the main context, is the one that
makes it terminate.

    python tools/loop.py                    # what to do next, one line
    python tools/loop.py --json
    python tools/loop.py --restore          # perform the reset (destructive)
    python tools/loop.py --agent-status BLOCKED --attempt 1
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


GATE_RUNG_NOTE = {
    "present": "Ask with AskUserQuestion. Offer approve, revise, and reject — and "
               "say in the question that the revise/reject options take the "
               "reason as free text. Record whatever comes back verbatim.",
    "revise": "Rejected with a reason. Address it, change the plan, re-present. "
              "The recorded reason is the brief for this revision.",
    "unchanged": "REFUSE to re-present. The plan is byte-for-byte what was "
                 "rejected last time, so asking again spends the user's "
                 "attention on a question they have already answered. Change "
                 "something or retreat.",
    "retreat": "Three rejections of the same plan means the approach is wrong, "
               "not the wording. Return to the design stage; a fourth draft of "
               "a plan nobody wants is not convergence.",
}


def gate_rung(rejections: int, changed: bool,
              max_rejections: int = 3) -> str:
    """What to do at a human gate. Pure, and deliberately NOT the failure ladder.

    A rejection is not a defect. There is no retry budget on a person's
    judgement, and the gate stays terminal for automation however many times it
    is answered -- nothing here ever proceeds without the approval.

    What IS bounded is *re-asking*. Two things a loop can get wrong at a gate:
    presenting the identical artifact again, and grinding out a fourth draft
    when the objection was never about the draft.
    """
    if rejections == 0:
        return "present"
    if not changed:
        return "unchanged"
    if rejections >= max_rejections:
        return "retreat"
    return "revise"


AGENT_RUNG_NOTE = {
    "accept": "Read the diff before ticking anything. An agent reporting DONE is "
              "a claim; the diff and its test output are the evidence.",
    "note": "Accept the work and record the concern verbatim where the reviewer "
            "will read it. A concern paraphrased is a concern lost.",
    "supply": "It named exactly what the brief lacked. Add that one fact and "
              "re-dispatch. Do not add the whole plan -- the brief being small is "
              "why this is cheap.",
    "escalate": "Re-dispatch once on a stronger model with the failure attached. "
                "Never retry BLOCKED unchanged on the same model: same input, "
                "same weights, same answer.",
    "serialize": "Stop dispatching this task. Run it inline, in the main context, "
                 "where you can see what the agent could not.",
    "diagnose": "This is no longer a dispatch problem. Hand the failure to "
                "`systematic-debugging` with the reports from every attempt.",
    "block": "Stop. Record every status, every brief, and what each attempt "
             "changed. A human decides.",
}

# What an agent's own status means for the next dispatch. Kept beside the failure
# ladder because it is the same kind of object -- a bounded ladder over an
# unreliable step -- and deliberately NOT the same table, because the remedies
# do not overlap: you cannot `rebase` a subagent, and `restore` is meaningless
# for a worker that was isolated in its own worktree.
#
# Added 2026-08-07. Until then a dispatch had no ladder at all: `implementer`
# said "never let a BLOCKED retry unchanged on the same model", which is a rule
# the dispatcher had to remember, with nothing computing the alternative. Every
# other unreliable step in this layer got a table; this one got a sentence.
AGENT_BUDGETS = {
    "DONE": 0,
    "DONE_WITH_CONCERNS": 0,
    # A named missing fact is not a defect, and supplying it is nearly free. Two,
    # because a brief can genuinely lack two things; a third means the brief was
    # never the problem.
    "NEEDS_CONTEXT": 2,
    # One escalation, then inline. A second stronger model on the same brief is
    # the same bet twice.
    "BLOCKED": 1,
    # The dispatch itself died -- a terminal API error, a killed process. That is
    # transient until it happens twice.
    "DIED": 1,
}


def agent_rung(status: str, attempt: int = 0, serialized: bool = False) -> str:
    """What to do about one subagent's result. Pure, total, order is the policy.

    `serialized` records that the task has already been pulled back into the main
    context. Without it the ladder would offer `serialize` forever, which is the
    exact shape of non-termination `test_loop.py` exists to rule out.
    """
    normalised = (status or "").strip().upper().replace("-", "_")
    if normalised == "DONE":
        return "accept"
    if normalised == "DONE_WITH_CONCERNS":
        return "note"

    budget = AGENT_BUDGETS.get(normalised, 1)

    if normalised == "NEEDS_CONTEXT":
        if attempt < budget:
            return "supply"
        return "diagnose" if serialized else "serialize"
    if normalised == "BLOCKED":
        if attempt < budget:
            return "escalate"
        return "diagnose" if serialized else "serialize"
    if normalised == "DIED":
        if attempt < budget:
            return "escalate"
        return "diagnose" if serialized else "serialize"

    # An unrecognised status is a defect in the agent's own contract, not noise.
    # It gets one clarifying re-dispatch and then stops, because a worker that
    # cannot report its own state is not one to keep feeding work to.
    if attempt < 1:
        return "supply"
    return "block"


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
    if state in ("WAITING_PLAN_APPROVAL", "WAITING_SHIP_APPROVAL"):
        which = gate_rung(int(facts.get("rejections", 0)),
                          bool(facts.get("plan_changed_since_rejection", True)))
        step.update({
            "gate_rung": which,
            "rejections": facts.get("rejections", 0),
            "last_reason": (facts.get("rejection_reasons") or [None])[-1],
            "note": GATE_RUNG_NOTE[which],
        })
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
    ap.add_argument("--agent-status", dest="agent_status",
                    help="a subagent's reported status: DONE, DONE_WITH_CONCERNS, "
                         "NEEDS_CONTEXT, BLOCKED or DIED")
    ap.add_argument("--attempt", type=int, default=0,
                    help="how many times this task has already been dispatched")
    ap.add_argument("--serialized", action="store_true",
                    help="the task has already been pulled back into the main context")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    slug = args.slug or _rs.gather_facts(root)["slug"]

    if args.agent_status:
        which = agent_rung(args.agent_status, args.attempt, args.serialized)
        payload = {
            "status": args.agent_status.upper(),
            "attempt": args.attempt,
            "budget": AGENT_BUDGETS.get(args.agent_status.strip().upper(), 1),
            "rung": which,
            "note": AGENT_RUNG_NOTE[which],
        }
        if args.as_json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"{payload['status']} attempt {args.attempt}"
                  f"/{payload['budget']} -> {which}\n{payload['note']}")
        return 0

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
