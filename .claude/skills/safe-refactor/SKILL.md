---
name: safe-refactor
model: sonnet
description: Restructures code without changing its behaviour, establishing the behavioural baseline first so any drift is caught rather than assumed absent. Use for "clean this up", "this is a mess", "refactor this", "extract this into a function", "this file is too big", "tidy this code", "rename this everywhere", "restructure this", "it works but it is horrible". Prefer this over editing structure freehand - a refactor with no baseline is indistinguishable from a rewrite that quietly changed behaviour. Do NOT use when the behaviour is meant to change; that is a feature change, not a refactor.
effort: medium
---

# Safe Refactor

**Behaviour before, behaviour after, identical.** That is the whole contract. Everything
below exists to make that claim checkable rather than hopeful.

## Steps

1. **Establish the baseline first.** Characterisation tests covering current behaviour -
   including the behaviour you think is wrong. If tests do not exist, write them before
   touching structure. Route to `testing-unit-test-generator`.
2. **Run the baseline and record the output.** A baseline you did not execute is not a
   baseline.
3. **Check the blast radius** with `impact-analysis` if anything exported moves.
4. **One transformation at a time**, each independently verifiable: extract, rename,
   inline, move. Batched refactors fail as a unit and cannot be bisected.
5. **Re-run after every step**, not at the end. The step that broke it is the information
   you want, and it is only available immediately.
6. **Behaviour drift is a defect, not an improvement.** If a bug surfaces mid-refactor,
   record it and fix it separately - a refactor commit that also fixes a bug is
   unreviewable.

## Rules

- **Never refactor and change behaviour in one change.** Reviewers cannot separate them,
  and neither can `git bisect`.
- **Stop when the baseline cannot be established.** Untested legacy code with no
  characterisation tests is not refactorable safely; say so rather than proceeding on
  optimism.
- Structural improvement to *live* code. Removing *dead* code is `no-slop-check`; reducing
  genuine complexity is `simplify`.
