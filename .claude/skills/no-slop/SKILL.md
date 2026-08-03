---
name: no-slop
description: Use to review the `.claude/` capability layer itself for architectural decay — overlapping triggers, paraphrased duplicate rules, god skills, orchestration leakage. Triggers include "audit the capability layer", "is the skill layer bloated", "review the .claude folder", "no-slop check", "are the skills clean", "did the layer rot". Do NOT use to review a code diff (that is `code-review`), to fix what it finds, or in place of `tools/test_no_slop.py`, which owns everything mechanically decidable.
effort: high
model: sonnet
---

# No-Slop

Review the `.claude/` layer for architectural decay. Entered from any stage, and
owned by nothing else — decay accumulates across sessions rather than inside one
change, so no diff review can catch it.

**This is not `code-review`.** That skill reads a diff someone is about to ship.
This one reads a standing artefact with no diff involved, and the two never
substitute: a layer can rot without a single line changing, because the repo
around it moved instead.

Cap visible output at ~500 tokens. Findings with `file:line`, not a tour.

<HARD-GATE>
Run `python tools/test_no_slop.py` FIRST and quote its last line.

It owns hedging language, description budgets, missing `## Success` and
`## Routing` contracts, duplicated sentences, prose-line budgets and credentials
in tracked files. Reviewing those by eye duplicates a check that already ran and
produces a second, less reliable answer to a question already settled.
</HARD-GATE>

## Why the split exists

The checklist this implements has fifteen categories and most are not decidable
by a program: "is every sentence earning its place", "could Claude misinterpret
this", "is the intent obvious" all need a reader.

A script claiming to check those would be the fourth false-confidence gate in
this repo's history — `03-review-gate`, `05-docs-gate` and `05-docs-required`
were each deleted for asserting a judgement they could not make. So the script
checks what is falsifiable and this skill carries the rest. Neither is the whole
answer and neither pretends to be.

## The four smells worth a read

Ranked by what they cost as the layer grows. Read for these specifically rather
than reading everything looking for anything.

**1. Overlapping triggers.** One request that two different skills would both
plausibly claim. The script catches identical keywords; it cannot catch *"review this
change"* and *"is this ready to ship"* pointing at different skills. Test it:
write three requests a real user would send and name which skill owns each.
This is the most expensive ambiguity there is, because the wrong skill still
produces confident output and nothing signals the mismatch.

**2. Duplicate knowledge, paraphrased.** The script catches identical sentences.
It misses one rule stated three different ways — worse, because the versions
drift and no reader can tell which is current. Ask: if this rule changed, how
many files would need editing? More than one means one owner and pointers.

**3. God skill.** One skill doing two jobs that could be rejected separately.
The signal is **not** length — the prose budget covers that, and the two longest
skills here are long because they ship templates, which is why the budget counts
prose and not raw lines. The signal is whether a reviewer could approve half of
it. Two definitions of done inside one `## Success` means it should be split.

**4. Orchestration leakage.** A skill deciding what comes next rather than
producing an artefact and letting the caller decide.

**This repo breaks that rule deliberately, so read carefully.** Every skill
states a terminal handoff and `.claude/workflow.md` owns the chain — a
considered choice, because a stage with no named successor gets skipped and the
handoffs are what make the chain traceable. The finding is therefore **not**
"this skill names a successor". It is a skill naming one that contradicts
`workflow.md`, or naming one conditionally in a way the workflow never
describes.

## Also worth checking

- **Does a skill assume another's internals?** Naming an artefact path is fine;
  depending on how that artefact gets produced is a leak.
- **Does anything hard-code a model or an MCP server** where a capability
  description would survive the vendor changing it?
- **Would a new contributor get the intent in one read?** A section needing a
  second pass is under-specified, not deep.
- **Does prose still describe the wiring?** This repo's recurring failure is a
  document asserting a capability nothing implements — seven instances.
  `tools/test_referenced_paths.py` catches the subset that names a path.

## Report

A table: `file:line` · the smell · one sentence on what breaks. Then the
verdict: clean, or the count.

If nothing is wrong, say so in one line **and name what you read** — an empty
review that lists nothing is indistinguishable from a review that never ran.

## Red Flags — you are not reviewing, you are padding

- Re-stating what `test_no_slop.py` already printed.
- A finding with no `file:line`.
- "Consider possibly simplifying this section" — name the sentence to cut.
- Flagging a terminal handoff as orchestration leakage without checking
  `workflow.md` first.
- Fixing something mid-review.
- Inventing a smell to avoid reporting clean.

**Each of these means: go back to the file and quote the line.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reviewing a diff instead of the layer | That is `code-review`; decay does not live in one change |
| Fixing findings as you go | The report then describes a tree that no longer exists |
| Treating skill length as the god-skill signal | The two longest skills here carry templates and are correct |
| Reporting the script's findings as your own | Two answers to a settled question, the weaker one last |
| Skipping the script because the layer "looks fine" | Its first run found a missing `## Success` nobody had noticed |

## Routing

- Mandatory validator: `tools/test_no_slop.py`, and it is a HARD-GATE rather
  than a suggestion — this skill's findings are only meaningful on a layer whose
  mechanical checks already pass.
- Entered from any stage, like `research` and `systematic-debugging`. Not part
  of the linear chain and it consumes no upstream artefact.
- Terminal handoff: none by default — this reports and stops, and fixing inside
  a review invalidates the review.
- Findings that need real work become their own task via `task-brief`. A finding
  worth remembering goes to `LOG.md` via `knowledge-manager`.
- Runs naturally after any session that added or edited a skill, agent or hook.

## Success

Every finding names a `file:line` and one sentence on what breaks, the script's
result is quoted rather than re-derived, nothing was fixed during the review,
and a clean verdict states what was read so it cannot be confused with a review
that never happened.
