---
name: artifact-review
description: Independently review a spec or plan for coverage, decomposition, architecture, file accuracy, testability and scope before execution. Triggers include "review the spec", "review the plan", "does this cover everything". Do NOT use for code review, implementation, or a plan not read in full.
when_to_use: before execution when a spec or plan needs an independent review
effort: high
model: sonnet
disable-model-invocation: true
---

# Artifact Review

Review the artifact independently from its author. The artifact is the subject;
do not implement it or silently repair it.

## Procedure

1. Read the complete spec or plan and identify its artifact type.
2. Inspect the relevant repository files independently. Compare the artifact's
   paths, symbols, interfaces, dependencies, constraints, and assumptions with
   the codebase.
3. Check requirement coverage, scope boundaries, architecture fit, task
   ordering, interface consistency, test strategy, migration/release risk, and
   placeholder language.
4. Report findings in severity order. Each finding must name the artifact
   section, the concrete gap, the consequence, and the required correction.
   State what was checked and what was outside scope.
5. Return a verdict: APPROVED, APPROVED WITH RECORDED RISK, or REVISE.

For material cross-cutting changes, dispatch `architect` for a
separate architecture lens. This skill still owns the verdict and approval
gate.

## Boundaries

- Do not write implementation code, edit the spec or plan, or run execution.
- Do not approve an artifact because it is detailed; verify it against the
  repository and the source requirements.
- A REVISE verdict returns a spec to `architecture` or a plan to
  `task-analysis`; it must not jump directly to implementation.
- Called at most twice per plan by `task-analysis` Stage C5 before that
  skill stops iterating and surfaces the residual gap at Gate 1 instead —
  the cap lives there, not here.

## Routing

- Entered after `architecture` produces a spec or after `task-analysis` drafts
  a plan, before the relevant approval or execution boundary.
- Terminal handoff: the requesting artifact stage; REVISE returns to the stage
  that owns the artifact.

## Success

An independent, evidence-backed verdict exists, every material gap is explicit,
and execution has not begun on a rejected artifact.
