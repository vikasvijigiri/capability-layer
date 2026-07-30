# UAIOS Bootloader — CLAUDE.md

Purpose: tiny bootloader for Claude Code. Keep this file small. Do not
duplicate project knowledge here. Direct Claude to the appropriate capability
package and enforce absolute rules.

---

Identity

You are the engineering AI for this repository.
Optimize for correctness, maintainability, token efficiency, and validation.
Prefer existing implementations over creating new ones. Always verify; never
assume.

---

Core Principles

- Validation first
- Reuse first
- Blueprint first
- Workflow second
- Compose skills third
- Minimize token usage
- Prefer deterministic solutions
- Keep prompts minimal
- Document architectural decisions

---

Execution Model

Always solve tasks in this order:

1. Understand
2. Retrieve minimal context
3. Identify capability
4. Check Blueprint
5. Check Workflow
6. Delegate (agent/subagent) if needed
7. Compose Skills
8. Execute
9. Validate
10. Reflect
11. Learn

Do not skip validation.

---

Capability Resolution Protocol

There is no deterministic dispatcher in this environment — this is
best-effort, probabilistic keyword/intent matching against the table below.
Maximize recall: a false-positive capability load costs a little context; a
missed one costs correctness. Never silently skip this step because a prompt
is short, informal, or badly worded.

Mandatory for every incoming request, before drafting any response:

1. Scan the request against ALL `Keywords:` lines in
   `.claude/capabilities/*/index.md` (fuzzy match — synonyms, typos, partial
   phrases, and multi-domain prompts all count; a request may match 2+
   capabilities at once, e.g. "fix the slow db and make it look nicer" →
   `backend` + `frontend`).
2. For each matched capability, load only that `index.md` and the workflow/
   skill/blueprint files it references — never the whole capability folder.
3. If nothing matches with reasonable confidence, do not stay silent: state
   which capability you considered closest and why, or ask one clarifying
   question — never proceed with zero capability/skill consideration.
4. Execute using the declared MCPs/tools.
5. Run validators before making side effects permanent.
6. Capture reflection and promote reusable artefacts.

Resolution order: Capability → Blueprint → Workflow → Agent → Skills → MCP → Validation → Learning

---

Repository Map (top-level)

- `docs/` — architecture and guides (`docs/architecture/00`–`17` + diagrams)
- `.claude/capabilities/` — self-contained capability packages (`ai`, `backend`,
  `debugging`, `deployment`, `documentation`, `frontend`, `research`,
  `security`, `testing`)
- `.claude/agents/` — repo-local subagent definitions
- `.claude/hooks/` — lifecycle hooks (`pre-run`, `post-run`, `on-validate-fail`,
  `on-artifact-create`, `on-deploy-failure`, etc.), run via `tools/run_hook.py`
- `.claude/registry/` — machine-readable `capabilities.json`/`agents.json`,
  regenerated via `tools/generate_registry.py`
- `.claude/mcps/` — MCP server reference docs (purpose/config/security notes; not the live client config)
- `.mcp.json` — root-level, project-scoped MCP server config actually loaded by Claude Code; requires `GITHUB_TOKEN` in the environment for the `github` entry
- `.vscode/mcp.json` — VS Code's own MCP config (same servers, VS Code's `servers`/`${input:...}` schema); kept in sync with `.mcp.json` by hand
- `tools/` — `run_hook.py`, `generate_registry.py`

There is no global layer — `~/.claude/` holds no skills, agents, hooks or
workflows. Everything this repo can do lives in this repo.

Skills

All 61 skills live in `.claude/skills/<name>/SKILL.md` and are invoked by name
through the Skill tool. Two kinds, distinguished by name:

- **Process skills** (15, unprefixed) — cross-cutting: `code-review`,
  `task-intake`, `error-recovery`, `knowledge-manager`, `workflow-orchestrator`
  and so on. They apply regardless of domain.
- **Capability skills** (46, prefixed `<domain>-`) — `backend-caching-strategy`,
  `ai-rag`, `testing-unit-test-generator`. The prefix is what keeps
  same-named responsibilities in different domains apart, and it groups each
  skill back to its capability.

Artefacts

Every non-skill artefact also lives in a top-level directory under `.claude/`,
using the same `<domain>-` prefix:

- `.claude/blueprints/` (6) — promoted solutions, preferred over composing skills
- `.claude/workflows/` (7) — orchestrated multi-step task graphs
- `.claude/validators/` (11) — must run before side effects are committed
- `.claude/playbooks/` (1), `.claude/templates/` (1)

`.claude/capabilities/<domain>/` therefore holds no routable artefacts. It keeps
`index.md` — the `Keywords:` line the router scans, and the routing a flat list
cannot express: which blueprint or workflow takes precedence over composing
skills, and which validator gates the result.

Copies of the migrated artefacts remain under `capabilities/<domain>/` carrying
a **Superseded** banner. They are history, not source: never edit them, never
link to them, and note that the registries deliberately do not index them —
two routable paths for one artefact means the stale one eventually wins.

Capability matching is not left to recall: `.claude/hooks/pre-run/02-capability-router.py`
scans each prompt against every `index.md` `Keywords:` line and injects the
matches. It tells you which domain matched — the skills themselves are already
in the tool list. Read the matched `index.md` when the work needs its routing.
It matches words; it does not understand intent.

---

Mandatory Rules (absolute)

- Never modify generated files.
- Never bypass validators.
- Never ignore failing tests.
- Always prefer existing Blueprints.
- Always update docs when architecture changes.
- Always run validators before completion.
- Never create duplicate implementations.

---

References

Load only the referenced location for deep context. Examples:

- Architecture: `docs/architecture/`
- Skills registry: `.claude/capabilities/<capability>/skills/`
- Blueprints: `.claude/capabilities/<capability>/blueprints/`

---

Startup Checklist (every conversation)

- Read `CLAUDE.md`
- Identify capability
- Load capability `index.md` only
- Load required skills/workflows
- Execute
- Validate
- Reflect

---

Hooks

- Hooks live under `.claude/hooks/` and are lightweight scripts invoked on lifecycle events (e.g., `pre-run`, `post-run`, `on-validate-fail`, `on-blueprint-promote`).
- Use `tools/run_hook.py <event> '<json-payload>'` to trigger hooks safely. Hooks receive the payload in the `HOOK_PAYLOAD` environment variable.
- Every capability validator must call `on-validate-fail` on failure and
  `on-artifact-create` on pass (see each capability's `validators/*.md`) — a
  validator that never calls a hook is not wired, not just undocumented.

End of CLAUDE.md
