---
name: change-summary
model: opus
description: Produces the summary a human needs for final review - what changed, why, what was deliberately not done, how to verify it and how to reverse it. Use at the end of a unit of work and for "summarise what you did", "what changed", "walk me through it", "write up the changes", "what did you actually do", "give me the summary", "recap this", "ready for review". Prefer this over a file list or commit log - a reviewer needs intent and risk, and a diff shows neither. Do NOT use as a substitute for code-review; this describes the change, it does not judge it.
---

# Change Summary

The last artefact before a human signs off. Written for someone who was not present for the
work.

## Structure

1. **What changed and why** - grouped by intent, not by file. Three files serving one
   purpose is one entry, not three.
2. **What was deliberately not done** - scope consciously cut, problems found and left,
   shortcuts taken. The section reviewers most need and the one most often omitted; an
   unmentioned gap reads as an oversight.
3. **How to verify** - specific commands or steps, with the output that means success. Not
   "run the tests" but the invocation and the expected result.
4. **How to reverse** - the concrete undo, and honestly whether it is clean.
5. **Anything unverified** - claims resting on inspection rather than execution. Say so
   explicitly; a reviewer assuming everything was run is reviewing a fiction.

## Rules

- **Faithful over flattering.** Failures, skipped steps and partial work are reported
  plainly. A summary reading better than the work is worse than no summary.
- **No unverified claims of success.** "Tests pass" requires having run them and quoting
  the result.
- Keep it proportional. A one-line fix does not need five sections.

## Relationship to other skills

Runs after `code-review` and `no-slop-check`, before the final human gate. For an
irreversible action, pair with `approval-brief` - this one says what happened, that one
asks permission for what happens next.
