# Hooks never name a skill

Date: 2026-08-04

## Decision

A hook measures state and acts on it. It never names a skill in anything it
emits. Where a fact needs a consequence, the hook renders it from
`.claude/workflow.md`, which already owns which skill owns which stage.

Enforced, not asserted: `tools/test_hook_registration.py` AST-parses every hook,
collects its emitted string constants, and fails if any contains a skill
directory name. Docstrings and comments are exempt — they never reach a session.

Deleted rather than rewired: `pre-run/05-process-skill-router.py`,
`post-run/07-layer-drift.py`, `pre-compact/01-knowledge-staleness.py`,
`routing/process-skills.md`.

## Why

11 of 13 skills were named inside hook source and nothing validated any of it. A
hook was pointed at `skill-that-was-deleted` and four suites — referenced-paths,
process-router, no-slop, hook-registration — all passed. In a repo whose stated
worst failure mode is a name resolving to nothing, that is the failure mode
itself, sitting in the mechanism layer.

The deeper problem is duplication of a routing decision. `workflow.md` says which
skill owns a stage. A hook saying "run `no-slop`" is a second copy of that, in a
file no routing test reads, in a language where it is a string literal.

## The option it beat

`.claude/routing/events.md` plus `_hooklib.nudge(event, facts)` — hooks emit an
event key, a table maps keys to skills, a test validates the table. Built, then
reverted the same session.

It fixes the *validation* gap and leaves the *coupling*: the hook still exists
only to cause a skill to run, and the layer still has two files that must agree
about what a stage means. Deleting the couplers is strictly less machinery and
removes the class rather than guarding it. A table with four entries guarding a
decision that `workflow.md` already states is a second source of truth wearing a
test as a disguise.

## What it costs, accepted

- **`no-slop` and `knowledge-manager` lose their prompts.** Partially recovered by
  `session-start/03-state-report.py`, which reports the facts and renders
  `workflow.md`'s `[state:<key>]` block — but only at session start, not per turn.
- **A `description:` that misses a phrasing has no second signal.** The keyword
  table was the backstop against skill-listing truncation. This is not recovered,
  and the only levers left are `skillListingMaxDescChars` and
  `skillListingBudgetFraction`.

## Prior art

mindfold-ai/Trellis renders per-turn breadcrumbs exclusively from `workflow.md`
tag blocks and states in the hook's own docstring that it keeps no fallback dicts,
so a missing tag degrades visibly rather than being masked. pedrohcgs/
claude-code-my-workflow injects facts plus generic recovery actions on
compact/resume and names no skill. Anthropic's own guidance draws the line at
determinism — *"the model choosing to run a formatter is different from the
formatter running automatically"* — which puts measurement in a hook and the
decision in an instruction file.
