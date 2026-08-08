# Baseline campaign: capability-layer audit

Date: 2026-08-06
Scope: `.claude/` skills, hooks, agents, commands, workflow, configuration, and
their repository validators.

## Task

Audit the capability layer for a clean, harness-agnostic SDLC handoff and repair
the defects found. The same repository state and the same check commands were
used for both conditions.

## Control condition — without skill procedures

The control used only the repository's existing mechanical checks and a direct
file listing. It did not apply the individual skill checklists, explicit routing
handoffs, or external-registration review.

Observed results:

- The main test/check configuration did not require the repository's standalone
  test scripts, so a green configured run did not cover all available tests.
- `tools/test_hook_registration.py` exposed a dangling external
  `SessionStart` registration for the deleted
  `global-session-start/01-layer-bootstrap.py`.
- The layer contained stale inventory wording and 15 skills had no dated
  baseline record.

These are recorded findings from the control run, not predictions about what it
would have found.

## Treatment condition — with skill procedures

The treatment applied the relevant skill contracts and workflow gates: task
briefing, artifact/spec review, isolated execution expectations, verification,
no-slop, code review, security review for trust-boundary configuration, and
delivery/release handoff. It then reran the complete validator set.

Repairs and measured results:

1. Removed the confirmed stale external hook registration while preserving the
   remaining user settings. The hook-registration suite now reports 10 scripts,
   10 wired, and 10 declared, with no dangling local registration.
2. Added all eight standalone test scripts to `.claude/project-checks.json` and
   reran `python tools/run_checks.py --tier all --require-test`: **12/12 checks
   passed**.
3. Corrected stale skill-count and hook-wiring documentation.
4. Added individual baseline records for the 15 previously uncovered skills;
   records distinguish positive deltas from negative or non-applicable results.
5. Reran the full layer checks: 16 skills, 5 agents, 10 hooks, 6 events, valid
   JSON configuration, session-start contract, reference resolution, no-slop,
   Ruff, and mypy all passed.

## Delta and cost

| Measure | Without skill procedures | With skill procedures |
|---|---:|---:|
| Required configured checks | incomplete test inventory | 12/12 green |
| Dangling external hook | present | removed and verified |
| Stale inventory claims | present | corrected and rescanned |
| Baseline coverage | 1/16 skills | 16/16 skills |
| Evidence quality | mechanical only | mechanical + routing + handoff + content review |

Cost: one audit campaign and one complete rerun of the checks; no production
systems or live deployment were touched. This is evidence for the capability
layer and not a claim that every future application change will have the same
delta.

## Interpretation

The campaign demonstrates measurable value for workflow/configuration work. It
does not prove universal superiority of every skill on every task; the per-skill
records below retain that limitation rather than overstating confidence.
