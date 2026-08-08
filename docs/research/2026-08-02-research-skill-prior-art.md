# What should a `research` skill for this repo look like?

**Asked because:** workflow stage 3 was unowned, and the same request had been
made five times in one session with visibly varying output quality.
**Verdict:** adopt `agent-studio/deep-research`'s five-phase structure and Iron
Law, add `minsky/research-sandwich`'s grounding discipline, and skip its
subagent orchestration. Built as `.claude/skills/research/`.

## Findings

**A five-phase shape is the convergent structure.** HIGH — both primary sources
independently land on scope → gather → synthesise → validate → report, and 508
`.claude/skills/*research*` files exist, so the pattern is well-trodden.
[agent-studio/deep-research](https://github.com/oimiragieo/agent-studio/blob/main/.claude/skills/deep-research/SKILL.md)
states it explicitly; [minsky/research-sandwich](https://github.com/edobry/minsky/blob/main/.claude/skills/research-sandwich/SKILL.md)
compresses it into plan → fan out → synthesise.
*Here:* adopted directly as Phases 1-5.

**"Never synthesise without reading sources" is the load-bearing rule.** HIGH —
agent-studio makes it the Iron Law, minsky words it as "verify, don't inherit:
the failure family this project keeps hitting is inheriting a framing without
checking it". Two sources, same conclusion, arrived at from different directions.
*Here:* this repo's own recurring failure is *prose declares a capability the
wiring does not implement*, seven instances — the same class. Became the
HARD-GATE.

**Evidence must be logged before synthesis, not after.** MEDIUM — single source
(agent-studio), but its reasoning is concrete: "context resets lose unsaved
evidence", and it pairs the rule with "ASSUME INTERRUPTION".
*Here:* kept as guidance rather than a hard phase gate, since our sessions are
shorter than the ones that rule was written for.

**Confidence must be graded and conflicts surfaced, not resolved silently.**
HIGH — agent-studio grades CONSENSUS/CONFLICT and forbids presenting LOW as a
conclusion; minsky requires distinguishing the "settled layer" from the
"unsettled layer" and flagging anything unground.
*Here:* both folded into Phase 3, plus a `## Disagreements` report section.

**Findings must map back to a named local mechanism.** HIGH — minsky is
emphatic: "an ungrounded lit-review is not the deliverable", web research must
map to "the named Minsky mechanism the workstream illuminates".
*Here:* this is the single most transferable idea. "Repo X does Y" is a fact
about repo X, not a decision input.

**The deliverable must land outside chat.** HIGH — minsky: "chat is not the
storage layer"; agent-studio writes a dated report to a fixed path.
*Here:* the sharpest local evidence. The best find of 2026-08-02 —
`no-auto-commit-gate.py`'s blast-radius banding — was deferred in prose and is
now buried under 400 lines of `LOG.md`. Report path is
`docs/research/YYYY-MM-DD-<topic>.md`.

## Disagreements

**Orchestration vs single-context.** minsky mandates a frontier planner, 4-7
parallel subagents, and a frontier synthesiser, and says "the planner is not
optional". agent-studio does it in one context with a phase discipline.

Leaned to agent-studio. minsky's own gate is that the question must exceed one
context, and none of the five research asks this session did — each was answered
by 2-6 tool calls. Their cost warning applies directly: "justified by breadth
and a durable deliverable, not by 'this would be thorough.'" The decompose
option survives in `## Routing` as guidance, without spawning agents.

**Report location.** agent-studio nests under `.claude/context/reports/backend/`;
minsky routes to a task, memory, doc, or Notion page by shape. Chose `docs/`,
matching where `brainstormer` and `writing-plans` already write.

## Not adopted

- **Subagent fan-out.** See above; also, agents should not be spawned unless
  asked for.
- **`pnpm search:code` / `ripgrep` skill chain** (agent-studio) — Node-specific;
  our equivalent is `mcp__github__search_code` plus `Grep`.
- **Memory Protocol block** (agent-studio) — reading `learnings.md` /
  `issues.md` / `decisions.md` before and after. `knowledge-manager` already
  owns that here, and duplicating it would create the second owner this repo
  keeps having to delete.
- **Trust/provenance frontmatter** (`trust_score`, `provenance_sha`) — machinery
  with nothing to consume it here.
- **`[UNVERIFIED]` as a separate report section** — kept as an inline label
  instead; a section invites parking things there.

## Sources

- [oimiragieo/agent-studio `.claude/skills/deep-research/SKILL.md`](https://github.com/oimiragieo/agent-studio/blob/main/.claude/skills/deep-research/SKILL.md) — read in full
- [edobry/minsky `.claude/skills/research-sandwich/SKILL.md`](https://github.com/edobry/minsky/blob/main/.claude/skills/research-sandwich/SKILL.md) — read in full
- `mcp__github__search_code` — 508 hits on `research` + `SKILL.md` under
  `.claude/skills`; 5 on `deep-research`/`web-research`. Repos named but not
  opened: `tyrchen/rust-lib-template`, `friedbotstudio/baseline`,
  `tstapler/dotfiles`, `alvarovillalbaa/open-evals`.
- This session's own five research passes, as the local evidence base.
