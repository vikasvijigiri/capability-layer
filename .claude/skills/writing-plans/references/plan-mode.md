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

## The skill enters plan mode itself

**`EnterPlanMode` exists, and this skill calls it** at the start of Stage C,
before it reads the repository to plan. The user consents to the prompt that
tool raises — its own contract says it *"REQUIRES user approval"* — so nobody
has to remember to select a mode before asking for work.

That is the whole reachability story, and it took a correction to get right.
This file previously said:

> There is no tool for it… no skill, hook or command can put the session into
> plan mode.

**That was false.** `EnterPlanMode` is a documented tool, and the refusal
message from `ExitPlanMode` names it outright:

    You are not in plan mode. To enter plan mode, call the EnterPlanMode tool first.

The consequence was not cosmetic. `ExitPlanMode` refuses outside plan mode, and
the same change that made it Gate 1 also removed `AskUserQuestion` from this
skill — so **Gate 1 had no working mechanism unless the session happened to
already be in plan mode.** The chain's first gate was conditional on something
nothing controlled, and the assertion guarding it passed the whole time because
it checked that the tool was *named in the file* rather than that the gate was
*reachable*.

It is the defect this repository names most often — prose asserting what the
wiring does not implement — committed by the file written to explain the gate.

## `AskUserQuestion` is banned from the approval, not from the skill

The narrower rule, and the one that matches the tools' own documentation.
`EnterPlanMode` says plainly: *"Use `AskUserQuestion` if you need to clarify
approaches"* inside plan mode, and *"Do NOT use `AskUserQuestion` to ask 'Is this
plan okay?'"*

So:

| | |
|---|---|
| The **approval** at Gate 1 | `ExitPlanMode`, and only that |
| A **clarification** while planning | `AskUserQuestion` is allowed |

The first version of this rule banned the tool outright. That was over-tight, it
contradicted the official guidance, and it is what left the gate unreachable
when `ExitPlanMode` refused.

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
