# Objectives 1-10 — full quantitative re-audit, 2026-08-22

**Asked because:** the last full quantitative pass was 2026-08-16 (`docs/objectives.md:123`), now 9+ days and several commits stale (E0-E5 router built, skill-metadata deduplicated, telemetry `run_id`/predicted-vs-actual fixed). Re-run every instrument fresh rather than trust the old grades.

**Verdict:** 5 green (1, 7, 8, 9, 10), 5 amber (2, 3, 4, 5, 6), 0 red. Real movement since 2026-08-16 (`4 green / 5 amber / 1 red`): objective 2 moved **red → amber** and objective 8 moved **amber → green**. Nothing regressed.

## Findings

| # | Objective | Grade | Evidence (command + number) |
|---|---|---|---|
| 1 | Minimal human interference | **Green** | `tools/test_process_router.py`: all two-gate ownership assertions pass (`task-analysis` declares+calls `ExitPlanMode`, `release-git` declares+calls `AskUserQuestion`, no other skill prompts). Live: latest `telemetry.jsonl` row, `human_interventions: {calls: 107, AskUserQuestion: 57, ExitPlanMode: 50}` — real gate usage tracked, not just asserted. |
| 2 | Minimal tokens | **Amber** (was Red 2026-08-16) | `python tools/bench.py`: skill/cmd/agent listing **13,751 ch (~3,437 tok)/turn** — this session's own fix (merging `when_to_use` into `description` across 14 skills) cut this from an 18,646-ch baseline measured earlier the same session, a real ~26% reduction on the one guaranteed-every-turn cost line. Upgraded from Red because the worst-offending, always-paid cost dropped measurably; not Green because no formal target exists to grade against, and skill-body reload cost remains large in absolute terms on a long session (340 calls, ~599K tok cumulative — expected for this session's length, not a steady-state number). |
| 3 | Minimal context | **Amber** | `CLAUDE.md`+rules 9,681 ch, SessionStart output 4,779 ch, both once-per-session. No dedicated instrument proves "just-in-time" retrieval beyond character counts; unchanged from 08-16. |
| 4 | Minimal API/tool calls | **Amber** | `tools/bench.py`: 1,226 total tool calls across 19 distinct tools this session. Now genuinely measured (was "asserted but never graded" before 2026-08-21's instrumentation) — real evidence exists, but no per-task efficiency target exists to compare a raw count against, so this stays Amber rather than Green. |
| 5 | Minimal repetitive work | **Amber** | `tools/bench.py`: duplicate rate **9% (142/1,494)**. The detection *mechanism* was fixed this session (`01-context-cost.py`'s `VOLATILE` cd-prefix bug — legitimately-exempt re-runs were miscounted as repeats), but the cumulative session total was already contaminated by the pre-fix counting and won't reflect the fix until a fresh session accumulates calls under the corrected logic. Real mechanism fix, not yet a real number improvement — stated as both, not conflated. |
| 6 | Minimal latency | **Amber** | Fast tier measured 86.9s this run; `tools/bench.py`'s own docstring states seconds drift ~2x across runs on an unchanged tree and must be compared interleaved, which this pass did not do. `parallel_groups.py` used correctly in both of this session's multi-task plans (concurrency computed, not assumed). Mechanism present and used; the timing number itself is not a clean comparison this pass. |
| 7 | Minimal compute/cost | **Green** | `grep "^model:" .claude/skills/*/SKILL.md .claude/agents/*.md`: 22 files, every value one of `opus`/`sonnet`/`haiku`, no invalid tier. Matches "cheapest capable model" per-skill assignment. |
| 8 | Maximum efficiency | **Green** (was Amber 2026-08-16) | `python tools/test_entry_classifier.py`: `OK: the entry predicate matches the labelled corpus`, plus all 9 E0-E5 estimator unit cases pass including the specific E4/E5-inversion regression case. Upgraded from Amber because the E0-E5 router (Gap A in the 2026-08-20 audit) is now built, tested, and matches the labeled corpus — not asserted, verified. |
| 9 | Maximum reliability (deterministic gating) | **Green** | `python tools/test_scope.py`: `All scope tests passed (5 clauses, 3 risk tiers)`. `FAILURE_BUDGETS` present in `_hooklib.py:594` and consumed by `rung()`. |
| 10 | Maximum reliability (verification) | **Green** | `python tools/run_checks.py --tier all --require-test`: `PASS: 55 check(s) green (audit, build, lint, smoke, test, typecheck)`, run fresh this pass. |

## Disagreements

None — single-pass instrument run, no conflicting sources.

## Not adopted

- Did not attempt an interleaved before/after timing comparison for
  objective 6 this pass — `bench.py`'s own warning against comparing
  single-run wall-clock numbers across different times was taken at
  face value rather than worked around, since no specific latency
  regression was being investigated.
- Did not re-grade objectives 11-30 — the 2026-08-20 qualitative pass
  (`docs/research/2026-08-20-notion-objectives-audit.md`) still stands
  as the last word there; this pass was scoped to 1-10 only, per what
  was asked.

## Sources

- `python tools/bench.py` (run fresh this pass)
- `python tools/test_entry_classifier.py` (run fresh)
- `python tools/test_scope.py` (run fresh)
- `python tools/test_process_router.py` (run fresh, grepped for gate assertions)
- `python tools/run_checks.py --tier all --require-test` (run fresh)
- `.claude/hooks/state/telemetry.jsonl` (last row, read fresh)
- `grep "^model:" .claude/skills/*/SKILL.md .claude/agents/*.md` (run fresh)
- `docs/objectives.md` (read for the 2026-08-16 baseline grades and instrument table)
