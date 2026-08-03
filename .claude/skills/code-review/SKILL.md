---
name: code-review
description: Use before a change is delivered - before "git commit", "git push" or "gh pr create". Triggers include "review this change", "review the PR", "is this ready to ship", "code review", "sanity check this". Do NOT use to write code, to fix what the review finds (report first, fix separately), or for a diff you have not actually read.
effort: high
model: sonnet
---

# Code Review

Review a pending change, report what is actually wrong with it, then get the
user's sign-off.

Cap visible output at ~500 tokens. Findings, not a recap of the diff.

<HARD-GATE>
NEVER report a change as reviewed without having read the actual diff, and never
treat your own approval as the user's. "No findings" is not sign-off — ask anyway.

State plainly what you read and what you did not. A review that silently skipped
half the change is worse than no review, because it is indistinguishable from a
thorough one.
</HARD-GATE>

## Why this is a skill and not a hook

A hook fires once, mechanically, and cannot read a diff or hold a conversation.
A `pre-commit` review gate tried to enforce this and was deleted:
it could only ask *whether* a review happened, never perform one, and
its receipt fingerprinted the whole working tree — so writing the log entry that
`05-docs-required.py` demanded — a gate deleted alongside it — invalidated the
receipt,
a measured deadlock.
Five comparable repos were read and not one gates review this way.

So the enforcement is this skill plus the user, not a mechanism. The upside is
that it can no longer be satisfied by a file on disk; the cost is that skipping
it is now silent. Do not skip it.

## Steps

**0. Before reading anything: is this one change or several?**

Only when the surface is a branch or a PR — skip it for a working-tree review.
Four numbers, quoted:

```bash
git rev-list --count <base>..HEAD
git diff --name-only <base>..HEAD | wc -l
git diff --name-only <base>..HEAD | awk -F/ '{print $1}' | sort | uniq -c | sort -rn
git log --reverse --format='%ar' <base>..HEAD | head -1
```

Then ask the one question that decides it: **could half of this have merged
separately and still made sense?** If yes, say so now and ask whether to split
before you read a line. Splitting after a review throws the review away; the
decision is nearly free before it and expensive after.

There is deliberately **no threshold**. A wide rename is 300 files and one
concern; two unrelated bug fixes are four files and two concerns. File count is a
proxy that fires on the wrong things — it is why Danger.js's large-PR warning
gets talked past. Judge coherence, not size.

The strongest single signal is cheap: a token in the branch *name* that matches
zero changed paths means the branch stopped doing what it is called. `/git-state`
section 8 prints it.

State the verdict in one line either way — "one concern" is a finding too, and
saying it is what stops this becoming a step people skip.

**1. Get the change.** Pick the surface from what is being delivered:

| Delivering | Read |
|---|---|
| `git commit` | `git diff --cached` and `git diff`, plus `git status --porcelain` for new files |
| `git push` | `git log <upstream>..HEAD` and the diff across those commits |
| `gh pr create` / `merge` | `git diff <merge-base> HEAD` — the whole branch, not today's edit |

Untracked files carry no diff content. Open them; a whole new file is the change
most in need of review and the one a diff shows least.

**2. Review it.** Report only what you can point at — file and line. In priority
order:

- **Correctness** — logic that is wrong, not merely unusual. State the input that
  breaks it.
- **Security** — injected input, secrets, widened permissions, auth paths.
- **Silent failure** — a swallowed exception, a bare `except`, a degraded path
  with no signal. The standing rule is that no failure stays silent.
- **Tests** — a behaviour change with no test, or a test weakened to pass.
- **Repo rules** — AI attribution in a commit message, a named skill or file path
  that does not resolve, a hook edited but never run against a payload.
- **Simplification** — only where it is concrete. "Could be cleaner" is not a
  finding.

**3. Report.** Group by severity, most severe first. Each finding: `file:line`,
one sentence on the defect, one on what breaks. If nothing is wrong, say so in
one line and name what you checked — an empty review that lists nothing looks
identical to a review that never happened.

**4. Get sign-off.** `AskUserQuestion`:

- **Approve** — they accept the change as reviewed.
- **Approve with findings noted** — they accept it and want the findings recorded
  in `ISSUES.md` or `HANDOFF.md` rather than fixed now.
- **Not yet** — they want findings addressed first.

Free-text **Other** is appended by the tool. A plain "yes"/"approved" in chat is
sign-off; the dialogue is the default, not a hoop.

**5. Say what the review covered.** One line naming the files read and the files
not read. Nothing mechanical records this, so the statement in
the conversation — and in the commit message, if one follows — is the only trace
the review happened at all. Write it as evidence, not as reassurance.

Then stop. Do not commit, push, or open the PR yourself unless separately asked.

## Red Flags — stop and ask

- "The diff is small and clean, I'll call it reviewed and mention it after."
- "They said 'go ahead' about the task, so that covers the review."
- "No findings, so there is nothing to sign off on."
- "I'll say it's reviewed and they can read the summary." Backwards — the claim
  asserts they already did.
- "The suites pass, so it is reviewed." Passing is not reading.
- Reviewing `git diff` for a PR. That is today's edit, not the branch.
- "It is a big branch but I will just review it all." Step 0 exists because that
  is the expensive order. Ask first.
- "Splitting is the user's call, I will mention it in the findings." By then the
  review is spent — mentioning it costs them the work twice.

**Each of these means: ask.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Summarising the diff instead of judging it | The user can read the diff; they cannot see what you think is wrong with it |
| Findings with no `file:line` | Unactionable, and indistinguishable from a guess |
| Reviewing only tracked changes | A brand-new untracked file has no diff and is the likeliest place for a defect |
| Fixing findings inside the review | The sign-off then covers content that no longer exists, and nobody can tell which version was accepted |
| Reviewing the working tree when the delivery is a PR | A PR delivers every commit the base lacks, not today's edit |
| Reading the diff before asking whether it is one change | A split decision after the review discards it; before, it costs nothing |
| Treating a file count as the split signal | A 300-file rename is one concern; two four-file fixes are two |

## Next step — you MUST take it

**The terminal state is invoking `delivering`**, once the user has signed off.
Do not commit, push or open the PR here; that skill owns the route and its own
approval gate.

## Parallel work — `diff-reviewer`

For a change large enough that one pass blurs the angles together, write the
diff to a file and dispatch a **`diff-reviewer`** per angle — `correctness`,
`security`, `test-quality`, `scope` — in the same message. Each returns findings
with `file:line`; you merge them, drop duplicates, and present one list.

Hand over the diff as a **path**, never pasted: anything you paste into a
dispatch stays in your context for the rest of the session.

What does not delegate: assembling the surface, showing the user, and asking for
sign-off. An agent reporting "looks good" is not a review a human gave.

**Only when the user has asked for subagents.**

## Routing

- Mandatory validator: none. The sign-off in step 4 is the gate.
- Preceded by `no-slop`, which sweeps the repo at stage 6 — so its repairs
  are part of the diff you are reading, not a separate unreviewed change.
- Terminal handoff: `delivering`, once the user has signed off. This skill does
  not push, merge or open the PR itself — that is `delivering`'s job, and it has
  its own approval gate.
- Invoked directly before `git commit`, `git push` or `gh pr create`. Nothing
  fires it automatically: a review gate did until it was deleted, so this is now
  a habit rather than an interrupt.
- Findings that need real work become their own task via `task-brief`. Do not
  absorb them here.

## Success

The user saw the findings, said yes or no explicitly, and the answer is written
somewhere durable — the commit message, `HANDOFF.md`, or `ISSUES.md`. A review
that lives only in the conversation is lost at the next context reset.
