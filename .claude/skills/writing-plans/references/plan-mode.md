---
name: plan-mode
description: How Gate 1 works when planning happens in plan mode - which tool asks for approval, why there is only one, and when TASK.md is written given that plan mode is read-only. Read before changing the gate or moving TASK.md. Do NOT read for ordinary planning, or to learn what a plan contains - that is plan-document.md.
---

# Plan mode and Gate 1

## One approval, one tool

Gate 1 is `ExitPlanMode`. Its contract is precisely this gate — it *"inherently
requests user approval"* — and it says outright not to pair it with a second
question.

So `writing-plans` must never call `AskUserQuestion`, for the markers or for the
approval. Two mechanisms for one approval means the plan is approved twice and
one of them is theatre; and the one that is theatre is whichever the reader
answers second, which is not something the file can control.

`test_process_router.py` checks each gate against **its own** tool —
`ExitPlanMode` for Gate 1, `AskUserQuestion` for Gate 2 — rather than checking
both against one. A blanket check passes on any incidental mention, which is a
marker that reads as a gate and stops nothing.

## Plan mode is read-only, so `TASK.md` moves

Plan mode permits no edit except the plan itself. Stage A therefore **drafts**
the six fields and writes `TASK.md` **immediately after `ExitPlanMode` returns**,
as the first act of execution.

Ownership does not move. This skill still owns those six fields and their
`(inferred)` markers; only the moment does.

The alternative — dropping `TASK.md` from stage 1 altogether — was rejected
because two mechanisms read it:

- `session-start/02-bootstrap-docs.py` injects its `## Active` block at the
  start of every session;
- `_hooklib.declaration_sources` counts it as one of the two things that can
  declare a path, and the minimal-diff commit gate does not apply where neither
  exists.

Removing it would silently turn that gate off for every unit of work that had
not yet written a plan.

## Nothing here can switch permission mode

There is no tool for it. Exiting plan mode returns to whatever mode was active
before, and no skill, hook or command can put the session into plan mode or take
it out of one on its own.

Any instruction claiming otherwise is describing a capability that does not
exist — which is this repository's most-repeated defect, prose asserting what
the wiring does not implement. If planning needs to happen in plan mode, a person
enters it.

## Record the decision, whichever it was

    python tools/chain.py --gate 1 --decision approve|revise|reject --reason "<their words>"

Appended to the same append-only ledger the chain instrument writes, so "what
was decided, when, and why" is one query rather than an archaeology exercise
across a transcript nobody kept.

**The reason is stored verbatim.** `tools/loop.py` refuses to re-present a plan
body whose hash has not changed, so a rejection that was summarised rather than
quoted produces a second submission that looks new and is not.

Record a rejection as readily as an approval. A gate log holding only approvals
answers the easy question and loses the one worth having.

## The three outcomes must all stay reachable

Approval is not the only door, and a plan presented as though it were is a gate
in name only:

| Outcome | Means |
|---|---|
| Approve | write `## Approved`, hand off to `executing-plans` |
| Revise | rejected; the user's own words become the brief |
| Reject | the approach is wrong; return to `brainstormer` |

Revise and reject are recorded **verbatim**. A reason paraphrased is a reason
lost, and `tools/loop.py` refuses to re-present a plan body whose hash has not
changed — so a rejection that was summarised rather than quoted produces a
second submission that looks new and is not.
