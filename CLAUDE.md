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
   `.claude/routing/capabilities.md` (fuzzy match — synonyms, typos, partial
   phrases, and multi-domain prompts all count; a request may match 2+
   capabilities at once, e.g. "fix the slow db and make it look nicer" →
   `backend` + `frontend`).
2. For each matched capability, invoke the `<domain>-` skills by name. Each
   skill's own `## Routing` section names its mandatory validator and the
   blueprint or workflow that takes precedence — read those, not a folder.
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
- `.claude/routing/capabilities.md` — the nine capabilities (`ai`, `backend`,
  `debugging`, `deployment`, `documentation`, `frontend`, `research`,
  `security`, `testing`): keyword lists and per-domain artefact pointers
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

All 86 skills live in `.claude/skills/<name>/SKILL.md` and are invoked by name
through the Skill tool. Two kinds, distinguished by name:

- **Process skills** (32, unprefixed) — cross-cutting: `code-review`,
  `task-intake`, `error-recovery`, `knowledge-manager`, `workflow-orchestrator`
  and so on. They apply regardless of domain.
- **Capability skills** (54, prefixed `<domain>-`) — `backend-caching-strategy`,
  `ai-rag`, `testing-unit-test-generator`. The prefix is what keeps
  same-named responsibilities in different domains apart, and it groups each
  skill back to its capability.

Each skill declares a `model:` matching its pipeline phase — `opus` up to and
including planning, `sonnet` for implementation, `haiku` for testing and
deployment.

**The skill listing is truncated against a token budget.** At 86 skills roughly
half the descriptions arrive as bare names with no trigger surface, and which
half varies between turns. Never conclude a skill does not exist because it has
no description in the listing; check `.claude/registry/skills.json`. This is why
the keyword router below is load-bearing rather than redundant.

Artefacts

Every non-skill artefact also lives in a top-level directory under `.claude/`,
using the same `<domain>-` prefix:

- `.claude/blueprints/` (6) — promoted solutions, preferred over composing skills
- `.claude/workflows/` (7) — orchestrated multi-step task graphs
- `.claude/validators/` (11) — must run before side effects are committed
- `.claude/playbooks/` (1), `.claude/templates/` (1)

Which validator is mandatory, which blueprint takes precedence and which
workflow orchestrates the multi-step case is stated in each skill's own
`## Routing` section. There is no second copy of that routing anywhere.

`.claude/capabilities/` was removed on 2026-07-31. Its nine `index.md` files
collapsed into `.claude/routing/capabilities.md`, and the superseded artefact
copies it also held were deleted — they were history, and two routable paths for
one artefact means the stale one eventually wins. Recover any of it from commit
`4069f4b` if needed.

Capability matching is not left to recall: `.claude/hooks/pre-run/02-capability-router.py`
scans each prompt against every `Keywords:` line in
`.claude/routing/capabilities.md` and injects the matches. It tells you which
domain matched — then invoke that domain's skills by name. It matches words; it
does not understand intent.

Adding a capability is one edit: a new `## <domain>` section in
`.claude/routing/capabilities.md`. The router hook, `tools/generate_registry.py`
and `tools/resolve_capability.py` all derive the capability list from those
headings, so they cannot disagree about which capabilities exist.

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
- Capability routing: `.claude/routing/capabilities.md`
- Skills: `.claude/skills/<name>/SKILL.md`; index at `.claude/registry/skills.json`
- Blueprints: `.claude/blueprints/<domain>-<name>.md`

---

Startup Checklist (every conversation)

- Read `CLAUDE.md`
- Identify capability (the router hook injects the keyword match for you)
- Invoke the matched skills by name; read their `## Routing` sections
- Execute
- Validate
- Reflect

---

Hooks

- Hooks live under `.claude/hooks/` and are lightweight scripts invoked on lifecycle events (e.g., `pre-run`, `post-run`, `on-validate-fail`, `on-blueprint-promote`).
- Use `tools/run_hook.py <event> '<json-payload>'` to trigger hooks safely. Hooks receive the payload in the `HOOK_PAYLOAD` environment variable.
- Every validator must call `on-validate-fail` on failure and
  `on-artifact-create` on pass (see `.claude/validators/*.md`) — a validator
  that never calls a hook is not wired, not just undocumented.

End of CLAUDE.md
