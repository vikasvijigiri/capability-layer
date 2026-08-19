# Skill quality: `verifying-work` vs affaan-m/ECC

Compares `.claude/skills/verifying-work/SKILL.md` (185 lines) against the
closest real comparables in [affaan-m/ECC](https://github.com/affaan-m/ECC), a
large public multi-skill Claude Code repo.

## Comparables read in full

- `skills/verification-loop/SKILL.md` (~100 lines) — the direct generic
  analog: a 6-phase mechanical checklist (build, typecheck, lint, test+coverage,
  security grep, diff review) ending in a fixed-format `VERIFICATION REPORT`
  block.
- `skills/django-verification/SKILL.md` (~250 lines) — the same shape
  specialized for Django: 12 phases (env, quality, migrations, tests+coverage
  targets by component, security scan, management commands, performance,
  static assets, settings audit, logging, API docs, diff review), a fully
  rendered worked-example report, a pre-deployment checklist, and a GitHub
  Actions YAML.

## Gaps in ours (concrete, with fixes)

1. **No worked example of a filled verdict.** Ours describes the coverage
   table abstractly ("Report as a table: requirement | evidence | verdict")
   but never renders one with real rows. `django-verification`'s "Output
   Template" section shows a complete report with actual numbers ("Tests: 247
   passed, 0 failed, 5 skipped", "Coverage: 87%", per-phase ✓/✗). Same gap
   found earlier in `writing-plans` vs `plan.md` and `delivering` vs `pr.md` —
   a pattern across this layer's skills. Fix: add one small worked example
   showing 2-3 rows of a real requirement→evidence→verdict table.
2. **No baseline check categories independent of the project's own suite.**
   Ours delegates the mechanical half entirely to `tools/run_checks.py`
   (`--scoped` / `--tier all`) — good for genericity, but if that suite is
   thin or misconfigured (e.g. no secrets scan), the skill offers no fallback.
   ECC's `verification-loop` enumerates fixed baseline phases (a
   `grep -rn "sk-"` / `api_key` secrets pass, a `console.log` sweep, a
   `git diff --stat` review) that run regardless of what the project's own
   tooling covers. Fix: name a minimal fallback phase list (secrets grep,
   diff-stat review) for when `run_checks.py` doesn't already cover them.

## Where ours is stronger (confirmed by reading the source)

1. **Coverage-against-brief is the deliverable; ECC never does this at all.**
   Both ECC files are entirely mechanical — build/type/lint/test/security/diff
   — and stop at "do the checks pass." Neither ever maps a requirement from a
   brief, spec, or plan to evidence, and neither produces an "unbacked set."
   Ours makes this the explicit second question ("Was every asked-for thing
   delivered?") and states plainly that a green suite answers a different
   question than coverage does — a distinction ECC's report format has no
   place for.
2. **Fresh-evidence enforcement has no ECC counterpart.** Ours has a
   HARD-GATE plus a "Red Flags" list naming exact failure phrases ("should
   work now", "quoting a run from earlier in the session"). Neither ECC file
   says anything about re-running versus trusting a stale/previous run.
3. **Regression tests must be proven capable of failing.** Ours requires
   revert → confirm FAIL → restore → confirm PASS before a regression test
   counts as evidence. ECC treats "tests pass" as sufficient on its own —
   neither file mentions verifying a test can fail.
4. **Verification is kept separate from fixing.** Ours calls out "fixing gaps
   inside verification" as a Common Mistake (the evidence then describes a
   tree that no longer exists). `verification-loop`'s Phase 1 says the
   opposite: "If build fails, STOP and fix before continuing" — mixing the
   two exactly where ours warns not to.
5. **Explicit routing and independent re-verification.** Ours routes
   Verified/Gaps/Blocked to different next skills (`no-slop`, `code-review`,
   `systematic-debugging`, back to planning) and dispatches `test-verifier`
   for material changes. ECC's "Continuous Mode" is a prose aside ("Set a
   mental checkpoint... Run: /verify") with no subagent dispatch and no
   verdict routing.

## Verdict

ECC's comparables are tighter, more copy-pasteable mechanical scripts with a
concrete rendered report (django-verification especially); ours is the one
actually built to answer whether the work matches what was asked, with
tool-enforced freshness and an honest unbacked/unverifiable split that ECC's
report format has no category for.
