---
name: requirements-traceability
model: opus
description: Maps every line of a change back to the requirement it serves, and every requirement forward to the change that implements it - exposing both unrequested work and quietly dropped scope. Use for "does this match the brief", "did we do everything", "why is this in here", "trace this back", "is anything missing", "did we build extra", "check scope", "is this all in scope". Prefer this over reading the diff alone - a diff shows what was written, never what was asked for and skipped. Do NOT use before a brief exists; there is nothing to trace against.
---

# Requirements Traceability

Two directions, and the second is the one that finds real problems.

## Steps

1. **Forward - requirement to code.** For each requirement in the brief, name the change
   that implements it. A requirement with no corresponding change is dropped scope, and it
   produces no test failure and no review comment. It is invisible unless traced.
2. **Backward - code to requirement.** For each meaningful change in the diff, name the
   requirement it serves. Changes serving none are either unrequested scope, incidental
   refactoring, or something the brief failed to capture. All three are worth surfacing;
   they have different responses.
3. **Classify unmatched items** rather than reporting them as one pile:
   - dropped requirement (worst - silent)
   - unrequested scope (risk without a mandate)
   - implicit necessity (genuinely required, brief was incomplete - update the brief)

## Output

Two tables, forward and backward, with unmatched rows highlighted. One verdict: `fully
traced`, `traced with gaps`, or `untraceable`.

## Rules

- **Do not retrofit the brief to match the code.** If the work exceeded scope, say so; the
  fix is a conversation, not a rewritten requirement.
- Incidental refactoring is legitimate but should be *named*, not smuggled.
- Runs before `change-summary`, whose "what was deliberately not done" section this
  directly feeds.
