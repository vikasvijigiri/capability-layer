---
description: Route a review request to the command that already handles its target — a GitHub PR, a saved plan, or a security-sensitive diff.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Review

Mode: read-only
Arguments: `$ARGUMENTS` names what to review — a PR number/URL, a plan
path, or "security" plus a diff description.

This is a router, not a fourth review implementation. Resolve the target
and hand off — never re-derive what the target command already does:

| `$ARGUMENTS` names | Route to |
|---|---|
| a PR number or GitHub URL | `/pr-review` |
| a path under `docs/plans/` or `docs/specs/` | `/plan` |
| "security", or the change touches auth/secrets/deployment | `/security-review` |
| none of the above — an uncommitted diff or the working tree | `code-review` directly |

Ambiguous or unstated: ask which target, once, rather than guessing.
