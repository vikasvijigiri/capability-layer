# Merge the layer into the Notion target architecture, by measurement not by name

Date: 2026-08-21

## Decision

`.claude/` is restructured to match the Notion page *Agentic Workflows (IDE) —
Universal Adaptive SDLC v2*'s naming and shape (§5-9, §18), full literal
rename, chain rewired to match — superseding the 2026-08-20 audit's decision
to keep stage-shaped names over Notion's domain names. Full task-by-task
detail lives in `docs/plans/2026-08-21-notion-architecture-merge.md`; this
record is the rationale and the traceability tables, not a second copy of
the task list.

**Naming map** (full detail in the plan's File map):

| Layer | Before | After |
|---|---|---|
| Hooks (10 families) | `session-start, user-prompt, pre-run, on-artifact-create, post-tool{01,02}, post-tool{04-07}, pre-commit+pre-deploy, pre-edit, post-run{00,03,06-08}, post-run{09}` | `session-init, prompt-intake, pre-tool, post-edit-validation, context-budget, post-tool, permission-security, pre-edit, stop-finalization, telemetry` |
| Skills (12 Notion + 2 extensions) | `repo-recon, executing-plans, systematic-debugging, verifying-work, no-slop, knowledge-manager, brainstormer+designer, delivering+releasing, writing-plans, research, code-review, capability-layer-maintenance` | `repository-navigation, implementation, debugging, testing, refactoring, documentation, architecture, release-git, task-analysis, research (unchanged), code-review (kept, extension), capability-layer-maintenance (kept, extension)`, plus new `data-analysis`, `security` |
| Agents (7 Notion + 2 platform-native) | `architecture-reviewer, task-implementer, test-verifier, failure-investigator, diff-reviewer+spec-reviewer+release-verifier, source-digger+repo-cartographer, security-reviewer, Explore` | `architect, implementer, tester, debugger, reviewer, researcher, security-reviewer (unchanged), Explore (unchanged, platform-native)` |
| Commands (6 Notion + 5 repo-specific) | `plan-review` renamed; `git-state, handoff, wip, verify, verify-change` kept | `+task, debug, review, research, release`; `plan-review`→`plan` |

## Why

**Measured, not assumed, per the explicit instruction this unit was built
under.** Three things were tested empirically rather than taken on faith:

1. **"JS hooks run way faster than Python" — did not hold.** Timed on the
   build machine: trivial cold start, Python 51.9ms avg vs Node 69.2ms avg
   (Python faster); with a JSON-module import (closer to real hook work),
   77.2ms vs 76.7ms (statistically identical); one real hook
   (`pre-edit/01-forbidden-change-guard.py`) cold = 146ms, and the gap above
   the ~77ms interpreter floor is the hook's own logic (git subprocess
   calls), which costs the same in any host language. Hooks stay Python.
2. **The real latency cost was subprocess count, not language.** Every
   `Bash`/`PowerShell` call fired 5 separate Python process launches on
   `PreToolUse` before this unit. This repo had already solved the same
   problem once, for `Stop` (`post-run/00-dispatch.py`) — just not yet
   applied to `pre-commit`/`pre-deploy`. `permission-security/00-dispatch.py`
   is that same pattern, applied where it was missing.
3. **The real token cost was skill-body size, not directory naming.**
   `tools/bench.py`, one session: 189 skill-body loads, 1,329,482 chars
   (~332,370 tokens) — the largest measured cost in the whole layer,
   dwarfing hook latency or duplicate calls. `writing-plans/SKILL.md`
   (21,329 ch) was both the largest body and, per
   `decisions/2026-08-09-one-door-into-the-chain.md`, the single door for
   all named work — highest-leverage compression target. External grounding
   (Claude skill-authoring docs, via websearch): progressive disclosure
   targets ~750 tokens (~3,000 ch) per body. `TASK.md`'s "Rewrite skill
   frontmatter for triggering" task had already named this exact follow-up
   in its own Out of Scope line — this unit is that follow-up, not a new
   idea invented here.

**The naming reversal itself.** The 2026-08-20 audit
(`docs/research/2026-08-20-notion-objectives-audit.md`) graded stage-shaped
names a better fit than Notion's domain names and called Notion's list
"illustrative... not mandatory." That reasoning was sound *as a default* —
this repo's whole purpose is enforcing an SDLC chain, and a rename with zero
functional gain has real cost (every hardcoded reference across
`test_process_router.py`, `workflow.md`, `decisions/`, docs). It was
overridden here on **explicit, repeated user direction** after that exact
tension was surfaced and the cost was stated plainly — not silently done,
and not because the prior reasoning was wrong on its own terms.

**The E0-E5 execution-level router.** Notion §3's execution-level model
(E0 direct through E5 full workflow, chosen by evidence not complexity) had
been scoped once as "S2/S3" in `TASK.md`'s "S1: make every turn cheap" task
and never built; `.claude/hooks/telemetry/09-telemetry.py` shipped with a
hardcoded string admitting exactly this
(`"execution_level": "no E0-E5 router exists yet -- a separate audit gap"`).
This is the mechanism most directly tied to the user's stated top
priorities (minimal tokens, minimal end-to-end time, maximum efficiency) —
Notion §3 exists specifically so "long prompt ≠ many agents" and "complex
domain ≠ maximum reasoning." The weighted scoring shape (files 0.30,
domains 0.25, steps 0.25, research 0.20) is adapted from a production
complexity-classifier pattern found via websearch alongside arXiv 2603.22455
(*SkillRouter*), using signals this repo already computes
(`tools/scope.py`, `_hooklib.PROGRESS_TASK_BOX`,
`parallel_groups.py` concurrency) — not a new NLP pass. It reports, never
gates, matching the `context-budget` hook's own precedent for the same
reason (a `PreToolUse` gate on this class of signal was tried once and
rejected — Gap B, 2026-08-20 audit).

## Section-by-section coverage (all 25 Notion sections)

| § | Section | Verdict | Where |
|---|---|---|---|
| 0 | 30 Primary Objectives | Partial | Top 4 the user named drive the workstreams below; the rest are pre-graded in `docs/objectives.md` — this unit's Task 9 re-checks only the objectives its own files touch |
| 1 | Universal Adaptive SDLC (11-box lifecycle) | Closed | `task-analysis` covers INTAKE+STATE (`tools/resume.py`) + a genuine-task TASK GATE (new) + TASK ANALYZER (the E0-E5 score) + CONTEXT BUDGETER (skill compression); CAPABILITY/EXECUTION ROUTER = entry-classifier + the E0-E5 score |
| 2.1 | Context Budget | Closed | Skill-body compression (7 oversized files split to `references/`) |
| 2.2 | API/Tool Budget | Deferred, reasoned | Behavioral principle already in `CLAUDE.md` ("Reuse before creating"); a request-fingerprint cache is new infrastructure out of proportion to this unit |
| 2.3 | Work/Effort Budget | Already matched | `tools/loop.py`'s rung ladder already implements this exactly |
| 3 | Execution Levels E0-E5 | Closed | `01-entry-classifier.py`'s weighted score; `09-telemetry.py`'s predicted/actual pair |
| 4 | Capability Architecture | Already matched | `.claude/agent-memory/` already served "Memory"; Notion's own §18 tree omits it too |
| 5 | Core Skill Set — 12 | Closed | Naming map above |
| 6 | Core Agent Set — 7 | Closed | Naming map above |
| 7 | Hook Architecture — 10 families | Closed | Naming map above + consolidation |
| 8 | Commands — 6 | Closed | Naming map above |
| 9 | Workflow Set — 5 (W1-W5) | Closed | Each `workflows/*.md` points at a distinct existing mechanism (see plan's Design A tables) — not one pointer repeated five times |
| 10 | Anti-Repetition Layer | Partial | Single-Source-of-Truth half already enforced (`decisions/2026-08-07-one-workflow-engine.md`); reuse-before-retrieve cache half is detection-only (duplicate-rate `statusMessage`) |
| 11 | Artifact-First Agent Communication | Already matched | Claude Code's own subagent model returns a summary by construction |
| 12 | API/Tool Call Optimization | Deferred, reasoned | Same as 2.2 |
| 13 | Context Compression Strategy | Closed | Same mechanism as 2.1 |
| 14 | Verification Pyramid | Already matched | `testing` (was `verifying-work`) → `code-review` → Gate 2, cheap-to-expensive already |
| 15 | Adaptive Verification Depth | Already matched, coarser | `tools/scope.py`'s small/major + 3-tier risk is a coarser, functionally equivalent version |
| 16 | Failure Recovery | Already matched | `workflow.md`'s failure loop already local-repair-before-escalate |
| 17 | Human Intervention Policy | Already matched | The two-gate model already encodes this |
| 18 | Optimal `.claude/` Architecture | Closed | This entire unit |
| 19 | Runtime Decision Matrix | Closed | Folded into `task-analysis/SKILL.md` as explicit guidance |
| 20 | What MUST NOT Happen | Self-checked | See table below |
| 21 | Telemetry schema | Substantially closed already | Cluster C (prior unit) built most of it; this unit closes the one field it left a gap-string |
| 22 | Ultimate Routing Objective | Already matched (philosophy) | Rationale connecting hook latency, token cost, and right-sized execution into one frame — not separately coded |
| 23 | World-Class Example | Already matched | The small-work path already is this example |
| 24 | Final Architecture | Closed | "Capability Resolver" = entry-classifier + `task-analysis`; "Policy Gate" = the new `policies/` directory |
| 25 | Final Principles (20) | Traceability below | |

### §20 anti-pattern self-check

| Anti-pattern | Avoided how |
|---|---|
| Agent explosion | 11 → 7 (consolidation) |
| Skill explosion | `data-analysis`/`refactoring` given real, grounded content, not stubs |
| Context dumping | Skill-body compression |
| API explosion | Duplicate-rate detection |
| Repeated retrieval/reasoning | `reviewer`/`researcher` agent merges |
| Hook explosion | Consolidation reduces process count, adds no hooks |
| Workflow inflation | `workflows/change.md` points at the small-work path specifically |
| Verification theater | `security_gate.py`'s existing design untouched |
| Max reasoning everywhere / full-suite reflex | E0-E5 makes right-sizing itself measurable |

### §25 — 20 Final Principles, traced

1. One universal SDLC, adaptive execution — `workflow.md`'s 9-stage table, unchanged in shape, renamed in owner
2. Direct execution is the default — small-work path, unchanged
3. Agents are exceptions — 7-agent catalogue, consolidated not grown
4. Skills loaded just in time — unchanged mechanism, smaller bodies
5. Hooks enforce deterministic invariants — consolidated, same contract
6. Tools/MCPs called only when they add information — unchanged
7. Context is a budget — Workstream C
8. API calls are a budget — duplicate-rate detection
9. Repetition is a defect — same
10. Reuse before retrieve — `CLAUDE.md`, reinforced in `task-analysis`
11. Batch before serial — unchanged (not rebuilt this unit)
12. Parallelize only when ROI positive — `tools/parallel_groups.py`, unchanged
13. Deterministic before semantic verification — the existing pyramid, unchanged
14. Repair locally before restarting — `tools/loop.py`, unchanged
15. Escalate capability, not the workflow — same
16. Artifacts are interfaces between agents — platform-native subagent model
17. Single Source of Truth — `workflows/`/`policies/` are pointers, never restatements
18. Human is an exception path — the two-gate model, unchanged
19. Telemetry optimizes routing — Cluster C + this unit's `execution_level`
20. Every addition must earn its place — §20 self-check above

## What this cost, accepted

- **A large, breaking rename** across the whole layer — every hardcoded
  reference in `test_process_router.py`, `workflow.md`, `decisions/`, docs
  needed updating in the same unit, not incrementally.
- **Objective 20 (backward-compatible) is not advanced by this unit.** No
  evidence any downstream repo installed a pre-merge copy — `../physrun/`
  is untouched and not assumed to have one — so no live migration path was
  built. If one is ever needed, it starts from this record, not from
  scratch.
- **The 2026-08-20 audit's naming verdict is superseded, not proven wrong.**
  Its reasoning holds as a general default; this unit is a documented,
  deliberate exception on explicit direction, not a correction.

## What is enforced rather than asserted

Every renamed/merged reference is checked by the existing suites
(`test_process_router.py`, `test_hooks.py`, `test_hook_standards.py`,
`test_agent_standards.py`, `test_portability_contract.py`,
`test_entry_classifier.py`, `test_install.py`, `test_package.py`) — updated
in the same unit, not left to prose. `python tools/run_checks.py --tier all
--require-test` is Task 9's gate.

## The option it beat

**Keep stage-shaped names, document a Notion crosswalk instead of
renaming.** This was the first plan drafted for this unit — lower risk,
zero blast radius, satisfies "align to Notion" via documented equivalence.
Rejected on explicit user direction after the tradeoff was stated plainly:
the user chose full rename over crosswalk-only, accepting the larger blast
radius for literal naming alignment.

**Build synthetic stub skills for every Notion category with no obvious
local use** (`data-analysis`, `refactoring`-as-code-editing). Rejected:
websearch confirmed both are real, common Claude Code skill categories with
genuine existing ad hoc equivalents in this repo (`no-slop` for refactoring;
`tools/bench.py`/telemetry analysis for data-analysis) — real content was
built from those, not placeholder stubs, consistent with §20's own
"skill explosion" warning.
