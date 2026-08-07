---
name: code-review
description: Review the actual branch diff and return a verdict. Triggers include "review this", "check the diff", "threat model this", "check auth", "audit dependencies", "is this accessible", "why is this slow", "is this safe to merge". Do NOT use to implement fixes, to release, or to replace verification. Use this whenever a diff is about to be delivered, even if the user does not ask for a review.
when_to_use: when a verified change needs an independent review
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
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

## Lenses — load one only when the diff earns it

Four specialist reviews were separate skills. Each cost its own
description on every turn, for depth that applies to a minority of diffs. They
are now references: same content, read on demand, nothing charged when unused.

| The diff touches | Read |
|---|---|
| auth, secrets, personal data, external input, trust boundaries | `references/security-review.md` |
| dependencies, lockfiles, CI config, build scripts | `references/supply-chain-audit.md` |
| user-facing markup, forms, focus, colour, motion | `references/accessibility-audit.md` |
| hot paths, queries, bundle size, startup, anything with a budget | `references/performance-engineering.md` |

Pick by what changed, not by habit — reading all four on a typo fix is the cost
this consolidation exists to remove. A lens that produces a finding reports it
through the same severity/`file:line`/evidence format as everything else.

**A high-severity security finding is never auto-waived**, whichever lens found
it: it blocks, and `_hooklib.classify_failure` gives its class a budget of zero.

When the security lens needs an independent pass rather than a reading, dispatch
`security-reviewer`; it reports, this skill still owns the verdict.

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
