# One workflow engine, and it is the Python one

**Date:** 2026-08-07
**Status:** accepted

## Context

Two implementations of the same SDLC contract existed side by side:

- `tools/resume.py` + `tools/loop.py` — derives state from git facts, decides the
  recovery rung, ~60 assertions across `test_resume.py` and `test_loop.py`.
- `.claude/workflows/feature-delivery.js` (101 lines) + `tools/run_workflow.mjs`
  (251 lines) — an in-memory state machine driven by a hand-rolled runtime.

Audited against `templates/workflow.md` and the official dynamic-workflow docs,
the JavaScript path had four problems:

1. **It could not be invoked.** The contract for a dynamic workflow is top-level
   code with `agent`/`pipeline` as runtime globals. It exported
   `run({ args, agent, pipeline })` instead, so `/feature-delivery` never
   existed, it never appeared in `/workflows`, and it got none of the runtime's
   concurrency caps or resume caching.
2. **A second budget table.** `BUDGETS = {transient, repair, reentry, conflict,
   rollback}` against `_hooklib.FAILURE_BUDGETS = {security, merge, transient,
   deterministic, unknown}`. Only `transient` overlapped by name. A
   `deterministic` failure fell through to `?? BUDGETS.repair` and happened to
   get 3 attempts, matching Python — by coincidence, not design, and nothing
   asserted it.
3. **Run state in memory.** `transitions[]` and `incidents[]` died with the
   process. `resume.py` re-derives from git and survives a crash, a `/clear`, or
   a different machine.
4. **Tested by a line count.** `test_workflow_standards.py` was 47 lines whose
   substantive assertion was `text.count("agent(") < 5`.

## Decision

Delete the JavaScript path: `feature-delivery.js`, `run_workflow.mjs`,
`test_workflow_runner.mjs`, `test_workflow_standards.py`, and its stale run
state. `package.json` stays with no dependencies so `npm audit` still resolves
for any JS a product adds later.

Harness neutrality — the reason the JS runtime existed — is unaffected.
`resume.py` and `loop.py` are plain scripts; Codex, Gemini and VS Code agents can
shell out to them exactly as Claude Code does.

## Consequences

- One engine, one budget table, one set of tests.
- The dynamic-workflow primitive is still available and still documented in
  `templates/workflow.md`. Nothing stops a future `.claude/workflows/*.js` — it
  just has to match the real contract, which this one never did.
- `npm audit` now audits zero dependencies. That is an honest report of this
  repo's JavaScript surface, not a weakened gate; the note is in `package.json`.

## What made this findable

`workflow.md` named `artifact-review` after that skill became a reference file,
and every suite stayed green — the resolution check only ever read `SKILL.md`
files. `test_process_router.py` now validates `workflow.md`'s own names too.
