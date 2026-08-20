---
description: Create a durable session handoff from the repository's actual branch, task, verification, pending, and next-step state.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Handoff

Mode: read-only
Arguments: optional focus hint in `$ARGUMENTS`.

Read `git status --porcelain=v1 -uall`, `TASK.md`, `HANDOFF.md`, `LOG.md`, and
`ISSUES.md` if present. Report current work, completed evidence, blockers,
open questions, exact changed areas, and the next concrete action. Do not edit
handoff documents; this command reports drift for `knowledge-manager` to record.
