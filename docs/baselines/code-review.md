# Baseline: `code-review`

Date: 2026-08-04
Verdict: **passes the Iron Law.** Found two live defects and one scope error that
eight green suites and roughly thirty turns of self-checking had all missed.

## Why this baseline is unusually trustworthy

It was not staged. The baseline ran for most of a session *before* anyone thought
to invoke the skill, so there was no incentive to make it lose. The comparison is
between what actually happened and what happened next.

## The task

Judge whether branch `rebuild-capability-layer` was fit to deliver. 68 commits,
359 files, four days.

## Baseline — without the skill

Across roughly thirty turns the pattern was consistent, and it is worth naming
exactly because it *felt* like reviewing:

- Ran the suites after every change and reported the result: `8/8 suites PASS`,
  `mypy 24 files clean`, `ruff clean`.
- Ran `no-slop` twice at `--scope layer` and once at `--scope repo`.
- Installed into a virgin repo and ran the suites there.
- Reported each checkpoint with its file count and green status.

**What the baseline concluded:** repeatedly, that the work was in good shape, and
five separate offers to review it "when you want".

**What the baseline never did:** ask whether the branch was one change. Read the
diff as a whole. Look at the branch name. Check whether the deny hooks had any
test coverage at all.

The failure mode was not laziness — it was substituting *passing* for *reading*.
The skill names this exactly: "The suites pass, so it is reviewed. Passing is not
reading."

## With the skill

Step 0, before reading a line, on four numbers:

    'collapse' -> 0 paths    'capabilities' -> 37    'routing' -> 0 paths

The branch was named `collapse-capabilities-into-routing` and `routing` matched
nothing, because `.claude/routing/` had been deleted that morning. The branch was
doing the opposite of its name. Step 0 exists to ask this before the review is
spent, and it cost nothing.

Then two defects, neither visible to any suite:

1. `tools/test_hooks.py` fired five of seven event directories.
   `pre-edit/01-forbidden-change-guard.py` and `pre-deploy/01-spend-guard.py` had
   **no coverage at all** — and both are deny hooks, where a broken hook exits 0
   and *allows* what it exists to refuse. Silent permission.
2. `.claude/hooks/session-start/03-state-report.py:97` — `base_commit()` fell
   through to the root commit when HEAD was the default branch, reporting the
   whole 66-commit history as one branch's work. Verified: `base == root`.

Both were fixed before sign-off. A third finding was recorded and accepted rather
than fixed: `global-session-start/01-layer-bootstrap.py` writes 54 files into any
git repo root lacking `.claude/`.

## The delta

| | Baseline | With the skill |
|---|---|---|
| Scope error caught | no | yes, before reading |
| Live defects found | 0 | 2 |
| Untested deny hooks noticed | no | yes |
| Confidence expressed | high | qualified, with what was *not* read |

The last row matters as much as the count. The baseline reported green without
saying what it had not looked at; the skill forces a statement of the unread set —
the 60 `docs/` files, `docs/archive/`, the 13 `SKILL.md` bodies end-to-end.

## What it cost

Three turns: step 0 and the split question, assembling and reading the surface,
then the sign-off dialogue. Two extra turns to fix the findings. Around 380
characters of description budget on every turn of every session.

Against two live defects on one branch, and a scope error that would have cost the
whole review had it surfaced afterwards, that is cheap. **Keep.**

## Caveat on generality

One run, on an unusually large branch, in a repo whose diff is almost entirely
prose and hooks. It says nothing about how the skill performs on a two-file change
to application code, which is the common case and remains unmeasured.
