---
description: Route a high-risk or trust-boundary change through an independent security review with evidence and residual-risk reporting.
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
