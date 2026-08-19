# Universal agent operating contract

This file is the harness-neutral entry point for any coding agent working in
this repository. A harness may add its own adapter instructions, but it must
preserve these invariants.

## Before acting

1. Read this file and `TASK.md` when present.
2. Read the relevant design, specification, plan, and acceptance evidence.
3. Inspect the repository's existing conventions before inventing new ones.
4. State assumptions when requirements are incomplete.

## SDLC contract

Use the smallest applicable path:

```text
brief → design → plan → implement → verify → clean → review → deliver → release → record
```

Do not skip verification for a completion claim. Do not push, merge, publish,
deploy, or spend money without explicit approval. Keep changes within scope,
preserve user changes, and report failures as failures.

## Capability adapters

`.claude/` is the only repository-native source of truth for skills, agents,
commands, workflow policy, rules, hooks, settings, output styles, memory, and
workflow state. Every declared host must follow the complete path map in
`harnesses.json`. Claude Code consumes `.claude/` natively; Codex and generic
agents must read or project from `.claude/` without
creating a second, untracked source of truth.

No generated adapter directory is required. Hosts must consume or project the
canonical `.claude/` content directly.

Hosts that cannot auto-discover Claude lifecycle hooks must invoke the canonical
checks under `.claude/hooks/` through their own lifecycle API. This repository
ships a native Claude Code adapter plus canonical source paths for Codex and a
generic agent; it does not claim native lifecycle registration for arbitrary
IDE extensions. A null or absent native hook registration must not be
interpreted as an absent hook contract. `docs/harness-hook-bridge.md` is the
exact invocation contract for doing this — payload delivery, exit-code
semantics, and ordering — so a bridging host does not have to reverse it from
Claude Code's own behavior.

`.claude/portability/capabilities.json` defines the host-neutral capabilities
the workflow requires; `.claude/adapters/` binds each declared host to them.
An adapter declaration is not runtime proof. A capability may be called native
only after its named conformance check passes; bridge-required safety
capabilities must refuse the dependent action until the bridge is verified.

## Runtime model

Execution is host-managed: Claude Code, Codex, or a generic agent host **is**
the runner. It reads this contract directly and drives the session; no
`ANTHROPIC_API_KEY` and no separate script are required for that path.

There is no standalone repository runner today. An earlier draft of this file
described one with `--host-managed`/`--dry-run`/`--sdk-live` flags before any
such binary existed — the same failure `harnesses.json`'s manifest test
already guards against for workflows (see the comment above its `workflows`
omission): a contract that promises a path with nothing behind it. If a
standalone automation path is ever built, it must satisfy this same contract
rather than a parallel one, and its dry-run mode must write nothing, matching
`.claude/install.py --dry-run`'s existing guarantee.

## Evidence contract

Every important claim needs evidence appropriate to the claim: test output for
behavior, a diff for scope, rendered output for visual quality, and a smoke or
log result for deployment. Record unresolved risks, deliberate exceptions,
owner, and follow-up date.

## Failure and safety

Stop on secrets, destructive ambiguity, scope escape, failed required checks,
or a missing approval. Use repository-native diagnosis and preserve recovery
state. Never hide an error to make a gate green.
