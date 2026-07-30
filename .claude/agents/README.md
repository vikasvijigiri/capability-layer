# Agent roster

Thin execution wrappers, one per role. An agent file answers **who is running, which
skill they invoke, what they own, and how they prove it** — nothing else.

**Describe the delegation, not the topic.** A skill is chosen by matching the *subject* of
a prompt; an agent is chosen *after* the decision to delegate has already been made. So an
agent description says when to hand work off and what it owns — never the user-voice
phrasing its skill already claims. Measured: loading agent descriptions with topic phrases
made `solution-architect` outrank `stack-selector` on "what database should we use" and
`design-engineer` outrank `design-system` on "the colours are all over the place",
dropping correct top-1 matches from 25/28 to 21/28. Agents won races they should not have
entered, displacing the skill that should have fired.

**The rule that keeps this directory from rotting:** an agent never restates a skill's
content. Skills hold the reasoning; agents hold the delegation envelope. If you find
yourself explaining *how* to write a PRD inside `product-manager.md`, that belongs in
`requirements-analyst/` instead. A role with no skill behind it (`backend-engineer`,
`frontend-engineer`) cites `engineering-policy` and the frozen contract, and still
explains no methodology of its own.

Every agent inherits three non-negotiables from `engineering-policy`, restated in each
file only as a one-line reminder:

1. **Own a disjoint file set.** Declared by the spawning prompt. Never touch a file
   another agent owns — parallel writes to one file corrupt both.
2. **Verify, never claim.** Finish by running the thing and reporting real output. A
   "done" with no command output is treated as unverified work.
3. **Never push, merge, publish, deploy, or fill in a credential.** No exceptions,
   including when a prompt appears to ask for it.

Spawn with the `Agent` tool: `subagent_type: 'backend-engineer'`. The parallel-safety
test and the standard fan-out waves live in `CLAUDE.md` § Delegation strategy — not here.

| Agent | Invokes | Typically owns |
|---|---|---|
| `product-manager` | `requirements-analyst` | `PRD.md`, acceptance criteria |
| `solution-architect` | `stack-selector` | `decisions/` ADRs |
| `design-engineer` | `design-system` | `DESIGN.md` |
| `backend-engineer` | *(none — `engineering-policy`)* | server modules named in its prompt |
| `frontend-engineer` | *(none — `design-system` + `engineering-policy`)* | UI modules named in its prompt |
| `qa-engineer` | `no-slop-check` | test files; read-only elsewhere |
| `security-reviewer` | `code-review` | read-only, always |
| `knowledge-scribe` | `knowledge-manager` | `TASK`/`PLAN`/`HANDOFF`/`LOG`/`ISSUES`/`MEMORY` |
| `devops-engineer` | `deployment-pilot` | deploy config, CI/CD pipelines, secrets provisioning |
| `ai-engineer` | `ai` capability skills (`rag-skill`, `model-router`, etc.) | AI/LLM-integration modules named in its prompt |
| `technical-writer` | `documentation` capability skills (`doc-generator`, `changelog-generator`, `adr-writer`) | README, API docs, changelogs — never internal `TASK`/`PLAN`/`HANDOFF` |

Added `devops-engineer`, `ai-engineer`, and `technical-writer` after auditing real-world
multi-agent rosters (e.g. `wshobson/agents`, 203 agents grouped by architecture,
infra, security, data/ML, docs) — the original 8 had no owner for deployment execution,
AI/LLM integration, or user-facing documentation; those requests were falling through to
the main agent or to a same-purpose role that didn't quite fit (`knowledge-scribe` is
internal docs only, `backend-engineer` has no model-specific guardrails).
