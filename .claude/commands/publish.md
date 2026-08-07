---
description: Create the GitHub repository, add the remote, push the branch and open the PR after explicit confirmation; never configures its own merge gates.
---

# Publish

Mode: mutating
Arguments: `$ARGUMENTS` is the repository name, or empty to propose one from the
directory name. It is not permission to publish.

Outward-facing: this is the only command here that sends anything to a service.

This is the only command that sends anything off this machine. A repository,
once public, can be indexed, cloned or forked before anyone deletes it — so the
confirmation in step 4 is the whole point, and showing a plan is not confirmation.

## Order

1. Run `/verify` (equivalently `python tools/run_checks.py --tier all --require-test`).
   Stop if anything is red. The verification must be fresh for this tree; do not
   continue from an earlier transcript claim.
2. Run `git remote -v`, `git status --porcelain=v1 -uall`, `git log --oneline @{u}..HEAD`
   or `git log --oneline -20` when there is no upstream, and `gh api user --jq .login`.
   Stop if a remote already exists — this command creates one, it does not
   re-point an existing repository at somewhere else.
3. Report, in this order: the resolved owner, the proposed repository name, the
   visibility, the branch, the number of commits that would be pushed, and any
   uncommitted paths that would **not** be pushed.
4. Ask for **explicit confirmation**, naming the visibility in the question.
   Default to `--private`. Public is a separate answer, never an assumption.
5. `gh repo create <owner>/<name> --private --source . --remote origin`
   then `git push -u origin <branch>`. Never `--force`, never to `main`.
6. `gh pr create --fill --base main --head <branch>`.
7. Print the settings to enable by hand, and stop:

       branch protection on `main`  → require the status check `conclusion`
       merge queue                  → enable for `main`

## Never

- Never enable branch protection, required checks, or the merge queue itself.
  Those settings decide what may merge unattended; an agent that configures its
  own gates has removed the reason the gates exist. Print them, let a human set them.
- Never `gh pr merge`, `--admin`, or `--auto` in this command. Landing is
  `delivering`'s business and the queue's, after review.
- Never publish a repository whose tree has uncommitted secrets — step 1 runs
  the secret scan as part of the tier, and a red tier stops here.
- Never make a repository public without being told to, in that turn.

## Why it is a command and not a hook

This layer shipped an automatic version once: a `SessionStart` hook installed
the whole capability layer into any git repository it found, unasked. It was
removed on 2026-08-07 with `install.py`, and `session-start/02-bootstrap-docs.py`
was reduced from authoring to detection —
`tools/test_session_start_contract.py` now asserts it creates nothing.

A hook fires unasked and its failure mode is silence. Publishing is irreversible
and outward-facing, so it gets a command, one confirmation, and a human.
`session-start/03-state-report.py` reports the `[state:no-remote]` condition when
a branch has commits and nowhere to send them; reporting is a hook's job, acting
is not.
