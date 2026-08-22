---
description: Granular git accounting — exact counts for committed, staged, unstaged, untracked, recoverable and branch scope (how many concerns one branch is carrying), with the command behind every number
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

Mode: read-only
Arguments: optional section filter in `$ARGUMENTS` such as `staged`, `history`, or `recoverable`.

Measure the repository. Report numbers with the command that produced them, never
a recollection. Read-only: this command never stages, commits, pushes or edits.

`/wip` answers "where was I" and judges whether the docs are stale. This one does
not judge — it counts. Use it before a commit to know exactly what would land.

Every number below must come from a command actually run in this turn. If a
command fails, say so and report the number as unknown rather than guessing.

---

## 1. Position

    git rev-parse --abbrev-ref HEAD          # current branch
    git branch --format='%(refname:short)'   # what branches exist AT ALL
    git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null

**Detect the base branch, never assume it.** A repository's base has been
`master` while the session banner claimed `main`; `git merge-base HEAD main`
returned `fatal: Not a valid object name main`. Take the first that resolves:

    for b in main master develop; do git rev-parse --verify -q "$b" && break; done

Then, only if an upstream exists:

    git rev-list --left-right --count <base>...HEAD    # behind<TAB>ahead

Report: branch, whether it is protected (`main`, `master`, `develop`, `release` —
`permission-security/02-branch-guard.py` denies commits there), the base actually found,
and ahead/behind. Say "no upstream" plainly rather than printing 0.

## 2. The four buckets, and why they overlap

    git diff --cached --name-only | wc -l        # STAGED   -- queued for commit
    git diff --name-only | wc -l                 # UNSTAGED -- edited, not queued
    git ls-files -o --exclude-standard | wc -l    # UNTRACKED -- git has never seen
    git status --porcelain -uall | wc -l          # DISTINCT PATHS

**`-uall` is mandatory.** Plain `--porcelain` collapses a new directory to one
entry (`?? docs/specs/`), hiding every file in it. That bug made
`stop-finalization/06-artifact-autocommit.py` see no new spec at all.

The first three do not sum to the fourth: one file can be both staged and
unstaged (staged, then edited again). Report all four and say so — a single
"88 files changed" hides the distinction that matters at commit time.

## 3. Status codes — the granular view

    git status --porcelain=v1 -uall | awk '{print substr($0,1,2)}' | sort | uniq -c | sort -rn

Left column = index, right = working tree. `R ` is a staged rename, ` M` an
unstaged edit, `??` untracked, `RM` renamed then modified. This distinguishes
"50 files staged" from "50 pure renames", which is the difference between a
change needing review and one that does not.

## 4. What a bare `git commit` would actually take

    git diff --cached --stat | tail -1
    git diff --cached --name-only | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn

A commit spends the index, not your intent. `0 insertions(+), 0 deletions(-)`
across 50 files means pure renames.

## 5. Inherited work — what an earlier session left staged

    git diff --cached --name-only | wc -l            # staged right now
    git log -1 --format='%h %ar %s'                  # when the last commit landed

**No longer tracked automatically.** `session-init/03-index-baseline.py` and
`permission-security/06-index-scope-guard.py` recorded and guarded this until they were
deleted, along with the `_hooklib` helpers this section used to
call. Git itself cannot tell "staged a moment ago" from "staged on Tuesday", so
if the index is non-empty and the last commit is old, say the staged set is of
**unknown provenance** rather than guessing.

The condition that made this valuable is gone: `stop-finalization/06-artifact-autocommit.py`
commits every turn, so the index does not accumulate across sessions any more. If
you find a large staged set here, that is itself the finding — the auto-commit
has been refusing, and its reason is in the Stop output.

## 6. Commit history, counted

    git rev-list --count HEAD                       # commits in total
    git log --since=midnight --oneline | wc -l       # commits today
    git rev-list --count <base>..HEAD                # commits this branch adds
    git show --stat --format='%h %s' HEAD            # what the last one touched

## 7. What is recoverable if this goes wrong

    git for-each-ref --count=5 --sort=-creatordate \
      --format='%(refname:short)  %(creatordate:relative)' refs/checkpoints/
    git stash list | wc -l

`stop-finalization/03-checkpoint.py` snapshots the whole tree every turn. This is why a
large uncommitted pile is a reviewability problem, not a safety one — say that
explicitly, because the size of the number invites the opposite conclusion.

## 8. Branch scope — how many concerns are on this branch

    git rev-list --count <base>..HEAD                     # commits it adds
    git diff --name-only <base>..HEAD | wc -l             # files it touches
    git diff --name-only <base>..HEAD | awk -F/ '{print $1}' | sort | uniq -c | sort -rn
    git log --reverse --format='%ar' <base>..HEAD | head -1   # how old it is

Name coherence — do the changed paths have anything to do with what the branch is
called? Tokens from the name, counted against the paths:

    git rev-parse --abbrev-ref HEAD | tr '_/-' '\n' | grep -v '^$' | \
      while read t; do \
        printf '%-22s %s\n' "$t" "$(git diff --name-only <base>..HEAD | grep -ic "$t")"; \
      done

The dash goes **last** in `tr`'s first argument. Leading, it parses as an option
flag and the command dies with `tr: unknown option -- _`.

A token matching **zero** paths is the signal worth reporting. It means the branch
is no longer doing the thing it is named after — either it drifted, or it grew a
second concern that deserves its own branch.

Report the four numbers and any zero-match tokens. **Do not judge and do not
gate.** There is no file count that means "too many": a wide rename is 300 files
and one concern, while two unrelated bug fixes are four files and two. The
question that decides it is *could half of this have merged separately and still
made sense* — and that is `code-review`'s to ask, not this command's.

Measured on a real branch — 26 commits, 337 files, 3 days, 11 top-level areas —
the name check reads:

    collapse          0 paths
    capabilities     37 paths
    into              0 paths
    routing           1 paths

Three of four tokens match essentially nothing. The branch is named after a
capability-layer collapse and now carries the hook layer, the skill layer, the
gate deletion, the commit loop, the model policy, the context budget and the
project-check layer. That is the case this section exists to make visible, and it
took four numbers to see.

## 9. Surprises worth surfacing

    git ls-files -i -c --exclude-standard          # tracked but ignored -- contradiction
    git ls-files -v | grep '^[a-z]'                 # assume-unchanged / skip-worktree
    git count-objects -vH | grep size-pack

Report only non-empty results. A tracked-but-ignored file, or one marked
assume-unchanged, silently disappears from every diff and is worth knowing about.

---

## Output shape

A table of the numbers first, then at most three observations that the numbers
themselves do not make obvious — a bucket that is unexpectedly large, an inherited
set that is about to be swept, a status code that changes how the work should be
reviewed. No narrative, no next-action advice; that is `/wip`.

Rules:

- **Quote real output.** A number with no command behind it is a guess.
- **Never assume `main` exists.** Detect the base or report that there is none.
- **Do not fix anything you find.** Read-only, including "helpfully" unstaging.
- If I passed an argument, treat it as a section filter (e.g. `staged`, `history`,
  `recoverable`) and say which sections you skipped: $ARGUMENTS
