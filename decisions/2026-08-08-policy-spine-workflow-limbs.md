# Policy is the spine; a dynamic workflow is a limb

**Date:** 2026-08-08
**Status:** accepted
**Amends:** `2026-08-07-one-workflow-engine.md` (does not reverse it)

## Context

`2026-08-07-one-workflow-engine.md` deleted a JavaScript workflow and said
plainly what would make a future one acceptable: *"Nothing stops a future
`.claude/workflows/*.js` — it just has to match the real contract, which this one
never did."* This is that future one, and the four reasons the last was deleted
are the specification for it.

What forced the question was a measured failure, not a preference. `README.md`
carried *"No subagent has ever completed a task"* because the first real fan-out —
five `task-implementer` agents dispatched in one message, exactly as
`parallel_groups.py` licensed — put every agent in a worktree based on the initial
commit rather than the working branch. Three returned BLOCKED with accurate
diagnoses, two wrote into stranded trees, and the round was salvaged by hand.

The dispatch instruction lived in a skill: *"dispatch one task-implementer per
task, all in the SAME message."* That is a rule the model has to remember and
execute correctly, which is the weakest mechanism this repository recognises.

## Decision

Two engines, on different axes, and the axis is what decides which:

| | Policy — `workflow.md` + `resume.py` + `loop.py` | Dynamic workflow — `.claude/workflows/*.js` |
|---|---|---|
| Lifetime | days; survives a crash, `/clear`, another machine | one turn |
| Sequencing | the model, reading a contract | the script, deterministically |
| State | derived from git; nothing stored | in-memory for the run |
| Harness | any host shells out to a Python script | Claude Code only |

**The scoping rule: if losing the run loses information, it belongs in the
policy. If losing the run only costs time, a workflow is fine.**

A parallel implementation round passes that test — the plan's checkboxes and git
are the record, and `resume.py` re-derives from them — so
`.claude/workflows/execute-rounds.js` executes rounds and nothing else.

The three substantive failures of the last attempt are designed out:

1. **Shape.** `export const meta` plus top-level code, which is the contract.
   Not `export default function run({...})`, which is why the last one never
   appeared as a command and nothing errored.
2. **One budget table.** The script carries no budgets and no ladder. It returns
   statuses; `tools/loop.py --agent-status` decides the rung, in the single place
   `_hooklib.FAILURE_BUDGETS` lives. Last time a `deterministic` failure got the
   right number of attempts by coincidence.
3. **No durable state.** Nothing is written. Acceptable only because nothing here
   *is* durable state — see the scoping rule.

The fourth failure was being tested by a line count.
`tools/test_workflow_contract.py` asserts the shape, the absent budget table, the
forbidden runtime APIs, and that every literal `phase()` has a `meta` entry. Each
check was proven red against a deliberately-wrong script before being relied on.

## Consequences

- **Harness neutrality is dented, deliberately and narrowly.** A dynamic workflow
  is Claude Code only, so `AGENTS.md`'s contract no longer covers this one path.
  Tolerable because it is an *optimisation*: the policy path still works on Codex,
  Gemini and VS Code agents, and a host without workflows loses parallel dispatch
  rather than the chain.
- The workflow cannot read the plan or run Python — no filesystem, no subprocess.
  The schedule is computed outside by `parallel_groups.py` and passed as `args`,
  which is the hybrid the tool's own guidance recommends.
- `.claude/workflows/` exists again. The contract suite fails on a directory
  holding non-`.js` leftovers, so it cannot decay into something that looks like
  a capability and is not.

**Corrected 2026-08-16.** The line above read *"the contract suite fails on an
empty one"* and that was never what the suite did:
`test_workflow_contract.py:80` asserts `bool(scripts) or not
any(WORKFLOWS.iterdir())`, so a **fully empty** directory passes and an
absent one is explicitly a valid state. `execute-rounds.js` was deleted this
same day and the directory removed with it — the policy spine (`resume.py` +
`loop.py`) has been the only engine since 2026-08-07. Nothing about this
decision changes; only the sentence describing the guard, which asserted a
stricter check than exists and would have blocked a correct cleanup.

## What is still unproven

`execute-rounds.js` has **not been run.** It is shaped correctly and validated
statically; whether `isolation: worktree` bases a worktree on the working branch —
the defect that broke the manual fan-out — is a runtime property this cannot
assert. The first real invocation is the test, and it belongs in the pilot.
