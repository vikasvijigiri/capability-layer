---
name: capability-layer-maintenance
description: Audit or repair the agent layer itself, and its governing contracts. Covers .claude/, CLAUDE.md, AGENTS.md, skills, subagents, hooks, slash commands, rules, settings.json and their validators. Triggers include "add a skill", "add a hook", "wire up a subagent", "the hook is not firing", "this skill never triggers", "the slash command is broken", "fix the layer", "audit .claude", or "the layer has drifted". Do NOT use for product code, product documentation, or a plain question about how the layer works. Use this whenever .claude/ is what changes.
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
  hooks, output styles, portability contract, host adapters, and capability
  validators.

`documentation` owns project knowledge: `README.md`, `TASK.md`,
`HANDOFF.md`, `MEMORY.md`, `LOG.md`, `ISSUES.md`, and `decisions/`. Hand off
those files when the requested change is project history or state rather than
the capability contract.

`refactoring` also reads `.claude/`, and the division is by **question, not by
directory**: it asks whether slop has accumulated and reports findings; this
skill asks whether the contract and its wiring are correct, and changes them. A
dead reference found by a sweep is reported there and repaired here. Running a
sweep is not maintenance, and neither is running the validators — `/verify`
resolves every one of them, so a command that re-runs a subset of them is a
second, weaker answer to a settled question.

`tools/test_process_router.py` fails if either skill stops naming the other. A
boundary held by one side's prose is one that drifts.

## Non-negotiable contract

1. Read `AGENTS.md`, `harnesses.json`, `CLAUDE.md`, `.claude/workflow.md`, and
   the applicable template/guide before changing the layer.
2. Keep `.claude/` as the only native source. Do not add a parallel
   `.agent-layer/`, generated source tree, routing keyword table, or duplicate
   registry that can drift.
3. Keep host-neutral capability requirements in
   `.claude/portability/capabilities.json` and host mappings in
   `.claude/adapters/`. A host-specific token in a skill must map through that
   contract for every declared adapter. An unverified bridge is not support.
4. Hooks may detect drift, enforce safety, or record mechanical state. Hooks
   must not author strategic content in `README.md`, `CLAUDE.md`, `AGENTS.md`,
   `TASK.md`, `HANDOFF.md`, `MEMORY.md`, `LOG.md`, `ISSUES.md`, `harnesses.json`,
   `workflow.md`, or decisions.
5. Preserve user changes, fail closed for secrets/destructive ambiguity, and
   never claim a live host execution from a dry-run.

## Procedure

### 1. Inventory

Count and inspect the canonical directories. Resolve every path named by prose,
settings, registries, workflow scripts, and tests. Search for deleted paths,
duplicate sources, stale counts, and ownership contradictions.

### 2. Compare

Compare the structure and content against the relevant files in `templates/`
and `guide/`. For a *new* skill or agent, also read
`references/adding-a-skill-or-agent.md` first — the repo-specific validator
rules and duplicated-count locations `templates/`/`guide/` don't cover,
each a real redo the hard way otherwise. Check frontmatter, routing,
handoffs, hook registration, tool allowlists, model/effort policy, and
harness paths. Score each unit **Keep**
(matches the template), **Repair** (a real deviation), **Extend** (an
intentional deviation — record the reason inline), or **Retire** (dead weight
nothing references).

One filled instance, so the taxonomy reads as a verdict rather than a label:
`documentation/SKILL.md`'s `when_to_use` field once carried a stray
`- formats.md` line folded into it by YAML's scalar-continuation rule —
**Repair**, because the deviation was an accidental copy-paste artifact, not a
documented extension.

When the request asks for a world-class or public-repository comparison, use
at least two primary repositories or official guides, read the relevant source
files rather than relying on stars or search snippets, and record the result in
`docs/research/YYYY-MM-DD-<topic>.md`. Compare invariants and mechanisms, not
copied wording. Keep static parity, local execution evidence, and live host conformance
as separate claims; external popularity is context, not proof.

### 3. Repair

Make the smallest coherent change in the canonical source. Update all explicit
registries, workflow tables, counts, tests, and references in the same change.
Do not make hooks silently rewrite contracts; use the skill for judgment-heavy
repairs and let hooks report the next action.

### 4. Verify

Run the scoped validator first, then the complete repository suite:

```text
python tools/run_checks.py --scoped
python tools/run_checks.py --tier all --require-test
```

For adapter or portability changes, run `python tools/test_portability_contract.py`.
It validates manifest completeness and honest status labels; it does **not**
prove a non-native host ran. Add and run a host-specific conformance command
before changing an adapter from bridge-required-unverified.

For hook changes, also run the relevant hook with a real payload and verify its
exit code, output, and filesystem diff. Prove that strategic files were not
authored by the hook.

### 5. Record

Hand the maintenance result to `documentation` for `LOG.md`, `HANDOFF.md`,
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
to this skill or `documentation`; it does not perform the update itself.

## Success

The canonical layer is internally consistent, all required harness paths exist,
hooks have a tested behavior classification, no strategic document was written
by a hook, and the complete validation suite is green.

## Routing

Use this skill for capability-layer maintenance, then hand durable project-state
updates to `documentation`. Do NOT use it as a substitute for product
planning, implementation, code review, or ordinary project documentation.
