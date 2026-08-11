---
name: no-slop
description: Sweep a codebase for slop, then repair what is approved. Finds dead code, placeholders, hedging, duplicated guidance and unverified claims. Triggers include "clean up this repo", "no-slop check", "is this clean enough to ship", "tidy this up", "remove the dead code", "any leftover placeholders", "audit this before we merge". Do NOT use to review a single diff before it lands — that's code review. Use this proactively before shipping, even if the user doesn't ask for a sweep.
when_to_use: when a unit of work is about to ship, merge or hand off, and when a component has just been added or removed
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# No-Slop

Sweep for slop, then repair what the user approves. Run this after work has
been verified and before it's reviewed for shipping — not instead of either.

That position is deliberate. Running after review would ship the repairs
unreviewed — the exact hole review exists to close. Running before verification
means you're sweeping a tree that's about to change anyway, wasting a reader's
attention on findings that won't survive.

**This is not a diff review, and `code-review` is.** The two run at adjacent
stages and can read the same files, so the division is stated on both sides
rather than assumed:

| | Reads | Answers |
|---|---|---|
| this skill | standing artefacts, **including files the change never touched** | has slop accumulated here |
| `code-review` | the diff, and under `small` its direct callers | is this change correct and safe to ship |

The load-bearing half is "including files the change never touched". Slop
accumulates across sessions and every turn that produced it was individually
fine at the time, so a sweep restricted to the diff cannot see the thing it
exists to find. A finding here about an unchanged file is the skill working; the
same finding from `code-review` would be scope creep.

A boundary asserted in one sentence and checked by nothing is a boundary that
drifts. `tools/test_process_router.py` fails if either skill stops naming the
other — the same back-reference shape it uses for agents and their dispatchers,
and the weakest mechanism that is still a mechanism.

Cap visible output at ~500 tokens. Findings with `file:line`, not a tour.

Classify every finding as `P0` release-blocking, `P1` high-risk, or `P2`
cleanup. State the evidence and the smallest safe repair. A clean result means
the automated checks passed and the judgement pass found no unexplained
findings; it is not a guarantee that an unrendered or untested surface is
correct.

## Scope is one dimension, set per run

Don't split this into fixed categories like "whole project" vs "just the new
part" — scope is however much of the tree this run is answerable for, and it
should be stated in the report so the reader knows what was and wasn't covered.
Typical triggers for running it:

- **Before shipping, merging, or handing off** a meaningful unit of work — the
  default case, and it should cover everything in that unit plus anything it
  touches.
- **After adding or removing a component** — a module, service, endpoint,
  config surface, dependency, script, or any other named unit the project is
  built from. This is when overlap, duplication, and dead references appear,
  and no single edit reveals them; a narrower sweep centered on the new or
  removed component plus its neighbors is usually enough.
- **On a cadence or a change-volume threshold you set** — e.g., weekly, or once
  N files have changed since the last sweep. Pick a number that fits the
  project's pace; the point is that slop is invisible turn-by-turn and only
  shows up at volume.

If the request doesn't specify scope, ask, or default to the smallest scope
that would still catch what prompted the request — and say which you picked.

## Two phases, and the gate between them is hard

<HARD-GATE>
Phase 1 REPORTS in full. Phase 2 then repairs **the local group only**, and
only after the user has seen every finding.

Deliver every finding before touching anything, even the one-character ones.
Fixing mid-sweep is still forbidden and the reason is unchanged: it makes the
report describe a tree that no longer exists, so the reader cannot check a
single claim against what is actually there.

**Structural findings are never applied here.** Merging or splitting a
component, renaming a public interface, deleting a document, re-cutting how
work is routed — those change what exists or what fires, and a change nobody
reviewed is exactly what this skill exists to prevent. They're reported and
handed to whatever planning or decision process the project uses, as their own
piece of work, not folded into this sweep.
</HARD-GATE>

## Phase 1 — sweep

**Run the project's automated checks first, if it has any** — linters,
formatters, type checkers, custom consistency scripts, CI's own lint stage —
and quote the last relevant line of output. Those own credentials,
merge-conflict markers, unresolved placeholders, empty tracked files, dead
imports, and anything else objectively decidable. Re-checking those by eye
produces a second, weaker answer to a settled question.

If the project has **no** automated checks for a category the sweep would
otherwise catch mechanically, say so explicitly as a finding (usually `P2`,
`P1` if it's a category that's bitten this project before) — the absence is
itself information, not a reason to skip the category.

Then read for what automation can't decide. Use this pass order so a cheap
failure stops an expensive review:

1. **P0 safety:** credentials, destructive commands, conflict markers, broken
   configuration (including a tool or skill whose declared permissions don't
   cover the steps it instructs), unsafe defaults, and claims of completion
   without proof.
2. **P1 correctness:** unhandled failures, unreachable code paths, missing
   edge cases, stale references, scope violations, and duplicated sources of
   truth.
3. **P1 product quality:** incomplete loading/empty/error/permission states,
   inaccessible interactions, responsive overflow, or a design-token violation
   on any user-facing surface.
4. **P2 maintainability:** naming, comments, local consistency, dead weight,
   redundant prose, and cosmetic cleanup.

**1. Overlapping responsibilities.** Two functions, modules, endpoints, docs,
or automations that would both plausibly handle the same request or input.
Automated checks catch identical names; they can't catch two things described
differently that actually compete. Test it: write three realistic inputs and
name which one owns each. The most expensive ambiguity there is — the wrong
one still produces confident output and nothing signals the mismatch.

**2. Duplicate knowledge, paraphrased.** Automated checks catch identical
text. They miss one rule stated three different ways, which is worse: the
versions drift and no reader can tell which is current. Ask how many places
would need editing if that rule changed — count paragraphs and comments, not
just files. More than one means pick an owner and replace the rest with a
pointer.

**3. God component.** One function, class, file, or service doing two jobs
that could be reviewed or replaced separately. The signal is **not** length —
long is fine when the length is inherent to the job (a template, a full
schema, a reference table). The signal is whether a reviewer could approve or
revert half of it without touching the rest.

**4. Orchestration leakage.** Something deciding what happens next instead of
producing its result and letting the caller decide. Watch for hardcoded
sequencing, hidden retries, or a component reaching outside its own boundary
to trigger unrelated work.

**5. Design-surface slop.** If the change touches a user-facing surface, read
the project's design system or style guide if one exists; don't invent rules
here. Check the implemented surface for consistent tokens (color, type,
spacing), all meaningful states (loading, empty, error, disabled), visible
focus, actual contrast, alt text, color-independent meaning, and reduced
motion. If there's no design contract to check against, report a `P1`
missing-decision finding rather than inventing a visual system during cleanup.

**6. Evidence slop.** For each important claim, ask what artifact proves it:
test output for behavior, a diff for scope, a rendered view for visual
quality, a log or smoke check for deployment. "Looks fine," "should work," and
"done" are not evidence. Missing evidence is a finding, not an invitation to
guess.

**Named handoffs get the same scrutiny, carefully.** If a component states
what should happen after it (a next step, a caller, a downstream owner),
that's fine on its own — a step with no named successor is one that's easy to
forget. The finding is **not** "this names what comes next." It's a named
successor that contradicts how the project actually routes work elsewhere, or
one stated unconditionally where the real logic is conditional.

**Counted provenance.** A number can be true of the current state and false
the moment anything changes — "seven call sites," "three teams affected,"
"five files reference this." That's different from a number that's generic
guidance and stays true regardless — "retry up to 3 times," "cap output at
~500 tokens." Automated checks can flag dates and possessive references but
can't tell these two kinds of number apart, since a bare count doesn't say
which one it is. Read each one and ask: does this describe the current
specific state, or is it a rule that would still hold after the state
changes?

At wider scopes, also read for dead weight nothing mechanical can judge: a
document superseded by a newer one and never marked as such, a script nothing
calls, a config key nothing reads, a dependency nothing imports.

For each unit reviewed, record one of three outcomes: `pass`, `finding`, or
`deliberate exception`. Exceptions must name the rule, the reason, an owner,
and an expiry or follow-up condition; "intentional" alone is not a
justification.

## The report

A table: `file:line` · the smell · one sentence on what breaks. State the
scope that was covered. Then the verdict: clean, or the count. If nothing is
wrong, say so in one line **and name what you read** — an empty review that
lists nothing is indistinguishable from a review that never ran.

Split the findings into two groups, because they carry different risk and only
one of them is safe to act on without asking:

| Group | Examples | Disposition |
|---|---|---|
| **Local** | a hedge, a stray `TODO`, a missing doc section, a stale count, an over-long description, dead code with no external reference | Repairable now — contained in one file, mechanically checkable afterwards |
| **Structural** | merging or splitting a component, renaming a public interface, retiring a document, changing how work is routed between parts of the system | **Its own unit of work, not an edit.** It changes what exists or what fires; doing it mid-sweep ships a change nobody reviewed |

Local findings are applied automatically in Phase 2, right after this report —
that's what makes them local: contained in one file and mechanically checkable
afterwards. Structural findings are never applied here, no matter how obvious
the fix looks.

Route each structural finding to whatever planning, RFC, or decision process
the project uses, and let that process decide from there — the question that
matters is *is the approach settled?* "Retire this dead document" is settled
and can go straight into a task. "This component overlaps its neighbor" is
not settled — merging them or splitting the responsibility are both live
options — and skipping straight to a task bakes in whichever answer came to
mind first. Name the finding and the tradeoff; don't pick the destination
yourself if the project has a process meant to make that call.

## Phase 2 — rectify

Only what was approved, and only the local group.

1. Apply the fixes.
2. **Re-run the project's automated checks at the same scope.** Repairs move
   line numbers, counts, and references that other checks may assert against
   — confirm nothing else broke.
3. Quote the result. Still red is a debugging problem, not a reason to retry
   the same fix.
4. Report what changed, and which structural findings were handed off, with
   the reason and the destination given.

**You may be editing something that's currently running or in use** — a
config file being read by a live process, a script invoked elsewhere, a
document another tool parses. An edited file doesn't necessarily reload in the
current session, so don't verify by re-triggering the very thing you just
edited; check its effect the way an outside caller would.

## What "clean" can and cannot mean

Green means every decidable check passed and the judgement pass found nothing
this time. It does not mean the project is provably clean — most of the
checklist needs a reader, which is why this skill exists at all. State the
verdict as what was checked, never as a guarantee.

## Red Flags — you are padding, not sweeping

- Re-stating what an automated check already printed.
- A finding with no `file:line`.
- "Consider possibly simplifying this section" — name the sentence to cut.
- Flagging a named handoff as leakage without checking how the project
  actually routes work.
- Editing anything before the full report has been delivered.
- Applying a structural fix because it "looked obvious."
- Sweeping a much narrower scope than the request implied, to finish faster.
- Inventing a smell to avoid reporting clean.
- Restating a rule you already stated, in different words, because the first
  version "didn't feel emphatic enough."

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the tree | Slop doesn't live in one change; it accumulates across many that each looked fine |
| Fixing as you go | The report then describes a tree that no longer exists |
| Treating a structural fix as a local one | It changes what exists or what fires; it ships a change nobody reviewed |
| Skipping the re-run after repairs | Repairs move counts and references other checks may assert against |
| Treating length as the god-component signal | Some units are long because the length is inherent to the job, and that's correct |
| Giving a tool or skill fewer permissions than its own steps require | It can report the gate but can't clear it |
| Fixing scope silently instead of stating it in the report | The reader can't tell what was and wasn't covered |

## Next step — you MUST take it

**The terminal state is invoking `code-review`.** The repairs made here
are themselves a change, and an unreviewed clean-up is how a sweep introduces
the defect it was run to prevent. If nothing was repaired, hand over anyway
and say the sweep was clean — the reviewer needs to know it ran.

## Routing

- Mandatory validator: the project's own automated checks, run at the start of
  Phase 1 and again in Phase 2. Findings only mean something on a tree whose
  mechanical checks already pass.
- Preceded by verification of the work being swept. Sweeping unverified work
  spends a reader on a tree that may still change.
- Terminal handoff: `code-review`, then `delivering`.
- Also entered off-chain after a component is added or removed, scoped to
  that component and its neighbors, then returns to whatever was happening.
- Structural findings become their own unit of work, routed to the project's
  planning or decision process rather than applied here. A sweep worth
  remembering — a recurring smell, a pattern worth documenting — goes wherever
  the project records decisions or lessons, if it keeps one.

## Success

Every finding named a `file:line`, the scope covered was stated, automated
check output was quoted rather than re-derived, nothing was edited before the
user approved it, structural findings were routed rather than applied, and
every relevant check was re-run and quoted after repairs.