---
description: Granular git accounting — exact counts for committed, staged, unstaged, untracked, inherited and recoverable, with the command behind every number
---

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

**Detect the base branch, never assume it.** On 2026-08-02 this repo's base was
`master` while the session banner claimed `main`; `git merge-base HEAD main`
returned `fatal: Not a valid object name main`. Take the first that resolves:

    for b in main master develop; do git rev-parse --verify -q "$b" && break; done

Then, only if an upstream exists:

    git rev-list --left-right --count <base>...HEAD    # behind<TAB>ahead

Report: branch, whether it is protected (`main`, `master`, `develop`, `release` —
`pre-commit/02-branch-guard.py` denies commits there), the base actually found,
and ahead/behind. Say "no upstream" plainly rather than printing 0.

## 2. The four buckets, and why they overlap

    git diff --cached --name-only | wc -l        # STAGED   -- queued for commit
    git diff --name-only | wc -l                 # UNSTAGED -- edited, not queued
    git ls-files -o --exclude-standard | wc -l    # UNTRACKED -- git has never seen
    git status --porcelain -uall | wc -l          # DISTINCT PATHS

**`-uall` is mandatory.** Plain `--porcelain` collapses a new directory to one
entry (`?? docs/specs/`), hiding every file in it. That bug made
`post-run/06-artifact-autocommit.py` see no new spec at all.

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

    python -c "import sys; sys.path.insert(0,'.claude/hooks'); \
    from _hooklib import load_index_baseline, staged_paths; \
    b=set(load_index_baseline() or []); s=set(staged_paths() or []); \
    print(f'inherited_still_staged={len(b&s)} this_session={len(s-b)}')"

`session-start/03-index-baseline.py` records what was already staged when the
session began, because git cannot tell "staged a moment ago" from "staged on
Tuesday". Anything in the intersection would land under your commit message
without being your work — `pre-commit/06-index-scope-guard.py` asks about exactly
this. A `None` baseline means unknown, not zero; report it as unknown.

## 6. Commit history, counted

    git rev-list --count HEAD                       # commits in total
    git log --since=midnight --oneline | wc -l       # commits today
    git rev-list --count <base>..HEAD                # commits this branch adds
    git show --stat --format='%h %s' HEAD            # what the last one touched

## 7. What is recoverable if this goes wrong

    git for-each-ref --count=5 --sort=-creatordate \
      --format='%(refname:short)  %(creatordate:relative)' refs/checkpoints/
    git stash list | wc -l

`post-run/03-checkpoint.py` snapshots the whole tree every turn. This is why a
large uncommitted pile is a reviewability problem, not a safety one — say that
explicitly, because the size of the number invites the opposite conclusion.

## 8. Surprises worth surfacing

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
