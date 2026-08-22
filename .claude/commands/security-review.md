---
description: Route a high-risk or trust-boundary change through an independent security review with evidence and residual-risk reporting.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Security Review

Mode: read-only
Arguments: `$ARGUMENTS` identifies the changed area, threat boundary, or saved artifact.

A typed entry point into the `security` skill's own procedure, not a second
copy of it. Invoke `security` with `$ARGUMENTS`. This command names no
procedure of its own — the deterministic gate, the security lens, the
licence/SBOM check, and the reporting contract all live in
`.claude/skills/security/SKILL.md`, and restating them here would be a
second copy of the same rule.
