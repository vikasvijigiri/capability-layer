---
name: code-review
description: Inspect the actual branch diff before delivery for correctness, security, tests, scope and silent failures, returning a structured verdict. Do NOT use to implement fixes, to release, or to replace verification.
when_to_use: when a verified change needs an independent review
effort: high
model: sonnet
disable-model-invocation: true
---

# Code Review

Perform an independent, evidence-based review of the actual delivery surface.
This skill is automated by the feature workflow. The only human decisions are
plan approval before implementation and shipment approval before release.

<HARD-GATE>
Never report a review without reading the complete relevant diff, including
untracked files. Never treat passing tests as a substitute for reading the diff.
</HARD-GATE>

## Steps

1. Establish the surface: working tree for a local change, or
   `git diff <merge-base> HEAD` for a branch/PR. Include `git status --porcelain`
   so untracked files are not missed.
2. Inspect correctness, security, silent failures, test quality, scope drift,
   dependency risk, and repository policy violations.
3. Report every finding with severity, `file:line`, defect, impact, and evidence.
4. Return `passed: true` only when no blocking finding remains. Return
   `passed: false` when repair is required. Do not edit, commit, push, merge, or
   ask the user a mid-run question.

For a large change, the workflow may dispatch `diff-reviewer` for independent
correctness, security, test-quality, and scope passes; merge duplicate findings
before applying recovery.

## Recovery

The workflow sends failed findings to `systematic-debugging`, applies one
bounded repair at a time, and runs this review again. A repeated root cause,
security finding, scope escape, or exhausted repair budget blocks the run or
returns it to the plan gate.

## Next step

On `passed: true`, hand off to `delivering`. On failure, hand off to
`systematic-debugging`; never deliver unresolved findings.

## Routing

- Mandatory validator: actual diff inspection plus evidence for every review claim.
- Terminal handoff: `delivering` on pass; `systematic-debugging` on failure.
- This skill never owns shipment approval or repository side effects.

## Success

The result is a structured, reproducible verdict tied to the actual diff, with
no unlocated findings and no unresolved blocking issue hidden by prose.
