# Delivery mechanics — stacked PRs, recovery, red flags

Split out of the former `delivering` skill's body to keep `SKILL.md`
scannable. Read this when a stack exists, a conflict needs recovery, or
before asserting delivery readiness.

## Stacked PRs — the failure table

A branch opened against another open PR's branch is a **stack**, and stacks
interact badly with the squash-merge the delivering procedure otherwise
assumes. Interim checkpoint commits are often kept deliberately for review
granularity — which is exactly what a stack breaks, because squash-merge
collapses them:

| Step | What happens |
|---|---|
| Squash-merge the base PR | `main` gets a **new** SHA; the base's original commits never land |
| The host retargets the child | Its history now references commits absent from `main` |
| The child's diff | Re-proposes its parent's files, as conflicts that are not real |

Three rules, in order of preference:

1. **Prefer no stack.** Independent branches off `main` merge in any order.
   Trunk-based practice keeps branches short-lived and parallel for exactly
   this reason; a stack is a scheduling constraint you are choosing to take
   on.
2. **If you stack, merge with merge commits, not squash** — the base's
   SHAs must survive for the children to stay clean. Decide this and say it
   out loud *before* opening the second PR, not when the first one is ready
   to land.
3. **Keep the stack shallow.** Past two or three the ordering constraint
   costs more than the review granularity buys, and the industry answer at
   that depth is tooling (Graphite, `ghstack`, `spr`) rather than
   discipline.

**Check the base you declare against the base you cut from.** A PR opened
with `--base X` from a branch cut off `Y` shows every one of `Y`'s files as
its own. One command, and it is the whole check:

```bash
[ "$(git merge-base origin/<base> origin/<head>)" = "$(git rev-parse origin/<base>)" ] \
  && echo aligned || echo MISMATCH
```

## Recovery

Conflict recovery is limited to two attempts. A failed required check
returns to the failed stage, not to a blind full rerun. Scope drift,
security findings, or repeated conflicts return to the plan gate.

## Red Flags — you are asserting readiness, not checking it

Each of these means: run the check, quote it, and let the result decide.

| Said | Why it bites |
|---|---|
| "The rebase should be clean, it's a small change." | Simulate it; don't predict it |
| "This conflict is probably just whitespace." | Classify it mechanically before touching it |
| "I'll resolve this migration conflict myself, it's probably fine." | Migration and auth-path conflicts need a diagnosis, not a fast guess — escalate |
| "`--fill` is close enough for the PR body." | It surfaces squashed checkpoint noise, not the change. Write it from the plan |
| "They'll probably say yes, I'll just push." | The confirmation exists precisely because prose approval is unreliable |
| "The merge queue will catch anything wrong." | Confirm the queue is enabled before trusting it; it may not exist on this tier |
| Opening a second stacked PR without declaring the merge strategy | Squash-merging the base silently breaks every child's history |
| Treating "could not determine" as a pass | An unchecked fact is not a fact that held |
| Reporting `clean` without the preflight output quoted beside it | The claim outruns the evidence |
