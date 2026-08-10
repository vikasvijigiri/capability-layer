---
name: delivering
description: Land reviewed work in the repository - branch, PR, merge queue. Triggers include "open a PR", "push this up", "merge it", "ship it", "is this ready to land", "rebase onto main", "resolve these conflicts", "why is the merge queue stuck". Do NOT use to deploy or roll out (releasing), to review code (code-review), or to diagnose a failing check. Use this whenever reviewed work must reach the repository.
when_to_use: when verified reviewed work is ready for repository integration
effort: high
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Delivering

Prepare the reviewed change for safe repository integration. This stage may
create local commits, branch/PR metadata, and a merge-queue handoff according
to the host contract. It does not deploy. Shipment approval remains the second
and final human gate.

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
3. **Before rebasing, know what it would do.**

       python tools/git_ops.py rebase-plan --base <base> --head <head>

   `rebase_plan()` never runs `git rebase` — it simulates the merge with
   `git merge-tree --write-tree`, which composes a tree object and reports,
   touching neither the index nor the working tree. It returns "no-op",
   `clean`, `conflict`, or `unknown`; `unknown` is not `clean` and is not
   licence to proceed as if it were.
4. If it reports `conflict`, classify the conflicting paths mechanically —
   never by eye:

       python -c "import sys; sys.path.insert(0,'tools'); import git_ops, json; \
       print(json.dumps(git_ops.classify_conflict(sys.argv[1:]), indent=2))" <paths>

   `classify_conflict()` reads `_hooklib.MIGRATION_PATH_PATTERNS` and
   `parallel_groups.SHARED_PATTERNS`: a lockfile or generated file is
   `mechanical`; a migration or auth path, or anything matching neither table,
   is `substantive` and **escalates** — resolve only a `mechanical` verdict
   with bounded attempts; a `substantive` one returns a structured conflict
   incident to `systematic-debugging` rather than being resolved by guess.
5. Prepare the PR or merge-queue handoff. **The body comes from `git_ops.pr_body()`,
   never from `gh pr create --fill`** — a fill reads the merged `wip:` checkpoint
   subjects, which are squash-commit noise by this repository's own design, not
   a description of the work. `pr_body()` composes from the plan's `**Goal:**`
   line, its ticked `## Progress` boxes, the risk tier, and review findings.
   Do not bypass protected-branch rules, required checks, or merge queue. Do
   not deploy.
6. **Run the preflight and quote it. Exit `1` is a stop, not a note.**

       python tools/delivery_check.py --base <base> --head <head>

   Seven facts, computed rather than asserted: base alignment, CI green *for
   this exact SHA*, stack depth, merge-method compatibility, divergence,
   worktree cleanliness, and whether any of it is enforceable at all. Exit `0`
   ready · `1` a check failed · `2` a fact could not be determined — and **`2`
   is not `0`**, because a check that could not run is unrun.

   Everything above this line is prose, and prose already failed here: step 1
   has said "confirm the base is known" throughout, and a PR was still opened
   with a base that was not its branch point, by an agent that had read this
   file that morning. The prose is the reason; the command is the mechanism.
7. **Before anything leaves the machine, confirm with `AskUserQuestion`.**
   See below — a prose question does not count.
8. Return `clean`, `conflict`, or `blocked` with changed paths, base, checks,
   conflict files, and evidence. Never `clean` without step 6's output quoted.

## The push confirmation

<HARD-GATE>
`git push`, `gh pr create`, and any merge are outward-facing and are **never**
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
and `test_process_router.py` still pins the gate set to exactly two.

**This file once said the opposite.** `## Routing` read *"No separate
delivery approval exists; shipment approval is owned by `releasing`"* — but
`releasing` runs **after** this stage, so the only click authorising a push
arrived after the push. Meanwhile `CLAUDE.md` forbids pushing without explicit
approval and `/publish` gated the same action with two `AskUserQuestion` calls.
One action, two rules, decided by which entry point you happened to take.

## Nothing here merges, and that is deliberate

**No skill in this layer runs `gh pr merge`.** Grep for it and the only hits are
prohibitions. This stage prepares the candidate and stops; a human presses the
button. `/publish` says the same from the other side — *"Landing is
`delivering`'s business and the queue's"* — and what that resolves to is: open
the PR, report it, stop.

Say so plainly in the report. Deferring to "the merge queue" is worse than
saying "a human merges this", because a merge queue is a paid GitHub feature and
`gh api repos/<o>/<r>/branches/main/protection` answers `403 Upgrade to GitHub
Pro or make this repository public` on a free private repository. Handing off to
a mechanism that may not exist is how a step becomes nobody's.

## Stacked PRs — state the merge strategy before you open the second one

A branch opened against another open PR's branch is a **stack**, and stacks
interact badly with the squash-merge this layer otherwise assumes.
`CLAUDE.md` says `wip:` checkpoints are deliberate *"because squash-merge
collapses them"* — true for one PR, and the thing that breaks a stack:

| Step | What happens |
|---|---|
| Squash-merge the base PR | `main` gets a **new** SHA; the base's original commits never land |
| GitHub retargets the child | Its history now references commits absent from `main` |
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

## Next step

On a clean handoff, invoke `releasing` for release readiness and the shipment
approval gate. On conflict or failed checks, invoke `systematic-debugging`.

## Routing

- Mandatory validator: all-tier checks, secret scan, review receipt, and base-branch evidence.
- Terminal handoff: `releasing` on clean; `systematic-debugging` on failure.
- Delivery is not a lifecycle gate, and it still requires one `AskUserQuestion`
  before any push, PR or merge — an operational safety check, per **The push
  confirmation** above. Shipment approval remains Gate 2, owned by `releasing`.

## Success

The candidate is reproducible, review-backed, conflict-safe, and queued for
integration without silently pushing, merging, or deploying around policy.
