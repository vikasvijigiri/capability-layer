# Git-flow walkthrough — one file through the whole chain

A live run on 2026-08-02. Subject: `dummy.py`, one line, `import os`. Every
output below is quoted from the run, not reconstructed.

Branch: `collapse-capabilities-into-routing`. Index at the time: 50 files staged
by earlier sessions, plus `dummy.py` = 51.

---

## What actually happened, in order

| # | Act | Tool | Hooks that fired | Result |
|---|---|---|---|---|
| 1 | write `dummy.py` | `Write` | `pre-edit/01-forbidden-change-guard` → `on-artifact-create/01-register`, `02-hook-self-test-nudge` | allowed silently |
| 2 | `git add -- dummy.py` | `Bash` | all 6 `pre-commit/*` | allowed — explicit pathspec is not a blanket add |
| 3 | `git commit -m "Add dummy.py" -- dummy.py` | `Bash` | all 6 `pre-commit/*` | **DENIED** by `05-docs-required` |

Stage 3 is where the run stopped. That is the correct outcome, and the reason is
in [What the deny actually proved](#what-the-deny-actually-proved).

---

## Stage → skill → hook

`.claude/workflow.md` owns the stage list; this table adds the git command and
the hook that guards it.

| Stage | Skill | Git command | Hook at that moment |
|---|---|---|---|
| 1 frame | `task-brief` | — | — |
| 2 design | `brainstormer` | — | — |
| 3 plan | `writing-plans` | — | — |
| 4 execute | `executing-plans` | `git add -- <paths>` | `pre-commit/06-index-scope-guard` (blanket-add trigger) |
| 5 validate | `verifying-work` | — | — |
| 6 review | `code-review` | — | writes the receipt `03-review-gate` later reads |
| 7 deliver | `delivering` | `git commit`, `git push`, `gh pr create` | `pre-commit/01`…`06` |
| 8 release | `releasing` | — | `pre-deploy/01-spend-guard` |
| 9 record | `knowledge-manager` | — | `post-run/06-artifact-autocommit` commits the prose |

A one-line file skips 1–5. It cannot skip 6, 7 and 9 — that is what the gates
are for.

---

## The six pre-commit hooks, and what each one said

Fired with `python tools/run_hook.py pre-commit --file <payload>.json`, one
payload per command shape.

### `git add -A` — blanket add

`06-index-scope-guard`, **ask**:

> ``index-scope-guard: `git add -A` stages everything in the working tree, not a
> set you chose. The index already holds 51 file(s). This is how 50 files from
> earlier sessions ended up staged in this repo for days.``

`git add -- dummy.py` produces nothing from this hook. Naming the path is the
whole difference.

### `git commit -m "Add dummy.py"` — no pathspec

Three hooks spoke at once.

`03-review-gate`, **ask** — a receipt existed but the diff had moved since:

> The change has been modified since it was reviewed, so the existing review no
> longer covers this commit.

`04-delivery-guard`, **additionalContext** (non-blocking):

> Git Delivery Guard notes (non-blocking): no review sign-off found in recent
> turns -- review the diff before proceeding.

`05-docs-required`, **deny**:

> 51 files staged and neither LOG.md nor HANDOFF.md is among them. Invoke
> `knowledge-manager` to record this unit of work in LOG.md/HANDOFF.md […] Set
> ALLOW_UNLOGGED_COMMIT=1 for a commit genuinely not worth logging.

`06-index-scope-guard`, **ask** — trigger 2, the load-bearing one:

> index-scope-guard: this commit would include 50 file(s) that were already
> staged when this session began, alongside 1 from this session.
> Inherited: .claude/workflow.md, docs/archive/00-vision.md, […] and 42 more

### `git commit -m "Add dummy.py" -- dummy.py` — with pathspec

`06-index-scope-guard` goes quiet: `PATHSPEC_COMMIT_RE` recognises that git will
only take the listed paths, so the commit cannot sweep. `03`, `04` and `05`
still fire, unchanged.

### `git push -u origin <branch>`

`03-review-gate`, **ask** (the push fingerprint is the HEAD sha, not the diff),
and `04-delivery-guard`, **ask**:

> Git Delivery Guard: push leaves the local machine -- explicit approval required.

`05-docs-required` and `06-index-scope-guard` are silent — both are commit-only.

### `git checkout main`

Nothing fires. `02-branch-guard` gates a *commit made while on* a protected
branch (`main`, `master`, `develop`, `release`), not the checkout.

### `01-secret-scan`

Silent throughout — `import os` matches none of its four patterns (AWS key,
private-key header, `ghp_` PAT, `key/secret/token/password = "…"`).

---

## What the deny actually proved

The scoped, correct command was still denied:

    $ git commit -m "Add dummy.py" -- dummy.py
    51 files staged and neither LOG.md nor HANDOFF.md is among them.

**`05-docs-required` judges the index, not the commit.** It calls
`git diff --cached --name-only` and counts everything staged, while git would
only have committed `dummy.py`. `06-index-scope-guard` has the pathspec
exemption (`PATHSPEC_COMMIT_RE`); `05-docs-required` does not. So a one-file
commit inherits the docs obligation of 50 files it was never going to touch.

Two readings, both defensible:

- **Working as intended** — the 50 files really are unrecorded, and the commit is
  the last moment that is visible.
- **A gap** — a pathspec commit is precisely the tool for *not* spending the
  index, and the gate that exists to reward that shape is overridden by one that
  ignores it.

Unresolved. It is the one thing this run found that the repo did not already
know about itself.

---

## Two things the run got wrong, and what they teach

**A malformed payload looks exactly like a passing hook.** The first attempt
wrote `"cwd":"c:\\Users\\…"` into a JSON file — `\U` is not a valid JSON escape.
All six hooks fail open on an unparseable payload, so `run_hook.py` printed six
`Running hook` lines and nothing else. Six silent allows and six silent
crashes are the same output. Use forward slashes in payload `cwd`, and treat a
fully silent hook run as unproven, not as green.

**The gates match verb text anywhere, including inside quotes.** A Bash call
whose only git content was `echo "########## B: git commit … ##########"` was
denied by `05-docs-required` — its `is_git_commit()` tokenises on whitespace and
found `git` followed by `commit`. That is deliberate
(`decisions/2026-08-01-review-gate-matches-verbs-anywhere.md`): one extra prompt
is cheaper than a missed sweep. The practical consequence is that you cannot
name these commands in a shell string without arming them.

---

## The route that would have completed

Pick one; each is a real decision, not a formality.

1. **Log it.** `knowledge-manager` writes `LOG.md`, stage it, commit
   `-- dummy.py LOG.md`. `05-docs-required` passes (`any(d in staged)`).
2. **Declare it unloggable.** `ALLOW_UNLOGGED_COMMIT=1` — and it must be set in
   Claude Code's own environment, not inline in the Bash command, where it never
   reaches the hook.
3. **Clear the index first.** `git restore --staged -- <the 50>`, which returns
   the count under `MIN_FILES = 10`.

Before any of them, stage 6 has to happen for real: `code-review` reads the
diff, asks for sign-off, and only then runs
`python .claude/hooks/pre-commit/03-review-gate.py --record`. That script
refuses without transcript evidence of a sign-off in the last turn:

> Refusing to record: no user sign-off found in the last 1 turns. […] Use
> --force only to test the mechanism itself, never to record a real review.

## Cleanup

`dummy.py` is staged and uncommitted. To undo the whole demo:

    git restore --staged -- dummy.py && rm dummy.py

## Known defect, unrelated to the flow

`04-delivery-guard` raised `UnicodeDecodeError: 'charmap' codec can't decode
byte 0x90` from a subprocess reader thread on the push payload — it reads git
output with the cp1252 console default instead of UTF-8. It fails open and still
emitted its `ask`, so nothing was lost, but the same class of bug turned a
passing check into a fake failure before (see `CLAUDE.md` gotchas).
