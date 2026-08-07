---
description: Prepare and commit the current work locally after verification and explicit human confirmation; never push.
---

# Save

Mode: mutating
Arguments: `$ARGUMENTS` is the requested commit-message guidance, not permission to bypass review.

This command can change Git state. Follow this exact order:

1. Run `/verify` (equivalently `python tools/run_checks.py --tier all --require-test`),
   then run `git status --porcelain=v1 -uall` and `git diff --stat`.

   The verification result must be fresh for this tree. Do not continue from
   an earlier transcript claim.
2. Stop if checks fail, the tree is empty, or the branch is
   `main`, `master`, `develop`, or `release`.
3. Read the complete staged and unstaged diff. Propose a subject under 72
   characters and list the exact paths that would be staged.
4. Use **`AskUserQuestion`** immediately before `git add` and `git commit`,
   with the proposed subject in the question. Showing a message is not
   confirmation, and neither is a prose question — approval has to be a click
   the user made, not an inference from whatever they said next.
5. Stage only the listed paths, commit without `--no-verify`, and report the
   resulting short SHA.

Never push. Never use `git add -A`, bypass hooks, amend unrelated work, or
commit a secret. If a hook denies the commit, report its message and stop.
