---
name: no-slop
description: Use before shipping, to sweep the whole repo for slop and repair what the user approves — credentials, conflict markers, stray placeholders, hedged instructions, overlapping skill triggers, duplicate rules, god skills. Also on `.claude/` drift, named by `07-layer-drift.py`. Triggers include "clean up the repo", "no-slop check", "audit the capability layer", "is this clean enough to ship", "fix the slop". Do NOT use to review a diff (`code-review`) or to edit before the report is approved.
effort: high
model: sonnet
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

## Two scopes, two cadences

| Scope | When | Command |
|---|---|---|
| **repo** | stage 6, before shipping — the full sweep | `python tools/test_no_slop.py --scope repo` |
| **layer** | when `07-layer-drift.py` names this skill | `python tools/test_no_slop.py` |

The hook watches **volume of change**, which no check can see, because each of
those turns passed. It fires on 8 changed `.claude/` files, or immediately when a
skill, agent or hook is **added or deleted** — that is when trigger overlap
appears, and no single edit can reveal it.

**Clear the counter as your last step**, or the nudge repeats:

```bash
python .claude/hooks/post-run/07-layer-drift.py --swept
```

## Two phases, and the gate between them is hard

<HARD-GATE>
Phase 1 REPORTS. Phase 2 REPAIRS. No edit before the full report is delivered
and the user has approved what to fix.

Fixing mid-review is not a style rule — it makes the report describe a tree that
no longer exists, so nothing the user approves matches what they read. Deliver
every finding first, even the one-character ones.
</HARD-GATE>

## Phase 1 — sweep

**Run the script for your scope first and quote its last line.** It owns
credentials, merge-conflict markers, unresolved placeholders, empty tracked
files, hedging in instruction documents, duplicated guidance sentences, the
500-char description budget, missing negative triggers, missing `## Success` and
`## Routing`, and prose-line budgets. Re-checking those by eye produces a
second, weaker answer to a settled question.

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

Ask with `AskUserQuestion`: apply all local fixes, apply a named subset, or
report only. Never infer approval from the user having asked for a sweep.

## Phase 2 — rectify

Only what was approved, and only the local group.

1. Apply the fixes.
2. **Re-run `test_no_slop.py` at the same scope, plus `test_process_router.py`
   and `test_referenced_paths.py`.** All of them, because repairs here move
   counts and paths the other two own — that broke twice while writing this.
3. Quote the result. Still red is `systematic-debugging`'s trigger, not a retry.
4. Clear the drift counter with `--swept`.
5. Report what changed, and what went to `task-brief` with the reason.

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
- Editing anything before the report is approved.
- Applying a structural fix because it "looked obvious".
- Running `--scope layer` at stage 6. Shipping is the repo-wide cadence.
- Inventing a smell to avoid reporting clean.

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the tree | That is `code-review`; slop does not live in one change |
| Fixing as you go | The report then describes a tree that no longer exists |
| Treating a structural fix as a local one | Routing decides what fires; it ships unreviewed |
| Skipping the re-run after repairs | Repairs move counts and paths two other suites assert |
| Forgetting `--swept` | The drift nudge repeats every turn and starts being ignored |
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
- Also entered off-chain when `07-layer-drift.py` names it. That entry uses
  `--scope layer` and returns to whatever was happening.
- Structural findings become their own task via `task-brief`. A sweep worth
  remembering goes to `LOG.md` via `knowledge-manager`.

## Success

Every finding named a `file:line`, the script's output was quoted rather than
re-derived, nothing was edited before the user approved it, structural findings
went to `task-brief` instead of being applied, every suite named in phase 2 was
re-run and quoted, and the drift counter was cleared.
