---
name: testing
description: Prove finished work meets the brief, before review or delivery. Every claim carries a command and its quoted output; produces a coverage verdict and names the unbacked set, keeping what nobody checked separate from what nothing could check. Triggers include "is this done", "are we finished", "did that work", "does this meet the brief", "prove it works", "show me it works", "confirm this is complete", or "did the fix land". Do NOT use to hunt defects in a diff (code-review), to diagnose a known failure (debugging), or when nothing has been claimed. Use this whenever completion is claimed in any wording, even if unasked.
effort: medium
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Testing

Decide whether the work did what it was asked to do. Runs after execution and
before review.

Two questions live here, and passing one does not pass the other:

1. **Do the checks pass?** Mechanical — the project's own suite answers it.
2. **Was every asked-for thing delivered?** A coverage question, and nothing
   mechanical answers it.

Cap visible output at ~500 tokens. The verdict and the gaps, not a tour.

<HARD-GATE>
NO COMPLETION CLAIM WITHOUT FRESH EVIDENCE.

If you have not run the command in this turn, you cannot say it passes. A
previous run proves the tree it ran on, not this one. "Should work", "looks
right", "probably fine" and an unearned "Done!" are all the same claim.
</HARD-GATE>

## The gate function

Before any statement implying success:

1. **Identify** — what command proves this claim?
2. **Run** it, fresh and in full. Not a subset, not from memory.
3. **Read** the whole output. Exit code. Failure count.
4. **Decide** — does that output confirm the claim? If not, state the real
   status with the output.
5. **Only then** make the claim, with the evidence beside it.

Skipping a step is asserting, not verifying.

## The coverage pass

Tests passing is the cheap half. Did we build what was asked?

1. **Build the requirement inventory** from the brief's Done Checks, the spec's
   success criteria, and each plan step. One line each, in their words.
2. **Map each requirement to executed evidence** — the command that proves it
   and what it printed. Not the code that implements it; the run that shows it.
3. **The unbacked set is the output.** Requirements with no executed evidence.
   That list is the deliverable; the backed ones are a byproduct.
4. **Report unverifiable separately from unverified.** A requirement nothing
   could check is not the same as one nobody checked.

Report as a table: requirement | evidence | verdict. Anything without a command
in the evidence column is unbacked, however obviously true it looks.

One filled row, so "evidence" reads as a command's output, not a description:

| Requirement | Evidence | Verdict |
|---|---|---|
| Login rejects a wrong password | `pytest tests/test_auth.py::test_bad_password` — 1 passed | Verified |
| Rate limiting on the login endpoint | grepped for a limiter; none found | Gap — no implementation, no test |

### Ask what is already known about these files

Before writing the verdict, query the durable knowledge for the paths the change
touched:

    python tools/memory.py --paths <the changed files>

It reads `MEMORY.md`, `ISSUES.md` and `decisions/` and returns entries naming
those files or their directory. **Say what came back, including when nothing
did** — "nothing recorded about these files" is itself a finding, and silence is
indistinguishable from not having looked.

Two things it catches that a green suite does not. A **past defect in this exact
file that no test covers**: `ISSUES.md` holds several whose symptom was silence,
and a verdict that does not check for the recurrence of a known silent failure is
a verdict about the tests rather than about the work. And a **decision this
change quietly reverses** — an ADR is evidence the reviewer is entitled to
before signing off, not after.

`task-analysis` runs the same query at stage 1, against files it is *about to*
touch. This is the other end: files that were *actually* touched, which is a
different set, because plans are wrong about their file maps. A returned entry is
evidence, not an order; `python tools/memory.py --stale` names entries the tree
has outgrown.

## What proves what

| Claim | Requires | Not sufficient |
|---|---|---|
| Tests pass | This turn's run, 0 failures, quoted | A previous run, "should pass" |
| The fix works | The original symptom retested and seen to pass | The code changed |
| The regression test works | Red-green: revert the fix, see it FAIL, restore, see it pass | It passes once |
| The hook fires | Triggering it against a realistic payload | The diff looks right — a hook's failure symptom is silence |
| The change is complete | Requirement-by-requirement coverage | The suites are green |
| A subagent did it | The diff, read | The agent reported success |
| Nothing else broke | The full suite on this tree | The touched file's test |

## Local conventions

- Run the project's automated check suite as the mechanical half: run it, quote
  it, don't re-derive it by eye.

  **Name the cheapest tier that answers the question.** A mid-chain stage takes
  `--scoped`; only the last verification before delivery takes `--tier all`.
  `CLAUDE.md` owns why — do not restate the cost here, because a figure copied
  into two files goes stale in one of them, and this one did.

      python tools/run_checks.py --scoped                    # mid-chain
      python tools/run_checks.py --tier all --require-test    # once, before delivery

  A scoped run prints `PARTIAL PASS`, never `PASS`, and names every suite it
  skipped, so quoting it cannot overstate what ran. It refuses outright on a
  `major` change, which is what stops this becoming "green on less evidence".

- Set whatever encoding or locale the toolchain needs before running scripts — a
  script printing non-ASCII can raise an encoding error and report a passing run
  as a failure.
- **A check that cannot fail is not evidence.** Before trusting a green check
  you wrote, break the thing on purpose and confirm it goes red.
- **A criterion that names a command IS its own check** — run that command. A
  success criterion naming a one-second check has shipped unrun, past clean
  suites, more than once.

## Deciding the verdict

- **Verified** — every requirement maps to output you ran and quoted this turn.
- **Gaps** — name them, each with what would close it. This is the normal
  outcome and not a failure of the work.
- **Blocked** — a check errors or cannot run. That requirement is unbacked and
  the captured stderr is the reason. An erroring check is never evidence.

Then route. Do not fix what you find here — a verifier that edits is one whose
result covers content that no longer exists.

## Red Flags — stop, you are asserting

- "Should work now" / "looks correct" / "seems fine".
- Satisfaction before evidence: "Great!", "Perfect!", "All done!".
- Quoting a run from earlier in the session.
- "The linter passed" as proof it builds.
- "The agent said it succeeded."
- "Tests pass, so the task is complete." Different question.
- "This requirement is obviously met." Then name the command.
- Fixing something mid-verification and not re-running.

**Each of these means: run the command and paste what it printed.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Reporting suite results as the verdict | Answers "do the checks pass", never "did we do the thing" |
| Skipping the requirement inventory | The missing requirement is the one nobody thought to check |
| Collapsing unverifiable into verified | The gap becomes invisible instead of visible |
| Trusting a check you have never seen fail | It may be incapable of failing |
| Fixing gaps inside the verification | The evidence then describes a tree that no longer exists |
| Verifying a hook by reading it | Its failure symptom is silence — fire it |

For material changes, dispatch `tester` before declaring the result
verified. It must independently run the relevant checks and report exact
evidence; an implementer's own report is never proof. It owns re-running the
suites and any red-green proof — if `implementation` already dispatched
`reviewer` (mode: spec) on this unit, that agent's plan-compliance check is not this
dispatch's job to repeat.

## Next step — you MUST take it

**The terminal state is invoking `refactoring`** once the verdict is verified — it
sweeps before `code-review` sees the diff, so the clean-up is itself reviewed
rather than shipped behind the review. If the verdict was gaps rather than
verified, route the gaps back into planning instead, and say so.

## Routing

- Mandatory validator: none — this is the validator. The HARD-GATE is the gate.
- Preceded by execution, or by any work about to be called done.
- Terminal handoff: `refactoring` when the result is a change to be delivered, then
  `code-review`; `release-git` once review has signed off.
- Gaps needing real work become their own unit, routed back into planning. A
  failure whose cause is unknown goes to `debugging`.
- The verdict and its evidence belong wherever the project records history — the
  coverage table is the most reusable thing this skill produces.
- Vetted external test-strategy references: `.claude/rules/testing-resources.md`
  (path-scoped; this skill only points at it).

## Success

Every requirement has a command beside it and a quoted result, the unbacked set
is stated plainly rather than rounded down, and someone reading the report can
re-run the evidence without asking you anything.
