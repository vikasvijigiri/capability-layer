---
description: Review a GitHub pull request with independent bug, policy, security, and history checks; print findings by default and require confirmation before commenting.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Pull Request Review

Mode: read-only
Arguments: `$ARGUMENTS` identifies the PR; `--comment` requests a proposed comment flow.

Inspect the PR state, diff, repository instructions, and relevant history. Run
independent review lenses, validate each finding before reporting it, and output
only high-confidence findings with file and line evidence. Default output is
local. If `--comment` is supplied, show the complete proposed comment and ask
`AskUserQuestion` before posting anything. Never merge, push, or close
the PR.
