# W2 — Change / Feature

Notion's shape: Understand → inspect only relevant code → implement →
targeted tests → verify → finish.

**This is the small-work path, specifically — not the full 9-stage
chain.** Read `.claude/workflow.md`'s "Entry" section, "The small-work
path — take it when it applies" subsection. That is the exact mechanism:
frame in one line, do it, run `--scoped` checks, record one line — no
plan, no Gate 1, no separate sweep or review pass.

Keeping this file pointed at the *short* path (not `universal-task.md`'s
full table) is what keeps it a W2-shaped shortcut instead of reinflating
every small change into a twelve-task plan — Notion §20's own named
anti-pattern, "workflow inflation."

Three vetoes force the full chain instead — a control/shared surface, a
sensitive surface, or `tools/scope.py` calling the work `major` once a
diff exists. `.claude/workflow.md`'s "Entry" section names all three.
