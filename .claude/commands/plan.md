---
description: Review a saved specification or implementation plan for requirement coverage, architecture, file accuracy, testability, and scope before execution.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Plan

Mode: read-only
Arguments: `$ARGUMENTS` must identify the saved spec or plan path.

Read the complete artifact and the relevant repository files. Apply
`.claude/skills/task-analysis/references/artifact-review.md`; for cross-cutting
boundaries also invoke
`architect`. Return the verdict, findings with file or section
evidence, unresolved assumptions, and the exact next routing decision.

Do not edit the artifact, implement any task, or approve on behalf of the user.
