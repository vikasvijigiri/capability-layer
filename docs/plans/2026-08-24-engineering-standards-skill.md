# Add an `engineering-standards` skill: backend/frontend/fullstack practice, for any repo

**Source brief:** `docs/specs/2026-08-24-fullstack-skills-scope-design.md`
(verdict superseded this turn — see Research below), plus the user's
direct follow-up asking for backend/frontend/fullstack develop/diagnose/
maintain/scale/monitor/repair coverage and two parallel-capable subagents.

**Goal:** Give this layer a portable backend/frontend/fullstack standards
skill, plus two subagents that can implement backend and frontend tasks in
parallel, grounded in current industry practice, usable in any repo this
layer is placed in.

**Constraints:** No new lifecycle stage or gate; must fit the existing
off-chain-capability slot and the existing `implementer`/`parallel_groups.py`
scheduling mechanism; no stack assumed (this repo has no application code);
must pass `new_skill_check.py`, `test_agent_standards.py`,
`test_process_router.py`, `test_referenced_paths.py`.

**Input:** This session's research (below) plus the five existing files this
plan cross-references: `architecture/SKILL.md`, `release-git/SKILL.md` and
its `references/observability-sre.md`, `architecture/references/
design-contract.md`, `.claude/agents/implementer.md`.

**Output:** `engineering-standards/SKILL.md` + 2 reference files; a
`workflow.md` off-chain row; one-line consult pointers in 4 skills;
`backend-engineer.md` + `frontend-engineer.md` agents; one routing-rule
edit in `implementation/SKILL.md`.

**Done Checks:** `python tools/new_skill_check.py engineering-standards`
exits 0; `python tools/new_skill_check.py --all` exits 0; `python
tools/test_agent_standards.py` exits 0; `python tools/test_process_router.py`
exits 0; `python tools/test_referenced_paths.py` exits 0; `python
tools/run_checks.py --tier all --require-test` exits 0.

**Out of Scope:** Live Grafana MCP wiring, deeper per-language reference
modules, an API-gateway MCP — all named as follow-on work below, none
built in this plan.

**Context:** The user rejected the first version of this plan (Grafana-only)
as too literal a reading — Grafana was one example of "monitor," not the
whole ask. They want a real backend/frontend/fullstack capability that can
develop, diagnose, maintain, scale, monitor, and repair, following
world-class industry practice, and that works "when placed in any repo" —
not bound to this repo (which has no application code of its own). They
asked for research on separate-vs-integrated skill shape before building.

**Research done this turn (supersedes the "no new skill" verdict in
`docs/specs/2026-08-24-fullstack-skills-scope-design.md`):**
- `siviter-xyz/dot-agent`'s `backend-engineer` and `frontend-engineer`
  skills (mirrored into `skills.sh`, read in full) are the one real example
  of skills — not subagents — genuinely shaped like the ask: a hub `SKILL.md`
  with a technology **decision matrix** (not one hardcoded stack), a
  best-practices checklist (OWASP Top 10, 70-20-10 testing pyramid,
  blue-green deploys, **"Prometheus/Grafana monitoring," OpenTelemetry**),
  and 8-9 `references/*.md` files (api-design, security, authentication,
  performance, architecture, testing, devops, technologies). This is
  portable by construction — it teaches *how to choose and apply* practice,
  not one project's actual stack — which resolves my earlier objection
  (that a stack-specific skill needs a stack to write against). It scored
  only ⭐⭐ in a third-party curated rating, most likely because it is pure
  reference content with no gates or verification — this repo's own
  `debugging`/`architecture`/`implementation` already own that discipline,
  so the new skill's job is to *ground* those, not duplicate their gates.
- Every other real hit (`RISHI168/ai-product-lifecycle`, `Team-Commonly/
  commonly`, `AtifAssari/MCP-Skills-Universe`'s catalog) uses
  backend-engineer/frontend-engineer as **subagent personas** in a
  multi-agent team, not as skills — a different mechanism (this repo's
  `.claude/agents/*.md`) from what's needed here: reference/standards
  content consulted by existing procedure skills, not a new dispatched role.
- `AThevon/genjutsu`'s `cast` skill (read in the prior research cycle, still
  the strongest precedent) handles Web, Android, and iOS from **one** skill
  via a `SCAN` phase that greps the target repo's actual config files
  (`package.json`, Gradle, `Package.swift`) and loads only the matching
  module. **Decision: integrated, not separate** — one `engineering-standards`
  skill with a SCAN phase and backend/frontend reference modules, not two
  top-level skills. This matches genjutsu's strongest precedent, this repo's
  own "hub + `references/*.md` loaded per task" convention (already used by
  `architecture`, `release-git`), and `CLAUDE.md`'s per-turn description-cost
  discipline — one trigger surface instead of two overlapping ones.

**Slug:** engineering-standards-skill

**Risk:** High — forced by: control-surface (`tools/scope.py --plan
docs/plans/2026-08-24-engineering-standards-skill.md`; this plan touches
`.claude/workflow.md`, four skills' `SKILL.md`, and two new
`.claude/agents/*.md` files — all control-surface paths by
`.claude/workflow.md`'s own rubric). No credentials, no CI; the tier is
about blast radius within the agent layer, not runtime risk.

**Blast radius:** New skill directory only, plus one row each in
`workflow.md`'s off-chain table and a one-line pointer added to
`architecture`, `implementation`, `debugging`, and `release-git`'s bodies.
No behavior change to those four skills' own procedures or gates.

**Rollback:** Delete the new skill directory, revert the workflow.md row and
the four one-line pointers. Nothing else depends on this mid-flight.

**Architecture:** One new off-chain capability skill (`.claude/workflow.md`'s
"Off-chain capabilities" table — same slot as `research`/`debugging`, not a
10th chain stage, so no Gate, no predecessor requirement). Structure:

- `SKILL.md` — frontmatter (`sonnet`/`high`, matching `documentation`'s and
  `security`'s "apply known standards" profile rather than `architecture`'s
  judgment-heavy `opus`), a **SCAN** phase (grep the target repo for
  `package.json`/`requirements.txt`/`pyproject.toml`/`go.mod`/`Cargo.toml`/
  `Gemfile`/`pom.xml` and known framework deps inside `package.json`), a
  Reference Navigation table, and routing: consulted *in place* by
  `architecture` (design), `implementation` (build), `debugging` (diagnose),
  and `release-git` (scale/monitor) — never a chain stage of its own, so it
  hands off to `task-analysis` only when the request implies new work with
  no plan yet, and to `debugging` when it implies an existing failure.
- `references/backend-standards.md` — API design (REST/GraphQL/gRPC),
  auth (OAuth2.1/JWT), data/caching, OWASP Top 10 security checklist,
  testing pyramid, deployment patterns (blue-green/canary), and an
  Observability section naming Prometheus + Grafana as the standard pairing
  (citing `grafana/mcp-grafana`, the real official MCP found this session,
  as the concrete tool if/when a target has one — wiring it live is
  follow-on work, not this plan; see Out of scope).
- `references/frontend-standards.md` — component architecture, state
  management, data fetching, rendering performance, bundle size, and
  frontend testing strategy. Deliberately **not** re-covering visual
  design/tokens/motion/a11y-floor — `architecture/references/design-contract.md`
  already owns that; this file is code-level engineering, that one is the
  visual contract, and each cites the other rather than duplicating.

**Tech stack and constraints:** No stack is assumed — the SCAN phase reads
whatever the target repo actually has. Reference content stays
decision-matrix/checklist style (mirroring `dot-agent`'s real structure and
this repo's own terse voice), not prose essays. `new_skill_check.py`'s
required checks govern the frontmatter shape: `name` matches the directory,
`description` ≤700 chars with a "Do NOT use" clause, `model` ∈
{opus,sonnet,haiku}, `effort` ∈ {low,medium,high}, frontmatter ≤1300 chars
total, and a row in `workflow.md` (off-chain table, no numbered stage, so no
predecessor/"Workflow stage N" requirement applies).

**Out of scope (named, not silently dropped — "can we have more?" is yes,
here's the queue):**
- Wiring the `grafana/mcp-grafana` MCP live into `release-git` — fully
  researched this session (8 real read-only tool names confirmed, config
  shape confirmed against `.mcp.json`/`.vscode/mcp.json`/`.env.example`'s
  existing patterns) and ready to execute as its own small follow-on plan;
  not bundled here so this plan stays one reviewable deliverable.
- Deeper per-language backend modules (Python/Go/Node/Rust specifics) and
  per-framework frontend modules (React/Vue/Svelte specifics) beyond the
  first general-purpose reference pair above.
- An API-gateway/API-manager MCP — no generic answer exists yet (Kong's is
  archived); deferred pending a real downstream target, per the original spec.

**Also in this plan — two new subagents, per the user's follow-up.**
`.claude/agents/implementer.md` is today's only task-executing subagent,
domain-agnostic, dispatched by `implementation` once
`tools/parallel_groups.py` proves a round's tasks touch disjoint files. Real
prior art for "backend-engineer"/"frontend-engineer" (`RISHI168/
ai-product-lifecycle`, `Team-Commonly/commonly`, `AtifAssari/
MCP-Skills-Universe`'s catalog) uses them as exactly this — subagent
personas, not skills. Adding `backend-engineer` and `frontend-engineer` as
thin specializations of `implementer` (same worktree/status-vocabulary/
never-commit contract, `tools/test_agent_standards.py`'s required shape,
plus one instruction to read the matching `engineering-standards` reference
file before starting) lets a round with one backend task and one disjoint
frontend task dispatch both **in parallel, in one message**, each grounded
in its own domain's standards — the existing scheduler already proves
disjointness; nothing new to compute.

## File map

| File | Change | Owns after |
|---|---|---|
| `.claude/skills/engineering-standards/SKILL.md` | Create | Hub: SCAN phase, reference navigation, routing |
| `.claude/skills/engineering-standards/references/backend-standards.md` | Create | Backend decision matrix, security, testing, deployment, observability |
| `.claude/skills/engineering-standards/references/frontend-standards.md` | Create | Frontend code-level engineering (state, performance, testing) |
| `.claude/workflow.md` | Modify — add one row to "Off-chain capabilities" table | Registers the skill so `new_skill_check.py` and `test_process_router.py` can reach it |
| `.claude/skills/architecture/SKILL.md` | Modify — one line in Routing pointing to `engineering-standards` for backend/frontend implementation-standard grounding | Cross-reference only, no procedural change |
| `.claude/skills/implementation/SKILL.md` | Modify — one line in Routing, same shape | Cross-reference only |
| `.claude/skills/debugging/SKILL.md` | Modify — one line in Routing, same shape | Cross-reference only |
| `.claude/skills/release-git/SKILL.md` | Modify — one line in Routing, same shape (scale/monitor) | Cross-reference only |
| `.claude/agents/backend-engineer.md` | Create | Backend-task subagent, grounded in `backend-standards.md` |
| `.claude/agents/frontend-engineer.md` | Create | Frontend-task subagent, grounded in `frontend-standards.md` |
| `.claude/skills/implementation/SKILL.md:149` | Modify — the `implementer` dispatch line gains a one-line routing rule | Which of the three task-agents a round dispatches per task |

## Progress
- [ ] Task 1 — Write `engineering-standards/SKILL.md` (hub, SCAN phase, routing)
- [ ] Task 2 — Write `references/backend-standards.md`
- [ ] Task 3 — Write `references/frontend-standards.md`
- [ ] Task 4 — Register in `workflow.md` and add consult pointers in 4 skills; verify reachability
- [ ] Task 5 — Create `backend-engineer` and `frontend-engineer` subagents
- [ ] Task 6 — Wire the parallel-dispatch routing rule in `implementation`

## Tasks

### Task 1: Write the `engineering-standards` hub skill
**Purpose:** a single, stack-detecting entry point for backend/frontend/
fullstack standards, reachable both directly (user asks) and by consultation
from `architecture`/`implementation`/`debugging`/`release-git`.
**Files:**
- Create: `.claude/skills/engineering-standards/SKILL.md` — hub skill:
  frontmatter, SCAN phase, reference navigation, routing (exact content
  below, in Implementation notes)
**Dependencies:** none
**Implementation notes:** Frontmatter: name engineering-standards,
description covering triggers "make this backend world class", "is this
scalable", "audit our API design", "review our frontend architecture",
"what's best practice for X", "harden this service", "improve
observability", "diagnose this backend/frontend issue", plus a "Do NOT use"
clause for single-fact lookups (goes to research instead) and for replacing
task-analysis's plan or debugging's root-cause procedure; model sonnet,
effort high, disable-model-invocation false, allowed-tools Read Grep Glob
Bash. Body: a SCAN phase (bash/grep commands detecting a Node manifest plus
known framework dependencies, a Python manifest, a Go module file, a Rust
manifest, a Ruby gemfile, a JVM build file — name each file pattern in prose,
not as a bulleted Files-style entry, so the plan scheduler does not read
illustrative filenames as declared paths); an explicit note that this
repository itself has no application code so SCAN correctly finds nothing
here — the skill exists to run against whatever repo it's placed in; a
Reference Navigation table to the two files below; a Routing section naming
the four consulting skills and the two possible handoffs (task-analysis for
new work, debugging for an existing failure); Success criteria. Mirror
`architecture/SKILL.md`'s frontmatter shape and `release-git/SKILL.md`'s
Routing-section shape exactly — same files this plan already read in full
this session, cite `file:line` for the pattern rather than re-deriving it.
**Rollback:** delete the directory.
**Preconditions:** none.
**Verification:**
- Run: `python tools/new_skill_check.py engineering-standards`
- Expect: every REQUIRED row PASS (directory/frontmatter/name-match/
  description+"do not use"/length caps/model/effort); the workflow.md row
  and reachability checks will still FAIL until Task 4 — expected at this
  point, not a defect.
**Done when:** `new_skill_check.py`'s frontmatter-level checks all pass.

### Task 2: Write `references/backend-standards.md`
**Purpose:** the backend decision matrix and checklist content, in this
repo's terse/checklist voice, not a prose essay.
**Files:**
- Create: `.claude/skills/engineering-standards/references/backend-standards.md`
  — sections: Technology decision matrix (language/framework/DB/API-style by
  need, mirroring `dot-agent`'s real matrix rather than inventing one); API
  design (REST/GraphQL/gRPC — when each fits); Auth (OAuth2.1+PKCE, JWT,
  session vs. token); Security (OWASP Top 10 checklist: parameterized
  queries, Argon2id, input validation, rate limiting, security headers);
  Testing (unit/integration/E2E pyramid with rough proportions); Deployment
  (blue-green/canary, feature flags, health checks); Observability (SLIs/SLOs
  — cross-reference `release-git/references/observability-sre.md` rather
  than duplicate it — naming Prometheus+Grafana as the standard pairing and
  `grafana/mcp-grafana` as the real MCP to wire in when a target exists).
**Dependencies:** 1 (the hub's Reference Navigation table must name this file)
**Implementation notes:** cross-reference `observability-sre.md` by path,
do not restate its readiness sequence.
**Rollback:** delete the file.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: passes (every path this file and the hub reference resolves)
**Done when:** the file exists, is referenced from the hub, and
`test_referenced_paths.py` is clean.

### Task 3: Write `references/frontend-standards.md`
**Purpose:** code-level frontend engineering standards, deliberately
distinct from `design-contract.md`'s visual contract.
**Files:**
- Create: `.claude/skills/engineering-standards/references/frontend-standards.md`
  — sections: Component architecture (composition, boundaries, colocation);
  State management (local vs. global, when a store is warranted); Data
  fetching (caching, request waterfalls, optimistic updates); Rendering
  performance (re-render causes, memoization, bundle size, code-splitting);
  Testing (component/integration/E2E proportions, what to mock); an explicit
  note that visual/token/motion/accessibility-floor content lives in
  `architecture/references/design-contract.md`, cross-referenced by path,
  not duplicated.
**Dependencies:** 1
**Implementation notes:** same cross-reference discipline as Task 2.
**Rollback:** delete the file.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: passes
**Done when:** the file exists, is referenced from the hub, and
`test_referenced_paths.py` is clean.

### Task 4: Register the skill and add consult pointers
**Purpose:** make the skill reachable (`new_skill_check.py`'s workflow-row
requirement) and discoverable from the four skills that should consult it.
**Files:**
- Modify: `.claude/workflow.md` — add one row to the "Off-chain capabilities"
  table: `| Ground engineering practice | engineering-standards | backend,
  frontend, and fullstack implementation, diagnosis, and scaling, grounded
  in current industry practice for whatever stack the target repo actually
  uses |`
- Modify: `.claude/skills/architecture/SKILL.md` — one line in its Routing
  section: consult `engineering-standards` for backend/frontend
  implementation-standard grounding once the design direction is chosen
- Modify: `.claude/skills/implementation/SKILL.md` — one line, same shape,
  for build-time grounding
- Modify: `.claude/skills/debugging/SKILL.md` — one line, same shape, for
  diagnosis-time grounding
- Modify: `.claude/skills/release-git/SKILL.md` — one line, same shape, for
  scale/monitor-time grounding, cross-referencing `observability-sre.md`
**Dependencies:** 1, 2, 3
**Implementation notes:** one line each — do not restructure any of the four
existing skills' procedures; this is a pointer, not a rewrite.
**Rollback:** revert the five file diffs.
**Preconditions:** Tasks 1-3 complete.
**Verification:**
- Run: `python tools/new_skill_check.py engineering-standards`
- Expect: `All <N> required check(s) pass`
- Run: `python tools/new_skill_check.py --all`
- Expect: no new failures on any existing skill (the four one-line edits
  don't change their own frontmatter or chain position)
- Run: `python tools/test_process_router.py`
- Expect: passes
**Done when:** `engineering-standards` is fully reachable per
`new_skill_check.py`, and all four consulting skills carry the pointer.

### Task 5: Create the `backend-engineer` and `frontend-engineer` subagents
**Purpose:** two task-executing subagents, procedurally identical to
`implementer` (same contract, same safety rails) but each grounded in one
domain's `engineering-standards` reference, so a round with disjoint backend
and frontend tasks can dispatch both at once, each held to its own
standards.
**Files:**
- Create: `.claude/agents/backend-engineer.md` — frontmatter mirroring
  `.claude/agents/implementer.md:1-8` exactly (`tools: Read, Write, Edit,
  Grep, Glob, Bash, PowerShell`, `model: sonnet`, `isolation: worktree`,
  `allowed-paths: dispatched`), `description` ≤500 chars ending in a "Do NOT
  use for frontend files..." clause per `test_agent_standards.py`; body:
  `implementer.md`'s exact contract (the four statuses, worktree/base-check
  method, "never commit," "stay in declared files" rules — copied, not
  paraphrased, since it is a proven procedure) with one new opening
  paragraph: "Before starting, read
  `.claude/skills/engineering-standards/references/backend-standards.md` and
  hold your implementation to its checklist — API design, auth, OWASP
  security, testing pyramid, deployment — in addition to the task brief."
- Create: `.claude/agents/frontend-engineer.md` — same shape, pointing at
  `frontend-standards.md`, "Do NOT use for backend files."
**Dependencies:** 2, 3 (the two reference files must exist before an agent
is told to read them)
**Implementation notes:** do not invent a different procedural contract —
any divergence from `implementer`'s tested worktree/status/rules shape is a
new failure mode with no measurement behind it. The only real difference is
the one-paragraph domain-grounding instruction and the description's file
scope.
**Rollback:** delete both files.
**Preconditions:** Tasks 2-3 complete.
**Verification:**
- Run: `python tools/test_agent_standards.py`
- Expect: `OK: <N> agents satisfy safety and portability invariants` (N
  includes the 2 new agents; no `mcp__` tools, both descriptions carry "Do
  NOT use", both declare `allowed-paths` since both grant Write/Edit)
**Done when:** both agent files exist and `test_agent_standards.py` passes
clean with them included.

### Task 6: Wire the parallel-dispatch routing rule into `implementation`
**Purpose:** tell the dispatcher when to pick `backend-engineer`/
`frontend-engineer` over the generic `implementer`, using the existing
scheduler — no new scheduling logic.
**Files:**
- Modify: `.claude/skills/implementation/SKILL.md:149` — extend "Dispatch
  one **`implementer`** per task in the round..." to: for each task in the
  round, dispatch `backend-engineer` if its declared `Files:` are backend
  paths (server/api/backend/service directories, or a backend language/
  framework file extension), `frontend-engineer` if they are frontend paths
  (client/frontend/ui/components directories, or `.tsx`/`.jsx`/`.vue`
  files), otherwise `implementer` — still one dispatch per task, all in the
  same message, each pointed at its pre-created worktree path exactly as
  today.
**Dependencies:** 5
**Implementation notes:** a heuristic on the task's own declared `Files:`
list, read by the dispatcher before sending the round's message — no change
to `tools/parallel_groups.py` itself, which still only proves disjointness
and rounds, not agent choice.
**Rollback:** revert the one edit; every round falls back to `implementer`
for everything, exactly today's behavior.
**Preconditions:** Task 5 complete.
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: passes (routing text change only, no frontmatter/chain change)
**Done when:** the routing rule is stated in `implementation/SKILL.md` and
names both new agents by their exact file names.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — N/A for this task class (new reference/skill content,
      no runtime behavior); `new_skill_check.py`/`test_referenced_paths.py`/
      `test_process_router.py` are the tests, run after each task
- [x] III Smallest change — one skill, two reference files, four one-line
      pointers, two agent files that reuse `implementer`'s proven contract
      rather than inventing a new one, one routing-rule edit; deeper
      stack-specific modules and the Grafana wiring are named follow-on
      work, not bundled in
- [x] IV Reversibility — every change is a new file or a one-line addition;
      rollback is delete/revert
- [x] V No silent degradation — no check is skipped
- [x] VI Mechanism — `new_skill_check.py` is the enforced reachability
      contract this plan is built to satisfy
- [x] VII Secrets — none touched in this plan (Grafana credentials are
      explicitly deferred to the follow-on plan)

## Complexity tracking
(none — all seven articles ticked)

## Final verification (all tasks)
- `python tools/run_checks.py --tier all --require-test` exits 0
- `python tools/new_skill_check.py --all` — 0 required-check failures
- `python tools/test_agent_standards.py` — `OK` including both new agents
- `python tools/test_process_router.py` — passes

## Approved
