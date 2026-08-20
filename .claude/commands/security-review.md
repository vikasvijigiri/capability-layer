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

Invoke `code-review` with its security lens
(`.claude/skills/code-review/references/security-review.md`) and, when subagents
are available, dispatch
`security-reviewer`. Cover authentication, authorization, secrets, external
input, data exposure, dependencies, hooks, deployment, and unsafe agent
actions. Return prioritized findings, evidence, remediation, and residual risk.

Do not exploit live systems, retrieve real secrets, edit files, or sign off.
