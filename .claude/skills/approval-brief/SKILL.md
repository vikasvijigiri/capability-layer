---
name: approval-brief
model: opus
description: Packages a decision a human is about to approve - what changes, what it costs, what breaks if it is wrong, and how to undo it - so approval is informed rather than reflexive. Use before any push, merge, deploy, release, migration, deletion or spend, and for "is this ok to do", "can I go ahead", "do you approve", "should I proceed", "about to ship this", "ready to push", "shall I run it". Prefer this over a bare yes/no question - approval given without blast radius and a rollback path is not consent, it is a guess. Do NOT use for reversible local actions that need no gate.
---

# Approval Brief

Both human gates in the pipeline are enforced by hooks, but nothing tells the human what
they are agreeing to. This does.

## The brief - five lines, in this order

1. **What will happen** - the concrete action, one sentence, imperative. "Push 14 commits
   to `origin/main`", not "finalise the work".
2. **Blast radius** - who and what is affected if this is correct. Draw from
   `impact-analysis` when the change is non-trivial.
3. **What breaks if this is wrong** - the realistic failure, not the worst imaginable one.
   Say whether it fails loudly or silently; silent is worse and must be stated.
4. **How to undo it** - the actual command or procedure, and honestly whether it is
   *reversible*, *recoverable with effort*, or *irreversible*. Never claim reversible
   without naming the mechanism.
5. **Cost** - money, time, or rate/quota consumed. State zero explicitly when it is zero.

## Rules

- **Never bundle.** One approval per irreversible action. A single yes covering a push and
  a deploy is not informed consent for either.
- **Lead with the irreversible part.** If any component cannot be undone, that is the
  headline, not a footnote.
- **State unknowns.** "I have not verified whether X has consumers" belongs in the brief,
  not omitted because it weakens the ask.
- Give the recommendation, then the option to decline and what follows from declining.
- Approval for one action never carries to the next. Ask again.
