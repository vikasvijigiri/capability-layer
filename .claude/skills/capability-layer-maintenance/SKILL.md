---
name: capability-layer-maintenance
description: Audit or repair the agent layer itself. Covers .claude/, CLAUDE.md, AGENTS.md, skills, agents, hooks, commands, rules and validators. Triggers include "add a skill", "the hook is not firing", "fix the layer", "audit .claude", "this skill never triggers", "wire up a subagent", "the layer has drifted". Do NOT use for product code, product docs, or a plain question about how the layer works. Use this whenever .claude/ is what changes.
when_to_use: when the agent layer or its governing contracts need audit, repair, migration, or ownership clarification
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Capability-layer maintenance

Treat `.claude/` as the only canonical runtime source. Treat `AGENTS.md` and
`harnesses.json` as the harness-neutral contract. Generated projections,
duplicated routing tables, and hook-emitted strategic prose are not sources of
truth.

## Ownership

This skill owns the capability contract and its wiring:

- `CLAUDE.md`, `AGENTS.md`, and `harnesses.json`;
- `.claude/workflow.md`, settings, rules, skills, agents, commands, workflows,
  hooks, output styles, and capability validators.

`knowledge-manager` owns project knowledge: `README.md`, `TASK.md`,
`HANDOFF.md`, `MEMORY.md`, `LOG.md`, `ISSUES.md`, and `decisions/`. Hand off
those files when the requested change is project history or state rather than
the capability contract.

## Non-negotiable contract

1. Read `AGENTS.md`, `harnesses.json`, `CLAUDE.md`, `.claude/workflow.md`, and
   the applicable template/guide before changing the layer.
2. Keep `.claude/` as the only native source. Do not add a parallel
   `.agent-layer/`, generated source tree, routing keyword table, or duplicate
   registry that can drift.
3. Hooks may detect drift, enforce safety, or record mechanical state. Hooks
   must not author strategic content in `README.md`, `CLAUDE.md`, `AGENTS.md`,
   `TASK.md`, `HANDOFF.md`, `MEMORY.md`, `LOG.md`, `ISSUES.md`, `harnesses.json`,
   `workflow.md`, or decisions.
4. Preserve user changes, fail closed for secrets/destructive ambiguity, and
   never claim a live host execution from a dry-run.

## Procedure

### 1. Inventory

Count and inspect the canonical directories. Resolve every path named by prose,
settings, registries, workflow scripts, and tests. Search for deleted paths,
duplicate sources, stale counts, and ownership contradictions.

### 2. Compare

Compare the structure and content against the relevant files in `templates/`
and `guide/`. Check frontmatter, routing, handoffs, hook registration, tool
allowlists, model/effort policy, and harness paths. Separate a real deviation
from an intentional extension and record the reason for the latter.

### 3. Repair

Make the smallest coherent change in the canonical source. Update all explicit
registries, workflow tables, counts, tests, and references in the same change.
Do not make hooks silently rewrite contracts; use the skill for judgment-heavy
repairs and let hooks report the next action.

### 4. Verify

Run the scoped validator first, then the complete repository suite:

```text
python tools/run_checks.py --tier all --require-test
```

For hook changes, also run the relevant hook with a real payload and verify its
exit code, output, and filesystem diff. Prove that strategic files were not
authored by the hook.

### 5. Record

Hand the maintenance result to `knowledge-manager` for `LOG.md`, `HANDOFF.md`,
`ISSUES.md`, `MEMORY.md`, or `decisions/` updates. Include before/after counts,
files changed, validator output, and remaining live-host limitations.

## Hook contract

Each hook must declare one of these behaviors in its module docstring and test:

- **detect drift** — read-only checks and actionable reports;
- **enforce safety** — allow/deny decisions with fail-closed handling;
- **record state** — checkpoints or mechanical measurements in ignored state;
- **never author strategic content** — no writes to the contract or knowledge
  documents listed above.

When a hook needs a document update, it emits the evidence and hands the work
to this skill or `knowledge-manager`; it does not perform the update itself.

## Success

The canonical layer is internally consistent, all required harness paths exist,
hooks have a tested behavior classification, no strategic document was written
by a hook, and the complete validation suite is green.

## Routing

Use this skill for capability-layer maintenance, then hand durable project-state
updates to `knowledge-manager`. Do NOT use it as a substitute for product
planning, implementation, code review, or ordinary project documentation.
