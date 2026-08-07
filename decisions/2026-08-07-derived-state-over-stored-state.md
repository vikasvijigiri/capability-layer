# Derived state over stored state

**Date:** 2026-08-07
**Status:** accepted

## Context

`.claude/workflow.md` described a 21-state workflow machine, an incident schema
with `attempt`/`maxAttempts`, and six recovery budgets. A grep for the state
names across every `.py`, `.json` and `.md` in the repository returned exactly
one file — `workflow.md` itself. No hook wrote to it, no tool read it, no suite
asserted it. The layer had a state machine in the same sense that a repo has a
test suite when the file is empty.

Two proposals arrived to formalise it further, both adding structure on top of
the prose rather than under it.

## Decision

State is **derived from git**, never stored:

- `tools/resume.py` gathers facts (plan file, approval marker, clarification
  markers, branch, green ref, PR labels) and `derive_state` maps them to one of
  ten states. The mapping is a pure function; its priority order is the policy.
- One slug ties `docs/plans/*-<slug>.md`, `feat/<slug>`,
  `refs/uaios/green/<slug>` and the PR head together.
- The only thing persisted is an attempt counter in
  `.claude/hooks/state/resume-<slug>.json`, because a count of past attempts is
  not a fact about the tree and git cannot hold it.

Failures are classified by a table before any budget is spent
(`_hooklib.FAILURE_CLASSES`), and `tools/loop.py` maps class plus attempt onto
one of six rungs, the last two of which are terminal.

## Consequences

Resume survives what memory does not: a cleared context, a crash mid-repair, a
new session a week later, a fresh clone. There is no counter to reset and no
document to keep in sync, so the class of bug where the notes disagree with the
repository cannot occur.

The cost is that every state must be observable. A state that is only in
someone's head cannot be derived, so states like "the design feels wrong" have
no representation — which is correct, because those are Gate 1's business, not
the loop's.

`workflow.md`'s prose state machine is now redundant with working code. It
should be cut to what the code does not cover rather than left as a second,
unenforced description — the exact failure this decision is about.

## Alternatives rejected

**Persist a run-state JSON per unit.** This is what the rejected proposals
implied. It reintroduces the desync class of bug, needs its own migration story,
and every crash risks a half-written file at the moment recovery matters most.

**Keep the prose and add a validator that the model must follow.** Tried in this
repo repeatedly. `post-run/05-docs-gate.py` blocked a turn until a skill ran,
deadlocked, and was deleted on 2026-08-02. A rule the model must remember is not
a mechanism.

See also [[2026-08-04-hooks-never-name-a-skill]].
