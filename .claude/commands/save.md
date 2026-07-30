---
description: Stage, describe and commit the current work in one step (local only, never pushes)
---

Commit the current work. This is a convenience wrapper, not an automation —
every step that needs judgment stays visible, and nothing leaves the machine.

Run these in order:

1. `git status --porcelain` and `git diff --stat`. If there is nothing to
   commit, say so and stop.

2. Check the branch with `git rev-parse --abbrev-ref HEAD`. If it is `main`,
   `master`, `develop` or `release`, do **not** try to commit — the branch guard
   will deny it. Propose a short branch name derived from the actual change and
   ask before running `git checkout -b <name>`.

3. Read the full diff (`git diff` and `git diff --cached`). Write a commit
   message describing **why** the change was made, not a restatement of the
   file list. A subject line under 72 characters, and a body only when the
   reason is not obvious from the subject.

4. Show me the proposed message and the list of files, then stage and commit.
   Prefer `git add <specific paths>` over `git add -A` so nothing unrelated is
   swept in.

5. Report the resulting short SHA.

Rules:

- **Never push.** Not part of this command. If I want that I will ask.
- Never use `--no-verify`, and never bypass a hook that denies the commit —
  report what it said instead.
- If the secret scan denies the commit, do not try to work around it. Show me
  the flagged file.
- If I passed an argument, treat it as the intended commit message or as
  guidance for writing one: $ARGUMENTS
