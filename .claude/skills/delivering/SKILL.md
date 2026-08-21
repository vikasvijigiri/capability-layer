---
name: delivering
description: Land reviewed work in the repository - branch, PR, rebase, merge. Reports what actually landed, and never pushes, merges or opens a pull request without explicit human approval. Triggers include "open a PR", "raise a PR", "push this up", "merge it", "land this", "ship it", "is this ready to land", "can this go in", "rebase onto main", "resolve these conflicts", "update the branch", "why is the merge queue stuck". Do NOT use to deploy to a running environment (releasing), to review the code (code-review), or to diagnose a failing check (systematic-debugging). Use this whenever reviewed work must reach the repository.
when_to_use: Trigger when the user says open a PR, raise a PR, create a pull request, push this up, push it, merge it, merge this, land this, ship it, is this ready to land, can this go in, rebase onto main, rebase this, resolve these conflicts, fix the conflicts, update the branch, or why is the merge queue stuck.
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash AskUserQuestion
---

# Delivering

Prepare the reviewed change for safe repository integration. This stage may
create local commits, branch/PR metadata, and a merge-queue handoff according
to the host's contract. It does not deploy. Shipment approval remains the
second and final human gate.

<HARD-GATE>
Never integrate a change without current verification evidence, a passing
automated code review, clean secret checks, and a named base branch. Never use
model preference to choose between competing changes: promote the candidate
with objective checks, acceptance coverage, security status, scope fit,
rollback, and then the smallest lower-risk diff.
</HARD-GATE>

## Steps

1. Confirm the worktree/branch is isolated and the base is known. For parallel
   work, use one worktree per task and serialize shared-interface changes.
2. Run the repository's required all-tier checks and secret scan on the actual
   candidate. Preserve command, exit code, and relevant output as evidence.
3. **Before rebasing, know what it would do — without doing it.**

       git merge-tree --write-tree <base> <head>

   This composes a tree object and reports the result without touching the
   index or working tree — a real simulation, not a guess. If the project
   provides a wrapper that classifies the result for you, use its answer; read
   the outcome as one of "no-op", `clean`, `conflict`, or `unknown` either way.
   **`unknown` is not `clean`** and is not licence to proceed as if it were.
4. If it reports `conflict`, classify the conflicting paths mechanically —
   never by eye. A lockfile or a purely generated file is `mechanical` and safe
   to resolve with bounded attempts; a migration, an auth path, or anything
   that doesn't clearly match a known-safe pattern is `substantive` and
   **escalates** — hand it to dedicated debugging as a structured incident
   rather than resolving it by guess. If the project maintains a table of
   which paths count as which, use it instead of judging fresh each time.
5. Prepare the PR or merge-queue handoff. **Compose the description yourself
   from the plan's goal, its checked-off progress, the risk tier, and review
   findings — never from an auto-fill of squashed commit subjects.** Squashed
   checkpoint commits are noise by design, not a description of the work; if
   your history uses interim checkpoint commits for exactly that reason, an
   auto-filled body will read them back as the PR description, which is the
   bug this step exists to prevent. If the project provides a body-generator
   that does this composition for you, use it instead of `--fill`. Do not
   bypass protected-branch rules, required checks, or the merge queue. Do not
   deploy.
6. **Run the integration preflight and quote it. A failing exit code is a
   stop, not a note.** Verify seven facts, computed rather than asserted: base
   alignment, CI green *for this exact SHA*, stack depth, merge-method
   compatibility, divergence from the base, worktree cleanliness, and whether
   each of these is even enforceable in this repository's configuration. In
   this repository that command exists:

       python tools/delivery_check.py --base <base> --head <head>

   Exit `0` ready · `1` a check failed · `2` a fact could not be determined —
   and **`2` is not `0`**, because a check that could not run is unrun. Exit 1
   is a stop, not a note. Where a project has no such command, run the manual
   seven-point check and treat "could not determine" the same way.

   Stating a check in prose ("confirm the base is known") is not the same as
   running one — that gap alone is enough to ship a PR against the wrong base.
   The command above, or the manual seven-point check if none exists, is what
   actually closes it; the surrounding instructions are the reason it matters,
   not the mechanism that enforces it.
7. **Before anything leaves the machine, confirm with `AskUserQuestion`.**
   See below — a prose question does not count.
8. Return `clean`, `conflict`, or `blocked` with changed paths, base, checks,
   conflict files, and evidence. Never `clean` without step 6's output quoted.

## The push confirmation

<HARD-GATE>
`git push`, opening a PR, and any merge are outward-facing and are **never**
performed on an inferred yes. Ask with `AskUserQuestion`, naming the remote, the
branch and the base in the question itself, with real options — push and open a
PR, keep it local, cancel.

A prose question is answerable by silence and it scrolls away in a long turn.
"Say the word and I'll push" is not approval; it is a sentence that looks like
one.
</HARD-GATE>

**This is an operational safety check, not a third lifecycle gate**, and the
distinction is what keeps the chain at two gates. Gate 1 approves a plan and
Gate 2 approves a shipment; this authorises one irreversible operation on the
tree in front of you. It carries no `<!-- GATE n -->` marker for that reason,
and whatever this project uses to validate its gate count should still expect
exactly two.

**Get the location of this authorization precisely right.** It would be easy
to place it in the wrong stage — for instance, deferring to a later
release-approval step, when that step runs only *after* this one's push has
already happened, which means nothing would have actually authorized the push
itself. If the project has more than one entry point into this same action (a
shortcut command, a script, a habit), every one of them needs the same
confirmation, not a weaker or absent one — one irreversible action should never
carry zero authorizations from one entry point and two from another.

### Exception: a parallel round's task branches

**Scope, exactly:** branches `executing-plans` created for one round of
tasks `tools/parallel_groups.py` proved independent (see its "Dispatching
subagents for parallel tasks" section) — nothing else. For those branches
only, `git push` and PR-creation happen automatically, per branch, with no
`AskUserQuestion`. Nothing is merged by this step, each branch is small and
independently reviewable, and the round's own `no-slop`/`code-review` pass
still gates the merge (below) — so the irreversible action this section
exists to gate has not happened yet.

Every other push in this repository — a single-task plan, a manual push, a
shortcut command — keeps requiring the full per-instance confirmation above,
unchanged. This exception does not widen to "any push from `executing-plans`"
or "any small branch"; it is scoped to a round the scheduler itself proved
independent, and it stays that narrow.

## Nothing here merges, and that is deliberate

**No skill in this layer runs the merge command.** Grep for it and the only
hits should be prohibitions. This stage prepares the candidate and stops; a
human presses the button. Say so plainly in the report: open the PR, report
it, stop.

Deferring to "the merge queue" is worse than saying "a human merges this,"
because a merge queue is often a paid or plan-gated feature, and the hosting
API can simply refuse to confirm one exists on a given repository's tier.
**Confirm the mechanism you're deferring to is actually enabled before you
defer to it** — handing off to something that may not exist is how a step
becomes nobody's.

## Stacked PRs — state the merge strategy before you open the second one

A branch opened against another open PR's branch is a **stack**, and stacks
interact badly with the squash-merge this stage otherwise assumes. Interim
checkpoint commits are often kept deliberately for review granularity — which
is exactly what a stack breaks, because squash-merge collapses them:

| Step | What happens |
|---|---|
| Squash-merge the base PR | `main` gets a **new** SHA; the base's original commits never land |
| The host retargets the child | Its history now references commits absent from `main` |
| The child's diff | Re-proposes its parent's files, as conflicts that are not real |

Three rules, in order of preference:

1. **Prefer no stack.** Independent branches off `main` merge in any order.
   Trunk-based practice keeps branches short-lived and parallel for exactly this
   reason; a stack is a scheduling constraint you are choosing to take on.
2. **If you stack, merge with merge commits, not squash** — the base's SHAs must
   survive for the children to stay clean. Decide this and say it out loud
   *before* opening the second PR, not when the first one is ready to land.
3. **Keep the stack shallow.** Past two or three the ordering constraint costs
   more than the review granularity buys, and the industry answer at that depth
   is tooling (Graphite, `ghstack`, `spr`) rather than discipline.

**Check the base you declare against the base you cut from.** A PR opened with
`--base X` from a branch cut off `Y` shows every one of `Y`'s files as its own.
One command, and it is the whole check:

```bash
[ "$(git merge-base origin/<base> origin/<head>)" = "$(git rev-parse origin/<base>)" ] \
  && echo aligned || echo MISMATCH
```

## Recovery

Conflict recovery is limited to two attempts. A failed required check returns to
the failed stage, not to a blind full rerun. Scope drift, security findings, or
repeated conflicts return to the plan gate.

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

## Next step — you MUST take it

On a clean handoff, invoke `releasing` for release readiness and the shipment
approval gate. On conflict or failed checks, invoke `systematic-debugging`.

## Routing

- Mandatory validator: all-tier checks, secret scan, review receipt, and
  base-branch evidence.
- Preceded by review — this consumes a change that has already been reviewed
  and verified.
- Terminal handoff: `releasing` on clean; `systematic-debugging` on failure.
- Delivery is not a lifecycle gate, and it still requires one
  `AskUserQuestion` before any push, PR or merge — an operational safety
  check, per **The push confirmation** above. Shipment approval remains
  Gate 2, owned by the release-readiness step.

## Success

The candidate is reproducible, review-backed, conflict-safe, and queued for
integration without silently pushing, merging, or deploying around policy.