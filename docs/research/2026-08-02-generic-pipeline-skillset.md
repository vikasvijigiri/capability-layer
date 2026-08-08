# What skill set makes a pipeline that can solve a problem in any domain?

**Asked because:** the capability layer is being built stage by stage against
`docs/workflow.md`, and the target is a pipeline generic enough for a product
build, a research programme, or anything else — at minimal tokens and time.
**Verdict:** the answer is **not more skills**. Every serious repo converges on
**~10-14 domain-free process skills plus a pluggable knowledge-pack layer**. In
the largest research library found, 94 of 98 skills are domain knowledge and
only 4 are process. We have 7 of the ~11 process skills; the four gaps are
**execute, validate, deliver, and a skill for writing skills**. The second,
larger finding: our pipeline shape is linear-only, and open-ended domains
(research, discovery) need a **two-loop** shape the current `workflow.md` cannot
express.

## Findings

### 1. The process layer is small, fixed, and domain-free. HIGH.

Four independently built families, one shape:

| Stage | ours | superpowers (14 skills) | spec-kit (10 commands) | BMAD (core + modules) | Orchestra autoresearch |
|---|---|---|---|---|---|
| Frame | `task-brief` | — | `specify`, `clarify` | `bmad-product-brief` | bootstrap: scope question |
| Ideate | `brainstormer` | `brainstorming` | — | `bmad-brainstorming`, `bmad-forge-idea` | `21-research-ideation` |
| Research | `research` | — | — | `bmad-deep-recon` | literature survey |
| Design | `brainstormer` | — | `plan` | `bmad-architecture`, `bmad-spec` | hypotheses + protocol |
| Plan | `writing-plans` | `writing-plans` | `tasks` | `bmad-create-epics-and-stories` | — |
| **Execute** | **—** | `executing-plans`, `subagent-driven-development`, `test-driven-development` | `implement` | `bmad-build`, `bmad-build-auto` | inner loop |
| **Validate** | **—** | `verification-before-completion` | `analyze`, `checklist` | `bmad-check-implementation-readiness` | sanity check + eval lock |
| Review | `code-review` | `requesting-`/`receiving-code-review` | — | `bmad-code-review`, `bmad-review` | — |
| Debug | `systematic-debugging` | `systematic-debugging` | — | `bmad-correct-course` | "stuck" protocol |
| Record | `knowledge-manager` | — | — | `bmad-retrospective` | `findings.md` outer loop |
| **Deliver** | **—** | `finishing-a-development-branch` | `converge` | `ship` module | conclude → paper |
| **Meta** | **—** | `writing-skills`, `using-superpowers` | `constitution` | `bmad-customize`, BMad Builder | skill routing table |

Nobody's process layer exceeds ~14. superpowers stops at 14 including two git
utilities. BMAD's *generic core* is 8 (`advanced-elicitation`, `brainstorming`,
`customize`, `deep-recon`, `forge-idea`, `help`, `party-mode`, `review`).

*Here:* the ceiling is real and we are near it. Growth belongs in the pack
layer, not the skill list.

### 2. Domain-genericity comes from packs under one skill, not from more
skills. HIGH — three independent implementations.

- **Orchestra AI-Research-SKILLs** — 23 top-level directories; 22 are domain
  knowledge (`01-model-architecture` … `19-emerging-techniques`) and one is the
  orchestrator. Its `autoresearch` SKILL.md states the split outright:
  *"You are a research project manager, not a domain expert. You orchestrate;
  the domain skills execute."* It carries a routing table (research activity →
  directory).
- **BMAD** — a module registry (`bmad-modules.yaml`) installs domain modules
  beside a fixed core: Creative Intelligence Suite (ideation/problem-solving),
  Game Dev Studio, Whiteport UX, Test Architect. Same core skills, different
  module.
- **BMAD deep-recon** — one research skill with *type packs*: `market`,
  `domain`, `technical`, `competitive`, `user-voice`, `academic-lit`, plus a
  `select` shape for choose-between decisions, and user overrides. *"You already
  know how to research; the pack is where this harness is opinionated."*

*Here:* this is the direct answer to "any domain". Our `research`,
`brainstormer` and `task-brief` are already domain-free; what is missing is the
pack slot — a `references/<domain>.md` a skill loads on demand, and a rule that
domain opinion may only live there.

### 3. Linear pipelines cannot express open-ended work. HIGH.

`docs/workflow.md` is a 13-stage line with one loop-back (INVALID → planning).
Fine for a change with a known done-check. `autoresearch` is explicitly not
that shape:

> INNER LOOP: pick hypothesis → experiment → measure → record → learn → next
> OUTER LOOP: review results → find patterns → update findings → new
> hypotheses → decide direction

and it names four direction verdicts — **DEEPEN / BROADEN / PIVOT / CONCLUDE** —
where our workflow has only VALID/INVALID. It also says the structure "is a
rhythm, not a railroad": returning to literature 1-3 times mid-project is normal.

*Here:* for the user's own example — ideate a research problem from recent
publications, then plan — stages 3→5 are re-entered repeatedly and stage 8 is a
*direction decision*, not a pass/fail gate. Adding a loop mode is cheaper than a
second pipeline: same skills, a state file, and a termination criterion.

### 4. Token cost is controlled by five named mechanisms, all mechanical. HIGH.

Each is stated in at least two sources:

1. **Progressive disclosure.** `SKILL.md` is a router; `references/*.md` load
   only when the branch is taken. spec-kit's `analyze` loads *named sections*
   of each artifact, not whole files. BMAD resolves references by path at need.
2. **Extract, don't ingest.** deep-recon: *"Raw reports and search results never
   enter the parent context whole; subagents return relevance-filtered digests,
   and the parent reads digest files JIT."* superpowers' subagent skill says the
   same in reverse — everything pasted into a dispatch stays resident for the
   rest of the session, so hand artifacts over as **files**.
3. **Files are the store, chat is the control channel.** deep-recon: *"Nothing
   exists until it is a file."* autoresearch: `research-state.yaml` +
   `findings.md` read at the start of every tick. superpowers: the ledger is
   what survives compaction.
4. **Capped output.** spec-kit's `analyze`: max 50 findings, overflow
   aggregated, "minimal high-signal tokens". Ours: ~500 tokens per skill.
5. **A machine-readable completion contract.** deep-recon's headless mode ends
   in a fixed JSON object (`status`, artifact paths, claim tallies). Skills
   compose on that instead of on prose.

*Here:* we do 3 and 4. We do not do 1 (every SKILL.md is monolithic — no skill
has a `references/` directory), 2, or 5.

### 5. Two quality mechanisms are worth stealing outright. HIGH / MEDIUM.

- **A coverage matrix, not a vibe check** (spec-kit `analyze`, HIGH). It builds
  a requirements inventory from the spec, maps every task to a requirement, and
  reports requirements with zero tasks and tasks with no requirement, plus
  severity. It is read-only and never edits. This is exactly our approved but
  unbuilt `docs/specs/2026-08-01-evidence-ledger-design.md`, arrived at
  independently — strong evidence the ledger's shape is right.
- **The research firewall** (deep-recon, MEDIUM — single source, but sharply
  argued): *"Project context … shapes what to ask, never what is true. It is
  inadmissible as evidence."* Research subagents get only their brief, never
  project files. Our `research` skill has the Iron Law (never synthesise from
  something unread) but not this separation.
- **Lock before you run** (autoresearch): commit the experiment protocol to git
  *before* executing, so history proves the plan predates the result;
  confirmatory vs exploratory results are labelled. A cheap pre-registration our
  plan files could adopt verbatim.

### 6. Autonomy defaults diverge, and that is a domain property. MEDIUM.

`autoresearch` runs unattended by design — *"Do not ask the user for permission
or confirmation… The human is asleep"* — with `/loop 20m` as a heartbeat.
spec-kit puts a hard `gate` between every phase (`on_reject: abort`).
superpowers sits between: no pauses inside a plan, hard stop at anything
irreversible.

*Here:* not a contradiction — reversibility differs. An experiment in a scratch
directory is cheap to be wrong about; a merge is not. The generic rule is
**gate on blast radius, not on phase**, which is the banding idea already parked
in `HANDOFF.md` from `011matthias/agentic-ops1.01`. It now has three independent
supports.

## Disagreements

**How many skills is right?** Orchestra ships 98, BMAD ships modules totalling
far more, superpowers ships 14. The number only conflicts if you count process
and knowledge together — split them and all three agree on ~10 process skills.
Reported as a disagreement because a naive skill count is what makes big
libraries look like the goal; the token budget on the skill listing means a
large *process* layer actively harms routing.

**Where domain opinion lives.** BMAD puts it in installable modules with their
own config; Orchestra in sibling directories; deep-recon in per-type pack files
inside one skill. Leaning to deep-recon's shape for us — a pack file under the
skill that owns the stage — because our routing file must name every skill, so
new top-level skills cost routing entries and listing budget while pack files
cost nothing.

## Not adopted

- **A separate skill per research activity** (Orchestra's 22 categories). Those
  are knowledge, not process; ours would be `references/` files if we ever need
  them.
- **BMAD's installer, module registry and `customize.toml` resolution.**
  Machinery for distributing to many repos. We are one repo.
- **spec-kit's extension-hook protocol** (`.specify/extensions.yml`, before/after
  hooks per command). We already have real lifecycle hooks in `.claude/hooks/`.
- **Unattended `/loop` heartbeat autonomy** (autoresearch). It presumes cheap,
  reversible experiments and a human who accepts unreviewed direction changes.
  Conflicts with CLAUDE.md's approval gates; revisit only behind blast-radius
  banding.
- **`party-mode` / multi-persona roundtables** (BMAD core). Entertaining;
  no evidence offered that it beats a single reviewer with a rubric.

## What this implies for this repo

Ordered by leverage. Items 1-3 close the workflow; 4-5 are what make it generic.

1. **`executing-plans` (stage 7)** — already researched and specified in
   `docs/research/2026-08-02-executing-plans-prior-art.md`. Blocks everything
   downstream: no plan has ever been executed by a skill here.
2. **`verifying-work` (stage 8)** — the coverage matrix. Answers "did we solve
   the thing the brief asked for", not "do the tests pass" (`/verify` already
   answers that). This is the evidence-ledger spec's units 1-4 in skill form,
   and spec-kit's `analyze` is a working reference implementation.
3. **`delivering` (stage 12)** — the ship gate: branch finish, what to say in
   the log, when a decision record is owed, explicit approval before anything
   irreversible. Today this is three hooks and a slash command with no skill
   coordinating them.
4. **A pack slot in the skills that have domain opinion** — `references/` files
   under `research`, `brainstormer` and `task-brief`, plus the rule that domain
   opinion may live nowhere else. This is what turns the same seven skills into
   a research pipeline, a product pipeline, or a legal one.
5. **A loop mode for open-ended work** — inner/outer with DEEPEN / BROADEN /
   PIVOT / CONCLUDE, a state file, and a stated termination criterion. Belongs
   inside `executing-plans` as a mode, not as a new skill.
6. **`writing-skills` (meta)** — every skill here has been written by hand
   against an implicit standard. superpowers, BMAD Builder and Orchestra all
   ship one. Lowest urgency, highest compounding.

Not on the list, deliberately: more skills. Six process skills for six stages,
then packs.

## Sources

All opened this session unless noted.

- [obra/superpowers](https://github.com/obra/superpowers) — `skills/` directory listing (14 skills); `executing-plans/SKILL.md` and `subagent-driven-development/SKILL.md` read in full
- [github/spec-kit](https://github.com/github/spec-kit) — `workflows/speckit/workflow.yml` (specify → gate → plan → gate → tasks → implement) and `templates/commands/analyze.md` read in full; `templates/commands/` listing (10 commands)
- [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) — `bmad-modules.yaml` and `src/core-skills/bmad-deep-recon/SKILL.md` read in full; `src/core-skills/`, `src/bmm-skills/plan/`, `src/bmm-skills/ship/` listings
- [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) — `0-autoresearch-skill/SKILL.md` read in full; root listing (23 categories)
- [edobry/minsky `implement-task`](https://github.com/edobry/minsky/blob/main/.claude/skills/implement-task/SKILL.md) — read earlier this session; carried in as the fourth family
- Named but not opened, for a later pass: [Galaxy-Dawn/claude-scholar](https://github.com/Galaxy-Dawn/claude-scholar), [wanshuiyin/auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/auto-claude-code-research-in-sleep) (ARIS, 81 composable skills), [imbad0202/academic-research-skills](https://github.com/imbad0202/academic-research-skills)
- This repo: `docs/workflow.md`, `docs/specs/2026-08-01-evidence-ledger-design.md`, `.claude/routing/process-skills.md`, all seven `SKILL.md` files
