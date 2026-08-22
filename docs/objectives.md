# Primary objectives

The standing brief this layer is graded against, alongside `GOAL_CHECKLIST.md`.

**Provenance.** Transcribed 2026-08-16 from the Notion page *Agentic Workflows
(IDE) — Universal Adaptive SDLC v2*, then re-fetched in full on 2026-08-20 via
the Notion MCP connector — the source had grown from 10 objectives to **30**
in the interim, plus 25 sections of target architecture (execution levels,
efficiency budgets, hook/skill/agent catalogues, telemetry schema, anti-
repetition layer) that the 2026-08-16 transcription never captured at all.
That gap is itself the finding this update exists to close: a copy that
silently falls behind its source is worse than no copy, and nobody reading
this repository could have known objectives 11-30 existed.

Notion remains the source. When it changes, change this file in the same unit
and say so in `LOG.md`; a copy that drifts is worse than no copy.

---

1. **Minimal human interference** — ask only when the system genuinely cannot
   proceed safely or correctly.
2. **Minimal tokens** — use the minimum necessary prompt, context, reasoning,
   skill instructions and agent output.
3. **Minimal context** — retrieve only relevant information, just in time; never
   dump the repository or history into context.
4. **Minimal API/tool/MCP calls** — maximize useful work per call, batch
   independent requests, reuse existing results and avoid redundant calls.
5. **Minimal repetitive work** — never rediscover, reread, re-reason or
   regenerate information already available and still valid.
6. **Minimal latency** — avoid unnecessary serial stages and parallelize only
   when the latency benefit exceeds coordination cost.
7. **Minimal compute/cost** — use the cheapest capable model, agent and tool
   path.
8. **Maximum efficiency** — select the minimum-sufficient execution graph.
9. **Maximum quality** — increase reasoning, specialization and verification
   only when evidence/risk justifies it.
10. **Maximum reliability** — deterministic controls for deterministic
    requirements; adaptive intelligence only where intelligence is required.
11. **World-class engineering** — practices, architecture, validation,
    observability and operational discipline consistent with high-performing
    production engineering organizations.
12. **Production-grade by default** — robust, testable, observable,
    maintainable, secure, deployable, unless the task explicitly calls for a
    prototype.
13. **Universal / generic** — never assume a specific repository, language,
    framework, architecture, domain, team convention or project maturity
    unless discovered or provided.
14. **Portable** — useful when installed, copied or introduced into any
    compatible repository regardless of its structure, tooling or stage.
15. **Stage-agnostic** — correct on greenfield, partial, legacy, broken,
    undocumented, active or near-release repositories.
16. **Repository-agnostic** — discover structure, conventions, dependencies,
    tooling, architecture and constraints before assuming or changing.
17. **Non-destructive integration** — coexist with existing workflows;
    preserve working behavior; avoid unnecessary restructuring.
18. **Adaptive, not prescriptive** — detect maturity, risk and state, then
    choose the workflow rather than forcing every project through one process.
19. **Idempotent and repeatable** — repeated execution converges without
    duplicating work, corrupting artifacts or introducing inconsistency.
20. **Backward-compatible where practical** — preserve contracts, interfaces
    and behavior unless a deliberate, justified breaking change is required.
21. **Secure by default** — minimize secrets exposure, privilege, attack
    surface, unsafe tool usage and accidental data leakage.
22. **Observable and auditable** — every meaningful decision, change,
    verification result and failure traceable, without excessive logging.
23. **Evidence-driven** — assumptions explicit, important claims validated
    against evidence, discovered facts distinguished from inferred ones.
24. **Self-adapting and self-healing** — detect, diagnose locally, repair when
    safe, re-verify, escalate only when current capability is insufficient.
25. **Technology-agnostic** — languages, frameworks, build systems, package
    managers, deployment models and layouts, without hardcoded assumptions.
26. **Low-coupling / composable** — each capability independently usable,
    replaceable and reusable; no unnecessary dependency on one path.
27. **Progressively adoptable** — value when dropped into an existing
    repository without requiring a rewrite, reorganization or migration first.
28. **Safe under uncertainty** — inspect and establish evidence before
    acting; never compensate for uncertainty with arbitrary assumptions.
29. **No hardcoded project truth** — project-specific facts discovered,
    configured or learned, never embedded into universal workflow logic.
30. **Continuous improvement without instability** — learn from validated
    telemetry while preventing noisy, speculative or unverified learning from
    changing core behavior.

> **Prime Directive:** every token, context item, API call, tool call, skill,
> agent, workflow stage, verification step and human interruption must
> justify its existence. *The best agentic IDE is not the one that uses the
> most agents. It is the one that reliably knows when NOT to use them.*

---

## Where each one is measured

Grades are worthless without the command that produced them. These are the
instruments; run them rather than quoting a remembered number.

| # | Instrument |
|---|---|
| 2, 3 | `python tools/bench.py` — per-session and per-turn character costs |
| 4, 5 | `python tools/bench.py`, from the counters in `context-budget/01-context-cost.py`, `context-budget/02-skill-cost.py` and `post-tool/06-tool-cost.py` (total tool calls, every tool name) |
| 6 | `python tools/bench.py` tier timings; `python tools/parallel_groups.py <plan>`; `09-telemetry.py`'s `turn_latency_seconds`, from `prompt-intake/02-turn-timer.py` |
| 7 | `model:` frontmatter across `.claude/skills/` and `.claude/agents/` |
| 8 | `.claude/hooks/prompt-intake/01-entry-classifier.py` replayed over `docs/evals/trigger-queries.json` |
| 9 | `python tools/scope.py`; `_hooklib.FAILURE_BUDGETS` |
| 10 | `python tools/run_checks.py --tier all --require-test` |
| 1 | `python tools/test_process_router.py` — the two-gate ownership assertions; `09-telemetry.py`'s `human_interventions` field, from `post-tool/07-human-cost.py` (live rate, `AskUserQuestion`/`ExitPlanMode` counts) |
| 9, 10 | `09-telemetry.py`'s `retries` field, surfacing `tools/resume.py`'s `attempts`/`max_attempts`/`failure_class` and `tools/loop.py`'s `rung()` verdict per turn |
| 14 | `python tools/test_install.py`, `python tools/test_package.py` — fresh install into a Python and Node target |
| 21 | `python tools/security_gate.py`, `python tools/deps.py` (licence gate), `permission-security/*` hooks |
| 23 | `testing`'s HARD-GATE (no completion claim without fresh, quoted evidence) |
| 28 | `[NEEDS CLARIFICATION]` markers in `task-analysis`; `EnterPlanMode`/`ExitPlanMode` gate |
| 30 | `tools/bench.py --save` baselines; `decisions/` records (e.g. `budget.ELAPSED_CEILING_HOURS` deliberately not refit from one noisy measurement) |
| 18 | `tools/test_entry_classifier.py`'s full-corpus route-presence check (`entry-small`/`entry-direct` both confirmed reachable) plus a fallback-safety check on `01-entry-classifier.py`'s `_control_or_sensitive_patterns()` |
| 22 | `python tools/bench.py`'s `schema_coverage()` — `09-telemetry.py`'s own `unavailable` map against its `SPEC_FIELD_COUNT`, plus `chain.fingerprint` trace-completeness |
| 24 | `python tools/bench.py`'s `local_repair_ratio()` — incident-deduplicated aggregate over `telemetry.jsonl`'s `retries.rung` history |
| 19 | `python tools/test_idempotence.py` — install-twice byte-level tree delta, plus stateless decision-hook (`pre-edit`/`permission-security`/`pre-tool`) determinism across two identical firings |
| 17 | `python tools/test_preservation_rate.py` — fraction of a fixture target's own pre-existing files that survive an install byte-identical |
| 20 | `python tools/test_contract_surface.py` against `.claude/contracts/layer-contract.golden.json` — skill/hook/capability/project-checks surface plus a two-tier stable/unstable telemetry-field split |

Objectives 11, 12, 13, 15, 16, 25, 26, 27, 29 (Clusters A and D) have no
dedicated instrument yet on this branch — see `docs/research/
2026-08-20-notion-objectives-audit.md` for a qualitative first pass and
what would make each one measurable, and `docs/specs/2026-08-21-
qualitative-objective-metrics.md` for the design that closed 18, 22, 24
(Cluster C) and 17, 19, 20 (Cluster B) here, plus the plan for Clusters A
and D (D built independently on `feat/cluster-d-layer-self-grading`, not
yet merged to this branch). (Cluster C's own closure edit left `22` and
`24` in this line despite already having rows above — corrected here
alongside the Cluster B removal.)

**Last full quantitative audit: 2026-08-22 — 5 green (1, 7, 8, 9, 10), 5 amber
(2, 3, 4, 5, 6), 0 red**, against objectives 1-10 only — see
`docs/research/2026-08-22-objectives-1-10-requant.md` for the exact command
and number behind each grade. Real movement since the 2026-08-16 pass (4
green / 5 amber / 1 red): objective 2 moved red -> amber (skill-metadata
listing cost cut ~26%) and objective 8 moved amber -> green (the E0-E5
router now matches the labelled corpus, not just asserted). Objectives 11-30
are still only the 2026-08-20 qualitative pass
(`docs/research/2026-08-20-notion-objectives-audit.md`) — not re-run here.
