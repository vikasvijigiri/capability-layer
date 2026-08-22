---
name: code-review
description: Review a code change and return a verdict with findings at file:line. Covers correctness, security, auth, secrets, injection, dependency risk, accessibility, performance, test quality and scope creep, over a diff, branch, PR or working tree. Triggers include "review this", "code review", "review the PR", "check the diff", "find bugs", "is this safe to merge", "critique this", "threat model this", "check auth", or "audit dependencies". Do NOT use to implement the fixes it finds, to release or deploy, or to substitute for running the tests. Use this whenever a diff is about to be delivered, even if the user does not ask.
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Code Review

## Overview

Return an independent, evidence-based verdict on the actual delivery surface.
Every finding carries a severity, a `file:line`, the defect, its impact, and the
evidence. Runs after verification and before delivery; the only human decisions
in the chain are plan approval and shipment approval.

<HARD-GATE>
Never report a review without reading the complete relevant diff, including
untracked files. Never treat passing tests as a substitute for reading the diff.
</HARD-GATE>

## Workflow

1. **Establish the surface.** Working tree for a local change, `git diff
   <merge-base> HEAD` for a branch or PR. Always include `git status
   --porcelain` so untracked files are not missed.
2. **Compute the scope** with `tools/scope.py`, and review exactly that much.
3. **Run the security gate** — its exit code decides the security lens, step 6.
4. **Inspect** correctness, security, silent failures, test quality, scope
   drift, dependency risk and policy violations, within the scope from step 2.
5. **Report** every finding with severity, `file:line`, defect, impact, evidence.
6. **Decide** the verdict, and never edit, commit, push or merge.

Each step in full below.

### Step 2 — compute the scope

Run `python tools/scope.py` (add `--base <ref>` for a branch or PR).

| Verdict | Review |
|---|---|
| `small` | the changed files and their direct callers |
| `major` | the whole branch diff |
| `undetermined` | read as `major` |

A clause that could not be evaluated is not permission to look at less.

### 3. Run the security gate

`python tools/security_gate.py --base <merge-base> --json`. Exit `1` names the
clauses that fired; exit `2` names the ones it could not evaluate, and `2` is
not `0`. **This decides the security lens in step 5 — it is not advice.**

### 4. Inspect

Correctness, security, silent failures, test quality, scope drift, dependency
risk, and repository policy violations, within the scope from step 2.

For a large change, dispatch `reviewer` (mode: diff) for independent
correctness, security, test-quality and scope passes; merge duplicate findings before
applying recovery. For an independent security pass rather than a reading,
dispatch `security-reviewer` — it reports, this skill still owns the verdict.
For a diff wide enough that even those four passes would serialize slowly,
`ultracode` parallelizes further across Claude Code's native dynamic-workflow
subagents — worth suggesting to the user at that scale.

### 5. Report and decide

Return `passed: true` only when no blocking finding remains. A `small` review
states its scope in the verdict, so `passed: true` is never read as broader than
it was. Return `passed: false` when repair is required.

**Never** edit, commit, push, merge, or ask a mid-run question.

| Severity | Meaning | Action |
|---|---|---|
| P0 | Exploitable now, destroys data, or leaks a secret | Blocks unconditionally — `_hooklib.classify_failure` gives its class a budget of zero |
| P1 | Wrong behavior on a common path, or a real security gap | Blocks; repair before re-review |
| P2 | Wrong behavior on an edge case, or a maintainability risk | Blocks a `major` review; a `small` review may note and proceed |

Same P0/P1/P2 vocabulary `refactoring` uses — one severity scheme across both
skills, not two that drift.

## Reference files — load one only when the diff earns it

| The diff touches | Read |
|---|---|
| auth, secrets, personal data, external input, trust boundaries | `references/security-review.md` |
| dependencies, lockfiles, CI config, build scripts | `references/supply-chain-audit.md` |
| user-facing markup, forms, focus, colour, motion | `references/accessibility-audit.md` |
| hot paths, queries, bundle size, startup, anything with a budget | `references/performance-engineering.md` |

Pick by what changed, not by habit — reading all four on a typo fix is the cost
this consolidation exists to remove.

**The security lens is computed, not picked.** If step 3's gate exits non-zero,
`references/security-review.md` is mandatory and the fired clause names where to
start. A rule whose whole content is a judgement call made under time pressure
has one reliable answer.

**A high-severity security finding is never auto-waived**, whichever lens found
it: it blocks, and `_hooklib.classify_failure` gives its class a budget of zero.

## Boundaries

**`refactoring` runs at the stage before this one** and can read the same files. It
reads standing artefacts — including files the change never touched — and asks
whether slop has accumulated. This reads **the diff** and asks whether the
change is correct and safe to ship. A finding about an unchanged file belongs
there, not here. `tools/test_process_router.py` fails if either skill stops
naming the other.

## Recovery

Failed findings go to `debugging`, one bounded repair at a time, then
this review runs again. A repeated root cause, security finding, scope escape,
or exhausted repair budget blocks the run or returns it to the plan gate.

## Next step

On `passed: true`, hand off to `release-git`. On `passed: false`, hand off to
`debugging` — never deliver unresolved findings.

## Routing

- Mandatory validator: actual diff inspection plus evidence for every review claim.
- Terminal handoff: `release-git` on pass; `debugging` on failure.
- This skill never owns shipment approval or repository side effects.

## Success

A structured, reproducible verdict tied to the actual diff, with no unlocated
findings and no unresolved blocking issue hidden by prose.
