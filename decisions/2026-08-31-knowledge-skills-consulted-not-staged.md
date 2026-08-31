## Decision

A skill that teaches domain practice (what "good" looks like — API design,
testing pyramids, accessibility, security checklists) is registered off-chain
in `.claude/workflow.md`'s "Off-chain capabilities" table and *consulted* by
the procedure-owning skills that already gate develop/diagnose/design/scale
(`implementation`, `debugging`, `architecture`, `release-git`), never given
its own numbered lifecycle stage. Separately: when a subagent needs the same
procedural contract as an existing one plus a small addition, it reads the
existing agent's file at runtime (`Read .claude/agents/implementer.md` as
its first instruction) rather than copying the contract's prose into its own
file.

Both landed together in `engineering-standards` (`docs/plans/
2026-08-24-engineering-standards-skill.md`, PR #42): one skill plus two
`backend-engineer`/`frontend-engineer` subagents.

## Why

**Off-chain, not staged.** This repo's SDLC chain already owns every verb a
"full-stack" request implies — design (`architecture`), develop
(`implementation`), diagnose (`debugging`), scale/monitor (`release-git`'s
`observability-sre.md`). A new skill that *also* claimed one of those verbs
would duplicate an existing gate (`CLAUDE.md`: "Never: create a duplicate
implementation of something that already exists"). The actual gap was
narrower — none of those skills carried backend/frontend *domain knowledge*
to apply while doing their own job. The off-chain slot (same one `research`
and `security` already use) is exactly "reusable capability, not a stage,"
which fits without inventing a new mechanism.

**Runtime-read contract, not copy-paste.** The first draft of
`backend-engineer.md`/`frontend-engineer.md` literally duplicated
`implementer.md`'s entire body (four statuses, worktree method, rules) —
the plan's own words were "copied, not paraphrased," reasoning that any
divergence would be an unmeasured new failure mode. `test_no_slop.py
--scope layer` correctly flagged the result as three-way duplicated prose.
Both intentions were right and in tension: identical procedural fidelity,
but one owner. Since every agent here already has `Read`, a subagent can be
told to read another agent's file as its first action — same fidelity as a
copy (it is the same text, read live), one source of truth instead of
three, and a future edit to `implementer.md`'s contract now reaches both
variants automatically instead of needing three synchronized edits.

## Alternatives considered

- **Two separate top-level skills** (`backend-standards`, `frontend-standards`)
  instead of one `engineering-standards` skill with a SCAN phase. Real prior
  art splits both ways — `siviter-xyz/dot-agent` ships two skills;
  `AThevon/genjutsu` (rated the strongest precedent in the prior UI/UX
  research cycle) handles three platforms from *one* skill via stack
  detection. Chose one skill: `CLAUDE.md`'s per-turn description-cost
  discipline favors one trigger surface over two overlapping ones, and this
  repo's own convention (`architecture`, `release-git`) is already
  hub-plus-`references/*.md`, not many similar top-level skills.
- **Role-persona subagents** (`RISHI168/ai-product-lifecycle`'s BACKEND
  ENGINEER AGENT / FRONTEND ENGINEER AGENT / DATABASE ARCHITECT AGENT
  swarm) as the whole answer, no skill at all. Rejected as the sole shape:
  this repo's agents are procedure specializations dispatched *by* a
  verb-owning skill for one plan task (`implementer`'s existing role), not
  a standing cast of department personas — adopting the persona shape
  wholesale would restructure the agent system around a different axis
  than the rest of the layer uses, for a narrower gap than that scale of
  change justifies. The subagent half of this decision (`backend-engineer`/
  `frontend-engineer`) borrows the *naming*, not the persona architecture.
- **First draft: reject the whole request, add nothing.** The initial
  research pass (`docs/specs/2026-08-24-fullstack-skills-scope-design.md`)
  found every named verb already owned and concluded no new skill was
  needed. Correct on the narrow question asked (naming Grafana specifically)
  but wrong on the actual ask once the user clarified Grafana was one
  example among develop/diagnose/maintain/scale/monitor/repair, not the
  whole request — superseded once the real scope was research-backed rather
  than argued from what already existed.
