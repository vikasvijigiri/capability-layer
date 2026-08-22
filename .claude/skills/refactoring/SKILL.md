---
name: refactoring
description: Sweep a codebase for accumulated slop, then repair what is approved. Finds dead code, unused files, placeholders and TODOs, stale counts, dangling references, duplicated guidance, hedging, and claims nothing backs - reading standing artefacts including files the change never touched. Triggers include "clean up this repo", "tidy this up", "refactoring check", "is this clean enough to ship", "audit this before we merge", "remove the dead code", "anything unused", or "tech debt". Do NOT use to review a single diff before it lands - that is code-review. Use this proactively before shipping, even if the user does not ask for a sweep.
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Refactoring

Sweep for slop, then repair what the user approves. Runs after work is verified
and before it is reviewed — not instead of either. Running after review would
ship the repairs unreviewed; running before verification sweeps a tree that is
about to change.

**This is not a diff review, and `code-review` is.** Both can read the same
files, so the division is stated on both sides:

| | Reads | Answers |
|---|---|---|
| this skill | standing artefacts, **including files the change never touched** | has slop accumulated here |
| `code-review` | the diff, and under `small` its direct callers | is this change correct and safe to ship |

"Including files the change never touched" is the load-bearing half: slop
accumulates across sessions and every turn that produced it was fine at the
time, so a sweep restricted to the diff cannot see what it exists to find.

**`capability-layer-maintenance` is the other neighbour**, divided by question
rather than directory: sweeping `.claude/` is this skill's job, deciding what
its contracts should be is that skill's. A dead reference is **reported here and
repaired there**. `tools/test_process_router.py` fails if either neighbour stops
naming the other.

Cap visible output at ~500 tokens. Findings with `file:line`, not a tour.

Classify every finding `P0` release-blocking, `P1` high-risk, or `P2` cleanup,
with the evidence and the smallest safe repair. Clean means the automated checks
passed and the judgement pass found nothing — not that an unrendered or untested
surface is correct.

## Scope is one dimension, set per run

Scope is however much of the tree this run is answerable for, and it is stated
in the report so the reader knows what was covered. Typical triggers:

- **Before shipping, merging or handing off** — the default; covers the unit
  plus anything it touches.
- **After adding or removing a component** — where overlap, duplication and dead
  references appear, and no single edit reveals them.
- **On a cadence or change-volume threshold you set** — slop is invisible
  turn-by-turn and shows up at volume.

If the request doesn't specify, ask, or default to the smallest scope that would
catch what prompted the request — and say which you picked.

At a scope wide enough that Phase 1 would take many serial passes, `ultracode`
(or "use a workflow to sweep `<scope>`") parallelizes it across Claude Code's
native dynamic-workflow subagents — worth suggesting to the user rather than
sweeping serially, when the scope is that wide.

## Two phases, and the gate between them is hard

<HARD-GATE>
Phase 1 REPORTS in full. Phase 2 repairs **the local group only**, and only
after the user has seen every finding.

Fixing mid-sweep makes the report describe a tree that no longer exists, so the
reader cannot check a single claim against what is there.

**Structural findings are never applied here.** Merging or splitting a
component, renaming a public interface, deleting a document, re-cutting how work
is routed — those change what exists or what fires, and an unreviewed change is
what this skill exists to prevent. Report them and hand them to planning as
their own piece of work.
</HARD-GATE>

## Phase 1 — sweep

**Run the project's automated checks first** and quote the last relevant line.
**Take the scoped tier** (`python tools/run_checks.py --scoped`): this stage runs
mid-chain and the full tier belongs to the last verification before delivery.
Phase 2's re-run is scoped too. Those checks own credentials, conflict markers,
placeholders, empty files, dead imports — anything objectively decidable.
Re-checking them by eye is a second, weaker answer to a settled question.

If the project has **no** automated check for a category, say so as a finding
(usually `P2`, `P1` if it has bitten this project) — the absence is information.

Then read for what automation cannot decide, cheapest failure first:

1. **P0 safety:** credentials, destructive commands, conflict markers, broken
   configuration (including a tool whose declared permissions don't cover the
   steps it instructs), unsafe defaults, completion claimed without proof.
2. **P1 correctness:** unhandled failures, unreachable paths, missing edge
   cases, stale references, scope violations, duplicated sources of truth.
3. **P1 product quality:** incomplete loading/empty/error/permission states,
   inaccessible interactions, responsive overflow, design-token violations.
4. **P2 maintainability:** naming, comments, consistency, dead weight.

**1. Overlapping responsibilities.** Two things that would both plausibly handle
the same input. Automation catches identical names, not two things described
differently that compete. Test it: write three realistic inputs and name which
one owns each. The wrong one still produces confident output.

**2. Duplicate knowledge, paraphrased.** One rule stated three ways drifts, and
no reader can tell which is current. Count the paragraphs that would need
editing if the rule changed; more than one means pick an owner and leave
pointers.

**3. God component.** One unit doing two jobs that could be reviewed or replaced
separately. The signal is **not** length — it is whether a reviewer could
approve or revert half of it without touching the rest.

**4. Orchestration leakage.** Something deciding what happens next instead of
producing its result and letting the caller decide.

**5. Design-surface slop.** On a user-facing surface, read the project's design
system if one exists; don't invent rules. Check tokens, all meaningful states,
visible focus, contrast, alt text, colour-independent meaning, reduced motion.
No design contract to check against is a `P1` missing-decision finding.

**6. Evidence slop.** For each important claim, ask what artifact proves it.
"Looks fine" and "done" are not evidence. Missing evidence is a finding, not an
invitation to guess.

**Named handoffs get scrutiny, carefully.** A component stating what comes next
is fine — a step with no named successor is easy to forget. The finding is a
successor that *contradicts* how the project routes work, or one stated
unconditionally where the real logic is conditional.

**Counted provenance.** A number can be true now and false after any change
("seven call sites"), or generic and durable ("retry 3 times"). Automation
cannot tell them apart. Ask: does this describe current state, or a rule that
survives the state changing?

At wider scopes, read for dead weight nothing mechanical can judge: a superseded
document never marked as such, a script nothing calls, a config key nothing
reads, a dependency nothing imports.

Record each unit as `pass`, `finding`, or `deliberate exception`. An exception
names the rule, the reason, an owner, and an expiry; "intentional" is not a
justification.

## The report

A table: `file:line` · the smell · one sentence on what breaks. State the scope
covered, then the verdict: clean, or the count. If nothing is wrong, say so in
one line **and name what you read** — an empty review is indistinguishable from
one that never ran.

One filled instance, so the row shape is unambiguous rather than assumed:

| file:line | smell | what breaks |
|---|---|---|
| `documentation/SKILL.md:5` | malformed frontmatter — a stray list item folded into `when_to_use` by YAML's scalar-continuation rule | the live trigger text every skill listing shows ends with junk appended, not a formatting artifact |

And a clean verdict reads: *"Scope: `.claude/skills/refactoring/references/`. Both
files read in full. Clean — no TODOs, no dangling links, no stale counts."*

Split the findings, because only one group is safe to act on unasked:

| Group | Examples | Disposition |
|---|---|---|
| **Local** | a hedge, a stray `TODO`, a stale count, dead code with no external reference | Applied in Phase 2 — contained in one file, mechanically checkable after |
| **Structural** | merging or splitting a component, renaming an interface, retiring a document, changing how work is routed | **Its own unit of work.** It changes what exists or what fires |

Route each structural finding to the project's planning or decision process and
let that decide. "Retire this dead document" is settled and can become a task;
"this component overlaps its neighbour" is not — merging and splitting are both
live, and skipping to a task bakes in whichever came to mind first.

## Phase 2 — rectify

Only what was approved, and only the local group.

1. Apply the fixes.
2. **Re-run the project's automated checks at the same scope.** Repairs move
   line numbers, counts and references other checks assert against.
3. Quote the result. Still red is a debugging problem, not a reason to retry.
4. Report what changed, and which structural findings were handed off, where.

**You may be editing something in use** — a config a live process is reading, a
script invoked elsewhere. An edited file does not necessarily reload, so check
its effect the way an outside caller would rather than by re-triggering what you
just edited.

## What "clean" can and cannot mean

Green means every decidable check passed and the judgement pass found nothing
this time. It does not mean the project is provably clean — most of the
checklist needs a reader, which is why this skill exists. State the verdict as
what was checked, never as a guarantee.

## Red Flags — you are padding, not sweeping

- Re-stating what an automated check already printed.
- A finding with no `file:line`.
- "Consider possibly simplifying this section" — name the sentence to cut.
- Flagging a named handoff as leakage without checking how the project routes work.
- Editing anything before the full report has been delivered.
- Applying a structural fix because it "looked obvious."
- Sweeping a narrower scope than the request implied, to finish faster.
- Inventing a smell to avoid reporting clean.

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the tree | Slop accumulates across many changes that each looked fine |
| Fixing as you go | The report then describes a tree that no longer exists |
| Treating a structural fix as local | It ships a change nobody reviewed |
| Skipping the re-run after repairs | Repairs move counts other checks assert against |
| Treating length as the god-component signal | Some units are long because the job is |
| Giving a tool fewer permissions than its own steps require | It can report the gate but not clear it |
| Fixing scope silently instead of stating it | The reader can't tell what was covered |

## Next step — you MUST take it

**The terminal state is invoking `code-review`.** The repairs made here are
themselves a change, and an unreviewed clean-up is how a sweep introduces the
defect it was run to prevent. If nothing was repaired, hand over anyway and say
the sweep was clean — the reviewer needs to know it ran.

## Routing

- Mandatory validator: the project's automated checks, at the start of Phase 1
  and again in Phase 2. Findings only mean something on a mechanically green tree.
- Preceded by verification of the work being swept.
- Terminal handoff: `code-review`, then `release-git`.
- Also entered off-chain after a component is added or removed, scoped to that
  component and its neighbours, then returns to whatever was happening.
- Structural findings become their own unit, routed to planning rather than
  applied. A recurring smell goes wherever the project records lessons.

## Success

Every finding named a `file:line`, the scope covered was stated, automated check
output was quoted rather than re-derived, nothing was edited before approval,
structural findings were routed rather than applied, and every relevant check
was re-run and quoted after repairs.
