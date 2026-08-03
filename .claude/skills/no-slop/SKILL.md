---
name: no-slop
description: Use to review AND clean the `.claude/` capability layer itself — overlapping triggers, paraphrased duplicate rules, god skills, orchestration leakage, hedged instructions. Triggers include "audit the capability layer", "clean up the .claude folder", "is the skill layer bloated", "no-slop check", "are the skills clean", "fix the slop", "did the layer rot". Do NOT use on a code diff (that is `code-review`), or to apply a fix before the full report has been approved.
effort: high
model: sonnet
---

# No-Slop

Review the `.claude/` layer for architectural decay, then repair what the user
approves. Entered from any stage, owned by nothing else — decay accumulates
across sessions rather than inside one change, so no diff review can catch it.

**This is not `code-review`.** That skill reads a diff someone is about to ship.
This one reads a standing artefact with no diff involved: a layer rots when the
repo around it moves, not when a line changes.

Cap visible output at ~500 tokens. Findings with `file:line`, not a tour.

## Two phases, and the gate between them is hard

<HARD-GATE>
Phase 1 REPORTS. Phase 2 REPAIRS. No edit before the full report is delivered
and the user has approved what to fix.

Fixing mid-review is not a style rule — it makes the report describe a tree that
no longer exists, so nothing the user approves matches what they read. Deliver
every finding first, even the one-character ones.
</HARD-GATE>

## Phase 1 — review

**Run `python tools/test_no_slop.py` first and quote its last line.** It owns
hedging language, the 500-char description budget, missing `## Success` and
`## Routing` contracts, descriptions with no negative trigger, duplicated
guidance sentences, prose-line budgets, and credentials in tracked files.
Re-checking those by eye produces a second, weaker answer to a settled question.

Then read for the four things it cannot decide.

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

**This repo breaks that rule deliberately, so read carefully.** Every skill
states a terminal handoff and `.claude/workflow.md` owns the chain — considered,
because a stage with no named successor gets skipped. The finding is therefore
**not** "this skill names a successor". It is one naming a successor that
contradicts `workflow.md`, or naming one conditionally where the workflow
describes no condition.

Also cheap to check: a skill assuming another's internals; a hard-coded model or
MCP server where a capability description would survive the vendor changing it;
a section that needs a second read; prose asserting a capability nothing
implements — this repo's recurring failure, seven instances.

## The report, and the approval gate

A table: `file:line` · the smell · one sentence on what breaks. Then the
verdict: clean, or the count. If nothing is wrong, say so in one line **and name
what you read** — an empty review that lists nothing is indistinguishable from a
review that never ran.

Split the findings into two groups before asking, because they carry different
risk and the user is approving that risk:

| Group | Examples | Disposition |
|---|---|---|
| **Local** | a hedge, a missing `## Success`, a stale count, an over-budget description, a duplicated sentence | Repairable here — contained in one file, mechanically checkable afterwards |
| **Structural** | merging or splitting a skill, retiring one, re-cutting triggers, moving an owner | **`task-brief`, not an edit.** Routing decides which skill fires; re-cutting it mid-review ships a layer nobody reviewed |

Ask with `AskUserQuestion`: apply all local fixes, apply a named subset, or
report only. Never infer approval from the user having asked for a review.

## Phase 2 — rectify

Only what was approved, and only the local group.

1. Apply the fixes.
2. **Re-run `tools/test_no_slop.py`, `tools/test_process_router.py` and
   `tools/test_referenced_paths.py`.** All three, because repairs here move
   counts and paths that the other two own — fixing one skill's description has
   twice broken a count asserted somewhere else.
3. Quote the result. Still red is `systematic-debugging`'s trigger, not a retry.
4. Report what changed, and what was deferred to `task-brief` with the reason.

**You are editing the layer that is running.** An edited `SKILL.md` does not
reload in this session, so do not verify by re-triggering it. An edited hook
takes effect immediately and its failure symptom is silence — fire it with
`tools/run_hook.py` against a realistic payload.

## What "clean" can and cannot mean

Green means every decidable check passed and the judgement pass found nothing
this time. It does not mean the layer is provably clean — most of the checklist
needs a reader, which is why this skill exists at all. State the verdict as what
was checked, never as a guarantee.

## Red Flags — you are padding, not reviewing

- Re-stating what `test_no_slop.py` already printed.
- A finding with no `file:line`.
- "Consider possibly simplifying this section" — name the sentence to cut.
- Flagging a terminal handoff as leakage without opening `workflow.md`.
- Editing anything before the report is approved.
- Applying a structural fix because it "looked obvious".
- Inventing a smell to avoid reporting clean.

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the layer | That is `code-review`; decay does not live in one change |
| Fixing as you go | The report then describes a tree that no longer exists |
| Treating a structural fix as a local one | Routing decides what fires; it ships unreviewed |
| Skipping the re-run after repairs | Repairs move counts and paths two other suites assert |
| Treating skill length as the god-skill signal | The longest skills here carry templates and are correct |
| Verifying an edited skill by re-triggering it | Frontmatter does not reload mid-session |

## Routing

- Mandatory validator: `tools/test_no_slop.py`, a HARD-GATE in phase 1 and a
  re-run in phase 2 — findings only mean something on a layer whose mechanical
  checks already pass.
- Entered from any stage, like `research` and `systematic-debugging`. Not on the
  linear chain; consumes no upstream artefact.
- Terminal handoff: none. It reports, repairs on approval, and stops.
- Structural findings become their own task via `task-brief`. A repair worth
  remembering goes to `LOG.md` via `knowledge-manager`.
- Runs naturally after any session that added or edited a skill, agent or hook.

## Success

Every finding named a `file:line`, the script's output was quoted rather than
re-derived, nothing was edited before the user approved it, structural findings
went to `task-brief` instead of being applied, and every suite named in phase 2
was re-run and quoted after the repairs.
