---
description: Gather outside evidence a decision can rest on — a typed entry point into the research skill's own procedure.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Research

Mode: read-only
Arguments: `$ARGUMENTS` is the question needing outside evidence.

Invoke `research` with `$ARGUMENTS`. This command names no procedure of its
own — the context-ladder, source-evaluation, and `[UNVERIFIED]` discipline
all live in `research/SKILL.md`.
