---
name: approval-brief
model: opus
description: Packages a decision a human is about to approve - what changes, what it costs, what breaks if it is wrong, and how to undo it - so approval is informed rather than reflexive. Use before any push, merge, deploy, release, migration, deletion or spend, and for "is this ok to do", "can I go ahead", "do you approve", "should I proceed", "about to ship this", "ready to push", "shall I run it". Prefer this over a bare yes/no question - approval given without blast radius and a rollback path is not consent, it is a guess. Do NOT use for reversible local actions that need no gate.
effort: high
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

## The gate - required, not optional

Print the five lines as plain text, then call `AskUserQuestion`. Prose ending in "shall
I proceed?" is not a gate: it reads as narration, it is easy to answer past, and it
leaves no record of what was actually agreed to.

Three options, in this order:

- **Approve** - the label names the concrete irreversible action, not the word "approve".
  "Push 14 commits to origin/main" is a decision; "Approve" is a reflex. The description
  restates the undo path from line 4 so the last thing read before consenting is the cost
  of being wrong.
- **Cancel** - nothing runs, and the description says what state is left behind (usually
  "work stays local and uncommitted", which is not the same as "nothing happened").
- **Change something first** - for the answer that is neither yes nor no: run the tests
  again, narrow the scope, split the push. Name the most likely one.

`AskUserQuestion` appends **Other** with free-text input, which is where a condition the
options do not cover gets expressed. Never add a fourth option that is a variation on
approval - filler options are a recommendation in disguise.

Never pre-tick, never mark the destructive option "(Recommended)" unless you would defend
it unprompted, and never fold two irreversible actions into one question.

If the gate is declined, say what you are doing instead in one line and stop. Do not
re-ask the same question with softer wording.

## Rules

- **Never bundle.** One approval per irreversible action. A single yes covering a push and
  a deploy is not informed consent for either.
- **Lead with the irreversible part.** If any component cannot be undone, that is the
  headline, not a footnote.
- **State unknowns.** "I have not verified whether X has consumers" belongs in the brief,
  not omitted because it weakens the ask.
- Give the recommendation, then the option to decline and what follows from declining.
- Approval for one action never carries to the next. Ask again.
