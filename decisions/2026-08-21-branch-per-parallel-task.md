# Branch-per-parallel-task, permanent, with a batched merge confirmation

Date: 2026-08-21

## Decision

`executing-plans` dispatches a schedulable parallel round by default —
`tools/parallel_groups.py` reporting concurrency > 1 is now the license,
not a user asking for it by name. Each task in such a round gets its own
named branch (`tools/worktree.py`'s new, additive `--branch` mode), pushed
and opened as its own PR automatically once its own verification passes.
The merge into `main` still asks — every time, live — but batched into one
`AskUserQuestion` per round naming every PR, instead of one confirmation
per PR.

## Why

Every plan in this repository's history executed serially, even when its
own tasks were provably independent, because the only gate on concurrent
dispatch was an opt-in nobody ever invoked ("Only when parallel dispatch
was explicitly chosen for this run"). The scheduler
(`tools/parallel_groups.py`) already proved disjointness and frozen
interfaces; nothing used the proof. Separately, `tools/worktree.py`'s
`create()` always detached, by an earlier, explicit design choice ("a named
branch per worktree leaves branches behind after teardown") — correct for
a scratch surface the dispatcher folds back into one branch, wrong for work
that needs to be independently pushable.

The user asked for this directly, mid-session, and for the merge step to
stay gated rather than fully automatic — this repository has a hard, tested
invariant that no skill executes a merge (`tools/test_process_router.py`'s
`_MERGE_VERBS`, and `delivering/SKILL.md`'s own "No skill in this layer
runs the merge command... a human presses the button"). Batching the
existing per-PR confirmation into one per round satisfies both: the human
still presses the button, every time, live; they press it once per round
of independent work instead of once per task.

## What this cost, accepted

- **A parsing bug in `tools/parallel_groups.py` had to be fixed first**,
  found live while scheduling the plan this decision's own mechanism was
  built to execute: a `Dependencies: none (explanation containing digits)`
  field was misread as a numeric dependency on a nonexistent task, and a
  backticked code fragment in a `Files:` bullet was misread as a phantom
  file. Both are covered by regression tests now; see
  `docs/plans/2026-08-21-four-more-spec-metrics.md`'s own history for the
  live reproduction.
- **Two exceptions live inside `delivering/SKILL.md`'s otherwise-absolute
  push confirmation and no-merge rules**, each scoped narrowly by name
  ("a parallel round's task branches", "a parallel round's batched merge")
  and pinned by a test (`tools/test_process_router.py`) that fails if
  either heading stops naming "parallel" explicitly — the risk being
  guarded against is a future edit quietly widening either into the
  general rule.
- **Per-branch review was traded for speed, deliberately.** A task's PR
  opens right after its own task-level verification, not after a scoped
  `no-slop`/`code-review` pass on that branch alone — review happens once,
  combined, over the whole round's diff, gating the merge instead of the
  PR-open. Decided by the user via `AskUserQuestion` mid-session, in favor
  of the faster option.
- **A multi-round plan where a later round depends on an earlier parallel
  round's output now blocks on that round's batched merge landing**, the
  same as any other cross-round dependency already did — no stacked-PR or
  rebase tooling was built to avoid this.

## What is enforced rather than asserted

`tools/test_process_router.py`: `delivering`'s push-exception and
merge-exception headings must each name "parallel" explicitly; the merge
exception must name the real mechanism
(`mcp__github__merge_pull_request`) rather than leaving it implicit. The
existing `_MERGE_VERBS` scan (no skill/command/tools file may contain the
literal phrase `gh pr merge` on an ungated line) is unchanged and still
passes — the batched-merge exception was written to use the GitHub MCP
tool specifically so it never needs that phrase.

`tools/test_worktree.py`: the new `branch` mode is proven to check out a
real, named branch (not detached) and to still resolve and prove its base
by ancestry, same as the existing detached mode; every existing detached
assertion is proven unchanged by the same run.

## The option it beat

Full automatic merging on approval of the plan itself (a standing
pre-authorization covering every future PR a round produces). Rejected
immediately, before any design work: it is exactly the "Say the word and
I'll push' is not approval" failure `delivering/SKILL.md` already named,
and it would have required weakening or deleting `_MERGE_VERBS` — this
repository's `CLAUDE.md` separately forbids weakening a test to make a
build pass, independent of the merge question itself.
