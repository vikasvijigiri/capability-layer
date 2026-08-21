---
description: Verify release readiness through artifact identity, smoke checks, health signals, observation, rollback readiness, and residual-risk ownership.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Release Check

Mode: read-only
Arguments: `$ARGUMENTS` identifies the release version and environment.

Run only approved non-destructive release checks. Confirm the exact artifact,
environment, smoke result, health signal, observation window, rollback path, and
risk owner. Dispatch `reviewer` (mode: release) when available. Return PASS, FAIL, or
BLOCKED with timestamps and quoted evidence.

Do not deploy, rollback, mutate production, or declare success without health
evidence.
