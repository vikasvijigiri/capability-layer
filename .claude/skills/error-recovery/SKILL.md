---
name: error-recovery
model: opus
description: Bounded diagnose-fix-reverify loop for a failing check (build, test, deploy or API error) - never repeats an already-falsified hypothesis, hands a finished record to knowledge-manager's ISSUES.md. Use on the second consecutive failure of the same thing, whenever a test or build goes red, and for "still failing", "why is this broken", "it doesn't work", "it broke again", "same error as before", "I have tried everything", "nothing I do fixes it", "we are going in circles". Prefer this over another ad-hoc retry - unstructured retrying is how the same wrong hypothesis gets tried three times. Do NOT use for a first failure with an obvious one-line cause.
effort: high
argument-hint: "[the failing check or error text]"
user-invocable: true
allowed-tools:
  - Read
  - Edit
  - Grep
  - Glob
  - Agent
  - Skill
provides: [diagnosis, fix, issue-record]
requires: [failure-signal]
produces_artifact: false
retryable: false
---

# Error Recovery

Not a retry wrapper. Running the same fix twice because nothing was learned between
attempts wastes both attempts. This skill's actual value is narrowing context per
attempt, never repeating a hypothesis a prior attempt already falsified, and turning a
transient failure into a durable record via `knowledge-manager`. Reusable standalone on
any tough bug in an ordinary session, not just inside `mvp-builder`.

## The loop

Bounded at 3 attempts by default (1 initial run + 2 recovery attempts; a caller may pass
a different bound). Two independent give-up triggers, whichever fires first:

1. The attempt counter reaches the bound, or
2. A new diagnosis's root-cause hypothesis is the same classification as a prior
   attempt's — no attempt is spent re-trying an idea already falsified.

Either trigger ends the loop in the same terminal state: **Escalated**. What happens to
the pipeline next (skip the sub-task, log a blocker, keep going) is explicitly not this
skill's job — its contract ends at returning a result plus a written `ISSUES.md` entry.

Per iteration:

1. **Diagnose** — given exactly: the failing command's trimmed output/stack trace (not
   a full log), only the files the trace actually names (plus their direct imports if
   the failure looks like an interface mismatch), and this incident's prior attempts
   (hypothesis / fix / outcome) so a repeated idea is recognizable. Optionally grep the
   repo's `ISSUES.md` for a matching prior symptom — reuse a fix that already worked (or
   already failed) for the same class of error instead of rediscovering it.
2. If the new hypothesis matches a prior attempt's classification → stop, go to
   Escalated.
3. **Apply** — edit scoped only to the files the diagnosis named.
4. **Re-verify** — re-run the *same* failing check that triggered the incident, not a
   broader validation.
5. Record the attempt; loop again if it's still failing and a give-up trigger hasn't
   fired.

## The record — hand off to `knowledge-manager`, once per incident

Whether Resolved or Escalated, hand off exactly one finished entry (not one append per
attempt) to `knowledge-manager`, in the `ISSUES.md` format its `formats.md` defines:

```
## YYYY-MM-DD HH:MM — <short symptom title>
- **Phase/Context**:
- **Symptom**:
- **Diagnosis**:
- **Attempts**:
  - 1. <tried> → <fixed / still failing / partial>
- **Fix**:
- **Status**: `Resolved` | `Escalated` | `Abandoned`
```

After a `Resolved` entry, apply `MEMORY.md`'s own durability question ("true in three
months, independent of this bug's code?") — if yes, `knowledge-manager` adds one line to
`MEMORY.md` referencing this entry by date, never duplicating the Attempts detail.
`Escalated`/`Abandoned` incidents are never promoted.

## Relationship to other skills

- Never decides pipeline-level consequences (retry the whole phase, abort the run,
  pause) — that's the calling context's job (e.g. `build-mvp.js`'s `withRecovery`
  wrapper).
- Hands its finished record to `knowledge-manager` the same way `workflow-orchestrator`
  already hands off its own Knowledge Update stage — no new composition idiom.

## Note on project-local overrides

A repo can have its own `.claude/skills/error-recovery/` with a repo-tailored version
(e.g. a tighter or looser attempt bound than the global default of 3, or a stricter
escalation policy for a higher-stakes project). Where both exist, the project-local one
takes precedence for that repo — this global version is the default otherwise.
