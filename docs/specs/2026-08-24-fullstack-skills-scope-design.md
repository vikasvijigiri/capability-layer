# Should this repo add "full-stack engineer" skills (backend/frontend, gap ID, design fetch, Grafana/API-manager monitoring, backend diagnosis)?

**Asked because:** user wants their agent to "diagnose, design, maintain, develop and
scale" backend and frontend work at a "world-class" level, framed as needing new
backend/frontend/fullstack skills, a gap-identification skill, design-creation skills,
and a backend-monitoring skill using Grafana and an "API manager." Asked to check GitHub.

**Verdict:** Do not create new top-level skills. Every named lifecycle verb
(diagnose/design/maintain/develop/scale) already has an owning skill in this repo's
generic SDLC chain (`AGENTS.md`: brief → design → plan → implement → verify → clean →
review → deliver → release → record). The only real, narrow gap is one MCP wiring
(Grafana) analogous to the Figma wiring done in PR #39/#40 — and even that has an open
question this repo cannot answer for itself, because **it has no application code**
(`CLAUDE.md`: "There is no application code here"; `../physrun/` is the actual product).

## Findings

### (a) The five verbs already map to five existing, generic skills

| Verb | Owner | Evidence |
|---|---|---|
| Diagnose | `debugging` | `SKILL.md` description: "Find the root cause of a failure... whenever something fails unexpectedly" — no stack qualifier |
| Design | `architecture` (design-contract mode) | `references/design-contract.md`, extended with iOS/Android + Figma MCP in PR #39/#40 |
| Develop | `implementation` | Test-first, builds from an approved plan |
| Maintain | `refactoring` + `documentation` | Sweeps dead code/slop repo-wide; records decisions and durable docs |
| Scale | `release-git` → `references/observability-sre.md` | Covers SLIs/SLOs, metrics, dashboards, alerts, capacity/saturation, runbooks — generic, tool-agnostic |

None of these five is stack-specific by construction. Confidence: **high** — read
directly from each `SKILL.md`/reference this session.

### (b) Real "backend-engineer"/"frontend-engineer" skills in public prior art are either project-bound or a different architecture entirely

**Finding 1** — `majiayu000/claude-skill-registry`'s `frontend-engineer` skill is bound
to one real codebase's actual stack ("Lighthouse Journey Timeline... React patterns,
TypeScript, TanStack Query, Zustand"). It only works because a concrete stack exists to
write against. This repo has none — writing an equivalent skill here would mean
inventing a stack, which is exactly the kind of guess `CLAUDE.md`/`AGENTS.md` forbid.

**Finding 2** — `RISHI168/ai-product-lifecycle` runs a *role-persona agent swarm*
(BACKEND ENGINEER AGENT, FRONTEND ENGINEER AGENT, DATABASE ARCHITECT AGENT, DEVOPS INFRA
AGENT, CHIEF ORCHESTRATION AGENT, ...) — a structurally different pattern from this
repo's procedure-owning skills (one skill per SDLC verb, not per job title). Adopting it
would mean rebuilding the skill system around a different axis, not extending it.

**Finding 3** — no official Anthropic backend/frontend skill exists.
`org:anthropics topic:skills` returns only `claude-plugins-official`, a directory of
third-party plugins, not an authored skill itself (same finding as the prior UI/UX
research cycle, `docs/research/2026-08-23-ui-ux-skill-prior-art.md`).

**Means here:** neither prior-art shape fits without either (a) inventing a stack this
repo doesn't have, or (b) restructuring the whole skill system around personas — both
out of proportion to the actual gap.

### (c) Monitoring: Grafana MCP is real; "API manager" has no single answer

**Finding 4** — `grafana/mcp-grafana` is the official Grafana MCP server (3,381 stars,
updated within the last day). Legitimate to wire in, same shape as the Figma precedent:
add to `.mcp.json`, add its tools to `release-git`'s `allowed-tools`, add a short
Grafana-specific subsection to `observability-sre.md`.

**Finding 5** — "API manager" has no single MCP the way Figma covers all three design
platforms. Candidates found: `Kong/mcp-konnect` (official, but **archived**), Azure API
Management's MCP gateway samples (Azure-specific), and several generic MCP-to-REST
gateway bridges (`AmoyLab/Unla`, `acehoss/mcp-gateway` — these gate *access to* MCP
servers, they don't manage a product's own API surface). None is a generic "the" answer
the way Grafana is for dashboards/alerts.

**Means here:** Grafana is a safe, narrow addition. API-management tooling depends on
which product a downstream project actually uses (Kong vs. Apigee vs. Azure APIM vs.
none) — not decidable from this repo.

### (d) "Identify gaps" already has a home

`repository-navigation` maps "what already works and what was left unfinished."
`task-analysis` Stage A1 requires verifying claims (confirmed/disputed/unverifiable)
before framing any work. `refactoring` sweeps for stale/dangling/unfinished work
repo-wide. A dedicated "gap-identification" skill would duplicate parts of all three
without a concrete case where they fall short.

## Decision

**Extend, narrowly, in two places — no new skill:**

1. Add `grafana` to `.mcp.json` (mirroring the `figma` entry's shape) and add its
   read tools to `release-git`'s `allowed-tools`; add a "Grafana" subsection to
   `references/observability-sre.md` naming which of its existing generic concepts
   (dashboards, alerts, SLOs) map to Grafana panels/alert rules specifically.
2. Leave "API manager" unwired. `[NEEDS CLARIFICATION: does any real downstream
   project (e.g. physrun) already run an API gateway product — Kong, Apigee, Azure
   APIM, or none? Wiring a specific gateway MCP with no live target to point it at is
   inert, and the "API manager" prior art has no single generic answer the way Figma
   does for design.]`

**Rejected:**
- New `backend`/`frontend`/`fullstack` top-level skills — duplicates
  `debugging`/`architecture`/`implementation`/`refactoring`/`release-git`, the exact
  "Never: create a duplicate implementation of something that already exists" rule,
  and would require inventing a stack this repo doesn't have.
- A `gap-identification` skill — already covered by
  `repository-navigation` + `task-analysis` Stage A1 + `refactoring`; no concrete
  failure case surfaced where those three fall short.
- Persona/role-based agent restructuring (the `ai-product-lifecycle` shape) — a
  different architecture than this repo's procedure-per-verb skills; not asked for and
  a much larger change than the actual gap warrants.

## Sources

- This repo: `.claude/skills/{debugging,architecture,implementation,refactoring,
  release-git,repository-navigation,task-analysis}/SKILL.md`,
  `release-git/references/observability-sre.md`, `.mcp.json`,
  `docs/research/2026-08-23-ui-ux-skill-prior-art.md` — read directly.
- `mcp__github__search_repositories`: `grafana mcp server topic:mcp-server`,
  `org:grafana mcp`, `api gateway mcp server kong OR apigee OR "api management"`,
  `org:anthropics topic:skills`.
- `mcp__github__search_code`: `"backend engineer" SKILL.md claude in:path`,
  `"frontend-engineer" SKILL.md description in:file`, `"gap analysis" SKILL.md
  description:`.
- `RISHI168/ai-product-lifecycle`, `CLAUDE SWE AGENTS/` directory listing —
  structure only, bodies not read in full (sufficient to answer "does it exist
  and what shape is it").
