# Primary objectives

The standing brief this layer is graded against, alongside `GOAL_CHECKLIST.md`.

**Provenance.** Transcribed 2026-08-16 from the Notion page *Agentic Workflows
(IDE)*, supplied verbatim by the repository owner. It is reproduced here because
it was not: `HANDOFF.md` carried a verdict on these ten — 4 green, 3 amber,
3 red, dated 2026-08-15 — that nobody reading this repository could check, and
two published audits inherited grades whose criteria they had no access to. A
layer whose whole discipline is *prefer a mechanism over a written rule* was
being graded against a rule that lived somewhere else.

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

---

## Where each one is measured

Grades are worthless without the command that produced them. These are the
instruments; run them rather than quoting a remembered number.

| # | Instrument |
|---|---|
| 2, 3 | `python tools/bench.py` — per-session and per-turn character costs |
| 4, 5 | `python tools/bench.py`, from the counter in `.claude/hooks/post-tool/01-context-cost.py` |
| 6 | `python tools/bench.py` tier timings; `python tools/parallel_groups.py <plan>` |
| 7 | `model:` frontmatter across `.claude/skills/` and `.claude/agents/` |
| 8 | `.claude/hooks/user-prompt/01-entry-classifier.py` replayed over `docs/evals/trigger-queries.json` |
| 9 | `python tools/scope.py`; `_hooklib.FAILURE_BUDGETS` |
| 10 | `python tools/run_checks.py --tier all --require-test` |
| 1 | `python tools/test_process_router.py` — the two-gate ownership assertions |

**Last full audit: 2026-08-16 — 4 green (1, 6, 7, 9), 5 amber (3, 4, 5, 8, 10),
1 red (2).** The red is the per-turn description listing at 17,900 characters,
raised deliberately to buy triggering and not yet paid back.
