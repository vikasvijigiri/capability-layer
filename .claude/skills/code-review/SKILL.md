---
name: code-review
description: Use when a change is about to be delivered and has not been reviewed - before "git commit", "git push", "gh pr create", or whenever the review gate returns "No code review has been recorded". Triggers include "review the diff", "review this change", "review my code", "review the PR", "check this before I commit", "is this ready to ship", "look over these changes", "code review", "can you sanity check this". Also use when the gate asks a second time because the change moved after an earlier review. Do NOT use to write new code, to fix what the review finds (report first, fix as separate work), or for a diff you have not actually read.
effort: high
model: opus
---

# Code Review

Review a pending change, report what is actually wrong with it, then get the
user's sign-off. The sign-off is the only thing that records a review receipt,
which is what lets `pre-commit/03-review-gate.py` stop asking.

Cap visible output at ~500 tokens. Findings, not a recap of the diff.

<HARD-GATE>
NEVER run `--record` without the user explicitly signing off in this turn.
Recording is the whole mechanism: the receipt is a claim that a human was shown
this change and accepted it. Recording on your own judgement — however clean the
diff — forges that claim and silently disarms the gate.

"No findings" is not sign-off. Ask anyway.
</HARD-GATE>

## Why the gate needs you

A hook fires once, mechanically, and cannot read a diff or hold a conversation.
`03-review-gate.py` therefore can only ask *whether* a review happened; it cannot
perform one. It answers that question by looking for a receipt fingerprinted to
the exact content being delivered. No receipt, or a receipt for different
content, means it interrupts.

Nothing else writes that receipt. If you skip the sign-off, the gate asks
forever and the user learns to click through it — which is worse than no gate.

## Steps

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
  with no signal. This repo's stated rule is that no failure stays silent.
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

- **Approve and record** — runs `--record`, the gate stops asking for this exact
  content. State plainly that you are recording on their authority.
- **Approve without recording** — they accept the change but the gate keeps
  asking. Correct when the diff is about to move again.
- **Not yet** — nothing recorded. They want findings addressed first.

Free-text **Other** is appended by the tool. A plain "yes"/"approved" in chat is
sign-off; the dialogue is the default, not a hoop.

**5. Record, only on approval.**

```bash
python ".claude/hooks/pre-commit/03-review-gate.py" --record        # commit or push
python ".claude/hooks/pre-commit/03-review-gate.py" --record --pr   # pull request
```

`--pr` fingerprints the branch against its base; plain `--record` fingerprints
the working tree. Recording the wrong one leaves the gate asking, correctly.

Then stop. Do not commit, push, or open the PR yourself unless separately asked.

## Red Flags — stop, do not record

- "The diff is small and clean, I'll record and mention it after."
- "They said 'go ahead' about the task, so that covers the review."
- "No findings, so there is nothing to sign off on."
- "I'll record now and they can review the summary." Backwards — the receipt
  claims they already did.
- "The gate is noisy, recording will quiet it down." The noise is the feature.
- Reviewing `git diff` for a PR. That is today's edit, not the branch.

**Each of these means: do not run `--record`. Ask.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Summarising the diff instead of judging it | The user can read the diff; they cannot see what you think is wrong with it |
| Findings with no `file:line` | Unactionable, and indistinguishable from a guess |
| Reviewing only tracked changes | A brand-new untracked file has no diff and is the likeliest place for a defect |
| Fixing findings inside the review | The receipt then covers content that no longer exists; the gate re-asks and the review is wasted |
| Recording with `--record` when the delivery is a PR | Wrong fingerprint kind; the gate asks again and the sign-off is lost |

## Routing

- Mandatory validator: none. The sign-off in step 4 is the gate, and it is the
  only thing that may write a receipt.
- Terminal handoff: none. This reports and records; it does not deliver.
- Triggered by `03-review-gate.py` returning `ask` on `git commit`, `git push`
  or `gh pr create`, or invoked directly before any of those.
- Findings that need real work become their own task via `task-brief`. Do not
  absorb them here.

## Success

The user saw the findings, said yes or no explicitly, and the receipt exists if
and only if they said yes. Re-running the same delivery command now passes the
gate silently; changing one byte of the diff makes it ask again.
