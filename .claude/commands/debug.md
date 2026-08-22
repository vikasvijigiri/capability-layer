---
description: Find the root cause of a failure before proposing any fix — a typed entry point into the debugging skill's own procedure.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Debug

Mode: read-only
Arguments: `$ARGUMENTS` is the symptom, reproduction steps, or error text.

This command's own read is diagnosis only; `debugging`'s own HARD-GATE
still governs Phase 4's fix. Invoke `debugging` with `$ARGUMENTS`. This command names no procedure of
its own — Phase 1 through Phase 4, the Failure Capture format, and the
Agent Self-Debug Report all live in `debugging/SKILL.md`, and restating
them here would be a second copy of the same rule.
