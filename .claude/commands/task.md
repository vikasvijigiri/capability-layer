---
description: Enter the default flow for named work — the same chain a plain request already enters, made explicit as a typed entry point.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Task

Mode: read-only
Arguments: `$ARGUMENTS` is the work, in the user's own words.

This command itself decides and changes nothing; the chain it enters may
become mutating once inside `task-analysis`'s own procedure.

Not a second router. `.claude/workflow.md` §Entry already routes any named
request to `task-analysis` — this command exists only so the entry point
can be typed explicitly rather than inferred from prose, matching Notion's
6-command shape. Invoke `task-analysis` with `$ARGUMENTS` as the request.

Everything after that point is `task-analysis`'s own procedure: frame,
dispatch for what is missing, plan, Gate 1. This command adds nothing to
that chain and duplicates none of it.
