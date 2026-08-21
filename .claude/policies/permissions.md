# Permissions policy

Part of Notion §24's "Policy Gate" — what may act, and within what scope.

**Tool/hook permission boundary**: `.claude/settings.json` is the live
registration; every `PreToolUse`/`PostToolUse` entry there is the actual
enforcement, not this file. `guide/how_to_create_hooks.md` documents the
contract.

**Per-agent write scope**: `.claude/hooks/pre-edit/02-agent-scope-guard.py`
denies a write outside a dispatched agent's declared `allowed-paths:` (a
static glob, or `dispatched` for a per-round scope set via
`UAIOS_AGENT_SCOPE`). See that hook's own docstring for the dormancy note
on `UAIOS_AGENT_NAME` — the guard's static-scope half is enforced on
every host; the per-round half needs a host that sets the env var, which
Claude Code does not.

Nothing here restates either mechanism; both are code, and code is the
source of truth.
