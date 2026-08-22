---
description: Route a release request to the command that already handles its stage — a local commit, publishing the repository, or checking release readiness.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Release

Mode: mutating
Arguments: `$ARGUMENTS` names the stage — "commit", "publish", or "check".

The routed-to command decides exactly what mutates and holds its own
confirmation; this router adds none of its own beyond the ambiguity case
below.

A router, not a fourth mutating implementation. Resolve the stage and hand
off — never re-derive what the target command already does:

| `$ARGUMENTS` means | Route to |
|---|---|
| commit the current work locally | `/save` |
| create the GitHub repository and open the PR | `/publish` |
| verify a release is actually ready/serving | `/release-check` |
| deploy, or anything past a PR being open | `release-git`'s releasing procedure directly |

Ambiguous or unstated: use `AskUserQuestion` to ask which stage, once,
rather than guessing — this command never bypasses the confirmation the
routed-to command itself requires.
