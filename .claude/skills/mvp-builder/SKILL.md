---
name: mvp-builder
model: opus
description: Fully autonomous, zero-checkpoint MVP build — takes a goal/constraints statement once and runs PRD, architecture, scaffold, implementation, QA, deployment and handoff unattended, on free tiers only, to a live product. Use for "build me an MVP", "build me a SaaS/app/platform", "build and deploy this", "build project from scratch", "create app unattended", or any ask for a complete product unattended. Prefer this over an interactive build when nobody is available to answer checkpoints - it logs blockers instead of stopping. Do NOT use for smaller asks or feature tweaks — use workflow-orchestrator instead.
user-invocable: true
allowed-tools:
  - Read
  - Agent
provides: [autonomous-build]
requires: [goal]
produces_artifact: true
retryable: false
---

# MVP Builder

Launches an autonomous, zero-checkpoint MVP build via the `build-mvp.js` workflow script.

## Execution Sequence

1. **Intake & Brief Confirmation**: Accept goal/constraints, restate as a structured brief, and obtain user approval. No further prompts after this step.
2. **Workspace Setup**: Derive hyphenated slug from 2–4 key terms in goal (e.g., `~/mvp-builds/<project-slug>`). Ensure fresh directory creation.
3. **Complexity Classification**: Classify as `trivial`, `small`, or `full` to scope phase execution.
4. **Run the phases yourself**, in the order specified by
   [`.claude/workflows/build-mvp.js`](../../workflows/build-mvp.js). That file is a
   **phase specification, not an executable** - it assumes `agent()`/`phase()`
   primitives from a workflow runtime that does not exist in Claude Code, and Node
   rejects it outright (`SyntaxError: Illegal return statement`). Read it for the
   phase order, gates and per-phase prompts, then drive each phase with the real
   mechanisms:

   | Phase | Drive with |
   |---|---|
   | PRD | `requirements-analyst` skill, or `product-manager` agent |
   | Architecture | `stack-selector` skill, or `solution-architect` agent |
   | Scaffold | `repo-onboarding` skill |
   | Implement (per feature) | `backend-engineer` / `frontend-engineer` / `ai-engineer` agents |
   | Review gate | `code-review`, then `no-slop-check` |
   | Recovery on failure | `error-recovery` (never retry ad hoc) |
   | QA | `qa-engineer` agent |
   | Deploy | `deployment-pilot` skill, or `devops-engineer` agent |
   | Handoff | `knowledge-manager` skill |

   Honour the spec's recovery rule: a phase that fails twice goes to `error-recovery`,
   and an unrecoverable one is logged as a blocker rather than silently dropped.
5. **Final Handoff**: Relay final report (live URL, repo URL, feature list, zero-cost confirmation, and any logged blockers).

## Autonomy Principles

- **Zero Checkpoints**: Overrides intermediate human approval prompts during execution. Resolves ambiguities using skill defaults (`requirements-analyst`, `stack-selector`, `deployment-pilot`) or logs them as blockers in `HANDOFF.md`.
- **Zero Cost Floor**: Enforces free-tier infrastructure, free APIs, and open-weight models (`openai/gpt-oss-120b` on Groq).
- **Safety Limits Apply**: Standard safety rules remain non-negotiable (no malicious content, no credentials committed).
