# Build turn checkpoints in a temporary index, not with `git stash create`

## Decision

`post-run/03-checkpoint.py` snapshots the working tree at every turn end by
pointing `GIT_INDEX_FILE` at a throwaway file, running `read-tree HEAD` +
`add -A` + `write-tree` against it, and storing the resulting `commit-tree`
object under `refs/checkpoints/<timestamp>`.

The real index, working tree and HEAD are never modified. The ref lives outside
`refs/heads/`, so a checkpoint is not a branch and does not appear in `git log`
or `git branch`. The newest 50 are kept.

## Why

The obvious implementation is `git stash create`, which returns a commit object
without touching anything. It was rejected on a specific failure:
**`stash create` ignores untracked files.** In a fresh or partially-tracked repo
— exactly this one, which had zero commits when the hook was written — it would
return a snapshot containing none of the new work, while appearing to succeed.
A safety net that silently saves nothing is worse than no safety net, because it
is trusted.

The temp-index approach captures untracked files, still respects `.gitignore`
(it goes through `git add`, so ignore rules apply), and is equally
non-destructive. Both properties are asserted directly in the test suite rather
than assumed.

Storing outside `refs/heads/` matters: a checkpoint must never be something you
can `git checkout` by tab-completion, or show up as clutter in branch listings,
while still being a real ref that garbage collection will not reclaim.

## Alternatives considered

- **`git stash create`.** Rejected above — misses untracked files.
- **`git stash push -u`.** Rejected: it *modifies the working tree*, reverting
  the user's in-progress edits. Catastrophic in a hook that fires automatically
  at every turn boundary.
- **Auto-commit to a WIP branch.** Rejected: moves HEAD, pollutes real history,
  and interacts badly with both the branch guard and the global `review_gate`
  receipt mechanism.
- **Copy files to a directory outside the repo.** Rejected: no dedup, no diffing,
  no `git restore`, and unbounded disk growth.
