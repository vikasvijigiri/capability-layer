---
name: verifying-work
description: Prove finished work meets the brief, before review. Triggers include "is this done", "does this meet the brief", "prove it works", "are we finished", "did that work", "confirm this is complete". Do NOT use to find defects in a diff, to diagnose a known failure, or when nothing is claimed — those are separate steps. Use this whenever completion is claimed in any wording, even if unasked.
when_to_use: when results need validation after execution
effort: medium
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Verifying Work

Decide whether the work actually did what it was asked to do. Runs after
execution and before review.

Two different questions live here, and passing one does not pass the other:

1. **Do the checks pass?** Mechanical. The project's own automated check suite
   — lint, tests, typecheck, whatever it runs — answers it.
2. **Was every asked-for thing delivered?** A coverage question, and nothing
   mechanical answers it automatically.

Cap visible output at ~500 tokens. The verdict and the gaps, not a tour.

<HARD-GATE>
NO COMPLETION CLAIM WITHOUT FRESH EVIDENCE.

If you have not run the command in this turn, you cannot say it passes. A
previous run proves the tree it ran on, not this one. Violating the letter of
this rule is violating the spirit of it — "should work", "looks right",
"probably fine" and an unearned "Done!" are all the same claim.
</HARD-GATE>

## The gate function

Before any statement that implies success:

1. **Identify** — what command proves this claim?
2. **Run** it, fresh and in full. Not a subset, not from memory.
3. **Read** the whole output. Exit code. Failure count.
4. **Decide** — does that output confirm the claim? If not, state the real
   status with the output.
5. **Only then** make the claim, with the evidence beside it.

Skipping a step is not verifying. It is asserting.

## The coverage pass

Tests passing is the cheap half. The expensive half is: did we build what was
asked?

1. **Build the requirement inventory.** From the brief's Done Checks, the
   spec's success criteria, and each step of the plan. One line each, in their
   own words — not yours.
2. **Map each requirement to executed evidence** — the command that proves it
   and what it printed. Not the code that implements it; the run that
   demonstrates it.
3. **The unbacked set is the output.** Requirements with no executed evidence
   behind them. That list is the deliverable; the backed ones are a byproduct.
4. **Report unverifiable separately from unverified.** A requirement nothing
   could check ("the design is clearer") is not the same as one nobody checked.
   Collapsing them is how a gap disappears.

Report as a table: requirement | evidence | verdict. Anything without a command
in the evidence column is unbacked, however obviously true it looks.

## What proves what

| Claim | Requires | Not sufficient |
|---|---|---|
| Tests pass | This turn's run, 0 failures, quoted | A previous run, "should pass" |
| The fix works | The original symptom retested, and seen to pass | The code changed |
| The regression test works | Red-green: revert the fix, see it FAIL, restore, see it pass | It passes once |
| The hook fires | Triggering it directly against a realistic payload | The diff looks right — a hook's failure symptom is silence |
| The change is complete | Requirement-by-requirement coverage | The suites are green |
| A subagent did it | The diff, read | The agent reported success |
| Nothing else broke | The full suite on this tree | The touched file's test |

## Local conventions

- Run the project's own automated check suite (lint, test, typecheck, a
  frontmatter or schema parse — whatever it declares) as the mechanical half:
  run it, quote it, don't re-derive it by eye.
- Set whatever encoding or locale your toolchain needs before running scripts —
  a script that prints non-ASCII output can raise an encoding error on a
  default console and report a passing run as a failure.
- A check that cannot fail is not evidence. Before trusting a green check you
  wrote, break the thing on purpose and confirm it goes red. A probe returning
  the same answer when the system is broken verifies nothing.
- A criterion that names a command **is** its own check — run that command:
  a success criterion naming a one-second check has shipped unrun, past clean
  suites, more than once.

## Deciding the verdict

- **Verified** — every requirement maps to output you ran and quoted this turn.
- **Gaps** — name them, each with what would close it. This is the normal
  outcome and it is not a failure of the work.
- **Blocked** — a check errors or cannot run. That requirement is unbacked and
  the captured stderr is the reason. An erroring check never counts as evidence.

Then route. Do not fix what you find here — a verifier that edits is a verifier
whose result covers content that no longer exists.

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
| Skipping the requirement inventory | The missing requirement is exactly the one nobody thought to check |
| Collapsing unverifiable into verified | The gap becomes invisible instead of visible |
| Trusting a check you have never seen fail | It may be incapable of failing |
| Fixing gaps inside the verification | The evidence then describes a tree that no longer exists |
| Verifying a hook by reading it | Its failure symptom is silence — fire it |

For material changes, dispatch `test-verifier` before
declaring the result verified. It must independently run the relevant checks
and report exact evidence; an implementer's own report is never proof.

## Next step — you MUST take it

**The terminal state is invoking `no-slop`** once the verdict is verified — it
sweeps before `code-review` sees the diff, so the clean-up is itself reviewed
rather than shipped behind the review. If the verdict was gaps rather
than verified, route the gaps back into planning instead, and say so.

## Routing

- Mandatory validator: none — this is the validator. The HARD-GATE is the gate.
- Preceded by execution, or by any work about to be called done.
- Terminal handoff: `no-slop` when the result is a change to be delivered, then
  `code-review`; `delivering` once review has signed off.
- Gaps that need real work become their own unit, routed back into planning,
  which dispatches whatever ideation or design step it needs when the approach
  is open. A gap like "rollback is unproven" usually is. A failure whose cause
  is unknown goes to dedicated debugging.
- The verdict and its evidence belong wherever the project records decisions or
  session history, if it keeps one — the coverage table is the most reusable
  thing this skill produces.

## Success

Every requirement has a command beside it and a quoted result, the unbacked set
is stated plainly rather than rounded down, and someone reading the report can
re-run the evidence without asking you anything.