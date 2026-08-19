# GOAL_CHECKLIST.md
### Autonomous `.claude/` Engineering System — Production-Grade, 2-Gate Build Checklist

**North Star:** A prompt dropped into Claude Code flows end-to-end — understanding → decomposition → parallel subagent execution → plan → **Gate 1** → build/verify/review → **Gate 2** → ship → monitor → remember — with exactly two human touchpoints. Everything between the gates must be trustworthy enough to run **unattended**, which is the real bar for "production grade."

---

## 0. Scaffolding

- [ ] `.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, `.claude/workflows/`, `.claude/memory/`, `.claude/state/` (gitignored)
- [ ] `.claude/settings.json` — model routing, tool permissions, hook wiring
- [ ] `.claude/audit/` — append-only, immutable log of every tool call, file write, and decision (see §13)
- [ ] `.claude/README.md` documenting the pipeline for future contributors and future agents

---

## 1. Understand Prompt
- [ ] Intake normalizes: goal, constraints, non-goals, acceptance criteria, blast radius
- [ ] Ambiguity → ≤1 clarifying question, else assume-and-state
- [ ] Classify request weight (typo/chore/feature/migration) → routes pipeline depth
- [ ] Output: `state/intent.json`

## 2. Task Decomposition
- [ ] DAG of tasks tagged `independent` vs `dependent`, owning agent, blast radius
- [ ] Conflict detection on overlapping file ownership
- [ ] Minimality check — smallest viable decomposition, not sharding for its own sake
- [ ] Output: `state/plan.json`

## 3. Subagent Dispatch
- [ ] Agent roster in `.claude/agents/`: role, allowed tools, allowed file globs, model tier, hard boundaries
- [ ] Independent tasks run concurrently; dependents queued
- [ ] Structured returns: diff, summary, self-reported confidence, open questions

## 4. PLAN (Opus, Plan Mode)
- [ ] Model-locked to Opus for this stage only
- [ ] Synthesizes subagent outputs into ordered steps, each with: files touched, rollback strategy, verification strategy, definition of done
- [ ] Read-only stage — no writes, no commits
- [ ] **New — Risk tier assigned to the whole plan**: `low` / `medium` / `high` based on blast radius, data-migration involvement, and public-surface change. This tier controls how much automation is trusted later (see §9, §11)
- [ ] Output: `state/plan_final.md` / `.json`

---

## ✅ GATE 1 — Plan Approval
- [ ] Human sees plan summary, risk tier, rollback strategy, affected surfaces
- [ ] Decisions: `approve` / `reject` / `replan-with-feedback` (capped at 3 replans)
- [ ] **No default-approve on timeout** — silence blocks, never advances
- [ ] Decision + rationale logged to `state/gate-log.json`
- [ ] From here to Gate 2, the system runs **without a human unless it explicitly escalates**

---

## 5. Plan Executor
- [ ] Executes steps in dependency order
- [ ] Minimal-diff mandate enforced structurally (hook flags unrelated churn), not just requested
- [ ] One commit per logical step, message references plan step ID
- [ ] Halts and escalates if a step's preconditions no longer hold at execution time — never improvises around a broken assumption

## 6. Executor Verifier
- [ ] Verifier is a distinct agent/context from the executor (no self-grading)
- [ ] Verifies against `definition_of_done`, not just "it compiles" — actual observable behavior
- [ ] Retry loop, max 3 per step, counters persisted; exhausted retries escalate rather than silently pass or silently drop
- [ ] Full-plan integration verification once all steps individually pass

## 7. No-Slop Pass
- [ ] `local` scope: dead code, unused imports, debug prints, stub TODOs, naming drift
- [ ] `global` scope: duplicated logic, architectural drift, over-engineering vs. stated goal
- [ ] Auto-fixable → fixed + re-verified; non-auto-fixable → flagged forward, never dropped

## 8. Code Review
- [ ] Local: correctness, edge cases, secrets/injection/auth basics
- [ ] Global: fits existing conventions, doesn't break other consumers, debt proportionate to task
- [ ] Reviewer agent distinct from executor agent; blocking findings loop back to §5/§6

## 9. Security & Compliance Gate *(new — automated, not a human gate)*
- [ ] SAST on the diff; dependency/SBOM vulnerability scan on anything newly added
- [ ] Secret scanning (also present as a pre-commit hook, this is the belt-and-suspenders pass)
- [ ] License compliance check on new dependencies
- [ ] For `high` risk-tier plans: mandatory DAST/pen-test-lite pass against a staging instance before proceeding
- [ ] Any finding above severity threshold **blocks** progression — routes back to §5, does not degrade to a warning

## 10. Data & Migration Safety *(new — only triggers if plan touches schema/data)*
- [ ] Migrations are backward-compatible / dual-write or otherwise reversible by design, not just "has a down-migration"
- [ ] Rollback of the migration is actually executed once in staging, not merely written
- [ ] No destructive migration (drop column/table) ships without an explicit soak period already having passed

## 11. Git Operations
- [ ] Branch per run; rebase before push for a linear, minimal-diff history
- [ ] Trivial conflicts auto-resolved; substantive conflicts escalate
- [ ] PR description auto-generated from the plan + review findings, not the raw commit list
- [ ] Merge to main/staging only after §6–§10 all pass

## 12. Staging Rehearsal *(new)*
- [ ] Full deploy rehearsed in staging with production-like data shape/load
- [ ] Smoke tests + a short synthetic load/perf check against the acceptance criteria from §1
- [ ] Canary/feature-flag wiring validated (flag exists, defaults correctly, can be flipped independently of a deploy)
- [ ] Rollback path from §4/§10 executed once here, not just documented
- [ ] Output: a staging report attached to the release candidate — this is what Gate 2 actually reviews

---

## ✅ GATE 2 — Production Release Approval
- [ ] Human sees: staging report, security/compliance results, risk tier, rollback plan, blast radius, diff summary
- [ ] Decisions: `approve` / `reject` / `hold-for-more-info`
- [ ] For `low`-risk-tier plans, this gate can be pre-configured as **auto-approve-with-notify** (still logged, still reversible) — keeps the human focused on things that matter instead of rubber-stamping every typo fix. `medium`/`high` tier always waits for explicit approval.
- [ ] No default-approve on timeout for anything above `low` tier
- [ ] Decision + rationale logged to `state/gate-log.json`

---

## 13. Release / Ship
- [ ] Progressive rollout (canary % → full) rather than instant 100% for `medium`/`high` tier changes
- [ ] **Automatic rollback triggers** wired to real metrics (error rate, latency, saturation) — not just a human noticing something's wrong
- [ ] Auto-generated changelog + semver bump from the plan + review history
- [ ] Post-ship smoke check against production, not just staging

## 14. Post-Release Monitoring
- [ ] Defined bake time per risk tier before the run is considered "done" (not "merged = done")
- [ ] Alerting wired to the same dashboards a human on-call would watch
- [ ] Auto-rollback (§13) fires without waiting for a gate — production incidents don't get a human-approval bottleneck
- [ ] Blameless post-mortem template auto-drafted on any rollback/incident, feeding §15

## 15. Knowledge Manager (Learn & Record)
- [ ] Persists: what worked, what failed and why, gate decisions and feedback patterns, recurring no-slop/review findings → candidate new hook/lint rules, repo-specific conventions and shorthand
- [ ] **Read**, not just written: Stage 1 and Stage 4 query memory on every subsequent run
- [ ] Periodic pruning/compaction so memory doesn't rot into noise
- [ ] Incident post-mortems (§14) become explicit inputs to future risk-tier assignment (§4)

---

## Cross-Cutting: What Makes This *World-Class*, Not Just Complete

- [ ] **Least-privilege agent sandboxing** — every agent's tool/file access is scoped to exactly what its task needs, enforced by hooks, not by prompt instruction alone
- [ ] **Immutable audit trail** (`.claude/audit/`) — every tool call, file write, and gate decision logged with timestamp and actor, queryable after the fact for "what did the system actually do"
- [ ] **Kill switch** — a single command that halts any in-flight run at any stage, safely, from any state (mid-execution, mid-rollout)
- [ ] **Cost/token governance** — budget ceiling per run; runs that blow the budget escalate instead of running unbounded
- [ ] **Meta-evaluation suite** — a fixed set of golden tasks run periodically through the *whole pipeline* to detect drift/regression in the agents and hooks themselves, not just in the target codebase
- [ ] **Idempotency** everywhere — any stage can be safely re-run after an interruption without duplicating commits, deploys, or side effects
- [ ] **Model routing tuned to risk, not uniformly** — strongest models on Plan/Verify/Review/Security, cheaper/faster models on mechanical execution and local no-slop
- [ ] **Async escalation channel** (Slack/email/etc.) distinct from the two gates — for "FYI, retries maxed on step 4" notifications that don't need to block the pipeline the way Gate 1/2 do

---

## Definition of "Done" for This Meta-System

- [ ] A `high`-risk feature runs the full pipeline with exactly two human touchpoints (Gate 1, Gate 2)
- [ ] A `low`-risk chore auto-classifies, auto-approves at Gate 2, and still leaves a full audit trail
- [ ] At least one dry run has exercised: reject-and-replan at Gate 1, retry-then-escalate at §6, a blocked security finding at §9, and an automatic production rollback at §14
- [ ] Memory from a prior run demonstrably changes risk-tiering or planning behavior on a later, similar run
- [ ] The kill switch has been tested mid-run at least once and left the repo/state in a clean, resumable condition