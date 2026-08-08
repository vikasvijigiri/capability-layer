# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Current Work

Branch `rebuild-capability-layer`, **pushed** — `origin` is
`https://github.com/NG-VikasV/capability-layer.git` and the branch tracks
`origin/rebuild-capability-layer`. The canonical layer is `.claude/`; `AGENTS.md`
and `harnesses.json` define the harness-neutral contract. Workflow state is
derived, not stored — `tools/resume.py` reads it from git, and
`decisions/2026-08-07-derived-state-over-stored-state.md` says why.

**31 checks green across both tiers.** The slow tier has exactly one member,
`tools/test_package.py`, and it is the first thing that has ever verified an
artifact rather than the source that produced it.

## Completed (this cycle)

- **Distribution.** `pip install git+…` → `capability-layer install --into .`
  (alias `cl`). The package is a carrier, not a library: `.claude/` is copied into
  the target's working tree, because that is where hooks resolve and where a team
  reads the skills. Proven end to end by `test_package.py` — wheel → clean venv →
  fresh repo → that repo's own tier green.
- **`upgrade` that does not destroy local work.** Manifest v2 records sha256 per
  installed file, so an edited file is kept and named while an untouched one takes
  the upstream change. `--force` is how you say otherwise.
- **The layer can enter a repository it has never seen.** `repo-recon` +
  `tools/recon.py`, and a `RECON` state in `resume.py` — which previously answered
  `PLANNING` for any repo that had never used the layer, including this one after
  104 commits of finished work.
- **Concurrency is computed.** `tools/parallel_groups.py` derives rounds from a
  plan's declared `Files:`/`Depends on:` and refuses a plan rather than guessing.
  Replaced a flat "never two implementers at once".
- **Two gates, actually two.** `brainstormer` carried ten `AskUserQuestion` calls
  plus a prose "Ask, then wait"; they are `[NEEDS CLARIFICATION]` markers now,
  answered together at Gate 1. Each gate declares itself with a `<!-- GATE n -->`
  marker the suite checks.
- **Descriptions rewritten for triggering** — capability-first, ≥6 trigger
  phrases, proactive clause, no cross-skill phrase collisions. Four properties
  enforced, each proven red first.

## Pending

- **The chain has never completed once.** No approved plan has gone spec →
  release. Gate 1 has now fired once (the pip-package plan); Gate 2 never has.
  This is the single highest-value gap and one pilot closes most of it.
- **Trigger rates are unmeasured.** `tools/eval_triggers.py` holds 168 queries
  across all 14 skills, sandboxed and instrument-checked. No live run has been
  paid for (~$120 full, ~$20 sampled). Everything about triggering currently rests
  on properties the suite checks, not on a measured rate.
- **No subagent has ever completed a task.** The first fan-out — five
  `task-implementer` agents — failed because every worktree was based on `main`
  @ `4069f4b` rather than the working branch. `isolation: worktree` is unverified
  against *which commit* it bases on, and
  `executing-plans/references/parallel-dispatch.md` asserts a mechanism that has
  not worked yet.
- **`audit` is still `false`** and there is no e2e or smoke command, so the slow
  tier proves the package and nothing about a running system. `tools/smoke.py` has
  never probed a process.
- **`.claude/rules/llm-env.md`** loads every session mandating groq +
  `opengpt oss 120B` and a root `.env.example` that does not exist. Excluded from
  the payload so it cannot travel, still live here.
- Canary release (`release.yaml` thresholds, auto-rollback) is unbuilt on purpose
  — there is no deploy target, so every assertion would test a mock.
- One stale git worktree, `mutation-sweep-tmp`, pointing at a deleted temp path.

## Next Steps

1. **Run the pilot.** Install into the product repo and take one real feature
   through the chain. Everything in Pending above is speculation until that
   happens once.
2. Use `capability-layer-maintenance` for capability-layer contract changes, and
   `knowledge-manager` for README/TASK/HANDOFF/MEMORY/LOG/ISSUES/decisions.
3. `python tools/run_checks.py --tier all --require-test` before any completion
   claim. The slow tier needs ~400MB free or `test_package.py` skips — and says so.

## Open Questions

- Which product repository is the pilot? (Answered in principle — the layer is
  packaged for exactly this — but not yet named.)
- Which deploy target, if any, should be used for release verification? Until
  there is one, stage 9 `releasing` and Gate 2 stay untested.
- Should `refs/uaios/green/` and `UAIOS_AUTOCOMMIT_RUNNING` be renamed to match
  the package? Deliberately left alone: invisible to users, and renaming orphans
  every green ref already recorded here.
