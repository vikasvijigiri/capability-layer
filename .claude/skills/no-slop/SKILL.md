---
name: no-slop
description: Sweep the whole repo for slop and repair what is approved. Triggers include "clean up the repo", "no-slop check", "is this clean enough to ship", "tidy this up", "remove the dead code", "any leftover placeholders". Do NOT use to review a diff (code-review) or to edit before the report is approved. Use this proactively before shipping, even if the user does not ask for a sweep.
when_to_use: when the repo needs a cleanup audit before shipping
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob
---

# No-Slop

Sweep for slop, then repair what the user approves. **Workflow stage 6**, between
`verifying-work` and `code-review`.

That position is deliberate. Running after review would ship the repairs
unreviewed — the exact hole `code-review` exists to close. Running before means
the clean-up lands *inside* the diff the reviewer reads.

**This is not `code-review`.** That skill reads a diff someone is about to ship.
This one reads standing artefacts, diff or no diff: slop accumulates across
sessions, and every turn that produced it was individually green.

Cap visible output at ~500 tokens. Findings with `file:line`, not a tour.

Classify every finding as `P0` release-blocking, `P1` high-risk, or `P2` cleanup.
State the evidence and the smallest safe repair. A clean result means the
automated checks passed and the judgement pass found no unexplained findings;
it is not a guarantee that an unrendered or untested surface is correct.

## Two scopes, two cadences

| Scope | When | Command |
|---|---|---|
| **repo** | stage 6, before shipping — the full sweep | `python tools/test_no_slop.py --scope repo` |
| **layer** | after adding or removing a skill, agent or hook | `python tools/test_no_slop.py` |

The hook watches **volume of change**, which no check can see, because each of
those turns passed. It fires on 8 changed `.claude/` files, or immediately when a
skill, agent or hook is **added or deleted** — that is when trigger overlap
appears, and no single edit can reveal it.

## Two phases, and the gate between them is hard

<HARD-GATE>
Phase 1 REPORTS in full. Phase 2 then repairs **the local group only, without
asking** — the chain has two gates and this is not one.

Deliver every finding before touching anything, even the one-character ones.
Fixing mid-sweep is still forbidden and the reason is unchanged: it makes the
report describe a tree that no longer exists, so the reader cannot check a single
claim against what is actually there.

**Structural findings are never applied here.** Merging or retiring a skill,
re-cutting triggers, deleting a document — those change what fires, and a layer
nobody reviewed is exactly what this skill exists to prevent. They go to
`task-brief` as their own task, reported and not touched.
</HARD-GATE>

## Phase 1 — sweep

**Run the script for your scope first and quote its last line.** It owns
credentials, merge-conflict markers, unresolved placeholders, empty tracked
files, hedging in instruction documents, duplicated guidance sentences, the
500-char description budget, missing negative triggers, missing `## Success` and
`## Routing`, and prose-line budgets. Re-checking those by eye produces a
second, weaker answer to a settled question.

Then read for the four things it cannot decide.

Use this pass order so a cheap failure stops an expensive review:

1. **P0 safety:** credentials, destructive commands, conflict markers, broken
   configuration, unsafe permissions, and claims of completion without proof.
2. **P1 correctness:** unhandled failures, unreachable behavior, missing edge
   cases, stale references, scope violations, and duplicated sources of truth.
3. **P1 product quality:** incomplete loading/empty/error/permission states,
   inaccessible interactions, responsive overflow, or a design token violation.
4. **P2 maintainability:** naming, comments, local consistency, dead weight,
   redundant prose, and cosmetic cleanup.

**1. Overlapping triggers.** One request that two different skills would both
plausibly claim. The script catches identical keywords; it cannot catch *"review
this change"* and *"is this ready to ship"* pointing elsewhere. Test it: write
three requests a real user would send and name which skill owns each. The most
expensive ambiguity there is — the wrong skill still produces confident output
and nothing signals the mismatch.

**2. Duplicate knowledge, paraphrased.** The script catches identical sentences.
It misses one rule stated three ways, which is worse: the versions drift and no
reader can tell which is current. Ask how many files would need editing if that
rule changed. More than one means one owner and pointers.

**3. God skill.** One skill doing two jobs that could be rejected separately.
The signal is **not** length — the prose budget covers that, and the longest
skills here are long because they ship templates, which is why the budget counts
prose rather than raw lines. The signal is whether a reviewer could approve half
of it.

**4. Orchestration leakage.** A skill deciding what comes next rather than
producing an artefact and letting the caller decide.

**5. Design-surface slop.** If the change touches a user-facing surface, read
`DESIGN.md` or the design contract in `brainstormer`; do not recreate its rules here. Check the
implemented surface for semantic tokens, allowed type and spacing scales,
responsive behavior, all meaningful states, visible focus, actual contrast,
alternative text, color-independent meaning, and reduced motion. If there is no
design contract, report a `P1` missing-decision finding and route it to
`brainstormer`; do not invent a visual system during cleanup.

**6. Evidence slop.** For each important claim, ask what artifact proves it:
test output for behavior, a diff for scope, a rendered view for visual quality,
and a log/smoke check for deployment. “Looks fine”, “should work”, and “done”
are not evidence. Missing evidence is a finding, not an invitation to guess.

**This layer breaks that rule deliberately, so read carefully.** Every skill
states a terminal handoff and `.claude/workflow.md` owns the chain — considered,
because a stage with no named successor gets skipped. The finding is therefore
**not** "this skill names a successor". It is one naming a successor that
contradicts `workflow.md`, or naming one conditionally where the workflow
describes no condition.

**Counted provenance** is the one portability smell the script cannot see. It
catches dates and possessive references to the source repository, but a phrase
like "seven instances of this" or "five comparable repos were read" is equally
false elsewhere — and no pattern separates those from the legitimate numbers
sitting beside them ("2-5 minutes", "~500 tokens"). Read for it yourself.

At `--scope repo`, also read for dead weight the script cannot judge: a document
superseded by a newer one and never marked, a `tools/` script nothing calls, a
config key no code reads.

For each changed file, record one of three outcomes: `pass`, `finding`, or
`deliberate exception`. Exceptions must name the rule, reason, owner, and expiry
or follow-up; “intentional” alone is not a justification.

## The report, and the approval gate

A table: `file:line` · the smell · one sentence on what breaks. Then the
verdict: clean, or the count. If nothing is wrong, say so in one line **and name
what you read** — an empty review that lists nothing is indistinguishable from a
review that never ran.

Split the findings into two groups before asking, because they carry different
risk and the user is approving that risk:

| Group | Examples | Disposition |
|---|---|---|
| **Local** | a hedge, a stray `TODO`, a missing `## Success`, a stale count, an over-budget description | Repairable here — contained in one file, mechanically checkable afterwards |
| **Structural** | merging or splitting a skill, retiring one, re-cutting triggers, deleting a document | **`task-brief`, not an edit.** Routing decides which skill fires; re-cutting it mid-sweep ships a layer nobody reviewed |

Then apply the local group. Do not ask — that group is defined by being
contained in one file and mechanically checkable afterwards, which is exactly what
makes it safe to apply unasked. Say what you changed after, with `file:line`.

Structural findings are listed and left alone; name the `task-brief` each one
would become.

## Phase 2 — rectify

Only what was approved, and only the local group.

1. Apply the fixes.
2. **Re-run `test_no_slop.py` at the same scope, plus `test_process_router.py`
   and `test_referenced_paths.py`.** All of them, because repairs here move
   counts and paths the other two own — that broke twice while writing this.
3. Quote the result. Still red is `systematic-debugging`'s trigger, not a retry.
4. Report what changed, and what went to `task-brief` with the reason.

**You are editing the layer that is running.** An edited `SKILL.md` does not
reload in this session, so do not verify by re-triggering it. An edited hook
takes effect immediately and its failure symptom is silence — fire it with
`tools/run_hook.py` against a realistic payload.

## What "clean" can and cannot mean

Green means every decidable check passed and the judgement pass found nothing
this time. It does not mean the repo is provably clean — most of the checklist
needs a reader, which is why this skill exists at all. State the verdict as what
was checked, never as a guarantee.

## Red Flags — you are padding, not sweeping

- Re-stating what the script already printed.
- A finding with no `file:line`.
- "Consider possibly simplifying this section" — name the sentence to cut.
- Flagging a terminal handoff as leakage without opening `workflow.md`.
- Editing anything before the full report has been delivered.
- Applying a structural fix because it "looked obvious".
- Running `--scope layer` at stage 6. Shipping is the repo-wide cadence.
- Inventing a smell to avoid reporting clean.

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the tree | That is `code-review`; slop does not live in one change |
| Fixing as you go | The report then describes a tree that no longer exists |
| Applying a structural fix because it looked contained | Routing decides what fires; it ships a layer nobody reviewed |
| Treating a structural fix as a local one | Routing decides what fires; it ships unreviewed |
| Skipping the re-run after repairs | Repairs move counts and paths two other suites assert |

| Treating skill length as the god-skill signal | The longest skills here carry templates and are correct |

## Next step — you MUST take it

**The terminal state is invoking `code-review`.** The repairs made here are
themselves a change, and an unreviewed clean-up is how a sweep introduces the
defect it was run to prevent. If nothing was repaired, hand over anyway and say
the sweep was clean — the reviewer needs to know it ran.

## Routing

- Mandatory validator: `tools/test_no_slop.py` — a HARD-GATE in phase 1 and a
  re-run in phase 2. Findings only mean something on a tree whose mechanical
  checks already pass.
- Preceded by `verifying-work`. Sweeping work that has not been verified spends
  a reader on a tree that may still change.
- Terminal handoff: `code-review`, then `delivering`.
- Also entered off-chain after a skill, agent or hook is added or removed. That
  entry uses `--scope layer` and returns to whatever was happening.
- Structural findings become their own task via `task-brief`. A sweep worth
  remembering goes to `LOG.md` via `knowledge-manager`.

## Success

Every finding named a `file:line`, the script's output was quoted rather than
re-derived, nothing was edited before the user approved it, structural findings
went to `task-brief` instead of being applied, every suite named in phase 2 was
re-run and quoted, and structural findings were routed rather than applied.
