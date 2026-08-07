---
name: using-git-worktrees
description: Work must be isolated from the current checkout before implementation - multi-file changes, parallel work, risky experiments. Triggers include "create a worktree", "isolate this work", "keep this off main". Do NOT use for read-only research, work already in the right worktree, or a one-file edit with explicit branch context.
when_to_use: before implementation when checkout isolation is required
effort: medium
model: sonnet
disable-model-invocation: true
---

# Using Git Worktrees

Create and verify an isolated working directory before implementation begins.

## Procedure

1. Resolve the repository root, current branch, worktree state, and target
   branch. If already inside a linked worktree, keep it and report its path.
2. Never create a worktree from an unrecorded dirty state without first naming
   what must be preserved. Do not hide, discard, reset, or overwrite changes.
3. Choose a descriptive branch and a worktree path under the repository's
   approved worktree directory. Confirm both with the user when the choice is
   not already explicit.
4. Create the worktree from the intended base commit. Verify its absolute path,
   branch, HEAD, and clean status before handing it to the executor.
5. Pass the worktree path, branch, base commit, and cleanup rule as file-backed
   context to the next skill. Do not paste a large state dump into a subagent.
6. Do not remove the worktree during implementation. Cleanup belongs after
   delivery or explicit abandonment, after checking for uncommitted work.

## Safety rules

- Never work directly on a protected branch for a multi-step change unless the
  user explicitly chose that path.
- Never use `git reset --hard`, `git clean`, or branch deletion as setup.
- Never assume a worktree is isolated if `git worktree list --porcelain` does
  not prove it.
- If native isolation exists in the harness, use it; otherwise use Git's
  worktree mechanism and record the fallback.

## Routing

- Entered from any implementation-bound task that needs isolation.
- Terminal handoff: the stage that requested isolation, normally
  `executing-plans`.
- A failed setup is an infrastructure failure; diagnose it before editing code.

## Success

The executor has a verified worktree path, branch, base commit, and clean
starting state, and the original checkout remains unchanged.
