---
name: delivering
description: Use when verified, reviewed work needs to reach its destination in the repository - merged, pushed, opened as a PR or handed over. Triggers include "ship it", "deliver this", "merge this", "open a PR", "raise the PR", "push this up", "wrap this up", "finish the branch", "how do we land this", "what do we do with this branch". Also use when a branch is complete and the integration route has not been chosen. Do NOT use to review the change first (code-review), to prove it works (verifying-work), to put the change into a running environment (releasing), or to record what happened afterwards (knowledge-manager).
effort: high
model: opus
---

# Delivering

Land finished work where it belongs in the repository, without deciding on the
user's behalf. Workflow stage 7.

**This stage ends at the branch, not at the environment.** Merging changes a
repository; releasing changes what users are looking at right now. `releasing`
owns the second act, and its approval is separate from this one.

Cap visible output at ~500 tokens.

<HARD-GATE>
NEVER push, merge, publish or deploy without explicit approval in this
conversation.

This is CLAUDE.md's standing rule and it survives every argument for skipping
it: a clean review, an obvious base branch, an approval given about something
else earlier, or a user who "clearly wants it merged". The integration decision
is theirs. Present the options and wait.

A local commit is not covered by this gate. Everything that leaves the machine
is.
</HARD-GATE>

## Three preconditions, checked in order

Do not present the menu until all three hold. Each is a question with a command
behind it, not a judgement.

1. **The checks pass, on this tree.** Run `/verify` now and quote it. A run from
   earlier proves the tree it ran on. If anything fails, report the failures and
   stop — the menu comes after a green suite.
2. **The work was verified against what was asked.** `verifying-work` produced a
   coverage verdict, and its gaps are closed or explicitly accepted. Green
   suites are not that verdict.
3. **The branch was reviewed and signed off.** `code-review` ran over
   `git diff <merge-base> HEAD` — the branch, not the working tree — the user
   answered explicitly, and the answer is written down.

   This is *the* review boundary. Since 2026-08-02 commits are automatic `wip:`
   checkpoints made by `post-run/06-artifact-autocommit.py`; none of them was
   reviewed and none was meant to be. Everything they contain is reviewed here,
   once, or not at all. Squash-merge so the checkpoints collapse into the message
   a human actually wrote.

State which of the three you actually ran. "All good" is not one of them.

## Choosing the route

Determine the base branch before offering anything — whatever this work forked
from, named in the plan, the conversation, or the branch's upstream. If it is
not already known, ask: "This branch split from `<best guess>` — correct?"
Merging into the wrong base is expensive to undo.

Then present exactly these, and wait:

```
Work verified and reviewed. What would you like to do?

1. Merge back to <base> locally
2. Push and open a pull request
3. Keep the branch as-is
```

Present it as written. **Discarding is not on the menu** — it happens only when
the user asks for it in so many words, and then only after they type `discard`
against a list of exactly what disappears.

## Executing the choice

**Merge locally.** Merge first, then verify the merged result before deleting
anything: `git checkout <base>` → `git merge <branch>` → run `/verify` again on
the merged tree. If it fails, stop and leave the branch in place — nothing has
left the machine and the merge is recoverable. Only once green: `git branch -d`.

**Pull request.** `git push -u origin <branch>`, then open the PR against the
base with `gh`, following the repo's PR template if one exists, and report the
URL.

A PR delivers every commit this branch has that the base does not — so the
review that covers it is one over `git diff <merge-base> HEAD`, not over today's
working tree. If `code-review` only saw the working tree, review the branch
before opening the PR.

**Keep as-is.** Report the branch name and stop. This is a legitimate outcome,
not a failure to deliver.

## The gates you will meet, and what each means

These fire on the delivery commands themselves. None is noise; each names a real
missing thing.

| Gate | Fires when | The actual fix |
|---|---|---|
| `01-secret-scan.py` | A staged file matches a credential pattern | Remove the secret. Never override |
| `02-branch-guard.py` | The commit is destined for a protected branch | Branch first |
| `04-delivery-guard.py` | AI attribution in the commit message | Remove it — git history carries no AI attribution here |
| `06-index-scope-guard.py` | A blanket `git add`, or a commit spending files staged before this session | Name the paths: `git commit -- <paths>` |

`03-review-gate.py` and `05-docs-required.py` were deleted on 2026-08-02, so
review and recording are no longer enforced here at all — they are steps 2 and 3
of the checklist above and nothing will stop you skipping them.

## Before anything irreversible

Say plainly, in one line each: what will move, where it will land, and what
cannot be undone. Then wait for a yes. A push to a shared branch, a merge, a
release and a deploy are all in this class; a local commit is not.

If the push is rejected, the remote moved. Investigate. Force-push only on an
explicit request for it.

## Red Flags — stop, do not deliver

- "The review was clean, so I'll just push it."
- "They said go ahead earlier." About what, and to where?
- "The base is obviously `main`."
- "Tests passed a few turns ago."
- "I'll open the PR and they can look at it there." The receipt claims they
  already did.
- "The gate is noisy, I'll set the override." The override is for the case you
  can name out loud.
- "They seem finished with this — I'll offer to discard it."
- "Force-push will fix the rejection."

**Each of these means: stop and ask, in this conversation.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Presenting the menu before the three preconditions | The user chooses under a false premise |
| Deleting the branch before verifying the merged result | The recoverable state is gone |
| `--record` where `--pr` was needed | Wrong fingerprint kind; the sign-off is lost |
| Overriding a gate to make it quiet | The noise was the feature; the next person inherits a disarmed gate |
| Treating "keep as-is" as failure | It is one of the three legitimate outcomes |
| Delivering, then logging | The log entry is part of delivery, not an afterthought |

## Next step — you MUST take it

**Does this repo have a deploy target?** That question decides the handoff, and
it is answered from the repo, not from memory — `releasing` step 2 lists the
files that answer it.

- **Yes** → `releasing`. The branch moved; the environment has not. Say so
  rather than letting "delivered" stand in for "live".
- **No** → `knowledge-manager` directly. A library, a docs change or a
  `.claude/` edit has nothing to release, and inventing a release for it is
  worse than skipping the stage.

Either way the unit of work is not finished until `LOG.md` says what shipped and
`HANDOFF.md` reflects the new state. A hard-to-reverse decision also earns a
`decisions/` record.

## Routing

- Mandatory validator: none — the HARD-GATE plus the three preconditions are it.
- Preceded by `verifying-work` and then `code-review`. Both, in that order.
- Terminal handoff: `releasing` when a deploy target exists; `knowledge-manager`
  directly when there is none — this stage is terminal only for work with no
  environment. Handing to `releasing` does not carry this stage's approval with
  it; that stage takes its own, per target.
- Never invoked to *fix* what a gate found. Each row above routes somewhere else.

## Success

The work reached the destination the user chose, every gate that fired was
answered rather than bypassed, the merged or pushed result was verified on the
tree that actually landed, and `LOG.md` says what shipped.
