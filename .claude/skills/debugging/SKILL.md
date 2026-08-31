---
name: debugging
description: Find the root cause of a failure before proposing any fix. Reproduce it, isolate it, prove the cause with evidence, then repair one thing at a time. Triggers include "why is this failing", "it does not work", "it worked before", "what changed", "root cause", "debug this", "this test is red", "it hangs", or "it silently fails". Do NOT use for a failure whose root cause is already known, or for a feature that was never implemented. Use this whenever something fails unexpectedly, even if only the symptom is reported.
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Debugging

Find the root cause before proposing a fix. A symptom fix is a failure, even
when the symptom goes away.

Cap visible output at ~500 tokens. The hypothesis and the evidence, not a
narration of everything you looked at.

<HARD-GATE>
NO FIX WITHOUT ROOT-CAUSE INVESTIGATION FIRST.

If you have not completed Phase 1, you may not propose a fix. Violating the
letter of this is violating the spirit of it.
</HARD-GATE>

## Silence is the usual symptom

In a repo wired with this layer, most failures do not throw. A hook that fails
open, a gate that never fires, a skill whose description silently vanished — each looks exactly like
"no problem". Two consequences:

- **Absence of output is data, not reassurance.** Prove the thing ran.
- **The repo's recurring failure is that prose declares a capability the wiring
   does not implement** — historically observed in prior audits. When something
   is documented and not working, suspect the wiring before the logic.

Useful levers: `tools/run_hook.py <event> '<json>'` fires one hook against a real
payload; `PYTHONIOENCODING=utf-8` first, or `→`/`—` raise `UnicodeEncodeError` and
a passing run reads as a failure; the suites in `tools/`.

## Failure capture

Before retrying an agent-run failure, capture the state that a later agent or
human needs to reproduce it:

```markdown
## Failure Capture
- Session / task:
- Goal in progress:
- Error:
- Last successful step:
- Last failed tool or command:
- Repeated pattern or context pressure:
- Environment assumptions:
- Failure class: logic | state | environment | policy | agent-run
```

Agent-run failures include repeated tool calls, context drift, tool-loop limits,
wrong working directory or branch, missing files after a write, and a policy
boundary that the host did not enforce. Capture is evidence, not a diagnosis.

## Phase 1 — Root cause

Complete this before anything else.

1. **Read the error completely.** Stack trace, line numbers, exit codes. It
   often contains the answer.
2. **Reproduce it.** Exact steps, every time. Not reproducible means gather more
   data, never guess.
3. **Check what changed.** `git diff`, `git log --oneline -5`, new config, new
   dependency.
4. **Instrument the boundaries.** For anything with more than one component, log
   what enters and what leaves each one, then run *once* to find which boundary
   breaks. Narrow to the component before investigating inside it.
5. **Trace backwards.** Where did the bad value originate? What passed it in?
   Keep going up until you reach the source. Fix there, not where it surfaced.

## Phase 2 — Pattern

1. **Find something similar that works** in this codebase.
2. **Read the working version completely.** Not a skim. Partial understanding
   guarantees a wrong fix.
3. **List every difference**, however small. "That can't matter" is where the
   bug lives.

## Phase 3 — Hypothesis

1. **State one hypothesis**: "X is the root cause, because Y." Specific, written
   down, falsifiable.
2. **Test it with the smallest possible change.** One variable.
3. **Confirmed → Phase 4. Not confirmed → new hypothesis.** Never stack a second
   fix on an unconfirmed first.
4. **Say "I don't understand X"** when true. Do not narrate a guess as a finding.

## Phase 4 — Fix

1. **Write the failing test first.** Simplest reproduction that fails for the
   right reason. Watch it fail before you fix.
2. **One fix, addressing the cause.** No "while I'm here".
3. **Check whether the same root cause exists elsewhere** — same pattern,
   different call site or file. Note it even if fixing it there is out of
   scope for this pass; an unnoted twin is the next person's fresh incident.
4. **Verify:** the test passes, nothing else broke, the original symptom is gone.
   Quote the real output.
5. **Record it in `ISSUES.md`** — symptom, diagnosis, every attempt with its
   outcome, fix, status. Format is in `.claude/skills/documentation/formats.md`. The
   failed attempts are the valuable part; they stop the next person re-running
   them.

**If the fix does not work:** count your attempts. Under three, return to Phase 1
with what you learned. **Three or more, stop and question the architecture** —
when each fix reveals a new problem somewhere else, that is not a failed
hypothesis, it is the wrong design. Raise it with the user rather than trying
a fourth.

End with an `Agent Self-Debug Report` whenever the failure involved the agent,
its tools, or its environment:

```markdown
## Agent Self-Debug Report
- Failure:
- Root cause:
- Recovery action:
- Result: success | partial | blocked
- Evidence:
- Follow-up:
```

## Test the test before you trust it

A test that fails can be wrong about the code. A gate test once reported two
false failures and three rounds went into theorising about CRLF round-tripping;
the harness was reading and rewriting files through text mode.
Rewritten to snapshot bytes, all six cases passed and the code had been correct
throughout.

- Make the harness byte-exact and state-independent before believing its verdict.
- A test that depends on leftover state from an earlier test measures the wrong
  thing. One passed only because a previous case had written a receipt.
- Reasoning about whether a test is correct is slower and less reliable than
  making it deterministic.

## Red Flags — stop and return to Phase 1

- "Quick fix now, investigate later."
- "Just try changing X and see."
- "It's probably X, let me fix that."
- "I don't fully understand this, but this might work."
- Proposing a fix before tracing the data flow.
- Changing several things and running the tests.
- "One more attempt" when you have already tried two.
- Each fix surfacing a new problem somewhere else.

From the user: *"is that not happening?"* means you assumed without verifying.
*"stop guessing"* means exactly that. Both mean return to Phase 1.

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Treating no-output as no-problem | Here, silence is the most common symptom of a real bug |
| Fixing where the error surfaced | The bad value came from somewhere upstream and will come back |
| Two changes in one test cycle | You cannot tell which one worked, and one may have added a bug |
| Trusting a failing test over the code | The harness is code too, and it is usually the newer, less-exercised code |
| Skipping `ISSUES.md` because it's fixed | The attempts that failed are what save the next person an hour |
| Debugging by reasoning alone | Run the thing. These bugs do not announce themselves |

## Quick Reference

| Phase | Do | Done when |
|---|---|---|
| 1 Root cause | Read, reproduce, diff, instrument, trace back | You can say what and why |
| 2 Pattern | Find a working twin, read it fully, list differences | The difference is named |
| 3 Hypothesis | One theory, smallest test, one variable | Confirmed, or replaced |
| 4 Fix | Failing test, one fix, verify, record | Symptom gone, `ISSUES.md` written |

## Parallel work — `debugger`

When several *independent* failures land at once — different files, different
subsystems, no shared cause — dispatch one **`debugger`** per
failure, all in the same message. Each reproduces its own failure, finds the
root cause, and returns the cause plus the command that proves it. None of them
fixes anything, so they cannot collide.

Independence is the gate, and it is a judgement you make first: if fixing one
might fix another, they are one investigation, not three. Shared state, or a
suspicion of a common cause, means do it here.

You still own the fix, the four-phase loop, and the `ISSUES.md` entry.

**Only when the user has asked for subagents.**

## Routing

- Mandatory validator: none. The Phase 4 failing test is the gate — a fix with
  no test that failed first is not verified.
- Terminal handoff: none. Writes the `ISSUES.md` entry itself, per
  `documentation`'s format; hand off to `documentation` only if the
  incident also changes `MEMORY.md` or warrants a decision record.
- A `Resolved` incident that would still be true in three months, independent of
  this bug's code, earns one `MEMORY.md` line. `Escalated` and `Abandoned` never
  do — an unresolved incident is a hypothesis, not a lesson.
- If the fix turns into a design change, stop and hand it to `task-analysis`,
  which dispatches `architecture` itself when the approach is open. Do not enter
  the design stage directly — a fix that grew into a design still needs framing,
  and skipping it is how a redesign arrives with no `TASK.md` behind it.
- Consult `engineering-standards` while diagnosing a backend or frontend
  failure, for the failure classes industry practice already names
  (connection-pool exhaustion, N+1 queries, hydration mismatches).

## Success

The root cause is named, a test that failed for the right reason now passes,
nothing else broke, and `ISSUES.md` carries the attempts as well as the answer.
